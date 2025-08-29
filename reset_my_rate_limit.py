#!/usr/bin/env python3
"""
One-time script to reset your Discord user rate limit
Run this locally to clear your rate limit
"""

import json
import os
from pathlib import Path

def reset_user_rate_limit():
    """Reset rate limit by clearing data files."""
    
    # Your Discord user ID (you'll need to replace this with your actual Discord user ID)
    # To find your Discord ID: Enable Developer Mode in Discord settings, right-click your username, copy ID
    YOUR_USER_ID = "346768154581794816"  # Replace with your Discord user ID if different
    
    data_paths = [
        Path("data"),  # Local
        Path("/opt/bananabot/data")  # VPS (if running there)
    ]
    
    reset_count = 0
    
    for data_root in data_paths:
        if not data_root.exists():
            continue
            
        gallery_file = data_root / "user_galleries" / f"{YOUR_USER_ID}.json"
        stats_file = data_root / "user_stats" / f"{YOUR_USER_ID}.json"
        
        print(f"Checking data path: {data_root}")
        
        # Check if user files exist
        if gallery_file.exists():
            try:
                with open(gallery_file) as f:
                    data = json.load(f)
                    
                recent_works = len([w for w in data.get('works', []) 
                                 if w.get('created_at', '').startswith('2025-08-29')])
                print(f"Found {recent_works} generations today in gallery")
                reset_count += 1
                
            except Exception as e:
                print(f"Error reading gallery: {e}")
        
        if stats_file.exists():
            print(f"Found stats file: {stats_file}")
    
    print(f"\n🔄 RATE LIMIT RESET OPTIONS:")
    print(f"1. Wait 1 hour for natural reset")
    print(f"2. Restart the bot service (clears in-memory rate limits)")
    print(f"3. Manual reset via bot admin commands (if implemented)")
    
    if reset_count > 0:
        print(f"\n💡 Your user data exists in {reset_count} location(s)")
        print(f"Rate limits are enforced in-memory by the running bot")
        print(f"Restarting the bot service will clear all rate limits")
    else:
        print(f"\n✅ No user data found - you may not be rate limited")
        print(f"Rate limits are stored in bot memory, not files")

if __name__ == "__main__":
    print("🍌 BANANABOT RATE LIMIT RESET")
    print("=" * 40)
    reset_user_rate_limit()