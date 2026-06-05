# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Telegram bot for a furniture store administrator (aiogram 3.x + aiosqlite + SQLite). The bot manages orders, product catalog, discounts, customer messaging, blacklists, analytics dashboards, and action logging.

### Branch structure

The main production code lives on `cursor-vkr-furniture-bot-6cf5`. The `main` branch contains only the thesis assignment document.

### Running the bot

```bash
source .venv/bin/activate
python -m bot.main
```

The bot requires a valid `BOT_TOKEN` in `.env` to connect to Telegram. Without it, the application initializes (config, DB schema, mock data source) but fails at `bot.get_me()` with `TelegramUnauthorizedError`.

### Configuration

Copy `.env.example` to `.env`. Key settings:
- `BOT_TOKEN` — required, obtain from @BotFather
- `ADMIN_IDS` — comma-separated Telegram user IDs
- `SHOP_SOURCE=mock` — use mock data (default, no external dependencies)
- `DB_PATH=data/furniture_bot.sqlite3` — auto-created on first run

### Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Directories `data/` and `logs/` are created automatically by the application.

### Seeding demo data

```bash
python scripts/seed_demo.py
```

Creates 60 demo orders and 8 products in the SQLite database.

### Linting

No linter config is committed. Use `ruff check bot/ scripts/` for quick linting. There are 3 pre-existing unused-import warnings (F401) in the existing code.

### Testing

No automated test suite exists. Verify functionality via:
1. `python -c "from bot.config import settings; print(settings.shop_source)"` — config loads
2. `python scripts/seed_demo.py` — DB operations work
3. `python -m bot.main` — application starts (requires valid BOT_TOKEN)

### Key gotchas

- The `build_orders_chart()` function in `bot/services/analytics.py` expects `Sequence[tuple[str, int]]` (date string, count), NOT raw `Order` objects.
- `MockShopAPI` methods are `fetch_new_orders()` and `fetch_products()` (not `fetch_orders` / `fetch_catalog`).
- `OrderSyncService` method is `run_once()` (not `sync_once`).
- Python 3.12 works despite README stating 3.11+ requirement.
- `python3.12-venv` system package is needed to create virtualenvs on Ubuntu 24.04.
