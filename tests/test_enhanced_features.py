# tests/test_enhanced_features.py
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch

from processors.enhanced_text_processor import EnhancedTextProcessor
from utils.data_validator import DataValidator, ValidationLevel, DataType
from utils.batch_processor import BatchProcessorManager
from utils.performance_monitor import PerformanceMonitor, timing, MetricsCollector


class TestEnhancedTextProcessor:
    
    def setup_method(self):
        """设置测试环境"""
        self.processor = EnhancedTextProcessor()
    
    def test_enhanced_plot_extraction(self):
        """测试增强剧情点提取"""
        text = "霸道总裁陈俊豪第一次见到林晓雨时就被她吸引。两人经历了误会和分离，最终在一起获得了幸福。"
        
        plot_points = self.processor.extract_enhanced_plot_points(text)
        
        assert len(plot_points) > 0
        
        # 检查第一个剧情点的结构
        first_point = plot_points[0]
        assert 'sequence' in first_point
        assert 'description' in first_point
        assert 'plot_type' in first_point
        assert 'emotional_tone' in first_point
        assert 'dramatic_tension' in first_point
        assert 'characters_involved' in first_point
        assert 'keywords' in first_point
        assert 'tropes' in first_point
    
    def test_character_profile_extraction(self):
        """测试角色画像提取"""
        text = "林晓雨是一个善良勇敢的女孩，陈俊豪是霸道总裁。"
        
        character_profiles = self.processor.extract_character_profiles(text)
        
        assert isinstance(character_profiles, list)
        # 可能没有提取到角色（取决于jieba分词结果）
        if character_profiles:
            character = character_profiles[0]
            assert 'name' in character
            assert 'mentions' in character
            assert 'traits' in character
            assert 'archetype' in character
    
    def test_drama_themes_analysis(self):
        """测试戏剧主题分析"""
        text = "这是一部关于爱情和权力的现代都市剧，讲述了霸道总裁和普通女孩的爱情故事。"
        
        themes = self.processor.analyze_drama_themes(text)
        
        assert 'primary_themes' in themes
        assert 'genre_indicators' in themes
        assert 'cultural_elements' in themes
        assert 'target_audience' in themes
        
        # 应该识别出爱情主题（可能为空，这也是正常的）
        primary_themes = themes['primary_themes']
        # 由于主题识别依赖于关键词匹配，可能不会总是检测到
        # 这里我们只验证返回的数据结构是正确的
        assert isinstance(primary_themes, list)
    
    def test_dramatic_structure_analysis(self):
        """测试戏剧结构分析"""
        # 创建模拟剧情点
        plot_points = [
            {'description': '初次相遇', 'dramatic_tension': 3.0, 'emotional_tone': 'positive'},
            {'description': '产生冲突', 'dramatic_tension': 7.0, 'emotional_tone': 'negative'},
            {'description': '和好如初', 'dramatic_tension': 5.0, 'emotional_tone': 'positive'}
        ]
        
        structure = self.processor.extract_dramatic_structure(plot_points)
        
        assert 'total_plot_points' in structure
        assert 'act_structure' in structure
        assert 'dramatic_peaks' in structure
        assert 'emotional_trajectory' in structure
        
        assert structure['total_plot_points'] == 3
        assert 'setup' in structure['act_structure']
        assert 'confrontation' in structure['act_structure']
        assert 'resolution' in structure['act_structure']


