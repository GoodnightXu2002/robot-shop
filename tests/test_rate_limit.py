import pytest

from services.rate_limit import InMemoryRateLimiter


class FakeClock:
    def __init__(self, current=0.0):
        self.current = current

    def __call__(self):
        return self.current

    def advance(self, seconds):
        self.current += seconds


def test_rate_limit_allows_requests_within_limit():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    first = limiter.check("user:1", window_seconds=60, max_requests=2)
    second = limiter.check("user:1", window_seconds=60, max_requests=2)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0


def test_rate_limit_rejects_requests_over_limit():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    assert limiter.check("ip:127.0.0.1", 60, 2).allowed is True
    assert limiter.check("ip:127.0.0.1", 60, 2).allowed is True
    rejected = limiter.check("ip:127.0.0.1", 60, 2)

    assert rejected.allowed is False
    assert rejected.remaining == 0
    assert rejected.retry_after == pytest.approx(60.0)


def test_rate_limit_keys_are_independent():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    assert limiter.check("user:1", 60, 1).allowed is True
    assert limiter.check("user:1", 60, 1).allowed is False

    other_key = limiter.check("user:2", 60, 1)

    assert other_key.allowed is True


def test_rate_limit_allows_again_after_window_expires():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    assert limiter.check("user:1", 10, 1).allowed is True
    assert limiter.check("user:1", 10, 1).allowed is False

    clock.advance(10.1)
    after_window = limiter.check("user:1", 10, 1)

    assert after_window.allowed is True
    assert after_window.remaining == 0


def test_rate_limit_cleanup_removes_expired_keys():
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)

    limiter.check("user:1", 10, 2)
    limiter.check("user:2", 10, 2)
    assert limiter.key_count() == 2

    clock.advance(11)
    limiter.cleanup(window_seconds=10)

    assert limiter.key_count() == 0
