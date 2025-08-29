#!/usr/bin/env python3
"""
BananaBot Real Metrics Display
Simple command-line tool to show actual bot usage and costs
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

def load_real_metrics():
    """Load real metrics from bot data files."""
    # Check both local and VPS data paths
    data_paths = [
        Path("data"),  # Local
        Path("/opt/bananabot/data")  # VPS
    ]
    
    data_root = None
    for path in data_paths:
        if path.exists():
            data_root = path
            break
    
    if not data_root:
        return None
        
    gallery_path = data_root / "user_galleries"
    stats_path = data_root / "user_stats"
    
    # Initialize counters
    total_users = 0
    total_generations = 0 
    total_cost = 0.0
    active_users_24h = 0
    recent_activity_24h = 0
    users_today = 0
    cost_today = 0.0
    
    # Calculate time boundaries
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)
    today_str = now.strftime('%Y-%m-%d')
    
    # Load user gallery data
    if gallery_path.exists():
        for user_file in gallery_path.glob('*.json'):
            try:
                with open(user_file) as f:
                    user_data = json.load(f)
                    total_users += 1
                    works = user_data.get('works', [])
                    user_total_cost = user_data.get('total_cost', 0)
                    
                    total_generations += len(works)
                    total_cost += user_total_cost
                    
                    # Check recent activity
                    user_active_24h = False
                    user_active_today = False
                    
                    for work in works:
                        work_date = work.get('created_at', '')
                        work_cost = work.get('cost', 0.039)  # Default cost
                        
                        # Check if today
                        if work_date.startswith(today_str):
                            cost_today += work_cost
                            if not user_active_today:
                                users_today += 1
                                user_active_today = True
                        
                        # Check if within 24h
                        try:
                            work_datetime = datetime.fromisoformat(work_date.replace('Z', '+00:00'))
                            if work_datetime > cutoff_24h:
                                if not user_active_24h:
                                    active_users_24h += 1
                                    user_active_24h = True
                                recent_activity_24h += 1
                        except:
                            pass
                            
            except Exception as e:
                continue
    
    return {
        'data_path': str(data_root),
        'total_users': total_users,
        'total_generations': total_generations,
        'total_cost': total_cost,
        'active_users_24h': active_users_24h,
        'recent_activity_24h': recent_activity_24h,
        'users_today': users_today,
        'cost_today': cost_today,
        'avg_cost_per_user': total_cost / max(1, total_users),
        'avg_generations_per_user': total_generations / max(1, total_users),
        'guild_count': 1 if total_users > 0 else 0  # Bot is active if users exist
    }

def display_metrics():
    """Display metrics in a nice command-line format."""
    print("\n🍌 BANANABOT REAL METRICS")
    print("=" * 50)
    
    metrics = load_real_metrics()
    
    if not metrics:
        print("❌ No data found!")
        print("   • Check if bot is running")  
        print("   • Check if users have generated images")
        print("   • Data paths checked: ./data/ and /opt/bananabot/data/")
        return
    
    print(f"📊 Data Source: {metrics['data_path']}")
    print(f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Current Status
    print("🟢 BOT STATUS")
    print(f"   Guilds Connected: {metrics['guild_count']}")
    print(f"   Total Users: {metrics['total_users']}")
    print(f"   Total Generations: {metrics['total_generations']}")
    print()
    
    # Costs
    print("💰 COST ANALYSIS")
    print(f"   Total Cost Spent: ${metrics['total_cost']:.4f}")
    print(f"   Cost Today: ${metrics['cost_today']:.4f}")
    print(f"   Avg Cost/User: ${metrics['avg_cost_per_user']:.4f}")
    print()
    
    # Activity  
    print("📈 RECENT ACTIVITY")
    print(f"   Active Users (24h): {metrics['active_users_24h']}")
    print(f"   Images Generated (24h): {metrics['recent_activity_24h']}")
    print(f"   Users Active Today: {metrics['users_today']}")
    print(f"   Avg Generations/User: {metrics['avg_generations_per_user']:.1f}")
    print()
    
    # Rate Limit Safety
    print("🛡️ RATE LIMIT PROTECTION")
    max_daily_cost = metrics['total_users'] * 3 * 0.039  # 3/hour * $0.039
    print(f"   Rate Limit: 3 images/hour/user")
    print(f"   Max Daily Cost: ${max_daily_cost:.2f}")
    print(f"   Current Daily Cost: ${metrics['cost_today']:.4f}")
    print()
    
    # Growth Projections  
    if metrics['total_users'] > 0:
        print("📊 GROWTH PROJECTIONS")
        current_monthly = metrics['avg_cost_per_user'] * 30
        for users in [10, 25, 50, 100]:
            monthly_cost = current_monthly * users
            print(f"   {users:3d} users: ${monthly_cost:.0f}/month")
        print()
    
    # Status Assessment
    if metrics['cost_today'] == 0:
        print("✅ STATUS: No usage today - costs under control")
    elif metrics['cost_today'] < 1.0:
        print("✅ STATUS: Low usage - very safe costs")
    elif metrics['cost_today'] < 5.0:
        print("🟡 STATUS: Moderate usage - monitor costs")
    else:
        print("🔴 STATUS: High usage - review rate limits")
    
    print("=" * 50)

if __name__ == "__main__":
    display_metrics()