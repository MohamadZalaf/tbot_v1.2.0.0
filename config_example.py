#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📋 ملف الإعدادات المثال - بوت التداول v1.2.0
==================================================

هذا ملف مثال لإعدادات البوت. 
انسخ هذا الملف إلى config.py وعدّل القيم حسب احتياجاتك.

⚠️ تحذير: لا تشارك مفاتيح API مع أي شخص!
"""

# ===== إعدادات البوت الأساسية =====

# رمز بوت Telegram (احصل عليه من @BotFather)
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'

# كلمة مرور البوت (غيّرها لحماية أفضل)
BOT_PASSWORD = 'tra12345678'

# مفتاح Google Gemini AI (احصل عليه من https://ai.google.dev)
GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY_HERE'
# قائمة مفاتيح بديلة للتبديل التلقائي عند حدود RPD/Quota
GEMINI_API_KEYS = [GEMINI_API_KEY, 'YOUR_SECOND_GEMINI_API_KEY_IF_ANY']

# ===== إعدادات MetaTrader5 =====

# معلومات الحساب (اختيارية - للاتصال التلقائي)
MT5_LOGIN = None  # رقم الحساب
MT5_PASSWORD = None  # كلمة مرور الحساب  
MT5_SERVER = None  # اسم الخادم

# ===== إعدادات المراقبة =====

# تردد فحص الأسعار (بالثواني)
MONITORING_INTERVAL = 30

# الحد الأدنى لمستوى الثقة لإرسال الإشعارات (0-100)
MIN_CONFIDENCE_THRESHOLD = 70

# أقصى عدد إشعارات يومية لكل مستخدم
MAX_DAILY_ALERTS = 50

# ===== إعدادات Gemini AI =====

# نموذج Gemini المستخدم
GEMINI_MODEL = 'gemini-2.0-flash'  # خيارات: 'gemini-2.0-flash', 'gemini-1.5-pro'

# إعدادات توليد المحتوى
GEMINI_GENERATION_CONFIG = {
    'temperature': 0.7,  # درجة العشوائية (0.0 - 1.0)
    'top_p': 0.8,       # Top-p sampling
    'top_k': 40,        # Top-k sampling
    'max_output_tokens': 1024,  # أقصى عدد رموز في الإخراج
}

# إعدادات الأمان
GEMINI_SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH", 
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    }
]

# حدود جلسة المحادثة والسياق
GEMINI_CONTEXT_TOKEN_LIMIT = 120000
GEMINI_CONTEXT_NEAR_LIMIT_RATIO = 0.85
GEMINI_ROTATE_ON_RATE_LIMIT = True

# حفظ سجلات المحادثة لكل رمز
SAVE_CHAT_LOGS = True
CHAT_LOG_RETENTION_DAYS = 7

# ===== إعدادات التحليل =====

# نموذج prompt للتحليل المالي
ANALYSIS_PROMPT_TEMPLATE = """
قم بتحليل البيانات التالية للرمز المالي {symbol}:

المعلومات الحالية:
- السعر الحالي: {current_price}
- سعر الشراء: {bid_price}
- سعر البيع: {ask_price}
- الفرق (Spread): {spread}
- الوقت: {timestamp}

اعطني تحليل فني شامل يتضمن:
1. اتجاه السوق المتوقع (صاعد/هابط/جانبي)
2. قوة الإشارة من 1 إلى 100
3. التوصية (شراء/بيع/انتظار)
4. أهم مستويات الدعم والمقاومة
5. الأسباب الفنية وراء هذا التحليل

