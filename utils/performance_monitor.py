# utils/performance_monitor.py
import time
import logging
import asyncio
import psutil
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class ProcessingStats:
    """处理统计"""
    total_processed: int = 0
    total_failed: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    throughput: float = 0.0  # 每秒处理数
    
    def update(self, processing_time: float, success: bool = True):
        """更新统计"""
        if success:
            self.total_processed += 1
        else:
            self.total_failed += 1
        
        self.total_time += processing_time
        self.min_time = min(self.min_time, processing_time)
        self.max_time = max(self.max_time, processing_time)
        
        total_operations = self.total_processed + self.total_failed
        if total_operations > 0:
            self.average_time = self.total_time / total_operations
            self.throughput = self.total_processed / self.total_time if self.total_time > 0 else 0


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.processing_stats: Dict[str, ProcessingStats] = defaultdict(ProcessingStats)
        self.system_metrics: Dict[str, Any] = {}
        
        # 监控线程控制
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 10  # 10秒
        
        # 性能阈值
        self.thresholds = {
            'cpu_usage': 80.0,      # CPU使用率
            'memory_usage': 80.0,    # 内存使用率
            'processing_time': 30.0, # 处理时间（秒）
            'error_rate': 5.0,       # 错误率（%）
            'throughput_min': 1.0    # 最小吞吐量
        }
        
        logger.info("性能监控器初始化完成")
    
    def start_monitoring(self):
        """启动监控"""
        if self.monitoring_active:
            logger.warning("监控已在运行中")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system_metrics)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        logger.info("性能监控已停止")
    
    def record_metric(self, name: str, value: float, unit: str = "", 
                     tags: Dict[str, str] = None):
        """记录指标"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.metrics_history.append(metric)
        logger.debug(f"记录指标: {name}={value}{unit}")
    
    def timing(self, operation_name: str, tags: Dict[str, str] = None):
        """计时装饰器"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    # 更新统计
                    self.processing_stats[operation_name].update(processing_time, success)
                    
                    # 记录指标
                    self.record_metric(
                        f"{operation_name}_duration",
                        processing_time,
                        "seconds",
                        tags
                    )
                    
                    # 检查性能阈值
                    self._check_performance_thresholds(operation_name, processing_time, success)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    # 更新统计
                    self.processing_stats[operation_name].update(processing_time, success)
                    
                    # 记录指标
                    self.record_metric(
                        f"{operation_name}_duration",
                        processing_time,
                        "seconds",
                        tags
                    )
                    
                    # 检查性能阈值
                    self._check_performance_thresholds(operation_name, processing_time, success)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    def get_processing_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """获取处理统计"""
        if operation_name:
            if operation_name in self.processing_stats:
                return asdict(self.processing_stats[operation_name])
            else:
                return {}
        
        return {name: asdict(stats) for name, stats in self.processing_stats.items()}
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        return self.system_metrics.copy()
    
    def get_recent_metrics(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """获取最近的指标"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_metrics = [
            asdict(metric) for metric in self.metrics_history
            if metric.timestamp >= cutoff_time
        ]
        
        return recent_metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {
            'system_metrics': self.get_system_metrics(),
            'processing_stats': self.get_processing_stats(),
            'total_metrics_recorded': len(self.metrics_history),
            'monitoring_active': self.monitoring_active,
            'alerts': self._check_all_thresholds()
        }
        
        return summary
    
    def _monitor_system_metrics(self):
        """监控系统指标（在后台线程中运行）"""
        while self.monitoring_active:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                self.system_metrics['cpu_usage'] = cpu_percent
                self.record_metric('system_cpu_usage', cpu_percent, '%')
                
                # 内存使用率
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.system_metrics['memory_usage'] = memory_percent
                self.system_metrics['memory_available'] = memory.available
                self.record_metric('system_memory_usage', memory_percent, '%')
                
                # 磁盘使用率
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.system_metrics['disk_usage'] = disk_percent
                self.record_metric('system_disk_usage', disk_percent, '%')
                
                # 网络IO
                net_io = psutil.net_io_counters()
                self.system_metrics['network_bytes_sent'] = net_io.bytes_sent
                self.system_metrics['network_bytes_recv'] = net_io.bytes_recv
                
                # 进程信息
                current_process = psutil.Process()
                self.system_metrics['process_memory'] = current_process.memory_info().rss
                self.system_metrics['process_cpu'] = current_process.cpu_percent()
                
                self.system_metrics['timestamp'] = datetime.utcnow().isoformat()
                
            except Exception as e:
                logger.error(f"系统指标监控错误: {e}")
            
            time.sleep(self.monitoring_interval)
    
    def _check_performance_thresholds(self, operation_name: str, 
                                    processing_time: float, success: bool):
        """检查性能阈值"""
        alerts = []
        
        # 检查处理时间
        if processing_time > self.thresholds['processing_time']:
            alerts.append({
                'type': 'slow_processing',
                'operation': operation_name,
                'value': processing_time,
                'threshold': self.thresholds['processing_time'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # 检查错误率
        stats = self.processing_stats[operation_name]
        total_ops = stats.total_processed + stats.total_failed
        if total_ops >= 10:  # 至少10次操作后才检查错误率
            error_rate = (stats.total_failed / total_ops) * 100
            if error_rate > self.thresholds['error_rate']:
                alerts.append({
                    'type': 'high_error_rate',
                    'operation': operation_name,
                    'value': error_rate,
                    'threshold': self.thresholds['error_rate'],
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # 检查吞吐量
        if stats.throughput < self.thresholds['throughput_min'] and stats.total_processed > 5:
            alerts.append({
                'type': 'low_throughput',
                'operation': operation_name,
                'value': stats.throughput,
                'threshold': self.thresholds['throughput_min'],
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # 记录告警
        for alert in alerts:
            logger.warning(f"性能告警: {alert}")
            self.record_metric(
                f"alert_{alert['type']}",
                alert['value'],
                alert.get('unit', ''),
                {'operation': operation_name}
            )
    
    def _check_all_thresholds(self) -> List[Dict[str, Any]]:
        """检查所有阈值"""
        alerts = []
        
        # 检查系统CPU
        cpu_usage = self.system_metrics.get('cpu_usage', 0)
        if cpu_usage > self.thresholds['cpu_usage']:
            alerts.append({
                'type': 'high_cpu_usage',
                'value': cpu_usage,
                'threshold': self.thresholds['cpu_usage'],
                'severity': 'warning'
            })
        
        # 检查系统内存
        memory_usage = self.system_metrics.get('memory_usage', 0)
        if memory_usage > self.thresholds['memory_usage']:
            alerts.append({
                'type': 'high_memory_usage',
                'value': memory_usage,
                'threshold': self.thresholds['memory_usage'],
                'severity': 'warning'
            })
        
        return alerts
    
    def export_metrics(self, format_type: str = 'json') -> str:
        """导出指标"""
        if format_type == 'json':
            data = {
                'metrics': [asdict(metric) for metric in self.metrics_history],
                'processing_stats': self.get_processing_stats(),
                'system_metrics': self.system_metrics,
                'export_timestamp': datetime.utcnow().isoformat()
            }
            return json.dumps(data, indent=2, default=str)
        
        # 可以添加其他格式，如Prometheus格式
        raise ValueError(f"不支持的导出格式: {format_type}")
    
    def reset_stats(self):
        """重置统计"""
        self.processing_stats.clear()
        self.metrics_history.clear()
        logger.info("性能统计已重置")


# 全局性能监控器实例
global_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return global_monitor


def timing(operation_name: str, tags: Dict[str, str] = None):
    """计时装饰器（便捷函数）"""
    return global_monitor.timing(operation_name, tags)


def record_metric(name: str, value: float, unit: str = "", tags: Dict[str, str] = None):
    """记录指标（便捷函数）"""
    global_monitor.record_metric(name, value, unit, tags)


class MetricsCollector:
    """指标收集器（用于特定组件）"""
    
    def __init__(self, component_name: str, monitor: PerformanceMonitor = None):
        self.component_name = component_name
        self.monitor = monitor or global_monitor
        
    def record(self, metric_name: str, value: float, unit: str = ""):
        """记录组件指标"""
        full_name = f"{self.component_name}_{metric_name}"
        self.monitor.record_metric(
            full_name, 
            value, 
            unit, 
            {'component': self.component_name}
        )
    
    def timing(self, operation_name: str):
        """组件计时装饰器"""
        full_name = f"{self.component_name}_{operation_name}"
        return self.monitor.timing(
            full_name, 
            {'component': self.component_name}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取组件统计"""
        all_stats = self.monitor.get_processing_stats()
        component_stats = {}
        
        prefix = f"{self.component_name}_"
        for name, stats in all_stats.items():
            if name.startswith(prefix):
                short_name = name[len(prefix):]
                component_stats[short_name] = stats
        
        return component_stats