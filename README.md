# <? Drama Collector System

**?gpn6???** - A comprehensive, production-ready platform for collecting, processing, and managing Chinese short drama data with advanced automation capabilities.

## < Features

### =? **Core Capabilities**
- **Multi-Source Data Collection**: Intelligent aggregation from multiple data sources with fallback mechanisms
- **Advanced NLP Processing**: Chinese text segmentation using jieba, plot extraction, and theme analysis
- **Comprehensive Data Validation**: Multi-level validation with quality scoring and data cleaning
- **Batch Processing**: Parallel processing system for large datasets with job queues
- **Export System**: Multi-format export (JSON, CSV, Excel, XML) with compression and metadata

### <? **Automation & Orchestration**
- **Advanced Orchestrator**: Complete job lifecycle management with scheduling and state tracking
- **Configuration Management**: YAML/JSON configuration with environment variable overrides
- **Performance Monitoring**: Real-time system metrics and alerting
- **Retry Mechanisms**: Intelligent retry logic with exponential backoff

### < **Web Interface & API**
- **RESTful API**: 15+ endpoints with FastAPI for complete system control
- **Web Dashboard**: Interactive management interface with real-time updates
- **System Monitoring**: Health checks, performance stats, and job tracking
- **Data Management**: Export controls, configuration updates, and drama browsing

## =? Installation

### Prerequisites
- Python 3.9+
- MongoDB 5.0+
- Git

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd drama_collector

# Install dependencies
pip install -r requirements.txt

# Start the complete system
python start_system.py
```

## =? Quick Start

### 1. **Access the Web Dashboard**
```
http://localhost:8000/dashboard
```

### 2. **Use the REST API**
```bash
# Check system health
curl http://localhost:8000/health

# Start a collection job
curl -X POST "http://localhost:8000/jobs/start" \
  -H "Content-Type: application/json" \
  -d '{"collection": {"count": 30}}'
```

### 3. **API Documentation**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## =? System Commands

```bash
# Start complete system
python start_system.py

# Start only API server
python start_api.py

# Check system status
python start_system.py status

# Stop system
python start_system.py stop
```

## =? Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Web management interface |
| GET | `/health` | System health check |
| POST | `/jobs/start` | Start collection job |
| GET | `/jobs/current` | Current job status |
| POST | `/export` | Export data |
| GET | `/dramas` | Browse collected dramas |

## <? System Status

** COMPLETED FEATURES:**
-  Multi-source data collection with fallback mechanisms
-  Advanced NLP processing pipeline with Chinese text support
-  Comprehensive data validation and quality scoring
-  Batch processing system with job queues
-  Performance monitoring with real-time metrics
-  Advanced orchestrator with scheduling and state management
-  Configuration management with YAML/JSON support
-  Multi-format data export (JSON, CSV, Excel, XML)
-  RESTful API with 15+ endpoints for complete system control
-  Interactive web dashboard for system management
-  Production-ready deployment with comprehensive error handling

**=? READY FOR PRODUCTION USE**

## =? Architecture Overview

```
Web Dashboard ? FastAPI Server ? Drama Orchestrator
                                        ?
Multi-Source ? Data Validator ? Batch Processor ? MongoDB
Collector        ?               ?
              Export System   Performance Monitor
```

## =' Development

### Run Tests
```bash
pytest
```

### Code Quality
```bash
black .      # Format code
flake8 .     # Lint code
```

## =? Support

- =? [API Documentation](http://localhost:8000/docs)
- =? [Web Dashboard](http://localhost:8000/dashboard)
- =? [System Status](http://localhost:8000/status)

---

**Built with d for the Chinese drama community**