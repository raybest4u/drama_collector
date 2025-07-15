import asyncio
from typing import Optional


class RateLimiter:
    """异步速率限制器"""
    
    def __init__(self, rate: int, per: float = 1.0):
        """
        初始化速率限制器
        
        Args:
            rate: 允许的请求数量
            per: 时间窗口（秒）
        """
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """获取令牌（阻塞直到可用）"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # 计算需要添加的令牌数
            elapsed = now - self.last_update
            tokens_to_add = elapsed * (self.rate / self.per)
            
            # 更新令牌数（不超过最大值）
            self.tokens = min(self.rate, self.tokens + tokens_to_add)
            self.last_update = now
            
            # 如果没有可用令牌，等待
            if self.tokens < 1:
                sleep_time = (1 - self.tokens) * (self.per / self.rate)
                await asyncio.sleep(sleep_time)
                self.tokens = 0
            else:
                self.tokens -= 1
    
    def can_acquire(self) -> bool:
        """检查是否可以立即获取令牌（非阻塞）"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_update
        tokens_to_add = elapsed * (self.rate / self.per)
        current_tokens = min(self.rate, self.tokens + tokens_to_add)
        return current_tokens >= 1