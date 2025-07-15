# orchestrator/drama_orchestrator.py
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import signal
import sys

from config.config_manager import get_config_manager, SystemConfig
from collectors.multi_source_collector import MultiSourceCollector
from utils.data_validator import DataValidator, ValidationLevel, DataType
from utils.batch_processor import BatchProcessorManager
from utils.performance_monitor import PerformanceMonitor, timing
from utils.cache_manager import get_cache_manager, CachedDataProcessor
from utils.db_helper import DatabaseHelper

logger = logging.getLogger(__name__)


class OrchestrationState(Enum):
    """编排状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    STORING = "storing"
    EXPORTING = "exporting"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class CollectionJob:
    """收集任务"""
    job_id: str
    state: OrchestrationState
    start_time: datetime
    end_time: Optional[datetime] = None
    total_collected: int = 0
    total_processed: int = 0
    total_stored: int = 0
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


class DramaOrchestrator:
    """戏剧数据收集编排器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        
        # 核心组件初始化
        self.db = DatabaseHelper()
        self.batch_manager = BatchProcessorManager()
        self.performance_monitor = PerformanceMonitor()
        self.cache_manager = None
        self.cached_processor = None
        
        # 状态管理
        self.state = OrchestrationState.IDLE
        self.current_job: Optional[CollectionJob] = None
        self.job_history: List[CollectionJob] = []
        self.is_running = False
        self.shutdown_requested = False
        
        # 组件状态
        self.components_initialized = False
        self.last_collection_time: Optional[datetime] = None
        self.next_scheduled_time: Optional[datetime] = None
        
        # 回调函数
        self.status_callbacks: List[Callable] = []
        
        logger.info("戏剧数据编排器初始化完成")
    
    async def initialize(self):
        """初始化所有组件"""
        if self.components_initialized:
            return
        
        self.state = OrchestrationState.INITIALIZING
        logger.info("开始初始化编排器组件...")
        
        try:
            # 初始化缓存管理器
            if self.config.cache.enabled:
                try:
                    self.cache_manager = await get_cache_manager()
                    self.cached_processor = CachedDataProcessor(self.cache_manager)
                    logger.info("缓存管理器初始化成功")
                except Exception as e:
                    logger.warning(f"缓存管理器初始化失败，将在无缓存模式下运行: {e}")
            
            # 初始化数据库索引
            await self.db.create_indexes()
            
            # 启动性能监控
            if self.config.monitoring.enabled:
                self.performance_monitor.start_monitoring()
                logger.info("性能监控已启动")
            
            # 计算下次调度时间
            self._calculate_next_schedule()
            
            self.components_initialized = True
            self.state = OrchestrationState.IDLE
            
            logger.info("编排器组件初始化完成")
            
        except Exception as e:
            self.state = OrchestrationState.ERROR
            logger.error(f"编排器初始化失败: {e}")
            raise
    
    async def start(self):
        """启动编排器"""
        if self.is_running:
            logger.warning("编排器已在运行中")
            return
        
        await self.initialize()
        
        self.is_running = True
        self.shutdown_requested = False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("戏剧数据编排器已启动")
        
        try:
            if self.config.scheduler.enabled:
                await self._run_scheduler_loop()
            else:
                logger.info("调度器已禁用，等待手动触发")
                await self._wait_for_manual_trigger()
                
        except Exception as e:
            logger.error(f"编排器运行错误: {e}")
            self.state = OrchestrationState.ERROR
        finally:
            await self.shutdown()
    
    async def run_collection_job(self, job_config: Optional[Dict[str, Any]] = None) -> str:
        """运行单次收集任务"""
        job_id = f"collection_{int(datetime.utcnow().timestamp())}"
        
        job = CollectionJob(
            job_id=job_id,
            state=OrchestrationState.COLLECTING,
            start_time=datetime.utcnow(),
            metadata=job_config or {}
        )
        
        self.current_job = job
        self.job_history.append(job)
        
        logger.info(f"开始执行收集任务: {job_id}")
        
        try:
            # 步骤1: 数据收集
            collected_data = await self._collect_data(job)
            job.total_collected = len(collected_data)
            
            # 步骤2: 数据处理
            job.state = OrchestrationState.PROCESSING
            processed_data = await self._process_data(collected_data, job)
            job.total_processed = len(processed_data)
            
            # 步骤3: 数据存储
            job.state = OrchestrationState.STORING
            stored_ids = await self._store_data(processed_data, job)
            job.total_stored = len(stored_ids)
            
            # 步骤4: 数据导出（可选）
            if self.config.export.enabled:
                job.state = OrchestrationState.EXPORTING
                await self._export_data(processed_data, job)
            
            job.state = OrchestrationState.IDLE
            job.end_time = datetime.utcnow()
            
            duration = (job.end_time - job.start_time).total_seconds()
            logger.info(f"收集任务完成: {job_id}, 耗时: {duration:.2f}s, "
                       f"收集: {job.total_collected}, 处理: {job.total_processed}, "
                       f"存储: {job.total_stored}")
            
            self.last_collection_time = job.end_time
            self._calculate_next_schedule()
            
            await self._notify_status_change(job)
            
            return job_id
            
        except Exception as e:
            job.state = OrchestrationState.ERROR
            job.end_time = datetime.utcnow()
            job.errors.append(str(e))
            
            logger.error(f"收集任务失败: {job_id}, 错误: {e}")
            
            await self._notify_status_change(job)
            raise
        
        finally:
            self.current_job = None
    
    @timing('data_collection')
    async def _collect_data(self, job: CollectionJob) -> List[Dict[str, Any]]:
        """数据收集阶段"""
        logger.info("开始数据收集...")
        
        # 检查缓存
        if self.cached_processor:
            cached_data = await self.cached_processor.get_cached_collection(
                'multi_source', job.metadata
            )
            if cached_data:
                logger.info(f"使用缓存数据: {len(cached_data)} 条")
                return cached_data
        
        # 从多数据源收集
        enabled_sources = [
            name for name, config in self.config.data_sources.items()
            if config.enabled
        ]
        
        async with MultiSourceCollector(enable_sources=enabled_sources) as collector:
            # 获取收集配置
            collection_config = job.metadata.get('collection', {})
            count = collection_config.get('count', 20)
            
            collected_data = await collector.collect_drama_list(count=count)
            
            # 收集详细信息
            for drama in collected_data:
                try:
                    detail = await collector.collect_drama_detail(
                        drama['id'], 
                        preferred_source=drama.get('data_source')
                    )
                    drama.update(detail)
                except Exception as e:
                    logger.warning(f"获取详情失败: {drama.get('id')}, 错误: {e}")
                    job.errors.append(f"详情获取失败: {drama.get('id')}")
        
        # 缓存结果
        if self.cached_processor and collected_data:
            await self.cached_processor.cache_collection_result(
                'multi_source', job.metadata, collected_data
            )
        
        logger.info(f"数据收集完成: {len(collected_data)} 条")
        return collected_data
    
    @timing('data_processing')
    async def _process_data(self, raw_data: List[Dict[str, Any]], 
                          job: CollectionJob) -> List[Dict[str, Any]]:
        """数据处理阶段"""
        logger.info("开始数据处理...")
        
        if not raw_data:
            return []
        
        # 使用批处理管理器
        processing_job_id = f"{job.job_id}_processing"
        
        batch_job_id = await self.batch_manager.process_dramas_batch(
            raw_data, 
            job_id=processing_job_id,
            batch_size=self.config.processing.batch_size
        )
        
        # 等待批处理完成
        while True:
            status = await self.batch_manager.get_job_status(batch_job_id)
            if not status:
                break
            
            if status['status'] in ['completed', 'failed']:
                break
            
            await asyncio.sleep(1)
        
        # 获取处理结果
        if status['status'] == 'completed':
            results = await self.batch_manager.processor.get_job_results(batch_job_id)
            
            # 过滤成功的结果
            processed_data = []
            for result in results:
                if result and result.get('status') == 'success':
                    processed_data.append(result['processed_data'])
        else:
            logger.error(f"批处理失败: {batch_job_id}")
            processed_data = []
        
        # 质量过滤
        if processed_data and self.config.processing.quality_threshold > 0:
            quality_filtered = [
                drama for drama in processed_data
                if drama.get('quality_score', 0) >= self.config.processing.quality_threshold
            ]
            
            filtered_count = len(processed_data) - len(quality_filtered)
            if filtered_count > 0:
                logger.info(f"质量过滤移除 {filtered_count} 条低质量数据")
            
            processed_data = quality_filtered
        
        logger.info(f"数据处理完成: {len(processed_data)} 条")
        return processed_data
    
    @timing('data_storage')
    async def _store_data(self, processed_data: List[Dict[str, Any]], 
                         job: CollectionJob) -> List[str]:
        """数据存储阶段"""
        logger.info("开始数据存储...")
        
        if not processed_data:
            return []
        
        try:
            stored_ids = await self.db.save_dramas_batch(processed_data)
            logger.info(f"数据存储完成: {len(stored_ids)} 条")
            return stored_ids
            
        except Exception as e:
            logger.error(f"数据存储失败: {e}")
            job.errors.append(f"数据存储失败: {e}")
            raise
    
    async def _export_data(self, processed_data: List[Dict[str, Any]], 
                          job: CollectionJob):
        """数据导出阶段"""
        logger.info("开始数据导出...")
        
        try:
            from export.data_exporter import get_export_manager
            
            export_manager = get_export_manager()
            
            # 导出配置
            export_formats = self.config.export.export_formats
            include_metadata = self.config.export.include_metadata
            compress = self.config.export.compress_exports
            
            # 执行导出
            export_results = await export_manager.export_data(
                data=processed_data,
                formats=export_formats,
                compress=compress,
                include_metadata=include_metadata,
                filename=f"drama_collection_{job.job_id}"
            )
            
            # 记录导出结果
            export_metadata = {
                'job_id': job.job_id,
                'timestamp': datetime.utcnow().isoformat(),
                'count': len(processed_data),
                'export_files': [
                    {
                        'format': meta.format_type,
                        'file_path': meta.file_path,
                        'file_size': meta.file_size_bytes,
                        'checksum': meta.checksum
                    }
                    for meta in export_results
                ]
            }
            
            job.metadata['export'] = export_metadata
            logger.info(f"数据导出完成: {len(export_results)} 个文件")
            
        except Exception as e:
            logger.error(f"数据导出失败: {e}")
            job.errors.append(f"数据导出失败: {e}")
            # 继续执行，不中断任务
    
    async def _run_scheduler_loop(self):
        """运行调度循环"""
        logger.info("调度器循环已启动")
        
        while self.is_running and not self.shutdown_requested:
            try:
                current_time = datetime.utcnow()
                
                # 检查是否需要执行收集
                if self._should_run_collection(current_time):
                    logger.info("触发定时收集任务")
                    await self.run_collection_job({
                        'trigger': 'scheduled',
                        'collection': {'count': 50}
                    })
                
                # 检查是否需要维护
                if self._should_run_maintenance(current_time):
                    await self._run_maintenance()
                
                # 等待下次检查
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"调度器循环错误: {e}")
                await asyncio.sleep(60)
    
    def _should_run_collection(self, current_time: datetime) -> bool:
        """判断是否应该运行收集"""
        if not self.config.scheduler.enabled:
            return False
        
        if self.current_job:  # 已有任务在运行
            return False
        
        if self.next_scheduled_time and current_time >= self.next_scheduled_time:
            return True
        
        return False
    
    def _should_run_maintenance(self, current_time: datetime) -> bool:
        """判断是否应该运行维护"""
        maintenance_hour = self.config.scheduler.maintenance_hour
        return (current_time.hour == maintenance_hour and 
                current_time.minute == 0 and
                not self.current_job)
    
    def _calculate_next_schedule(self):
        """计算下次调度时间"""
        if not self.config.scheduler.enabled:
            self.next_scheduled_time = None
            return
        
        interval_hours = self.config.scheduler.collection_interval_hours
        
        if self.last_collection_time:
            self.next_scheduled_time = self.last_collection_time + timedelta(hours=interval_hours)
        else:
            # 首次运行，立即执行
            self.next_scheduled_time = datetime.utcnow()
        
        logger.info(f"下次调度时间: {self.next_scheduled_time}")
    
    async def _run_maintenance(self):
        """运行维护任务"""
        logger.info("开始维护任务...")
        
        self.state = OrchestrationState.MAINTENANCE
        
        try:
            # 清理完成的任务
            await self.batch_manager.processor.cleanup_completed_jobs(
                keep_hours=self.config.scheduler.cleanup_completed_jobs_hours
            )
            
            # 清理缓存（如果启用）
            if self.cache_manager:
                # 可以添加缓存清理逻辑
                pass
            
            # 重置性能统计
            self.performance_monitor.reset_stats()
            
            logger.info("维护任务完成")
            
        except Exception as e:
            logger.error(f"维护任务失败: {e}")
        
        finally:
            self.state = OrchestrationState.IDLE
    
    async def _wait_for_manual_trigger(self):
        """等待手动触发"""
        while self.is_running and not self.shutdown_requested:
            await asyncio.sleep(1)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，开始优雅关闭...")
        self.shutdown_requested = True
    
    async def shutdown(self):
        """关闭编排器"""
        if not self.is_running:
            return
        
        logger.info("开始关闭编排器...")
        self.state = OrchestrationState.STOPPING
        
        # 等待当前任务完成
        if self.current_job:
            logger.info("等待当前任务完成...")
            timeout = 300  # 5分钟超时
            for _ in range(timeout):
                if not self.current_job:
                    break
                await asyncio.sleep(1)
        
        # 关闭组件
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()
        
        if self.batch_manager:
            await self.batch_manager.shutdown()
        
        if self.cache_manager:
            await self.cache_manager.disconnect()
        
        self.is_running = False
        self.state = OrchestrationState.STOPPED
        
        logger.info("编排器已关闭")
    
    def add_status_callback(self, callback: Callable):
        """添加状态变化回调"""
        self.status_callbacks.append(callback)
    
    async def _notify_status_change(self, job: CollectionJob):
        """通知状态变化"""
        for callback in self.status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception as e:
                logger.error(f"状态回调执行失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取编排器状态"""
        current_job_info = None
        if self.current_job:
            current_job_info = asdict(self.current_job)
            # 转换datetime对象为字符串
            if current_job_info['start_time']:
                current_job_info['start_time'] = current_job_info['start_time'].isoformat()
            if current_job_info['end_time']:
                current_job_info['end_time'] = current_job_info['end_time'].isoformat()
        
        return {
            'state': self.state.value,
            'is_running': self.is_running,
            'components_initialized': self.components_initialized,
            'last_collection_time': self.last_collection_time.isoformat() if self.last_collection_time else None,
            'next_scheduled_time': self.next_scheduled_time.isoformat() if self.next_scheduled_time else None,
            'current_job': current_job_info,
            'total_jobs': len(self.job_history),
            'successful_jobs': len([j for j in self.job_history if not j.errors]),
            'failed_jobs': len([j for j in self.job_history if j.errors]),
            'config_summary': self.config_manager.get_config_summary()
        }


# 全局编排器实例
_orchestrator: Optional[DramaOrchestrator] = None


def get_orchestrator() -> DramaOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = DramaOrchestrator()
    
    return _orchestrator