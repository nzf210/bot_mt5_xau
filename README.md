# MT5 AI Bot, Python + Gemini

A phased trading bot scaffold built for MT5 execution, Python orchestration, and Gemini analysis.

## What is included
- FastAPI service with `/analyze`, `/health`, `/review/daily`, `/review/symbol/{symbol}`, `/review/timeframe/{timeframe}`, `/trade-result`, `/profile/{mode}`, `/kill-switch`, and `/news/cache`
- Structured market request and decision response schemas
- Gemini client for text and optional vision flow
- Decision parsing and schema validation
- Risk filter with emergency stop, session checks, spread, confidence, RR, duplicate signal, daily trade caps, timestamp-based cooldown, max daily loss guard, and external news blackout checks
- Persistent SQLite state for duplicate signal, cooldown, daily trade counting, and news event cache
- Trade result ingest and daily performance aggregation
- Profile-based behavior for dry-run/demo/live
- Symbol normalization and currency mapping service for hybrid news guard
- JSONL logging for decisions and trade events
- MT5 EA bridge with HTTP POST, market JSON builder, MT5 news-guard stub/context, stronger decision subtree parsing, guarded execution hook, and close-result reporting
- Demo/live safety flags

## Project layout
```text
mt5_ai_bot/
├── app/
├── data/
├── logs/
├── mt5/
├── SOP.md
├── CHECKLIST_DAILY.md
├── CHECKLIST_WEEKLY_ADAPTIVE.md
├── .env.example
├── requirements.txt
└── README.md
```

## Phase mapping
### Phase A, local pipeline
Goal: MT5 -> Python -> Gemini -> Python -> MT5, no trade execution.
- Use `mode=dry_run`
- Keep `EMERGENCY_STOP=true`
- Keep `ALLOW_LIVE_TRADING=false`

### Phase B, stronger filtering and observability
Goal: validate schema, filter weak signals, log every decision.
- Scaffolded in `risk_filter.py`, `logger_service.py`, and `state_store.py`
- Tune thresholds in `.env`
- State persists in `data/bot_state.sqlite3`

### Phase C, demo execution
Goal: enable demo mode with tiny size and strict caps.
- Set MT5 EA `DryRun=false`, `DemoMode=true`, `LiveMode=false`
- Send `mode=demo`
- Keep `ALLOW_LIVE_TRADING=false`
- Keep `EMERGENCY_STOP=false` only after testing

### Phase D, vision
Goal: include screenshot context and multimodal Gemini request.
- Set `ENABLE_VISION=true`
- Send `chart_image_base64` and `chart_image_mime`
- Keep same decision schema

### Phase E, cautious live
Goal: real-money trading with strict protection.
- Set `ALLOW_LIVE_TRADING=true`
- Set `EMERGENCY_STOP=false`
- MT5 EA `LiveMode=true`
- Use one symbol, one timeframe, smallest lot, one open position max

## Quick start

### Linux or macOS
#### 1. Create venv and install
```bash
cd mt5_ai_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Configure env
```bash
cp .env.example .env
# edit .env and put your Gemini API key
```

#### 3. Run API
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Windows
#### 1. Create venv and install
```powershell
cd mt5_ai_bot
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
```

For Command Prompt use:
```bat
cd mt5_ai_bot
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

#### 2. Configure env
```powershell
copy .env.example .env
```
Then edit `.env` and put your Gemini API key.

#### 3. Run API
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Test health
```bash
curl http://127.0.0.1:8000/health
```

### 4b. Test daily review
```bash
curl http://127.0.0.1:8000/review/daily
```

### 4c. Test trade result ingest
```bash
curl -X POST http://127.0.0.1:8000/trade-result \
  -H 'Content-Type: application/json' \
  --data @data/sample_trade_result.json
```

### 4d. Test symbol/timeframe review
```bash
curl http://127.0.0.1:8000/review/symbol/XAUUSD
curl http://127.0.0.1:8000/review/timeframe/M15
```

### 4e. Test profiles and kill switch
```bash
curl http://127.0.0.1:8000/profile/dry_run
curl http://127.0.0.1:8000/profile/demo
curl http://127.0.0.1:8000/profile/live
curl http://127.0.0.1:8000/kill-switch
curl -X POST http://127.0.0.1:8000/kill-switch -H 'Content-Type: application/json' -d '{"active":true,"reason":"manual_stop"}'
```

### 4f. Test external news cache
```bash
curl -X POST http://127.0.0.1:8000/news/cache \
  -H 'Content-Type: application/json' \
  --data @data/sample_news_events.json
```

### 5. Test analyze with sample request
```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  --data @data/sample_market_request.json
```

