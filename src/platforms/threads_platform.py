from __future__ import annotations

import asyncio
import logging
import random
from typing import List

from playwright.async_api import Page, Locator

from .base_platform import BasePlatform, PostElement
from ..content_detector import ContentDetector
from ..utils.rate_limiter import RateLimiter
from ..utils.logger import log_sleep, ActionTracer

logger = logging.getLogger("content_filter")


class ThreadsPlatform(BasePlatform):
    FEED_URL = "https://www.threads.net/"
    LOGIN_URL = "https://www.threads.net/login"

    async def navigate_to_feed(self):
        logger.info(f"[NAV] Loading {self.FEED_URL}")
        await self.page.goto(self.FEED_URL, wait_until="domcontentloaded")
        await log_sleep(3.0, "waiting for Threads feed to fully render")
        logger.info("[NAV] Threads feed loaded")

    async def get_visible_posts(self) -> list[PostElement]:
        posts: list[PostElement] = []

        post_data = await self.page.evaluate("""
            () => {
                const results = [];
                const articles = document.querySelectorAll('[data-pressable-container="true"]');
                for (const article of articles) {
                    const textEls = article.querySelectorAll('span');
                    let text = '';
                    for (const span of textEls) {
                        if (span.textContent && span.textContent.length > 2) {
                            text += span.textContent + ' ';
                        }
                    }
                    text = text.trim();
                    if (!text) continue;

                    const link = article.querySelector('a[href*="/post/"]');
                    const href = link ? link.getAttribute('href') : null;

                    const rect = article.getBoundingClientRect();
                    const id = href || `pos_${Math.round(rect.top)}_${Math.round(rect.left)}`;

                    results.push({ id, text, top: rect.top });
                }
                return results;
            }
        """)

        for data in post_data:
            if "/post/" in data["id"]:
                selector = f'[data-pressable-container="true"]:has(a[href*="{data["id"]}"])'
            else:
                selector = '[data-pressable-container="true"]'

            locator = self.page.locator(selector).first
            posts.append(PostElement(id=data["id"], text=data["text"], element=locator))

        logger.info(f"[EXTRACT] Extracted {len(posts)} posts from DOM")
        return posts

    async def dismiss_post(self, post: PostElement):
        """辟邪: Click "Not interested" to dismiss unwanted post."""
        menu_texts = await self._open_more_menu(post)

        logger.info("[DISMISS] Looking for dismiss option in menu")
        exact_texts = [
            "不感兴趣", "不感興趣", "Not interested",
            "没兴趣", "沒興趣",
            "不想看", "不关心", "不關心",
            "隐藏", "隱藏", "Hide",
        ]
        fuzzy_keywords = [
            "兴趣", "興趣", "interested",
            "不想看", "不关心", "不關心",
            "隐藏", "隱藏", "hide",
        ]

        clicked = await self._click_menu_option(exact_texts, fuzzy_keywords, menu_texts, "DISMISS")

        if not clicked:
            logger.warning("[DISMISS] No dismiss option found in menu, pressing Escape")
            await self.page.keyboard.press("Escape")
            raise Exception(f"No dismiss option found. Menu had: {menu_texts}")

        await log_sleep(random.uniform(0.5, 1.5), "waiting for dismiss animation")
        logger.info("[DISMISS] Post dismissed successfully (辟邪)")

    async def _open_more_menu(self, post: PostElement):
        """Shared helper: scroll post into view and click the '更多/More' button."""
        logger.info("[MORE] Scrolling post into view")
        await post.element.scroll_into_view_if_needed()
        await log_sleep(random.uniform(0.3, 0.8), "pause after scrolling post into view")

        logger.info("[MORE] Looking for 'More' / '更多' button")
        more_button = None

        for label in ["更多", "More", "更多選項", "更多选项"]:
            btn = post.element.get_by_role("button", name=label)
            if await btn.count() > 0:
                more_button = btn.first
                logger.info(f"[MORE] Found button by role name='{label}'")
                break

        if more_button is None:
            logger.info("[MORE] Trying aria-label contains 'more' fallback")
            btn = post.element.locator('[aria-label*="更多"], [aria-label*="more" i], [aria-label*="More"]')
            if await btn.count() > 0:
                more_button = btn.first
                logger.info("[MORE] Found button by aria-label contains 'more'")

        if more_button is None:
            logger.info("[MORE] Trying JS-based detection for three-dot button")
            found = await self.page.evaluate("""
                (postText) => {
                    const articles = document.querySelectorAll('[data-pressable-container="true"]');
                    for (const article of articles) {
                        if (!article.textContent.includes(postText.substring(0, 30))) continue;
                        const buttons = article.querySelectorAll('div[role="button"]');
                        for (const btn of buttons) {
                            const svg = btn.querySelector('svg');
                            if (!svg) continue;
                            const circles = svg.querySelectorAll('circle');
                            if (circles.length >= 3) {
                                btn.setAttribute('data-cf-more-btn', 'true');
                                return true;
                            }
                        }
                    }
                    return false;
                }
            """, post.text)
            if found:
                more_button = post.element.locator('[data-cf-more-btn="true"]').first
                logger.info("[MORE] Found three-dot button via SVG circle detection")

        if more_button is None:
            raise Exception("Could not find 'More' (三个点) button on this post")

        logger.info("[MORE] Clicking 'More' button")
        await more_button.click()
        await log_sleep(random.uniform(0.5, 1.0), "waiting for menu to appear")

        # Dump menu texts for debugging
        await asyncio.sleep(0.5)
        menu_texts = await self.page.evaluate("""
            () => {
                const items = [];
                const allEls = document.querySelectorAll('div[role="dialog"] *, div[role="menu"] *, div[role="listbox"] *, div[role="button"], span');
                for (const el of allEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && el.textContent && el.textContent.trim().length > 0 && el.textContent.trim().length < 50) {
                        const t = el.textContent.trim();
                        if (!items.includes(t)) items.push(t);
                    }
                }
                return items.slice(0, 30);
            }
        """)
        logger.info(f"[MORE] Visible menu texts: {menu_texts}")
        return menu_texts

    async def _click_menu_option(self, exact_texts: list, fuzzy_keywords: list, menu_texts: list, action_name: str) -> bool:
        """Shared helper: find and click a menu option with exact + fuzzy matching."""
        # Phase 1: exact match on visible elements
        for text in exact_texts:
            btn = self.page.locator(f'text="{text}" >> visible=true')
            if await btn.count() > 0:
                logger.info(f"[{action_name}] Exact match: clicking '{text}'")
                await btn.first.click()
                return True

        # Phase 2: fuzzy match against dumped menu texts
        if menu_texts:
            for menu_item in menu_texts:
                for kw in fuzzy_keywords:
                    if kw in menu_item:
                        logger.info(f"[{action_name}] Fuzzy match: '{kw}' found in '{menu_item}'")
                        btn = self.page.locator(f'text="{menu_item}" >> visible=true')
                        if await btn.count() > 0:
                            await btn.first.click()
                            return True

        return False

    async def block_user(self, post: PostElement):
        """除魔: Block the user who posted unwanted content."""
        menu_texts = await self._open_more_menu(post)

        logger.info("[BLOCK] Looking for block/mute option in menu")
        exact_texts = [
            "屏蔽", "封鎖", "封锁", "Block",
            "拉黑", "拉黑该用户",
            "静音", "靜音", "Mute",
            "屏蔽用户", "屏蔽此用户",
        ]
        fuzzy_keywords = [
            "屏蔽", "封鎖", "封锁", "block", "Block",
            "拉黑",
            "静音", "靜音", "mute", "Mute",
        ]

        clicked = await self._click_menu_option(exact_texts, fuzzy_keywords, menu_texts, "BLOCK")

        if not clicked:
            logger.warning(f"[BLOCK] No block/mute option found in menu, pressing Escape")
            await self.page.keyboard.press("Escape")
            raise Exception(f"No block/mute option found. Menu had: {menu_texts}")

        await log_sleep(random.uniform(0.5, 1.5), "waiting for block confirmation")

        # Handle confirmation dialog if one appears
        confirm_texts = [
            "屏蔽", "封鎖", "封锁", "Block",
            "确认", "確認", "Confirm",
            "确定", "確定",
        ]
        for text in confirm_texts:
            btn = self.page.locator(f'text="{text}" >> visible=true')
            if await btn.count() > 0:
                logger.info(f"[BLOCK] Confirming block: clicking '{text}'")
                await btn.first.click()
                await log_sleep(random.uniform(0.5, 1.0), "waiting for block to complete")
                break

        logger.info("[BLOCK] User blocked successfully (除魔)")

    async def leave_comment(self, post: PostElement, message: str):
        logger.info("[COMMENT] Scrolling post into view")
        await post.element.scroll_into_view_if_needed()
        await log_sleep(random.uniform(0.3, 0.8), "pause before clicking reply")

        # Click the reply button
        logger.info("[COMMENT] Looking for Reply/Comment button")
        reply_button = post.element.get_by_role("button", name="Reply")
        if await reply_button.count() == 0:
            reply_button = post.element.get_by_role("button", name="Comment")
        logger.info("[COMMENT] Clicking reply button")
        await reply_button.first.click()
        await log_sleep(random.uniform(1.0, 2.0), "waiting for reply input to appear")

        # Type the comment
        logger.info("[COMMENT] Typing comment text")
        reply_input = self.page.locator(
            'div[contenteditable="true"], textarea[placeholder*="Reply"], textarea[placeholder*="reply"]'
        ).first
        await reply_input.click()
        await reply_input.fill(message)
        await log_sleep(random.uniform(0.5, 1.0), "pause after typing comment")

        # Submit
        logger.info("[COMMENT] Submitting comment")
        post_button = self.page.get_by_role("button", name="Post")
        if await post_button.count() == 0:
            post_button = self.page.get_by_role("button", name="Reply")
        await post_button.first.click()
        await log_sleep(random.uniform(1.0, 2.0), "waiting for comment to post")
        logger.info("[COMMENT] Comment posted successfully")
