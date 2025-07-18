# config/config_manager.py
import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime
import copy

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """数据源配置"""
    enabled: bool = True
    priority: int = 1
    rate_limit: int = 5
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    custom_headers: Dict[str, str] = field(default_factory=dict)
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class ProcessingConfig:
    """处理配置"""
    validation_level: str = "moderate"  # strict, moderate, lenient
    batch_size: int = 10
    max_concurrent_jobs: int = 5
    enable_enhanced_nlp: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600
    quality_threshold: float = 7.0


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 27017
    database: str = "drama_database"
    collection: str = "dramas"
    username: Optional[str] = None
    password: Optional[str] = None
    connection_timeout: int = 30
    max_pool_size: int = 100


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 3600
    max_retries: int = 3


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    metrics_interval: int = 10
    performance_alerts: bool = True
    log_level: str = "INFO"
    metrics_retention_hours: int = 24
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'cpu_usage': 80.0,
        'memory_usage': 80.0,
        'processing_time': 30.0,
        'error_rate': 5.0
    })


@dataclass
class SchedulerConfig:
    """调度器配置"""
    enabled: bool = True
    collection_interval_hours: int = 6
    maintenance_hour: int = 2  # 凌晨2点维护
    max_collection_duration_hours: int = 4
    auto_retry_failed_jobs: bool = True
    cleanup_completed_jobs_hours: int = 24


@dataclass
class ExportConfig:
    """导出配置"""
    enabled: bool = True
    export_formats: List[str] = field(default_factory=lambda: ['json', 'csv'])
    output_directory: str = "./data/exports"
    include_metadata: bool = True
    compress_exports: bool = True
    max_export_size_mb: int = 100