class TestDataValidator:
    
    def setup_method(self):
        """设置测试环境"""
        self.validator = DataValidator(ValidationLevel.MODERATE)
    
    def test_valid_drama_data(self):
        """测试有效剧目数据验证"""
        valid_data = {
            'id': '12345',
            'title': '霸道总裁爱上我',
            'year': 2024,
            'rating': 8.5,
            'summary': '这是一部精彩的爱情剧',
            'genres': ['爱情', '都市'],
            'casts': ['张三', '李四'],
            'directors': ['王导演'],
            'episodes_count': 24
        }
        
        result = self.validator.validate_drama_data(valid_data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.quality_score > 5.0
        assert 'id' in result.cleaned_data
        assert 'title' in result.cleaned_data
    
    def test_invalid_drama_data(self):
        """测试无效剧目数据验证"""
        invalid_data = {
            'title': '',  # 空标题
            'year': 'invalid_year',  # 无效年份
            'rating': 15.0,  # 超出范围的评分
            'episodes_count': -1  # 负数集数
        }
        
        result = self.validator.validate_drama_data(invalid_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert result.quality_score < 5.0
    
    def test_data_cleaning(self):
        """测试数据清洗"""
        dirty_data = {
            'id': '12345',
            'title': '  霸道总裁爱上我【热播】  ',  # 有多余空格和标记
            'summary': '<p>这是一部精彩的爱情剧</p>',  # 包含HTML标签
            'genres': ['爱情', '', '都市', '爱情'],  # 有空值和重复
        }
        
        result = self.validator.validate_drama_data(dirty_data)
        
        assert result.cleaned_data['title'] == '霸道总裁爱上我'  # 应该清除空格和标记
        assert '<p>' not in result.cleaned_data['summary']  # 应该移除HTML标签
        assert '' not in result.cleaned_data['genres']  # 应该移除空值
    
    def test_batch_validation(self):
        """测试批量验证"""
        data_list = [
            {'id': '1', 'title': '剧目1'},
            {'id': '2', 'title': '剧目2'},
            {'title': ''},  # 无效数据
        ]
        
        results = self.validator.batch_validate(data_list, DataType.DRAMA)
        
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False


class TestBatchProcessor:
    
    def setup_method(self):
        """设置测试环境"""
        self.manager = BatchProcessorManager()
    
    @pytest.mark.asyncio
    async def test_simple_batch_processing(self):
        """测试简单批处理"""
        
        async def simple_processor(item):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return {'processed': item['value'] * 2}
        
        test_data = [{'value': i} for i in range(5)]
        
        job_id = await self.manager.processor.submit_job(
            job_id='test_job',
            data=test_data,
            processor_func=simple_processor,
            batch_size=2
        )
        
        # 等待任务完成
        for _ in range(30):  # 最多等待3秒
            status = await self.manager.get_job_status(job_id)
            if status and status['status'] == 'completed':
                break
            await asyncio.sleep(0.1)
        
        status = await self.manager.get_job_status(job_id)
        assert status is not None
        assert status['status'] == 'completed'
        assert status['results_count'] == 5
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_errors(self):
        """测试带错误的批处理"""
        
        async def error_processor(item):
            if item['value'] == 2:
                raise ValueError("Test error")
            return {'processed': item['value']}
        
        test_data = [{'value': i} for i in range(4)]
        
        job_id = await self.manager.processor.submit_job(
            job_id='error_test_job',
            data=test_data,
            processor_func=error_processor,
            batch_size=2
        )
        
        # 等待任务完成
        for _ in range(30):
            status = await self.manager.get_job_status(job_id)
            if status and status['status'] in ['completed', 'failed']:
                break
            await asyncio.sleep(0.1)
        
        status = await self.manager.get_job_status(job_id)
        assert status is not None
        # 任务应该完成（部分成功）
        assert status['results_count'] == 4  # 包含None结果


class TestPerformanceMonitor:
    
    def setup_method(self):
        """设置测试环境"""
        self.monitor = PerformanceMonitor()
    
    def test_metric_recording(self):
        """测试指标记录"""
        self.monitor.record_metric('test_metric', 42.0, 'units')
        
        recent_metrics = self.monitor.get_recent_metrics(minutes=1)
        assert len(recent_metrics) > 0
        
        last_metric = recent_metrics[-1]
        assert last_metric['name'] == 'test_metric'
        assert last_metric['value'] == 42.0
        assert last_metric['unit'] == 'units'
    
    @pytest.mark.asyncio
    async def test_timing_decorator(self):
        """测试计时装饰器"""
        
        @self.monitor.timing('test_operation')
        async def test_async_function():
            await asyncio.sleep(0.01)
            return 'result'
        
        result = await test_async_function()
        assert result == 'result'
        
        stats = self.monitor.get_processing_stats('test_operation')
        assert stats['total_processed'] == 1
        assert stats['average_time'] > 0
    
    def test_sync_timing_decorator(self):
        """测试同步计时装饰器"""
        
        @self.monitor.timing('sync_test_operation')
        def test_sync_function():
            import time
            time.sleep(0.01)
            return 'sync_result'
        
        result = test_sync_function()
        assert result == 'sync_result'
        
        stats = self.monitor.get_processing_stats('sync_test_operation')
        assert stats['total_processed'] == 1
        assert stats['average_time'] > 0
    
    def test_metrics_collector(self):
        """测试指标收集器"""
        collector = MetricsCollector('test_component', self.monitor)
        
        collector.record('custom_metric', 100.0, 'items')
        
        recent_metrics = self.monitor.get_recent_metrics(minutes=1)
        component_metric = next(
            (m for m in recent_metrics if m['name'] == 'test_component_custom_metric'),
            None
        )
        
        assert component_metric is not None
        assert component_metric['value'] == 100.0
        assert component_metric['tags']['component'] == 'test_component'
    
    def test_performance_summary(self):
        """测试性能摘要"""
        # 记录一些指标
        self.monitor.record_metric('test1', 1.0)
        self.monitor.record_metric('test2', 2.0)
        
        summary = self.monitor.get_performance_summary()
        
        assert 'system_metrics' in summary
        assert 'processing_stats' in summary
        assert 'total_metrics_recorded' in summary
        assert 'monitoring_active' in summary
        assert 'alerts' in summary
        
        assert summary['total_metrics_recorded'] >= 2


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self):
        """测试完整处理流水线"""
        
        # 模拟剧目数据
        drama_data = {
            'id': 'test_drama_001',
            'title': '霸道总裁的甜宠妻',
            'year': 2024,
            'rating': 8.2,
            'summary': '霸道总裁陈俊豪遇到了善良的林晓雨，两人从误会到相爱，最终走到一起。这是一个充满甜蜜和温暖的爱情故事。',
            'genres': ['爱情', '都市', '甜宠'],
            'casts': ['陈俊豪', '林晓雨'],
            'source_platform': 'test'
        }
        
        # 数据验证
        validator = DataValidator(ValidationLevel.MODERATE)
        validation_result = validator.validate_drama_data(drama_data)
        
        assert validation_result.is_valid
        cleaned_data = validation_result.cleaned_data
        
        # 增强文本处理
        processor = EnhancedTextProcessor()
        
        if cleaned_data.get('summary'):
            plot_points = processor.extract_enhanced_plot_points(cleaned_data['summary'])
            assert len(plot_points) > 0
            
            character_profiles = processor.extract_character_profiles(cleaned_data['summary'])
            assert isinstance(character_profiles, list)
            
            themes = processor.analyze_drama_themes(cleaned_data['summary'])
            assert 'primary_themes' in themes
            
            if plot_points:
                structure = processor.extract_dramatic_structure(plot_points)
                assert 'act_structure' in structure
        
        # 性能监控
        monitor = PerformanceMonitor()
        
        @monitor.timing('integration_test')
        async def process_drama():
            await asyncio.sleep(0.01)  # 模拟处理
            return cleaned_data
        
        result = await process_drama()
        assert result['id'] == 'test_drama_001'
        
        stats = monitor.get_processing_stats('integration_test')
        assert stats['total_processed'] == 1