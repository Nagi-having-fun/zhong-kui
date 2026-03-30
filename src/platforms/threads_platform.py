import asyncio
import logging
import random

from playwright.async_api import Page, Locator

from .base_platform import BasePlatform, PostElement
from ..content_detector import ContentDetector
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger("content_filter")


class ThreadsPlatform(BasePlatform):
    FEED_URL = "https://www.threads.net/"
    LOGIN_URL = "https://www.threads.net/login"

    async def navigate_to_feed(self):
        await self.page.goto(self.FEED_URL, wait_until="domcontentloaded")
        # Wait for posts to load
        await self.page.wait_for_timeout(3000)
        logger.info("Navigated to Threads feed")

    async def get_visible_posts(self) -> list[PostElement]:
        posts: list[PostElement] = []

        # Threads renders posts inside divs with role="article" or uses
        # semantic elements. We use a JS-based extraction for resilience.
        post_data = await self.page.evaluate("""
            () => {
                const results = [];
                // Threads posts are typically in elements with data-pressable-container
                // or we can look for the post text containers
                const articles = document.querySelectorAll('[data-pressable-container="true"]');
                for (const article of articles) {
                    // Extract text content from the post
                    const textEls = article.querySelectorAll('span');
                    let text = '';
                    for (const span of textEls) {
                        // Skip very short spans (usually UI elements)
                        if (span.textContent && span.textContent.length > 2) {
                            text += span.textContent + ' ';
                        }
                    }
                    text = text.trim();
                    if (!text) continue;

                    // Try to get a unique ID from a link
                    const link = article.querySelector('a[href*="/post/"]');
                    const href = link ? link.getAttribute('href') : null;

                    // Get position for identification
                    const rect = article.getBoundingClientRect();
                    const id = href || `pos_${Math.round(rect.top)}_${Math.round(rect.left)}`;

                    results.push({ id, text, top: rect.top });
                }
                return results;
            }
        """)

        for data in post_data:
            # Create a locator that can find this post element
            if "/post/" in data["id"]:
                selector = f'[data-pressable-container="true"]:has(a[href*="{data["id"]}"])'
            else:
                # Fallback: use nth-of-type based on position
                selector = f'[data-pressable-container="true"]'

            locator = self.page.locator(selector).first
            posts.append(PostElement(id=data["id"], text=data["text"], element=locator))

        logger.debug(f"Found {len(posts)} visible posts")
        return posts

    async def dismiss_post(self, post: PostElement):
        # Find the "more" menu button (three dots / ellipsis) within the post
        # Threads uses various selectors for this; try multiple approaches
        more_button = None

        # Approach 1: Look for SVG-based more button near the post
        try:
            # Scroll post into view first
            await post.element.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.3, 0.8))

            # Threads "more" button is typically an icon button with aria-label
            more_button = post.element.get_by_role("button", name="More")
            if await more_button.count() == 0:
                # Try alternative: look for a button with "..." or ellipsis icon
                more_button = post.element.locator('div[role="button"]').filter(
                    has=self.page.locator('svg')
                ).last

            await more_button.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            logger.warning(f"Could not find more button: {e}")
            raise

        # Click "Not interested" from the popup menu
        try:
            # Look for the menu item containing "Not interested" or similar text
            not_interested = self.page.get_by_text("Not interested", exact=False)
            if await not_interested.count() > 0:
                await not_interested.first.click()
            else:
                # Try alternative text variations
                hide_btn = self.page.get_by_text("Hide", exact=False)
                if await hide_btn.count() > 0:
                    await hide_btn.first.click()
                else:
                    # Try to find any menu item that suggests hiding/dismissing
                    mute_btn = self.page.get_by_text("Mute", exact=False)
                    if await mute_btn.count() > 0:
                        await mute_btn.first.click()
                    else:
                        raise Exception("No dismiss option found in menu")

            await asyncio.sleep(random.uniform(0.5, 1.5))
            logger.debug("Clicked dismiss option")
        except Exception as e:
            # Try to close the menu if we couldn't find the option
            await self.page.keyboard.press("Escape")
            raise

    async def leave_comment(self, post: PostElement, message: str):
        try:
            await post.element.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.3, 0.8))

            # Click the comment/reply icon on the post
            reply_button = post.element.get_by_role("button", name="Reply")
            if await reply_button.count() == 0:
                reply_button = post.element.get_by_role("button", name="Comment")

            await reply_button.first.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))

            # Type the comment in the reply input
            # Threads uses a contenteditable div or textarea for replies
            reply_input = self.page.locator(
                'div[contenteditable="true"], textarea[placeholder*="Reply"], textarea[placeholder*="reply"]'
            ).first
            await reply_input.click()
            await reply_input.fill(message)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # Submit the reply
            post_button = self.page.get_by_role("button", name="Post")
            if await post_button.count() == 0:
                post_button = self.page.get_by_role("button", name="Reply")
            await post_button.first.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))

            logger.debug("Comment posted successfully")
        except Exception as e:
            # Close any open dialogs
            await self.page.keyboard.press("Escape")
            raise
