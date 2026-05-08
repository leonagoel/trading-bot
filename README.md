# PrimeTrade Bot 🚀

> A clean, production-grade Binance Futures Testnet trading CLI built in Python.

```
 ██████╗ ██████╗ ██╗███╗   ███╗███████╗████████╗██████╗  █████╗ ██████╗ ███████╗
 ██╔══██╗██╔══██╗██║████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
 ██████╔╝██████╔╝██║██╔████╔██║█████╗     ██║   ██████╔╝███████║██║  ██║█████╗
 ██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝
 ██║     ██║  ██║██║██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██║  ██║██████╔╝███████╗
 ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
```

---

## Features

| Feature | Details |
|---|---|
| **Order Types** | MARKET, LIMIT, STOP_MARKET (bonus) |
| **Sides** | BUY and SELL |
| **Input Validation** | Full validation layer with clear error messages |
| **Logging** | Rotating file logs + color-coded console output |
| **Error Handling** | API errors, network timeouts, invalid input — all handled gracefully |
| **Clean Architecture** | Separated client / orders / validators / CLI layers |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py         # Package metadata
│   ├── client.py           # Binance REST client (signing, retries, error handling)
│   ├── orders.py           # Order placement logic (MARKET, LIMIT, STOP_MARKET)
│   ├── validators.py       # Input validation (symbol, side, type, qty, price)
│   ├── logging_config.py   # Rotating file + color console logging
│   └── cli.py              # CLI entry point (argparse, formatted output)
├── logs/
│   ├── sample_market_order.log
│   └── sample_limit_order.log
├── .env.example            # Credential template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / unzip the project

```bash
unzip trading_bot.zip
cd trading_bot
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your **Binance Futures Testnet** credentials:

```dotenv
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
```

> **Get testnet credentials:**
> 1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
> 2. Sign in with GitHub
> 3. Go to **API Key** tab → generate a new key pair
> 4. Copy both values into your `.env`

### 5. Load environment variables

```bash
# macOS / Linux
export $(grep -v '^#' .env | xargs)

# Windows (PowerShell)
Get-Content .env | ForEach-Object { if ($_ -notmatch '^#') { $k,$v = $_ -split '=',2; [System.Environment]::SetEnvironmentVariable($k,$v) } }
```

Alternatively, install `python-dotenv` (already in requirements) and it loads automatically.

---

## Usage

All commands follow the pattern:

```
python -m bot.cli <command> [options]
```

### Commands

#### `place` — Place an order

```
python -m bot.cli place --symbol SYMBOL --side BUY|SELL --type TYPE --quantity QTY [--price PRICE] [--stop-price STOP] [--tif GTC|IOC|FOK] [--json]
```

| Flag | Required | Description |
|---|---|---|
| `--symbol` | ✅ | Trading pair (e.g. `BTCUSDT`, `ETHUSDT`) |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` | ✅ | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--quantity` | ✅ | Order size |
| `--price` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Stop trigger price |
| `--tif` | ❌ | Time-in-force for LIMIT: `GTC` (default), `IOC`, `FOK` |
| `--json` | ❌ | Print raw JSON response instead of formatted output |

#### `account` — View balances & positions

```
python -m bot.cli account
```

#### `open-orders` — List open orders

```
python -m bot.cli open-orders [--symbol BTCUSDT]
```

#### `ping` — Check connectivity

```
python -m bot.cli ping
```

---

## Example Runs

### Market BUY 0.01 BTC

```bash
python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

```
┌────────────────────────────────────────────────┐
│              ORDER REQUEST                     │
├────────────────────────────────────────────────┤
│  Symbol       BTCUSDT                          │
│  Side         BUY                              │
│  Type         MARKET                           │
│  Quantity     0.01                             │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│              ORDER RESPONSE                    │
├────────────────────────────────────────────────┤
│  Order ID     4058629731                       │
│  Status       FILLED                           │
│  Exec Qty     0.01                             │
│  Avg Price    67432.10                         │
│  Client ID    web_abc123...                    │
└────────────────────────────────────────────────┘

  ✔  Order FILLED successfully!
```

---

### Limit SELL 0.05 ETH at $3200

```bash
python -m bot.cli place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3200
```

---

### Stop-Market BUY 0.01 BTC at $70000

```bash
python -m bot.cli place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 70000
```

---

### Raw JSON output

```bash
python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --json
```

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log` with rotation at 5 MB (keeps 3 files).

Each log line includes:

```
2025-07-14 10:23:01 | INFO     | bot.client | place_order:148 | Order placed | orderId=4058629731 status=FILLED
```

- **File logs**: DEBUG level — full request params (signature redacted), response status codes, exceptions with tracebacks
- **Console logs**: INFO level — clean, color-coded, human-readable

Sample log files for a MARKET order and a LIMIT order are included in `logs/`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Invalid symbol format | Clear validation error before any API call |
| Missing required price | Validation error with fix hint |
| Binance API error (e.g. -1121 Invalid Symbol) | Error message with Binance error code and message |
| Network timeout | Logged + user-friendly message; retried up to 3× automatically |
| Missing API credentials | Immediate exit with setup instructions |

---

## Assumptions

- The bot targets **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`)
- All symbols must end in `USDT` (e.g. `BTCUSDT`, `ETHUSDT`)
- Credentials are read from environment variables (not hardcoded)
- No `python-binance` library used — all interactions are direct REST calls via `requests`
- `STOP_MARKET` is implemented as the bonus third order type

---

## Dependencies

```
requests>=2.31.0      # HTTP client with retry support
urllib3>=2.0.0        # Used by requests
python-dotenv>=1.0.0  # Loads .env into environment
```

No third-party Binance SDK required.

---

*Built for the PrimeTrade.ai Python Developer Internship Assignment.*
