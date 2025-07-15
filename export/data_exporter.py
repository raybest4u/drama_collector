# export/data_exporter.py
import os
import csv
import json
import logging
import gzip
import zipfile
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import pandas as pd
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ExportMetadata:
    """导出元数据"""
    export_id: str
    format_type: str
    file_path: str
    file_size_bytes: int
    record_count: int
    created_at: datetime
    compression: Optional[str] = None
    checksum: Optional[str] = None
    schema_version: str = "2.0"


class BaseExporter(ABC):
    """导出器基类"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    async def export(self, data: List[Dict[str, Any]], 
                    filename: str, **kwargs) -> ExportMetadata:
        """导出数据"""
        pass
    
    def _generate_filename(self, base_name: str, extension: str) -> str:
        """生成文件名"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp}.{extension}"
    
    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()


class JSONExporter(BaseExporter):
    """JSON导出器"""
    
    async def export(self, data: List[Dict[str, Any]], 
                    filename: str = None, 
                    indent: int = 2,
                    ensure_ascii: bool = False) -> ExportMetadata:
        """导出为JSON格式"""
        
        if not filename:
            filename = self._generate_filename("dramas", "json")
        
        file_path = self.output_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii, 
                         default=str, separators=(',', ': '))
            
            metadata = ExportMetadata(
                export_id=f"json_{int(datetime.utcnow().timestamp())}",
                format_type="json",
                file_path=str(file_path),
                file_size_bytes=file_path.stat().st_size,
                record_count=len(data),
                created_at=datetime.utcnow(),
                checksum=self._calculate_checksum(str(file_path))
            )
            
            logger.info(f"JSON导出完成: {filename}, {len(data)} 条记录")
            return metadata
            
        except Exception as e:
            logger.error(f"JSON导出失败: {e}")
            raise


