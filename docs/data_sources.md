# 数据源配置指南

## 概述

本系统支持多种数据源，提供灵活的数据收集策略。当某个数据源不可用时，系统会自动回退到其他可用的数据源。

## 支持的数据源

### 1. Mock Collector（模拟数据源）
- **状态**: ✅ 总是可用
- **用途**: 开发测试、系统演示
- **数据量**: 5部精选中国短剧
- **特点**: 包含完整的剧目信息和详细数据

```python
from collectors.mock_collector import MockCollector

async with MockCollector() as collector:
    dramas = await collector.collect_drama_list(count=5)
```

### 2. Douban Collector（豆瓣数据源）
- **状态**: ⚠️ API限制，已添加网页回退
- **用途**: 获取权威的中文剧目数据
- **挑战**: API返回403错误，需要完善的反爬虫策略
- **解决方案**: 
  - 添加了浏览器头信息
  - 实现了网页爬取回退
  - 降低了请求频率

```python
from collectors.douban_collector import DoubanCollector

async with DoubanCollector() as collector:
    dramas = await collector.collect_drama_list(count=10)
```

### 3. MyDramaList Collector（国际剧目数据库）
- **状态**: ⚠️ 需要进一步优化
- **用途**: 获取国际化的中国剧目数据
- **特点**: 包含用户评分和国际视角的数据
- **挑战**: 需要HTML解析和反爬虫处理

```python
from collectors.mydramalist_collector import MyDramaListCollector

async with MyDramaListCollector() as collector:
    dramas = await collector.collect_drama_list(count=10)
```

### 4. Multi-Source Collector（多源聚合）
- **状态**: ✅ 推荐使用
- **用途**: 自动聚合多个数据源
- **特点**: 
  - 并行数据收集
  - 智能去重
  - 数据完整性评分
  - 优雅的错误处理

```python
from collectors.multi_source_collector import MultiSourceCollector

async with MultiSourceCollector() as collector:
    dramas = await collector.collect_drama_list(count=20)
```

## 数据源配置

### 启用/禁用数据源

```python
# 只使用可靠的数据源
collector = MultiSourceCollector(enable_sources=['mock', 'douban'])

# 使用所有数据源（默认）
collector = MultiSourceCollector()  # ['mock', 'douban', 'mydramalist']
```

### 数据源优先级

系统按以下优先级使用数据源：
1. **Douban** - 权威性最高
2. **MyDramaList** - 国际化数据
3. **Mock** - 保底数据源

## 故障处理策略

### 1. 自动回退
当高优先级数据源失败时，系统自动尝试下一个数据源：

```
Douban API失败 → Douban网页爬取 → MyDramaList → Mock数据
```

### 2. 数据去重
系统自动识别并合并重复的剧目：
- 基于标题和年份进行去重
- 保留数据更完整的版本
- 计算数据完整性得分

### 3. 错误日志
所有数据源错误都会被记录，便于调试：

```python
INFO:collectors.multi_source_collector:数据源 douban 收集到 0 部剧目
WARNING:collectors.multi_source_collector:数据源 douban 获取详情失败: 403 Forbidden
```

## 性能优化

### 1. 并行收集
多个数据源同时工作，减少总耗时：

```python
# 并行从3个数据源收集
tasks = [source1.collect(), source2.collect(), source3.collect()]
results = await asyncio.gather(*tasks)
```

### 2. 速率限制
每个数据源都有独立的速率限制：
- Douban: 2 requests/second
- MyDramaList: 3 requests/second  
- Mock: 无限制

### 3. 连接池
使用aiohttp连接池优化网络请求。

## 添加新数据源

### 1. 创建收集器类

```python
from .base_collector import BaseCollector

class NewSourceCollector(BaseCollector):
    async def collect_drama_list(self, **kwargs):
        # 实现数据收集逻辑
        pass
    
    async def collect_drama_detail(self, drama_id):
        # 实现详情收集逻辑
        pass
```

### 2. 注册到多源收集器

```python
# 在MultiSourceCollector中添加
if 'newsource' in self.enabled_sources:
    self.collectors['newsource'] = NewSourceCollector()
```

### 3. 更新优先级配置

```python
self.source_priority = ['newsource', 'douban', 'mydramalist', 'mock']
```

## 监控和维护

### 数据源状态检查

```python
async with MultiSourceCollector() as collector:
    status = collector.get_source_status()
    print(f"可用数据源: {status}")
```

### 数据质量评估

系统会自动评估每个数据源的数据质量：
- 完整性得分
- 成功率统计
- 响应时间监控

## 未来扩展

### 计划中的数据源
1. **iQiyi API** - 爱奇艺官方接口
2. **Tencent Video** - 腾讯视频数据
3. **Bilibili** - B站短剧内容
4. **直播平台** - 抖音、快手短剧数据

### 技术改进
1. **缓存机制** - Redis缓存热门数据
2. **代理轮换** - 绕过IP限制
3. **智能重试** - 指数退避重试策略
4. **数据验证** - 自动检测数据质量