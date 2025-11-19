"""
Rate Limiter for API calls

Implements token bucket algorithm for rate limiting with backpressure handling.
"""

import time
import threading
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Provides backpressure by limiting requests per time window.
    """
    
    def __init__(self, max_calls: int, time_window: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds (default 60 seconds = 1 minute)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = threading.Lock()
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make an API call.
        
        Args:
            blocking: If True, wait until permission is granted
            timeout: Maximum time to wait (None = wait forever)
        
        Returns:
            True if permission granted, False if rate limit exceeded and not blocking
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                now = time.time()
                
                # Remove calls outside the time window
                self.calls = [call_time for call_time in self.calls 
                             if now - call_time < self.time_window]
                
                # Check if we can make another call
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return True
                
                # Calculate wait time until next available slot
                if self.calls:
                    oldest_call = min(self.calls)
                    wait_time = self.time_window - (now - oldest_call)
                else:
                    wait_time = 0
            
            # If not blocking, return False
            if not blocking:
                return False
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False
                # Adjust wait time to not exceed timeout
                wait_time = min(wait_time, timeout - elapsed)
            
            # Wait before retrying
            if wait_time > 0:
                time.sleep(min(wait_time + 0.1, 1.0))  # Add small buffer, max 1 second
            else:
                time.sleep(0.1)  # Small delay to avoid busy waiting
    
    def get_wait_time(self) -> float:
        """
        Get estimated wait time until next call is allowed.
        
        Returns:
            Wait time in seconds (0 if call can be made immediately)
        """
        with self.lock:
            now = time.time()
            
            # Remove old calls
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.time_window]
            
            # If under limit, no wait
            if len(self.calls) < self.max_calls:
                return 0.0
            
            # Calculate wait time
            if self.calls:
                oldest_call = min(self.calls)
                return max(0.0, self.time_window - (now - oldest_call))
            return 0.0
    
    def reset(self):
        """Reset the rate limiter (clear all recorded calls)"""
        with self.lock:
            self.calls = []
