"""User-based rate limiting for Discord commands."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class RateLimitInfo:
    """Rate limit information for a user."""
    
    def __init__(self, max_requests: int, window_hours: int):
        """
        Initialize rate limit info.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_hours: Time window in hours
        """
        self.max_requests = max_requests
        self.window_hours = window_hours
        self.requests: list[datetime] = []
        self.lock = asyncio.Lock()
    
    def is_limited(self) -> bool:
        """
        Check if user is currently rate limited.
        
        Returns:
            True if user is rate limited, False otherwise
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self.window_hours)
        
        # Remove old requests
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]
        
        return len(self.requests) >= self.max_requests
    
    def add_request(self) -> None:
        """Add a new request timestamp."""
        self.requests.append(datetime.utcnow())
    
    def time_until_reset(self) -> Optional[float]:
        """
        Get seconds until rate limit resets.
        
        Returns:
            Seconds until reset, None if not limited
        """
        if not self.requests:
            return None
        
        oldest_request = min(self.requests)
        reset_time = oldest_request + timedelta(hours=self.window_hours)
        now = datetime.utcnow()
        
        if reset_time > now:
            return (reset_time - now).total_seconds()
        
        return None

class RateLimiter:
    """
    User-based rate limiter with async support.
    
    Tracks requests per user within a time window and enforces limits.
    """
    
    def __init__(self, max_requests: int = 10, window_hours: int = 1, cleanup_interval: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per user in the window
            window_hours: Time window in hours
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_requests = max_requests
        self.window_hours = window_hours
        self.users: Dict[str, RateLimitInfo] = {}
        self.cleanup_interval = cleanup_interval
        self._global_lock = asyncio.Lock()  # Global lock for user creation
        
        # Cleanup task will be started when needed
        self._cleanup_task = None
        
        logger.info(f"Rate limiter initialized: {max_requests} requests per {window_hours} hours")
    
    async def check_user(self, user_id: str) -> bool:
        """
        Check if user can make a request with atomic check-and-add.
        
        Args:
            user_id: Discord user ID as string
            
        Returns:
            True if user can make request, False if rate limited
        """
        # Start cleanup task if not already running
        if self._cleanup_task is None:
            async with self._global_lock:
                if self._cleanup_task is None:  # Double-check locking pattern
                    self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        # Get or create user rate limit info with global lock
        if user_id not in self.users:
            async with self._global_lock:
                if user_id not in self.users:  # Double-check locking pattern
                    self.users[user_id] = RateLimitInfo(self.max_requests, self.window_hours)
        
        user_info = self.users[user_id]
        
        # ATOMIC: check and add in single lock to prevent race conditions
        async with user_info.lock:
            if user_info.is_limited():
                logger.warning(f"Rate limit exceeded for user {user_id} ({len(user_info.requests)}/{self.max_requests})")
                return False
            
            # Add request atomically after check
            user_info.add_request()
            logger.debug(f"Request allowed for user {user_id} ({len(user_info.requests)}/{self.max_requests})")
            return True
    
    async def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get rate limit status for a user.
        
        Args:
            user_id: Discord user ID as string
            
        Returns:
            Dictionary with rate limit status
        """
        if user_id not in self.users:
            return {
                'limited': False,
                'requests_used': 0,
                'requests_remaining': self.max_requests,
                'reset_time': None
            }
        
        user_info = self.users[user_id]
        
        async with user_info.lock:
            is_limited = user_info.is_limited()
            requests_used = len(user_info.requests)
            
            return {
                'limited': is_limited,
                'requests_used': requests_used,
                'requests_remaining': max(0, self.max_requests - requests_used),
                'reset_time': user_info.time_until_reset()
            }
    
    async def reset_user(self, user_id: str) -> bool:
        """
        Reset rate limit for a specific user.
        
        Args:
            user_id: Discord user ID as string
            
        Returns:
            True if user was reset, False if user not found
        """
        if user_id in self.users:
            async with self.users[user_id].lock:
                self.users[user_id].requests.clear()
                logger.info(f"Rate limit reset for user {user_id}")
                return True
        
        return False
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old user data to prevent memory leaks."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_users()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    async def _cleanup_old_users(self) -> None:
        """Remove users with no recent requests."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self.window_hours * 2)  # Keep extra buffer
        
        users_to_remove = []
        
        for user_id, user_info in self.users.items():
            async with user_info.lock:
                # Remove old requests first
                user_info.requests = [req_time for req_time in user_info.requests if req_time > cutoff]
                
                # Mark user for removal if no recent requests
                if not user_info.requests:
                    users_to_remove.append(user_id)
        
        # Remove inactive users
        for user_id in users_to_remove:
            del self.users[user_id]
        
        if users_to_remove:
            logger.info(f"Cleaned up {len(users_to_remove)} inactive users")
    
    async def shutdown(self) -> None:
        """Clean shutdown of rate limiter."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rate limiter shutdown complete")

# Global rate limiter instance (will be initialized by bot)
default_rate_limiter: Optional[RateLimiter] = None