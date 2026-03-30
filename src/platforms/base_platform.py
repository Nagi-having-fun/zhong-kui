import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from playwright.async_api import Page, Locator

from ..content_detector import ContentDetector
from ..utils.rate_limiter import RateLimiter

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
        import random
        distance = random.randint(300, 700)
        await self.page.evaluate(f"window.scrollBy(0, {distance})")
        await asyncio.sleep(random.uniform(1.5, 3.5))

    async def run_filter_loop(self, max_actions: int = 50):
        await self.navigate_to_feed()
        seen_ids: set[str] = set()
        action_count = 0
        leave_comment = self.config.get("leave_comment", False)
        comment_text = self.config.get("comment_text", DEFAULT_COMMENT)

        logger.info(f"Starting filter loop (max_actions={max_actions}, dry_run={self.dry_run})")

        while action_count < max_actions:
            posts = await self.get_visible_posts()
            for post in posts:
                if post.id in seen_ids:
                    continue
                seen_ids.add(post.id)

                result = self.detector.check(post.text)
                if result.matched:
                    preview = post.text[:80].replace("\n", " ")
                    logger.info(
                        f"[MATCH] confidence={result.confidence:.2f} reason={result.reason} | {preview}"
                    )

                    if self.dry_run:
                        logger.info("[DRY RUN] Would dismiss this post")
                        action_count += 1
                        continue

                    await self.rate_limiter.wait()
                    try:
                        await self.dismiss_post(post)
                        logger.info("[ACTION] Dismissed post")
                        action_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to dismiss post: {e}")
                        continue

                    if leave_comment:
                        try:
                            await self.leave_comment(post, comment_text)
                            logger.info("[ACTION] Left comment")
                        except Exception as e:
                            logger.warning(f"Failed to leave comment: {e}")

            await self.scroll_down()

        logger.info(f"Filter loop complete. Actions taken: {action_count}")
