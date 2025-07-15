# utils/batch_processor.py
import asyncio
import logging
from typing import List, Dict, Any, Callable, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import time
import json
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class BatchJob:
    """批处理任务"""
    job_id: str
    data: List[Dict[str, Any]]
    processor_func: Callable
    batch_size: int = 10
    max_retries: int = 3
    timeout: float = 300.0
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: List[Any] = None
    errors: List[str] = None
    progress: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.results is None:
            self.results = []
        if self.errors is None:
            self.errors = []


class BatchProcessor:
    """批处理器，支持大数据集的并行处理"""
    
    def __init__(self, max_concurrent_jobs: int = 5, 
                 max_workers: int = 10,
                 checkpoint_interval: int = 100):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_workers = max_workers
        self.checkpoint_interval = checkpoint_interval
        
        self.active_jobs: Dict[str, BatchJob] = {}
        self.completed_jobs: Dict[str, BatchJob] = {}
        self.job_queue: List[BatchJob] = []
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.is_processing = False
        
        logger.info(f"批处理器初始化: 最大并发任务数={max_concurrent_jobs}, 最大工作线程={max_workers}")
    
    async def submit_job(self, job_id: str, 
                        data: List[Dict[str, Any]], 
                        processor_func: Callable,
                        batch_size: int = 10,
                        max_retries: int = 3,
                        timeout: float = 300.0) -> str:
        """提交批处理任务"""
        
        if job_id in self.active_jobs or job_id in self.completed_jobs:
            raise ValueError(f"任务ID {job_id} 已存在")
        
        job = BatchJob(
            job_id=job_id,
            data=data,
            processor_func=processor_func,
            batch_size=batch_size,
            max_retries=max_retries,
            timeout=timeout
        )
        
        self.job_queue.append(job)
        logger.info(f"任务 {job_id} 已提交，数据量: {len(data)}")
        
        # 如果处理器未运行，启动它
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        job = self.active_jobs.get(job_id) or self.completed_jobs.get(job_id)
        
        if not job:
            # 检查队列中的任务
            for queued_job in self.job_queue:
                if queued_job.job_id == job_id:
                    job = queued_job
                    break
        
        if not job:
            return None
        
        return {
            'job_id': job.job_id,
            'status': job.status.value,
            'progress': job.progress,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'data_count': len(job.data),
            'results_count': len(job.results),
            'errors_count': len(job.errors),
            'batch_size': job.batch_size
        }
    
    async def get_job_results(self, job_id: str) -> Optional[List[Any]]:
        """获取任务结果"""
        job = self.completed_jobs.get(job_id)
        return job.results if job else None
    
    async def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        # 从队列中移除
        self.job_queue = [job for job in self.job_queue if job.job_id != job_id]
        
        # 标记活动任务为失败
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.status = ProcessingStatus.FAILED
            job.errors.append("任务被用户取消")
            job.completed_at = datetime.utcnow()
            
            self.completed_jobs[job_id] = job
            del self.active_jobs[job_id]
            
            logger.info(f"任务 {job_id} 已取消")
            return True
        
        return False
    
    async def _process_queue(self):
        """处理任务队列"""
        self.is_processing = True
        
        try:
            while self.job_queue or self.active_jobs:
                # 启动新任务
                while (len(self.active_jobs) < self.max_concurrent_jobs and 
                       self.job_queue):
                    job = self.job_queue.pop(0)
                    self.active_jobs[job.job_id] = job
                    asyncio.create_task(self._process_job(job))
                
                # 等待一段时间再检查
                await asyncio.sleep(1)
                
        finally:
            self.is_processing = False
            logger.info("批处理队列处理完成")
    
    async def _process_job(self, job: BatchJob):
        """处理单个任务"""
        job.status = ProcessingStatus.PROCESSING
        job.started_at = datetime.utcnow()
        
        logger.info(f"开始处理任务 {job.job_id}")
        
        try:
            # 分批处理数据
            batches = self._create_batches(job.data, job.batch_size)
            total_batches = len(batches)
            
            for i, batch in enumerate(batches):
                batch_start_time = time.time()
                
                try:
                    # 处理当前批次
                    batch_results = await self._process_batch(
                        batch, job.processor_func, job.timeout
                    )
                    
                    job.results.extend(batch_results)
                    job.progress = (i + 1) / total_batches
                    
                    batch_time = time.time() - batch_start_time
                    logger.debug(f"任务 {job.job_id} 批次 {i+1}/{total_batches} 完成，耗时: {batch_time:.2f}s")
                    
                    # 检查点保存
                    if (i + 1) % self.checkpoint_interval == 0:
                        await self._save_checkpoint(job)
                
                except Exception as e:
                    error_msg = f"批次 {i+1} 处理失败: {str(e)}"
                    job.errors.append(error_msg)
                    logger.error(error_msg)
                    
                    # 如果错误过多，终止任务
                    if len(job.errors) > job.max_retries:
                        raise Exception(f"任务失败次数超过限制: {len(job.errors)}")
            
            # 任务完成
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 1.0
            
            total_time = (job.completed_at - job.started_at).total_seconds()
            logger.info(f"任务 {job.job_id} 完成，总耗时: {total_time:.2f}s，处理数据: {len(job.results)}")
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.errors.append(f"任务失败: {str(e)}")
            logger.error(f"任务 {job.job_id} 失败: {str(e)}")
        
        finally:
            # 移动到完成队列
            if job.job_id in self.active_jobs:
                self.completed_jobs[job.job_id] = job
                del self.active_jobs[job.job_id]
    
    async def _process_batch(self, batch: List[Dict[str, Any]], 
                           processor_func: Callable,
                           timeout: float) -> List[Any]:
        """处理单个批次"""
        tasks = []
        
        for item in batch:
            if asyncio.iscoroutinefunction(processor_func):
                task = processor_func(item)
            else:
                # 在线程池中运行同步函数
                task = asyncio.get_event_loop().run_in_executor(
                    self.executor, processor_func, item
                )
            tasks.append(task)
        
        # 等待所有任务完成
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # 处理结果和异常
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"单项处理失败: {str(result)}")
                    processed_results.append(None)
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error(f"批次处理超时: {timeout}s")
            raise
    
    def _create_batches(self, data: List[Any], batch_size: int) -> List[List[Any]]:
        """将数据分批"""
        batches = []
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batches.append(batch)
        return batches
    
    async def _save_checkpoint(self, job: BatchJob):
        """保存检查点"""
        checkpoint_data = {
            'job_id': job.job_id,
            'progress': job.progress,
            'results_count': len(job.results),
            'errors_count': len(job.errors),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 这里可以保存到文件或数据库
        logger.debug(f"保存检查点: {job.job_id} - {job.progress:.2%}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        total_jobs = len(self.active_jobs) + len(self.completed_jobs) + len(self.job_queue)
        
        completed_jobs = [job for job in self.completed_jobs.values() 
                         if job.status == ProcessingStatus.COMPLETED]
        failed_jobs = [job for job in self.completed_jobs.values() 
                      if job.status == ProcessingStatus.FAILED]
        
        stats = {
            'total_jobs': total_jobs,
            'active_jobs': len(self.active_jobs),
            'queued_jobs': len(self.job_queue),
            'completed_jobs': len(completed_jobs),
            'failed_jobs': len(failed_jobs),
            'success_rate': len(completed_jobs) / len(self.completed_jobs) if self.completed_jobs else 0,
            'total_items_processed': sum(len(job.results) for job in completed_jobs),
            'average_processing_time': self._calculate_average_processing_time(completed_jobs)
        }
        
        return stats
    
    def _calculate_average_processing_time(self, jobs: List[BatchJob]) -> float:
        """计算平均处理时间"""
        if not jobs:
            return 0
        
        total_time = 0
        for job in jobs:
            if job.started_at and job.completed_at:
                total_time += (job.completed_at - job.started_at).total_seconds()
        
        return total_time / len(jobs)
    
    async def cleanup_completed_jobs(self, keep_hours: int = 24):
        """清理已完成的任务"""
        cutoff_time = datetime.utcnow().timestamp() - (keep_hours * 3600)
        
        jobs_to_remove = []
        for job_id, job in self.completed_jobs.items():
            if job.completed_at and job.completed_at.timestamp() < cutoff_time:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.completed_jobs[job_id]
        
        if jobs_to_remove:
            logger.info(f"清理了 {len(jobs_to_remove)} 个过期任务")
    
    async def shutdown(self):
        """关闭批处理器"""
        logger.info("正在关闭批处理器...")
        
        # 等待活动任务完成
        while self.active_jobs:
            logger.info(f"等待 {len(self.active_jobs)} 个活动任务完成...")
            await asyncio.sleep(2)
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        logger.info("批处理器已关闭")


class BatchProcessorManager:
    """批处理器管理器"""
    
    def __init__(self):
        self.processor = BatchProcessor()
        self.predefined_processors = {}
        self._register_default_processors()
    
    def _register_default_processors(self):
        """注册默认处理器"""
        
        async def drama_processing_pipeline(drama_data: Dict[str, Any]) -> Dict[str, Any]:
            """剧目数据处理流水线"""
            from utils.data_validator import DataValidator, ValidationLevel, DataType
            from processors.enhanced_text_processor import EnhancedTextProcessor
            
            # 数据验证和清洗
            validator = DataValidator(ValidationLevel.MODERATE)
            validation_result = validator.validate_drama_data(drama_data)
            
            if not validation_result.is_valid:
                return {
                    'status': 'failed',
                    'errors': validation_result.errors,
                    'original_data': drama_data
                }
            
            cleaned_data = validation_result.cleaned_data
            
            # 增强文本处理
            text_processor = EnhancedTextProcessor()
            
            if cleaned_data.get('summary'):
                # 提取剧情点
                plot_points = text_processor.extract_enhanced_plot_points(cleaned_data['summary'])
                cleaned_data['enhanced_plot_points'] = plot_points
                
                # 角色画像
                character_profiles = text_processor.extract_character_profiles(cleaned_data['summary'])
                cleaned_data['character_profiles'] = character_profiles
                
                # 主题分析
                themes = text_processor.analyze_drama_themes(cleaned_data['summary'])
                cleaned_data['themes'] = themes
                
                # 戏剧结构
                if plot_points:
                    structure = text_processor.extract_dramatic_structure(plot_points)
                    cleaned_data['dramatic_structure'] = structure
            
            return {
                'status': 'success',
                'processed_data': cleaned_data,
                'quality_score': validation_result.quality_score,
                'processing_metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'processor_version': '1.0'
                }
            }
        
        self.predefined_processors['drama_pipeline'] = drama_processing_pipeline
    
    async def process_dramas_batch(self, dramas: List[Dict[str, Any]], 
                                  job_id: str = None,
                                  batch_size: int = 10) -> str:
        """批量处理剧目数据"""
        if job_id is None:
            job_id = f"drama_batch_{int(time.time())}"
        
        return await self.processor.submit_job(
            job_id=job_id,
            data=dramas,
            processor_func=self.predefined_processors['drama_pipeline'],
            batch_size=batch_size,
            timeout=600.0  # 10分钟超时
        )
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return await self.processor.get_job_status(job_id)
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return await self.processor.get_processing_stats()
    
    async def shutdown(self):
        """关闭管理器"""
        await self.processor.shutdown()