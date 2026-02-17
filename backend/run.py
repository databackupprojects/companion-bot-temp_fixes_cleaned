#!/usr/bin/env python3
# backend/run.py - FIXED VERSION
"""
Run script for AI Companion Bot v3.1 - FIXED for async/await issues
"""
import os
import sys
import asyncio
import logging
import signal
from dotenv import load_dotenv
from core.container import container

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manage async services with proper shutdown."""
    
    def __init__(self):
        self.tasks = []
        self.should_stop = False
        self.telegram_bot_manager = None  # Keep reference to bot manager for proper cleanup
    
    async def run_api(self):
        """Run FastAPI application."""
        import uvicorn
        from constants import API_HOST, API_PORT, ENVIRONMENT
        
        logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
        
        config = uvicorn.Config(
            "main:app",
            host=API_HOST,
            port=API_PORT,
            reload=False,  # Disable reload in production/multi-service mode
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except asyncio.CancelledError:
            logger.info("API server task cancelled")
            raise
    
    async def run_telegram_bot(self):
        """Run Telegram bots with proper async handling - Multi-bot support."""
        try:
            from telegram_bot import TelegramBotManager
            from database import AsyncSessionLocal
            
            logger.info("Initializing Telegram bots (multi-persona support)...")

            session = AsyncSessionLocal()
            await container.startup()
            try:
                message_handler = container.build_message_handler(session)
                command_handler = container.build_command_handler(session)
                
                # Create bot manager for all personas
                self.telegram_bot_manager = TelegramBotManager(message_handler, command_handler)
                
                # Initialize all persona bots
                await self.telegram_bot_manager.initialize_all()
                
                if self.telegram_bot_manager.bots:
                    logger.info(f"Telegram bot manager initialized {len(self.telegram_bot_manager.bots)} persona bot(s)")
                    # Start all bots
                    await self.telegram_bot_manager.start_all()
                else:
                    logger.error("No Telegram bots were initialized - check tokens in .env")
                    await session.close()
            except Exception as inner_e:
                await session.close()
                # Re-raise to outer handler which will check for network errors
                raise inner_e
            
        except ImportError as e:
            logger.error(f"Cannot run Telegram bot: {e}")
            logger.info("Install Telegram dependencies: pip install python-telegram-bot")
        except Exception as e:
            # Check if it's a network/DNS error
            error_msg = str(e).lower()
            if 'network' in error_msg or 'dns' in error_msg or 'name or service not known' in error_msg or 'connecterror' in error_msg:
                logger.warning(f"⚠️ Telegram bot disabled due to network/DNS error: {e}")
                logger.warning("⚠️ API server will continue running. Telegram functionality will be unavailable.")
                logger.info("💡 To fix: Check your internet connection or DNS settings")
            else:
                logger.error(f"Failed to run Telegram bot: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    async def run_celery_worker(self):
        """Run Celery worker."""
        try:
            from tasks.celery import celery_app
            
            logger.info("Starting Celery worker...")
            
            # Import all tasks
            import tasks
            
            # Run worker
            argv = ['worker', '--loglevel=info', '--concurrency=2']
            worker = celery_app.Worker(
                argv=argv,
                hostname='worker@%h',
                pool='solo',  # Use solo pool for async
                loglevel='INFO'
            )
            await worker.start()
            
        except Exception as e:
            logger.error(f"Failed to run Celery worker: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def run_celery_beat(self):
        """Run Celery beat scheduler."""
        try:
            from tasks.celery import celery_app
            
            logger.info("Starting Celery beat scheduler...")
            
            beat = celery_app.Beat(
                loglevel='INFO'
            )
            await beat.run()
            
        except Exception as e:
            logger.error(f"Failed to run Celery beat: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def start_service(self, coro):
        """Start a service task."""
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task
    
    async def stop_services(self):
        """Stop all services gracefully."""
        logger.info("Stopping all services...")
        self.should_stop = True
        
        # Stop Telegram bot manager first
        if self.telegram_bot_manager:
            try:
                logger.info("Stopping Telegram bot manager...")
                await self.telegram_bot_manager.stop_all()
                logger.info("Telegram bot manager stopped")
            except Exception as e:
                logger.error(f"Error stopping Telegram bot manager: {e}")
        
        # Dispose of database engine BEFORE cancelling tasks
        try:
            from database import engine
            logger.info("Closing database connections...")
            await engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error disposing database: {e}")

        try:
            await container.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down services: {e}")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All services stopped")

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Companion Bot v3.1")
    parser.add_argument("--api", action="store_true", help="Run API server")
    parser.add_argument("--telegram", action="store_true", help="Run Telegram bot")
    parser.add_argument("--celery-worker", action="store_true", help="Run Celery worker")
    parser.add_argument("--celery-beat", action="store_true", help="Run Celery beat scheduler")
    parser.add_argument("--all", action="store_true", help="Run all services")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('companion_bot.log')
        ]
    )
    
    # Set up asyncio debug if in development
    if os.getenv("ENVIRONMENT") == "development":
        asyncio.get_event_loop().set_debug(True)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)
    
    # Default to API + Telegram if no args specified
    if args.all or (not args.api and not args.telegram and not args.celery_worker and not args.celery_beat):
        args.api = True
        args.telegram = True
    
    # Create service manager
    manager = ServiceManager()
    
    # Set up signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(manager.stop_services()))
    
    try:
        # Start services
        if args.api:
            manager.start_service(manager.run_api())
        
        if args.telegram:
            manager.start_service(manager.run_telegram_bot())
        
        if args.celery_worker:
            manager.start_service(manager.run_celery_worker())
        
        if args.celery_beat:
            manager.start_service(manager.run_celery_beat())
        
        # Wait for tasks to start
        if manager.tasks:
            # Give tasks time to initialize
            await asyncio.sleep(3)
        
        # Keep running until stopped
        while not manager.should_stop:
            await asyncio.sleep(1)
            # Check if critical tasks have failed
            if manager.tasks:
                done_tasks = [task for task in manager.tasks if task.done()]
                if done_tasks:
                    for task in done_tasks:
                        try:
                            # This will raise if the task failed
                            task.result()
                        except asyncio.CancelledError:
                            pass  # Normal cancellation
                        except Exception as e:
                            logger.error(f"Task failed with error: {e}")
                    
                    # If all tasks are done, something went wrong
                    if all(task.done() for task in manager.tasks):
                        logger.error("All service tasks have stopped unexpectedly")
                        break
        
    except asyncio.CancelledError:
        logger.info("Shutdown requested...")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error running services: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        await manager.stop_services()

if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())