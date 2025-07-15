# collectors/mydramalist_collector.py
from typing import List, Dict
from .base_collector import BaseCollector
import asyncio
import re
from urllib.parse import quote


class MyDramaListCollector(BaseCollector):
    """MyDramaList 网站爬虫收集器"""
    
    def __init__(self):
        super().__init__(rate_limit=3)  # 适中的访问频率
        self.base_url = "https://mydramalist.com"
        
    async def collect_drama_list(self, count: int = 20, year: int = 2024) -> List[Dict]:
        """收集剧目列表"""
        dramas = []
        page = 1
        
        while len(dramas) < count and page <= 5:  # 限制最多5页
            # 构建搜索URL - 中国短剧
            search_url = f"{self.base_url}/search"
            params = {
                'adv': 'titles',
                'ty': 'sh',  # 短剧类型
                'co': '3',   # 中国
                'yr': str(year),
                'page': page
            }
            
            # 由于这是HTML页面，我们需要特殊处理
            html_content = await self._get_html_content(search_url, params)
            
            if not html_content:
                break
            
            page_dramas = self._parse_drama_list_html(html_content)
            
            if not page_dramas:
                break
                
            dramas.extend(page_dramas)
            page += 1
            
            await asyncio.sleep(1)  # 礼貌延时
            
        return dramas[:count]
    
    async def collect_drama_detail(self, drama_id: str) -> Dict:
        """收集剧目详情"""
        detail_url = f"{self.base_url}/{drama_id}"
        
        html_content = await self._get_html_content(detail_url)
        
        if not html_content:
            return {}
        
        return self._parse_drama_detail_html(html_content, drama_id)
    
    async def _get_html_content(self, url: str, params: Dict = None) -> str:
        """获取HTML内容"""
        try:
            await self.rate_limiter.acquire()
            
            if params:
                # 手动构建查询字符串
                query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
                url = f"{url}?{query_string}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"HTTP错误: {response.status} for {url}")
                    return ""
                    
        except Exception as e:
            print(f"获取HTML失败: {url}, 错误: {e}")
            return ""
    
    def _parse_drama_list_html(self, html: str) -> List[Dict]:
        """解析剧目列表HTML（简化版本）"""
        dramas = []
        
        # 使用正则表达式简单提取（实际项目中应使用BeautifulSoup）
        # 这里创建模拟数据来演示结构
        
        # 模拟从HTML中提取的数据
        mock_extractions = [
            {
                'id': 'chinese-drama-2024-1',
                'title': '霸道总裁的小甜妻',
                'year': 2024,
                'rating': 8.1,
                'country': 'China',
                'episodes': 20
            },
            {
                'id': 'chinese-drama-2024-2', 
                'title': '穿越之王妃要上位',
                'year': 2024,
                'rating': 7.9,
                'country': 'China',
                'episodes': 24
            },
            {
                'id': 'chinese-drama-2024-3',
                'title': '重生之娱乐圈女王',
                'year': 2024,
                'rating': 8.3,
                'country': 'China', 
                'episodes': 30
            }
        ]
        
        for item in mock_extractions:
            dramas.append({
                'id': item['id'],
                'title': item['title'],
                'year': item['year'],
                'rating': item['rating'],
                'ratings_count': 1000,  # 默认值
                'genres': ['Romance', 'Drama'],
                'countries': [item['country']],
                'languages': ['Chinese'],
                'directors': ['Unknown Director'],
                'writers': ['Unknown Writer'],
                'casts': ['Unknown Cast'],
                'episodes_count': item['episodes'],
                'source_platform': 'mydramalist'
            })
        
        return dramas
    
    def _parse_drama_detail_html(self, html: str, drama_id: str) -> Dict:
        """解析剧目详情HTML（简化版本）"""
        
        # 模拟详情数据
        detail_info = {
            'id': drama_id,
            'summary': '这是一部精彩的中国短剧，讲述了现代都市中的爱情故事。男女主角经历了种种波折，最终走到了一起。',
            'poster_url': f'https://mydramalist.com/images/{drama_id}.jpg',
            'tags': ['Romance', 'Modern', 'Happy Ending'],
            'alternative_titles': [],
            'broadcast_info': {
                'original_network': 'Online Platform',
                'status': 'Completed',
                'aired_date': '2024'
            },
            'production_info': {
                'screenwriter': 'Unknown',
                'director': 'Unknown',
                'producer': 'Unknown'
            }
        }
        
        return detail_info