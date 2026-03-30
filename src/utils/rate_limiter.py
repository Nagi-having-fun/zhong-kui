import asyncio
import logging
import random

logger = logging.getLogger("content_filter")


class RateLimiter:
    def __init__(self, config: dict):
        self.min_delay = config.get("min_delay_seconds", 3)
        self.max_delay = config.get("max_delay_seconds", 8)
        self.actions_before_pause = config.get("actions_before_pause", 10)
        self.pause_duration = config.get("pause_duration_seconds", 30)
        self.action_count = 0

    async def wait(self):
        self.action_count += 1
        if self.action_count % self.actions_before_pause == 0:
            delay = self.pause_duration + random.uniform(0, 10)
            logger.info(f"Pausing for {delay:.1f}s after {self.action_count} actions")
        else:
            delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
