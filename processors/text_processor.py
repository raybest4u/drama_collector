# processors/text_processor.py
import re
import jieba
from typing import List, Dict
import openai  # 可选：用于高级文本处理

class TextProcessor:
    def __init__(self):
        # 加载停用词
        self.stop_words = self._load_stop_words()
        # 角色类型关键词
        self.role_keywords = {
            'male_lead': ['男主', '男主角', '总裁', '王爷', '皇帝'],
            'female_lead': ['女主', '女主角', '女孩', '公主', '皇后'],
            'supporting': ['配角', '朋友', '助理', '管家', '闺蜜']
        }
        
    def extract_plot_points(self, text: str) -> List[Dict]:
        """从剧情描述中提取情节点"""
        # 按句号分割
        sentences = re.split(r'[。！？]', text)
        plot_points = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 5:  # 过滤太短的句子
                continue
                
            plot_type = self._classify_plot_type(sentence)
            emotional_tone = self._analyze_emotion(sentence)
            characters = self._extract_characters_from_text(sentence)
            
            plot_points.append({
                'sequence': i + 1,
                'description': sentence,
                'plot_type': plot_type,
                'emotional_tone': emotional_tone,
                'characters_involved': characters
            })
            
        return plot_points
    
    def _classify_plot_type(self, text: str) -> str:
        """分类情节类型"""
        conflict_words = ['冲突', '争吵', '对抗', '矛盾', '斗争']
        romance_words = ['爱情', '恋爱', '喜欢', '表白', '约会', '吻']
        revelation_words = ['发现', '揭露', '真相', '秘密', '惊讶']
        choice_words = ['选择', '决定', '犹豫', '考虑', '权衡']
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in conflict_words):
            return 'conflict'
        elif any(word in text_lower for word in romance_words):
            return 'romance'
        elif any(word in text_lower for word in revelation_words):
            return 'revelation'
        elif any(word in text_lower for word in choice_words):
            return 'choice'
        else:
            return 'general'
    
    def _analyze_emotion(self, text: str) -> str:
        """分析情感倾向"""
        positive_words = ['高兴', '快乐', '幸福', '甜蜜', '温暖', '感动']
        negative_words = ['伤心', '难过', '痛苦', '愤怒', '绝望', '孤独']
        tense_words = ['紧张', '激动', '刺激', '危险', '惊险', '焦虑']
        
        text_lower = text.lower()
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        tense_score = sum(1 for word in tense_words if word in text_lower)
        
        if tense_score > max(positive_score, negative_score):
            return 'tense'
        elif positive_score > negative_score:
            return 'happy'
        elif negative_score > positive_score:
            return 'sad'
        else:
            return 'neutral'
    
    def _extract_characters_from_text(self, text: str) -> List[str]:
        """从文本中提取人物名称"""
        # 简单的人名识别（实际项目中可能需要更复杂的NLP）
        words = jieba.lcut(text)
        names = []
        
        for word in words:
            # 简单规则：2-4个字符，包含常见人名字符
            if (2 <= len(word) <= 4 and 
                any(char in word for char in '小大老张王李赵刘陈杨黄周吴徐孙马朱胡林郭何高梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋魏陈蔡贾丁薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭盛邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段漕钱汤尹黎易常武乔贺赖龚文庞樊兰殷施陶洪翟安颜倪严牛温芦季俞章鲁葛伍韦申尤毕聂丛焦向柳邢路岳齐沿梅莫庄辛管祝左涂谷祁时舒耿牟卜路詹关苗凌费纪靳盛童欧甄项曲成游阳裴席卫查屈鲍位覃霍翁隋植甘景薄单包司柏宁柯阮桂闵欧阳令狐皇甫上官司徒诸葛司马宇文呼延夏侯'):
                names.append(word)
                
        return list(set(names))  # 去重
    
    def _load_stop_words(self) -> set:
        """加载停用词"""
        # 这里可以加载中文停用词表
        return {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
