# utils/db_helper.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
import asyncio
from datetime import datetime

class DatabaseHelper:
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client.drama_database
        self.dramas_collection = self.db.dramas
        self.characters_collection = self.db.characters
        
    async def save_drama(self, drama_data: Dict) -> str:
        """保存剧目数据"""
        drama_data['created_at'] = datetime.now()
        drama_data['updated_at'] = datetime.now()
        
        result = await self.dramas_collection.insert_one(drama_data)
        return str(result.inserted_id)
    
    async def save_dramas_batch(self, dramas: List[Dict]) -> List[str]:
        """批量保存剧目"""
        if not dramas:
            return []
            
        now = datetime.now()
        for drama in dramas:
            drama['created_at'] = now
            drama['updated_at'] = now
            
        result = await self.dramas_collection.insert_many(dramas)
        return [str(id) for id in result.inserted_ids]
    
    async def find_drama_by_title(self, title: str) -> Optional[Dict]:
        """根据标题查找剧目"""
        return await self.dramas_collection.find_one({'title': title})
    
    async def update_drama(self, drama_id: str, update_data: Dict) -> bool:
        """更新剧目数据"""
        update_data['updated_at'] = datetime.now()
        result = await self.dramas_collection.update_one(
            {'_id': drama_id}, 
            {'$set': update_data}
        )
        return result.modified_count > 0
    
    async def get_all_dramas(self, limit: int = 100) -> List[Dict]:
        """获取所有剧目"""
        cursor = self.dramas_collection.find().limit(limit)
        return await cursor.to_list(length=limit)
    
    async def create_indexes(self):
        """创建数据库索引"""
        try:
            # 基础索引
            await self.dramas_collection.create_index("title")
            await self.dramas_collection.create_index("year")
            await self.dramas_collection.create_index("data_source")
            await self.dramas_collection.create_index("rating")
            await self.dramas_collection.create_index("created_at")
            await self.dramas_collection.create_index("source_platform")
            
            # 复合索引（优化常见查询）
            await self.dramas_collection.create_index([("year", -1), ("rating", -1)])
            await self.dramas_collection.create_index([("data_source", 1), ("created_at", -1)])
            await self.dramas_collection.create_index([("genre", 1), ("year", -1)])
            await self.dramas_collection.create_index([("processing_version", 1), ("updated_at", -1)])
            
            # 文本搜索索引
            await self.dramas_collection.create_index([("title", "text"), ("summary", "text")])
            
            # 稀疏索引（如果有重复数据，跳过唯一约束）
            try:
                await self.dramas_collection.create_index("id", unique=True, sparse=True)
            except Exception as e:
                print(f"ID索引创建跳过（可能存在重复数据）: {e}")
                await self.dramas_collection.create_index("id", sparse=True)
            
            await self.dramas_collection.create_index("themes.primary_themes.theme", sparse=True)
            await self.dramas_collection.create_index("tags")
            
            print("数据库索引创建完成")
            
        except Exception as e:
            print(f"索引创建警告: {e}")
            print("继续运行...")
