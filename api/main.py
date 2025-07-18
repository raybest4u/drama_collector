# api/main.py
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Path as PathParam
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

from orchestrator.drama_orchestrator import get_orchestrator, OrchestrationState
from config.config_manager import get_config_manager
from export.data_exporter import get_export_manager
from utils.performance_monitor import PerformanceMonitor
from utils.db_helper import DatabaseHelper

logger = logging.getLogger(__name__)


# Pydantic Models
class JobConfig(BaseModel):
    """收集任务配置"""
    trigger: str = "manual"
    collection: Dict[str, Any] = Field(default_factory=lambda: {"count": 20})
    export_enabled: bool = True
    quality_threshold: Optional[float] = None


class ExportRequest(BaseModel):
    """导出请求"""
    formats: List[str] = ["json", "csv"]
    compress: bool = False
    include_metadata: bool = True
    filters: Optional[Dict[str, Any]] = None


class ConfigUpdate(BaseModel):
    """配置更新请求"""
    updates: Dict[str, Any]
    save_to_file: bool = False


class SystemStatus(BaseModel):
    """系统状态响应"""
    orchestrator: Dict[str, Any]
    components: Dict[str, bool]
    performance: Dict[str, Any]
    timestamp: str


# Global instances
orchestrator = None
config_manager = None
export_manager = None
db_helper = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global orchestrator, config_manager, export_manager, db_helper
    
    logger.info("启动 Drama Collector API...")
    
    # 初始化组件
    orchestrator = get_orchestrator()
    config_manager = get_config_manager()
    export_manager = get_export_manager()
    db_helper = DatabaseHelper()
    
    await orchestrator.initialize()
    
    yield
    
    # 清理资源
    logger.info("关闭 Drama Collector API...")
    if orchestrator:
        await orchestrator.shutdown()


# 创建FastAPI应用
app = FastAPI(
    title="Drama Collector API",
    description="短剧数据收集系统的RESTful API",
    version="2.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加静态文件服务
dashboard_path = Path(__file__).parent.parent / "dashboard"
if dashboard_path.exists():
    app.mount("/static", StaticFiles(directory=str(dashboard_path / "static")), name="static")


# 依赖注入
def get_orchestrator_instance():
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="编排器未初始化")
    return orchestrator


def get_config_manager_instance():
    if config_manager is None:
        raise HTTPException(status_code=503, detail="配置管理器未初始化")
    return config_manager


def get_export_manager_instance():
    if export_manager is None:
        raise HTTPException(status_code=503, detail="导出管理器未初始化")
    return export_manager


def get_db_helper_instance():
    if db_helper is None:
        raise HTTPException(status_code=503, detail="数据库助手未初始化")
    return db_helper


