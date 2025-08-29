#!/usr/bin/env python3
"""
Volume Detection Script for BananaBot
Run this on your VPS to check which volume path is available
"""

import os
from pathlib import Path

def check_volume_paths():
    """Check which volume paths are available on the VPS."""
    print("🔍 Checking volume paths for BananaBot data storage...")
    print("=" * 50)
    
    # Possible volume paths to check
    paths_to_check = [
        "/mnt/HC_Volume_103242903",         # Volume ID format
        "/mnt/volume-ash-2",                # Volume name format
        "/volume1",                         # Alternative mount point
        "/opt",                             # Alternative location
        "/var/lib",                         # System data location
        "/home/bananabot-data"              # User data location
    ]
    
    available_paths = []
    
    for path_str in paths_to_check:
        path = Path(path_str)
        exists = path.exists()
        writable = False
        
        if exists:
            try:
                writable = os.access(path, os.W_OK)
            except:
                writable = False
        
        status = "✅ Available & Writable" if (exists and writable) else \
                 "📁 Exists (Read-only)" if exists else \
                 "❌ Not found"
        
        print(f"{status:25} {path}")
        
        if exists and writable:
            available_paths.append(path)
    
    print("\n" + "=" * 50)
    
    if available_paths:
        print(f"✅ Found {len(available_paths)} suitable path(s) for data storage:")
        for path in available_paths:
            print(f"   📂 {path}/bananabot-data/")
        
        print(f"\n🍌 Recommended: Use {available_paths[0]}/bananabot-data/")
    else:
        print("❌ No writable volume paths found!")
        print("💡 Consider creating /opt/bananabot-data or using /tmp/bananabot-data")
    
    # Check current working directory as fallback
    cwd = Path.cwd()
    print(f"\n📍 Current directory: {cwd}")
    print(f"   Writable: {'✅' if os.access(cwd, os.W_OK) else '❌'}")

if __name__ == "__main__":
    check_volume_paths()