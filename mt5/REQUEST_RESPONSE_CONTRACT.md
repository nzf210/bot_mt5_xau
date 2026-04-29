# MT5 <-> Python Contract

## POST /analyze request
MT5 should send JSON matching `app.schemas.MarketRequest`.

Core fields:
- symbol
- timeframe
- higher_timeframe
- session
- bid
- ask
- spread
- ohlc[]
- indicators
- support_resistance
- trend_context
- position_context
- mode: dry_run | demo | live
- optional chart_image_base64, chart_image_mime

## Response
Python returns:
```json
{
  "ok": true,
  "phase": "A|C|D|E",
  "decision": {
    "decision_id": "uuid-string",
    "decision": "BUY|SELL|WAIT",
    "confidence": 0,
    "entry": 0,
    "stop_loss": 0,
    "take_profit": 0,
    "risk_reward": 0,
    "reason": "",
    "warnings": [],
    "source": "ai",
    "passed_filter": false,
    "filter_reason": ""
  },
  "raw_model_text": ""
}
```

## Trade result ingest
When MT5 reports trade results back to Python, it should include the same `decision_id` received from `/analyze` whenever available. This is used to link a closed or opened trade back to the exact originating AI decision for cleaner dataset building and model training.

## Execution rule in MT5
Only consider execution when all are true:
- mode is demo or live
- decision.decision is BUY or SELL
- decision.passed_filter is true
- DryRun is false
- if live, LiveMode must be true
