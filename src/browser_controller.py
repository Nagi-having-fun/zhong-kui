import asyncio
import logging
import random
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext

logger = logging.getLogger("content_filter")


class BrowserController:
    def __init__(self, config: dict):
        self.config = config
        self.playwright = None
        self.browser = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self, platform: str):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)

        state_path = Path(f"auth/{platform}_state.json")
        if state_path.exists():
            logger.info(f"Loading saved session for {platform}")
            self.context = await self.browser.new_context(storage_state=str(state_path))
        else:
            self.context = await self.browser.new_context()

        self.page = await self.context.new_page()

    async def save_auth(self, platform: str):
        Path("auth").mkdir(exist_ok=True)
        state_path = f"auth/{platform}_state.json"
        await self.context.storage_state(path=state_path)
        logger.info(f"Session saved to {state_path}")

    async def manual_login(self, platform: str, url: str):
        await self.page.goto(url)
        input(f"\n>>> Please log in to {platform} in the browser, then press Enter here to continue...")
        await self.save_auth(platform)

    async def scroll_down(self):
        distance = random.randint(300, 700)
        await self.page.evaluate(f"window.scrollBy(0, {distance})")
        await asyncio.sleep(random.uniform(1.5, 3.5))

    async def shutdown(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
