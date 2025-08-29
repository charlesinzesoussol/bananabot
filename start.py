#!/usr/bin/env python3
"""Startup script for BananaBot."""

import sys
import logging
import platform
import asyncio
import main_bot  # Import from main_bot.py in project root

if __name__ == "__main__":
    try:
        # Configure basic logging for startup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        print("🍌 Starting BananaBot v2.0...")
        print("📁 Using new template-based architecture")
        print("🎯 Press Ctrl+C to stop the bot")
        print()
        
        # Ensure proper event loop on Windows
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Run the bot
        asyncio.run(main_bot.main())
        
    except KeyboardInterrupt:
        print("\n🍌 BananaBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start BananaBot: {e}")
        logging.error(f"Startup error: {e}", exc_info=True)
        sys.exit(1)