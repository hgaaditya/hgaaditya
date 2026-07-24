import pandas as pd
import pytest

from tradingbot.config import AppConfig
from tradingbot.data.synthetic import generate_days, generate_intraday


@pytest.fixture
def cfg(tmp_path) -> AppConfig:
    c = AppConfig()
    c.runs_dir = str(tmp_path / "runs")
    c.data_dir = str(tmp_path / "data")
    return c


@pytest.fixture
def intraday_df() -> pd.DataFrame:
    return generate_intraday(seed=7)


@pytest.fixture
def multiday_df() -> pd.DataFrame:
    return generate_days(days=5, seed=7)
