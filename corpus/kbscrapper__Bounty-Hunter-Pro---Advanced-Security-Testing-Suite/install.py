#!/usr/bin/env python3
"""
Bounty Hunter Pro - Installation Script
Automatically installs all required dependencies
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("🎯 Bounty Hunter Pro - Installation Script")
    print("="*50)
    
    # Check if pip is available
    try:
        import pip
    except ImportError:
        print("❌ pip is not installed. Please install pip first.")
        return False
    
    # Install requirements
    requirements_file = "requirements.txt"
    
    if not os.path.exists(requirements_file):
        print("❌ requirements.txt not found!")
        return False
    
    print("📦 Installing required packages...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False

def create_desktop_shortcut():
    """Create desktop shortcut (Windows)"""
    if sys.platform == "win32":
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            path = os.path.join(desktop, "Bounty Hunter Pro.lnk")
            target = os.path.join(os.getcwd(), "bounty_hunter_gui.py")
            wDir = os.getcwd()
            icon = target
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{target}"'
            shortcut.WorkingDirectory = wDir
            shortcut.IconLocation = icon
            shortcut.save()
            
            print("✅ Desktop shortcut created!")
            
        except ImportError:
            print("⚠️ Could not create desktop shortcut (winshell not available)")
        except Exception as e:
            print(f"⚠️ Could not create desktop shortcut: {e}")

def main():
    """Main installation function"""
    print("Starting installation...")
    
    if install_requirements():
        print("\n🎉 Installation completed successfully!")
        print("\nTo run Bounty Hunter Pro:")
        print(f"python {os.path.join(os.getcwd(), 'bounty_hunter_gui.py')}")
        
        if sys.platform == "win32":
            create_desktop_shortcut()
        
        print("\n⚠️  IMPORTANT LEGAL NOTICE:")
        print("This tool is for authorized security testing only.")
        print("Only use on systems you own or have explicit permission to test.")
        
    else:
        print("\n❌ Installation failed!")
        print("Please check the error messages above and try again.")

if __name__ == "__main__":
    main()

