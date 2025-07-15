# collectors/mock_collector.py
import asyncio
from typing import List, Dict
from .base_collector import BaseCollector


class MockCollector(BaseCollector):
    """模拟数据收集器，用于开发和测试"""
    
    def __init__(self):
        super().__init__(rate_limit=100)  # 无需限速
        self.mock_dramas = self._generate_mock_data()
    
    async def collect_drama_list(self, count: int = 20) -> List[Dict]:
        """收集剧目列表"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        # 返回指定数量的模拟剧目
        return self.mock_dramas[:count]
    
    async def collect_drama_detail(self, drama_id: str) -> Dict:
        """收集单个剧目详情"""
        await asyncio.sleep(0.05)  # 模拟网络延迟
        
        # 查找对应的剧目详情
        for drama in self.mock_dramas:
            if str(drama['id']) == str(drama_id):
                return self._add_detailed_info(drama)
        
        return {}
    
    def _generate_mock_data(self) -> List[Dict]:
        """生成模拟短剧数据"""
        return [
            {
                'id': '35267208',
                'title': '霸道总裁爱上我',
                'original_title': '霸道总裁爱上我',
                'year': 2024,
                'rating': 8.2,
                'ratings_count': 15420,
                'genres': ['爱情', '都市', '偶像'],
                'countries': ['中国大陆'],
                'languages': ['汉语普通话'],
                'directors': ['张导演'],
                'writers': ['李编剧'],
                'casts': ['林晓雨', '陈俊豪', '王美丽', '李强'],
                'summary': '普通职场女孩林晓雨意外成为大企业总裁陈俊豪的贴身秘书。冷酷霸道的总裁表面对她严厉，实则内心早已被她的善良和真诚打动。在经历了误会、分离、重逢等一系列波折后，两人最终突破身份差距，收获了真挚的爱情。',
                'tags': ['霸总', '职场', '甜宠', '现代'],
                'episodes_count': 24,
                'duration': ['15分钟'],
                'source_platform': 'mock'
            },
            {
                'id': '35267209',
                'title': '古装甜宠：王爷的小娇妻',
                'original_title': '古装甜宠：王爷的小娇妻',
                'year': 2024,
                'rating': 7.8,
                'ratings_count': 12850,
                'genres': ['古装', '爱情', '甜宠'],
                'countries': ['中国大陆'],
                'languages': ['汉语普通话'],
                'directors': ['赵导演'],
                'writers': ['孙编剧'],
                'casts': ['苏小小', '萧王爷', '柳如烟', '顾管家'],
                'summary': '现代医学博士苏小小意外穿越到古代，成为丞相府的庶女。她用现代医术救了冷面王爷萧王爷一命，从此两人命运纠缠。王爷被她的聪慧和医术吸引，苏小小也被他的温柔守护感动，在宫廷阴谋中携手成长，谱写甜蜜恋曲。',
                'tags': ['穿越', '古装', '甜宠', '王爷'],
                'episodes_count': 30,
                'duration': ['12分钟'],
                'source_platform': 'mock'
            },
            {
                'id': '35267210',
                'title': '重生之娱乐圈女王',
                'original_title': '重生之娱乐圈女王',
                'year': 2024,
                'rating': 8.5,
                'ratings_count': 18960,
                'genres': ['都市', '励志', '重生'],
                'countries': ['中国大陆'],
                'languages': ['汉语普通话'],
                'directors': ['陈导演'],
                'writers': ['王编剧'],
                'casts': ['夏诗雨', '顾寒川', '林小娟', '张经纪人'],
                'summary': '前世被闺蜜背叛、事业尽毁的女星夏诗雨重生回到出道前。这一世，她利用前世的经验和记忆，重新规划演艺道路，不仅要在娱乐圈站稳脚跟，更要让那些伤害过她的人付出代价。在这个过程中，她遇到了真心守护她的制片人顾寒川。',
                'tags': ['重生', '娱乐圈', '复仇', '励志'],
                'episodes_count': 36,
                'duration': ['18分钟'],
                'source_platform': 'mock'
            },
            {
                'id': '35267211',
                'title': '校园恋爱物语',
                'original_title': '校园恋爱物语',
                'year': 2024,
                'rating': 7.6,
                'ratings_count': 9430,
                'genres': ['校园', '青春', '爱情'],
                'countries': ['中国大陆'],
                'languages': ['汉语普通话'],
                'directors': ['李导演'],
                'writers': ['陈编剧'],
                'casts': ['叶青青', '林志轩', '张小雨', '王同学'],
                'summary': '学霸女孩叶青青一直专注学习，直到遇到了阳光男孩林志轩。他是学校的篮球队长，成绩优异，人缘极好。两人从互不相识到成为同桌，再到互相喜欢，在青春校园里演绎了一段纯美的初恋故事。',
                'tags': ['校园', '初恋', '青春', '学霸'],
                'episodes_count': 20,
                'duration': ['10分钟'],
                'source_platform': 'mock'
            },
            {
                'id': '35267212',
                'title': '军婚甜宠：首长老公太霸道',
                'original_title': '军婚甜宠：首长老公太霸道',
                'year': 2024,
                'rating': 8.0,
                'ratings_count': 14520,
                'genres': ['军旅', '爱情', '甜宠'],
                'countries': ['中国大陆'],
                'languages': ['汉语普通话'],
                'directors': ['周导演'],
                'writers': ['吴编剧'],
                'casts': ['沈曼曼', '季司令', '赵副官', '李大嫂'],
                'summary': '军医沈曼曼在一次军演中救治了重伤的神秘首长季司令。首长被她的专业和勇敢深深吸引，展开了猛烈的追求攻势。从初时的抗拒到慢慢动心，沈曼曼发现这个看似严肃的军人首长私下里竟然如此温柔体贴。',
                'tags': ['军婚', '首长', '甜宠', '军医'],
                'episodes_count': 28,
                'duration': ['16分钟'],
                'source_platform': 'mock'
            }
        ]
    
    def _add_detailed_info(self, drama: Dict) -> Dict:
        """为剧目添加详细信息"""
        detailed_info = {
            'douban_url': f"https://movie.douban.com/subject/{drama['id']}/",
            'poster_url': f"https://img.example.com/poster_{drama['id']}.jpg",
            'cast_info': [
                {'name': cast, 'role': f'角色{i+1}', 'avatar': f'https://img.example.com/actor_{i}.jpg'} 
                for i, cast in enumerate(drama.get('casts', []))
            ],
            'plot_keywords': self._extract_plot_keywords(drama.get('summary', '')),
            'similar_dramas': [],  # 相似剧目
            'user_comments': self._generate_mock_comments(),
            'broadcast_info': {
                'platform': '短剧平台',
                'status': '已完结',
                'update_schedule': '每日更新2集'
            }
        }
        
        return {**drama, **detailed_info}
    
    def _extract_plot_keywords(self, summary: str) -> List[str]:
        """从剧情简介提取关键词"""
        keywords_map = {
            '霸道总裁': ['霸总', 'CEO', '豪门', '职场'],
            '穿越': ['古代', '现代', '时空', '王爷'],
            '重生': ['前世', '复仇', '逆袭', '预知'],
            '校园': ['学霸', '青春', '初恋', '同桌'],
            '军婚': ['军人', '首长', '军医', '部队']
        }
        
        extracted = []
        for key, keywords in keywords_map.items():
            if key in summary:
                extracted.extend(keywords)
        
        return extracted
    
    def _generate_mock_comments(self) -> List[Dict]:
        """生成模拟用户评论"""
        return [
            {'user': '爱看剧的小仙女', 'rating': 5, 'comment': '超级甜！男主太帅了，女主也很可爱！'},
            {'user': '剧迷小王子', 'rating': 4, 'comment': '剧情虽然俗套但是很好看，演员演技在线'},
            {'user': '短剧爱好者', 'rating': 5, 'comment': '节奏紧凑，每一集都有看点，停不下来！'}
        ]