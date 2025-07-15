#!/usr/bin/env python3
# start_api.py
"""
Drama Collector API启动脚本
"""
import os
import sys
import logging
import uvicorn

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    """启动API服务器"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("启动 Drama Collector API 服务器...")
    
    # 检查环境变量
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    
    logger.info(f"服务器配置: {host}:{port}, reload={reload}")
    
    try:
        # 启动服务器
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"启动API服务器失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()