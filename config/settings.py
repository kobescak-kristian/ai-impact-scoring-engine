from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    use_simulation_fallback: bool = True
    database_url: str = "sqlite:///./impact_engine.db"
    log_level: str = "INFO"

    # Impact cost constants — used by evaluator
    false_positive_cost_multiplier: float = 0.15   # 15% of lead value = sales cost of chasing bad lead
    delayed_conversion_penalty: float = 0.10        # 10% of lead value = cost of delay
    missed_opportunity_multiplier: float = 1.0      # full lead value lost if archived + later converted

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
