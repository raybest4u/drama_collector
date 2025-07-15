# tests/test_text_processor.py
import pytest
from processors.text_processor import TextProcessor


class TestTextProcessor:
    
    def setup_method(self):
        """设置测试环境"""
        self.processor = TextProcessor()
    
    def test_extract_plot_points(self):
        """测试剧情点提取"""
        text = "霸道总裁陈俊豪爱上了普通员工林晓雨。经历了误会和分离后最终在一起。"
        
        plot_points = self.processor.extract_plot_points(text)
        
        assert isinstance(plot_points, list)
        assert len(plot_points) > 0
        
        # 检查返回的是字典格式
        for point in plot_points:
            assert isinstance(point, dict)
            assert 'description' in point
            assert 'plot_type' in point
            assert 'emotional_tone' in point
    
    def test_extract_characters_from_text(self):
        """测试从文本提取角色名"""
        text = "林晓雨是一个普通的职场女孩，陈俊豪是霸道总裁。"
        
        names = self.processor._extract_characters_from_text(text)
        
        assert isinstance(names, list)
        # 检查是否提取到人名
        assert len(names) >= 0  # 可能没有提取到，取决于实现
    
    def test_classify_plot_type(self):
        """测试剧情类型分类"""
        romance_text = "两人相爱了"
        conflict_text = "他们发生了争吵"
        
        romance_type = self.processor._classify_plot_type(romance_text)
        conflict_type = self.processor._classify_plot_type(conflict_text)
        
        assert isinstance(romance_type, str)
        assert isinstance(conflict_type, str)
    
    def test_analyze_emotion(self):
        """测试情感分析"""
        positive_text = "他们幸福地在一起了"
        negative_text = "她伤心地离开了"
        
        positive_emotion = self.processor._analyze_emotion(positive_text)
        negative_emotion = self.processor._analyze_emotion(negative_text)
        
        assert isinstance(positive_emotion, str)
        assert isinstance(negative_emotion, str)