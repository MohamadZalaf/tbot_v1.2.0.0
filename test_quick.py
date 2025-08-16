#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Quick Test for DateTime Errors
=================================
Quick test to catch datetime errors before building .exe

Developer: Mohamad Zalaf ©️2025
"""

import sys
import os

def test_datetime_imports():
    """Test datetime imports"""
    print("🧪 Testing datetime imports...")
    
    try:
        # Test the exact imports from bot_ui.py
        from datetime import datetime, timedelta
        
        # Test datetime usage
        now = datetime.now()
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"  ✅ datetime.now() works: {formatted}")
        print(f"  ✅ timedelta works: {now + timedelta(seconds=5)}")
        return True
        
    except Exception as e:
        print(f"  ❌ DateTime error: {e}")
        return False

def test_bot_ui_import():
    """Test importing bot_ui.py"""
    print("🧪 Testing bot_ui.py import...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to import (this will catch syntax errors)
        import bot_ui
        print("  ✅ bot_ui.py imports successfully")
        
        # Test creating the embedded bot class
        bot = bot_ui.EmbeddedTradingBot()
        print("  ✅ EmbeddedTradingBot class created")
        
        # Test the datetime usage in add_log method
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  ✅ Timestamp format works: {timestamp}")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Runtime error: {e}")
        return False

def test_tkinter():
    """Test tkinter availability"""
    print("🧪 Testing tkinter...")
    
    try:
        import tkinter as tk
        
        # Test creating a root (but don't show it)
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.destroy()   # Clean up
        
        print("  ✅ tkinter works")
        return True
        
    except Exception as e:
        print(f"  ❌ tkinter error: {e}")
        return False

def main():
    """Run all tests"""
    print("🤖 Quick Test for Bot UI")
    print("=" * 30)
    
    tests = [
        ("DateTime Imports", test_datetime_imports),
        ("Bot UI Import", test_bot_ui_import),
        ("Tkinter", test_tkinter)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        print()
    
    print("=" * 30)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Ready to build .exe")
        print("💡 Run: python build_exe_simple.py")
        return True
    else:
        print("❌ Some tests failed! Fix errors before building")
        return False

if __name__ == "__main__":
    try:
        success = main()
        input(f"\nPress Enter to exit...")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        input("Press Enter to exit...")