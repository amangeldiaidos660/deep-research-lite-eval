from __future__ import annotations

import threading
import time


class RequestRateLimiter:
    """Simple shared request pacer for provider-facing calls."""

    def __init__(self, requests_per_minute: float | None = None) -> None:
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0
        self._min_interval = 0.0
        if requests_per_minute and requests_per_minute > 0:
            self._min_interval = 60.0 / requests_per_minute

    def wait_turn(self) -> None:
        if self._min_interval <= 0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                if now >= self._next_allowed_at:
                    self._next_allowed_at = now + self._min_interval
                    return
                sleep_for = self._next_allowed_at - now
            time.sleep(sleep_for)

    def observe_rate_limit(self, cooldown_seconds: float) -> None:
        if cooldown_seconds <= 0:
            return
        with self._lock:
            self._next_allowed_at = max(
                self._next_allowed_at,
                time.monotonic() + cooldown_seconds,
            )
