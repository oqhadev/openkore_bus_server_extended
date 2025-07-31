#!/usr/bin/env python3
"""
Build script for OpenKore Bus Server Extended
Creates executable files for different architectures using PyInstaller
"""

import os
import subprocess
import sys
import shutil
import platform

def get_architecture_suffix():
    """Get the architecture suffix for the executable name."""
    arch = platform.architecture()[0]
    machine = platform.machine().lower()
    
    if arch == "64bit" or "64" in machine or "amd64" in machine:
        return "x64"
    elif arch == "32bit" or "x86" in machine or "i386" in machine:
        return "x86"
    else:
        return platform.machine()

def build_exe(arch_suffix=None):
    """Build the executable using PyInstaller."""
    if arch_suffix is None:
        arch_suffix = get_architecture_suffix()
    
    exe_name = f"openkore-bus-server-{arch_suffix}"
    print(f"🔨 Building OpenKore Bus Server Extended ({arch_suffix})...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single file
        f"--name={exe_name}",           # Output name with architecture
        "--console",                    # Console application
        "--icon=NONE",                  # No icon for now
        "--clean",                      # Clean cache
        "--noconfirm",                  # Overwrite without confirmation
        "main.py"                       # Entry point
    ]
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Build successful for {arch_suffix}!")
        
        # Check if exe was created
        exe_path = os.path.join("dist", f"{exe_name}.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"📦 Executable created: {exe_path}")
            print(f"📏 File size: {file_size:.1f} MB")
            
            # Copy config example as config.ini for immediate use (only once)
            config_example = "config.ini.example"
            config_dest = "dist/config.ini"
            if os.path.exists(config_example) and not os.path.exists(config_dest):
                shutil.copy2(config_example, config_dest)
                print("📋 Copied config.ini.example to dist/config.ini")
            
            print(f"\n🚀 {arch_suffix} build ready!")
            return True
        else:
            print(f"❌ Executable not found for {arch_suffix}!")
            return False            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed for {arch_suffix}: {e}")
        print("Output:", e.stdout)
        print("Error:", e.stderr)
        return False

def build_all():
    """Build for current architecture."""
    arch = get_architecture_suffix()
    print(f"🏗️  Building for current architecture: {arch}")
    print(f"🖥️  Platform: {platform.platform()}")
    print(f"🐍 Python: {platform.python_version()}")
    print("=" * 60)
    
    success = build_exe(arch)
    
    if success:
        print("=" * 60)
        print("✅ Build completed successfully!")
        print(f"📁 Check the dist/ folder for openkore-bus-server-{arch}.exe")
        print("\n💡 To build for other architectures:")
        print("   • Install Python x86 and run this script there")
        print("   • Or use a different machine/VM with the target architecture")
    else:
        print("❌ Build failed!")
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
    
    print("✅ Clean completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_build()
    else:
        build_all()