### 6. Wire MT5
- In MT5, add `http://127.0.0.1:8000` to allowed WebRequest URLs.
- Copy `mt5/AiTraderEA.mq5` into your MT5 Experts folder.
- On Windows this is usually under one of these paths:
  - `%APPDATA%\MetaQuotes\Terminal\<instance-id>\MQL5\Experts\`
  - or from MT5 use `File -> Open Data Folder`, then open `MQL5\Experts`
- Compile in MetaEditor.
- Start with `DryRun=true`.
- Attach EA to one chart only.
- Watch the Experts tab for the outbound payload/result.
- Optional: keep `EnableMt5FileLogging=true` to create `mt5_ai_bridge_log.csv` in the terminal files area.
- Optional: turn on `EnableVision=true` only after the Python `.env` has `ENABLE_VISION=true`.
- MT5 news guard is wired as a stub path first. You can simulate a blackout by setting terminal Global Variable `MT5_NEWS_BLACKOUT_<SYMBOL>` to `1`, for example `MT5_NEWS_BLACKOUT_XAUUSD`.

## Dataset builder and adaptive analytics
After you have some logs/results, you can export datasets and generate a first adaptive report:

```bash
python scripts/build_decision_dataset.py
python scripts/build_trade_dataset.py
python scripts/run_adaptive_analytics.py
```

Outputs:
- `data/training/decision_dataset.csv`
- `data/training/trade_outcome_dataset.csv`
- `data/exports/adaptive_report.json`

To push one level further and get a ready-to-review recommendation package:

```bash
python scripts/generate_config_recommendation.py
python scripts/compare_config_vs_recommendation.py
python scripts/run_adaptive_tuning.py
```

Additional outputs:
- `data/exports/recommended_config.env`
- `data/exports/config_comparison.json`
- `data/exports/candidate_config.env`

Model-assisted learning scaffolding:

```bash
python scripts/train_setup_model.py
python scripts/evaluate_setup_model.py
python scripts/tune_model_threshold.py
python scripts/log_model_evaluation_history.py
python scripts/summarize_model_history.py
python scripts/promote_candidate_model.py
python scripts/rollback_model.py
```

Model paths:
- `models/current/model.pkl`
- `models/current/model_meta.json`
- `models/candidates/candidate_model.pkl`
- `models/candidates/candidate_model_meta.json`
- `models/reports/model_evaluation.json`
- `models/reports/model_threshold_tuning.json`
- `models/reports/model_evaluation_history.jsonl`
- `models/reports/model_history_summary.json`

Approval and rollback flow:

```bash
python scripts/check_performance_checkpoint.py
python scripts/check_rollback_trigger.py
python scripts/log_tuning_history.py
python scripts/approve_candidate_config.py
python scripts/rollback_env_config.py
```

Additional outputs:
- `data/exports/performance_checkpoint.json`
- `data/exports/rollback_trigger_check.json`
- `data/exports/adaptive_tuning_history.jsonl`

Notes:
- `run_adaptive_tuning.py` now prepares a candidate config file automatically and logs tuning history.
- `check_performance_checkpoint.py` gives a quick gate before you approve a candidate.
- `check_rollback_trigger.py` gives a simple rollback signal scaffold if weak outcomes persist.
- `approve_candidate_config.py` merges the candidate into `.env` and creates a timestamped backup first.
- `rollback_env_config.py` restores the latest backup.

## Running on Windows, recommended flow
1. Open PowerShell in the project folder.
2. Activate the virtual environment:
```powershell
.\.venv\Scripts\activate
```
3. Start the API:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
4. Open MT5 on the same Windows machine.
5. Add `http://127.0.0.1:8000` to MT5 WebRequest allowlist.
6. Compile and attach `AiTraderEA.mq5`.
7. Start with `DryRun=true`, then move to demo only after logs look clean.

## Live safety
Never start with live mode.
Recommended progression:
1. Dry run only
2. Demo execution with tiny size
3. Review logs for days or weeks
4. Enable live with smallest risk

## Notes
- Read `SOP.md` for the full operating procedure.
- Use `CHECKLIST_DAILY.md` for routine monitoring.
- Use `CHECKLIST_WEEKLY_ADAPTIVE.md` before tuning, approval, or promotion.
- Daily counts, duplicate signal checks, cooldown source timestamps, and external news cache now persist in `data/bot_state.sqlite3`.
- Trade results are stored in the same SQLite database and surfaced through `/review/daily`, `/review/symbol/{symbol}`, and `/review/timeframe/{timeframe}`.
- Profiles let you inspect effective dry-run/demo/live behavior without changing code, and the kill switch lets you stop new signals quickly through the API.
- The external news layer is now active in Python risk filtering. If cached high or medium impact news falls inside the blackout window for the symbol currencies, the decision is blocked before execution.
- MT5 now sends `news_context` and can locally short-circuit on an MT5-side blackout stub before calling Python. This is ready to be swapped to real calendar integration later.
- A bounded model-assisted scoring hook now exists in Python. It now supports a simple statistical model pipeline using scikit-learn, uses a configurable `MODEL_SCORE_THRESHOLD`, and can now tune that threshold from evaluation data before feeding it back into the recommendation flow.
- Current MT5 bridge now builds real payloads, posts to Python, parses the response, validates core fields, can execute guarded demo/live trades when you turn off `DryRun`, and reports both open and closed trade states.
- Vision support is wired in both layers and only activates when `ENABLE_VISION=true` in Python and `EnableVision=true` in MT5.
- The MT5 JSON parser is still a lightweight manual parser, but it now extracts the `decision` subtree first so top-level `phase` and nested `decision.decision` do not collide.