@dataclass
class SystemConfig:
    """系统配置"""
    # 核心配置
    app_name: str = "Drama Collector"
    version: str = "2.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = False
    
    # 组件配置
    data_sources: Dict[str, DataSourceConfig] = field(default_factory=lambda: {
        'mock': DataSourceConfig(enabled=True, priority=3),
        'douban': DataSourceConfig(enabled=True, priority=1, rate_limit=2),
        'mydramalist': DataSourceConfig(enabled=True, priority=2, rate_limit=3)
    })
    
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    export: ExportConfig = field(default_factory=ExportConfig)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config: SystemConfig = SystemConfig()
        self.config_history: List[Dict[str, Any]] = []
        self.config_file = config_file or self._find_config_file()
        
        # 加载配置
        self._load_config()
        self._load_environment_variables()
        self._validate_config()
        
        logger.info(f"配置管理器初始化完成: {self.config_file}")
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        possible_paths = [
            "./config/config.yaml",
            "./config/config.yml", 
            "./config.yaml",
            "./config.yml",
            "/etc/drama_collector/config.yaml",
            os.path.expanduser("~/.drama_collector/config.yaml")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果没有找到，创建默认配置文件
        default_path = "./config/config.yaml"
        os.makedirs(os.path.dirname(default_path), exist_ok=True)
        self._save_config_to_file(default_path)
        return default_path
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            logger.warning(f"配置文件不存在: {self.config_file}，使用默认配置")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.endswith(('.yaml', '.yml')):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            if config_data:
                self._update_config_from_dict(config_data)
                logger.info(f"配置加载成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            logger.warning("使用默认配置")
    
    def _load_environment_variables(self):
        """从环境变量加载配置"""
        env_mappings = {
            'DRAMA_COLLECTOR_ENV': ('environment',),
            'DRAMA_COLLECTOR_DEBUG': ('debug', lambda x: x.lower() == 'true'),
            'MONGODB_HOST': ('database', 'host'),
            'MONGODB_PORT': ('database', 'port', int),
            'MONGODB_DATABASE': ('database', 'database'),
            'MONGODB_USERNAME': ('database', 'username'),
            'MONGODB_PASSWORD': ('database', 'password'),
            'REDIS_HOST': ('cache', 'host'),
            'REDIS_PORT': ('cache', 'port', int),
            'REDIS_PASSWORD': ('cache', 'password'),
            'LOG_LEVEL': ('monitoring', 'log_level'),
            'COLLECTION_INTERVAL_HOURS': ('scheduler', 'collection_interval_hours', int),
            'DOUBAN_API_KEY': ('data_sources', 'douban', 'api_key'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config_path, value)
    
    def _set_nested_config(self, path: tuple, value: Any):
        """设置嵌套配置值"""
        converter = None
        if len(path) > 1 and callable(path[-1]):
            converter = path[-1]
            path = path[:-1]
        elif len(path) > 2 and callable(path[-1]):
            converter = path[-1]
            path = path[:-1]
        
        if converter:
            try:
                value = converter(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"环境变量转换失败: {path} = {value}, 错误: {e}")
                return
        
        # 导航到配置对象
        current = self.config
        for key in path[:-1]:
            if hasattr(current, key):
                current = getattr(current, key)
            else:
                logger.warning(f"配置路径不存在: {'.'.join(path)}")
                return
        
        # 设置最终值
        final_key = path[-1]
        if hasattr(current, final_key):
            setattr(current, final_key, value)
            logger.info(f"环境变量配置已更新: {'.'.join(path)} = {value}")
        else:
            logger.warning(f"配置键不存在: {'.'.join(path)}")
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """从字典更新配置"""
        for key, value in config_data.items():
            if hasattr(self.config, key):
                current_attr = getattr(self.config, key)
                
                if isinstance(current_attr, dict) and isinstance(value, dict):
                    # 处理字典类型的配置
                    if key == 'data_sources':
                        for source_name, source_config in value.items():
                            if source_name in current_attr:
                                self._update_dataclass_from_dict(
                                    current_attr[source_name], source_config
                                )
                            else:
                                current_attr[source_name] = DataSourceConfig(**source_config)
                    else:
                        current_attr.update(value)
                        
                elif hasattr(current_attr, '__dataclass_fields__'):
                    # 处理dataclass类型的配置
                    self._update_dataclass_from_dict(current_attr, value)
                else:
                    # 处理简单类型的配置
                    setattr(self.config, key, value)
    
    def _update_dataclass_from_dict(self, dataclass_obj: Any, data: Dict[str, Any]):
        """更新dataclass对象"""
        for key, value in data.items():
            if hasattr(dataclass_obj, key):
                setattr(dataclass_obj, key, value)
    
    def _validate_config(self):
        """验证配置"""
        errors = []
        warnings = []
        
        # 验证数据库配置
        if not self.config.database.host:
            errors.append("数据库主机地址不能为空")
        
        if self.config.database.port <= 0 or self.config.database.port > 65535:
            errors.append("数据库端口无效")
        
        # 验证缓存配置
        if self.config.cache.enabled:
            if not self.config.cache.host:
                warnings.append("缓存已启用但主机地址为空")
        
        # 验证处理配置
        if self.config.processing.batch_size <= 0:
            errors.append("批处理大小必须大于0")
        
        if self.config.processing.validation_level not in ['strict', 'moderate', 'lenient']:
            errors.append("验证级别无效")
        
        # 验证调度器配置
        if self.config.scheduler.collection_interval_hours <= 0:
            errors.append("收集间隔必须大于0")
        
        # 验证导出配置
        valid_formats = ['json', 'csv', 'xlsx', 'xml']
        invalid_formats = [f for f in self.config.export.export_formats if f not in valid_formats]
        if invalid_formats:
            warnings.append(f"不支持的导出格式: {invalid_formats}")
        
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if warnings:
            warning_msg = "配置验证警告:\n" + "\n".join(f"- {warning}" for warning in warnings)
            logger.warning(warning_msg)
    
    def get_config(self) -> SystemConfig:
        """获取配置对象"""
        return copy.deepcopy(self.config)
    
    def get_data_source_config(self, source_name: str) -> Optional[DataSourceConfig]:
        """获取数据源配置"""
        return self.config.data_sources.get(source_name)
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        # 保存配置历史
        self.config_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'config': asdict(self.config)
        })
        
        # 应用更新
        self._update_config_from_dict(updates)
        
        # 重新验证
        self._validate_config()
        
        logger.info("配置已更新")
    
    def save_config(self):
        """保存配置到文件"""
        self._save_config_to_file(self.config_file)
    
    def _save_config_to_file(self, file_path: str):
        """保存配置到指定文件"""
        try:
            config_dict = asdict(self.config)
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    yaml.dump(config_dict, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
                else:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise
    
    def reload_config(self):
        """重新加载配置"""
        logger.info("重新加载配置...")
        self._load_config()
        self._load_environment_variables()
        self._validate_config()
        logger.info("配置重新加载完成")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            'app_name': self.config.app_name,
            'version': self.config.version,
            'environment': self.config.environment,
            'config_file': self.config_file,
            'enabled_data_sources': [
                name for name, config in self.config.data_sources.items() 
                if config.enabled
            ],
            'database_host': self.config.database.host,
            'cache_enabled': self.config.cache.enabled,
            'monitoring_enabled': self.config.monitoring.enabled,
            'scheduler_enabled': self.config.scheduler.enabled,
            'validation_level': self.config.processing.validation_level
        }
    
    def export_config(self, format_type: str = 'yaml') -> str:
        """导出配置"""
        config_dict = asdict(self.config)
        
        if format_type.lower() == 'yaml':
            return yaml.dump(config_dict, default_flow_style=False, 
                           allow_unicode=True, indent=2)
        elif format_type.lower() == 'json':
            return json.dumps(config_dict, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager


def get_config() -> SystemConfig:
    """获取系统配置"""
    return get_config_manager().get_config()


def reload_config():
    """重新加载配置"""
    global _config_manager
    if _config_manager:
        _config_manager.reload_config()