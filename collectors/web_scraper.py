# collectors/web_scraper.py
from typing import List, Dict
import asyncio
from bs4 import BeautifulSoup
from .base_collector import BaseCollector

class WebScraper(BaseCollector):
    def __init__(self):
        super().__init__(rate_limit=8)
        
    async def collect_drama_list(self, source_url: str = None) -> List[Dict]:
        """从网页收集剧目列表"""
        if not source_url:
            # 默认一些公开的影视信息网站
            source_url = "https://example-drama-site.com/short-dramas"
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            async with self.session.get(source_url, headers=headers) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                dramas = []
                drama_elements = soup.find_all('div', class_='drama-item')  # 需要根据实际网站调整
                
                for element in drama_elements:
                    drama_data = self._extract_drama_info(element)
                    if drama_data:
                        dramas.append(drama_data)
                        
                return dramas
                
        except Exception as e:
            print(f"网页爬取失败: {e}")
            return []
    
    def _extract_drama_info(self, element) -> Dict:
        """从HTML元素提取剧目信息"""
        try:
            title = element.find('h3', class_='title')
            description = element.find('p', class_='description')
            tags = element.find_all('span', class_='tag')
            
            return {
                'title': title.text.strip() if title else '',
                'description': description.text.strip() if description else '',
                'tags': [tag.text.strip() for tag in tags],
                'source': 'web_scraper'
            }
        except Exception as e:
            print(f"数据提取失败: {e}")
            return {}

    async def collect_drama_detail(self, drama_url: str) -> Dict:
        """收集单个剧目详情页"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            async with self.session.get(drama_url, headers=headers) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                return self._extract_detail_info(soup)
                
        except Exception as e:
            print(f"详情页爬取失败: {e}")
            return {}
    
    def _extract_detail_info(self, soup) -> Dict:
        """提取详情页信息"""
        # 这里需要根据具体网站的HTML结构来调整
        return {
            'plot_summary': self._safe_extract(soup, 'div.plot-summary'),
            'character_list': self._extract_characters(soup),
            'episode_list': self._extract_episodes(soup)
        }
    
    def _safe_extract(self, soup, selector: str) -> str:
        """安全提取文本"""
        element = soup.select_one(selector)
        return element.text.strip() if element else ''
    
    def _extract_characters(self, soup) -> List[Dict]:
        """提取角色信息"""
        characters = []
        char_elements = soup.find_all('div', class_='character-item')
        
        for char_element in char_elements:
            name = self._safe_extract(char_element, '.char-name')
            role = self._safe_extract(char_element, '.char-role')
            actor = self._safe_extract(char_element, '.char-actor')
            
            if name:
                characters.append({
                    'name': name,
                    'role': role,
                    'actor': actor
                })
                
        return characters
    
    def _extract_episodes(self, soup) -> List[Dict]:
        """提取分集信息"""
        episodes = []
        ep_elements = soup.find_all('div', class_='episode-item')
        
        for i, ep_element in enumerate(ep_elements, 1):
            title = self._safe_extract(ep_element, '.ep-title')
            summary = self._safe_extract(ep_element, '.ep-summary')
            
            episodes.append({
                'episode_number': i,
                'title': title,
                'summary': summary
            })
                
        return episodes
