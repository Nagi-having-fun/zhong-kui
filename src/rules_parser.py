import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FilterRules:
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    content_patterns: list[str] = field(default_factory=list)
    other_rules: list[str] = field(default_factory=list)


def parse_rules(filepath: str = "unwanted_content.md") -> FilterRules:
    text = Path(filepath).read_text(encoding="utf-8")
    # Strip HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    sections: dict[str, str] = {}
    current_section = None
    lines = text.split("\n")

    for line in lines:
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            sections[current_section] = ""
        elif current_section is not None:
            sections[current_section] += line + "\n"

    rules = FilterRules()

    if "topics" in sections:
        rules.topics = _extract_lines(sections["topics"])

    # Handle keyword sections with various names
    for key in sections:
        if "keyword" in key:
            raw = sections[key].strip()
            # Split on "/" and filter empty
            rules.keywords = [k.strip() for k in raw.split("/") if k.strip()]
            break

    if "content patterns" in sections:
        rules.content_patterns = _extract_lines(sections["content patterns"])

    if "other rules" in sections:
        rules.other_rules = _extract_lines(sections["other rules"])

    return rules


def _extract_lines(text: str) -> list[str]:
    return [line.strip() for line in text.strip().split("\n") if line.strip()]
