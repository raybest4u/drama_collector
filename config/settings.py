# config/settings.py
import os
from dataclasses import dataclass

@dataclass
class Settings:
    # 数据库配置
    MONGODB_URL: str = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # API配置
    DOUBAN_API_KEY: str = os.getenv('DOUBAN_API_KEY', '0df993c66c0c636e29ecbb5344252a4a')# 0b2bdeda43b5688921839c8ecb20399b 054022eaeae0b00e0fc068c0c0a2102a
    TMDB_API_KEY: str = os.getenv('TMDB_API_KEY', '')
    
    # 爬虫配置
    REQUEST_DELAY: float = 1.0
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30
    
    # 日志配置
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = 'drama_collector.log'

settings = Settings()
