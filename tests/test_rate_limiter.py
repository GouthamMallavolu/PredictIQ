"""
Unit tests for rate limiter (backpressure handling)
"""

import pytest
import time
from pipeline.ingest import RateLimiter


def test_rate_limiter_basic():
    """Test basic rate limiting"""
    limiter = RateLimiter(max_calls=3, time_window=1.0)
    
    # Should allow first 3 calls
    assert limiter.acquire(blocking=False) == True
    assert limiter.acquire(blocking=False) == True
    assert limiter.acquire(blocking=False) == True
    
    # Should block 4th call
    assert limiter.acquire(blocking=False) == False


def test_rate_limiter_window_reset():
    """Test rate limiter resets after time window"""
    limiter = RateLimiter(max_calls=2, time_window=0.5)
    
    # Use up the limit
    assert limiter.acquire(blocking=False) == True
    assert limiter.acquire(blocking=False) == True
    assert limiter.acquire(blocking=False) == False
    
    # Wait for window to reset
    time.sleep(0.6)
    
    # Should allow calls again
    assert limiter.acquire(blocking=False) == True


def test_rate_limiter_blocking():
    """Test blocking mode"""
    limiter = RateLimiter(max_calls=1, time_window=0.5)
    
    # First call succeeds
    assert limiter.acquire(blocking=False) == True
    
    # Second call blocks and waits
    start = time.time()
    assert limiter.acquire(blocking=True, timeout=1.0) == True
    elapsed = time.time() - start
    
    # Should have waited approximately the time window
    assert elapsed >= 0.4  # Allow some tolerance


def test_rate_limiter_timeout():
    """Test timeout in blocking mode"""
    limiter = RateLimiter(max_calls=1, time_window=5.0)
    
    # Use up the limit
    assert limiter.acquire(blocking=False) == True
    
    # Try to acquire with short timeout
    start = time.time()
    assert limiter.acquire(blocking=True, timeout=0.5) == False
    elapsed = time.time() - start
    
    # Should timeout after approximately 0.5 seconds
    assert 0.4 <= elapsed <= 0.7


def test_rate_limiter_wait_time():
    """Test getting estimated wait time"""
    limiter = RateLimiter(max_calls=2, time_window=1.0)
    
    # No wait initially
    assert limiter.get_wait_time() == 0.0
    
    # Use up limit
    limiter.acquire(blocking=False)
    limiter.acquire(blocking=False)
    
    # Should have wait time
    wait_time = limiter.get_wait_time()
    assert wait_time > 0.0
    assert wait_time <= 1.0


def test_rate_limiter_reset():
    """Test manual reset"""
    limiter = RateLimiter(max_calls=2, time_window=1.0)
    
    # Use up limit
    limiter.acquire(blocking=False)
    limiter.acquire(blocking=False)
    assert limiter.acquire(blocking=False) == False
    
    # Reset and try again
    limiter.reset()
    assert limiter.acquire(blocking=False) == True


def test_rate_limiter_concurrent():
    """Test rate limiter with multiple concurrent requests"""
    limiter = RateLimiter(max_calls=5, time_window=1.0)
    
    # Simulate burst of requests
    successful = 0
    failed = 0
    
    for i in range(10):
        if limiter.acquire(blocking=False):
            successful += 1
        else:
            failed += 1
    
    assert successful == 5
    assert failed == 5
