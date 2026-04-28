from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "mt5-ai-bot"
    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    gemini_api_key: str = "replace_me"
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    min_confidence: int = 72
    min_risk_reward: float = 1.7
    max_spread_points: float = 30.0
    max_trades_per_day: int = 3
    max_open_positions_per_symbol: int = 1
    cooldown_minutes: int = 30
    max_daily_loss: float = 100.0
    model_score_threshold: float = 0.5

    allow_live_trading: bool = False
    enable_vision: bool = False
    emergency_stop: bool = True
    default_session_allowlist: str = "London,NewYork,Overlap"

    decision_log_path: str = "logs/ai_decisions.jsonl"
    event_log_path: str = "logs/trade_events.jsonl"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_sessions(self) -> list[str]:
        return [s.strip() for s in self.default_session_allowlist.split(",") if s.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
