import asyncio
import random
from typing import Union


async def delay(seconds: Union[int, float]) -> None:
    """
    Creates an async delay for the specified number of seconds
    
    Args:
        seconds: Number of seconds to delay
    """
    await asyncio.sleep(seconds)


async def random_delay(min_seconds: Union[int, float], max_seconds: Union[int, float]) -> None:
    """
    Creates a random async delay between min and max seconds
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay_time = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay_time)


async def human_delay(base_seconds: Union[int, float], variation_percent: float = 25.0) -> None:
    """
    Creates a human-like delay with random variation
    
    Args:
        base_seconds: Base delay in seconds
        variation_percent: Percentage variation (0-100)
    """
    variation = (base_seconds * variation_percent) / 100
    min_delay = max(0.1, base_seconds - variation)  # Minimum 0.1 seconds
    max_delay = base_seconds + variation
    await random_delay(min_delay, max_delay)


class RateLimiter:
    """Simple rate limiter for controlling request frequency"""
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits"""
        now = asyncio.get_event_loop().time()
        
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        # If we're at the limit, wait until we can make another request
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0]) + 0.1  # Small buffer
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Record this request
        self.requests.append(now)
