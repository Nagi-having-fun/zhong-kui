from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from .utils.logger import log_sleep, ActionTracer

logger = logging.getLogger("content_filter")


class BrowserController:
    def __init__(self, config: dict):
        self.config = config
        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self, platform: str):
        with ActionTracer("Launching Chromium browser"):
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)

        state_path = Path(f"auth/{platform}_state.json")
        if state_path.exists():
            logger.info(f"[AUTH] Loading saved session from {state_path}")
            self.context = await self.browser.new_context(storage_state=str(state_path))
        else:
            logger.info("[AUTH] No saved session found, starting fresh")
            self.context = await self.browser.new_context()

        self.page = await self.context.new_page()
        logger.info("[BROWSER] Browser ready")

    async def save_auth(self, platform: str):
        Path("auth").mkdir(exist_ok=True)
        state_path = f"auth/{platform}_state.json"
        await self.context.storage_state(path=state_path)
        logger.info(f"[AUTH] Session saved to {state_path}")

    async def manual_login(self, platform: str, url: str):
        logger.info(f"[AUTH] Navigating to login page: {url}")
        await self.page.goto(url)
        logger.info("[AUTH] Waiting for user to complete manual login...")
        input(f"\n>>> Please log in to {platform} in the browser, then press Enter here to continue...")
        logger.info("[AUTH] User confirmed login, saving session")
        await self.save_auth(platform)

    async def scroll_down(self):
        distance = random.randint(300, 700)
        logger.info(f"[SCROLL] Scrolling down {distance}px")
        await self.page.evaluate(f"window.scrollBy(0, {distance})")
        await log_sleep(random.uniform(1.5, 3.5), "post-scroll wait")

    async def shutdown(self):
        logger.info("[BROWSER] Shutting down...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("[BROWSER] Shutdown complete")
