# collectors/douban_collector.py
from typing import List, Dict
from .base_collector import BaseCollector
import asyncio

class DoubanCollector(BaseCollector):
    def __init__(self):
        super().__init__(rate_limit=2)  # 豆瓣限制更严，降低速率
        self.api_base_url = "https://api.douban.com/v2"
        self.web_base_url = "https://movie.douban.com"
        self.use_web_fallback = True  # 当API失败时使用网页爬取
        
    async def collect_drama_list(self, genre: str = "电视剧", count: int = 50) -> List[Dict]:
        """收集豆瓣剧目列表"""
        dramas = []
        start = 0
        
        while len(dramas) < count:
            # 首先尝试API访问
            url = f"{self.api_base_url}/movie/search"
            params = {
                'q': f'{genre} 短剧',
                'start': start,
                'count': min(20, count - len(dramas))
            }
            
            data = await self.safe_request(url, params=params)
            
            # 如果API失败且启用了网页回退，尝试网页爬取
            if not data.get('subjects') and self.use_web_fallback:
                print(f"API访问失败，尝试网页爬取...")
                web_data = await self._scrape_douban_web(genre, start, min(20, count - len(dramas)))
                if web_data:
                    data = {'subjects': web_data}
            
            if not data.get('subjects'):
                break
                
            for item in data['subjects']:
                if self._is_short_drama(item):
                    dramas.append({
                        'id': item['id'],
                        'title': item['title'],
                        'year': item.get('year'),
                        'rating': item.get('rating', {}).get('average', 0),
                        'genres': item.get('genres', []),
                        'directors': [d['name'] for d in item.get('directors', [])],
                        'casts': [c['name'] for c in item.get('casts', [])]
                    })
            
            start += 20
            await asyncio.sleep(1)  # 额外延时保护
            
        return dramas
    
    async def collect_drama_detail(self, drama_id: str) -> Dict:
        """收集剧目详情"""
        # 尝试API访问
        url = f"{self.api_base_url}/movie/subject/{drama_id}"
        data = await self.safe_request(url)
        
        # 如果API失败，尝试网页爬取
        if not data and self.use_web_fallback:
            print(f"API获取详情失败，尝试网页爬取: {drama_id}")
            data = await self._scrape_drama_detail_web(drama_id)
        
        if not data:
            return {}
            
        return {
            'id': data.get('id'),
            'title': data.get('title'),
            'original_title': data.get('original_title'),
            'summary': data.get('summary', ''),
            'genres': data.get('genres', []),
            'countries': data.get('countries', []),
            'languages': data.get('languages', []),
            'year': data.get('year'),
            'rating': data.get('rating', {}).get('average', 0),
            'ratings_count': data.get('ratings_count', 0),
            'directors': [d['name'] for d in data.get('directors', [])],
            'writers': [w['name'] for w in data.get('writers', [])],
            'casts': [c['name'] for c in data.get('casts', [])],
            'episodes_count': data.get('episodes_count'),
            'duration': data.get('durations', []),
            'tags': [tag['name'] for tag in data.get('tags', [])]
        }
    
    def _is_short_drama(self, item: Dict) -> bool:
        """判断是否为短剧"""
        title = item.get('title', '').lower()
        genres = item.get('genres', [])
        
        # 简单规则判断
        short_keywords = ['短剧', '微剧', '网剧']
        duration_indicators = ['集', '话', '期']
        
        return (any(keyword in title for keyword in short_keywords) or
                '电视剧' in genres or 
                any(indicator in title for indicator in duration_indicators))
    
    async def _scrape_douban_web(self, genre: str, start: int, count: int) -> List[Dict]:
        """从豆瓣网页爬取剧目列表（备用方案）"""
        try:
            # 构建搜索URL
            search_url = f"{self.web_base_url}/j/search_subjects"
            params = {
                'type': 'tv',  # 电视剧类型
                'tag': '短剧',
                'page_limit': count,
                'page_start': start
            }
            
            data = await self.safe_request(search_url, params=params)
            
            if not data.get('subjects'):
                return []
            
            # 转换为统一格式
            subjects = []
            for item in data['subjects']:
                subjects.append({
                    'id': item.get('id'),
                    'title': item.get('title'),
                    'year': item.get('year'),
                    'rating': {'average': float(item.get('rate', 0))},
                    'genres': [],  # 网页版可能不包含完整类型信息
                    'directors': [],
                    'casts': []
                })
            
            return subjects
            
        except Exception as e:
            print(f"网页爬取失败: {e}")
            return []
    
    async def _scrape_drama_detail_web(self, drama_id: str) -> Dict:
        """从豆瓣网页爬取剧目详情（备用方案）"""
        try:
            detail_url = f"{self.web_base_url}/subject/{drama_id}/"
            
            # 这里需要解析HTML，暂时返回基础信息
            # 实际实现需要使用BeautifulSoup解析HTML
            response = await self.safe_request(detail_url)
            
            # 简单返回基础结构，实际需要HTML解析
            if response:
                return {
                    'id': drama_id,
                    'title': f'Drama_{drama_id}',  # 占位符
                    'summary': '通过网页爬取获得',
                    'rating': {'average': 0},
                    'genres': ['电视剧'],
                    'year': 2024
                }
            
            return {}
            
        except Exception as e:
            print(f"详情页爬取失败: {e}")
            return {}
