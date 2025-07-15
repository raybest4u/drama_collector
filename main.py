# main.py
import asyncio
from collectors.douban_collector import DoubanCollector
from collectors.web_scraper import WebScraper
from processors.text_processor import TextProcessor
from utils.db_helper import DatabaseHelper
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollectionOrchestrator:
    def __init__(self):
        self.db = DatabaseHelper()
        self.text_processor = TextProcessor()
        
    async def run_collection_pipeline(self):
        """运行完整的数据收集流程"""
        logger.info("开始数据收集流程...")
        
        # 步骤1：从多个数据源收集数据
        all_dramas = []
        
        # 豆瓣数据收集
        async with DoubanCollector() as douban:
            logger.info("开始收集豆瓣数据...")
            douban_dramas = await douban.collect_drama_list(count=50)
            
            # 收集详细信息
            for drama in douban_dramas[:10]:  # MVP阶段先收集10部的详细信息
                detail = await douban.collect_drama_detail(drama['id'])
                drama.update(detail)
                
            all_dramas.extend(douban_dramas)
            logger.info(f"豆瓣数据收集完成，共{len(douban_dramas)}部")
        
        # 网页爬虫收集（可选）
        # async with WebScraper() as scraper:
        #     web_dramas = await scraper.collect_drama_list()
        #     all_dramas.extend(web_dramas)
        
        # 步骤2：数据处理和结构化
        logger.info("开始处理数据...")
        processed_dramas = await self.process_dramas(all_dramas)
        
        # 步骤3：存储到数据库
        logger.info("开始存储数据...")
        saved_ids = await self.db.save_dramas_batch(processed_dramas)
        
        logger.info(f"数据收集完成！共处理{len(processed_dramas)}部剧目，存储ID: {saved_ids[:5]}...")
        
        return len(processed_dramas)
    
    async def process_dramas(self, raw_dramas: List[Dict]) -> List[Dict]:
        """处理和结构化剧目数据"""
        processed = []
        
        for drama in raw_dramas:
            try:
                # 基础数据清洗
                cleaned_drama = self.clean_drama_data(drama)
                
                # 提取剧情点
                if cleaned_drama.get('summary'):
                    plot_points = self.text_processor.extract_plot_points(
                        cleaned_drama['summary']
                    )
                    cleaned_drama['plot_points'] = plot_points
                
                # 提取角色信息
                characters = self.extract_characters(cleaned_drama)
                cleaned_drama['characters'] = characters
                
                # 添加元数据
                cleaned_drama['data_source'] = 'douban'
                cleaned_drama['processing_version'] = '1.0'
                
                processed.append(cleaned_drama)
                
            except Exception as e:
                logger.error(f"处理剧目失败: {drama.get('title', 'Unknown')}, 错误: {e}")
                continue
                
        return processed
    
    def clean_drama_data(self, drama: Dict) -> Dict:
        """清洗剧目数据"""
        return {
            'id': str(drama.get('id', '')),
            'title': drama.get('title', '').strip(),
            'original_title': drama.get('original_title', '').strip(),
            'summary': drama.get('summary', '').strip(),
            'genre': drama.get('genres', []),
            'tags': drama.get('tags', []),
            'year': drama.get('year'),
            'rating': float(drama.get('rating', 0)),
            'ratings_count': int(drama.get('ratings_count', 0)),
            'total_episodes': drama.get('episodes_count', 1),
            'duration': drama.get('duration', []),
            'countries': drama.get('countries', []),
            'languages': drama.get('languages', []),
            'directors': drama.get('directors', []),
            'writers': drama.get('writers', []),
            'casts': drama.get('casts', []),
            'source_platform': 'unknown'
        }
    
    def extract_characters(self, drama: Dict) -> List[Dict]:
        """提取角色信息"""
        characters = []
        casts = drama.get('casts', [])
        
        for i, cast_name in enumerate(casts[:6]):  # 最多取前6个角色
            role_type = 'male_lead' if i == 0 else 'female_lead' if i == 1 else 'supporting'
            
            characters.append({
                'id': f"char_{drama['id']}_{i}",
                'name': cast_name,
                'actor': cast_name,  # 演员名
                'role': role_type,
                'description': '',
                'personality_traits': []
            })
            
        return characters

async def main():
    """主函数"""
    orchestrator = DataCollectionOrchestrator()
    
    # 创建数据库索引
    await orchestrator.db.create_indexes()
    
    # 运行收集流程
    total_count = await orchestrator.run_collection_pipeline()
    
    print(f"✅ 数据收集完成！共收集了 {total_count} 部短剧数据")

if __name__ == "__main__":
    asyncio.run(main())
