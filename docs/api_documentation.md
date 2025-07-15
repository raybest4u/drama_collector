# Drama Collector API 文档

## 概述

Drama Collector API 是短剧数据收集系统的RESTful API接口，提供完整的系统控制、监控和数据管理功能。

## 基本信息

- **基础URL**: `http://localhost:8000`
- **API版本**: 2.0.0
- **文档地址**: `http://localhost:8000/docs` (Swagger UI)
- **RedDoc文档**: `http://localhost:8000/redoc`

## 启动API服务器

```bash
# 方法1: 使用启动脚本
python start_api.py

# 方法2: 直接使用uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 方法3: 设置环境变量
export API_HOST=0.0.0.0
export API_PORT=8000
export API_RELOAD=true
python start_api.py
```

## API端点分类

### 1. 系统状态和健康检查

#### GET `/`
- **描述**: API根路径，返回基本信息
- **响应示例**:
```json
{
  "message": "Drama Collector API",
  "version": "2.0.0",
  "status": "running",
  "docs": "/docs"
}
```

#### GET `/health`
- **描述**: 健康检查端点
- **响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "orchestrator_state": "idle",
  "components_initialized": true,
  "environment": "development"
}
```

#### GET `/status`
- **描述**: 获取详细系统状态
- **响应**: 包含编排器状态、组件状态、性能信息的完整系统状态

### 2. 任务管理

#### POST `/jobs/start`
- **描述**: 启动数据收集任务
- **请求体**:
```json
{
  "trigger": "manual",
  "collection": {
    "count": 20
  },
  "export_enabled": true,
  "quality_threshold": 7.0
}
```
- **响应示例**:
```json
{
  "job_id": "collection_1642234200",
  "status": "started",
  "message": "收集任务已启动"
}
```

#### GET `/jobs/current`
- **描述**: 获取当前运行中的任务状态
- **响应**: 当前任务的详细信息（如果有）

#### GET `/jobs/history?limit=10`
- **描述**: 获取任务历史记录
- **查询参数**:
  - `limit`: 返回记录数量限制 (1-100，默认10)
- **响应**: 任务历史记录列表

### 3. 编排器控制

#### POST `/orchestrator/start`
- **描述**: 启动编排器（后台运行）
- **响应示例**:
```json
{
  "message": "编排器启动中",
  "status": "starting"
}
```

#### POST `/orchestrator/stop`
- **描述**: 停止编排器
- **响应示例**:
```json
{
  "message": "编排器停止中",
  "status": "stopping"
}
```

### 4. 配置管理

#### GET `/config`
- **描述**: 获取当前配置摘要
- **响应**: 系统配置概览

#### POST `/config/update`
- **描述**: 更新系统配置
- **请求体**:
```json
{
  "updates": {
    "processing": {
      "batch_size": 20
    }
  },
  "save_to_file": true
}
```

#### POST `/config/reload`
- **描述**: 重新加载配置文件
- **响应**: 重新加载状态确认

### 5. 数据导出

#### POST `/export`
- **描述**: 导出剧目数据
- **查询参数**:
  - `limit`: 导出数据条数限制 (1-1000，默认100)
- **请求体**:
```json
{
  "formats": ["json", "csv"],
  "compress": false,
  "include_metadata": true,
  "filters": {
    "year_range": [2020, 2024],
    "min_rating": 7.0
  }
}
```
- **响应**: 导出文件的元数据列表

#### GET `/export/history`
- **描述**: 获取导出历史记录
- **响应**: 所有导出操作的历史记录

#### GET `/export/statistics`
- **描述**: 获取导出统计信息
- **响应**: 导出操作的统计数据

### 6. 剧目数据

#### GET `/dramas?limit=20&skip=0`
- **描述**: 获取剧目列表
- **查询参数**:
  - `limit`: 返回数量限制 (1-100，默认20)
  - `skip`: 跳过记录数 (默认0)
- **响应**: 简化的剧目信息列表

#### GET `/dramas/{drama_id}`
- **描述**: 获取特定剧目的详细信息
- **路径参数**:
  - `drama_id`: MongoDB ObjectId
- **响应**: 完整的剧目详细信息

### 7. 性能监控

#### GET `/performance/stats`
- **描述**: 获取系统性能统计
- **响应**: 当前性能指标（如果启用监控）

## 数据过滤器

在导出API中，支持以下过滤条件：

```json
{
  "filters": {
    "year_range": [2020, 2024],        // 年份范围
    "min_rating": 7.0,                 // 最低评分
    "genres": ["romance", "drama"],     // 类型筛选
    "data_sources": ["douban", "mock"],// 数据源筛选
    "min_quality_score": 8.0           // 最低质量分数
  }
}
```

## 错误处理

API使用标准HTTP状态码：

- `200`: 成功
- `404`: 资源不存在
- `409`: 冲突（如任务已在运行）
- `422`: 请求参数验证失败
- `500`: 内部服务器错误
- `503`: 服务不可用

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

## 认证和安全

当前版本为开发环境配置，未启用认证。生产环境建议：

1. 启用API密钥认证
2. 配置CORS允许的域名
3. 使用HTTPS
4. 实施速率限制

## 使用示例

### Python客户端示例

```python
import requests

# 基础配置
API_BASE = "http://localhost:8000"

# 启动收集任务
response = requests.post(f"{API_BASE}/jobs/start", json={
    "collection": {"count": 50},
    "export_enabled": True
})
job_info = response.json()
print(f"任务启动: {job_info['job_id']}")

# 检查任务状态
response = requests.get(f"{API_BASE}/jobs/current")
current_job = response.json()
print(f"当前任务: {current_job}")

# 导出数据
response = requests.post(f"{API_BASE}/export", json={
    "formats": ["json", "csv"],
    "compress": True,
    "filters": {"min_rating": 8.0}
})
export_results = response.json()
print(f"导出完成: {len(export_results)} 个文件")
```

### cURL示例

```bash
# 健康检查
curl -X GET "http://localhost:8000/health"

# 启动收集任务
curl -X POST "http://localhost:8000/jobs/start" \
  -H "Content-Type: application/json" \
  -d '{"collection": {"count": 30}}'

# 获取剧目列表
curl -X GET "http://localhost:8000/dramas?limit=10"

# 导出数据
curl -X POST "http://localhost:8000/export" \
  -H "Content-Type: application/json" \
  -d '{"formats": ["json"], "compress": false}'
```

## 监控和日志

API服务器提供详细的日志记录：

- 请求/响应日志
- 错误追踪
- 性能指标
- 系统状态变化

日志级别可通过环境变量 `LOG_LEVEL` 配置。

## 部署建议

### 开发环境
```bash
python start_api.py
```

### 生产环境
```bash
# 使用gunicorn部署
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用Docker部署
docker build -t drama-collector-api .
docker run -p 8000:8000 drama-collector-api
```

## 故障排除

### 常见问题

1. **503 Service Unavailable**
   - 检查MongoDB和Redis是否运行
   - 验证数据库连接配置

2. **任务启动失败**
   - 检查系统配置
   - 查看编排器状态

3. **导出失败**
   - 确认输出目录存在且可写
   - 检查磁盘空间

### 调试技巧

1. 启用调试模式：`export API_RELOAD=true`
2. 查看详细日志：访问 `/logs` 端点（如果实现）
3. 监控性能：定期检查 `/performance/stats`

---

更多详细信息请访问 Swagger UI 文档: `http://localhost:8000/docs`