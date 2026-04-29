from pathlib import Path
import json
import joblib
import pandas as pd
from app.config import get_settings
from app.models.trade_decision import TradeDecision
from app.schemas import MarketRequest


ROOT = Path(__file__).resolve().parents[2]
CURRENT_MODEL = ROOT / "models" / "current" / "model.pkl"
CURRENT_META = ROOT / "models" / "current" / "model_meta.json"


def load_current_model() -> tuple[object | None, dict | None]:
    if not CURRENT_MODEL.exists() or not CURRENT_META.exists():
        return None, None
    model = joblib.load(CURRENT_MODEL)
    meta = json.loads(CURRENT_META.read_text(encoding="utf-8"))
    return model, meta


def build_model_feature_row(market: MarketRequest, decision: TradeDecision) -> dict:
    return {
        "confidence": int(decision.confidence),
        "risk_reward": float(decision.risk_reward),
        "spread": float(market.spread),
        "entry_price": float(decision.entry),
        "stop_loss": float(decision.stop_loss),
        "take_profit": float(decision.take_profit),
        "symbol": market.symbol,
        "timeframe": market.timeframe,
        "session": market.session,
        "decision": decision.decision,
        "mode": market.mode,
        "ema20": float(market.indicators.ema20) if getattr(market, 'indicators', None) else 0,
        "ema50": float(market.indicators.ema50) if getattr(market, 'indicators', None) else 0,
        "rsi14": float(market.indicators.rsi14) if getattr(market, 'indicators', None) else 0,
        "macd_main": float(market.indicators.macd_main or 0) if getattr(market, 'indicators', None) else 0,
        "macd_signal": float(market.indicators.macd_signal or 0) if getattr(market, 'indicators', None) else 0,
        "atr14": float(market.indicators.atr14) if getattr(market, 'indicators', None) else 0,
        "htf_trend": market.trend_context.htf_trend if getattr(market, 'trend_context', None) else "",
        "market_structure": market.trend_context.market_structure if getattr(market, 'trend_context', None) else "",
        "momentum": market.trend_context.momentum if getattr(market, 'trend_context', None) else "",
    }


def score_market_with_model(market: MarketRequest, decision: TradeDecision) -> dict:
    settings = get_settings()
    model, meta = load_current_model()
    if not model or not meta:
        return {"model_loaded": False, "score": None, "allow": True, "reason": "no_model_loaded"}

    row = build_model_feature_row(market, decision)
    feature_cols = meta.get("numeric_features", []) + meta.get("categorical_features", [])
    X = pd.DataFrame([{k: row.get(k) for k in feature_cols}])

    score = 0.5
    try:
        if hasattr(model, "predict_proba"):
            score = float(model.predict_proba(X)[0][1])
        else:
            score = float(model.predict(X)[0])
    except Exception:
        return {"model_loaded": True, "score": None, "allow": True, "reason": "model_score_error", "model_type": meta.get("model_type", "unknown")}

    allow = score >= float(settings.model_score_threshold)
    return {
        "model_loaded": True,
        "score": round(score, 4),
        "allow": allow,
        "reason": "model_score_passed" if allow else "model_score_blocked",
        "model_type": meta.get("model_type", "unknown"),
    }
