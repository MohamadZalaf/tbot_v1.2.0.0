@echo off
chcp 65001 > nul
title بوت التداول v1.2.0 - وضع الاستقرار

echo ========================================
echo 🤖 بوت التداول المتقدم v1.2.0
echo 🔧 وضع الاستقرار المحسن
echo ========================================
echo.

:: إعداد متغيرات البيئة للاستقرار
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

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

echo ✅ جميع المتطلبات متوفرة

echo.
echo 🚀 بدء تشغيل البوت...
echo 💡 لإيقاف البرنامج، اضغط Ctrl+C
echo ========================================
echo.

:start_bot
:: تشغيل البوت مع إعادة التشغيل التلقائي
python tbot_v1.2.0.py

:: فحص كود الخروج
if errorlevel 1 (
    echo.
    echo ⚠️ البوت توقف بخطأ - كود الخروج: %errorlevel%
    echo 🔄 إعادة التشغيل خلال 10 ثوان...
    timeout /t 10 /nobreak > nul
    goto start_bot
) else (
    echo.
    echo ✅ تم إنهاء البوت بشكل طبيعي
)

echo.
echo ========================================
echo 🛑 تم إنهاء البوت
echo ========================================
pause