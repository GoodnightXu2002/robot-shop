from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: float


class InMemoryRateLimiter:
    def __init__(self, clock=None):
        self._clock = clock or monotonic
        self._requests = {}

    def check(self, key, window_seconds, max_requests):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than 0")

        now = self._clock()
        self.cleanup(window_seconds, now)

        timestamps = self._requests.setdefault(str(key), [])
        cutoff = now - window_seconds
        timestamps[:] = [timestamp for timestamp in timestamps if timestamp > cutoff]

        if len(timestamps) >= max_requests:
            retry_after = max(0.0, window_seconds - (now - timestamps[0]))
            return RateLimitResult(False, 0, retry_after)

        timestamps.append(now)
        return RateLimitResult(True, max_requests - len(timestamps), 0.0)

    def cleanup(self, window_seconds, now=None):
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")

        current_time = self._clock() if now is None else now
        cutoff = current_time - window_seconds
        expired_keys = []
        for key, timestamps in self._requests.items():
            timestamps[:] = [timestamp for timestamp in timestamps if timestamp > cutoff]
            if not timestamps:
                expired_keys.append(key)

        for key in expired_keys:
            del self._requests[key]

    def key_count(self):
        return len(self._requests)