# API路由
@app.get("/", response_model=Dict[str, str])
async def root():
    """API根路径"""
    return {
        "message": "Drama Collector API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "dashboard": "/dashboard"
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Web Dashboard"""
    dashboard_file = Path(__file__).parent.parent / "dashboard" / "templates" / "index.html"
    
    if not dashboard_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return HTMLResponse(content=content)


@app.get("/health", response_model=Dict[str, Any])
async def health_check(
    orchestrator_inst = Depends(get_orchestrator_instance),
    config_mgr = Depends(get_config_manager_instance)
):
    """健康检查"""
    try:
        # 检查组件状态
        orchestrator_status = orchestrator_inst.get_status()
        config_summary = config_mgr.get_config_summary()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "orchestrator_state": orchestrator_status["state"],
            "components_initialized": orchestrator_status["components_initialized"],
            "environment": config_summary["environment"]
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail=f"系统不健康: {str(e)}")


@app.get("/status", response_model=SystemStatus)
async def get_system_status(orchestrator_inst = Depends(get_orchestrator_instance)):
    """获取系统状态"""
    try:
        orchestrator_status = orchestrator_inst.get_status()
        
        # 获取性能监控信息
        performance_stats = {}
        if hasattr(orchestrator_inst, 'performance_monitor'):
            performance_stats = orchestrator_inst.performance_monitor.get_performance_summary()
        
        return SystemStatus(
            orchestrator=orchestrator_status,
            components={
                "orchestrator_initialized": orchestrator_status["components_initialized"],
                "cache_enabled": orchestrator_inst.cache_manager is not None,
                "performance_monitoring": orchestrator_inst.performance_monitor is not None
            },
            performance=performance_stats,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/start", response_model=Dict[str, str])
async def start_collection_job(
    job_config: JobConfig,
    background_tasks: BackgroundTasks,
    orchestrator_inst = Depends(get_orchestrator_instance)
):
    """启动收集任务"""
    try:
        if orchestrator_inst.current_job:
            raise HTTPException(
                status_code=409, 
                detail="已有任务在运行中"
            )
        
        # 在后台启动任务
        job_id = await orchestrator_inst.run_collection_job(job_config.dict())
        
        return {
            "job_id": job_id,
            "status": "started",
            "message": "收集任务已启动"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动收集任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/current", response_model=Dict[str, Any])
async def get_current_job(orchestrator_inst = Depends(get_orchestrator_instance)):
    """获取当前任务状态"""
    current_job = orchestrator_inst.current_job
    
    if not current_job:
        return {"message": "当前无运行中的任务"}
    
    # 转换任务信息为可序列化格式
    job_info = {
        "job_id": current_job.job_id,
        "state": current_job.state.value,
        "start_time": current_job.start_time.isoformat(),
        "end_time": current_job.end_time.isoformat() if current_job.end_time else None,
        "total_collected": current_job.total_collected,
        "total_processed": current_job.total_processed,
        "total_stored": current_job.total_stored,
        "errors": current_job.errors,
        "metadata": current_job.metadata
    }
    
    return job_info


@app.get("/jobs/history", response_model=List[Dict[str, Any]])
async def get_job_history(
    limit: int = Query(default=10, ge=1, le=100),
    orchestrator_inst = Depends(get_orchestrator_instance)
):
    """获取任务历史"""
    job_history = orchestrator_inst.job_history[-limit:]
    
    return [
        {
            "job_id": job.job_id,
            "state": job.state.value,
            "start_time": job.start_time.isoformat(),
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "total_collected": job.total_collected,
            "total_processed": job.total_processed,
            "total_stored": job.total_stored,
            "errors_count": len(job.errors),
            "metadata": job.metadata
        }
        for job in job_history
    ]


@app.post("/orchestrator/start", response_model=Dict[str, str])
async def start_orchestrator(
    background_tasks: BackgroundTasks,
    orchestrator_inst = Depends(get_orchestrator_instance)
):
    """启动编排器"""
    try:
        if orchestrator_inst.is_running:
            return {"message": "编排器已在运行中", "status": "running"}
        
        # 在后台启动编排器
        background_tasks.add_task(orchestrator_inst.start)
        
        return {"message": "编排器启动中", "status": "starting"}
        
    except Exception as e:
        logger.error(f"启动编排器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrator/stop", response_model=Dict[str, str])
async def stop_orchestrator(orchestrator_inst = Depends(get_orchestrator_instance)):
    """停止编排器"""
    try:
        orchestrator_inst.shutdown_requested = True
        return {"message": "编排器停止中", "status": "stopping"}
        
    except Exception as e:
        logger.error(f"停止编排器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config", response_model=Dict[str, Any])
async def get_config(config_mgr = Depends(get_config_manager_instance)):
    """获取配置"""
    try:
        return config_mgr.get_config_summary()
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/update", response_model=Dict[str, str])
async def update_config(
    config_update: ConfigUpdate,
    config_mgr = Depends(get_config_manager_instance)
):
    """更新配置"""
    try:
        config_mgr.update_config(config_update.updates)
        
        if config_update.save_to_file:
            config_mgr.save_config()
        
        return {"message": "配置更新成功", "status": "updated"}
        
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/reload", response_model=Dict[str, str])
async def reload_config(config_mgr = Depends(get_config_manager_instance)):
    """重新加载配置"""
    try:
        config_mgr.reload_config()
        return {"message": "配置重新加载成功", "status": "reloaded"}
        
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export", response_model=List[Dict[str, Any]])
async def export_data(
    export_request: ExportRequest,
    limit: int = Query(default=100, ge=1, le=1000),
    export_mgr = Depends(get_export_manager_instance),
    db = Depends(get_db_helper_instance)
):
    """导出数据"""
    try:
        # 获取数据
        dramas = await db.get_all_dramas(limit=limit)
        
        if not dramas:
            raise HTTPException(status_code=404, detail="没有数据可导出")
        
        # 应用过滤器（如果有）
        if export_request.filters:
            filtered_data = await export_mgr.export_filtered_data(
                dramas, 
                export_request.filters,
                formats=export_request.formats,
                compress=export_request.compress,
                include_metadata=export_request.include_metadata
            )
        else:
            filtered_data = await export_mgr.export_data(
                dramas,
                formats=export_request.formats,
                compress=export_request.compress,
                include_metadata=export_request.include_metadata
            )
        
        return [
            {
                "export_id": meta.export_id,
                "format": meta.format_type,
                "file_path": meta.file_path,
                "file_size": meta.file_size_bytes,
                "record_count": meta.record_count,
                "created_at": meta.created_at.isoformat(),
                "checksum": meta.checksum
            }
            for meta in filtered_data
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export/history", response_model=List[Dict[str, Any]])
async def get_export_history(export_mgr = Depends(get_export_manager_instance)):
    """获取导出历史"""
    try:
        return export_mgr.get_export_history()
    except Exception as e:
        logger.error(f"获取导出历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export/statistics", response_model=Dict[str, Any])
async def get_export_statistics(export_mgr = Depends(get_export_manager_instance)):
    """获取导出统计"""
    try:
        return export_mgr.get_export_statistics()
    except Exception as e:
        logger.error(f"获取导出统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dramas", response_model=List[Dict[str, Any]])
async def get_dramas(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    db = Depends(get_db_helper_instance)
):
    """获取剧目列表"""
    try:
        dramas = await db.get_all_dramas(limit=limit)
        
        # 简化返回的数据结构（移除敏感信息）
        simplified_dramas = []
        for drama in dramas[skip:skip+limit]:
            simplified_drama = {
                "id": str(drama.get("_id", "")),
                "title": drama.get("title", ""),
                "year": drama.get("year", 0),
                "rating": drama.get("rating", 0),
                "genre": drama.get("genre", []),
                "data_source": drama.get("data_source", ""),
                "quality_score": drama.get("quality_score", 0),
                "created_at": drama.get("created_at", "").isoformat() if drama.get("created_at") else None
            }
            simplified_dramas.append(simplified_drama)
        
        return simplified_dramas
        
    except Exception as e:
        logger.error(f"获取剧目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dramas/{drama_id}", response_model=Dict[str, Any])
async def get_drama_detail(
    drama_id: str = PathParam(..., description="剧目ID"),
    db = Depends(get_db_helper_instance)
):
    """获取剧目详情"""
    try:
        from bson import ObjectId
        
        # 查找剧目
        drama = await db.dramas_collection.find_one({"_id": ObjectId(drama_id)})
        
        if not drama:
            raise HTTPException(status_code=404, detail="剧目不存在")
        
        # 转换ObjectId为字符串
        drama["_id"] = str(drama["_id"])
        
        # 转换日期为字符串
        if drama.get("created_at"):
            drama["created_at"] = drama["created_at"].isoformat()
        if drama.get("updated_at"):
            drama["updated_at"] = drama["updated_at"].isoformat()
        
        return drama
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取剧目详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/performance/stats", response_model=Dict[str, Any])
async def get_performance_stats(orchestrator_inst = Depends(get_orchestrator_instance)):
    """获取性能统计"""
    try:
        if hasattr(orchestrator_inst, 'performance_monitor') and orchestrator_inst.performance_monitor:
            return orchestrator_inst.performance_monitor.get_performance_summary()
        else:
            return {"message": "性能监控未启用"}
            
    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误"}
    )


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 启动服务器
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )