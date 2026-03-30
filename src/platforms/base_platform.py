from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Set

from playwright.async_api import Page, Locator

from ..content_detector import ContentDetector
from ..utils.rate_limiter import RateLimiter
from ..utils.logger import log_sleep, ActionTracer

logger = logging.getLogger("content_filter")

DEFAULT_COMMENT = "This content is not relevant to me. Please stop recommending similar posts."


@dataclass
class PostElement:
    id: str
    text: str
    element: Locator


class BasePlatform(ABC):
    def __init__(self, page: Page, detector: ContentDetector, rate_limiter: RateLimiter, config: dict):
        self.page = page
        self.detector = detector
        self.rate_limiter = rate_limiter
        self.config = config
        self.dry_run = config.get("dry_run", False)

    @abstractmethod
    async def navigate_to_feed(self): ...

    @abstractmethod
    async def get_visible_posts(self) -> list[PostElement]: ...

    @abstractmethod
    async def dismiss_post(self, post: PostElement): ...

    @abstractmethod
    async def leave_comment(self, post: PostElement, message: str): ...

    async def scroll_down(self):
        distance = random.randint(300, 700)
        await log_sleep(random.uniform(0.5, 1.0), "pre-scroll pause")
        logger.info(f"[SCROLL] Scrolling down {distance}px")
        await self.page.evaluate(f"window.scrollBy(0, {distance})")
        wait = random.uniform(1.5, 3.5)
        await log_sleep(wait, "waiting for new posts to load after scroll")

    async def run_filter_loop(self, max_actions: int = 50):
        with ActionTracer("Navigate to feed"):
            await self.navigate_to_feed()

        seen_ids: set[str] = set()
        action_count = 0
        skip_count = 0
        leave_comment = self.config.get("leave_comment", False)
        comment_text = self.config.get("comment_text", DEFAULT_COMMENT)

        logger.info("=" * 60)
        logger.info(f"[CONFIG] max_actions={max_actions}, dry_run={self.dry_run}, leave_comment={leave_comment}")
        logger.info("=" * 60)

        scroll_round = 0
        while action_count < max_actions:
            scroll_round += 1
            logger.info(f"--- Scroll round #{scroll_round} | actions={action_count}/{max_actions} | seen={len(seen_ids)} | skipped={skip_count} ---")

            with ActionTracer(f"Extracting visible posts (round #{scroll_round})"):
                posts = await self.get_visible_posts()
            logger.info(f"[SCAN] Found {len(posts)} visible posts")

            for i, post in enumerate(posts):
                if post.id in seen_ids:
                    continue
                seen_ids.add(post.id)

                preview = post.text[:100].replace("\n", " ")
                logger.info(f"[POST #{len(seen_ids)}] Analyzing: {preview}")

                with ActionTracer("Content detection"):
                    result = self.detector.check(post.text)

                if result.matched:
                    logger.info(
                        f"[MATCH] confidence={result.confidence:.2f} | reason={result.reason}"
                    )

                    if self.dry_run:
                        logger.info("[DRY RUN] Would dismiss this post — skipping action")
                        action_count += 1
                        continue

                    logger.info("[RATE LIMIT] Waiting before action...")
                    await self.rate_limiter.wait()

                    with ActionTracer("Dismiss post"):
                        try:
                            await self.dismiss_post(post)
                            action_count += 1
                            logger.info(f"[ACTION] Post dismissed ({action_count}/{max_actions})")
                        except Exception as e:
                            logger.warning(f"[FAIL] Dismiss failed: {e}")
                            continue

                    if leave_comment:
                        with ActionTracer("Leave comment"):
                            try:
                                await self.leave_comment(post, comment_text)
                                logger.info(f"[ACTION] Comment posted: {comment_text[:50]}...")
                            except Exception as e:
                                logger.warning(f"[FAIL] Comment failed: {e}")
                else:
                    skip_count += 1
                    logger.debug(f"[SKIP] No match (confidence={result.confidence:.2f})")

            with ActionTracer(f"Scroll #{scroll_round}"):
                await self.scroll_down()

        logger.info("=" * 60)
        logger.info(f"[SUMMARY] Filter loop complete")
        logger.info(f"  Actions taken: {action_count}")
        logger.info(f"  Posts scanned: {len(seen_ids)}")
        logger.info(f"  Posts skipped: {skip_count}")
        logger.info("=" * 60)
