#!/usr/bin/env python3
"""Startup script for BananaBot."""

import sys
import logging
from bot.main import main

if __name__ == "__main__":
    try:
        # Configure basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        print("🍌 Starting BananaBot...")
        print("Press Ctrl+C to stop the bot")
        
        # Run the bot
        import asyncio
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n🍌 BananaBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start BananaBot: {e}")
        sys.exit(1)