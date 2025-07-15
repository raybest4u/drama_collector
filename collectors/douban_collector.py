# collectors/douban_collector.py
from typing import List, Dict
from .base_collector import BaseCollector
import asyncio

class DoubanCollector(BaseCollector):
    def __init__(self):
        super().__init__(rate_limit=5)  # 豆瓣限制较严
        self.base_url = "https://api.douban.com/v2"
        
    async def collect_drama_list(self, genre: str = "电视剧", count: int = 50) -> List[Dict]:
        """收集豆瓣剧目列表"""
        dramas = []
        start = 0
        
        while len(dramas) < count:
            url = f"{self.base_url}/movie/search"
            params = {
                'q': f'{genre} 短剧',
                'start': start,
                'count': min(20, count - len(dramas))
            }
            
            data = await self.safe_request(url, params=params)
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
        url = f"{self.base_url}/movie/subject/{drama_id}"
        data = await self.safe_request(url)
        
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
