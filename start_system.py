#!/usr/bin/env python3
# start_system.py
"""
Drama Collector System Launcher
Starts all necessary services for the drama collection system
"""
import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SystemLauncher:
    def __init__(self):
        self.processes = {}
        self.running = False
        
    def check_mongodb(self):
        """Check if MongoDB is running"""
        try:
            import pymongo
            client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
            client.server_info()
            logger.info("MongoDB is running")
            return True
        except Exception as e:
            logger.warning(f"MongoDB not available: {e}")
            return False
    
    def start_mongodb(self):
        """Start MongoDB if not running"""
        if self.check_mongodb():
            return True
            
        logger.info("Starting MongoDB...")
        
        # Try different MongoDB startup methods
        mongodb_commands = [
            ['mongod', '--dbpath', './data/db', '--logpath', './data/logs/mongodb.log', '--fork'],
            ['brew', 'services', 'start', 'mongodb-community'],
            ['systemctl', 'start', 'mongod'],
            ['sudo', 'systemctl', 'start', 'mongod']
        ]
        
        for cmd in mongodb_commands:
            try:
                # Create data directories if they don't exist
                os.makedirs('./data/db', exist_ok=True)
                os.makedirs('./data/logs', exist_ok=True)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"MongoDB started with command: {' '.join(cmd)}")
                    time.sleep(3)  # Give MongoDB time to start
                    if self.check_mongodb():
                        return True
                else:
                    logger.debug(f"Command failed: {' '.join(cmd)} - {result.stderr}")
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
                logger.debug(f"Failed to start MongoDB with {cmd[0]}: {e}")
                continue
        
        logger.warning("Could not start MongoDB automatically. Please start it manually:")
        logger.warning("  Option 1: mongod --dbpath ./data/db")
        logger.warning("  Option 2: brew services start mongodb-community")
        logger.warning("  Option 3: Use Docker: docker run -d -p 27017:27017 mongo")
        return False
    
    def start_api_server(self):
        """Start the API server"""
        logger.info("Starting Drama Collector API server...")
        
        try:
            # Start the API server
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path.cwd())
            
            process = subprocess.Popen(
                [sys.executable, 'start_api.py'],
                env=env,
                cwd=Path.cwd()
            )
            
            self.processes['api'] = process
            logger.info(f"API server started with PID: {process.pid}")
            logger.info("Dashboard available at: http://localhost:8000/dashboard")
            logger.info("API docs available at: http://localhost:8000/docs")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            return False
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Start all system components"""
        logger.info("🎭 Starting Drama Collector System...")
        
        self.setup_signal_handlers()
        
        # Check Python dependencies
        try:
            import fastapi
            import uvicorn
            import pymongo
            logger.info("✓ Python dependencies available")
        except ImportError as e:
            logger.error(f"Missing Python dependencies: {e}")
            logger.error("Please install requirements: pip install -r requirements.txt")
            return False
        
        # Start MongoDB
        if not self.start_mongodb():
            logger.error("Failed to start MongoDB")
            return False
        
        # Start API server
        if not self.start_api_server():
            logger.error("Failed to start API server")
            return False
        
        self.running = True
        logger.info("🚀 Drama Collector System started successfully!")
        logger.info("")
        logger.info("Available endpoints:")
        logger.info("  📊 Dashboard: http://localhost:8000/dashboard")
        logger.info("  📖 API Docs:  http://localhost:8000/docs")
        logger.info("  🔧 API Root:  http://localhost:8000/")
        logger.info("")
        logger.info("Press Ctrl+C to stop the system")
        
        # Wait for processes
        try:
            while self.running:
                # Check if processes are still running
                for name, process in self.processes.items():
                    if process.poll() is not None:
                        logger.error(f"{name} process died with code {process.returncode}")
                        self.running = False
                        break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        
        self.shutdown()
        return True
    
    def shutdown(self):
        """Shutdown all processes"""
        logger.info("Shutting down Drama Collector System...")
        
        self.running = False
        
        # Terminate all processes
        for name, process in self.processes.items():
            try:
                logger.info(f"Terminating {name} process...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {name} process...")
                    process.kill()
                    process.wait()
                    
                logger.info(f"{name} process stopped")
                
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("Drama Collector System stopped")
    
    def status(self):
        """Check system status"""
        logger.info("Drama Collector System Status:")
        
        # Check MongoDB
        if self.check_mongodb():
            logger.info("✓ MongoDB: Running")
        else:
            logger.info("✗ MongoDB: Not running")
        
        # Check API server
        try:
            import requests
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                logger.info("✓ API Server: Running")
            else:
                logger.info(f"⚠ API Server: HTTP {response.status_code}")
        except Exception:
            logger.info("✗ API Server: Not running")

def main():
    launcher = SystemLauncher()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            launcher.status()
        elif command == 'stop':
            launcher.shutdown()
        elif command == 'start':
            launcher.start()
        else:
            print("Usage: python start_system.py [start|stop|status]")
            print("  start  - Start all system components (default)")
            print("  stop   - Stop all system components")
            print("  status - Check system status")
    else:
        # Default action is to start
        launcher.start()

if __name__ == "__main__":
    main()