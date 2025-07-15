# tests/test_multi_source_collector.py
import pytest
from collectors.multi_source_collector import MultiSourceCollector


class TestMultiSourceCollector:
    
    @pytest.mark.asyncio
    async def test_multi_source_initialization(self):
        """测试多数据源收集器初始化"""
        async with MultiSourceCollector() as collector:
            assert collector is not None
            assert len(collector.enabled_sources) > 0
            assert 'mock' in collector.enabled_sources
    
    @pytest.mark.asyncio
    async def test_collect_drama_list_with_fallback(self):
        """测试带回退的数据收集"""
        async with MultiSourceCollector() as collector:
            dramas = await collector.collect_drama_list(count=5)
            
            # 至少应该有来自mock的数据
            assert len(dramas) > 0
            assert all('data_source' in drama for drama in dramas)
            assert any(drama['data_source'] == 'mock' for drama in dramas)
    
    @pytest.mark.asyncio 
    async def test_source_status_reporting(self):
        """测试数据源状态报告"""
        async with MultiSourceCollector() as collector:
            status = collector.get_source_status()
            
            assert isinstance(status, dict)
            assert 'mock' in status
            assert status['mock'] is True  # mock源应该总是可用
    
    @pytest.mark.asyncio
    async def test_drama_detail_with_preferred_source(self):
        """测试带偏好数据源的详情获取"""
        async with MultiSourceCollector(enable_sources=['mock']) as collector:
            # 先获取一个剧目
            dramas = await collector.collect_drama_list(count=1)
            
            if len(dramas) > 0:
                drama = dramas[0]
                detail = await collector.collect_drama_detail(
                    drama['id'], 
                    preferred_source='mock'
                )
                
                assert 'data_source' in detail
                assert detail.get('id') == drama['id']
            else:
                # 如果没有获取到数据，测试基本的detail方法
                detail = await collector.collect_drama_detail('test_id', preferred_source='mock')
                # 至少应该返回一个字典（可能为空）
                assert isinstance(detail, dict)
    
    def test_deduplication_logic(self):
        """测试去重逻辑"""
        collector = MultiSourceCollector()
        
        # 创建重复数据
        dramas = [
            {'title': '霸道总裁爱上我', 'year': 2024, 'summary': '详细描述'},
            {'title': '霸道总裁爱上我', 'year': 2024, 'summary': ''},  # 重复但信息较少
            {'title': '另一部剧', 'year': 2024, 'summary': '不同的剧'}
        ]
        
        unique_dramas = collector._deduplicate_dramas(dramas)
        
        # 应该去重，只保留两部不同的剧
        assert len(unique_dramas) == 2
        
        # 应该保留信息更完整的版本
        kept_drama = next(d for d in unique_dramas if d['title'] == '霸道总裁爱上我')
        assert kept_drama['summary'] == '详细描述'
    
    def test_completeness_scoring(self):
        """测试数据完整性评分"""
        collector = MultiSourceCollector()
        
        drama1 = {
            'title': '剧目1',
            'summary': '详细描述',
            'genres': ['爱情', '都市'],
            'casts': ['演员1', '演员2']
        }
        
        drama2 = {
            'title': '剧目2'
            # 只有标题，信息较少
        }
        
        score1 = collector._calculate_completeness_score(drama1)
        score2 = collector._calculate_completeness_score(drama2)
        
        assert score1 > score2
        assert collector._is_more_complete(drama1, drama2) is True