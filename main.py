#!/usr/bin/env python3
"""
Nintendo Deals Bot - Main entry point
"""

import asyncio
import logging
import signal
import sys
from bot.bot import main
from bot.scheduler import price_checker

async def main_with_scheduler():
    """Main function that starts both bot and scheduler"""
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
        # Run the bot
        await main()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        # Stop scheduler on exit
        price_checker.stop()

if __name__ == "__main__":
    asyncio.run(main_with_scheduler())