تأكد من أن تكون التوصية واقعية ومبنية على تحليل فني صحيح.
"""

# ===== إعدادات إدارة المخاطر =====

# نسب الهدف ووقف الخسارة الافتراضية
DEFAULT_TAKE_PROFIT_PERCENTAGE = 3.0  # 3%
DEFAULT_STOP_LOSS_PERCENTAGE = 1.0    # 1%

# إعدادات خاصة بنمط التداول
TRADING_MODE_SETTINGS = {
    'scalping': {
        'min_confidence': 80,          # ثقة أعلى للسكالبينغ
        'take_profit_pct': 1.5,        # هدف أصغر
        'stop_loss_pct': 0.5,          # وقف خسارة أضيق
        'max_daily_alerts': 30         # عدد أقل من الإشعارات
    },
    'longterm': {
        'min_confidence': 60,          # ثقة أقل للمدى الطويل
        'take_profit_pct': 5.0,        # هدف أكبر
        'stop_loss_pct': 2.0,          # وقف خسارة أوسع
        'max_daily_alerts': 10         # عدد أقل من الإشعارات
    }
}

# ===== إعدادات الرموز المالية =====

# الرموز المفعلة للمراقبة الافتراضية
DEFAULT_ACTIVE_SYMBOLS = [
    'EURUSD',  # يورو/دولار
    'GBPUSD',  # جنيه/دولار
    'USDJPY',  # دولار/ين
    'XAUUSD',  # الذهب
    'BTCUSD'   # بيتكوين
]

# أولوية الرموز (الأعلى أولوية = رقم أصغر)
SYMBOL_PRIORITY = {
    'EURUSD': 1,
    'GBPUSD': 2,
    'USDJPY': 3,
    'AUDUSD': 4,
    'USDCAD': 5,
    'XAUUSD': 6,
    'XAGUSD': 7,
    'BTCUSD': 8,
    'ETHUSD': 9,
    'US30': 10
}

# ===== إعدادات التخزين =====

# مسارات مجلدات البيانات
DATA_DIRECTORIES = {
    'main': 'trading_data',
    'feedback': 'trading_data/user_feedback',
    'trade_logs': 'trading_data/trade_logs',
    'logs': 'logs',
    'backups': 'backups'
}

# إعدادات الأرشفة
ARCHIVE_SETTINGS = {
    'auto_archive': True,           # أرشفة تلقائية
    'archive_after_days': 30,       # أرشفة بعد 30 يوم
    'max_backup_files': 10,         # أقصى عدد ملفات نسخ احتياطية
    'compress_archives': True       # ضغط الأرشيف
}

# ===== إعدادات السجلات =====

# مستوى السجلات
LOG_LEVEL = 'INFO'  # خيارات: DEBUG, INFO, WARNING, ERROR, CRITICAL

# إعدادات ملف السجل
LOG_FILE_CONFIG = {
    'filename': 'advanced_trading_bot_v1.2.0.log',
    'max_bytes': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5,               # عدد ملفات النسخ الاحتياطية
    'encoding': 'utf-8'
}

# ===== إعدادات الإشعارات =====

# إعدادات التنبيهات الافتراضية
DEFAULT_NOTIFICATION_SETTINGS = {
    'trading_signals': True,         # إشارات التداول
    'support_alerts': True,          # تنبيهات الدعم
    'breakout_alerts': True,         # تنبيهات الاختراق
    'pattern_alerts': True,          # تنبيهات الأنماط
    'volume_alerts': False,          # تنبيهات الحجم
    'news_alerts': False,            # تنبيهات الأخبار
    'success_threshold': 70,         # عتبة النجاح
    'frequency': 'normal',           # تردد الإشعارات
    'timing': 'always'               # توقيت الإشعارات
}

# توقيتات الإشعارات
NOTIFICATION_TIMINGS = {
    'market_hours_only': {
        'enabled': False,
        'start_time': '09:00',  # بداية السوق
        'end_time': '17:00'     # نهاية السوق
    },
    'quiet_hours': {
        'enabled': True,
        'start_time': '22:00',  # بداية الساعات الهادئة
        'end_time': '07:00'     # نهاية الساعات الهادئة
    }
}

# ===== إعدادات المنطقة الزمنية =====

# المنطقة الزمنية الافتراضية
DEFAULT_TIMEZONE = 'Asia/Baghdad'  # بغداد UTC+3

# خيارات المنطقة الزمنية المتاحة
AVAILABLE_TIMEZONES = [
    'Asia/Baghdad',      # بغداد UTC+3
    'Asia/Riyadh',       # الرياض UTC+3
    'Asia/Dubai',        # دبي UTC+4
    'Europe/London',     # لندن UTC+0
    'Europe/Berlin',     # برلين UTC+1
    'America/New_York',  # نيويورك UTC-5
    'Asia/Tokyo',        # طوكيو UTC+9
    'UTC'                # التوقيت العالمي
]

# ===== إعدادات الشبكة =====

# إعدادات timeout للطلبات
NETWORK_TIMEOUTS = {
    'mt5_connection': 10,      # ثواني للاتصال بـ MT5
    'gemini_request': 30,      # ثواني لطلبات Gemini
    'telegram_request': 20,    # ثواني لطلبات Telegram
    'general_request': 15      # ثواني للطلبات العامة
}

# إعادة المحاولة
RETRY_SETTINGS = {
    'max_retries': 3,          # أقصى عدد محاولات
    'retry_delay': 5,          # تأخير بين المحاولات (ثواني)
    'exponential_backoff': True # زيادة التأخير تدريجياً
}

# ===== إعدادات التطوير والاختبار =====

# وضع التطوير
DEVELOPMENT_MODE = False

# إعدادات الاختبار
TEST_SETTINGS = {
    'enabled': False,
    'mock_mt5_data': False,     # استخدام بيانات وهمية لـ MT5
    'mock_gemini_responses': False,  # استخدام ردود وهمية لـ Gemini
    'log_all_requests': False   # تسجيل جميع الطلبات
}

# إعدادات التصحيح
DEBUG_SETTINGS = {
    'verbose_logging': False,   # سجلات مفصلة
    'save_api_responses': False, # حفظ ردود API
    'print_analysis_details': False  # طباعة تفاصيل التحليل
}

# ===== تحذيرات وملاحظات =====

# تحذيرات مهمة
IMPORTANT_NOTES = """
⚠️ تحذيرات مهمة:

1. لا تشارك مفاتيح API مع أي شخص
2. استخدم حساب تجريبي أولاً للاختبار
3. تأكد من فهم المخاطر قبل التداول الحقيقي
4. اجعل كلمة مرور البوت قوية ومعقدة
5. احتفظ بنسخة احتياطية من إعداداتك

💡 نصائح:
- ابدأ بعتبة ثقة عالية (80+) للتأكد من جودة الإشارات
- راجع الإحصائيات بانتظام لتحسين الإعدادات
- استخدم وقف الخسارة دائماً
- لا تعتمد على البوت بنسبة 100% - استخدم تحليلك الشخصي أيضاً
"""

print(IMPORTANT_NOTES)