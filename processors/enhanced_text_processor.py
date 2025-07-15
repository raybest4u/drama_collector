# processors/enhanced_text_processor.py
import re
import jieba
import jieba.posseg as pseg
from typing import List, Dict, Set, Tuple
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class EnhancedTextProcessor:
    """增强版文本处理器，支持更复杂的NLP任务"""
    
    def __init__(self):
        # 加载停用词
        self.stop_words = self._load_stop_words()
        
        # 情感词典
        self.emotion_lexicon = self._load_emotion_lexicon()
        
        # 剧情结构模式
        self.plot_patterns = self._load_plot_patterns()
        
        # 角色关系词典
        self.relationship_words = self._load_relationship_words()
        
        # 短剧特有词汇
        self.drama_vocabulary = self._load_drama_vocabulary()
        
        logger.info("增强版文本处理器初始化完成")
    
    def extract_enhanced_plot_points(self, text: str) -> List[Dict]:
        """提取增强版剧情点，包含更多上下文信息"""
        # 预处理文本
        cleaned_text = self.clean_text(text)
        
        # 按句子分割
        sentences = self._split_sentences(cleaned_text)
        
        plot_points = []
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) < 5:
                continue
            
            # 基础信息
            plot_type = self._classify_plot_type_enhanced(sentence)
            emotional_tone = self._analyze_emotion_enhanced(sentence)
            characters = self._extract_characters_enhanced(sentence)
            
            # 高级分析
            dramatic_tension = self._calculate_dramatic_tension(sentence)
            relationship_dynamics = self._analyze_relationships(sentence, characters)
            narrative_function = self._identify_narrative_function(sentence, i, len(sentences))
            
            plot_point = {
                'sequence': i + 1,
                'description': sentence.strip(),
                'plot_type': plot_type,
                'emotional_tone': emotional_tone,
                'dramatic_tension': dramatic_tension,
                'characters_involved': characters,
                'relationship_dynamics': relationship_dynamics,
                'narrative_function': narrative_function,
                'keywords': self._extract_keywords(sentence),
                'tropes': self._identify_drama_tropes(sentence)
            }
            
            plot_points.append(plot_point)
        
        # 添加情节弧分析
        plot_points = self._analyze_plot_arc(plot_points)
        
        return plot_points
    
    def extract_character_profiles(self, text: str) -> List[Dict]:
        """提取角色画像和特征"""
        characters = {}
        
        # 分词并标注词性
        words = pseg.cut(text)
        
        current_character = None
        for word, flag in words:
            # 识别人名
            if flag == 'nr' and len(word) >= 2:
                if word not in characters:
                    characters[word] = {
                        'name': word,
                        'mentions': 0,
                        'traits': [],
                        'relationships': [],
                        'roles': [],
                        'emotional_arc': []
                    }
                characters[word]['mentions'] += 1
                current_character = word
            
            # 分析角色特征
            elif current_character and flag in ['a', 'ad']:  # 形容词
                if word not in self.stop_words:
                    characters[current_character]['traits'].append(word)
        
        # 分析角色关系
        for char_name, char_data in characters.items():
            char_data['relationships'] = self._analyze_character_relationships(text, char_name)
            char_data['archetype'] = self._identify_character_archetype(char_data)
            char_data['importance'] = self._calculate_character_importance(char_data, len(text))
        
        return list(characters.values())
    
    def analyze_drama_themes(self, text: str) -> Dict:
        """分析短剧主题和类型"""
        themes = {
            'primary_themes': [],
            'secondary_themes': [],
            'genre_indicators': [],
            'cultural_elements': [],
            'target_audience': '',
            'emotional_appeal': '',
            'narrative_style': ''
        }
        
        # 主题识别
        theme_keywords = {
            'romance': ['爱情', '恋爱', '表白', '约会', '心动', '喜欢'],
            'power': ['权力', '总裁', '豪门', '霸道', '强势', '控制'],
            'revenge': ['复仇', '报复', '仇恨', '背叛', '陷害', '算计'],
            'family': ['家庭', '亲情', '父母', '兄弟', '姐妹', '血缘'],
            'growth': ['成长', '蜕变', '进步', '学习', '努力', '奋斗'],
            'fantasy': ['穿越', '重生', '魔法', '仙侠', '异能', '系统']
        }
        
        text_lower = text.lower()
        for theme, keywords in theme_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            if count >= 2:
                themes['primary_themes'].append({
                    'theme': theme,
                    'strength': count,
                    'keywords_found': [kw for kw in keywords if kw in text_lower]
                })
        
        # 类型指标
        themes['genre_indicators'] = self._identify_genre_indicators(text)
        
        # 文化元素
        themes['cultural_elements'] = self._extract_cultural_elements(text)
        
        # 目标受众分析
        themes['target_audience'] = self._analyze_target_audience(text)
        
        return themes
    
    def extract_dramatic_structure(self, plot_points: List[Dict]) -> Dict:
        """分析戏剧结构（三幕结构/起承转合）"""
        if not plot_points:
            return {}
        
        total_points = len(plot_points)
        
        # 按三幕结构划分
        act1_end = total_points // 4
        act2_end = total_points * 3 // 4
        
        structure = {
            'total_plot_points': total_points,
            'act_structure': {
                'setup': {
                    'range': (0, act1_end),
                    'points': plot_points[:act1_end],
                    'key_elements': []
                },
                'confrontation': {
                    'range': (act1_end, act2_end),
                    'points': plot_points[act1_end:act2_end],
                    'key_elements': []
                },
                'resolution': {
                    'range': (act2_end, total_points),
                    'points': plot_points[act2_end:],
                    'key_elements': []
                }
            },
            'dramatic_peaks': [],
            'emotional_trajectory': [],
            'pacing_analysis': {}
        }
        
        # 识别戏剧高潮
        tension_scores = [point.get('dramatic_tension', 0) for point in plot_points]
        max_tension = max(tension_scores) if tension_scores else 0
        
        for i, score in enumerate(tension_scores):
            if score >= max_tension * 0.8:  # 高张力点
                structure['dramatic_peaks'].append({
                    'position': i,
                    'tension_score': score,
                    'description': plot_points[i]['description']
                })
        
        # 情感轨迹
        emotions = [point.get('emotional_tone', 'neutral') for point in plot_points]
        structure['emotional_trajectory'] = self._analyze_emotional_trajectory(emotions)
        
        return structure
    
    def _split_sentences(self, text: str) -> List[str]:
        """智能分句，处理中文标点"""
        # 中文句号、感叹号、问号
        sentences = re.split(r'[。！？；]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _classify_plot_type_enhanced(self, text: str) -> str:
        """增强版情节类型分类"""
        plot_patterns = {
            'introduction': ['初次见面', '第一次', '开始', '起初', '最初'],
            'conflict': ['冲突', '争吵', '对抗', '矛盾', '斗争', '问题'],
            'romance': ['爱情', '恋爱', '喜欢', '表白', '约会', '吻', '心动'],
            'revelation': ['发现', '揭露', '真相', '秘密', '惊讶', '原来'],
            'choice': ['选择', '决定', '犹豫', '考虑', '权衡', '必须'],
            'climax': ['关键', '重要', '决定性', '转折', '突然'],
            'resolution': ['结果', '最终', '最后', '终于', '解决']
        }
        
        text_lower = text.lower()
        scores = {}
        
        for plot_type, keywords in plot_patterns.items():
            score = sum(2 if keyword in text_lower else 0 for keyword in keywords)
            if score > 0:
                scores[plot_type] = score
        
        return max(scores.keys(), key=lambda k: scores[k]) if scores else 'general'
    
    def _analyze_emotion_enhanced(self, text: str) -> str:
        """增强版情感分析"""
        emotion_scores = {}
        
        for emotion, words in self.emotion_lexicon.items():
            score = sum(1 for word in words if word in text)
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            return 'neutral'
        
        return max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
    
    def _extract_characters_enhanced(self, text: str) -> List[str]:
        """增强版角色提取"""
        characters = []
        
        # 使用词性标注提取人名
        words = pseg.cut(text)
        for word, flag in words:
            if flag == 'nr' and len(word) >= 2:  # 人名
                characters.append(word)
        
        # 提取常见角色称谓
        role_patterns = ['总裁', '老板', '秘书', '助理', '医生', '老师', '学生', '王爷', '公主']
        for pattern in role_patterns:
            if pattern in text:
                characters.append(pattern)
        
        return list(set(characters))
    
    def _calculate_dramatic_tension(self, text: str) -> float:
        """计算戏剧张力"""
        tension_indicators = {
            'high': ['突然', '急忙', '惊讶', '震惊', '危险', '紧急', '关键'],
            'medium': ['担心', '焦虑', '紧张', '期待', '希望', '害怕'],
            'low': ['平静', '安详', '温和', '舒缓', '轻松', '愉快']
        }
        
        high_count = sum(1 for word in tension_indicators['high'] if word in text)
        medium_count = sum(1 for word in tension_indicators['medium'] if word in text)
        low_count = sum(1 for word in tension_indicators['low'] if word in text)
        
        tension_score = (high_count * 3 + medium_count * 2 - low_count) / len(text) * 100
        return max(0, min(10, tension_score))  # 归一化到0-10
    
    def _load_emotion_lexicon(self) -> Dict[str, List[str]]:
        """加载情感词典"""
        return {
            'positive': ['高兴', '快乐', '幸福', '甜蜜', '温暖', '感动', '满足', '兴奋'],
            'negative': ['伤心', '难过', '愤怒', '失望', '痛苦', '绝望', '恐惧', '焦虑'],
            'neutral': ['平静', '普通', '一般', '正常', '简单', '基本'],
            'romantic': ['浪漫', '深情', '温柔', '心动', '爱意', '甜蜜', '亲密'],
            'dramatic': ['激烈', '强烈', '剧烈', '猛烈', '严重', '重大', '关键']
        }
    
    def _load_plot_patterns(self) -> Dict:
        """加载剧情模式"""
        return {
            'meet_cute': ['偶遇', '巧合', '意外相遇', '不期而遇'],
            'misunderstanding': ['误会', '误解', '错误理解', '搞错'],
            'separation': ['分离', '离别', '分开', '告别'],
            'reunion': ['重逢', '再次见面', '重新相遇', '回来'],
            'confession': ['表白', '告白', '坦白', '承认感情'],
            'betrayal': ['背叛', '欺骗', '出卖', '陷害']
        }
    
    def _load_relationship_words(self) -> Dict:
        """加载关系词汇"""
        return {
            'romantic': ['爱人', '恋人', '情侣', '男友', '女友', '夫妻'],
            'family': ['父母', '兄弟', '姐妹', '儿女', '亲人', '家人'],
            'professional': ['同事', '上司', '下属', '合作伙伴', '客户'],
            'social': ['朋友', '闺蜜', '同学', '邻居', '室友']
        }
    
    def _load_drama_vocabulary(self) -> Set[str]:
        """加载短剧特有词汇"""
        return {
            '霸道总裁', '灰姑娘', '白马王子', '豪门', '逆袭', '穿越',
            '重生', '系统', '金手指', '玛丽苏', '杰克苏', '甜宠',
            '虐恋', '追妻火葬场', '打脸', '装逼', '开挂'
        }
    
    def clean_text(self, text: str) -> str:
        """文本清洗"""
        if not text:
            return ""
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符但保留中文标点
        text = re.sub(r'[^\u4e00-\u9fff\w\s，。！？；：""''（）【】]', '', text)
        
        return text.strip()
    
    def _load_stop_words(self) -> Set[str]:
        """加载停用词"""
        return {
            '的', '了', '在', '是', '我', '你', '他', '她', '它', '们',
            '这', '那', '些', '个', '也', '都', '就', '可以', '已经',
            '没有', '还是', '因为', '所以', '但是', '如果', '虽然'
        }
    
    def _analyze_relationships(self, text: str, characters: List[str]) -> List[Dict]:
        """分析角色关系"""
        relationships = []
        
        for rel_type, keywords in self.relationship_words.items():
            for keyword in keywords:
                if keyword in text:
                    relationships.append({
                        'type': rel_type,
                        'indicator': keyword,
                        'characters': characters
                    })
        
        return relationships
    
    def _identify_narrative_function(self, sentence: str, position: int, total: int) -> str:
        """识别叙事功能"""
        relative_position = position / total if total > 0 else 0
        
        if relative_position < 0.25:
            return 'exposition'  # 铺垫
        elif relative_position < 0.75:
            return 'development'  # 发展
        else:
            return 'conclusion'  # 结尾
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        words = jieba.cut(text)
        keywords = [word for word in words 
                   if len(word) > 1 and word not in self.stop_words]
        
        # 使用词频统计
        word_freq = Counter(keywords)
        return [word for word, freq in word_freq.most_common(5)]
    
    def _identify_drama_tropes(self, text: str) -> List[str]:
        """识别戏剧套路"""
        tropes = []
        
        trope_patterns = {
            '霸总': ['霸道总裁', '总裁', '霸道', '强势'],
            '灰姑娘': ['平凡', '普通', '贫穷', '出身'],
            '误会': ['误会', '误解', '错误'],
            '追妻': ['追回', '挽回', '重新'],
            '打脸': ['打脸', '证明', '实力']
        }
        
        for trope, patterns in trope_patterns.items():
            if any(pattern in text for pattern in patterns):
                tropes.append(trope)
        
        return tropes
    
    def _analyze_plot_arc(self, plot_points: List[Dict]) -> List[Dict]:
        """分析情节弧"""
        for i, point in enumerate(plot_points):
            # 计算相对位置
            relative_position = i / len(plot_points) if plot_points else 0
            
            # 标记情节位置
            if relative_position < 0.25:
                point['arc_position'] = 'setup'
            elif relative_position < 0.75:
                point['arc_position'] = 'confrontation'
            else:
                point['arc_position'] = 'resolution'
        
        return plot_points
    
    def _analyze_emotional_trajectory(self, emotions: List[str]) -> Dict:
        """分析情感轨迹"""
        emotion_values = {
            'positive': 1, 'romantic': 1, 'negative': -1, 
            'dramatic': 0.5, 'neutral': 0
        }
        
        trajectory = [emotion_values.get(emotion, 0) for emotion in emotions]
        
        return {
            'values': trajectory,
            'average': sum(trajectory) / len(trajectory) if trajectory else 0,
            'volatility': self._calculate_volatility(trajectory),
            'trend': 'ascending' if trajectory[-1] > trajectory[0] else 'descending'
        }
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """计算情感波动性"""
        if len(values) < 2:
            return 0
        
        changes = [abs(values[i] - values[i-1]) for i in range(1, len(values))]
        return sum(changes) / len(changes)
    
    def _analyze_character_relationships(self, text: str, character: str) -> List[str]:
        """分析角色关系"""
        relationships = []
        char_context = self._get_character_context(text, character)
        
        for rel_type, keywords in self.relationship_words.items():
            if any(keyword in char_context for keyword in keywords):
                relationships.append(rel_type)
        
        return relationships
    
    def _get_character_context(self, text: str, character: str) -> str:
        """获取角色上下文"""
        sentences = self._split_sentences(text)
        context = ""
        
        for sentence in sentences:
            if character in sentence:
                context += sentence + " "
        
        return context
    
    def _identify_character_archetype(self, char_data: Dict) -> str:
        """识别角色原型"""
        traits = char_data.get('traits', [])
        
        archetypes = {
            'hero': ['勇敢', '正义', '坚强', '善良'],
            'villain': ['邪恶', '狡猾', '残忍', '自私'],
            'mentor': ['智慧', '经验', '指导', '帮助'],
            'lover': ['温柔', '美丽', '善解人意', '体贴']
        }
        
        scores = {}
        for archetype, keywords in archetypes.items():
            score = sum(1 for trait in traits if trait in keywords)
            if score > 0:
                scores[archetype] = score
        
        return max(scores.keys(), key=lambda k: scores[k]) if scores else 'undefined'
    
    def _calculate_character_importance(self, char_data: Dict, text_length: int) -> float:
        """计算角色重要性"""
        mentions = char_data.get('mentions', 0)
        traits_count = len(char_data.get('traits', []))
        relationships_count = len(char_data.get('relationships', []))
        
        # 综合评分
        importance = (mentions * 2 + traits_count + relationships_count) / text_length * 1000
        return min(10, importance)  # 归一化到0-10
    
    def _identify_genre_indicators(self, text: str) -> List[str]:
        """识别类型指标"""
        genre_keywords = {
            'romance': ['爱情', '恋爱', '浪漫'],
            'drama': ['戏剧', '冲突', '情感'],
            'comedy': ['搞笑', '幽默', '有趣'],
            'thriller': ['悬疑', '紧张', '神秘']
        }
        
        indicators = []
        for genre, keywords in genre_keywords.items():
            if any(keyword in text for keyword in keywords):
                indicators.append(genre)
        
        return indicators
    
    def _extract_cultural_elements(self, text: str) -> List[str]:
        """提取文化元素"""
        cultural_keywords = {
            'traditional': ['传统', '古代', '古装', '宫廷'],
            'modern': ['现代', '都市', '职场', '科技'],
            'fantasy': ['玄幻', '仙侠', '魔法', '神话']
        }
        
        elements = []
        for culture, keywords in cultural_keywords.items():
            if any(keyword in text for keyword in keywords):
                elements.append(culture)
        
        return elements
    
    def _analyze_target_audience(self, text: str) -> str:
        """分析目标受众"""
        audience_indicators = {
            'young_female': ['言情', '甜宠', '霸总', '少女心'],
            'mature_female': ['职场', '家庭', '现实', '成熟'],
            'male': ['动作', '冒险', '战争', '权谋'],
            'general': ['温馨', '家庭', '喜剧', '正能量']
        }
        
        scores = {}
        for audience, keywords in audience_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[audience] = score
        
        return max(scores.keys(), key=lambda k: scores[k]) if scores else 'general'