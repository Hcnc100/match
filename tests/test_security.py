from unittest import TestCase
from unittest.mock import patch

from app.core.security import SlidingWindowRateLimiter


class SlidingWindowRateLimiterTests(TestCase):
    def test_rejects_requests_over_the_limit_and_returns_retry_after(self):
        limiter = SlidingWindowRateLimiter(requests=2, window_seconds=60)

        with patch("app.core.security.time.monotonic", side_effect=[100, 101, 102]):
            self.assertEqual(limiter.check("client"), (True, 0))
            self.assertEqual(limiter.check("client"), (True, 0))
            allowed, retry_after = limiter.check("client")

        self.assertFalse(allowed)
        self.assertEqual(retry_after, 59)

    def test_keeps_clients_separate(self):
        limiter = SlidingWindowRateLimiter(requests=1, window_seconds=60)

        self.assertEqual(limiter.check("client-a"), (True, 0))
        self.assertEqual(limiter.check("client-b"), (True, 0))
