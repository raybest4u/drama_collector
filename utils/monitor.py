# utils/monitor.py
import logging
import time
from functools import wraps

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logging.info(f"{func.__name__} 执行成功，耗时: {duration:.2f}秒")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"{func.__name__} 执行失败，耗时: {duration:.2f}秒，错误: {e}")
            raise
    return wrapper
