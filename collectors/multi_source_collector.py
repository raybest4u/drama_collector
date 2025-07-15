# collectors/multi_source_collector.py
from typing import List, Dict, Optional
from .base_collector import BaseCollector
from .douban_collector import DoubanCollector
from .mydramalist_collector import MyDramaListCollector
from .mock_collector import MockCollector
import asyncio
import logging

logger = logging.getLogger(__name__)


class MultiSourceCollector(BaseCollector):
    """多数据源聚合收集器"""
    
    def __init__(self, enable_sources: List[str] = None):
        super().__init__(rate_limit=5)
        
        # 默认启用的数据源
        if enable_sources is None:
            enable_sources = ['mock', 'douban', 'mydramalist']
        
        self.enabled_sources = enable_sources
        self.collectors = {}
        self.source_priority = ['douban', 'mydramalist', 'mock']  # 数据源优先级
        
    async def __aenter__(self):
        await super().__aenter__()
        
        # 初始化各个收集器
        if 'douban' in self.enabled_sources:
            self.collectors['douban'] = DoubanCollector()
            await self.collectors['douban'].__aenter__()
            
        if 'mydramalist' in self.enabled_sources:
            self.collectors['mydramalist'] = MyDramaListCollector()
            await self.collectors['mydramalist'].__aenter__()
            
        if 'mock' in self.enabled_sources:
            self.collectors['mock'] = MockCollector()
            await self.collectors['mock'].__aenter__()
            
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 关闭所有收集器
        for collector in self.collectors.values():
            await collector.__aexit__(exc_type, exc_val, exc_tb)
        
        await super().__aexit__(exc_type, exc_val, exc_tb)
    
    async def collect_drama_list(self, count: int = 20, **kwargs) -> List[Dict]:
        """从多个数据源收集剧目列表"""
        all_dramas = []
        source_results = {}
        
        # 并行从各数据源收集
        tasks = []
        for source_name, collector in self.collectors.items():
            task = self._collect_from_source(source_name, collector, count // len(self.collectors), **kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results):
            source_name = list(self.collectors.keys())[i]
            
            if isinstance(result, Exception):
                logger.error(f"数据源 {source_name} 收集失败: {result}")
                source_results[source_name] = []
            else:
                source_results[source_name] = result
                logger.info(f"数据源 {source_name} 收集到 {len(result)} 部剧目")
        
        # 按优先级合并结果
        for source in self.source_priority:
            if source in source_results:
                all_dramas.extend(source_results[source])
        
        # 去重（基于标题和年份）
        unique_dramas = self._deduplicate_dramas(all_dramas)
        
        return unique_dramas[:count]
    
    async def collect_drama_detail(self, drama_id: str, preferred_source: str = None) -> Dict:
        """收集剧目详情，支持指定偏好数据源"""
        
        # 如果指定了偏好数据源且可用，优先使用
        if preferred_source and preferred_source in self.collectors:
            try:
                detail = await self.collectors[preferred_source].collect_drama_detail(drama_id)
                if detail:
                    detail['data_source'] = preferred_source
                    return detail
            except Exception as e:
                logger.warning(f"偏好数据源 {preferred_source} 获取详情失败: {e}")
        
        # 按优先级尝试各数据源
        for source in self.source_priority:
            if source in self.collectors:
                try:
                    detail = await self.collectors[source].collect_drama_detail(drama_id)
                    if detail:
                        detail['data_source'] = source
                        return detail
                except Exception as e:
                    logger.warning(f"数据源 {source} 获取详情失败: {e}")
                    continue
        
        return {}
    
    async def _collect_from_source(self, source_name: str, collector: BaseCollector, count: int, **kwargs) -> List[Dict]:
        """从指定数据源收集数据"""
        try:
            dramas = await collector.collect_drama_list(count=count, **kwargs)
            
            # 为每个剧目添加数据源标识
            for drama in dramas:
                drama['data_source'] = source_name
                drama['collection_timestamp'] = asyncio.get_event_loop().time()
            
            return dramas
            
        except Exception as e:
            logger.error(f"从 {source_name} 收集数据失败: {e}")
            return []
    
    def _deduplicate_dramas(self, dramas: List[Dict]) -> List[Dict]:
        """根据标题和年份去重"""
        seen = set()
        unique_dramas = []
        
        for drama in dramas:
            # 创建唯一标识
            title = drama.get('title', '').strip().lower()
            year = drama.get('year', 0)
            identifier = f"{title}_{year}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique_dramas.append(drama)
            else:
                # 如果重复，选择数据更完整的版本
                existing_drama = next(
                    (d for d in unique_dramas if f"{d.get('title', '').strip().lower()}_{d.get('year', 0)}" == identifier), 
                    None
                )
                
                if existing_drama and self._is_more_complete(drama, existing_drama):
                    # 替换为更完整的版本
                    index = unique_dramas.index(existing_drama)
                    unique_dramas[index] = drama
        
        return unique_dramas
    
    def _is_more_complete(self, drama1: Dict, drama2: Dict) -> bool:
        """判断drama1是否比drama2数据更完整"""
        score1 = self._calculate_completeness_score(drama1)
        score2 = self._calculate_completeness_score(drama2)
        return score1 > score2
    
    def _calculate_completeness_score(self, drama: Dict) -> int:
        """计算剧目数据完整性得分"""
        score = 0
        
        # 基础字段
        if drama.get('title'): score += 1
        if drama.get('summary'): score += 2
        if drama.get('year'): score += 1
        if drama.get('rating', 0) > 0: score += 1
        
        # 详细信息
        if drama.get('genres'): score += len(drama['genres'])
        if drama.get('casts'): score += len(drama['casts'])
        if drama.get('directors'): score += len(drama['directors'])
        if drama.get('tags'): score += len(drama['tags'])
        
        return score
    
    def get_source_status(self) -> Dict[str, bool]:
        """获取各数据源状态"""
        status = {}
        for source_name in self.enabled_sources:
            status[source_name] = source_name in self.collectors
        return status