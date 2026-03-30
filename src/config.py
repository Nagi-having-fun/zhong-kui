import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(filepath: str = "config.yaml", args=None) -> dict:
    load_dotenv()  # Load .env file

    config = yaml.safe_load(Path(filepath).read_text(encoding="utf-8"))

    # CLI args override config file
    if args:
        if getattr(args, "platform", None):
            config["platform"] = args.platform
        if getattr(args, "max_actions", None):
            config["max_actions_per_session"] = args.max_actions
        if getattr(args, "dry_run", False):
            config["dry_run"] = True

    # Resolve OpenAI API key from .env
    detection = config.get("detection", {})
    detection["openai_api_key"] = os.environ.get("OPENAI_API_KEY", "")

    return config
