#!/usr/bin/env python3
"""
Build script for OpenKore Bus Server Extended
Creates a single executable file using PyInstaller
"""

import os
import subprocess
import sys
import shutil

def build_exe():
    """Build the executable using PyInstaller."""
    print("🔨 Building OpenKore Bus Server Extended...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single file
        "--name=openkore-bus-server",   # Output name
        "--console",                    # Console application
        "--icon=NONE",                  # No icon for now
        "--clean",                      # Clean cache
        "--noconfirm",                  # Overwrite without confirmation
        "main.py"                       # Entry point
    ]
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful!")
        
        # Check if exe was created
        exe_path = os.path.join("dist", "openkore-bus-server.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"📦 Executable created: {exe_path}")
            print(f"📏 File size: {file_size:.1f} MB")
            
            # Copy config example to dist folder
            config_example = "config.ini.example"
            if os.path.exists(config_example):
                shutil.copy2(config_example, "dist/")
                print("📋 Copied config.ini.example to dist/")
            
            print("\n🚀 Ready to deploy!")
            print("ℹ️  Don't forget to create config.ini from config.ini.example")
        else:
            print("❌ Executable not found!")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print("Output:", e.stdout)
        print("Error:", e.stderr)
        sys.exit(1)

def clean_build():
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")
    
    folders_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["*.spec"]
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"🗑️  Removed {folder}/")
    
    import glob
    for pattern in files_to_clean:
        for file in glob.glob(pattern):
            os.remove(file)
            print(f"🗑️  Removed {file}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_build()
    else:
        build_exe()
