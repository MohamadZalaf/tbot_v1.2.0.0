@echo off
chcp 65001 > nul
title بوت التداول المتقدم v1.2.0

:start
cls
echo.
echo ====================================================================
echo              🤖 بوت التداول المتقدم v1.2.0 
echo ====================================================================
echo.
echo 🚀 جاري تشغيل البوت...
echo.

:: التحقق من وجود ملف البوت
if not exist "tbot_v1.2.0.py" (
    echo ❌ ملف البوت غير موجود!
    echo 📁 تأكد من وجود ملف tbot_v1.2.0.py في نفس المجلد
    echo.
    pause
    exit /b 1
)

:: التحقق من Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python غير مثبت أو غير موجود في PATH!
    echo 📥 يرجى تثبيت Python من: https://python.org
    echo.
    pause
    exit /b 1
)

echo ✅ تم العثور على Python
echo ✅ تم العثور على ملف البوت
echo.

:: عرض معلومات مهمة قبل التشغيل
echo 📋 تذكير مهم قبل التشغيل:
echo.
echo 1️⃣  تأكد من تشغيل MetaTrader5 وتسجيل الدخول
echo 2️⃣  تأكد من إعداد GEMINI_API_KEY في الكود
echo 3️⃣  تأكد من إعداد BOT_TOKEN في الكود
echo 4️⃣  تأكد من اتصال الإنترنت
echo.
echo ⏳ سيبدأ البوت خلال 5 ثوانٍ...
timeout /t 5 /nobreak >nul

echo.
echo 🔄 بدء تشغيل بوت التداول v1.2.0...
echo.
echo ====================================================================
echo.

:: تشغيل البوت
python tbot_v1.2.0.py

:: في حالة إيقاف البوت
echo.
echo ====================================================================
echo.
echo ⚠️ تم إيقاف البوت!
echo.
echo اختر ما تريد فعله:
echo [1] إعادة تشغيل البوت
echo [2] إنهاء البرنامج
echo.
set /p choice="اختر (1 أو 2): "

if "%choice%"=="1" goto start
if "%choice%"=="" goto start

echo.
echo 👋 تم إنهاء البرنامج
echo.
pause