# tests/test_mock_collector.py
import pytest
import asyncio
from collectors.mock_collector import MockCollector


class TestMockCollector:
    
    @pytest.mark.asyncio
    async def test_collect_drama_list(self):
        """测试收集剧目列表功能"""
        async with MockCollector() as collector:
            dramas = await collector.collect_drama_list(count=3)
            
            assert len(dramas) == 3
            assert all('id' in drama for drama in dramas)
            assert all('title' in drama for drama in dramas)
            assert all('summary' in drama for drama in dramas)
    
    @pytest.mark.asyncio
    async def test_collect_drama_detail(self):
        """测试收集剧目详情功能"""
        async with MockCollector() as collector:
            # 获取一个剧目ID
            dramas = await collector.collect_drama_list(count=1)
            drama_id = dramas[0]['id']
            
            # 获取详情
            detail = await collector.collect_drama_detail(drama_id)
            
            assert 'douban_url' in detail
            assert 'cast_info' in detail
            assert 'plot_keywords' in detail
            assert detail['id'] == drama_id
    
    @pytest.mark.asyncio
    async def test_drama_data_structure(self):
        """测试剧目数据结构完整性"""
        async with MockCollector() as collector:
            dramas = await collector.collect_drama_list(count=1)
            drama = dramas[0]
            
            required_fields = [
                'id', 'title', 'year', 'rating', 'genres', 
                'countries', 'casts', 'summary', 'source_platform'
            ]
            
            for field in required_fields:
                assert field in drama, f"Missing required field: {field}"
    
    def test_mock_data_generation(self):
        """测试模拟数据生成"""
        collector = MockCollector()
        mock_data = collector.mock_dramas
        
        assert len(mock_data) > 0
        assert all('霸道总裁' in drama['title'] or 
                  '古装' in drama['title'] or 
                  '重生' in drama['title'] or
                  '校园' in drama['title'] or
                  '军婚' in drama['title'] 
                  for drama in mock_data)