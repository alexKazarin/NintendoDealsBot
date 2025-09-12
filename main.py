#!/usr/bin/env python3
"""
Nintendo Deals Bot - Main entry point
"""

import asyncio
import logging
import signal
import sys
import uvicorn
from fastapi import FastAPI
from bot.bot import main
from bot.scheduler import price_checker

# Create FastAPI app for health checks
app = FastAPI(title="Nintendo Deals Bot", version="1.0.0")

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "service": "nintendo-deals-bot"}

async def run_web_server():
    """Run FastAPI web server for health checks"""
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main_with_scheduler():
    """Main function that starts bot, scheduler and web server"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Import bot here to avoid circular imports
    from bot.bot import bot

    # Set bot for price checker
    price_checker.set_bot(bot)

    # Start price checker scheduler
    price_checker.start()
    logger.info("Price checker scheduler started")

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping services...")
        price_checker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run bot and web server concurrently
        logger.info("Starting web server on port 8000...")
        await asyncio.gather(
            main(),          # Bot polling
            run_web_server() # Health check server
        )
    except Exception as e:
        logger.error(f"Error running services: {e}")
    finally:
        # Stop scheduler on exit
        price_checker.stop()

if __name__ == "__main__":
    asyncio.run(main_with_scheduler())
