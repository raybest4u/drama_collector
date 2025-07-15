# utils/cache_manager.py
import json
import logging
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import asyncio
from dataclasses import asdict, dataclass

# Optional redis import with fallback
try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None
    logging.getLogger(__name__).warning("aioredis not available, cache will be disabled")

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """缓存配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 3600  # 默认1小时过期
    max_retries: int = 3
    retry_delay: float = 1.0
    

class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client = None
        self.is_connected = False
        
        # 缓存键前缀
        self.key_prefixes = {
            'drama': 'drama:',
            'character': 'char:',
            'plot': 'plot:',
            'themes': 'themes:',
            'validation': 'valid:',
            'processing': 'proc:',
            'collection': 'collect:'
        }
        
        logger.info("缓存管理器初始化完成")
    
    async def connect(self):
        """连接到Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis不可用，缓存功能将被禁用")
            self.is_connected = False
            return
            
        try:
            redis_url = f"redis://{self.config.host}:{self.config.port}/{self.config.db}"
            if self.config.password:
                redis_url = f"redis://:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.db}"
            
            self.redis_client = await aioredis.from_url(
                redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # 测试连接
            await self.redis_client.ping()
            self.is_connected = True
            
            logger.info(f"Redis连接成功: {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("Redis连接已关闭")
    
    async def set(self, key: str, value: Any, ttl: int = None, 
                 category: str = 'drama') -> bool:
        """设置缓存"""
        if not self.is_connected:
            logger.warning("Redis未连接，跳过缓存设置")
            return False
        
        try:
            full_key = self._build_key(key, category)
            serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            
            ttl = ttl or self.config.default_ttl
            
            await self.redis_client.setex(full_key, ttl, serialized_value)
            
            logger.debug(f"缓存设置成功: {full_key}")
            return True
            
        except Exception as e:
            logger.error(f"缓存设置失败: {key}, 错误: {e}")
            return False
    
    async def get(self, key: str, category: str = 'drama') -> Optional[Any]:
        """获取缓存"""
        if not self.is_connected:
            logger.warning("Redis未连接，跳过缓存获取")
            return None
        
        try:
            full_key = self._build_key(key, category)
            cached_value = await self.redis_client.get(full_key)
            
            if cached_value is None:
                logger.debug(f"缓存未命中: {full_key}")
                return None
            
            logger.debug(f"缓存命中: {full_key}")
            return json.loads(cached_value)
            
        except Exception as e:
            logger.error(f"缓存获取失败: {key}, 错误: {e}")
            return None
    
    async def delete(self, key: str, category: str = 'drama') -> bool:
        """删除缓存"""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._build_key(key, category)
            result = await self.redis_client.delete(full_key)
            
            logger.debug(f"缓存删除: {full_key}, 结果: {result}")
            return result > 0
            
        except Exception as e:
            logger.error(f"缓存删除失败: {key}, 错误: {e}")
            return False
    
    async def exists(self, key: str, category: str = 'drama') -> bool:
        """检查缓存是否存在"""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._build_key(key, category)
            result = await self.redis_client.exists(full_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"缓存检查失败: {key}, 错误: {e}")
            return False
    
    async def get_multiple(self, keys: List[str], 
                          category: str = 'drama') -> Dict[str, Any]:
        """批量获取缓存"""
        if not self.is_connected or not keys:
            return {}
        
        try:
            full_keys = [self._build_key(key, category) for key in keys]
            cached_values = await self.redis_client.mget(full_keys)
            
            results = {}
            for i, (key, cached_value) in enumerate(zip(keys, cached_values)):
                if cached_value is not None:
                    try:
                        results[key] = json.loads(cached_value)
                    except json.JSONDecodeError:
                        logger.warning(f"缓存值JSON解析失败: {key}")
            
            logger.debug(f"批量缓存获取: {len(results)}/{len(keys)} 命中")
            return results
            
        except Exception as e:
            logger.error(f"批量缓存获取失败: {e}")
            return {}
    
    async def set_multiple(self, data: Dict[str, Any], ttl: int = None,
                          category: str = 'drama') -> int:
        """批量设置缓存"""
        if not self.is_connected or not data:
            return 0
        
        success_count = 0
        ttl = ttl or self.config.default_ttl
        
        try:
            # 使用pipeline提高性能
            pipe = self.redis_client.pipeline()
            
            for key, value in data.items():
                full_key = self._build_key(key, category)
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
                pipe.setex(full_key, ttl, serialized_value)
            
            await pipe.execute()
            success_count = len(data)
            
            logger.debug(f"批量缓存设置成功: {success_count} 个键")
            
        except Exception as e:
            logger.error(f"批量缓存设置失败: {e}")
        
        return success_count
    
    async def invalidate_pattern(self, pattern: str, category: str = 'drama') -> int:
        """根据模式删除缓存"""
        if not self.is_connected:
            return 0
        
        try:
            full_pattern = self._build_key(pattern, category)
            keys = await self.redis_client.keys(full_pattern)
            
            if not keys:
                return 0
            
            deleted_count = await self.redis_client.delete(*keys)
            
            logger.info(f"模式删除缓存: {pattern}, 删除数量: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"模式删除缓存失败: {pattern}, 错误: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.is_connected:
            return {}
        
        try:
            info = await self.redis_client.info()
            
            stats = {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'evicted_keys': info.get('evicted_keys', 0)
            }
            
            # 计算命中率
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            total_requests = hits + misses
            
            stats['hit_rate'] = (hits / total_requests * 100) if total_requests > 0 else 0
            
            # 获取各类别的键数量
            category_counts = {}
            for category, prefix in self.key_prefixes.items():
                keys = await self.redis_client.keys(f"{prefix}*")
                category_counts[category] = len(keys)
            
            stats['category_counts'] = category_counts
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def _build_key(self, key: str, category: str = 'drama') -> str:
        """构建完整的缓存键"""
        prefix = self.key_prefixes.get(category, 'general:')
        return f"{prefix}{key}"
    
    def _generate_cache_key(self, data: Any) -> str:
        """为数据生成缓存键"""
        if isinstance(data, dict):
            # 使用ID或标题生成键
            if 'id' in data:
                return str(data['id'])
            elif 'title' in data:
                return hashlib.md5(data['title'].encode('utf-8')).hexdigest()
        
        # 使用数据的哈希值
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()


class CachedDataProcessor:
    """带缓存的数据处理器"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        
    async def get_or_process_drama(self, drama_data: Dict[str, Any],
                                  processor_func: callable,
                                  cache_ttl: int = 3600) -> Dict[str, Any]:
        """获取或处理剧目数据（带缓存）"""
        
        # 生成缓存键
        cache_key = self._generate_drama_cache_key(drama_data)
        
        # 尝试从缓存获取
        cached_result = await self.cache.get(cache_key, 'processing')
        
        if cached_result is not None:
            logger.debug(f"使用缓存结果: {cache_key}")
            return cached_result
        
        # 缓存未命中，执行处理
        logger.debug(f"缓存未命中，执行处理: {cache_key}")
        
        try:
            processed_result = await processor_func(drama_data)
            
            # 缓存结果
            await self.cache.set(cache_key, processed_result, cache_ttl, 'processing')
            
            return processed_result
            
        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            return drama_data  # 返回原始数据
    
    async def cache_validation_result(self, drama_data: Dict[str, Any],
                                     validation_result: Dict[str, Any],
                                     cache_ttl: int = 1800) -> None:
        """缓存验证结果"""
        cache_key = self._generate_validation_cache_key(drama_data)
        await self.cache.set(cache_key, validation_result, cache_ttl, 'validation')
    
    async def get_cached_validation(self, drama_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取缓存的验证结果"""
        cache_key = self._generate_validation_cache_key(drama_data)
        return await self.cache.get(cache_key, 'validation')
    
    async def cache_collection_result(self, source: str, query_params: Dict[str, Any],
                                     results: List[Dict[str, Any]],
                                     cache_ttl: int = 1800) -> None:
        """缓存数据收集结果"""
        cache_key = self._generate_collection_cache_key(source, query_params)
        
        cache_data = {
            'results': results,
            'timestamp': datetime.utcnow().isoformat(),
            'source': source,
            'query_params': query_params
        }
        
        await self.cache.set(cache_key, cache_data, cache_ttl, 'collection')
    
    async def get_cached_collection(self, source: str, 
                                   query_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的收集结果"""
        cache_key = self._generate_collection_cache_key(source, query_params)
        cached_data = await self.cache.get(cache_key, 'collection')
        
        if cached_data:
            return cached_data.get('results', [])
        
        return None
    
    def _generate_drama_cache_key(self, drama_data: Dict[str, Any]) -> str:
        """生成剧目缓存键"""
        if 'id' in drama_data:
            return f"drama_{drama_data['id']}"
        elif 'title' in drama_data and 'year' in drama_data:
            title_hash = hashlib.md5(drama_data['title'].encode('utf-8')).hexdigest()[:8]
            return f"drama_{title_hash}_{drama_data['year']}"
        else:
            # 使用数据哈希
            data_str = json.dumps(drama_data, sort_keys=True, default=str)
            return f"drama_{hashlib.md5(data_str.encode('utf-8')).hexdigest()[:12]}"
    
    def _generate_validation_cache_key(self, drama_data: Dict[str, Any]) -> str:
        """生成验证缓存键"""
        base_key = self._generate_drama_cache_key(drama_data)
        return f"validation_{base_key}"
    
    def _generate_collection_cache_key(self, source: str, 
                                      query_params: Dict[str, Any]) -> str:
        """生成收集缓存键"""
        params_str = json.dumps(query_params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode('utf-8')).hexdigest()[:8]
        return f"collection_{source}_{params_hash}"


# 全局缓存管理器实例
cache_manager = None


async def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global cache_manager
    
    if cache_manager is None:
        cache_manager = CacheManager()
        try:
            await cache_manager.connect()
        except Exception as e:
            logger.warning(f"Redis连接失败，将在无缓存模式下运行: {e}")
    
    return cache_manager


async def cleanup_cache_manager():
    """清理缓存管理器"""
    global cache_manager
    
    if cache_manager:
        await cache_manager.disconnect()
        cache_manager = None