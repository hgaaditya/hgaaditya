"""Typed configuration (pydantic) with YAML loading and safe defaults.

All tunable behaviour — risk limits, costs, strategy params, which broker — is
declared here so a run is fully described by one config object that gets logged
and audited alongside its trades.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    starting_capital: float = 100_000.0
    risk_per_trade: float = 0.005          # 0.5% of equity risked per trade
    max_positions: int = 3                 # concurrent open positions
    max_exposure: float = 1.0              # gross exposure as fraction of equity
    daily_max_loss: float = 0.02           # halt for the day at -2% equity
    daily_profit_target: float | None = None  # optional: stop when reached
    per_trade_max_qty: int = 100_000       # absolute sanity cap


class CostConfig(BaseModel):
    """Indian intraday equity cost model (fractions of turnover unless noted)."""

    brokerage_pct: float = 0.0003          # 0.03% ...
    brokerage_cap: float = 20.0            # ...capped at Rs.20 per leg
    stt_sell_pct: float = 0.00025          # STT on sell side only (intraday)
    exchange_txn_pct: float = 0.0000297    # NSE txn charge
    sebi_pct: float = 0.000001
    stamp_buy_pct: float = 0.00003         # stamp duty on buy side only
    gst_pct: float = 0.18                  # on (brokerage + txn + sebi)
    slippage_pct: float = 0.0002           # modelled slippage per fill


class StrategyConfig(BaseModel):
    name: str
    enabled: bool = True
    params: dict = Field(default_factory=dict)


class SentimentConfig(BaseModel):
    provider: str = "rules"                # "rules" | "llm" | "none"
    weight: float = 0.3                    # how much bias tilts sizing/gating


class MarketConfig(BaseModel):
    exchange: str = "NSE"
    symbols: list[str] = Field(default_factory=lambda: ["RELIANCE"])
    timeframe: str = "1m"


class AppConfig(BaseModel):
    mode: str = "paper"                    # paper | backtest | live
    market: MarketConfig = Field(default_factory=MarketConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    costs: CostConfig = Field(default_factory=CostConfig)
    sentiment: SentimentConfig = Field(default_factory=SentimentConfig)
    strategies: list[StrategyConfig] = Field(
        default_factory=lambda: [
            StrategyConfig(name="trend", params={"ema_fast": 9, "ema_slow": 21, "adx_min": 20}),
            StrategyConfig(name="mean_reversion", params={"bb_period": 20, "rsi_period": 14}),
        ]
    )
    data_dir: str = "data"
    runs_dir: str = "runs"

    @classmethod
    def load(cls, path: str | Path | None = None) -> AppConfig:
        if path is None:
            return cls()
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return cls.model_validate(raw)
