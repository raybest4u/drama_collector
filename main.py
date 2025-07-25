# main.py
import asyncio
from collectors.douban_collector import DoubanCollector
from collectors.mock_collector import MockCollector
from collectors.multi_source_collector import MultiSourceCollector
from collectors.web_scraper import WebScraper
from processors.text_processor import TextProcessor
from processors.enhanced_text_processor import EnhancedTextProcessor
from utils.data_validator import DataValidator, ValidationLevel, DataType
from utils.batch_processor import BatchProcessorManager
from utils.db_helper import DatabaseHelper
from typing import List, Dict
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollectionOrchestrator:
    def __init__(self):
        self.db = DatabaseHelper()
        self.text_processor = TextProcessor()
        self.enhanced_processor = EnhancedTextProcessor()
        self.validator = DataValidator(ValidationLevel.MODERATE)
        self.batch_manager = BatchProcessorManager()
        
    async def run_collection_pipeline(self):
        """运行完整的数据收集流程"""
        logger.info("开始数据收集流程...")
        
        # 步骤1：从多个数据源收集数据
        all_dramas = []
        
        # 使用多数据源收集器
        async with MultiSourceCollector() as multi_collector:
            logger.info("开始从多数据源收集数据...")
            
            # 获取数据源状态
            status = multi_collector.get_source_status()
            logger.info(f"可用数据源: {list(status.keys())}")
            
            # 收集剧目列表
            collected_dramas = await multi_collector.collect_drama_list(count=10)
            
            # 收集详细信息
            for drama in collected_dramas:
                detail = await multi_collector.collect_drama_detail(
                    drama['id'], 
                    preferred_source=drama.get('data_source')
                )
                drama.update(detail)
                
            all_dramas.extend(collected_dramas)
            logger.info(f"多数据源收集完成，共{len(collected_dramas)}部")
        
        # 豆瓣数据收集 (暂时禁用，API返回403)
        # async with DoubanCollector() as douban:
        #     logger.info("开始收集豆瓣数据...")
        #     douban_dramas = await douban.collect_drama_list(count=50)
        #     
        #     # 收集详细信息
        #     for drama in douban_dramas[:10]:  # MVP阶段先收集10部的详细信息
        #         detail = await douban.collect_drama_detail(drama['id'])
        #         drama.update(detail)
        #         
        #     all_dramas.extend(douban_dramas)
        #     logger.info(f"豆瓣数据收集完成，共{len(douban_dramas)}部")
        
        # 网页爬虫收集（可选）
        # async with WebScraper() as scraper:
        #     web_dramas = await scraper.collect_drama_list()
        #     all_dramas.extend(web_dramas)
        
        # 步骤2：数据验证和清洗
        logger.info("开始验证和清洗数据...")
        validated_dramas = self.validate_and_clean_dramas(all_dramas)
        
        # 步骤3：增强数据处理和结构化
        logger.info("开始增强处理数据...")
        processed_dramas = await self.process_dramas_enhanced(validated_dramas)
        
        # 步骤4：存储到数据库
        logger.info("开始存储数据...")
        saved_ids = await self.db.save_dramas_batch(processed_dramas)
        
        logger.info(f"数据收集完成！共处理{len(processed_dramas)}部剧目，存储ID: {saved_ids[:5]}...")
        
        return len(processed_dramas)
    
    def validate_and_clean_dramas(self, raw_dramas: List[Dict]) -> List[Dict]:
        """验证和清洗剧目数据"""
        validated_dramas = []
        
        for drama in raw_dramas:
            try:
                validation_result = self.validator.validate_drama_data(drama)
                
                if validation_result.is_valid:
                    validated_dramas.append(validation_result.cleaned_data)
                    if validation_result.warnings:
                        logger.warning(f"剧目 {drama.get('title', 'Unknown')} 验证警告: {validation_result.warnings}")
                else:
                    logger.error(f"剧目 {drama.get('title', 'Unknown')} 验证失败: {validation_result.errors}")
                    
            except Exception as e:
                logger.error(f"验证剧目失败: {drama.get('title', 'Unknown')}, 错误: {e}")
                
        logger.info(f"数据验证完成，有效数据: {len(validated_dramas)}/{len(raw_dramas)}")
        return validated_dramas
    
    async def process_dramas_enhanced(self, validated_dramas: List[Dict]) -> List[Dict]:
        """增强处理剧目数据"""
        processed_dramas = []
        
        for drama in validated_dramas:
            try:
                # 基础数据清洗
                cleaned_drama = self.clean_drama_data(drama)
                
                # 增强文本处理
                if cleaned_drama.get('summary'):
                    # 提取增强剧情点
                    enhanced_plot_points = self.enhanced_processor.extract_enhanced_plot_points(
                        cleaned_drama['summary']
                    )
                    cleaned_drama['enhanced_plot_points'] = enhanced_plot_points
                    
                    # 角色画像分析
                    character_profiles = self.enhanced_processor.extract_character_profiles(
                        cleaned_drama['summary']
                    )
                    cleaned_drama['character_profiles'] = character_profiles
                    
                    # 主题分析
                    drama_themes = self.enhanced_processor.analyze_drama_themes(
                        cleaned_drama['summary']
                    )
                    cleaned_drama['themes'] = drama_themes
                    
                    # 戏剧结构分析
                    if enhanced_plot_points:
                        dramatic_structure = self.enhanced_processor.extract_dramatic_structure(
                            enhanced_plot_points
                        )
                        cleaned_drama['dramatic_structure'] = dramatic_structure
                
                # 提取角色信息（保留原有逻辑）
                characters = self.extract_characters(cleaned_drama)
                cleaned_drama['characters'] = characters
                
                # 添加处理元数据
                cleaned_drama['data_source'] = drama.get('source_platform', 'unknown')
                cleaned_drama['processing_version'] = '2.0'  # 升级版本号
                cleaned_drama['processing_timestamp'] = datetime.utcnow().isoformat()
                
                processed_dramas.append(cleaned_drama)
                
            except Exception as e:
                logger.error(f"增强处理剧目失败: {drama.get('title', 'Unknown')}, 错误: {e}")
                continue
                
        return processed_dramas
    
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
                cleaned_drama['data_source'] = drama.get('source_platform', 'unknown')
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
