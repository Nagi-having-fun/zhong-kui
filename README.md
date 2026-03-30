# Preference Block

Automatically detect and dismiss unwanted content on Threads (and X/Twitter) using keyword matching and LLM-based classification.

## Features

- **Two-tier content detection**: Fast keyword scan + OpenAI GPT classification for nuanced pattern matching
- **Configurable rules**: Define unwanted topics, keywords, and content patterns in `unwanted_content.md`
- **Browser automation**: Uses Playwright to scroll feeds and click "Not interested"
- **Optional commenting**: Leave a polite dismissal comment (disabled by default)
- **Rate limiting**: Randomized delays and action budgets to avoid bot detection
- **Dry-run mode**: Test detection without taking any action

## Setup

### 1. Install dependencies

```bash
pip install playwright openai python-dotenv pyyaml
playwright install chromium
```

### 2. Configure API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-api-key-here
```

### 3. Define your content rules

Edit `unwanted_content.md` to add your own unwanted topics, keywords, and content patterns.

### 4. Adjust settings (optional)

Edit `config.yaml` to change:

- `platform`: `"threads"`, `"x"`, or `"both"`
- `max_actions_per_session`: Max posts to dismiss per run (default: 50)
- `leave_comment`: Set to `true` to enable commenting (default: false)
- `detection.llm_model`: OpenAI model for classification (default: `gpt-4o-mini`)
- `detection.llm_confidence_threshold`: Minimum confidence to flag a post (default: 0.7)
- `rate_limiting.*`: Adjust delays between actions

## Usage

### First run (login required)

```bash
python -m src.main --platform threads --login --dry-run
```

1. A Chromium browser will open and navigate to the login page
2. Log in manually in the browser
3. Press **Enter** in the terminal to continue
4. The tool scrolls your feed and logs detected posts (no actions taken in dry-run mode)

### Dry run (detect only)

```bash
python -m src.main --platform threads --dry-run
```

Review the output and check `logs/` for detection results.

### Live run

```bash
python -m src.main --platform threads
```

The tool will scroll your feed and click "Not interested" on matched posts.

### CLI flags

| Flag | Description |
|------|-------------|
| `--platform threads\|x\|both` | Platform to filter (default: from `config.yaml`) |
| `--login` | Force re-login (use if session expired) |
| `--dry-run` | Detect and log only, take no action |
| `--max-actions N` | Override max actions per session |

### Recommended test sequence

1. **`--dry-run`** — Review the log to check detection accuracy
2. **`--dry-run --max-actions 10`** — Look for false positives
3. **`--max-actions 3`** — Live test with just 3 dismissals while watching the browser
4. **Full run** once confident

## Project Structure

```
├── unwanted_content.md      # Your content filter rules
├── config.yaml              # Runtime configuration
├── .env                     # OpenAI API key (gitignored)
├── src/
│   ├── main.py              # CLI entry point
│   ├── config.py            # Config + .env loader
│   ├── rules_parser.py      # Parses unwanted_content.md
│   ├── content_detector.py  # Keyword + LLM detection
│   ├── browser_controller.py# Playwright browser lifecycle
│   ├── platforms/
│   │   ├── base_platform.py # Abstract platform interface
│   │   └── threads_platform.py # Threads-specific automation
│   └── utils/
│       ├── logger.py        # Logging setup
│       └── rate_limiter.py  # Anti-detection delays
├── auth/                    # Saved browser sessions (gitignored)
└── logs/                    # Run logs (gitignored)
```

## License

MIT
