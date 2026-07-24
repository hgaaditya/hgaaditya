"""Market calendar and clock for the NSE (default), with hooks for other venues.

Times are IST (Asia/Kolkata). This is intentionally small: enough to gate the
intraday session and force square-off, without pulling a full exchange-calendar
dependency. Extend `HOLIDAYS` or swap `MarketCalendar` for other markets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# Regular NSE equity session.
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)
# Intraday (MIS) positions must be squared off before the broker auto-square-off.
SQUARE_OFF = time(15, 15)

# Minimal holiday set; extend for production. (Weekends handled separately.)
HOLIDAYS: set[date] = set()


@dataclass
class MarketCalendar:
    session_open: time = SESSION_OPEN
    session_close: time = SESSION_CLOSE
    square_off: time = SQUARE_OFF
    tz: timezone = IST

    def is_trading_day(self, d: date) -> bool:
        return d.weekday() < 5 and d not in HOLIDAYS

    def is_open(self, ts: datetime) -> bool:
        ts = self._as_ist(ts)
        return self.is_trading_day(ts.date()) and self.session_open <= ts.time() < self.session_close

    def is_square_off(self, ts: datetime) -> bool:
        """True once we've reached forced intraday square-off time."""
        ts = self._as_ist(ts)
        return ts.time() >= self.square_off

    def _as_ist(self, ts: datetime) -> datetime:
        if ts.tzinfo is None:
            return ts.replace(tzinfo=self.tz)
        return ts.astimezone(self.tz)


def now_ist() -> datetime:
    return datetime.now(IST)