class CSVExporter(BaseExporter):
    """CSV导出器"""
    
    async def export(self, data: List[Dict[str, Any]], 
                    filename: str = None,
                    flatten_nested: bool = True) -> ExportMetadata:
        """导出为CSV格式"""
        
        if not data:
            raise ValueError("没有数据可导出")
        
        if not filename:
            filename = self._generate_filename("dramas", "csv")
        
        file_path = self.output_dir / filename
        
        try:
            # 处理嵌套数据
            if flatten_nested:
                processed_data = self._flatten_data(data)
            else:
                processed_data = data
            
            # 获取所有可能的字段
            all_fields = set()
            for record in processed_data:
                all_fields.update(record.keys())
            
            fieldnames = sorted(list(all_fields))
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in processed_data:
                    # 处理缺失字段
                    row = {field: record.get(field, '') for field in fieldnames}
                    # 转换复杂类型为字符串
                    for key, value in row.items():
                        if isinstance(value, (list, dict)):
                            row[key] = json.dumps(value, ensure_ascii=False)
                    
                    writer.writerow(row)
            
            metadata = ExportMetadata(
                export_id=f"csv_{int(datetime.utcnow().timestamp())}",
                format_type="csv",
                file_path=str(file_path),
                file_size_bytes=file_path.stat().st_size,
                record_count=len(data),
                created_at=datetime.utcnow(),
                checksum=self._calculate_checksum(str(file_path))
            )
            
            logger.info(f"CSV导出完成: {filename}, {len(data)} 条记录")
            return metadata
            
        except Exception as e:
            logger.error(f"CSV导出失败: {e}")
            raise
    
    def _flatten_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """扁平化嵌套数据"""
        flattened_data = []
        
        for record in data:
            flattened_record = {}
            self._flatten_dict(record, flattened_record)
            flattened_data.append(flattened_record)
        
        return flattened_data
    
    def _flatten_dict(self, obj: Any, flattened: Dict[str, Any], prefix: str = ""):
        """递归扁平化字典"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}_{key}" if prefix else key
                self._flatten_dict(value, flattened, new_key)
        elif isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                # 处理字典列表
                for i, item in enumerate(obj[:5]):  # 限制前5个元素
                    self._flatten_dict(item, flattened, f"{prefix}_{i}")
            else:
                # 简单列表转为字符串
                flattened[prefix] = json.dumps(obj, ensure_ascii=False)
        else:
            flattened[prefix] = str(obj) if obj is not None else ""


class ExcelExporter(BaseExporter):
    """Excel导出器"""
    
    async def export(self, data: List[Dict[str, Any]], 
                    filename: str = None,
                    sheet_name: str = "Drama Data") -> ExportMetadata:
        """导出为Excel格式"""
        
        if not filename:
            filename = self._generate_filename("dramas", "xlsx")
        
        file_path = self.output_dir / filename
        
        try:
            # 使用pandas处理Excel导出
            df = pd.json_normalize(data)
            
            # 处理复杂数据类型
            for col in df.columns:
                df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) 
                                      if isinstance(x, (list, dict)) else x)
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 添加元数据工作表
                metadata_df = pd.DataFrame([{
                    'Export Time': datetime.utcnow().isoformat(),
                    'Record Count': len(data),
                    'Schema Version': '2.0',
                    'Data Source': 'Drama Collector System'
                }])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            metadata = ExportMetadata(
                export_id=f"excel_{int(datetime.utcnow().timestamp())}",
                format_type="xlsx",
                file_path=str(file_path),
                file_size_bytes=file_path.stat().st_size,
                record_count=len(data),
                created_at=datetime.utcnow(),
                checksum=self._calculate_checksum(str(file_path))
            )
            
            logger.info(f"Excel导出完成: {filename}, {len(data)} 条记录")
            return metadata
            
        except Exception as e:
            logger.error(f"Excel导出失败: {e}")
            raise


class XMLExporter(BaseExporter):
    """XML导出器"""
    
    async def export(self, data: List[Dict[str, Any]], 
                    filename: str = None,
                    root_element: str = "dramas",
                    item_element: str = "drama") -> ExportMetadata:
        """导出为XML格式"""
        
        if not filename:
            filename = self._generate_filename("dramas", "xml")
        
        file_path = self.output_dir / filename
        
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.Element(root_element)
            root.set("export_time", datetime.utcnow().isoformat())
            root.set("count", str(len(data)))
            
            for record in data:
                item = ET.SubElement(root, item_element)
                self._dict_to_xml(record, item)
            
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding='utf-8', xml_declaration=True)
            
            metadata = ExportMetadata(
                export_id=f"xml_{int(datetime.utcnow().timestamp())}",
                format_type="xml",
                file_path=str(file_path),
                file_size_bytes=file_path.stat().st_size,
                record_count=len(data),
                created_at=datetime.utcnow(),
                checksum=self._calculate_checksum(str(file_path))
            )
            
            logger.info(f"XML导出完成: {filename}, {len(data)} 条记录")
            return metadata
            
        except Exception as e:
            logger.error(f"XML导出失败: {e}")
            raise
    
    def _dict_to_xml(self, data: Any, parent: 'ET.Element'):
        """将字典转换为XML元素"""
        import xml.etree.ElementTree as ET
        
        if isinstance(data, dict):
            for key, value in data.items():
                # 清理XML标签名
                clean_key = str(key).replace(' ', '_').replace('-', '_')
                element = ET.SubElement(parent, clean_key)
                self._dict_to_xml(value, element)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                element = ET.SubElement(parent, f"item_{i}")
                self._dict_to_xml(item, element)
        else:
            parent.text = str(data) if data is not None else ""


class CompressedExporter:
    """压缩导出器"""
    
    def __init__(self, base_exporter: BaseExporter):
        self.base_exporter = base_exporter
    
    async def export_compressed(self, data: List[Dict[str, Any]], 
                               filename: str = None,
                               compression_type: str = "gzip",
                               **kwargs) -> ExportMetadata:
        """导出压缩文件"""
        
        # 先执行基础导出
        base_metadata = await self.base_exporter.export(data, filename, **kwargs)
        
        # 压缩文件
        original_path = Path(base_metadata.file_path)
        
        if compression_type == "gzip":
            compressed_path = original_path.with_suffix(original_path.suffix + ".gz")
            
            with open(original_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
        
        elif compression_type == "zip":
            compressed_path = original_path.with_suffix(".zip")
            
            with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(original_path, original_path.name)
        
        else:
            raise ValueError(f"不支持的压缩类型: {compression_type}")
        
        # 删除原文件
        original_path.unlink()
        
        # 更新元数据
        base_metadata.file_path = str(compressed_path)
        base_metadata.file_size_bytes = compressed_path.stat().st_size
        base_metadata.compression = compression_type
        base_metadata.checksum = self.base_exporter._calculate_checksum(str(compressed_path))
        
        logger.info(f"压缩导出完成: {compressed_path.name}, 压缩类型: {compression_type}")
        return base_metadata


class DataExportManager:
    """数据导出管理器"""
    
    def __init__(self, output_dir: str = "./data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化导出器
        self.exporters = {
            'json': JSONExporter(str(self.output_dir)),
            'csv': CSVExporter(str(self.output_dir)),
            'xlsx': ExcelExporter(str(self.output_dir)),
            'xml': XMLExporter(str(self.output_dir))
        }
        
        self.export_history: List[ExportMetadata] = []
        
        logger.info(f"数据导出管理器初始化完成: {self.output_dir}")
    
    async def export_data(self, data: List[Dict[str, Any]], 
                         formats: List[str] = None,
                         compress: bool = False,
                         include_metadata: bool = True,
                         **kwargs) -> List[ExportMetadata]:
        """导出数据到多种格式"""
        
        if not data:
            raise ValueError("没有数据可导出")
        
        if formats is None:
            formats = ['json', 'csv']
        
        results = []
        
        for format_type in formats:
            if format_type not in self.exporters:
                logger.warning(f"不支持的导出格式: {format_type}")
                continue
            
            try:
                exporter = self.exporters[format_type]
                
                # 添加元数据到数据中
                export_data = data.copy()
                if include_metadata:
                    export_metadata = {
                        'export_info': {
                            'timestamp': datetime.utcnow().isoformat(),
                            'format': format_type,
                            'record_count': len(data),
                            'schema_version': '2.0',
                            'exported_by': 'Drama Collector System'
                        }
                    }
                    export_data.insert(0, export_metadata)
                
                if compress:
                    compressed_exporter = CompressedExporter(exporter)
                    metadata = await compressed_exporter.export_compressed(
                        export_data, compression_type="gzip", **kwargs
                    )
                else:
                    metadata = await exporter.export(export_data, **kwargs)
                
                results.append(metadata)
                self.export_history.append(metadata)
                
            except Exception as e:
                logger.error(f"导出格式 {format_type} 失败: {e}")
                continue
        
        logger.info(f"导出完成: {len(results)} 个文件")
        return results
    
    async def export_filtered_data(self, data: List[Dict[str, Any]], 
                                  filters: Dict[str, Any],
                                  **kwargs) -> List[ExportMetadata]:
        """导出过滤后的数据"""
        
        filtered_data = self._apply_filters(data, filters)
        
        logger.info(f"数据过滤: {len(data)} -> {len(filtered_data)} 条记录")
        
        return await self.export_data(filtered_data, **kwargs)
    
    def _apply_filters(self, data: List[Dict[str, Any]], 
                      filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用过滤条件"""
        filtered_data = data
        
        # 年份过滤
        if 'year_range' in filters:
            min_year, max_year = filters['year_range']
            filtered_data = [
                item for item in filtered_data
                if min_year <= item.get('year', 0) <= max_year
            ]
        
        # 评分过滤
        if 'min_rating' in filters:
            min_rating = filters['min_rating']
            filtered_data = [
                item for item in filtered_data
                if item.get('rating', 0) >= min_rating
            ]
        
        # 类型过滤
        if 'genres' in filters:
            target_genres = filters['genres']
            filtered_data = [
                item for item in filtered_data
                if any(genre in item.get('genres', []) for genre in target_genres)
            ]
        
        # 数据源过滤
        if 'data_sources' in filters:
            target_sources = filters['data_sources']
            filtered_data = [
                item for item in filtered_data
                if item.get('data_source') in target_sources
            ]
        
        # 质量分数过滤
        if 'min_quality_score' in filters:
            min_score = filters['min_quality_score']
            filtered_data = [
                item for item in filtered_data
                if item.get('quality_score', 0) >= min_score
            ]
        
        return filtered_data
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """获取导出历史"""
        return [asdict(metadata) for metadata in self.export_history]
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """获取导出统计"""
        if not self.export_history:
            return {}
        
        format_counts = {}
        total_records = 0
        total_size = 0
        
        for metadata in self.export_history:
            format_type = metadata.format_type
            format_counts[format_type] = format_counts.get(format_type, 0) + 1
            total_records += metadata.record_count
            total_size += metadata.file_size_bytes
        
        return {
            'total_exports': len(self.export_history),
            'format_distribution': format_counts,
            'total_records_exported': total_records,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'latest_export': self.export_history[-1].created_at.isoformat() if self.export_history else None
        }
    
    async def cleanup_old_exports(self, keep_days: int = 7):
        """清理旧导出文件"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        removed_files = []
        for metadata in self.export_history.copy():
            if metadata.created_at < cutoff_date:
                file_path = Path(metadata.file_path)
                if file_path.exists():
                    file_path.unlink()
                    removed_files.append(str(file_path))
                
                self.export_history.remove(metadata)
        
        if removed_files:
            logger.info(f"清理了 {len(removed_files)} 个旧导出文件")
        
        return removed_files


# 全局导出管理器实例
_export_manager: Optional[DataExportManager] = None


def get_export_manager() -> DataExportManager:
    """获取全局导出管理器实例"""
    global _export_manager
    
    if _export_manager is None:
        _export_manager = DataExportManager()
    
    return _export_manager