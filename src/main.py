import argparse
import asyncio
import logging
from pathlib import Path

from .config import load_config
from .rules_parser import parse_rules
from .content_detector import ContentDetector
from .browser_controller import BrowserController
from .utils.logger import setup_logger
from .utils.rate_limiter import RateLimiter
from .platforms.threads_platform import ThreadsPlatform

logger = logging.getLogger("content_filter")


async def run(args):
    config = load_config("config.yaml", args)
    config["dry_run"] = getattr(args, "dry_run", False)

    setup_logger(config.get("logging", {}))

    rules = parse_rules("unwanted_content.md")
    logger.info(f"Loaded {len(rules.keywords)} keywords, {len(rules.topics)} topics, {len(rules.content_patterns)} patterns")

    detection_config = config.get("detection", {})
    detector = ContentDetector(rules, detection_config)
    rate_limiter = RateLimiter(config.get("rate_limiting", {}))

    platform_name = config.get("platform", "threads")
    platforms_to_run = ["threads"] if platform_name == "threads" else [platform_name]

    for pname in platforms_to_run:
        controller = BrowserController(config)
        try:
            await controller.start(pname)

            # Check if login is needed
            auth_path = Path(f"auth/{pname}_state.json")
            if getattr(args, "login", False) or not auth_path.exists():
                login_url = _get_login_url(pname)
                await controller.manual_login(pname, login_url)

            platform = _create_platform(pname, controller.page, detector, rate_limiter, config)
            max_actions = config.get("max_actions_per_session", 50)
            await platform.run_filter_loop(max_actions=max_actions)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error running {pname}: {e}", exc_info=True)
        finally:
            await controller.shutdown()


def _get_login_url(platform: str) -> str:
    urls = {
        "threads": "https://www.threads.net/login",
        "x": "https://x.com/i/flow/login",
    }
    return urls[platform]


def _create_platform(name, page, detector, rate_limiter, config):
    if name == "threads":
        return ThreadsPlatform(page, detector, rate_limiter, config)
    raise ValueError(f"Unknown platform: {name}")


def cli():
    parser = argparse.ArgumentParser(description="Content filter for X and Threads")
    parser.add_argument("--platform", choices=["threads", "x", "both"], default=None,
                        help="Platform to filter (default: from config)")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--dry-run", action="store_true", help="Detect but don't take action")
    parser.add_argument("--max-actions", type=int, default=None, help="Max actions per session")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    cli()
