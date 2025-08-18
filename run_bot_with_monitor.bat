@echo off
chcp 65001 > nul
title بوت التداول v1.2.0 - مع المراقب

echo ========================================
echo 🤖 بوت التداول المتقدم v1.2.0
echo 🔧 مع مراقب الصحة التلقائي  
echo ========================================
echo.

echo 📋 التحقق من المتطلبات...

:: التحقق من وجود Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت أو غير موجود في PATH
    pause
    exit /b 1
)

:: التحقق من وجود ملف البوت
if not exist "tbot_v1.2.0.py" (
    echo ❌ ملف البوت غير موجود: tbot_v1.2.0.py
    pause
    exit /b 1
)

:: التحقق من وجود ملف المراقب
if not exist "bot_health_monitor.py" (
    echo ❌ ملف المراقب غير موجود: bot_health_monitor.py
    pause
    exit /b 1
)

echo ✅ جميع المتطلبات متوفرة

echo.
echo 🚀 بدء تشغيل البوت مع المراقب...
echo 💡 لإيقاف البرنامج، اضغط Ctrl+C
echo ========================================
echo.

:: تشغيل المراقب (الذي سيشغل البوت)
python bot_health_monitor.py

echo.
echo ========================================
echo 🛑 تم إنهاء البوت والمراقب
echo ========================================
pause