# collectors/base_collector.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio
import aiohttp
from utils.rate_limiter import RateLimiter

class BaseCollector(ABC):
    def __init__(self, rate_limit: int = 10):
        self.session = None
        self.rate_limiter = RateLimiter(rate_limit)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def collect_drama_list(self, **kwargs) -> List[Dict]:
        """收集剧目列表"""
        pass
    
    @abstractmethod
    async def collect_drama_detail(self, drama_id: str) -> Dict:
        """收集单个剧目详情"""
        pass
    
    async def safe_request(self, url: str, **kwargs) -> Dict:
        """安全的HTTP请求"""
        await self.rate_limiter.acquire()
        try:
            async with self.session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            print(f"请求失败: {url}, 错误: {e}")
            return {}
