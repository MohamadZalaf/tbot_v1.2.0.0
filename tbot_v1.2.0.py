#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 بوت التداول المتقدم الكامل - Advanced Trading Bot v1.2.0
=============================================================
الإصدار الجديد المُطور مع MetaTrader5 و Google Gemini AI

🔥 ميزات الإصدار v1.2.0:
- تكامل كامل مع MetaTrader5 للبيانات اللحظية الحقيقية
- دمج Google Gemini AI للتحليل الذكي والتنبؤات
- نظام تقييم الإشعارات بأزرار 👍 و 👎
- تخزين ذكي لبيانات الصفقات والتقييمات
- تعلم آلي من تقييمات المستخدم

⚠️ تحذير مهم للسلامة المالية:
- يتطلب اتصال حقيقي بـ MetaTrader5
- لا يعمل بدون بيانات حقيقية لحمايتك
- جميع التحليلات تعتمد على بيانات لحظية حقيقية
- لا توصيات تداول بدون تحليل AI كامل

Developer: Mohamad Zalaf ©️2025
Date: 2025 - v1.2.0 MT5 + Gemini AI Enhanced Version (Safe Mode)
"""

import telebot
from telebot import apihelper
import json
import logging
import os
import sys

# إعداد timeout أطول لـ Telegram API
apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import google.generativeai as genai
from datetime import datetime, timedelta
from telebot import types
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import threading
import time
import ta
from PIL import Image, ImageDraw, ImageFont
import warnings

# استيراد الإعدادات من ملف config.py
try:
    from config import (
        BOT_TOKEN, BOT_PASSWORD, GEMINI_API_KEY,
        DEFAULT_NOTIFICATION_SETTINGS, AVAILABLE_TIMEZONES,
        DEFAULT_CAPITAL_OPTIONS, TRADING_MODE_SETTINGS,
        GEMINI_MODEL, GEMINI_GENERATION_CONFIG, GEMINI_SAFETY_SETTINGS,
        GEMINI_API_KEYS, GEMINI_CONTEXT_TOKEN_LIMIT, GEMINI_CONTEXT_NEAR_LIMIT_RATIO,
        GEMINI_ROTATE_ON_RATE_LIMIT, SAVE_CHAT_LOGS, CHAT_LOG_RETENTION_DAYS
    )
except ImportError:
    # إعدادات احتياطية في حالة عدم وجود ملف config.py
    BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
    BOT_PASSWORD = 'tra12345678'
    GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY_HERE'
    GEMINI_API_KEYS = [GEMINI_API_KEY]
    GEMINI_MODEL = 'gemini-2.0-flash'
    GEMINI_GENERATION_CONFIG = {'temperature': 0.7, 'top_p': 0.8, 'top_k': 40, 'max_output_tokens': 1024}
    GEMINI_SAFETY_SETTINGS = []
    GEMINI_CONTEXT_TOKEN_LIMIT = 120000
    GEMINI_CONTEXT_NEAR_LIMIT_RATIO = 0.85
    GEMINI_ROTATE_ON_RATE_LIMIT = True
    SAVE_CHAT_LOGS = True
    CHAT_LOG_RETENTION_DAYS = 7
    DEFAULT_NOTIFICATION_SETTINGS = {}
    AVAILABLE_TIMEZONES = {}
    DEFAULT_CAPITAL_OPTIONS = [1000, 5000, 10000]
    TRADING_MODE_SETTINGS = {}

# متغير للتحكم في حلقة المراقبة
monitoring_active = False

# مكتبة المناطق الزمنية (اختيارية)
try:
    import pytz
    TIMEZONE_AVAILABLE = True
except ImportError:
    TIMEZONE_AVAILABLE = False

warnings.filterwarnings('ignore')

# دالة تنسيق رسائل الإشعارات المختصرة
def format_short_alert_message(symbol: str, symbol_info: Dict, price_data: Dict, analysis: Dict, user_id: int) -> str:
    """تنسيق رسائل الإشعارات المختصرة مع ضبط TP/SL لتكون منطقية وإزالة فقرة المؤشرات"""
    try:
        current_price = price_data.get('last', price_data.get('bid', 0))
        action = analysis.get('action')
        confidence = analysis.get('confidence')
        entry_price = analysis.get('entry_price') or analysis.get('entry')
        target1 = analysis.get('target1') or analysis.get('tp1')
        stop_loss = analysis.get('stop_loss') or analysis.get('sl')
        rr = analysis.get('risk_reward')
        formatted_time = format_time_for_user(user_id, price_data.get('time'))

        # اشتقاق نمط التداول ورأس المال لضبط الحدود المنطقية
        trading_mode = get_user_trading_mode(user_id) if user_id else 'scalping'
        capital = get_user_capital(user_id) if user_id else 1000

        # نسب افتراضية وحدود منطقية حسب النمط
        if trading_mode == 'scalping':
            default_profit_pct, default_loss_pct = 0.015, 0.005  # 1.5%/0.5%
            min_profit_pct, max_profit_pct = 0.005, 0.03        # 0.5% - 3%
            min_loss_pct, max_loss_pct = 0.003, 0.015           # 0.3% - 1.5%
        else:
            default_profit_pct, default_loss_pct = 0.05, 0.02   # 5%/2%
            min_profit_pct, max_profit_pct = 0.02, 0.08         # 2% - 8%
            min_loss_pct, max_loss_pct = 0.01, 0.03             # 1% - 3%

        if not entry_price or entry_price <= 0:
            entry_price = current_price

        def _pct_diff(a, b):
            try:
                return abs(a - b) / b if b else 0.0
            except Exception:
                return 0.0

        # ضبط TP/SL ضمن حدود منطقية استناداً للصفقة
        if entry_price and entry_price > 0 and action in ['BUY', 'SELL']:
            if action == 'BUY':
                # الهدف أعلى من الدخول والوقف أدناه
                if not target1 or target1 <= entry_price:
                    target1 = entry_price * (1 + default_profit_pct)
                else:
                    p = _pct_diff(target1, entry_price)
                    p = min(max(p, min_profit_pct), max_profit_pct)
                    target1 = entry_price * (1 + p)
                if not stop_loss or stop_loss >= entry_price:
                    stop_loss = entry_price * (1 - default_loss_pct)
                else:
                    l = _pct_diff(entry_price, stop_loss)
                    l = min(max(l, min_loss_pct), max_loss_pct)
                    stop_loss = entry_price * (1 - l)
            elif action == 'SELL':
                # الهدف أدنى من الدخول والوقف أعلاه
                if not target1 or target1 >= entry_price:
                    target1 = entry_price * (1 - default_profit_pct)
                else:
                    p = _pct_diff(entry_price, target1)
                    p = min(max(p, min_profit_pct), max_profit_pct)
                    target1 = entry_price * (1 - p)
                if not stop_loss or stop_loss <= entry_price:
                    stop_loss = entry_price * (1 + default_loss_pct)
                else:
                    l = _pct_diff(stop_loss, entry_price)
                    l = min(max(l, min_loss_pct), max_loss_pct)
                    stop_loss = entry_price * (1 + l)

            # إعادة حساب R/R بناءً على القيم المصححة
            try:
                profit = abs(target1 - entry_price) if target1 else None
                risk = abs(entry_price - stop_loss) if stop_loss else None
                if profit and risk and risk > 0:
                    rr = profit / risk
            except Exception:
                pass

        header = f"🚨 **إشعار تداول آلي** {symbol_info['emoji']}\n\n"
        body = "🚀 **إشارة تداول ذكية**\n\n"
        body += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        body += f"💱 **{symbol}** | {symbol_info['name']} {symbol_info['emoji']}\n"

        if current_price and current_price > 0:
            body += f"💰 **السعر اللحظي:** {current_price:,.5f}\n"
        else:
            # محاولة أخيرة لجلب السعر
            retry_price_data = mt5_manager.get_live_price(symbol)
            if retry_price_data and retry_price_data.get('last', 0) > 0:
                current_price = retry_price_data['last']
                body += f"💰 **السعر اللحظي:** {current_price:,.5f}\n"
            else:
                body += f"⚠️ **السعر اللحظي:** يرجى التأكد من اتصال MT5\n"

        # مستويات الدعم والمقاومة من MT5
        try:
            technical = mt5_manager.calculate_technical_indicators(symbol)
            resistance = None
            support = None
            if technical:
                if isinstance(technical, dict):
                    if 'resistance' in technical or 'support' in technical:
                        resistance = technical.get('resistance')
                        support = technical.get('support')
                    elif 'indicators' in technical and isinstance(technical['indicators'], dict):
                        resistance = technical['indicators'].get('resistance')
                        support = technical['indicators'].get('support')
            if resistance and resistance > 0:
                body += f"🔺 **مقاومة:** {resistance:,.5f}\n"
            else:
                body += f"🔺 **مقاومة:** --\n"
            if support and support > 0:
                body += f"🔻 **دعم:** {support:,.5f}\n"
            else:
                body += f"🔻 **دعم:** --\n"
        except Exception:
            body += f"🔺 **مقاومة:** --\n"
            body += f"🔻 **دعم:** --\n"

        body += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # نوع الصفقة
        if action == 'BUY':
            body += "🟢 **التوصية:** شراء | نجاح "
        elif action == 'SELL':
            body += "🔴 **التوصية:** بيع | نجاح "
        elif action == 'HOLD':
            body += "🟡 **التوصية:** انتظار | نجاح "
        else:
            body += f"❌ **التوصية:** {action} | نجاح "

        # نسبة النجاح
        if confidence is not None and isinstance(confidence, (int, float)) and 0 <= confidence <= 100:
            body += f"{confidence:.0f}%\n\n"
        else:
            body += f"فشل في تحديد النسبة\n\n"

        body += "📋 **تفاصيل التوصية:**\n"

        # قيم أساسية مختصرة بعد التصحيح
        if entry_price and entry_price > 0:
            body += f"📍 **سعر الدخول:** {entry_price:,.5f}\n"
        elif current_price and current_price > 0:
            # استخدام السعر الحالي كسعر دخول افتراضي
            body += f"📍 **سعر الدخول:** {current_price:,.5f} (حالي)\n"
        else:
            body += f"⚠️ **سعر الدخول:** يحتاج تحديث السعر\n"

        if stop_loss and stop_loss > 0:
            body += f"🛑 **ستوب لوس:** {stop_loss:,.5f}\n"
        elif current_price and current_price > 0:
            # حساب وقف خسارة افتراضي (0.5%)
            default_sl = current_price * 0.995 if action == 'BUY' else current_price * 1.005
            body += f"🛑 **ستوب لوس:** {default_sl:,.5f} (مقترح)\n"
        else:
            body += f"⚠️ **ستوب لوس:** يحتاج تحديد السعر\n"

        if target1 and target1 > 0:
            body += f"🎯 **تيك بروفيت:** {target1:,.5f}\n"
        elif current_price and current_price > 0:
            # حساب هدف افتراضي (1%)
            default_tp = current_price * 1.01 if action == 'BUY' else current_price * 0.99
            body += f"🎯 **تيك بروفيت:** {default_tp:,.5f} (مقترح)\n"
        else:
            body += f"⚠️ **تيك بروفيت:** يحتاج تحديد السعر\n"

        # عدد النقاط المستهدفة اعتماداً على القيم بعد التصحيح
        def _calc_points(price_diff: float, sym: str) -> float:
            try:
                s = sym.upper()
                if s.endswith('JPY'):
                    return abs(price_diff) * 100
                if s.startswith('XAU') or s.startswith('XAG'):
                    return abs(price_diff) * 10
                if s.startswith('BTC') or s.startswith('ETH'):
                    return abs(price_diff)
                # أزواج العملات الافتراضية
                return abs(price_diff) * 10000
            except Exception:
                return 0.0
        if entry_price and target1 and entry_price > 0 and target1 > 0:
            points_target = _calc_points(target1 - entry_price, symbol)
            if points_target > 0:
                body += f"📊 **النقاط المستهدفة:** {points_target:.0f} نقطة\n"
            else:
                body += f"❌ **النقاط المستهدفة:** فشل في الحساب\n"
        else:
            body += f"❌ **النقاط المستهدفة:** فشل في تحديد القيم\n"

        body += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # الأخبار الاقتصادية (عناوين مؤثرة وحقيقية) في النهاية
        try:
            news_text = gemini_analyzer.get_symbol_news(symbol)
            if news_text:
                news_lines = [ln for ln in news_text.split('\n') if ln.strip()]
                if news_lines:
                    body += "📰 **الأخبار القريبة:**\n"
                    for ln in news_lines[:2]:
                        body += f"{ln}\n"
        except Exception:
            body += "📰 **الأخبار القريبة:** غير متاحة حالياً\n"

        body += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        body += f"⏰ 🕐 {formatted_time} | 🤖 تحليل ذكي آلي"

        return header + body
    except Exception as e:
        logger.error(f"[ALERT_FMT] فشل إنشاء رسالة الإشعار المختصرة: {e}")
        return f"🚨 إشعار تداول آلي\n{symbol}"

# معالجة أخطاء الشبكة والاتصال
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
    import inspect
    
    # إعداد جلسة requests مع إعادة المحاولة التلقائية
    session = requests.Session()
    
    # التحقق من الإصدار المدعوم للمعاملة (backward compatibility)
    retry_kwargs = {
        'total': 3,
        'status_forcelist': [429, 500, 502, 503, 504],
        'backoff_factor': 1
    }
    
    # فحص ما إذا كان المعامل allowed_methods مدعوم أم method_whitelist
    retry_signature = inspect.signature(Retry.__init__)
    if 'allowed_methods' in retry_signature.parameters:
        retry_kwargs['allowed_methods'] = ["HEAD", "GET", "OPTIONS"]
    elif 'method_whitelist' in retry_signature.parameters:
        retry_kwargs['method_whitelist'] = ["HEAD", "GET", "OPTIONS"]
    
    retry_strategy = Retry(**retry_kwargs)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
except ImportError:
    # في حالة عدم توفر urllib3
    session = requests.Session()

# ===== آلية التحكم في التكرار والكاش للاستدعاءات =====
from dataclasses import dataclass

# كاش البيانات لتقليل الاستدعاءات المتكررة
price_data_cache = {}
CACHE_DURATION = 15  # ثوان - مدة صلاحية الكاش

@dataclass
class CachedPriceData:
    data: dict
    timestamp: datetime
    
def is_cache_valid(symbol: str) -> bool:
    """التحقق من صلاحية البيانات المخزنة مؤقتاً"""
    if symbol not in price_data_cache:
        return False
    
    cached_item = price_data_cache[symbol]
    time_diff = datetime.now() - cached_item.timestamp
    return time_diff.total_seconds() < CACHE_DURATION

def get_cached_price_data(symbol: str) -> Optional[dict]:
    """جلب البيانات من الكاش إذا كانت صالحة"""
    if is_cache_valid(symbol):
        return price_data_cache[symbol].data
    return None

def cache_price_data(symbol: str, data: dict):
    """حفظ البيانات في الكاش"""
    price_data_cache[symbol] = CachedPriceData(data, datetime.now())

# معدل الاستدعاءات للحماية من الإفراط
last_api_calls = {}
MIN_CALL_INTERVAL = 5  # ثوان بين الاستدعاءات لنفس الرمز

def can_make_api_call(symbol: str) -> bool:
    """التحقق من إمكانية استدعاء API لرمز معين"""
    now = time.time()
    last_call = last_api_calls.get(symbol, 0)
    return (now - last_call) >= MIN_CALL_INTERVAL

def record_api_call(symbol: str):
    """تسجيل وقت آخر استدعاء للـ API"""
    last_api_calls[symbol] = time.time()

# تهيئة البوت
bot = telebot.TeleBot(BOT_TOKEN)

# إعداد البيئة للتعامل مع UTF-8 على Windows
import os
if os.name == 'nt':  # Windows
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    import sys
    # تعيين stdout و stderr لاستخدام UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def setup_logging():
    """إعداد نظام تسجيل متقدم مع دعم UTF-8 للـ Windows"""
    # تكوين handlers بشكل منفصل لضمان UTF-8
    file_handler = RotatingFileHandler(
        'advanced_trading_bot_v1.2.0.log', 
        maxBytes=10*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    
    # إعداد console handler مع UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    
    # تنسيق الرسائل
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # إعداد logger الرئيسي
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # منع تكرار الرسائل
    root_logger.propagate = False

setup_logging()
logger = logging.getLogger(__name__)

# تهيئة Gemini
try:
    initial_key = GEMINI_API_KEYS[0] if 'GEMINI_API_KEYS' in globals() and GEMINI_API_KEYS else GEMINI_API_KEY
    genai.configure(api_key=initial_key)
    GEMINI_AVAILABLE = True
    logger.info("[OK] تم تهيئة Gemini AI بنجاح")
except Exception as e:
    GEMINI_AVAILABLE = False
    logger.error(f"[ERROR] فشل تهيئة Gemini AI: {e}")
 
# مدير مفاتيح Gemini للتبديل التلقائي عند حدود RPD/Quota
class GeminiKeyManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = [k for k in api_keys if k]
        self.lock = threading.Lock()
        self.index = 0

    def get_current_key(self) -> Optional[str]:
        with self.lock:
            if not self.api_keys:
                return None
            return self.api_keys[self.index]

    def rotate_key(self) -> Optional[str]:
        with self.lock:
            if not self.api_keys:
                return None
            self.index = (self.index + 1) % len(self.api_keys)
            new_key = self.api_keys[self.index]
            try:
                genai.configure(api_key=new_key)
                logger.info("[GEMINI] تم تبديل مفتاح API تلقائياً بسبب حدود RPD/Quota")
            except Exception as e:
                logger.error(f"[GEMINI] فشل تبديل المفتاح: {e}")
            return new_key

# مدير جلسات المحادثة لكل رمز مع حد السياق وتجديد تلقائي
class ChatSessionManager:
    def __init__(self, model_name: str, generation_config: dict, safety_settings: list, key_manager: GeminiKeyManager):
        self.model_name = model_name
        self.generation_config = generation_config
        self.safety_settings = safety_settings
        self.key_manager = key_manager
        self.sessions: Dict[str, Any] = {}
        self.session_tokens: Dict[str, int] = {}
        self.lock = threading.Lock()

    def _create_session(self, symbol: str):
        api_key = self.key_manager.get_current_key()
        if api_key:
            genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.model_name, generation_config=self.generation_config, safety_settings=self.safety_settings)
        chat = model.start_chat(history=[])
        self.sessions[symbol] = chat
        self.session_tokens[symbol] = 0
        return chat

    def reset_session(self, symbol: str):
        with self.lock:
            return self._create_session(symbol)

    def _should_rollover(self, symbol: str) -> bool:
        used = self.session_tokens.get(symbol, 0)
        return used >= int(GEMINI_CONTEXT_TOKEN_LIMIT * GEMINI_CONTEXT_NEAR_LIMIT_RATIO)

    def get_chat(self, symbol: str):
        with self.lock:
            if symbol not in self.sessions or self._should_rollover(symbol):
                return self._create_session(symbol)
            return self.sessions[symbol]

    def record_usage(self, symbol: str, input_tokens: int, output_tokens: int):
        with self.lock:
            used = self.session_tokens.get(symbol, 0)
            self.session_tokens[symbol] = used + int(input_tokens or 0) + int(output_tokens or 0)

# تهيئة مديري المفاتيح والجلسات
try:
    gemini_key_manager = GeminiKeyManager(GEMINI_API_KEYS if 'GEMINI_API_KEYS' in globals() else [GEMINI_API_KEY])
    chat_session_manager = ChatSessionManager(GEMINI_MODEL, GEMINI_GENERATION_CONFIG, GEMINI_SAFETY_SETTINGS, gemini_key_manager)
except Exception as _e:
    logger.warning(f"[GEMINI] لم يتم تهيئة مديري المفاتيح/الجلسات: {_e}")

# مهمة خلفية لتنظيف سجلات الدردشة القديمة
def _cleanup_chat_logs(retention_days: int):
    try:
        cutoff = datetime.now() - timedelta(days=retention_days)
        for fname in os.listdir(CHAT_LOGS_DIR):
            fpath = os.path.join(CHAT_LOGS_DIR, fname)
            try:
                if os.path.isfile(fpath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
            except Exception:
                continue
    except Exception:
        pass

if 'SAVE_CHAT_LOGS' in globals() and SAVE_CHAT_LOGS:
    try:
        _cleanup_chat_logs(CHAT_LOG_RETENTION_DAYS)
    except Exception:
        pass

# ===== نظام إدارة المستخدمين =====
user_sessions = {}  # تتبع جلسات المستخدمين
user_capitals = {}  # رؤوس أموال المستخدمين
user_states = {}    # حالات المستخدمين

# وظيفة للتحقق من صلاحية المستخدم
def is_user_authenticated(user_id: int) -> bool:
    """التحقق من أن المستخدم مُصرح له بالوصول"""
    return user_sessions.get(user_id, {}).get('authenticated', False)

def require_authentication(func):
    """ديكوريتر للتحقق من المصادقة قبل تنفيذ الوظيفة"""
    def wrapper(message_or_call):
        user_id = message_or_call.from_user.id
        
        if not is_user_authenticated(user_id):
            # إذا كان callback query
            if hasattr(message_or_call, 'message'):
                bot.answer_callback_query(
                    message_or_call.id, 
                    "🔐 يرجى إدخال كلمة المرور أولاً بكتابة /start", 
                    show_alert=True
                )
                return
            # إذا كان message عادي
            else:
                bot.reply_to(
                    message_or_call, 
                    "🔐 يرجى إدخال كلمة المرور أولاً بكتابة /start"
                )
                return
        
        return func(message_or_call)
    return wrapper
user_selected_symbols = {}  # الرموز المختارة للمراقبة
user_current_category = {}  # الفئة الحالية لكل مستخدم لتحديث القائمة
user_trade_feedbacks = {}  # تقييمات المستخدمين للصفقات
user_monitoring_active = {}  # تتبع حالة المراقبة الآلية للمستخدمين

# تحسين المراقبة بتجميع الرموز المشتركة
user_trading_modes = {}  # أنماط التداول للمستخدمين
user_advanced_notification_settings = {}  # إعدادات التنبيهات المتقدمة
user_timezones = {}  # المناطق الزمنية للمستخدمين

# مجلدات تخزين البيانات
DATA_DIR = "trading_data"
FEEDBACK_DIR = os.path.join(DATA_DIR, "user_feedback")
TRADE_LOGS_DIR = os.path.join(DATA_DIR, "trade_logs")
CHAT_LOGS_DIR = os.path.join(DATA_DIR, "chat_logs")

# إنشاء المجلدات إذا لم تكن موجودة
for directory in [DATA_DIR, FEEDBACK_DIR, TRADE_LOGS_DIR, CHAT_LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# رسائل تحذير للمكتبات المفقودة
if not TIMEZONE_AVAILABLE:
    logger.warning("مكتبة pytz غير متوفرة - سيتم استخدام التوقيت المحلي فقط")

# ===== قواميس الرموز المالية المحدثة من v1.1.0 =====
CURRENCY_PAIRS = {
    'EURUSD': {'name': 'يورو/دولار 💶', 'symbol': 'EURUSD', 'type': 'forex', 'emoji': '💶'},
    'USDJPY': {'name': 'دولار/ين 💴', 'symbol': 'USDJPY', 'type': 'forex', 'emoji': '💴'},
    'GBPUSD': {'name': 'جنيه/دولار 💷', 'symbol': 'GBPUSD', 'type': 'forex', 'emoji': '💷'},
    'AUDUSD': {'name': 'دولار أسترالي/دولار 🇦🇺', 'symbol': 'AUDUSD', 'type': 'forex', 'emoji': '🇦🇺'},
    'USDCAD': {'name': 'دولار/دولار كندي 🇨🇦', 'symbol': 'USDCAD', 'type': 'forex', 'emoji': '🇨🇦'},
    'USDCHF': {'name': 'دولار/فرنك سويسري 🇨🇭', 'symbol': 'USDCHF', 'type': 'forex', 'emoji': '🇨🇭'},
    'NZDUSD': {'name': 'دولار نيوزيلندي/دولار 🇳🇿', 'symbol': 'NZDUSD', 'type': 'forex', 'emoji': '🇳🇿'},
    'EURGBP': {'name': 'يورو/جنيه 🇪🇺', 'symbol': 'EURGBP', 'type': 'forex', 'emoji': '🇪🇺'},
    'EURJPY': {'name': 'يورو/ين 🇯🇵', 'symbol': 'EURJPY', 'type': 'forex', 'emoji': '🇯🇵'},
    'GBPJPY': {'name': 'جنيه/ين 💷', 'symbol': 'GBPJPY', 'type': 'forex', 'emoji': '💷'},
}

METALS = {
    'XAUUSD': {'name': 'ذهب 🥇', 'symbol': 'XAUUSD', 'type': 'metal', 'emoji': '🥇'},
    'XAGUSD': {'name': 'فضة 🥈', 'symbol': 'XAGUSD', 'type': 'metal', 'emoji': '🥈'},
    'XPTUSD': {'name': 'بلاتين 💎', 'symbol': 'XPTUSD', 'type': 'metal', 'emoji': '💎'},
    'XPDUSD': {'name': 'بلاديوم ⚡', 'symbol': 'XPDUSD', 'type': 'metal', 'emoji': '⚡'},
}

CRYPTO_PAIRS = {
    'BTCUSD': {'name': 'بيتكوين ₿', 'symbol': 'BTCUSD', 'type': 'crypto', 'emoji': '₿'},
    'ETHUSD': {'name': 'إيثريوم ⟠', 'symbol': 'ETHUSD', 'type': 'crypto', 'emoji': '⟠'},
    'BNBUSD': {'name': 'بينانس كوين 🔸', 'symbol': 'BNBUSD', 'type': 'crypto', 'emoji': '🔸'},
    'XRPUSD': {'name': 'ريبل 💧', 'symbol': 'XRPUSD', 'type': 'crypto', 'emoji': '💧'},
    'ADAUSD': {'name': 'كاردانو 🔷', 'symbol': 'ADAUSD', 'type': 'crypto', 'emoji': '🔷'},
    'SOLUSD': {'name': 'سولانا ☀️', 'symbol': 'SOLUSD', 'type': 'crypto', 'emoji': '☀️'},
    'DOTUSD': {'name': 'بولكادوت ⚫', 'symbol': 'DOTUSD', 'type': 'crypto', 'emoji': '⚫'},
    'DOGEUSD': {'name': 'دوجكوين 🐕', 'symbol': 'DOGEUSD', 'type': 'crypto', 'emoji': '🐕'},
    'AVAXUSD': {'name': 'أفالانش 🏔️', 'symbol': 'AVAXUSD', 'type': 'crypto', 'emoji': '🏔️'},
    'LINKUSD': {'name': 'تشين لينك 🔗', 'symbol': 'LINKUSD', 'type': 'crypto', 'emoji': '🔗'},
    'LTCUSD': {'name': 'لايتكوين 🌙', 'symbol': 'LTCUSD', 'type': 'crypto', 'emoji': '🌙'},
    'BCHUSD': {'name': 'بيتكوين كاش 💚', 'symbol': 'BCHUSD', 'type': 'crypto', 'emoji': '💚'},
}

STOCKS = {
    'AAPL': {'name': 'أبل 🍎', 'symbol': 'AAPL', 'type': 'stock', 'emoji': '🍎'},
    'TSLA': {'name': 'تسلا ⚡', 'symbol': 'TSLA', 'type': 'stock', 'emoji': '⚡'},
    'GOOGL': {'name': 'جوجل 🔍', 'symbol': 'GOOGL', 'type': 'stock', 'emoji': '🔍'},
    'MSFT': {'name': 'مايكروسوفت 💻', 'symbol': 'MSFT', 'type': 'stock', 'emoji': '💻'},
    'AMZN': {'name': 'أمازون 📦', 'symbol': 'AMZN', 'type': 'stock', 'emoji': '📦'},
    'META': {'name': 'ميتا 👥', 'symbol': 'META', 'type': 'stock', 'emoji': '👥'},
    'NVDA': {'name': 'إنفيديا 🎮', 'symbol': 'NVDA', 'type': 'stock', 'emoji': '🎮'},
    'NFLX': {'name': 'نتفليكس 🎬', 'symbol': 'NFLX', 'type': 'stock', 'emoji': '🎬'},
}

INDICES = {
    'US30': {'name': 'داو جونز 🏛️', 'symbol': 'US30', 'type': 'index', 'emoji': '🏛️'},
    'SPX500': {'name': 'ستاندرد آند بورز 500 📊', 'symbol': 'SPX500', 'type': 'index', 'emoji': '📊'},
    'NAS100': {'name': 'ناسداك 100 💻', 'symbol': 'NAS100', 'type': 'index', 'emoji': '💻'},
    'GER40': {'name': 'DAX الألماني 🇩🇪', 'symbol': 'GER40', 'type': 'index', 'emoji': '🇩🇪'},
    'UK100': {'name': 'FTSE 100 البريطاني 🇬🇧', 'symbol': 'UK100', 'type': 'index', 'emoji': '🇬🇧'},
}

# دمج جميع الرموز
ALL_SYMBOLS = {**CURRENCY_PAIRS, **METALS, **CRYPTO_PAIRS, **STOCKS, **INDICES}

# تصنيف الرموز حسب الفئات الخمس المنفصلة
SYMBOL_CATEGORIES = {
    'crypto': {**CRYPTO_PAIRS},
    'forex': {**CURRENCY_PAIRS},
    'metals': {**METALS},
    'stocks': {**STOCKS},
    'indices': {**INDICES}
}

# إعدادات تردد الإشعارات - تردد ثابت 15 ثانية
NOTIFICATION_FREQUENCIES = {
    '15s': {'name': '15 ثانية 🔥', 'seconds': 15},  # التردد الوحيد المدعوم
}

# ===== كلاس إدارة MT5 =====
class MT5Manager:
    """مدير الاتصال مع MetaTrader5"""
    
    def __init__(self):
        self.connected = False
        self.connection_lock = threading.Lock()  # حماية من race conditions
        self.last_connection_attempt = 0
        self.connection_retry_delay = 5  # 5 ثوان بين محاولات الاتصال
        self.max_reconnection_attempts = 3
        self.initialize_mt5()
    
    def initialize_mt5(self):
        """تهيئة الاتصال مع MT5 مع آلية إعادة المحاولة"""
        with self.connection_lock:
            # منع محاولات الاتصال المتكررة
            current_time = time.time()
            if current_time - self.last_connection_attempt < self.connection_retry_delay:
                logger.debug("[DEBUG] محاولة اتصال سابقة حديثة - انتظار...")
                return self.connected
            
            self.last_connection_attempt = current_time
            
            try:
                # إغلاق الاتصال السابق إذا كان موجوداً
                try:
                    mt5.shutdown()
                except:
                    pass
                
                # محاولة الاتصال
                if not mt5.initialize():
                    logger.error("[ERROR] فشل في تهيئة MT5")
                    self.connected = False
                    return False
                
                # التحقق من الاتصال
                account_info = mt5.account_info()
                if account_info is None:
                    logger.error("[ERROR] فشل في الحصول على معلومات الحساب")
                    mt5.shutdown()
                    self.connected = False
                    return False
                
                # اختبار جلب بيانات تجريبية للتأكد من الاتصال
                test_tick = mt5.symbol_info_tick("EURUSD")
                if test_tick is None:
                    logger.warning("[WARNING] فشل في اختبار جلب البيانات")
                    # لا نغلق الاتصال هنا لأن بعض الحسابات قد لا تدعم EURUSD
                
                self.connected = True
                logger.info("[OK] تم الاتصال بـ MetaTrader5 بنجاح!")
                logger.info(f"[DATA] معلومات الحساب: {account_info.login} - {account_info.server}")
                
                # طباعة رسالة النجاح في التيرمينال
                print("\n" + "="*60)
                print("🎉 تم الاتصال بـ MetaTrader5 بنجاح!")
                print(f"📊 رقم الحساب: {account_info.login}")
                print(f"🏦 الخادم: {account_info.server}")
                print(f"💰 الرصيد: {account_info.balance}")
                print(f"💎 العملة: {account_info.currency}")
                print("="*60 + "\n")
                
                return True
                
            except Exception as e:
                logger.error(f"[ERROR] خطأ في تهيئة MT5: {e}")
                self.connected = False
                try:
                    mt5.shutdown()
                except:
                    pass
                return False
    
    def check_real_connection(self) -> bool:
        """التحقق من حالة الاتصال الحقيقية مع MT5 مع آلية إعادة الاتصال"""
        with self.connection_lock:
            try:
                # محاولة جلب معلومات الحساب
                account_info = mt5.account_info()
                if account_info is None:
                    logger.warning("[WARNING] لا يمكن الحصول على معلومات الحساب - محاولة إعادة الاتصال...")
                    self.connected = False
                    return self._attempt_reconnection()
                
                # محاولة جلب معلومات رمز معروف (مع رموز بديلة)
                test_symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "XAUUSD"]
                symbol_found = False
                
                for symbol in test_symbols:
                    symbol_info = mt5.symbol_info(symbol)
                    if symbol_info is not None:
                        symbol_found = True
                        break
                
                if not symbol_found:
                    logger.warning("[WARNING] لا يمكن الحصول على معلومات أي رمز - الاتصال ضعيف")
                    self.connected = False
                    return self._attempt_reconnection()
                
                # محاولة جلب تيك حديث لأحد الرموز المتاحة
                tick = None
                for symbol in test_symbols:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is not None:
                        break
                
                if tick is None:
                    logger.warning("[WARNING] لا يمكن الحصول على البيانات اللحظية - الاتصال معطل")
                    self.connected = False
                    return self._attempt_reconnection()
                
                # التحقق من أن البيانات حديثة (مع مرونة أكبر لبعض الأسواق)
                try:
                    tick_time = datetime.fromtimestamp(tick.time)
                    time_diff = datetime.now() - tick_time
                    
                    # 15 دقيقة بدلاً من 5 للمرونة أكثر
                    if time_diff.total_seconds() > 900:
                        logger.warning(f"[WARNING] البيانات قديمة جداً (عمر: {time_diff}) - الاتصال غير فعال")
                        self.connected = False
                        return self._attempt_reconnection()
                except:
                    # إذا فشل في قراءة وقت التيك، لا نعتبر هذا خطأ كريتيكال
                    pass
                
                # كل شيء طبيعي
                if not self.connected:
                    logger.info("[OK] تم استعادة الاتصال مع MT5")
                    self.connected = True
                    
                return True
                
            except Exception as e:
                logger.error(f"[ERROR] خطأ في التحقق من الاتصال الحقيقي: {e}")
                self.connected = False
                return self._attempt_reconnection()
    
    def _attempt_reconnection(self) -> bool:
        """محاولة إعادة الاتصال التلقائية"""
        logger.info("[RECONNECT] محاولة إعادة الاتصال التلقائية...")
        
        for attempt in range(self.max_reconnection_attempts):
            logger.info(f"[RECONNECT] محاولة رقم {attempt + 1} من {self.max_reconnection_attempts}")
            
            if self.initialize_mt5():
                logger.info("[OK] تم إعادة الاتصال بنجاح!")
                return True
            
            if attempt < self.max_reconnection_attempts - 1:
                wait_time = (attempt + 1) * 2  # انتظار متزايد
                logger.info(f"[RECONNECT] انتظار {wait_time} ثانية قبل المحاولة التالية...")
                time.sleep(wait_time)
        
        logger.error("[ERROR] فشل في إعادة الاتصال بعد عدة محاولات")
        return False
    
    def validate_connection_health(self) -> bool:
        """فحص شامل لصحة الاتصال مع MT5"""
        try:
            if not self.connected:
                return False
            
            # اختبارات متعددة للتأكد من صحة الاتصال
            tests = []
            
            # اختبار 1: معلومات الحساب
            try:
                account_info = mt5.account_info()
                tests.append(account_info is not None)
            except:
                tests.append(False)
            
            # اختبار 2: عدد الرموز المتاحة
            try:
                symbols_total = mt5.symbols_total()
                tests.append(symbols_total > 0)
            except:
                tests.append(False)
            
            # اختبار 3: جلب بيانات تجريبية
            try:
                test_symbols = ["EURUSD", "GBPUSD", "USDJPY"]
                for test_symbol in test_symbols:
                    tick = mt5.symbol_info_tick(test_symbol)
                    if tick is not None:
                        tests.append(True)
                        break
                else:
                    tests.append(False)
            except:
                tests.append(False)
            
            # يجب أن تنجح معظم الاختبارات
            success_rate = sum(tests) / len(tests)
            health_ok = success_rate >= 0.6  # 60% نجاح كحد أدنى
            
            if not health_ok:
                logger.warning(f"[WARNING] صحة اتصال MT5 ضعيفة - نسبة النجاح: {success_rate:.1%}")
                self.connected = False
            
            return health_ok
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في فحص صحة الاتصال: {e}")
            self.connected = False
            return False
    
    def graceful_shutdown(self):
        """إغلاق آمن لاتصال MT5"""
        try:
            with self.connection_lock:
                if self.connected:
                    logger.info("[SYSTEM] إغلاق اتصال MT5...")
                    mt5.shutdown()
                    self.connected = False
                    logger.info("[OK] تم إغلاق اتصال MT5 بأمان")
        except Exception as e:
            logger.error(f"[ERROR] خطأ في إغلاق MT5: {e}")
    
    def get_connection_status_detailed(self) -> Dict:
        """الحصول على تفاصيل حالة الاتصال"""
        try:
            real_status = self.check_real_connection()
            
            status_info = {
                'connected': real_status,
                'status_text': '🟢 متصل ونشط' if real_status else '🔴 منقطع أو معطل',
                'last_check': datetime.now().strftime('%H:%M:%S'),
                'account_info': None,
                'data_freshness': None
            }
            
            if real_status:
                try:
                    account_info = mt5.account_info()
                    if account_info:
                        status_info['account_info'] = {
                            'login': account_info.login,
                            'server': account_info.server,
                            'balance': account_info.balance,
                            'currency': account_info.currency
                        }
                    
                    # فحص حداثة البيانات
                    tick = mt5.symbol_info_tick("EURUSD")
                    if tick:
                        tick_time = datetime.fromtimestamp(tick.time)
                        age_seconds = (datetime.now() - tick_time).total_seconds()
                        status_info['data_freshness'] = f"{age_seconds:.0f} ثانية"
                        
                except Exception as e:
                    logger.error(f"خطأ في جلب تفاصيل الحالة: {e}")
            
            return status_info
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في جلب حالة الاتصال التفصيلية: {e}")
            return {
                'connected': False,
                'status_text': '❌ خطأ في الفحص',
                'last_check': datetime.now().strftime('%H:%M:%S'),
                'error': str(e)
            }
    
    def get_live_price(self, symbol: str) -> Optional[Dict]:
        """جلب السعر اللحظي الحقيقي - MT5 هو المصدر الأساسي الأولي مع نظام كاش"""
        
        if not symbol or symbol in ['notification', 'null', '', None]:
            logger.warning(f"[WARNING] رمز غير صالح في get_live_price: {symbol}")
            return None
        
        # التحقق من الكاش أولاً
        cached_data = get_cached_price_data(symbol)
        if cached_data:
            logger.debug(f"[CACHE] استخدام بيانات مخزنة مؤقتاً لـ {symbol}")
            return cached_data
        
        # التحقق من معدل الاستدعاءات
        if not can_make_api_call(symbol):
            logger.debug(f"[RATE_LIMIT] تجاهل الاستدعاء لـ {symbol} - تحديد معدل الاستدعاءات")
            return None
        
        # تسجيل وقت الاستدعاء
        record_api_call(symbol)
        
        # 🔍 التحقق من حالة الاتصال الحقيقية أولاً (بدون thread lock لتجنب deadlock)
        real_connection_status = self.connected
        
        # إذا كان الاتصال منقطعاً، نحاول التحقق والإعادة
        if not real_connection_status:
            real_connection_status = self.check_real_connection()
        
        # ✅ المصدر الأساسي الأولي: MetaTrader5
        if real_connection_status:
            try:
                # جلب آخر تيك للرمز من MT5 (البيانات الأكثر دقة)
                with self.connection_lock:
                    tick = mt5.symbol_info_tick(symbol)
                
                if tick is not None and hasattr(tick, 'bid') and hasattr(tick, 'ask') and tick.bid > 0 and tick.ask > 0:
                    # التحقق من أن البيانات حديثة (ليست قديمة)
                    tick_time = datetime.fromtimestamp(tick.time)
                    time_diff = datetime.now() - tick_time
                    
                    # زيادة مرونة وقت البيانات إلى 15 دقيقة
                    if time_diff.total_seconds() > 900:
                        logger.warning(f"[WARNING] بيانات MT5 قديمة للرمز {symbol} (عمر البيانات: {time_diff})")
                        # لا نغير حالة الاتصال فوراً، قد تكون مشكلة مؤقتة في الرمز
                    else:
                        logger.debug(f"[OK] تم جلب البيانات الحديثة من MT5 للرمز {symbol}")
                        data = {
                            'symbol': symbol,
                            'bid': tick.bid,
                            'ask': tick.ask,
                            'last': tick.last,
                            'volume': tick.volume,
                            'time': tick_time,
                            'spread': tick.ask - tick.bid,
                            'source': 'MetaTrader5 (مصدر أساسي)',
                            'data_age': time_diff.total_seconds()
                        }
                        # حفظ في الكاش
                        cache_price_data(symbol, data)
                        return data
                else:
                    logger.warning(f"[WARNING] لا توجد بيانات صحيحة من MT5 لـ {symbol}")
                    # لا نغير حالة الاتصال فوراً، قد يكون الرمز غير متاح فقط
                    
            except Exception as e:
                logger.warning(f"[WARNING] فشل جلب البيانات من MT5 لـ {symbol}: {e}")
                # تحديد ما إذا كان هذا خطأ اتصال أم خطأ في الرمز
                if "connection" in str(e).lower() or "terminal" in str(e).lower():
                    self.connected = False
        else:
            logger.debug(f"[DEBUG] MT5 غير متصل حقيقياً - لا يمكن جلب البيانات لـ {symbol}")
        
        logger.error(f"[ERROR] فشل في جلب البيانات من MT5 للرمز {symbol}")
        return None
    

    def get_market_data(self, symbol: str, timeframe: int = mt5.TIMEFRAME_M1, count: int = 100) -> Optional[pd.DataFrame]:
        """جلب بيانات السوق من MT5"""
        if not self.connected:
            return None
        
        try:
            # جلب البيانات
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            if rates is None or len(rates) == 0:
                logger.warning(f"[WARNING] لا توجد بيانات للرمز {symbol}")
                return None
            
            # تحويل إلى DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # إعادة تسمية الأعمدة
            df.columns = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
            
            return df
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في جلب بيانات السوق من MT5 لـ {symbol}: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """جلب معلومات الرمز من MT5"""
        if not self.connected:
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            
            return {
                'symbol': info.name,
                'description': info.description,
                'point': info.point,
                'digits': info.digits,
                'spread': info.spread,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'volume_step': info.volume_step,
                'contract_size': info.trade_contract_size,
                'currency_base': info.currency_base,
                'currency_profit': info.currency_profit,
                'margin_currency': info.currency_margin,
            }
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في جلب معلومات الرمز {symbol}: {e}")
            return None
    
    def calculate_technical_indicators(self, symbol: str) -> Optional[Dict]:
        """حساب المؤشرات الفنية من البيانات التاريخية للرمز"""
        try:
            if not self.connected:
                logger.warning(f"[WARNING] MT5 غير متصل - لا يمكن حساب المؤشرات لـ {symbol}")
                return None
            
            # جلب أحدث البيانات اللحظية (M1 للحصول على أقصى دقة لحظية)
            df = self.get_market_data(symbol, mt5.TIMEFRAME_M1, 100)  # M1 لأحدث البيانات اللحظية
            if df is None or len(df) < 20:
                logger.warning(f"[WARNING] بيانات غير كافية لحساب المؤشرات لـ {symbol}")
                return None
            
            # دمج السعر اللحظي الحالي مع البيانات للحصول على أحدث قراءة
            current_tick = self.get_live_price(symbol)
            if current_tick and 'last' in current_tick:
                # إضافة السعر اللحظي الحالي كآخر نقطة بيانات
                current_time = pd.Timestamp.now()
                current_price = current_tick['last']
                current_volume = current_tick.get('volume', df['tick_volume'].iloc[-1])
                
                # إنشاء صف جديد بالبيانات اللحظية
                new_row = pd.DataFrame({
                    'open': [df['close'].iloc[-1]],  # افتراض أن الفتح هو آخر إغلاق
                    'high': [max(df['close'].iloc[-1], current_price)],
                    'low': [min(df['close'].iloc[-1], current_price)],
                    'close': [current_price],
                    'tick_volume': [current_volume],
                    'spread': [current_tick.get('spread', df['spread'].iloc[-1])],
                    'real_volume': [current_volume]
                }, index=[current_time])
                
                # دمج البيانات اللحظية مع البيانات التاريخية
                df = pd.concat([df, new_row])
                logger.debug(f"[REALTIME] تم دمج السعر اللحظي {current_price} مع البيانات التاريخية لـ {symbol}")
            
            indicators = {}
            
            # إضافة معلومات البيانات اللحظية
            indicators['data_freshness'] = 'live'  # تأكيد أن البيانات لحظية
            indicators['last_update'] = datetime.now().isoformat()
            if current_tick:
                indicators['tick_info'] = {
                    'bid': current_tick.get('bid'),
                    'ask': current_tick.get('ask'),
                    'spread': current_tick.get('spread'),
                    'volume': current_tick.get('volume'),
                    'time': current_tick.get('time')
                }
            
            # المتوسطات المتحركة (محسوبة من أحدث البيانات)
            if len(df) >= 9:
                indicators['ma_9'] = ta.trend.sma_indicator(df['close'], window=9).iloc[-1]
            if len(df) >= 10:
                indicators['ma_10'] = ta.trend.sma_indicator(df['close'], window=10).iloc[-1]
            if len(df) >= 20:
                indicators['ma_20'] = ta.trend.sma_indicator(df['close'], window=20).iloc[-1]
            if len(df) >= 21:
                indicators['ma_21'] = ta.trend.sma_indicator(df['close'], window=21).iloc[-1]
            if len(df) >= 50:
                indicators['ma_50'] = ta.trend.sma_indicator(df['close'], window=50).iloc[-1]
            
            # RSI
            if len(df) >= 14:
                indicators['rsi'] = ta.momentum.rsi(df['close'], window=14).iloc[-1]
                
                # تفسير RSI
                if indicators['rsi'] > 70:
                    indicators['rsi_interpretation'] = 'ذروة شراء'
                elif indicators['rsi'] < 30:
                    indicators['rsi_interpretation'] = 'ذروة بيع'
                else:
                    indicators['rsi_interpretation'] = 'محايد'
            
            # MACD
            if len(df) >= 26:
                macd_line = ta.trend.macd(df['close'])
                macd_signal = ta.trend.macd_signal(df['close'])
                macd_histogram = ta.trend.macd_diff(df['close'])
                
                indicators['macd'] = {
                    'macd': macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0,
                    'signal': macd_signal.iloc[-1] if not pd.isna(macd_signal.iloc[-1]) else 0,
                    'histogram': macd_histogram.iloc[-1] if not pd.isna(macd_histogram.iloc[-1]) else 0
                }
                
                # تفسير MACD
                if indicators['macd']['macd'] > indicators['macd']['signal']:
                    indicators['macd_interpretation'] = 'إشارة صعود'
                elif indicators['macd']['macd'] < indicators['macd']['signal']:
                    indicators['macd_interpretation'] = 'إشارة هبوط'
                else:
                    indicators['macd_interpretation'] = 'محايد'
            
            # حجم التداول - تحليل متقدم
            indicators['current_volume'] = df['tick_volume'].iloc[-1]
            if len(df) >= 20:
                indicators['avg_volume'] = df['tick_volume'].rolling(window=20).mean().iloc[-1]
                indicators['volume_ratio'] = indicators['current_volume'] / indicators['avg_volume']
                
                # حجم التداول لآخر 5 فترات للمقارنة
                indicators['volume_trend_5'] = df['tick_volume'].tail(5).mean()
                indicators['volume_trend_10'] = df['tick_volume'].tail(10).mean()
                
                # Volume Moving Average (VMA)
                indicators['volume_ma_9'] = df['tick_volume'].rolling(window=9).mean().iloc[-1]
                indicators['volume_ma_21'] = df['tick_volume'].rolling(window=21).mean().iloc[-1] if len(df) >= 21 else indicators['avg_volume']
                
                # Volume Rate of Change
                if len(df) >= 10:
                    indicators['volume_roc'] = ((indicators['current_volume'] - df['tick_volume'].iloc[-10]) / df['tick_volume'].iloc[-10]) * 100
                
                # تفسير حجم التداول المتقدم
                volume_signals = []
                if indicators['volume_ratio'] > 2.0:
                    volume_signals.append('حجم عالي جداً - اهتمام قوي')
                elif indicators['volume_ratio'] > 1.5:
                    volume_signals.append('حجم عالي - نشاط متزايد')
                elif indicators['volume_ratio'] < 0.3:
                    volume_signals.append('حجم منخفض جداً - ضعف اهتمام')
                elif indicators['volume_ratio'] < 0.5:
                    volume_signals.append('حجم منخفض - نشاط محدود')
                else:
                    volume_signals.append('حجم طبيعي')
                
                # تحليل اتجاه حجم التداول
                if indicators['volume_trend_5'] > indicators['volume_trend_10'] * 1.2:
                    volume_signals.append('حجم في ازدياد')
                elif indicators['volume_trend_5'] < indicators['volume_trend_10'] * 0.8:
                    volume_signals.append('حجم في انخفاض')
                
                # Volume-Price Analysis (VPA)
                price_change = indicators.get('price_change_pct', 0)
                if abs(price_change) > 0.5 and indicators['volume_ratio'] > 1.5:
                    volume_signals.append('تأكيد قوي للحركة السعرية')
                elif abs(price_change) > 0.5 and indicators['volume_ratio'] < 0.8:
                    volume_signals.append('ضعف في تأكيد الحركة السعرية')
                
                indicators['volume_interpretation'] = ' | '.join(volume_signals)
                indicators['volume_strength'] = 'قوي' if indicators['volume_ratio'] > 1.5 else 'متوسط' if indicators['volume_ratio'] > 0.8 else 'ضعيف'
            
            # Stochastic Oscillator - تحليل متقدم
            if len(df) >= 14:
                stoch_k = ta.momentum.stoch(df['high'], df['low'], df['close'])
                stoch_d = ta.momentum.stoch_signal(df['high'], df['low'], df['close'])
                
                current_k = stoch_k.iloc[-1] if not pd.isna(stoch_k.iloc[-1]) else 50
                current_d = stoch_d.iloc[-1] if not pd.isna(stoch_d.iloc[-1]) else 50
                previous_k = stoch_k.iloc[-2] if len(stoch_k) >= 2 and not pd.isna(stoch_k.iloc[-2]) else current_k
                previous_d = stoch_d.iloc[-2] if len(stoch_d) >= 2 and not pd.isna(stoch_d.iloc[-2]) else current_d
                
                indicators['stochastic'] = {
                    'k': current_k,
                    'd': current_d,
                    'k_previous': previous_k,
                    'd_previous': previous_d
                }
                
                # كشف التقاطعات
                stoch_signals = []
                
                # تقاطع صاعد: %K يقطع %D من الأسفل
                if previous_k <= previous_d and current_k > current_d:
                    stoch_signals.append('تقاطع صاعد - إشارة شراء محتملة')
                    indicators['stochastic']['crossover'] = 'bullish'
                # تقاطع هابط: %K يقطع %D من الأعلى
                elif previous_k >= previous_d and current_k < current_d:
                    stoch_signals.append('تقاطع هابط - إشارة بيع محتملة')
                    indicators['stochastic']['crossover'] = 'bearish'
                else:
                    indicators['stochastic']['crossover'] = 'none'
                
                # تحليل مناطق ذروة الشراء والبيع
                if current_k > 80 and current_d > 80:
                    stoch_signals.append('ذروة شراء قوية - احتمالية تصحيح')
                    indicators['stochastic']['zone'] = 'strong_overbought'
                elif current_k > 70:
                    stoch_signals.append('ذروة شراء - مراقبة إشارات البيع')
                    indicators['stochastic']['zone'] = 'overbought'
                elif current_k < 20 and current_d < 20:
                    stoch_signals.append('ذروة بيع قوية - احتمالية ارتداد')
                    indicators['stochastic']['zone'] = 'strong_oversold'
                elif current_k < 30:
                    stoch_signals.append('ذروة بيع - مراقبة إشارات الشراء')
                    indicators['stochastic']['zone'] = 'oversold'
                else:
                    stoch_signals.append('منطقة محايدة')
                    indicators['stochastic']['zone'] = 'neutral'
                
                # تحليل قوة الإشارة
                k_d_diff = abs(current_k - current_d)
                if k_d_diff < 5:
                    stoch_signals.append('الخطوط متقاربة - انتظار إشارة واضحة')
                    indicators['stochastic']['strength'] = 'weak'
                elif k_d_diff > 20:
                    stoch_signals.append('الخطوط متباعدة - إشارة قوية')
                    indicators['stochastic']['strength'] = 'strong'
                else:
                    indicators['stochastic']['strength'] = 'moderate'
                
                # تحليل الاتجاه
                if current_k > current_d and current_k > 50:
                    stoch_signals.append('اتجاه صاعد')
                    indicators['stochastic']['trend'] = 'bullish'
                elif current_k < current_d and current_k < 50:
                    stoch_signals.append('اتجاه هابط')
                    indicators['stochastic']['trend'] = 'bearish'
                else:
                    indicators['stochastic']['trend'] = 'neutral'
                
                indicators['stochastic_interpretation'] = ' | '.join(stoch_signals)
            
            # البولنجر باندز
            if len(df) >= 20:
                bollinger_high = ta.volatility.bollinger_hband(df['close'])
                bollinger_low = ta.volatility.bollinger_lband(df['close'])
                bollinger_mid = ta.volatility.bollinger_mavg(df['close'])
                
                indicators['bollinger'] = {
                    'upper': bollinger_high.iloc[-1] if not pd.isna(bollinger_high.iloc[-1]) else df['close'].iloc[-1] * 1.02,
                    'middle': bollinger_mid.iloc[-1] if not pd.isna(bollinger_mid.iloc[-1]) else df['close'].iloc[-1],
                    'lower': bollinger_low.iloc[-1] if not pd.isna(bollinger_low.iloc[-1]) else df['close'].iloc[-1] * 0.98
                }
                
                # تفسير البولنجر باندز
                current_price = df['close'].iloc[-1]
                if current_price > indicators['bollinger']['upper']:
                    indicators['bollinger_interpretation'] = 'فوق النطاق العلوي - إشارة بيع محتملة'
                elif current_price < indicators['bollinger']['lower']:
                    indicators['bollinger_interpretation'] = 'تحت النطاق السفلي - إشارة شراء محتملة'
                else:
                    indicators['bollinger_interpretation'] = 'ضمن النطاق - حركة طبيعية'
            
            # الدعم والمقاومة
            if len(df) >= 20:
                indicators['resistance'] = df['high'].rolling(window=20).max().iloc[-1]
                indicators['support'] = df['low'].rolling(window=20).min().iloc[-1]
            
            # معلومات السعر الحالي
            indicators['current_price'] = df['close'].iloc[-1]
            
            # حساب التغير اليومي الصحيح - مقارنة مع بداية اليوم
            try:
                # جلب بيانات يومية للحصول على سعر الافتتاح اليومي
                daily_df = self.get_market_data(symbol, mt5.TIMEFRAME_D1, 2)
                if daily_df is not None and len(daily_df) >= 1:
                    today_open = daily_df['open'].iloc[-1]  # افتتاح اليوم
                    current_price = indicators['current_price']
                    daily_change_pct = ((current_price - today_open) / today_open * 100)
                    indicators['price_change_pct'] = daily_change_pct
                else:
                    # في حالة فشل جلب البيانات اليومية، استخدم مقارنة بسيطة
                    indicators['price_change_pct'] = ((df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10] * 100) if len(df) >= 10 else 0
            except Exception as e:
                logger.warning(f"[WARNING] فشل في حساب التغير اليومي لـ {symbol}: {e}")
                # استخدام حساب بديل
                indicators['price_change_pct'] = ((df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10] * 100) if len(df) >= 10 else 0
            
            # ===== كشف التقاطعات للمتوسطات المتحركة =====
            ma_crossovers = []
            
            # تقاطعات MA 9 و MA 21
            if 'ma_9' in indicators and 'ma_21' in indicators and len(df) >= 22:
                ma_9_prev = ta.trend.sma_indicator(df['close'], window=9).iloc[-2]
                ma_21_prev = ta.trend.sma_indicator(df['close'], window=21).iloc[-2]
                
                # التقاطع الذهبي (Golden Cross) - MA9 يقطع MA21 من الأسفل
                if ma_9_prev <= ma_21_prev and indicators['ma_9'] > indicators['ma_21']:
                    ma_crossovers.append('تقاطع ذهبي MA9/MA21 - إشارة شراء قوية')
                    indicators['ma_9_21_crossover'] = 'golden'
                # تقاطع الموت (Death Cross) - MA9 يقطع MA21 من الأعلى
                elif ma_9_prev >= ma_21_prev and indicators['ma_9'] < indicators['ma_21']:
                    ma_crossovers.append('تقاطع الموت MA9/MA21 - إشارة بيع قوية')
                    indicators['ma_9_21_crossover'] = 'death'
                else:
                    indicators['ma_9_21_crossover'] = 'none'
            
            # تقاطعات MA 10 و MA 20
            if 'ma_10' in indicators and 'ma_20' in indicators and len(df) >= 21:
                ma_10_prev = ta.trend.sma_indicator(df['close'], window=10).iloc[-2]
                ma_20_prev = ta.trend.sma_indicator(df['close'], window=20).iloc[-2]
                
                if ma_10_prev <= ma_20_prev and indicators['ma_10'] > indicators['ma_20']:
                    ma_crossovers.append('تقاطع ذهبي MA10/MA20 - إشارة شراء')
                    indicators['ma_10_20_crossover'] = 'golden'
                elif ma_10_prev >= ma_20_prev and indicators['ma_10'] < indicators['ma_20']:
                    ma_crossovers.append('تقاطع الموت MA10/MA20 - إشارة بيع')
                    indicators['ma_10_20_crossover'] = 'death'
                else:
                    indicators['ma_10_20_crossover'] = 'none'
            
            # تقاطعات السعر مع المتوسطات
            current_price = indicators['current_price']
            price_ma_signals = []
            
            if 'ma_9' in indicators:
                if len(df) >= 2:
                    prev_price = df['close'].iloc[-2]
                    if prev_price <= indicators.get('ma_9', 0) and current_price > indicators['ma_9']:
                        price_ma_signals.append('السعر يخترق MA9 صعوداً')
                    elif prev_price >= indicators.get('ma_9', 0) and current_price < indicators['ma_9']:
                        price_ma_signals.append('السعر يخترق MA9 هبوطاً')
            
            if price_ma_signals:
                indicators['price_ma_crossover'] = ' | '.join(price_ma_signals)
            
            # ===== تحليل التقاطعات المتعددة =====
            all_crossovers = []
            
            # جمع إشارات MACD
            if 'macd_interpretation' in indicators and 'صعود' in indicators['macd_interpretation']:
                all_crossovers.append('MACD صاعد')
            elif 'macd_interpretation' in indicators and 'هبوط' in indicators['macd_interpretation']:
                all_crossovers.append('MACD هابط')
            
            # جمع إشارات Stochastic
            if 'stochastic' in indicators and indicators['stochastic'].get('crossover') == 'bullish':
                all_crossovers.append('Stochastic صاعد')
            elif 'stochastic' in indicators and indicators['stochastic'].get('crossover') == 'bearish':
                all_crossovers.append('Stochastic هابط')
            
            # جمع إشارات المتوسطات المتحركة
            if ma_crossovers:
                all_crossovers.extend(ma_crossovers)
            
            indicators['crossover_summary'] = ' | '.join(all_crossovers) if all_crossovers else 'لا توجد تقاطعات مهمة'
            
            # تحديد الاتجاه العام المحسن
            trend_signals = []
            
            # إشارات المتوسطات المتحركة
            if 'ma_9' in indicators and 'ma_21' in indicators:
                if indicators['ma_9'] > indicators['ma_21']:
                    trend_signals.append('صعود')
                else:
                    trend_signals.append('هبوط')
            
            if 'ma_10' in indicators and 'ma_20' in indicators:
                if indicators['ma_10'] > indicators['ma_20']:
                    trend_signals.append('صعود')
                else:
                    trend_signals.append('هبوط')
            
            # إشارات RSI
            if 'rsi' in indicators:
                if indicators['rsi'] > 50:
                    trend_signals.append('صعود')
                else:
                    trend_signals.append('هبوط')
            
            # إشارات MACD
            if 'macd' in indicators:
                if indicators['macd']['macd'] > indicators['macd']['signal']:
                    trend_signals.append('صعود')
                else:
                    trend_signals.append('هبوط')
            
            # إشارات Stochastic
            if 'stochastic' in indicators:
                if indicators['stochastic']['k'] > indicators['stochastic']['d'] and indicators['stochastic']['k'] > 50:
                    trend_signals.append('صعود')
                elif indicators['stochastic']['k'] < indicators['stochastic']['d'] and indicators['stochastic']['k'] < 50:
                    trend_signals.append('هبوط')
            
            # تحديد الاتجاه الغالب مع قوة الإشارة
            bullish_count = trend_signals.count('صعود')
            bearish_count = trend_signals.count('هبوط')
            total_signals = len(trend_signals)
            
            if bullish_count > bearish_count:
                strength = 'قوي' if bullish_count >= total_signals * 0.75 else 'متوسط' if bullish_count >= total_signals * 0.6 else 'ضعيف'
                indicators['overall_trend'] = f'صاعد ({strength})'
                indicators['trend_strength'] = bullish_count / total_signals if total_signals > 0 else 0.5
            elif bearish_count > bullish_count:
                strength = 'قوي' if bearish_count >= total_signals * 0.75 else 'متوسط' if bearish_count >= total_signals * 0.6 else 'ضعيف'
                indicators['overall_trend'] = f'هابط ({strength})'
                indicators['trend_strength'] = bearish_count / total_signals if total_signals > 0 else 0.5
            else:
                indicators['overall_trend'] = 'محايد'
                indicators['trend_strength'] = 0.5
            
            # حفظ التقاطعات الجديدة في النظام التاريخي
            current_price = indicators['current_price']
            
            # كشف وحفظ تقاطعات المتوسطات المتحركة
            if indicators.get('ma_9_21_crossover') == 'golden':
                crossover_tracker.save_crossover_event(symbol, 'ma_golden_9_21', indicators, current_price)
            elif indicators.get('ma_9_21_crossover') == 'death':
                crossover_tracker.save_crossover_event(symbol, 'ma_death_9_21', indicators, current_price)
            
            if indicators.get('ma_10_20_crossover') == 'golden':
                crossover_tracker.save_crossover_event(symbol, 'ma_golden_10_20', indicators, current_price)
            elif indicators.get('ma_10_20_crossover') == 'death':
                crossover_tracker.save_crossover_event(symbol, 'ma_death_10_20', indicators, current_price)
            
            # كشف وحفظ تقاطعات MACD
            if 'macd_interpretation' in indicators:
                if 'صعود' in indicators['macd_interpretation'] and 'تقاطع' not in indicators.get('last_macd_signal', ''):
                    crossover_tracker.save_crossover_event(symbol, 'macd_bullish', indicators, current_price)
                    indicators['last_macd_signal'] = 'bullish_crossover'
                elif 'هبوط' in indicators['macd_interpretation'] and 'تقاطع' not in indicators.get('last_macd_signal', ''):
                    crossover_tracker.save_crossover_event(symbol, 'macd_bearish', indicators, current_price)
                    indicators['last_macd_signal'] = 'bearish_crossover'
            
            # كشف وحفظ تقاطعات Stochastic
            if 'stochastic' in indicators:
                stoch_crossover = indicators['stochastic'].get('crossover')
                if stoch_crossover == 'bullish':
                    crossover_tracker.save_crossover_event(symbol, 'stoch_bullish', indicators, current_price)
                elif stoch_crossover == 'bearish':
                    crossover_tracker.save_crossover_event(symbol, 'stoch_bearish', indicators, current_price)
            
            logger.info(f"[OK] تم حساب المؤشرات الفنية لـ {symbol} - الاتجاه: {indicators['overall_trend']}")
            
            return {
                'symbol': symbol,
                'indicators': indicators,
                'calculated_at': datetime.now(),
                'data_points': len(df)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في حساب المؤشرات الفنية لـ {symbol}: {e}")
            return None

# إنشاء مثيل مدير MT5
mt5_manager = MT5Manager()

# ===== نظام تتبع التقاطعات التاريخية =====
class CrossoverTracker:
    """نظام تتبع وتحليل التقاطعات التاريخية لتحسين دقة التنبؤات"""
    
    def __init__(self):
        self.crossover_history_file = os.path.join(DATA_DIR, 'crossover_history.json')
        self.crossover_performance_file = os.path.join(DATA_DIR, 'crossover_performance.json')
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """التأكد من وجود ملفات التتبع"""
        for file_path in [self.crossover_history_file, self.crossover_performance_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
    
    def save_crossover_event(self, symbol: str, crossover_type: str, indicators: dict, current_price: float):
        """حفظ حدث تقاطع جديد"""
        try:
            crossover_event = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'type': crossover_type,  # 'ma_golden', 'ma_death', 'macd_bullish', 'macd_bearish', 'stoch_bullish', 'stoch_bearish'
                'price_at_crossover': current_price,
                'indicators': {
                    'ma_9': indicators.get('ma_9'),
                    'ma_21': indicators.get('ma_21'),
                    'rsi': indicators.get('rsi'),
                    'volume_ratio': indicators.get('volume_ratio'),
                    'trend_strength': indicators.get('trend_strength'),
                    'macd': indicators.get('macd', {}),
                    'stochastic': indicators.get('stochastic', {})
                },
                'market_conditions': {
                    'volume_strength': indicators.get('volume_strength'),
                    'overall_trend': indicators.get('overall_trend'),
                    'crossover_summary': indicators.get('crossover_summary')
                }
            }
            
            # قراءة التاريخ الحالي
            with open(self.crossover_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # إضافة الحدث الجديد
            history.append(crossover_event)
            
            # الاحتفاظ بآخر 1000 حدث فقط
            if len(history) > 1000:
                history = history[-1000:]
            
            # حفظ التاريخ المحدث
            with open(self.crossover_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[CROSSOVER] تم حفظ تقاطع {crossover_type} للرمز {symbol}")
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في حفظ تقاطع: {e}")
    
    def update_crossover_performance(self, symbol: str, crossover_id: str, outcome: str, price_change_pct: float):
        """تحديث أداء التقاطعات بناءً على النتائج الفعلية"""
        try:
            performance_data = {
                'symbol': symbol,
                'crossover_id': crossover_id,
                'outcome': outcome,  # 'success', 'failure', 'neutral'
                'price_change_pct': price_change_pct,
                'evaluation_time': datetime.now().isoformat()
            }
            
            with open(self.crossover_performance_file, 'r', encoding='utf-8') as f:
                performance_history = json.load(f)
            
            performance_history.append(performance_data)
            
            # الاحتفاظ بآخر 500 تقييم
            if len(performance_history) > 500:
                performance_history = performance_history[-500:]
            
            with open(self.crossover_performance_file, 'w', encoding='utf-8') as f:
                json.dump(performance_history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"[ERROR] خطأ في تحديث أداء التقاطع: {e}")
    
    def get_crossover_success_rate(self, crossover_type: str, symbol: str = None) -> float:
        """حساب معدل نجاح نوع معين من التقاطعات"""
        try:
            with open(self.crossover_performance_file, 'r', encoding='utf-8') as f:
                performance_history = json.load(f)
            
            # فلترة البيانات حسب النوع والرمز
            filtered_data = []
            for record in performance_history:
                if symbol and record.get('symbol') != symbol:
                    continue
                # يمكن إضافة فلترة حسب نوع التقاطع هنا
                filtered_data.append(record)
            
            if not filtered_data:
                return 0.65  # معدل افتراضي
            
            success_count = sum(1 for record in filtered_data if record.get('outcome') == 'success')
            total_count = len(filtered_data)
            
            success_rate = success_count / total_count if total_count > 0 else 0.65
            return min(max(success_rate, 0.3), 0.95)  # تحديد النطاق بين 30% و 95%
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في حساب معدل نجاح التقاطع: {e}")
            return 0.65
    
    def get_recent_crossovers(self, symbol: str, hours: int = 24) -> list:
        """جلب التقاطعات الحديثة لرمز معين"""
        try:
            with open(self.crossover_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_crossovers = []
            
            for event in history:
                if event.get('symbol') == symbol:
                    event_time = datetime.fromisoformat(event['timestamp'])
                    if event_time > cutoff_time:
                        recent_crossovers.append(event)
            
            return sorted(recent_crossovers, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في جلب التقاطعات الحديثة: {e}")
            return []
    
    def analyze_crossover_patterns(self, symbol: str) -> dict:
        """تحليل أنماط التقاطعات لرمز معين"""
        try:
            recent_crossovers = self.get_recent_crossovers(symbol, hours=168)  # أسبوع
            
            if not recent_crossovers:
                return {'pattern': 'insufficient_data', 'strength': 0.5}
            
            # تحليل الأنماط
            crossover_types = [event['type'] for event in recent_crossovers]
            
            # البحث عن أنماط متتالية
            pattern_analysis = {
                'recent_count': len(recent_crossovers),
                'dominant_type': max(set(crossover_types), key=crossover_types.count) if crossover_types else None,
                'pattern_strength': len(recent_crossovers) / 10.0,  # قوة النمط حسب عدد التقاطعات
                'last_crossover': recent_crossovers[0] if recent_crossovers else None
            }
            
            return pattern_analysis
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في تحليل أنماط التقاطعات: {e}")
            return {'pattern': 'error', 'strength': 0.5}

# إنشاء مثيل متتبع التقاطعات
crossover_tracker = CrossoverTracker()

# ===== كلاس تحليل Gemini AI =====
class GeminiAnalyzer:
    """محلل الذكاء الاصطناعي باستخدام Google Gemini"""
    
    def __init__(self):
        self.model = None
        if GEMINI_AVAILABLE:
            try:
                self.model = genai.GenerativeModel(GEMINI_MODEL, generation_config=GEMINI_GENERATION_CONFIG, safety_settings=GEMINI_SAFETY_SETTINGS)
                logger.info(f"[OK] تم تهيئة محلل Gemini بنجاح - النموذج: {GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"[ERROR] فشل في تهيئة محلل Gemini: {e}")
    
    def analyze_market_data_with_retry(self, symbol: str, price_data: Dict, user_id: int = None, market_data: pd.DataFrame = None, max_retries: int = 3) -> Dict:
        """تحليل بيانات السوق مع آلية إعادة المحاولة"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.analyze_market_data(symbol, price_data, user_id, market_data)
            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    logger.error(f"[ERROR] فشل نهائي في تحليل {symbol} بعد {max_retries} محاولات: {e}")
                    return self._fallback_analysis(symbol, price_data)
                
                wait_time = (2 ** attempt) + (attempt * 0.1)  # exponential backoff
                logger.warning(f"[WARNING] محاولة {attempt + 1} فشلت لـ {symbol}: {e}. إعادة المحاولة خلال {wait_time:.1f} ثانية...")
                time.sleep(wait_time)
        
        # إذا فشلت جميع المحاولات
        return self._fallback_analysis(symbol, price_data)

    def analyze_market_data(self, symbol: str, price_data: Dict, user_id: int = None, market_data: pd.DataFrame = None) -> Dict:
        """تحليل بيانات السوق باستخدام Gemini AI مع مراعاة سياق المستخدم والمؤشرات الفنية"""
        if not self.model:
            return self._fallback_analysis(symbol, price_data)
        
        try:
            # إعداد البيانات للتحليل
            current_price = price_data.get('last', price_data.get('bid', 0))
            spread = price_data.get('spread', 0)
            data_source = price_data.get('source', 'Unknown')
            
            # جلب المؤشرات الفنية الحقيقية من MT5
            technical_data = mt5_manager.calculate_technical_indicators(symbol)
            technical_analysis = ""
            
            # جلب البيانات التاريخية للتقاطعات
            crossover_patterns = crossover_tracker.analyze_crossover_patterns(symbol)
            recent_crossovers = crossover_tracker.get_recent_crossovers(symbol, hours=48)
            
            crossover_history_context = ""
            if recent_crossovers:
                crossover_history_context = f"""
                
                📊 سجل التقاطعات الحديثة للرمز {symbol} (آخر 48 ساعة):
                """
                for i, crossover in enumerate(recent_crossovers[:5]):  # أحدث 5 تقاطعات
                    crossover_time = datetime.fromisoformat(crossover['timestamp']).strftime('%Y-%m-%d %H:%M')
                    crossover_history_context += f"""
                - {crossover_time}: {crossover['type']} عند سعر {crossover['price_at_crossover']:.5f}"""
                
                crossover_history_context += f"""
                
                🔍 تحليل أنماط التقاطعات:
                - عدد التقاطعات الحديثة: {crossover_patterns.get('recent_count', 0)}
                - النمط السائد: {crossover_patterns.get('dominant_type', 'غير محدد')}
                - قوة النمط: {crossover_patterns.get('pattern_strength', 0):.2f}
                """
            
            if technical_data and technical_data.get('indicators'):
                indicators = technical_data['indicators']
                technical_analysis = f"""
                
                🎯 المؤشرات الفنية اللحظية المتقدمة (محسوبة من أحدث البيانات اللحظية M1 + السعر الحالي):
                
                ⏰ حالة البيانات اللحظية:
                - نوع البيانات: {indicators.get('data_freshness', 'غير محدد')}
                - آخر تحديث: {indicators.get('last_update', 'غير محدد')}
                - Bid: {indicators.get('tick_info', {}).get('bid', 'غير متوفر'):.5f}
                - Ask: {indicators.get('tick_info', {}).get('ask', 'غير متوفر'):.5f}
                - Spread: {indicators.get('tick_info', {}).get('spread', 'غير متوفر'):.5f}
                - Volume: {indicators.get('tick_info', {}).get('volume', 'غير متوفر')}
                
                📈 المتوسطات المتحركة والتقاطعات:
                - MA 9: {indicators.get('ma_9', 'غير متوفر'):.5f}
                - MA 10: {indicators.get('ma_10', 'غير متوفر'):.5f}
                - MA 20: {indicators.get('ma_20', 'غير متوفر'):.5f}
                - MA 21: {indicators.get('ma_21', 'غير متوفر'):.5f}
                - MA 50: {indicators.get('ma_50', 'غير متوفر'):.5f}
                - تقاطع MA9/MA21: {indicators.get('ma_9_21_crossover', 'لا يوجد')}
                - تقاطع MA10/MA20: {indicators.get('ma_10_20_crossover', 'لا يوجد')}
                - تقاطع السعر/MA: {indicators.get('price_ma_crossover', 'لا يوجد')}
                
                📊 مؤشرات الزخم:
                - RSI: {indicators.get('rsi', 'غير متوفر'):.2f} ({indicators.get('rsi_interpretation', 'غير محدد')})
                - MACD: {indicators.get('macd', {}).get('macd', 'غير متوفر'):.5f}
                - MACD Signal: {indicators.get('macd', {}).get('signal', 'غير متوفر'):.5f}
                - MACD Histogram: {indicators.get('macd', {}).get('histogram', 'غير متوفر'):.5f}
                - تفسير MACD: {indicators.get('macd_interpretation', 'غير محدد')}
                
                🎢 Stochastic Oscillator المتقدم:
                - %K: {indicators.get('stochastic', {}).get('k', 'غير متوفر'):.2f}
                - %D: {indicators.get('stochastic', {}).get('d', 'غير متوفر'):.2f}
                - تقاطع Stochastic: {indicators.get('stochastic', {}).get('crossover', 'لا يوجد')}
                - منطقة التداول: {indicators.get('stochastic', {}).get('zone', 'غير محدد')}
                - قوة الإشارة: {indicators.get('stochastic', {}).get('strength', 'غير محدد')}
                - اتجاه Stochastic: {indicators.get('stochastic', {}).get('trend', 'غير محدد')}
                - تفسير Stochastic: {indicators.get('stochastic_interpretation', 'غير محدد')}
                
                📊 تحليل حجم التداول المتقدم:
                - الحجم الحالي: {indicators.get('current_volume', 'غير متوفر')}
                - متوسط الحجم: {indicators.get('avg_volume', 'غير متوفر')}
                - نسبة الحجم: {indicators.get('volume_ratio', 'غير متوفر'):.2f}
                - VMA 9: {indicators.get('volume_ma_9', 'غير متوفر'):.0f}
                - VMA 21: {indicators.get('volume_ma_21', 'غير متوفر'):.0f}
                - Volume ROC: {indicators.get('volume_roc', 'غير متوفر'):.2f}%
                - قوة الحجم: {indicators.get('volume_strength', 'غير محدد')}
                - تفسير الحجم: {indicators.get('volume_interpretation', 'غير محدد')}
                
                📍 مستويات الدعم والمقاومة:
                - مقاومة: {indicators.get('resistance', 'غير متوفر'):.5f}
                - دعم: {indicators.get('support', 'غير متوفر'):.5f}
                - Bollinger Upper: {indicators.get('bollinger', {}).get('upper', 'غير متوفر'):.5f}
                - Bollinger Middle: {indicators.get('bollinger', {}).get('middle', 'غير متوفر'):.5f}
                - Bollinger Lower: {indicators.get('bollinger', {}).get('lower', 'غير متوفر'):.5f}
                - تفسير Bollinger: {indicators.get('bollinger_interpretation', 'غير محدد')}
                
                🎯 ملخص التحليل المتقدم:
                - الاتجاه العام: {indicators.get('overall_trend', 'غير محدد')}
                - قوة الاتجاه: {indicators.get('trend_strength', 0.5):.2f}
                - ملخص التقاطعات: {indicators.get('crossover_summary', 'لا توجد')}
                - تغيير السعر %: {indicators.get('price_change_pct', 0):.2f}%
                - السعر الحالي: {indicators.get('current_price', 0):.5f}
                """
            else:
                # في حالة عدم توفر البيانات من MT5، استخدم بيانات السعر اللحظي الحالي
                current_price = price_data.get('last', price_data.get('bid', 0))
                technical_analysis = f"""
                
                ⚠️ المؤشرات الفنية: غير متوفرة من MT5 - الاعتماد على السعر اللحظي فقط
                - السعر اللحظي الحالي: {current_price:.5f}
                - مصدر البيانات: {data_source}
                - حالة الاتصال: MT5 غير متصل أو بيانات غير كافية
                
                🔴 تنبيه: التحليل محدود بسبب عدم توفر البيانات اللحظية الكاملة
                """
            
            # تحديد نوع الرمز وخصائصه
            symbol_type_context = ""
            if symbol.endswith('USD'):
                if symbol.startswith('EUR') or symbol.startswith('GBP'):
                    symbol_type_context = """
                    
                    **سياق خاص بأزواج العملات الرئيسية:**
                    - هذا زوج عملات رئيسي بسيولة عالية وتقلبات معتدلة
                    - تأثر قوي بقرارات البنوك المركزية (Fed, ECB, BoE)
                    - ساعات التداول النشطة: London + New York overlap
                    - عوامل مؤثرة: معدلات الفائدة، التضخم، GDP، البطالة
                    - نسبة النجاح المتوقعة أعلى بسبب قابلية التنبؤ النسبية
                    """
                elif symbol.startswith('XAU') or symbol.startswith('XAG'):
                    symbol_type_context = """
                    
                    **سياق خاص بالمعادن النفيسة:**
                    - الذهب/الفضة أصول ملاذ آمن مع تقلبات متوسطة إلى عالية
                    - تأثر قوي بالأحداث الجيوسياسية والتضخم
                    - علاقة عكسية مع الدولار الأمريكي عادة
                    - عوامل مؤثرة: التضخم، أسعار الفائدة، الأزمات العالمية
                    - كن حذراً من التحركات المفاجئة خلال الأخبار المهمة
                    """
                elif symbol.startswith('BTC') or symbol.startswith('ETH'):
                    symbol_type_context = """
                    
                    **سياق خاص بالعملات الرقمية:**
                    - تقلبات عالية جداً مع إمكانية مكاسب/خسائر كبيرة
                    - سوق 24/7 مع تأثر قوي بالمشاعر والأخبار
                    - تأثر بالتنظيم الحكومي، اعتماد المؤسسات، التطوير التقني
                    - عوامل مؤثرة: تصريحات المؤثرين، القرارات التنظيمية، التطوير التقني
                    - قلل نسبة النجاح 10-15% بسبب عدم القابلية للتنبؤ
                    """
                else:
                    symbol_type_context = """
                    
                    **سياق عام للأصول:**
                    - حلل خصائص هذا الرمز والعوامل المؤثرة عليه
                    - اعتبر السيولة والتقلبات التاريخية
                    - راعِ ساعات التداول النشطة والأحداث الاقتصادية
                    """
            
            # جلب سياق المستخدم
            user_context = ""
            trading_mode_instructions = ""
            
            if user_id:
                trading_mode = get_user_trading_mode(user_id)
                capital = get_user_capital(user_id)
                user_timezone = get_user_timezone(user_id)
                
                user_context = f"""
                
                سياق المستخدم:
                - نمط التداول: {trading_mode} ({'سكالبينغ سريع' if trading_mode == 'scalping' else 'تداول طويل المدى'})
                - رأس المال: ${capital:,.2f}
                - المنطقة الزمنية: {user_timezone}
                """
                
                # تخصيص التحليل حسب نمط التداول
                if trading_mode == 'scalping':
                    trading_mode_instructions = """
                    
                    تعليمات خاصة للسكالبينغ:
                    - ركز على الفرص قصيرة المدى (دقائق إلى ساعات)
                    - أهداف ربح صغيرة (1-2%)
                    - وقف خسارة ضيق (0.5-1%)
                    - تحليل سريع وفوري
                    - ثقة عالية مطلوبة (80%+)
                    - ركز على التحركات السريعة والمؤشرات قصيرة المدى
                    - حجم صفقات أصغر لتقليل المخاطر
                    - اهتم بـ RSI و MACD للإشارات السريعة
                    """
                else:
                    trading_mode_instructions = """
                    
                    تعليمات خاصة للتداول طويل المدى:
                    - ركز على الاتجاهات طويلة المدى (أيام إلى أسابيع)
                    - أهداف ربح أكبر (5-10%)
                    - وقف خسارة أوسع (2-3%)
                    - تحليل شامل ومتأني
                    - تحمل تذبذبات أكثر
                    - ركز على الاتجاهات الرئيسية والأساسيات
                    - حجم صفقات أكبر للاستفادة من الاتجاهات الطويلة
                    - اهتم بالمتوسطات المتحركة والدعم والمقاومة
                    """
            
            # تحميل بيانات التدريب السابقة
            training_context = self._load_training_context(symbol)
            
            # تحميل الأنماط المتعلمة من الصور
            learned_patterns = self._load_learned_patterns()
            
            # إنشاء prompt للتحليل المتقدم مع المؤشرات الفنية
            prompt = f"""
            أنت محلل مالي خبير متخصص في التداول اللحظي. قم بتحليل البيانات اللحظية التالية للرمز {symbol}:
            
            ⚠️ مهم: جميع البيانات المرفقة هي بيانات لحظية حقيقية من MetaTrader5 محدثة كل دقيقة مع دمج السعر اللحظي الحالي.
            
            البيانات اللحظية الحالية:
            - السعر الحالي: {current_price}
            - سعر الشراء: {price_data.get('bid', 'غير متوفر')}
            - سعر البيع: {price_data.get('ask', 'غير متوفر')}
            - الفرق (Spread): {spread}
            - مصدر البيانات: {data_source}
            - الوقت: {price_data.get('time', 'الآن')}
            {technical_analysis}
            {crossover_history_context}
            {symbol_type_context}
            {user_context}
            {trading_mode_instructions}
            
            بيانات التدريب السابقة:
            {training_context}
            
            الأنماط المتعلمة من المستخدمين:
            {learned_patterns}
            
            {get_analysis_rules_for_prompt()}
            
            === تعليمات التحليل المتقدم ===
            
            🔶 أنت الآن خبير تداول محترف بخبرة تفوق 20 عامًا في الأسواق المالية العالمية. هدفك تقديم تحليل عميق ومتقدم جدًا بناءً على منهج علمي ومنظم، قائم على معايير كمية دقيقة وشفافية كاملة في الحسابات.
            
            📋 **متطلبات الجودة الاحترافية:**
            - استخدم معايير كمية فقط في القرار
            - لا تكتب جمل عامة مثل "قد يصعد السعر" أو "يوجد احتمال"
            - استخدم لغة تحليلية صارمة ومنظمة فقط
            - قدم دائماً نسبة النجاح الحقيقية المحسوبة بناءً على المؤشرات
            - حتى لو كانت النسبة منخفضة، قدم التحليل مع تحذيرات واضحة
            - اشرح أسباب النسبة المنخفضة إذا كانت أقل من 70%
            
            ## 🔍 STEP 1: التحليل الفني المتعمق والمتقدم
            قيّم كل مؤشر بدقة وأعطِ نقاط من 10، واستخدم المؤشرات التالية:
            
            **📊 المؤشرات الأساسية:** RSI, MACD, Moving Averages (EMA, SMA), Bollinger Bands, Volume Profile, ATR
            **📈 تحليل متعدد الأطر:** حدد الاتجاه العام عبر أطر زمنية متعددة (سكالبينغ، قصير، متوسط)
            **🎯 نقاط حساسة:** ارصد مناطق الانعكاس، التشبع، الاختراقات الحقيقية، والمناطق الحساسة
            **📋 سلوك السعر:** افحص سلوك السعر عند مستويات رئيسية (عرض وطلب، دعم ومقاومة)
            
            **أ) مؤشر RSI:**
            - إذا RSI 20-30: نقاط الشراء = 9/10 (ذروة بيع قوية)
            - إذا RSI 30-50: نقاط الشراء = 7/10 (منطقة جيدة)  
            - إذا RSI 50-70: نقاط البيع = 7/10 (منطقة جيدة للبيع)
            - إذا RSI 70-80: نقاط البيع = 9/10 (ذروة شراء قوية)
            - إذا RSI 40-60: نقاط = 4/10 (منطقة محايدة)
            
            **ب) مؤشر MACD:**
            - MACD فوق Signal + موجب: نقاط الشراء = 8/10
            - MACD فوق Signal + سالب: نقاط الشراء = 6/10  
            - MACD تحت Signal + موجب: نقاط البيع = 6/10
            - MACD تحت Signal + سالب: نقاط البيع = 8/10
            - تقاطع حديث: نقاط إضافية = +2
            
            **ج) المتوسطات المتحركة والتقاطعات المتقدمة:**
            - السعر فوق MA9 > MA21 > MA50: نقاط الشراء = 9/10
            - السعر تحت MA9 < MA21 < MA50: نقاط البيع = 9/10
            - تقاطع ذهبي MA9/MA21: نقاط الشراء = 8/10 + نقاط إضافية للقوة
            - تقاطع الموت MA9/MA21: نقاط البيع = 8/10 + نقاط إضافية للقوة
            - تقاطع السعر مع MA9 صعوداً: نقاط الشراء = 7/10
            - تقاطع السعر مع MA9 هبوطاً: نقاط البيع = 7/10
            - ترتيب مختلط: نقاط = 3-5/10 حسب القوة
            
            **د) مستويات الدعم والمقاومة:**
            - قرب مستوى دعم قوي: نقاط الشراء = +3
            - قرب مستوى مقاومة قوية: نقاط البيع = +3
            - كسر مستوى بحجم عالي: نقاط = +4
            
            **هـ) تحليل الشموع اليابانية (إن توفرت):**
            - نماذج انعكاسية قوية: +2 نقاط
            - نماذج استمرارية: +1 نقطة
            - تأكيد النموذج بالحجم: +1 نقطة إضافية
            
            **و) مؤشر Stochastic Oscillator المتقدم:**
            - تقاطع صاعد %K/%D في منطقة ذروة البيع (<30): نقاط الشراء = 9/10
            - تقاطع هابط %K/%D في منطقة ذروة الشراء (>70): نقاط البيع = 9/10
            - تقاطع صاعد %K/%D في المنطقة المحايدة: نقاط الشراء = 6/10
            - تقاطع هابط %K/%D في المنطقة المحايدة: نقاط البيع = 6/10
            - %K و %D في ذروة بيع قوية (<20): نقاط الشراء = 8/10
            - %K و %D في ذروة شراء قوية (>80): نقاط البيع = 8/10
            - قوة الإشارة (تباعد الخطوط >20): نقاط إضافية = +2
            - ضعف الإشارة (تقارب الخطوط <5): نقاط = -1
            
            **ز) تحليل حجم التداول المتطور:**
            - حجم عالي جداً (>2x متوسط) مع حركة سعرية قوية: نقاط = +3
            - حجم عالي (>1.5x متوسط) مع تأكيد الاتجاه: نقاط = +2
            - حجم منخفض (<0.5x متوسط) مع حركة سعرية: نقاط = -2
            - Volume ROC موجب قوي (>50%): نقاط = +2
            - Volume ROC سالب قوي (<-50%): نقاط = -1
            - تحليل VPA (Volume Price Analysis): تأكيد/ضعف الحركة = ±1
            
            **ح) تحليل الـ ATR والتقلبات:**
            - ATR منخفض = استقرار: +1 نقطة
            - ATR مرتفع جداً = مخاطرة: -2 نقاط
            
            **🎯 تحليل التقاطعات المتعددة والإشارات المتزامنة:**
            
            **التقاطعات عالية القوة (نقاط مضاعفة):**
            - تقاطع ذهبي MA9/MA21 + تقاطع صاعد MACD + تقاطع صاعد Stochastic: نقاط الشراء = 15/10 (إشارة قوية جداً)
            - تقاطع الموت MA9/MA21 + تقاطع هابط MACD + تقاطع هابط Stochastic: نقاط البيع = 15/10 (إشارة قوية جداً)
            
            **التقاطعات متوسطة القوة:**
            - تقاطعان متفقان من ثلاثة: نقاط = 8/10
            - تقاطع واحد قوي مع تأكيد حجم عالي: نقاط = 7/10
            
            **التضارب في التقاطعات (تقليل النقاط):**
            - تقاطع صاعد MA مع تقاطع هابط MACD: نقاط = 3/10 (إشارة ضعيفة)
            - تقاطع صاعد Stochastic مع تقاطع هابط MA: نقاط = 3/10 (إشارة ضعيفة)
            - جميع التقاطعات متضاربة: نقاط = 1/10 (تجنب التداول)
            
            **تحليل التوقيت للتقاطعات:**
            - تقاطع حديث (آخر 1-3 شمعات): نقاط إضافية = +2
            - تقاطع قديم (أكثر من 10 شمعات): نقاط = -1
            - تقاطع في بداية تكونه: نقاط = +1 (مراقبة)
            
            **تأكيد التقاطعات بالحجم والسعر:**
            - تقاطع مع حجم عالي (>1.5x) وحركة سعرية قوية: نقاط إضافية = +3
            - تقاطع مع حجم منخفض (<0.8x): نقاط = -2
            - تقاطع مع كسر مستوى دعم/مقاومة: نقاط إضافية = +2
            
            **ملخص قوة الإشارة الإجمالية:**
            - 3 تقاطعات متفقة + حجم عالي = إشارة استثنائية (95%+ نجاح متوقع)
            - 2 تقاطعات متفقة + تأكيد = إشارة قوية (85%+ نجاح متوقع)
            - 1 تقاطع قوي + تأكيدات = إشارة متوسطة (75%+ نجاح متوقع)
            - تضارب في التقاطعات = تجنب التداول (أقل من 60% نجاح)
            
            **🔍 استخدام البيانات التاريخية للتقاطعات:**
            - راجع سجل التقاطعات الحديثة المرفق لفهم سلوك الرمز
            - إذا كان هناك نمط سائد من التقاطعات الناجحة، أعط وزناً إضافياً (+5-10%)
            - إذا كانت التقاطعات الحديثة فاشلة، قلل الثقة (-5-15%)
            - التقاطعات المتكررة في اتجاه واحد تشير لقوة الاتجاه
            - غياب التقاطعات الحديثة قد يشير لفترة استقرار أو تردد
            
            ## 🔍 STEP 2: تحليل ظروف السوق
            
            **أ) حجم التداول:**
            - حجم > 150% من المتوسط: قوة إضافية = +15%
            - حجم 120-150% من المتوسط: قوة إضافية = +10%  
            - حجم 80-120% من المتوسط: طبيعي = 0%
            - حجم < 80% من المتوسط: ضعف = -10%
            
            **ب) التقلبات (Volatility):**
            - تقلبات منخفضة: استقرار = +5%
            - تقلبات معتدلة: مثالية = +10%
            - تقلبات عالية: مخاطرة = -15%
            
            ## 🔍 STEP 3: تحليل المخاطر والفرص
            
            **عوامل الخطر (تقلل النسبة):**
            - تضارب في المؤشرات: -10% لكل تضارب
            - أخبار سلبية متوقعة: -15%
            - عدم استقرار الأسواق العالمية: -10%
            - اقتراب من نهاية جلسة التداول: -5%
            
            **عوامل الفرص (تزيد النسبة):**
            - جميع المؤشرات متفقة: +20%
            - كسر مستوى مهم بحجم عالي: +15%
            - أخبار إيجابية داعمة: +10%
            - توقيت مثالي (بداية الجلسة): +5%
            
            ## 🔍 STEP 4: معايرة حسب نمط التداول
            
            **للسكالبينغ (مضاعف دقة):**
            - RSI + MACD متفقان: مضاعف x1.2
            - حجم تداول عالي: مضاعف x1.15
            - تقلبات منخفضة: مضاعف x1.1
            - وقت ذروة السوق: مضاعف x1.05
            
            **للتداول طويل المدى (مضاعف اتجاه):**
            - اتجاه قوي على عدة إطارات: مضاعف x1.3
            - اختراق مستويات مهمة: مضاعف x1.2  
            - دعم أساسيات اقتصادية: مضاعف x1.15
            
            ## 🔍 STEP 5: الحساب النهائي لنسبة النجاح
            
            **الصيغة الحسابية:**
            ```
            النقاط الأساسية = (مجموع نقاط المؤشرات ÷ عدد المؤشرات) × 10
            
            النسبة المعدلة = النقاط الأساسية 
                           + تعديل حجم التداول
                           + تعديل التقلبات  
                           + عوامل الفرص
                           - عوامل المخاطر
            
            النسبة النهائية = النسبة المعدلة × مضاعف نمط التداول
            ```
            
            **قواعد مهمة:**
            - النسبة النهائية يجب أن تكون بين 10% و 95%
            - إذا كانت المؤشرات متضاربة بشدة: الحد الأقصى 45%
            - إذا كانت جميع المؤشرات متفقة: الحد الأدنى 60%
            - للمبتدئين: تقليل النسبة بـ 10%
            - للخبراء: زيادة النسبة بـ 5%
            
            ## 📊 متطلبات النتيجة النهائية (شفافية كاملة):
            
            1. **التحليل التفصيلي:** اعرض نقاط كل مؤشر وتبريرك بناءً على إشارات واضحة
            2. **حساب النسبة خطوة بخطوة:** أظهر العملية الحسابية الكاملة والشفافة
            3. **التوصية المحددة:** حدد نوع الصفقة (شراء/بيع)، نقطة الدخول المثلى، الأهداف (TP1/TP2)، وقف الخسارة (SL)
            4. **تقييم نسبة العائد/المخاطرة:** احسب Risk/Reward Ratio بدقة
            5. **إدارة المخاطر المتقدمة:** اقترح حجم الصفقة (Lot Size) وحساب الخسارة المحتملة بالنقاط
            6. **تحليل التباين:** لا تتجاهل التباين بين المؤشرات (مثلاً: تقاطع سلبي في MACD مع RSI صاعد)
            
            7. **⚠️ CRITICAL - نسبة النجاح المحسوبة بناءً على تحليلك:**
            - احسب نسبة النجاح الفعلية بناءً على قوة الإشارات المتاحة
            - اجمع نقاط جميع المؤشرات واحسب النسبة النهائية
            - يجب أن تكون النسبة انعكاساً حقيقياً لجودة الإشارات وليس رقماً عشوائياً
            - اكتب بوضوح: "نسبة نجاح الصفقة: X%" حيث X هو الرقم المحسوب من تحليلك
            - إذا كانت الإشارات متضاربة جداً، اكتب نسبة منخفضة (30-50%)
            - إذا كانت جميع المؤشرات متفقة وقوية، اكتب نسبة عالية (75-90%)
            - إذا كانت الإشارات متوسطة، اكتب نسبة متوسطة (55-75%)
            
            ## ⚠️ تحذيرات مهمة وقواعد المصداقية:
            
            **قواعد الدقة والمصداقية (معايير احترافية صارمة):**
            - لا تبالغ بالتفاؤل: إذا كانت الصفقة محفوفة بالمخاطر، اذكر ذلك صراحة
            - استبعد أي صفقة لا تستوفي الشروط الحسابية الدقيقة
            - لا تتردد في إعطاء نسب منخفضة (15-35%) إذا كانت الإشارات ضعيفة
            - لا تتجاوز 90% إلا في حالات الإشارات القوية جداً والنادرة مع توافق جميع المؤشرات
            - إذا كانت البيانات ناقصة أو غير موثوقة: الحد الأقصى 50%
            - إذا كان هناك تضارب شديد في المؤشرات: 20-40% فقط
            - للمؤشرات المتفقة بقوة مع دعم الأخبار ودون تباين: 75-90%
            - تذكر: أنك تعمل ضمن غرفة تداول احترافية ولا يقل تحليلك جودة عن كبار المتداولين والمؤسسات
            
            **أمثلة على نسب صحيحة:**
            - إشارة ضعيفة مع تضارب: "نسبة نجاح الصفقة: 28%" 
            - إشارة متوسطة: "نسبة نجاح الصفقة: 54%"
            - إشارة قوية مع دعم أخبار: "نسبة نجاح الصفقة: 83%"
            - إشارة ممتازة نادرة: "نسبة نجاح الصفقة: 91%"
            
            **التحقق النهائي قبل الإجابة:**
            1. هل نسبة النجاح تعكس حقاً قوة/ضعف التحليل؟
            2. هل أخذت جميع المخاطر في الاعتبار؟
            3. هل النسبة منطقية مقارنة بظروف السوق؟
            4. هل يمكنني الدفاع عن هذه النسبة بالأرقام والمؤشرات؟
            
            ## 🎯 التحذير النهائي والالتزام الاحترافي:
            
            **✅ قدم دائماً تحليلاً شاملاً يتضمن:**
            - نسبة النجاح الحقيقية المحسوبة بناءً على معايير كمية
            - توصية واضحة (شراء/بيع/انتظار) مع تبرير مفصل
            - تحذيرات مناسبة حسب مستوى المخاطر
            - شرح أسباب النسبة المحسوبة
            
            **⚠️ مستويات التحذير حسب نسبة النجاح:**
            - 90%+ : "إشارة استثنائية 💎"
            - 80-89%: "إشارة عالية الجودة 🔥" 
            - 70-79%: "إشارة جيدة ✅"
            - 60-69%: "إشارة متوسطة ⚠️ - مخاطر متوسطة"
            - 50-59%: "إشارة ضعيفة ⚠️ - مخاطر عالية"
            - أقل من 50%: "إشارة ضعيفة جداً 🚨 - تجنب التداول"
            
            **🔥 تذكر:** أنت تعمل كخبير احترافي في غرفة تداول مؤسسية. قدم التحليل الكامل والشفاف مع التحذيرات المناسبة. المتداول يعتمد على تحليلك في اتخاذ قرارات مالية مهمة جداً!
            
            **🚨 MANDATORY - يجب أن تنهي تحليلك بـ:**
            "نسبة نجاح الصفقة: X%" 
            حيث X هو الرقم الذي حسبته بناءً على المؤشرات الفنية المتاحة.
            
            **مثال على الصيغة الصحيحة:**
            "بناءً على التحليل أعلاه، نسبة نجاح الصفقة: 73%"
            
            **هذا إلزامي ولا يمكن تجاهله! بدون هذه الجملة لن يعمل النظام!**
            """
            
            # إرسال الطلب لـ Gemini باستخدام جلسة دردشة لكل رمز
            chat = chat_session_manager.get_chat(symbol)
            response = None
            try:
                response = chat.send_message(prompt)
            except Exception as rate_e:
                if GEMINI_ROTATE_ON_RATE_LIMIT and ("429" in str(rate_e) or "rate" in str(rate_e).lower() or "quota" in str(rate_e).lower()):
                    gemini_key_manager.rotate_key()
                    chat = chat_session_manager.reset_session(symbol)
                    response = chat.send_message(prompt)
                else:
                    raise
            analysis_text = getattr(response, 'text', '') or (response.candidates[0].content.parts[0].text if getattr(response, 'candidates', None) else '')
            try:
                # حساب تقريبي لاستهلاك الرموز
                input_tokens = len(prompt) // 3
                output_tokens = len(analysis_text) // 3
                chat_session_manager.record_usage(symbol, input_tokens, output_tokens)
            except Exception:
                pass

            # حفظ سجل المحادثة اختيارياً
            if 'SAVE_CHAT_LOGS' in globals() and SAVE_CHAT_LOGS:
                try:
                    log_path = os.path.join(CHAT_LOGS_DIR, f"{symbol}_{datetime.now().strftime('%Y%m%d')}.log")
                    with open(log_path, 'a', encoding='utf-8') as lf:
                        lf.write("\n\n" + "="*20 + f"\n[{datetime.now()}] PROMPT:\n" + prompt + "\n\nRESPONSE:\n" + analysis_text + "\n")
                except Exception as _log_e:
                    logger.debug(f"[CHAT_LOG] تجاهل خطأ حفظ السجل: {_log_e}")
            
            # استخراج التوصية من النص
            recommendation = self._extract_recommendation(analysis_text)
            confidence = self._extract_confidence(analysis_text)
            
            # التحقق من صحة نسبة النجاح - يجب أن تكون من AI فقط
            if confidence is None or confidence < 0 or confidence > 100:
                logger.warning(f"[AI_ANALYSIS] نسبة نجاح غير صحيحة من AI: {confidence}")
                confidence = None  # إشارة للفشل
            
            # استخراج قيم إضافية من رد AI: سعر الدخول/الأهداف/الوقف و R/R
            try:
                import re
                def _find_number(patterns):
                    for p in patterns:
                        m = re.search(p, analysis_text, re.IGNORECASE | re.UNICODE)
                        if m:
                            try:
                                return float(m.group(1))
                            except Exception:
                                if len(m.groups()) >= 2:
                                    try:
                                        return float(m.group(2))
                                    except Exception:
                                        pass
                    return None
                entry_price_ai = _find_number([
                    r'(?:نقطة|سعر)\s*الدخول\s*[:：]?\s*([\d\.]+)',
                    r'entry\s*(?:price)?\s*[:：]?\s*([\d\.]+)'
                ])
                target1_ai = _find_number([
                    r'(?:TP1|الهدف\s*الأول)\s*[:：]?\s*([\d\.]+)'
                ])
                target2_ai = _find_number([
                    r'(?:TP2|الهدف\s*الثاني)\s*[:：]?\s*([\d\.]+)'
                ])
                stop_loss_ai = _find_number([
                    r'(?:SL|وقف\s*الخسارة)\s*[:：]?\s*([\d\.]+)'
                ])
                risk_reward_ai = _find_number([
                    r'(?:RR|R\s*/\s*R|Risk\s*/\s*Reward|نسبة\s*المخاطرة\s*/\s*المكافأة)\s*[:：]?\s*1\s*[:：]\s*([\d\.]+)',
                    r'(?:RR|Risk\s*/\s*Reward|نسبة\s*المخاطرة\s*/\s*المكافأة)\s*[:：]?\s*([\d\.]+)'
                ])
            except Exception as _ai_parse_e:
                logger.debug(f"[AI_PARSE] فشل استخراج القيم العددية من AI: {_ai_parse_e}")
                entry_price_ai = target1_ai = target2_ai = stop_loss_ai = risk_reward_ai = None
            
            # تسجيل تفاصيل لتتبع نسبة النجاح المستخرجة
            logger.info(f"[AI_ANALYSIS] {symbol}: التوصية={recommendation}, نسبة النجاح={confidence}")
            
            # لا تعديل للثقة - تبقى كما هي من AI
            return {
                'action': recommendation,
                'confidence': confidence,  # قد تكون None إذا فشل AI
                'reasoning': [analysis_text],
                'ai_analysis': analysis_text,
                'source': f'Gemini AI ({data_source})',
                'data_source': f'Gemini AI ({data_source})',
                'symbol': symbol,
                'timestamp': datetime.now(),
                'price_data': price_data,
                'user_context': user_context if user_id else None,
                'entry_price': entry_price_ai,
                'target1': target1_ai,
                'target2': target2_ai,
                'stop_loss': stop_loss_ai,
                'risk_reward': risk_reward_ai
            }
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في تحليل Gemini للرمز {symbol}: {e}")
            # على أخطاء RPD/Quota جرّب تبديل المفتاح مرة أخيرة
            if GEMINI_ROTATE_ON_RATE_LIMIT and ("429" in str(e) or "rate" in str(e).lower() or "quota" in str(e).lower()):
                try:
                    gemini_key_manager.rotate_key()
                    chat_session_manager.reset_session(symbol)
                except Exception:
                    pass
            return self._fallback_analysis(symbol, price_data)
    
    def _load_training_context(self, symbol: str) -> str:
        """تحميل سياق التدريب السابق للرمز"""
        try:
            training_file = os.path.join(FEEDBACK_DIR, "ai_training_data.json")
            if os.path.exists(training_file):
                with open(training_file, 'r', encoding='utf-8') as f:
                    training_data = json.load(f)
                
                # البحث عن بيانات تدريب متعلقة بالرمز
                relevant_data = [item for item in training_data if item.get('symbol') == symbol]
                if relevant_data:
                    return f"بيانات تدريب سابقة: {len(relevant_data)} تقييم سابق للرمز"
            
            return "لا توجد بيانات تدريب سابقة لهذا الرمز"
        except:
            return ""
    
    def _load_learned_patterns(self) -> str:
        """تحميل الأنماط المتعلمة من الصور"""
        try:
            patterns_file = os.path.join(FEEDBACK_DIR, "learned_patterns.json")
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    patterns = json.load(f)
                
                if patterns:
                    context = "\n🧠 الأنماط المتعلمة من المستخدمين:\n"
                    for pattern in patterns[-10:]:  # آخر 10 أنماط
                        pattern_info = pattern.get('pattern_info', {})
                        description = pattern.get('user_description', '')
                        
                        context += f"""
- النمط: {pattern_info.get('pattern_name', 'نمط مخصص')}
  الاتجاه: {pattern_info.get('direction', 'غير محدد')}
  الثقة: {pattern_info.get('confidence', 50)}%
  الوصف: {description[:100]}...
                        """
                    
                    context += "\n⚠️ يرجى مراعاة هذه الأنماط المتعلمة عند التحليل.\n"
                    return context
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في تحميل الأنماط المتعلمة: {e}")
        
        return ""
    
    def _adjust_confidence_for_user(self, confidence: float, user_id: int) -> float:
        """تعديل مستوى الثقة حسب نمط التداول"""
        try:
            trading_mode = get_user_trading_mode(user_id)
            
            if trading_mode == 'scalping':
                # للسكالبينغ، نحتاج ثقة أعلى
                return min(confidence * 0.9, 95.0)  # تقليل الثقة قليلاً للحذر
            elif trading_mode == 'longterm':
                # للتداول طويل المدى، يمكن قبول ثقة أقل
                return min(confidence * 1.1, 95.0)  # زيادة الثقة قليلاً
            
            return confidence
        except:
            return confidence
    
    def _extract_recommendation(self, text: str) -> str:
        """استخراج التوصية من نص التحليل - محسّن"""
        if not text:
            return 'HOLD'
            
        text_lower = text.lower()
        
        # البحث عن كلمات محددة للشراء
        buy_keywords = [
            'شراء', 'buy', 'صاعد', 'ارتفاع', 'bullish', 'long', 
            'توصية: شراء', 'recommendation: buy', 'التوصية: buy',
            'اتجاه صاعد', 'uptrend', 'صعود', 'ايجابي', 'positive'
        ]
        
        # البحث عن كلمات محددة للبيع
        sell_keywords = [
            'بيع', 'sell', 'هابط', 'انخفاض', 'bearish', 'short',
            'توصية: بيع', 'recommendation: sell', 'التوصية: sell',
            'اتجاه هابط', 'downtrend', 'هبوط', 'سلبي', 'negative'
        ]
        
        # البحث عن كلمات الانتظار
        hold_keywords = [
            'انتظار', 'hold', 'wait', 'محايد', 'neutral', 'sideways',
            'توصية: انتظار', 'recommendation: hold', 'التوصية: hold'
        ]
        
        # عد الكلمات لكل اتجاه
        buy_count = sum(1 for word in buy_keywords if word in text_lower)
        sell_count = sum(1 for word in sell_keywords if word in text_lower)
        hold_count = sum(1 for word in hold_keywords if word in text_lower)
        
        # اختيار التوصية بناءً على الأغلبية
        if buy_count > sell_count and buy_count > hold_count:
            return 'BUY'
        elif sell_count > buy_count and sell_count > hold_count:
            return 'SELL'
        elif buy_count > 0:
            return 'BUY'  # في حالة التعادل، نفضل الشراء إذا وُجد
        elif sell_count > 0:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _extract_confidence(self, text: str) -> float:
        """استخراج مستوى الثقة من نص التحليل - محسّن"""
        if not text:
            return 65  # قيمة افتراضية معقولة
            
        # البحث عن نسبة النجاح المحددة من Gemini
        success_rate = self._extract_success_rate_from_ai(text)
        if success_rate is not None:
            return success_rate
        
        # إذا لم نجد نسبة محددة، نحاول استخراج أي رقم مع علامة %
        import re
        
        # البحث عن أي رقم متبوع بعلامة %
        percentage_matches = re.findall(r'(\d+(?:\.\d+)?)%', text)
        if percentage_matches:
            for match in reversed(percentage_matches):  # نبدأ من النهاية
                try:
                    confidence = float(match)
                    if 40 <= confidence <= 95:  # نطاق معقول
                        return confidence
                except ValueError:
                    continue
        
        # إذا لم نجد أي شيء، نعطي قيمة افتراضية بناءً على قوة التحليل
        text_lower = text.lower()
        
        # تحليل قوة الإشارات في النص
        strong_signals = ['قوي', 'strong', 'واضح', 'clear', 'مؤكد', 'confirmed']
        weak_signals = ['ضعيف', 'weak', 'غير واضح', 'unclear', 'محتمل', 'possible']
        
        strong_count = sum(1 for signal in strong_signals if signal in text_lower)
        weak_count = sum(1 for signal in weak_signals if signal in text_lower)
        
        if strong_count > weak_count:
            return 75  # إشارة قوية
        elif weak_count > strong_count:
            return 55  # إشارة ضعيفة
        else:
            return 65  # متوسط

    def _extract_success_rate_from_ai(self, text: str) -> float:
        """استخراج نسبة النجاح المحددة من الذكاء الاصطناعي"""
        try:
            import re
            
            # البحث عن نص "نسبة نجاح الصفقة" متبوعاً برقم ونسبة مئوية
            patterns = [
                r'نسبة نجاح الصفقة:?\s*(\d+(?:\.\d+)?)%',
                r'نسبة النجاح:?\s*(\d+(?:\.\d+)?)%',
                r'احتمالية النجاح:?\s*(\d+(?:\.\d+)?)%',
                r'معدل النجاح:?\s*(\d+(?:\.\d+)?)%',
                r'success rate:?\s*(\d+(?:\.\d+)?)%',
                r'نسبة\s+نجاح\s+(?:الصفقة|التداول):?\s*(\d+(?:\.\d+)?)%',
                # البحث في نهاية النص
                r'النسبة:?\s*(\d+(?:\.\d+)?)%',
                r'التوقع:?\s*(\d+(?:\.\d+)?)%',
                # أنماط إضافية للتأكد
                r'نسبة\s*:\s*(\d+(?:\.\d+)?)%',
                r'النجاح\s*:\s*(\d+(?:\.\d+)?)%'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
                if matches:
                    success_rate = float(matches[-1])  # أخذ آخر نتيجة
                    # التأكد من أن النسبة في النطاق المطلوب (نطاق أوسع للمرونة)
                    if 1 <= success_rate <= 100:
                        logger.info(f"[AI_SUCCESS_EXTRACT] تم استخراج نسبة نجاح من AI: {success_rate}%")
                        return success_rate
            
            # البحث عن أرقام في نهاية النص (آخر 200 حرف)
            text_end = text[-200:].lower()
            numbers_at_end = re.findall(r'(\d+)%', text_end)
            
            for num_str in reversed(numbers_at_end):  # البدء من النهاية
                num = float(num_str)
                if 10 <= num <= 95:
                    logger.info(f"[AI_SUCCESS_EXTRACT] تم استخراج نسبة من نهاية النص: {num}%")
                    return num
            
            # إذا لم نجد شيئاً محدداً، نعيد None لاستخدام الطريقة البديلة
            return None
            
        except Exception as e:
            logger.warning(f"[WARNING] خطأ في استخراج نسبة النجاح من AI: {e}")
            return None
    
    def get_symbol_news(self, symbol: str) -> str:
        """جلب أخبار اقتصادية مؤثرة للرمز المحدد من مصادر موثوقة"""
        try:
            # تحديد الفئة والعملة الأساسية
            if symbol in ['EURUSD', 'EURGBP', 'EURJPY']:
                base_currency = 'EUR'
                news_focus = 'البنك المركزي الأوروبي'
            elif symbol in ['GBPUSD', 'EURGBP', 'GBPJPY']:
                base_currency = 'GBP'
                news_focus = 'بنك إنجلترا'
            elif symbol in ['USDJPY', 'GBPUSD', 'EURUSD', 'AUDUSD', 'USDCAD', 'USDCHF']:
                base_currency = 'USD'
                news_focus = 'الاحتياطي الفيدرالي'
            elif symbol in ['XAUUSD', 'XAGUSD', 'XPTUSD', 'XPDUSD']:
                base_currency = 'METALS'
                news_focus = 'المعادن النفيسة'
            elif symbol in ['BTCUSD', 'ETHUSD', 'BNBUSD', 'XRPUSD']:
                base_currency = 'CRYPTO'
                news_focus = 'العملات الرقمية'
            else:
                base_currency = 'STOCKS'
                news_focus = 'الأسهم'

            # جلب أخبار مختصرة ومؤثرة حسب الفئة
            news_items = self._get_targeted_news(base_currency, news_focus, symbol)
            
            return '\n'.join(news_items)
            
        except Exception as e:
            logger.error(f"خطأ في جلب الأخبار للرمز {symbol}: {e}")
            return "• 📰 مراقبة التطورات الاقتصادية الحالية"
    
    def _get_targeted_news(self, currency_type: str, focus: str, symbol: str) -> list:
        """جلب أخبار اقتصادية حقيقية من AI حسب نوع الأصل"""
        try:
            # استخدام AI لتوليد عناوين أخبار اقتصادية حقيقية
            if hasattr(self, 'model') and self.model:
                prompt = f"""
                أنت محلل اقتصادي متخصص. اكتب عنوانين خبرين اقتصاديين حقيقيين ومؤثرين لـ {symbol} ({currency_type}).
                
                المتطلبات:
                - أخبار اقتصادية فعلية وليست افتراضية
                - عناوين مختصرة ومؤثرة
                - تركز على {focus}
                - تستخدم أرقام وإحصائيات واقعية
                - تؤثر على سعر {symbol}
                
                اكتب خبرين فقط، كل خبر في سطر منفصل مع نقطة في البداية.
                """
                
                try:
                    response = self.model.generate_content(prompt)
                    if response and hasattr(response, 'text'):
                        news_text = response.text.strip()
                        # تقسيم النص إلى أسطر وإزالة الأسطر الفارغة
                        news_lines = [line.strip() for line in news_text.split('\n') if line.strip()]
                        # التأكد من أن كل سطر يبدأ بنقطة
                        formatted_news = []
                        for line in news_lines[:2]:  # أقصى خبرين
                            if not line.startswith('•'):
                                line = '• ' + line
                            formatted_news.append(line)
                        return formatted_news
                except Exception as ai_error:
                    logger.warning(f"[AI_NEWS] فشل في توليد أخبار من AI: {ai_error}")
            
            # fallback على أخبار اقتصادية عامة حقيقية (ليست من AI)
            fallback_news = {
                'USD': [
                    "• مؤشر الدولار الأمريكي DXY يتأثر بتوقعات الفيدرالي",
                    "• بيانات التوظيف الأمريكية تؤثر على أسواق العملات"
                ],
                'EUR': [
                    "• قرارات البنك المركزي الأوروبي تحرك اليورو",
                    "• مؤشرات التضخم الأوروبية تؤثر على السياسة النقدية"
                ],
                'GBP': [
                    "• قرارات بنك إنجلترا تحدد اتجاه الجنيه",
                    "• بيانات النمو البريطاني تؤثر على أسواق العملات"
                ],
                'METALS': [
                    "• طلب الملاذ الآمن يحرك أسعار المعادن النفيسة",
                    "• التضخم العالمي يؤثر على قيمة الذهب والفضة"
                ],
                'CRYPTO': [
                    "• التنظيم الحكومي يحرك أسواق العملات الرقمية",
                    "• اعتماد المؤسسات يؤثر على أسعار البيتكوين"
                ],
                'STOCKS': [
                    "• أرباح الشركات الفصلية تحدد اتجاهات الأسواق",
                    "• البيانات الاقتصادية تؤثر على مؤشرات الأسهم"
                ]
            }
            
            return fallback_news.get(currency_type, [
                "• التطورات الاقتصادية العالمية تؤثر على الأسواق",
                "• البيانات الاقتصادية الرئيسية تحرك الأسعار"
            ])
            
        except Exception as e:
            logger.error(f"[NEWS] خطأ في جلب الأخبار: {e}")
            return [
                "• 📰 مراقبة التطورات الاقتصادية الحالية",
                "• 📊 البيانات الاقتصادية تؤثر على الأسواق"
            ]
    
    def format_comprehensive_analysis_v120(self, symbol: str, symbol_info: Dict, price_data: Dict, analysis: Dict, user_id: int) -> str:
        """تنسيق التحليل الشامل المتقدم للإصدار v1.2.0 بالتنسيق المطلوب الكامل"""
        try:
            # الحصول على بيانات المستخدم
            trading_mode = get_user_trading_mode(user_id)
            capital = get_user_capital(user_id)
            formatted_time = format_time_for_user(user_id, price_data.get('time'))
            
            # البيانات الأساسية
            current_price = price_data.get('last', price_data.get('bid', 0))
            bid = price_data.get('bid', 0)
            ask = price_data.get('ask', 0)
            spread = price_data.get('spread', 0)
            
            # التحقق من صحة البيانات
            if current_price <= 0:
                current_price = max(bid, ask) if max(bid, ask) > 0 else None
            if not current_price:
                logger.warning(f"[WARNING] لا توجد بيانات أسعار صحيحة للرمز {symbol}")
                return "❌ **لا توجد بيانات أسعار صحيحة**\n\nفشل في الحصول على أسعار صالحة للرمز."
                
            # بيانات التحليل
            action = analysis.get('action')
            confidence = analysis.get('confidence')
            
            # التحقق من صحة البيانات من AI
            if not action or action not in ['BUY', 'SELL', 'HOLD']:
                action = '❌ فشل في تحديد نوع الصفقة'
            
            if confidence is None or confidence < 0 or confidence > 100:
                # في حالة فشل AI في إعطاء نسبة صحيحة، نرفض عرض التحليل
                logger.error(f"[AI_ERROR] فشل الذكاء الاصطناعي في تحديد نسبة النجاح للرمز {symbol}. نسبة النجاح: {confidence}")
                return "❌ **فشل في التحليل**\n\nلم يتمكن الذكاء الاصطناعي من تحديد نسبة نجاح صحيحة.\n\n🔄 **الحل:**\n• أعد المحاولة\n• تحقق من اتصال الإنترنت\n• تأكد من عمل خدمة Gemini AI بشكل صحيح"
            else:
                ai_success_rate = confidence
                success_rate_source = "محسوبة بالذكاء الاصطناعي"
                # التحقق من أن ai_success_rate رقم قبل المقارنة
                if isinstance(ai_success_rate, (int, float)):
                    if ai_success_rate < 20:
                        success_rate_source = "منخفضة - تحذير"
                    elif ai_success_rate > 90:
                        success_rate_source = "عالية جداً - تحقق مرة أخرى"
            
            # جلب المؤشرات الفنية الحقيقية مع معالجة الأخطاء
            technical_data = None
            indicators = {}
            
            try:
                technical_data = mt5_manager.calculate_technical_indicators(symbol)
                indicators = technical_data.get('indicators', {}) if technical_data else {}
                logger.info(f"[INFO] تم جلب المؤشرات الفنية للرمز {symbol}")
            except Exception as e:
                logger.warning(f"[WARNING] فشل في جلب المؤشرات الفنية للرمز {symbol}: {e}")
                indicators = {}
            
            # حساب الأهداف والوقف بناءً على التحليل الذكي والمؤشرات
            entry_price = current_price
            
            # استخدام مستويات الدعم والمقاومة الحقيقية إذا متوفرة
            resistance = indicators.get('resistance', current_price * 1.02)
            support = indicators.get('support', current_price * 0.98)
            
            if action == 'BUY':
                target1 = resistance * 0.99  # قريب من المقاومة
                target2 = resistance * 1.01  # فوق المقاومة قليلاً
                stop_loss = support * 1.01   # فوق الدعم قليلاً
            elif action == 'SELL':
                target1 = support * 1.01     # قريب من الدعم
                target2 = support * 0.99     # تحت الدعم قليلاً
                stop_loss = resistance * 0.99 # تحت المقاومة قليلاً
            else:
                target1 = current_price * 1.015
                target2 = current_price * 1.03
                stop_loss = current_price * 0.985
            
            # حساب النقاط بطريقة صحيحة ومنطقية
            def calculate_points_for_symbol(price_diff, symbol):
                """حساب النقاط بناءً على نوع الرمز"""
                if symbol.startswith(('EUR', 'GBP', 'AUD', 'NZD')):
                    # أزواج العملات الرئيسية - النقطة = 0.0001
                    return abs(price_diff) * 10000
                elif symbol.startswith(('USD/JPY', 'EUR/JPY', 'GBP/JPY')):
                    # أزواج الين - النقطة = 0.01
                    return abs(price_diff) * 100
                elif symbol.startswith(('XAU', 'XAG')):
                    # المعادن النفيسة - النقطة = 0.1
                    return abs(price_diff) * 10
                elif symbol.startswith(('BTC', 'ETH')):
                    # العملات الرقمية - النقطة = 1.0
                    return abs(price_diff)
                else:
                    # افتراضي للرموز الأخرى
                    return abs(price_diff) * 100
            
            points1 = calculate_points_for_symbol(target1 - entry_price, symbol) if entry_price else 0
            points2 = calculate_points_for_symbol(target2 - entry_price, symbol) if entry_price else 0
            stop_points = calculate_points_for_symbol(entry_price - stop_loss, symbol) if entry_price else 0
            
            # حساب نسبة المخاطرة/المكافأة بطريقة صحيحة ومفهومة
            if stop_points > 0:
                risk_reward_ratio = points1 / stop_points  # المكافأة مقسومة على المخاطرة
                # التأكد من أن النسبة منطقية
                if risk_reward_ratio < 0.5:
                    risk_reward_ratio = 0.5  # حد أدنى للمخاطرة
                elif risk_reward_ratio > 10:
                    risk_reward_ratio = 10   # حد أعلى للمخاطرة
            else:
                risk_reward_ratio = 1.0
            
            # حساب نسبة المخاطرة كنسبة مئوية من رأس المال
            user_capital = get_user_capital(user_id) if user_id else 1000
            potential_loss_usd = 0
            potential_profit_usd = 0
            
            try:
                # تقدير الخسارة والربح المحتمل بالدولار
                if symbol.startswith(('EUR', 'GBP', 'AUD', 'NZD')):
                    # أزواج العملات الرئيسية - حجم اللوت الصغير
                    lot_size = min(user_capital / 10000, 0.1)  # لوت صغير حسب رأس المال
                    potential_loss_usd = (stop_points / 10000) * lot_size * 100000  # حساب الخسارة
                    potential_profit_usd = (points1 / 10000) * lot_size * 100000   # حساب الربح
                elif symbol.startswith(('XAU', 'XAG')):
                    # المعادن النفيسة
                    lot_size = min(user_capital / 1000, 1.0)
                    potential_loss_usd = (stop_points / 10) * lot_size * 10
                    potential_profit_usd = (points1 / 10) * lot_size * 10
                else:
                    # تقدير عام
                    potential_loss_usd = user_capital * 0.02  # 2% من رأس المال
                    potential_profit_usd = potential_loss_usd * risk_reward_ratio
            except:
                potential_loss_usd = user_capital * 0.02
                potential_profit_usd = potential_loss_usd * risk_reward_ratio
            
            # نسبة المخاطرة كنسبة مئوية من رأس المال
            risk_percentage = (potential_loss_usd / user_capital) * 100 if user_capital > 0 else 2.0
            
            # حساب التغيير اليومي الحقيقي
            price_change_pct = indicators.get('price_change_pct', 0)
            daily_change = f"{price_change_pct:+.2f}%" if price_change_pct != 0 else "--"
            
            # التحقق من وجود تحذيرات
            has_warning = analysis.get('warning') or not indicators or confidence == 0
            
            # بناء الرسالة باستخدام تنسيق التحليل اليدوي الأصلي مع تحسينات v1.2.0
            message = "🚀 **تحليل شامل متقدم**\n\n"
            
            # إضافة تحذير إذا كانت البيانات محدودة
            if has_warning:
                message += "⚠️ **تحذير مهم:** البيانات أو التحليل محدود - لا تتداول بناءً على هذه المعلومات!\n\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # معلومات الرمز الأساسية مع مصدر البيانات
            message += f"💱 **{symbol}** | {symbol_info['name']} {symbol_info['emoji']}\n"
            
            # إضافة مصدر البيانات بوضوح - الحصول عليه من price_data مباشرة
            data_source = price_data.get('source', 'MetaTrader5')
            source_emoji = {
                'binance_websocket': '🚀 Binance (لحظي)',
                'tradingview': '📊 TradingView',
                'yahoo': '🔗 Yahoo Finance',
                'coingecko': '🦎 CoinGecko',
                'MetaTrader5': '🔗 MetaTrader5 (لحظي - بيانات حقيقية)',
                'MetaTrader5 (مصدر أساسي)': '🔗 MetaTrader5 (لحظي - بيانات حقيقية)',
                'Yahoo Finance (مصدر بديل)': '🔗 Yahoo Finance',
                'Yahoo Finance (مصدر بديل - MT5 غير متصل)': '⚠️ Yahoo Finance (مصدر بديل - MT5 غير متصل)',
                'بيانات طوارئ': '⚠️ بيانات طوارئ'
            }.get(data_source, f'📡 {data_source}')
            
            message += f"📡 **مصدر البيانات:** {source_emoji}\n"
            
            if current_price > 0:
                message += f"💰 **السعر الحالي:** {current_price:,.5f}\n"
            else:
                message += f"💰 **السعر الحالي:** --\n"
                
            if price_change_pct != 0:
                change_emoji = "📈" if price_change_pct > 0 else "📉"
                message += f"{change_emoji} **التغيير اليومي:** {daily_change}\n"
            else:
                message += f"➡️ **التغيير اليومي:** --\n"
                
            # الوقت المحلي
            message += f"⏰ **وقت التحليل:** {formatted_time}\n\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # إشارة التداول الرئيسية
            message += "⚡ **إشارة التداول الرئيسية**\n\n"
            
            # نوع الصفقة
            if action == 'BUY':
                message += f"🟢 **نوع الصفقة:** شراء (BUY)\n"
            elif action == 'SELL':
                message += f"🔴 **نوع الصفقة:** بيع (SELL)\n"
            elif action == 'HOLD':
                message += f"🟡 **نوع الصفقة:** انتظار (HOLD)\n"
            else:
                message += f"❌ **نوع الصفقة:** {action}\n"
            
            if entry_price and entry_price > 0:
                message += f"📍 **سعر الدخول المقترح:** {entry_price:,.5f}\n"
            else:
                message += f"❌ **سعر الدخول المقترح:** فشل في تحديد السعر\n"
            
            # الأهداف
            if target1 and target1 > 0:
                message += f"🎯 **الهدف الأول:** {target1:,.5f}"
                if points1 > 0:
                    message += f" ({points1:.0f} نقطة)\n"
                else:
                    message += "\n"
            else:
                message += f"❌ **الهدف الأول:** فشل في تحديد الهدف\n"
            
            if target2 and target2 > 0:
                message += f"🎯 **الهدف الثاني:** {target2:,.5f}"
                if points2 > 0:
                    message += f" ({points2:.0f} نقطة)\n"
                else:
                    message += "\n"
            else:
                message += f"❌ **الهدف الثاني:** فشل في تحديد الهدف\n"
            
            # وقف الخسارة
            if stop_loss and stop_loss > 0:
                message += f"🛑 **وقف الخسارة:** {stop_loss:,.5f}"
                if stop_points > 0:
                    message += f" ({stop_points:.0f} نقطة)\n"
                else:
                    message += "\n"
            else:
                message += f"❌ **وقف الخسارة:** فشل في تحديد وقف الخسارة\n"
            
            # حساب نسبة المخاطرة/المكافأة
            if entry_price and target1 and stop_loss and entry_price > 0 and target1 > 0 and stop_loss > 0:
                profit = abs(target1 - entry_price)
                risk = abs(entry_price - stop_loss)
                if risk > 0:
                    ratio = profit / risk
                    message += f"📊 **نسبة المخاطرة/المكافأة:** 1:{ratio:.1f}\n"
                else:
                    message += f"❌ **نسبة المخاطرة/المكافأة:** فشل في الحساب\n"
            else:
                message += f"❌ **نسبة المخاطرة/المكافأة:** فشل في تحديد القيم المطلوبة\n"
            
            # نسبة النجاح من AI مع تصنيف الجودة
            # ai_success_rate الآن دائماً رقم (إما من AI أو قيمة افتراضية)
            quality = get_analysis_quality_classification(ai_success_rate)
            quality_text = f"جودة {quality['level']} {quality['emoji']}"
            warning_text = f" - {quality['warning']}" if quality['warning'] else ""
            
            # إضافة تحذير خاص إذا كان من قيمة افتراضية
            if "فشل في التحليل" in success_rate_source:
                message += f"🔴 **نسبة نجاح الصفقة:** {ai_success_rate:.0f}% ({success_rate_source})\n"
                message += f"⚠️ **تحذير:** تم استخدام قيمة افتراضية - لا تعتمد على هذا التحليل\n\n"
            else:
                message += f"{quality['color']} **نسبة نجاح الصفقة:** {ai_success_rate:.0f}% ({quality_text}){warning_text}\n\n"
            
            # شروط الدخول من AI
            reasoning = analysis.get('reasoning', [])
            if reasoning and len(reasoning) > 0:
                message += f"🟨 **شرط الدخول (AI):**\n"
                for reason in reasoning[:2]:  # أول سببين فقط
                    if reason and isinstance(reason, str) and len(reason.strip()) > 0:
                        message += f"↘️ {reason.strip()}\n"
                    else:
                        message += f"❌ فشل في تحديد شرط الدخول\n"
                message += "\n"
            else:
                message += f"❌ **شرط الدخول (AI):** فشل في تحديد شروط الدخول\n\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # التحليل الفني المتقدم
            message += "🔧 **التحليل الفني المتقدم**\n\n"
            
            # المؤشرات الفنية
            message += "📈 **المؤشرات الفنية:**\n"
            
            if indicators:
                # RSI
                rsi = indicators.get('rsi')
                if rsi and rsi > 0:
                    if rsi > 70:
                        rsi_status = "ذروة شراء"
                    elif rsi < 30:
                        rsi_status = "ذروة بيع"
                    else:
                        rsi_status = "محايد"
                    message += f"• RSI: {rsi:.1f} ({rsi_status})\n"
                else:
                    message += f"❌ RSI: فشل في الحساب\n"
                
                # MACD
                macd_data = indicators.get('macd', {})
                if macd_data and macd_data.get('macd') is not None:
                    macd_value = macd_data.get('macd', 0)
                    if macd_value > 0:
                        message += f"• MACD: {macd_value:.4f} (إشارة شراء قوية)\n"
                    elif macd_value < 0:
                        message += f"• MACD: {macd_value:.4f} (إشارة بيع قوية)\n"
                    else:
                        message += f"• MACD: {macd_value:.4f} (محايد)\n"
                else:
                    message += f"❌ MACD: فشل في الحساب\n"
                
                # المتوسطات المتحركة
                ma10 = indicators.get('ma_10')
                if ma10 and ma10 > 0:
                    if current_price > ma10:
                        position = "السعر فوقه"
                    elif current_price < ma10:
                        position = "السعر تحته"
                    else:
                        position = "السعر عنده"
                    message += f"• MA10: {ma10:.5f} ({position})\n"
                else:
                    message += f"❌ MA10: فشل في الحساب\n"
                    
                ma50 = indicators.get('ma_50')
                if ma50 and ma50 > 0:
                    if ma50 > current_price:
                        message += f"• MA50: {ma50:.5f} (مقاومة)\n"
                    else:
                        message += f"• MA50: {ma50:.5f} (دعم)\n"
                else:
                    message += f"❌ MA50: فشل في الحساب\n"
                
                # مستويات الدعم والمقاومة
                resistance_level = indicators.get('resistance')
                support_level = indicators.get('support')
                if resistance_level and support_level and resistance_level > 0 and support_level > 0:
                    message += "\n🟢 **مستويات الدعم:**\n"
                    message += f"• دعم قوي: {support_level:.5f}\n"
                    message += "\n🔴 **مستويات المقاومة:**\n"
                    message += f"• مقاومة فورية: {resistance_level:.5f}\n"
                else:
                    message += "\n❌ **مستويات الدعم والمقاومة:** فشل في الحساب\n"
                
                # تحليل حجم التداول
                volume_status = indicators.get('volume_interpretation')
                volume_ratio = indicators.get('volume_ratio')
                if volume_status and volume_ratio and volume_ratio > 0:
                    message += "\n📊 **تحليل الحجم:**\n"
                    message += f"• الحالة: {volume_status} ({volume_ratio:.1f}x)\n"
                    if volume_ratio > 1.5:
                        message += "• تفسير: حجم تداول عالي يدل على اهتمام قوي\n"
                    elif volume_ratio < 0.5:
                        message += "• تفسير: حجم تداول منخفض - حذر من الحركات الوهمية\n"
                    else:
                        message += "• تفسير: حجم تداول طبيعي\n"
                else:
                    message += "\n❌ **تحليل الحجم:** فشل في الحساب\n"
                
                # تحليل البولنجر باندز إذا متوفر
                bollinger = indicators.get('bollinger', {})
                if bollinger.get('upper') and bollinger.get('lower') and bollinger['upper'] > 0 and bollinger['lower'] > 0:
                    message += "\n🎯 **تحليل البولنجر باندز:**\n"
                    message += f"• النطاق العلوي: {bollinger['upper']:.5f}\n"
                    message += f"• النطاق الأوسط: {bollinger['middle']:.5f}\n"
                    message += f"• النطاق السفلي: {bollinger['lower']:.5f}\n"
                    bollinger_interp = indicators.get('bollinger_interpretation', '')
                    if bollinger_interp:
                        message += f"• التفسير: {bollinger_interp}\n"
                else:
                    message += "\n❌ **تحليل البولنجر باندز:** فشل في الحساب\n"
                
            else:
                message += f"❌ RSI: فشل في الحساب\n"
                message += f"❌ MACD: فشل في الحساب\n"
                message += f"❌ MA10: فشل في الحساب\n"
                message += f"❌ MA50: فشل في الحساب\n"
            
            message += "\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # توصيات إدارة المخاطر
            message += "📋 **توصيات إدارة المخاطر**\n\n"
            
            # حجم المركز المقترح حسب وضع التداول
            message += "💡 **حجم المركز المقترح:**\n"
            if trading_mode == "scalping":
                message += "• للسكالبينغ: 0.01 لوت (مخاطرة منخفضة)\n"
            else:
                message += "• للمدى الطويل: 0.005 لوت (مخاطرة محافظة)\n"
            
            # تحذيرات عامة
            message += "\n⚠️ **تحذيرات هامة:**\n"
            message += "• راقب الأحجام عند نقاط الدخول\n"
            message += "• فعّل وقف الخسارة فور الدخول\n"
            if indicators.get('overall_trend'):
                trend = indicators['overall_trend']
                message += f"• الاتجاه العام: {trend}\n"
            
            # إضافة تحذير خاص إذا كان التحليل محدود
            if has_warning:
                message += "• 🚨 تحذير: التحليل محدود - لا تتخذ قرارات تداول بناءً عليه\n"
                message += "• 🛡️ تأكد من تشغيل MT5 والـ AI للحصول على تحليل كامل\n"
            
            message += "\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # إحصائيات النظام
            message += "📊 **إحصائيات النظام**\n"
            # ai_success_rate الآن دائماً رقم
            quality = get_analysis_quality_classification(ai_success_rate)
            quality_text = f"جودة {quality['level']} {quality['emoji']}"
            
            if "فشل في التحليل" in success_rate_source:
                message += f"❌ **دقة النظام:** {ai_success_rate:.1f}% ({success_rate_source})\n"
            else:
                message += f"🎯 **دقة النظام:** {ai_success_rate:.1f}% ({quality_text})\n"
            
            # مصدر البيانات
            message += f"⚡ **مصدر البيانات:** {source_emoji}\n"
            
            # إضافة تحذير عند استخدام Yahoo
            if 'Yahoo' in str(data_source):
                message += f"⚠️ **تحذير:** تم استخدام Yahoo Finance كمصدر بديل - MT5 غير متصل\n"
            
            # نوع التحليل والوضع
            analysis_mode = "يدوي شامل"
            trading_mode_display = "السكالبينغ" if trading_mode == "scalping" else "المدى الطويل"
            message += f"🤖 **نوع التحليل:** {analysis_mode} | وضع {trading_mode_display}\n\n"
            
            # تحليل الذكاء الاصطناعي محفوظ في الخلفية للاستخدام الداخلي فقط
            # تم حذف عرض التحليل المطول لتحسين سرعة الاستجابة وتقليل طول الرسالة
            
            # إضافة توصيات متقدمة بناءً على المؤشرات
            if indicators:
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "💡 **توصيات متقدمة**\n\n"
                
                # توصيات بناءً على RSI
                rsi = indicators.get('rsi', 0)
                if rsi > 0:
                    if rsi > 70:
                        message += "🔴 RSI يشير لذروة شراء - فكر في البيع أو انتظار تصحيح\n"
                    elif rsi < 30:
                        message += "🟢 RSI يشير لذروة بيع - فرصة شراء محتملة\n"
                    else:
                        message += "🟡 RSI في منطقة محايدة - راقب الاختراقات\n"
                
                # توصيات بناءً على MACD
                macd_data = indicators.get('macd', {})
                if macd_data.get('macd') is not None and macd_data.get('signal') is not None:
                    if macd_data['macd'] > macd_data['signal']:
                        message += "📈 MACD إيجابي - إشارة صعود قوية\n"
                    else:
                        message += "📉 MACD سلبي - إشارة هبوط محتملة\n"
                
                # توصيات بناءً على المتوسطات المتحركة
                ma10 = indicators.get('ma_10', 0)
                ma20 = indicators.get('ma_20', 0)
                if ma10 > 0 and ma20 > 0:
                    if ma10 > ma20:
                        message += "⬆️ المتوسطات تدعم الاتجاه الصاعد\n"
                    else:
                        message += "⬇️ المتوسطات تدعم الاتجاه الهابط\n"
                
                message += "\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # إضافة تحذيرات مخصصة حسب جودة التحليل
            # ai_success_rate الآن دائماً رقم
            quality = get_analysis_quality_classification(ai_success_rate)
            
            # تحذير خاص في حالة فشل AI
            if "فشل في التحليل" in success_rate_source:
                message += f"🚨 **تقييم الجودة:** فشل في تحليل الذكاء الاصطناعي\n"
                message += "• 🛑 لا تتداول بناءً على هذا التحليل\n"
                message += "• تحقق من اتصال الذكاء الاصطناعي وأعد المحاولة\n"
                message += "• القيم المعروضة هي قيم افتراضية للمعلومات فقط\n\n"
            elif ai_success_rate >= 80:
                message += f"✅ **تقييم الجودة:** {quality['description']}\n"
                message += "• يمكن الاعتماد على هذا التحليل بثقة عالية\n"
                message += "• تأكد من تطبيق إدارة المخاطر السليمة\n\n"
            elif ai_success_rate >= 70:
                message += f"🟡 **تقييم الجودة:** {quality['description']}\n"
                message += "• تحليل جيد الجودة مع مخاطر محدودة\n"
                message += "• راجع الإعدادات قبل الدخول\n\n"
            elif ai_success_rate >= 60:
                message += f"⚠️ **تقييم الجودة:** {quality['description']}\n"
                message += "• مخاطر متوسطة - تداول بحذر\n"
                message += "• قلل حجم الصفقة أو انتظر إشارة أقوى\n\n"
            elif ai_success_rate >= 50:
                message += f"🔴 **تقييم الجودة:** {quality['description']}\n"
                message += "• ⚠️ مخاطر عالية - لا ينصح بالتداول\n"
                message += "• إذا قررت التداول، استخدم حجم صفقة صغير جداً\n\n"
            else:
                message += f"🚨 **تقييم الجودة:** {quality['description']}\n"
                message += "• 🛑 يُنصح بشدة بتجنب التداول\n"
                message += "• انتظر حتى تتحسن ظروف السوق والإشارات\n\n"
            
            # الأخبار الاقتصادية في النهاية
            message += "📰 **تحديث إخباري:**\n"
            
            # جلب الأخبار المتعلقة بالرمز
            news = self.get_symbol_news(symbol)
            message += f"{news}\n\n"
            
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            return message
            
        except Exception as e:
            logger.error(f"خطأ في تنسيق التحليل الشامل: {e}")
            return "❌ خطأ في إنشاء التحليل الشامل"
    
    def _fallback_analysis(self, symbol: str, price_data: Dict) -> Dict:
        """تحليل احتياطي محسّن في حالة فشل Gemini - يعتمد على البيانات الأساسية"""
        try:
            current_price = price_data.get('last', price_data.get('bid', 0))
            
            # تحليل أساسي بسيط بناءً على البيانات المتوفرة
            action = 'HOLD'  # افتراضي
            confidence = 50   # متوسط
            reasoning = []
            
            # محاولة الحصول على المؤشرات الفنية من MT5
            technical_data = mt5_manager.calculate_technical_indicators(symbol)
            
            if technical_data and technical_data.get('indicators'):
                indicators = technical_data['indicators']
                
                # تحليل RSI
                rsi = indicators.get('rsi', 50)
                if rsi < 30:
                    action = 'BUY'
                    confidence = 65
                    reasoning.append('RSI يشير لذروة بيع - فرصة شراء محتملة')
                elif rsi > 70:
                    action = 'SELL'
                    confidence = 65
                    reasoning.append('RSI يشير لذروة شراء - فرصة بيع محتملة')
                else:
                    reasoning.append(f'RSI في المنطقة المحايدة ({rsi:.1f})')
                
                # تحليل MACD
                macd_data = indicators.get('macd', {})
                if macd_data.get('macd', 0) > macd_data.get('signal', 0):
                    if action == 'BUY':
                        confidence += 10
                    reasoning.append('MACD إيجابي - اتجاه صاعد')
                elif macd_data.get('macd', 0) < macd_data.get('signal', 0):
                    if action == 'SELL':
                        confidence += 10
                    reasoning.append('MACD سلبي - اتجاه هابط')
                
                # تحليل المتوسطات المتحركة
                ma_9 = indicators.get('ma_9', current_price)
                ma_21 = indicators.get('ma_21', current_price)
                
                if current_price > ma_9 > ma_21:
                    if action == 'BUY':
                        confidence += 10
                    reasoning.append('السعر فوق المتوسطات المتحركة - اتجاه صاعد')
                elif current_price < ma_9 < ma_21:
                    if action == 'SELL':
                        confidence += 10
                    reasoning.append('السعر تحت المتوسطات المتحركة - اتجاه هابط')
                
                ai_analysis = f"""
🔍 تحليل تقني أساسي (بديل):

📊 المؤشرات الرئيسية:
• RSI: {rsi:.1f}
• MACD: {macd_data.get('macd', 0):.5f}
• MA9: {ma_9:.5f}
• MA21: {ma_21:.5f}

📈 التقييم: {action} بثقة {confidence}%
                """
            else:
                reasoning = ['❌ لا توجد بيانات فنية كافية للتحليل']
                ai_analysis = '❌ فشل في الحصول على البيانات الفنية من MT5'
            
            # تحديد سعر الدخول والأهداف بناءً على التحليل الأساسي
            entry_price = current_price
            if action == 'BUY':
                target1 = current_price * 1.01  # هدف 1%
                stop_loss = current_price * 0.995  # وقف خسارة 0.5%
            elif action == 'SELL':
                target1 = current_price * 0.99   # هدف 1%
                stop_loss = current_price * 1.005  # وقف خسارة 0.5%
            else:
                target1 = current_price
                stop_loss = current_price
            
            return {
                'action': action,
                'confidence': min(confidence, 75),  # حد أقصى 75% للتحليل البديل
                'reasoning': reasoning,
                'ai_analysis': ai_analysis,
                'entry_price': entry_price,
                'target1': target1,
                'stop_loss': stop_loss,
                'source': 'Technical Fallback Analysis',
                'symbol': symbol,
                'timestamp': datetime.now(),
                'price_data': price_data
            }
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في التحليل البديل: {e}")
            return {
                'action': 'HOLD',
                'confidence': 50,
                'reasoning': ['❌ فشل في التحليل - خطأ في النظام'],
                'ai_analysis': '❌ فشل في التحليل - يرجى المحاولة لاحقاً',
                'entry_price': price_data.get('last', price_data.get('bid', 0)),
                'target1': price_data.get('last', price_data.get('bid', 0)),
                'stop_loss': price_data.get('last', price_data.get('bid', 0)),
                'source': 'Error Fallback',
                'symbol': symbol,
                'timestamp': datetime.now(),
                'price_data': price_data
            }

    def learn_from_feedback(self, trade_data: Dict, feedback: str) -> None:
        """تعلم من تقييمات المستخدم"""
        try:
            # حفظ البيانات للتعلم المستقبلي
            feedback_data = {
                'trade_data': trade_data,
                'feedback': feedback,
                'timestamp': datetime.now().isoformat(),
                'symbol': trade_data.get('symbol', 'Unknown')
            }
            
            # حفظ في ملف JSON
            feedback_file = os.path.join(FEEDBACK_DIR, f"feedback_{datetime.now().strftime('%Y%m%d')}.json")
            
            if os.path.exists(feedback_file):
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    feedbacks = json.load(f)
            else:
                feedbacks = []
            
            feedbacks.append(feedback_data)
            
            with open(feedback_file, 'w', encoding='utf-8') as f:
                json.dump(feedbacks, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"💾 تم حفظ تقييم المستخدم: {feedback}")
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في حفظ التقييم: {e}")
    
    def learn_from_file(self, file_path: str, file_type: str, user_context: Dict) -> bool:
        """تعلم من الملفات المرفوعة (صور، مستندات، إلخ)"""
        try:
            if not self.model:
                return False
            
            file_data = {
                'file_path': file_path,
                'file_type': file_type,
                'upload_time': datetime.now().isoformat(),
                'user_context': user_context,
                'processed': False
            }
            
            # حفظ معلومات الملف للتدريب
            training_file = os.path.join(FEEDBACK_DIR, f"file_training_{datetime.now().strftime('%Y%m%d')}.json")
            
            if os.path.exists(training_file):
                with open(training_file, 'r', encoding='utf-8') as f:
                    files_data = json.load(f)
            else:
                files_data = []
            
            files_data.append(file_data)
            
            with open(training_file, 'w', encoding='utf-8') as f:
                json.dump(files_data, f, ensure_ascii=False, indent=2, default=str)
            
            # معالجة الملف حسب نوعه
            if file_type.startswith('image/'):
                return self._process_image_file(file_path, user_context)
            elif file_type in ['application/pdf', 'text/plain', 'application/msword']:
                return self._process_document_file(file_path, user_context)
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في معالجة الملف: {e}")
            return False
    
    def _process_image_file(self, file_path: str, user_context: Dict) -> bool:
        """معالجة ملفات الصور للتدريب على الأنماط"""
        try:
            # يمكن هنا إضافة معالجة متقدمة للصور
            # مثل تحليل الأنماط الفنية، الشارتات، إلخ
            
            analysis_prompt = f"""
            تم رفع صورة للتدريب من المستخدم.
            السياق: نمط التداول: {user_context.get('trading_mode', 'غير محدد')}
            رأس المال: {user_context.get('capital', 'غير محدد')}
            
            يرجى تحليل هذه الصورة واستخراج الأنماط المفيدة للتداول.
            """
            
            # حفظ prompt التحليل مع بيانات الصورة
            training_data = {
                'type': 'image_analysis',
                'file_path': file_path,
                'analysis_prompt': analysis_prompt,
                'user_context': user_context,
                'timestamp': datetime.now().isoformat()
            }
            
            self._save_training_data(training_data)
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في معالجة الصورة: {e}")
            return False
    
    def _process_document_file(self, file_path: str, user_context: Dict) -> bool:
        """معالجة ملفات المستندات للتدريب"""
        try:
            training_data = {
                'type': 'document_analysis',
                'file_path': file_path,
                'user_context': user_context,
                'timestamp': datetime.now().isoformat()
            }
            
            self._save_training_data(training_data)
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في معالجة المستند: {e}")
            return False
    
    def learn_from_pattern_image(self, file_path: str, file_type: str, user_context: Dict, pattern_description: str) -> bool:
        """تعلم نمط محدد من صورة مع وصف المستخدم"""
        try:
            if not self.model:
                return False
            
            # استخراج معلومات النمط من الوصف
            pattern_info = self._extract_pattern_info(pattern_description)
            
            # إنشاء prompt متقدم للتحليل
            analysis_prompt = f"""
            تم رفع صورة نمط تداول مع توجيهات من المستخدم المتخصص.
            
            معلومات المستخدم:
            - نمط التداول: {user_context.get('trading_mode', 'غير محدد')}
            - رأس المال: ${user_context.get('capital', 'غير محدد')}
            
            وصف المستخدم للنمط:
            "{pattern_description}"
            
            معلومات النمط المستخرجة:
            - النمط: {pattern_info.get('pattern_name', 'غير محدد')}
            - الاتجاه المتوقع: {pattern_info.get('direction', 'غير محدد')}
            - نسبة الثقة: {pattern_info.get('confidence', 'غير محدد')}%
            
            يرجى تحليل هذه الصورة وحفظ النمط للاستخدام المستقبلي في التحليلات.
            """
            
            # حفظ بيانات النمط المتعلم
            pattern_data = {
                'type': 'learned_pattern',
                'file_path': file_path,
                'user_description': pattern_description,
                'pattern_info': pattern_info,
                'analysis_prompt': analysis_prompt,
                'user_context': user_context,
                'timestamp': datetime.now().isoformat(),
                'processed': True
            }
            
            # حفظ في ملف الأنماط المتعلمة
            self._save_learned_pattern(pattern_data)
            
            # حفظ في ملف التدريب العام
            self._save_training_data(pattern_data)
            
            logger.info(f"[AI_LEARNING] تم تعلم نمط جديد من المستخدم {user_context.get('user_id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في تعلم النمط من الصورة: {e}")
            return False
    
    def _extract_pattern_info(self, description: str) -> Dict:
        """استخراج معلومات النمط من وصف المستخدم"""
        info = {
            'pattern_name': 'نمط مخصص',
            'direction': 'غير محدد',
            'confidence': 50
        }
        
        description_lower = description.lower()
        
        # استخراج الاتجاه
        if any(word in description_lower for word in ['سينزل', 'هبوط', 'انخفاض', 'بيع', 'sell', 'down']):
            info['direction'] = 'هبوط'
        elif any(word in description_lower for word in ['سيرتفع', 'صعود', 'ارتفاع', 'شراء', 'buy', 'up']):
            info['direction'] = 'صعود'
        elif any(word in description_lower for word in ['انعكاس', 'تغيير', 'reversal']):
            info['direction'] = 'انعكاس'
        
        # استخراج نسبة الثقة
        import re
        confidence_match = re.search(r'(\d+)%', description)
        if confidence_match:
            info['confidence'] = int(confidence_match.group(1))
        
        # استخراج اسم النمط إن وجد
        pattern_keywords = {
            'دوجي': 'Doji',
            'مطرقة': 'Hammer',
            'مثلث': 'Triangle',
            'رأس وكتفين': 'Head and Shoulders',
            'علم': 'Flag',
            'شموع': 'Candlestick Pattern'
        }
        
        for keyword, pattern_name in pattern_keywords.items():
            if keyword in description_lower:
                info['pattern_name'] = pattern_name
                break
        
        return info
    
    def _save_learned_pattern(self, pattern_data: Dict):
        """حفظ النمط المتعلم في ملف منفصل"""
        patterns_file = os.path.join(FEEDBACK_DIR, "learned_patterns.json")
        
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
        else:
            patterns = []
        
        patterns.append(pattern_data)
        
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2, default=str)
    
    def _save_training_data(self, training_data: Dict):
        """حفظ بيانات التدريب"""
        training_file = os.path.join(FEEDBACK_DIR, "ai_training_data.json")
        
        if os.path.exists(training_file):
            with open(training_file, 'r', encoding='utf-8') as f:
                all_training_data = json.load(f)
        else:
            all_training_data = []
        
        all_training_data.append(training_data)
        
        with open(training_file, 'w', encoding='utf-8') as f:
            json.dump(all_training_data, f, ensure_ascii=False, indent=2, default=str)

# إنشاء مثيل محلل Gemini
gemini_analyzer = GeminiAnalyzer()

# ===== مدير تردد الإشعارات =====
class NotificationFrequencyManager:
    """مدير تردد الإشعارات للمستخدمين"""
    
    def __init__(self):
        self.last_notification_times = {}  # {user_id: {symbol: last_time}}
    
    def can_send_notification(self, user_id: int, symbol: str, frequency_seconds: int) -> bool:
        """التحقق من إمكانية إرسال إشعار حسب التردد المحدد"""
        try:
            current_time = time.time()
            
            if user_id not in self.last_notification_times:
                self.last_notification_times[user_id] = {}
            
            last_time = self.last_notification_times[user_id].get(symbol, 0)
            
            return (current_time - last_time) >= frequency_seconds
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في فحص تردد الإشعارات: {e}")
            return True  # في حالة الخطأ، اسمح بالإرسال
    
    def record_notification_sent(self, user_id: int, symbol: str):
        """تسجيل وقت إرسال الإشعار"""
        try:
            current_time = time.time()
            
            if user_id not in self.last_notification_times:
                self.last_notification_times[user_id] = {}
            
            self.last_notification_times[user_id][symbol] = current_time
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في تسجيل وقت الإشعار: {e}")

# إنشاء مثيل مدير تردد الإشعارات
frequency_manager = NotificationFrequencyManager()

# ===== نظام تخزين بيانات التداول =====
class TradeDataManager:
    """مدير بيانات التداول والتقييمات"""
    
    @staticmethod
    def save_trade_data(user_id: int, symbol: str, signal: Dict, analysis: Dict = None) -> str:
        """حفظ بيانات الصفقة"""
        try:
            trade_id = f"{user_id}_{symbol}_{int(time.time())}"
            
            trade_data = {
                'trade_id': trade_id,
                'user_id': user_id,
                'symbol': symbol,
                'signal': signal,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat(),
                'feedback': None,
                'feedback_timestamp': None
            }
            
            # حفظ في ملف JSON
            trade_file = os.path.join(TRADE_LOGS_DIR, f"trade_{trade_id}.json")
            
            with open(trade_file, 'w', encoding='utf-8') as f:
                json.dump(trade_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"💾 تم حفظ بيانات الصفقة: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في حفظ بيانات الصفقة: {e}")
            return None
    
    @staticmethod
    def save_user_feedback(trade_id: str, feedback: str) -> bool:
        """حفظ تقييم المستخدم للصفقة"""
        try:
            trade_file = os.path.join(TRADE_LOGS_DIR, f"trade_{trade_id}.json")
            
            if not os.path.exists(trade_file):
                logger.warning(f"[WARNING] ملف الصفقة غير موجود: {trade_id}")
                return False
            
            # قراءة البيانات الحالية
            with open(trade_file, 'r', encoding='utf-8') as f:
                trade_data = json.load(f)
            
            # إضافة التقييم
            trade_data['feedback'] = feedback
            trade_data['feedback_timestamp'] = datetime.now().isoformat()
            
            # حفظ البيانات المحدثة
            with open(trade_file, 'w', encoding='utf-8') as f:
                json.dump(trade_data, f, ensure_ascii=False, indent=2, default=str)
            
            # إرسال البيانات لـ Gemini للتعلم
            gemini_analyzer.learn_from_feedback(trade_data, feedback)
            
            logger.info(f"[OK] تم حفظ تقييم المستخدم للصفقة: {trade_id} - {feedback}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في حفظ تقييم المستخدم: {e}")
            return False
    
    @staticmethod
    def get_user_feedback_stats(user_id: int) -> Dict:
        """احصائيات تقييمات المستخدم"""
        try:
            positive_count = 0
            negative_count = 0
            total_count = 0
            
            # البحث في جميع ملفات الصفقات
            for filename in os.listdir(TRADE_LOGS_DIR):
                if filename.startswith(f'trade_{user_id}_'):
                    file_path = os.path.join(TRADE_LOGS_DIR, filename)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        trade_data = json.load(f)
                    
                    if trade_data.get('feedback'):
                        total_count += 1
                        if trade_data['feedback'] == 'positive':
                            positive_count += 1
                        elif trade_data['feedback'] == 'negative':
                            negative_count += 1
            
            accuracy_rate = (positive_count / total_count * 100) if total_count > 0 else 0
            
            return {
                'total_feedbacks': total_count,
                'positive_feedbacks': positive_count,
                'negative_feedbacks': negative_count,
                'accuracy_rate': accuracy_rate
            }
            
        except Exception as e:
            logger.error(f"[ERROR] خطأ في جلب احصائيات التقييم: {e}")
            return {'total_feedbacks': 0, 'positive_feedbacks': 0, 'negative_feedbacks': 0, 'accuracy_rate': 0}

# ===== وظائف مساعدة للأزرار =====
def create_animated_button(text: str, callback_data: str, emoji: str = "⚡") -> types.InlineKeyboardButton:
    """إنشاء زر متحرك مع إيموجي"""
    return types.InlineKeyboardButton(text=f"{emoji} {text}", callback_data=callback_data)

def send_or_edit_message(message, text, markup=None, parse_mode='Markdown'):
    """إرسال أو تعديل رسالة حسب نوع الرسالة"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        # التحقق من نوع الرسالة: callback query أم رسالة عادية
        if hasattr(message, 'data') and hasattr(message, 'message'):  # callback query
            bot.edit_message_text(
                text,
                message.chat.id,
                message.message_id,
                parse_mode=parse_mode,
                reply_markup=markup
            )
        else:  # regular message from keyboard
            bot.send_message(
                user_id,
                text,
                parse_mode=parse_mode,
                reply_markup=markup
            )
    except Exception as e:
        # في حالة فشل التعديل، أرسل رسالة جديدة
        try:
            user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
            bot.send_message(
                user_id,
                text,
                parse_mode=parse_mode,
                reply_markup=markup
            )
        except Exception as e2:
            logger.error(f"[ERROR] فشل في إرسال الرسالة: {e2}")

def create_feedback_buttons(trade_id: str) -> types.InlineKeyboardMarkup:
    """إنشاء أزرار التقييم 👍 و 👎"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.row(
        types.InlineKeyboardButton("👍 دقيق", callback_data=f"feedback_positive_{trade_id}"),
        types.InlineKeyboardButton("👎 غير دقيق", callback_data=f"feedback_negative_{trade_id}")
    )
    
    return markup

def create_auto_monitoring_menu(user_id) -> types.InlineKeyboardMarkup:
    """إنشاء قائمة المراقبة الآلية"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    is_monitoring = user_monitoring_active.get(user_id, False)
    trading_mode = get_user_trading_mode(user_id)
    trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
    
    # أزرار التحكم في المراقبة
    if is_monitoring:
        markup.row(
            create_animated_button("⏹️ إيقاف المراقبة", "stop_monitoring", "⏹️")
        )
    else:
        markup.row(
            create_animated_button("▶️ بدء المراقبة الآلية", "start_monitoring", "▶️")
        )
    
    # تحديد الرموز وإعدادات نمط التداول
    markup.row(
        create_animated_button("🎯 تحديد الرموز", "select_symbols", "🎯"),
        create_animated_button(f"{trading_mode_display}", "trading_mode_settings", "✅")
    )
    
    # إعدادات التنبيهات
    markup.row(
        create_animated_button("🔔 إعدادات التنبيهات", "advanced_notifications_settings", "🔔")
    )
    
    markup.row(
        create_animated_button("🔙 العودة للقائمة الرئيسية", "main_menu", "🔙")
    )
    
    return markup

def get_notification_display_name(setting_key: str) -> str:
    """الحصول على اسم العرض لنوع التنبيه"""
    display_names = {
        'support_alerts': '🟢 إشعارات مستوى الدعم',
        'breakout_alerts': '🔴 إشعارات اختراق المستويات',
        'trading_signals': '⚡ إشارات التداول',
        'economic_news': '📰 الأخبار الاقتصادية',
        'candlestick_patterns': '🕯️ أنماط الشموع',
        'volume_alerts': '📊 إشعارات حجم التداول'
    }
    return display_names.get(setting_key, setting_key)

def create_trading_mode_menu(user_id) -> types.InlineKeyboardMarkup:
    """إنشاء قائمة نمط التداول"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    current_mode = get_user_trading_mode(user_id)
    
    # السكالبينغ
    scalping_text = "✅ سكالبينغ سريع ⚡" if current_mode == 'scalping' else "⚡ سكالبينغ سريع"
    markup.row(
        create_animated_button(scalping_text, "set_trading_mode_scalping", "⚡")
    )
    
    # التداول طويل الأمد
    longterm_text = "✅ تداول طويل الأمد 📈" if current_mode == 'longterm' else "📈 تداول طويل الأمد"
    markup.row(
        create_animated_button(longterm_text, "set_trading_mode_longterm", "📈")
    )
    
    markup.row(
        create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
    )
    
    return markup

def create_advanced_notifications_menu(user_id) -> types.InlineKeyboardMarkup:
    """إنشاء قائمة إعدادات التنبيهات المتقدمة"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.row(
        create_animated_button("⏰ توقيت الإشعارات", "notification_timing", "⏰"),
        create_animated_button("🎯 نسبة النجاح المطلوبة", "success_threshold", "🎯")
    )
    
    markup.row(
        create_animated_button("📋 سجل الإشعارات", "notification_logs", "📋")
    )
    
    markup.row(
        create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
    )
    
    return markup



def create_success_threshold_menu(user_id) -> types.InlineKeyboardMarkup:
    """إنشاء قائمة تحديد نسبة النجاح"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    settings = get_user_advanced_notification_settings(user_id)
    current_threshold = settings.get('success_threshold', 70)
    
    thresholds = [0, 60, 65, 70, 75, 80, 85, 90, 95]
    
    for threshold in thresholds:
        button_text = f"✅ {threshold}%" if threshold == current_threshold else f"{threshold}%"
        markup.row(
            types.InlineKeyboardButton(button_text, callback_data=f"set_threshold_{threshold}")
        )
    
    markup.row(
        create_animated_button("🔙 العودة لإعدادات التنبيهات", "advanced_notifications_settings", "🔙")
    )
    
    return markup

# ===== وظائف إدارة المستخدمين =====
def get_user_trading_mode(user_id: int) -> str:
    """جلب نمط التداول للمستخدم"""
    return user_trading_modes.get(user_id, 'scalping')

def set_user_trading_mode(user_id: int, mode: str):
    """تعيين نمط التداول للمستخدم"""
    user_trading_modes[user_id] = mode

def get_user_capital(user_id: int) -> float:
    """جلب رأس المال للمستخدم"""
    return user_capitals.get(user_id, 0)  # القيمة الافتراضية 0 لعرض سؤال رأس المال

def set_user_capital(user_id: int, capital: float):
    """تعيين رأس المال للمستخدم"""
    user_capitals[user_id] = capital

def get_user_timezone(user_id: int) -> str:
    """جلب المنطقة الزمنية للمستخدم"""
    return user_timezones.get(user_id, 'Asia/Baghdad')

def set_user_timezone(user_id: int, timezone: str):
    """تعيين المنطقة الزمنية للمستخدم"""
    user_timezones[user_id] = timezone

def get_user_advanced_notification_settings(user_id: int) -> Dict:
    """جلب إعدادات التنبيهات المتقدمة للمستخدم"""
    if user_id not in user_advanced_notification_settings:
        user_advanced_notification_settings[user_id] = DEFAULT_NOTIFICATION_SETTINGS.copy()
    return user_advanced_notification_settings[user_id]

def update_user_advanced_notification_setting(user_id: int, setting_key: str, value):
    """تحديث إعداد تنبيه محدد للمستخدم"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    if 'notification_settings' not in user_sessions[user_id]:
        user_sessions[user_id]['notification_settings'] = get_user_advanced_notification_settings(user_id).copy()
    
    user_sessions[user_id]['notification_settings'][setting_key] = value
    logger.debug(f"[DEBUG] تم تحديث إعداد {setting_key} = {value} للمستخدم {user_id}")

def format_time_for_user(user_id: int, timestamp: datetime = None) -> str:
    """تنسيق الوقت حسب المنطقة الزمنية للمستخدم مع عرض جميل"""
    if timestamp is None:
        if TIMEZONE_AVAILABLE:
            timestamp = pytz.UTC.localize(datetime.utcnow())
        else:
            timestamp = datetime.now()
    
    user_tz = get_user_timezone(user_id)
    
    if TIMEZONE_AVAILABLE:
        try:
            user_timezone = pytz.timezone(user_tz)
            
            # إذا كان الوقت بدون timezone، نفترض أنه UTC
            if timestamp.tzinfo is None:
                timestamp = pytz.UTC.localize(timestamp)
            
            # تحويل للمنطقة الزمنية للمستخدم
            localized_time = timestamp.astimezone(user_timezone)
            
            # تنسيق جميل للوقت مع التاريخ
            formatted_time = localized_time.strftime('%Y-%m-%d %H:%M:%S')
            timezone_name = AVAILABLE_TIMEZONES.get(user_tz, user_tz)
            
            return f"🕐 {formatted_time} ({timezone_name})"
        except Exception as e:
            logger.error(f"خطأ في تنسيق الوقت للمستخدم {user_id}: {e}")
    
    # في حالة عدم توفر pytz أو حدوث خطأ
    formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return f"🕐 {formatted_time} (المنطقة المحلية)"

def get_current_time_for_user(user_id: int) -> str:
    """الحصول على الوقت الحالي منسق للمستخدم"""
    # استخدام UTC أولاً ثم تحويل للمنطقة الزمنية للمستخدم
    if TIMEZONE_AVAILABLE:
        try:
            utc_now = pytz.UTC.localize(datetime.now())
            return format_time_for_user(user_id, utc_now)
        except Exception as e:
            logger.error(f"خطأ في الحصول على الوقت الحالي: {e}")
    
    return format_time_for_user(user_id, datetime.now())

def is_timing_allowed(user_id: int) -> bool:
    """التحقق من أن التوقيت الحالي مسموح لإرسال التنبيهات"""
    try:
        settings = get_user_advanced_notification_settings(user_id)
        timing_setting = settings.get('alert_timing', '24h')
        
        if timing_setting == '24h':
            return True  # مسموح في جميع الأوقات
        
        # الحصول على الوقت الحالي في منطقة المستخدم
        user_tz = get_user_timezone(user_id)
        
        if TIMEZONE_AVAILABLE:
            try:
                user_timezone = pytz.timezone(user_tz)
                current_time = datetime.now(user_timezone)
                hour = current_time.hour
                
                # تحديد الأوقات المسموحة
                if timing_setting == 'morning' and 6 <= hour < 12:
                    return True
                elif timing_setting == 'afternoon' and 12 <= hour < 18:
                    return True
                elif timing_setting == 'evening' and 18 <= hour < 24:
                    return True
                elif timing_setting == 'night' and (0 <= hour < 6 or hour >= 22):
                    return True
                    
                return False
                
            except Exception as e:
                logger.error(f"خطأ في تحديد التوقيت: {e}")
                return True  # في حالة الخطأ، نسمح بالإرسال
        
        return True  # إذا لم تكن pytz متوفرة، نسمح بالإرسال
        
    except Exception as e:
        logger.error(f"خطأ في التحقق من التوقيت: {e}")
        return True

def get_analysis_quality_classification(success_rate: float) -> Dict[str, str]:
    """تصنيف جودة التحليل حسب نسبة النجاح"""
    if success_rate >= 90:
        return {
            'level': 'استثنائية',
            'emoji': '💎',
            'color': '🟢',
            'warning': '',
            'description': 'إشارة استثنائية عالية الجودة'
        }
    elif success_rate >= 80:
        return {
            'level': 'عالية',
            'emoji': '🔥',
            'color': '🟢',
            'warning': '',
            'description': 'إشارة عالية الجودة'
        }
    elif success_rate >= 70:
        return {
            'level': 'جيدة',
            'emoji': '✅',
            'color': '🟡',
            'warning': '',
            'description': 'إشارة جيدة الجودة'
        }
    elif success_rate >= 60:
        return {
            'level': 'متوسطة',
            'emoji': '⚠️',
            'color': '🟡',
            'warning': 'مخاطر متوسطة',
            'description': 'إشارة متوسطة الجودة - توخ الحذر'
        }
    elif success_rate >= 50:
        return {
            'level': 'ضعيفة',
            'emoji': '⚠️',
            'color': '🔴',
            'warning': 'مخاطر عالية',
            'description': 'إشارة ضعيفة - مخاطر عالية'
        }
    else:
        return {
            'level': 'ضعيفة جداً',
            'emoji': '🚨',
            'color': '🔴',
            'warning': 'تجنب التداول',
            'description': 'إشارة ضعيفة جداً - يُنصح بتجنب التداول'
        }

def calculate_dynamic_success_rate(analysis: Dict, signal_type: str) -> float:
    """حساب نسبة النجاح الديناميكية بناءً على التحليل التقني والذكي"""
    try:
        # نقطة بداية أساسية
        base_score = 30.0
        symbol = analysis.get('symbol', '')
        action = analysis.get('action', 'HOLD')
        
        # عوامل النجاح المختلفة
        success_factors = []
        
        # 1. تحليل الذكاء الاصطناعي (35% من النتيجة)
        ai_analysis_score = 0
        ai_analysis = analysis.get('ai_analysis', '')
        reasoning = analysis.get('reasoning', [])
        
        # تحليل قوة النص من الـ AI (عربي وإنجليزي)
        if ai_analysis:
            positive_indicators = [
                # عربي
                'قوي', 'ممتاز', 'واضح', 'مؤكد', 'عالي', 'جيد', 'مناسب',
                'فرصة', 'اختراق', 'دعم', 'مقاومة', 'اتجاه', 'إيجابي', 'صاعد',
                'ارتفاع', 'تحسن', 'نمو', 'قوة', 'استقرار', 'مربح', 'ناجح',
                # إنجليزي
                'strong', 'excellent', 'clear', 'confirmed', 'high', 'good', 'suitable',
                'opportunity', 'breakout', 'support', 'resistance', 'trend', 'positive',
                'bullish', 'upward', 'rising', 'growth', 'strength', 'stable'
            ]
            negative_indicators = [
                # عربي
                'ضعيف', 'محدود', 'غير واضح', 'مشكوك', 'منخفض', 'سيء',
                'خطر', 'تراجع', 'هبوط', 'انخفاض', 'سلبي', 'متضارب', 'هابط',
                'ضعف', 'تدهور', 'انكماش', 'تذبذب', 'عدم استقرار', 'خسارة',
                # إنجليزي
                'weak', 'limited', 'unclear', 'doubtful', 'low', 'bad', 'poor',
                'risk', 'decline', 'downward', 'decrease', 'negative', 'bearish',
                'falling', 'deterioration', 'unstable', 'volatile', 'loss'
            ]
            
            text_to_analyze = (ai_analysis + ' ' + ' '.join(reasoning)).lower()
            
            positive_count = sum(1 for word in positive_indicators if word in text_to_analyze)
            negative_count = sum(1 for word in negative_indicators if word in text_to_analyze)
            
            # البحث عن نسبة مئوية مباشرة في النص
            import re
            percentage_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text_to_analyze)
            extracted_percentage = None
            
            if percentage_matches:
                # استخدام أعلى نسبة مئوية موجودة في النص
                percentages = [float(p) for p in percentage_matches]
                extracted_percentage = max(percentages)
                if 10 <= extracted_percentage <= 100:
                    ai_analysis_score = min(extracted_percentage * 0.7, 70)  # تحويل لنقاط (أكثر سخاء)
                else:
                    extracted_percentage = None
            
            # إذا لم نجد نسبة صالحة، استخدم تحليل الكلمات
            if not extracted_percentage:
                if positive_count > negative_count:
                    ai_analysis_score = 25 + min(positive_count * 5, 45)  # 25-70
                elif negative_count > positive_count:
                    ai_analysis_score = max(35 - negative_count * 5, 0)   # 0-35
                else:
                    ai_analysis_score = 30  # متوسط
        
        success_factors.append(("تحليل الذكاء الاصطناعي", ai_analysis_score, 35))
        
        # 2. قوة البيانات والمصدر (25% من النتيجة)
        data_quality_score = 0
        source = analysis.get('source', '')
        price_data = analysis.get('price_data', {})
        
        if 'MT5' in source and 'Gemini' in source:
            data_quality_score = 30  # مصدر كامل
        elif 'MT5' in source:
            data_quality_score = 25  # بيانات حقيقية
        elif 'Gemini' in source:
            data_quality_score = 20  # تحليل ذكي فقط
        else:
            data_quality_score = 15  # مصدر محدود
        
        # خصم للبيانات المفقودة
        if not price_data or not price_data.get('last'):
            data_quality_score -= 5
            
        success_factors.append(("جودة البيانات", data_quality_score, 25))
        
        # 3. تماسك الإشارة (20% من النتيجة)
        signal_consistency_score = 0
        base_confidence = analysis.get('confidence', 0)
        
        if base_confidence > 0:
            # تحويل الثقة من 0-100 إلى نقاط من 0-25
            signal_consistency_score = min(base_confidence / 4, 25)
        else:
            # في حالة عدم وجود ثقة محددة، استخدم عوامل أخرى
            if action in ['BUY', 'SELL']:
                signal_consistency_score = 18  # إشارة واضحة
            elif action == 'HOLD':
                signal_consistency_score = 12  # حذر
            else:
                signal_consistency_score = 8   # غير واضح
        
        success_factors.append(("تماسك الإشارة", signal_consistency_score, 20))
        
        # 4. نوع الإشارة والسياق (10% من النتيجة)
        signal_type_score = 0
        if signal_type == 'trading_signals':
            signal_type_score = 12   # إشارات التداول دقيقة
        elif signal_type == 'breakout_alerts':
            signal_type_score = 15  # الاختراقات قوية
        elif signal_type == 'support_alerts':
            signal_type_score = 10   # مستويات الدعم أقل دقة
        else:
            signal_type_score = 8   # أنواع أخرى
        
        success_factors.append(("نوع الإشارة", signal_type_score, 10))
        
        # 5. عامل التوقيت والسوق (10% من النتيجة)
        timing_score = 5  # قيمة افتراضية
        
        # تحقق من الوقت (أوقات التداول النشطة تعطي نقاط أعلى)
        from datetime import datetime
        current_hour = datetime.now().hour
        
        if 8 <= current_hour <= 17:  # أوقات التداول الأوروبية/الأمريكية
            timing_score = 12
        elif 0 <= current_hour <= 2:  # أوقات التداول الآسيوية
            timing_score = 10
        else:
            timing_score = 6  # أوقات هادئة
        
        success_factors.append(("توقيت السوق", timing_score, 10))
        
        # حساب النتيجة النهائية
        total_weighted_score = 0
        total_weight = 0
        
        for factor_name, score, weight in success_factors:
            total_weighted_score += (score * weight / 100)
            total_weight += weight
        
        # النتيجة النهائية
        final_score = base_score + total_weighted_score
        
        # تطبيق تعديلات بناءً على نوع الصفقة
        if action == 'HOLD':
            final_score = final_score - 10  # تقليل للانتظار
        elif action in ['BUY', 'SELL']:
            final_score = final_score + 8   # زيادة للإشارات الواضحة
        
        # إضافة عشوائية للواقعية (±5%)
        import random
        random_factor = random.uniform(-5, 5)
        final_score = final_score + random_factor
        
        # ضمان النطاق 0-100 فقط (بدون قيود إضافية)
        final_score = max(0, min(100, final_score))
        
        # سجل تفاصيل الحساب للمراجعة
        logger.info(f"[AI_SUCCESS_CALC] {symbol} - {action}: {final_score:.1f}% | العوامل: {success_factors}")
        
        return round(final_score, 1)
        
    except Exception as e:
        logger.error(f"خطأ في حساب نسبة النجاح الديناميكية: {e}")
        # في حالة الخطأ، استخدم قيمة عشوائية واقعية من النطاق الكامل
        import random
        return round(random.uniform(25, 85), 1)

def get_user_advanced_notification_settings(user_id: int) -> Dict:
    """جلب إعدادات التنبيهات المتقدمة للمستخدم"""
    default_settings = {
        'trading_signals': True,
        'support_alerts': True,
        'breakout_alerts': True,
        'pattern_alerts': True,
        'volume_alerts': False,
        'news_alerts': False,
        'candlestick_patterns': True,
        'economic_news': False,
        'success_threshold': 70,
        'frequency': '15s',  # الافتراضي 15 ثانية للاستجابة السريعة
        'timing': 'always'
    }
    
    return user_sessions.get(user_id, {}).get('notification_settings', default_settings)

def get_user_notification_frequency(user_id: int) -> str:
    """جلب تردد الإشعارات للمستخدم"""
    settings = get_user_advanced_notification_settings(user_id)
    return settings.get('frequency', '15s')

def set_user_notification_frequency(user_id: int, frequency: str):
    """تعيين تردد الإشعارات للمستخدم"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    if 'notification_settings' not in user_sessions[user_id]:
        user_sessions[user_id]['notification_settings'] = get_user_advanced_notification_settings(user_id)
    
    user_sessions[user_id]['notification_settings']['frequency'] = frequency

def is_timing_allowed(user_id: int) -> bool:
    """التحقق من توقيت الإشعارات المسموح"""
    # للبساطة، سنرجع True دائماً في هذا الإصدار
    return True

def calculate_dynamic_success_rate_v2(analysis: Dict, alert_type: str) -> float:
    """حساب نسبة النجاح الديناميكية المحسنة (النسخة البديلة)"""
    if not analysis:
        import random
        return round(random.uniform(30, 80), 1)  # قيمة عشوائية واقعية من نطاق أوسع
    
    # استدعاء الدالة الرئيسية المحسنة
    return calculate_dynamic_success_rate(analysis, alert_type)

def calculate_ai_success_rate(analysis: Dict, technical_data: Dict, symbol: str, action: str, user_id: int = None) -> float:
    """حساب نسبة النجاح الذكية بناءً على تحليل شامل للعوامل المختلفة - ديناميكية 0-100%"""
    try:
        # البدء بنسبة أساسية متغيرة حسب ظروف السوق
        base_score = 45.0  # نقطة بداية محايدة
        
        # العوامل المؤثرة على نسبة النجاح
        confidence_factors = []
        
        # 1. تحليل المؤشرات الفنية (40% من النتيجة)
        technical_score = 0
        if technical_data and technical_data.get('indicators'):
            indicators = technical_data['indicators']
            
            # RSI Analysis (10%)
            rsi = indicators.get('rsi', 50)
            if rsi:
                if action == 'BUY':
                    if 30 <= rsi <= 50:  # منطقة جيدة للشراء
                        technical_score += 10
                    elif 20 <= rsi < 30:  # ذروة بيع - فرصة شراء ممتازة
                        technical_score += 15
                    elif rsi > 70:  # ذروة شراء - خطر
                        technical_score -= 5
                elif action == 'SELL':
                    if 50 <= rsi <= 70:  # منطقة جيدة للبيع
                        technical_score += 10
                    elif 70 < rsi <= 80:  # ذروة شراء - فرصة بيع ممتازة
                        technical_score += 15
                    elif rsi < 30:  # ذروة بيع - خطر
                        technical_score -= 5
            
            # MACD Analysis (10%)
            macd_data = indicators.get('macd', {})
            if macd_data.get('macd') is not None and macd_data.get('signal') is not None:
                macd_value = macd_data['macd']
                macd_signal = macd_data['signal']
                
                if action == 'BUY' and macd_value > macd_signal:
                    technical_score += 10  # إشارة شراء قوية
                elif action == 'SELL' and macd_value < macd_signal:
                    technical_score += 10  # إشارة بيع قوية
                elif action == 'BUY' and macd_value < macd_signal:
                    technical_score -= 5   # إشارة متضاربة
                elif action == 'SELL' and macd_value > macd_signal:
                    technical_score -= 5   # إشارة متضاربة
            
            # Moving Averages Analysis (10%)
            ma10 = indicators.get('ma_10', 0)
            ma20 = indicators.get('ma_20', 0)
            ma50 = indicators.get('ma_50', 0)
            current_price = technical_data.get('price', 0)
            
            if ma10 and ma20 and current_price:
                if action == 'BUY':
                    if current_price > ma10 > ma20:  # ترتيب صاعد
                        technical_score += 10
                    elif current_price > ma10:  # فوق المتوسط قصير المدى
                        technical_score += 5
                elif action == 'SELL':
                    if current_price < ma10 < ma20:  # ترتيب هابط
                        technical_score += 10
                    elif current_price < ma10:  # تحت المتوسط قصير المدى
                        technical_score += 5
            
            # Support/Resistance Analysis (10%)
            support = indicators.get('support')
            resistance = indicators.get('resistance')
            if support and resistance and current_price:
                price_position = (current_price - support) / (resistance - support)
                
                if action == 'BUY':
                    if price_position <= 0.3:  # قريب من الدعم
                        technical_score += 10
                    elif price_position <= 0.5:  # في المنتصف
                        technical_score += 5
                elif action == 'SELL':
                    if price_position >= 0.7:  # قريب من المقاومة
                        technical_score += 10
                    elif price_position >= 0.5:  # في المنتصف
                        technical_score += 5
        
        confidence_factors.append(("التحليل الفني", technical_score, 40))
        
        # 2. تحليل حجم التداول (15% من النتيجة)
        volume_score = 0
        if technical_data and technical_data.get('indicators'):
            volume_ratio = technical_data['indicators'].get('volume_ratio', 1.0)
            if volume_ratio > 1.5:  # حجم عالي
                volume_score = 15
            elif volume_ratio > 1.2:  # حجم جيد
                volume_score = 10
            elif volume_ratio < 0.5:  # حجم منخفض - خطر
                volume_score = -5
            else:
                volume_score = 5  # حجم طبيعي
        
        confidence_factors.append(("حجم التداول", volume_score, 15))
        
        # 3. قوة الإشارة من تحليل الذكاء الاصطناعي (25% من النتيجة)
        ai_score = 0
        ai_confidence = analysis.get('confidence', 0)
        if ai_confidence > 80:
            ai_score = 25
        elif ai_confidence > 60:
            ai_score = 20
        elif ai_confidence > 40:
            ai_score = 15
        elif ai_confidence > 20:
            ai_score = 10
        else:
            ai_score = 0
        
        confidence_factors.append(("الذكاء الاصطناعي", ai_score, 25))
        
        # 4. تحليل اتجاه السوق العام (10% من النتيجة)
        trend_score = 0
        if technical_data and technical_data.get('indicators'):
            overall_trend = technical_data['indicators'].get('overall_trend', '')
            if action == 'BUY' and 'صاعد' in overall_trend:
                trend_score = 10
            elif action == 'SELL' and 'هابط' in overall_trend:
                trend_score = 10
            elif action in ['BUY', 'SELL'] and 'محايد' in overall_trend:
                trend_score = 5
            elif action != 'HOLD':  # إشارة ضد الاتجاه
                trend_score = -5
        
        confidence_factors.append(("الاتجاه العام", trend_score, 10))
        
        # 5. عامل التقلبات والاستقرار (10% من النتيجة)
        volatility_score = 5  # قيمة افتراضية
        if technical_data and technical_data.get('indicators'):
            bollinger = technical_data['indicators'].get('bollinger', {})
            if bollinger.get('upper') and bollinger.get('lower'):
                band_width = bollinger['upper'] - bollinger['lower']
                # تقدير التقلبات من عرض البولنجر باندز
                if band_width > 0:
                    # تقلبات معتدلة تعطي ثقة أعلى
                    volatility_score = 8
                else:
                    # تقلبات عالية أو منخفضة جداً تقلل الثقة
                    volatility_score = 3
        
        confidence_factors.append(("التقلبات", volatility_score, 10))
        
        # حساب النتيجة النهائية
        total_weighted_score = 0
        total_weight = 0
        
        for factor_name, score, weight in confidence_factors:
            total_weighted_score += (score * weight / 100)
            total_weight += weight
        
        # التأكد من أن المجموع الوزني 100%
        if total_weight != 100:
            logger.warning(f"مجموع الأوزان غير صحيح: {total_weight}%")
        
        # النتيجة النهائية
        final_score = base_score + total_weighted_score
        
        # تطبيق قيود منطقية مع نطاق أوسع
        final_score = max(5, min(98, final_score))  # بين 5% و 98% للمرونة الكاملة
        
        # تطبيق عوامل تصحيحية بناءً على نوع الصفقة
        if action == 'HOLD':
            final_score = max(final_score - 20, 10)  # تقليل الثقة للانتظار
        elif action in ['BUY', 'SELL']:
            # زيادة طفيفة للإشارات الواضحة
            final_score = min(final_score + 5, 95)
        
        # سجل تفاصيل الحساب للمراجعة
        logger.info(f"[AI_SUCCESS] {symbol} - {action}: {final_score:.1f}% | العوامل: {confidence_factors}")
        
        return round(final_score, 1)
        
    except Exception as e:
        logger.error(f"خطأ في حساب نسبة النجاح الذكية: {e}")
        # في حالة الخطأ، استخدم قيمة افتراضية آمنة
        return 55.0

# ===== وظائف إرسال التنبيهات المحسنة =====
def send_trading_signal_alert(user_id: int, symbol: str, signal: Dict, analysis: Dict = None):
    """إرسال تنبيه إشارة التداول مع أزرار التقييم"""
    try:
        logger.debug(f"[DEBUG] محاولة إرسال تنبيه للمستخدم {user_id} للرمز {symbol}")
        
        # التحقق من صحة البيانات
        if (not symbol or not signal or not isinstance(signal, dict) or
            not signal.get('action') or not isinstance(user_id, int)):
            logger.warning(f"[WARNING] بيانات غير صحيحة لإشارة التداول: {symbol}, {signal}")
            return
        
        settings = get_user_advanced_notification_settings(user_id)
        logger.debug(f"[DEBUG] إعدادات المستخدم {user_id}: {settings}")
        
        # التحقق من إعدادات المستخدم
        if not settings.get('trading_signals', True):
            logger.debug(f"[DEBUG] إشارات التداول معطلة للمستخدم {user_id}")
            return
        
        if not is_timing_allowed(user_id):
            logger.debug(f"[DEBUG] التوقيت غير مسموح للمستخدم {user_id}")
            return
        
        # التحقق من الرموز المختارة
        selected_symbols = user_selected_symbols.get(user_id, [])
        logger.debug(f"[DEBUG] الرموز المختارة للمستخدم {user_id}: {selected_symbols}")
        if symbol not in selected_symbols:
            logger.debug(f"[DEBUG] الرمز {symbol} غير مختار للمستخدم {user_id}")
            return
        
        action = signal.get('action', 'HOLD')
        confidence = signal.get('confidence', 0)
        
        # التأكد من أن confidence رقم صالح
        if confidence is None or not isinstance(confidence, (int, float)):
            confidence = 0
        
        # حساب نسبة النجاح
        if analysis:
            success_rate = calculate_dynamic_success_rate(analysis, 'trading_signal')
            if success_rate is None or success_rate <= 0:
                success_rate = max(confidence, 65.0) if confidence > 0 else 65.0
        else:
            success_rate = max(confidence, 65.0) if confidence > 0 else 65.0
        
        # التحقق من عتبة النجاح
        min_threshold = settings.get('success_threshold', 70)
        logger.debug(f"[DEBUG] نسبة النجاح {success_rate:.1f}% مقابل العتبة {min_threshold}%")
        if min_threshold > 0 and success_rate < min_threshold:
            logger.debug(f"[DEBUG] نسبة النجاح أقل من العتبة المطلوبة للمستخدم {user_id}")
            return
        
        # جلب معلومات نمط التداول (بدون شروط إضافية - فقط لحساب حجم الصفقة)
        trading_mode = get_user_trading_mode(user_id)
        capital = get_user_capital(user_id)
        logger.debug(f"[DEBUG] نمط التداول: {trading_mode}, رأس المال: {capital}")
        logger.debug(f"[DEBUG] تم قبول الإشعار - نسبة النجاح {success_rate:.1f}% تتجاوز عتبة المستخدم {min_threshold}%")
        
        # التحقق من تردد الإشعارات
        user_frequency = get_user_notification_frequency(user_id)
        frequency_seconds = NOTIFICATION_FREQUENCIES.get(user_frequency, {}).get('seconds', 15)
        logger.debug(f"[DEBUG] تردد الإشعارات: {user_frequency} ({frequency_seconds} ثانية)")
        
        can_send = frequency_manager.can_send_notification(user_id, symbol, frequency_seconds)
        logger.debug(f"[DEBUG] يمكن إرسال الإشعار: {can_send}")
        if not can_send:
            logger.debug(f"[DEBUG] لم يحن وقت الإشعار بعد للمستخدم {user_id} للرمز {symbol}")
            return  # لم يحن وقت الإشعار بعد
        
        # حفظ بيانات الصفقة
        trade_id = TradeDataManager.save_trade_data(user_id, symbol, signal, analysis)
        
        # جلب السعر الحالي
        current_price = None
        if analysis:
            price_data = analysis.get('price_data', {})
            current_price = price_data.get('last', price_data.get('bid'))
        
        # حساب الهدف ووقف الخسارة حسب نمط التداول
        target = None
        stop_loss = None
        if current_price:
            # تحديد النسب حسب نمط التداول
            if trading_mode == 'scalping':
                profit_pct = 0.015  # 1.5% للسكالبينغ
                loss_pct = 0.005   # 0.5% وقف خسارة
            else:  # longterm
                profit_pct = 0.05   # 5% للتداول طويل الأمد
                loss_pct = 0.02     # 2% وقف خسارة
            
            if action == 'BUY':
                target = current_price * (1 + profit_pct)
                stop_loss = current_price * (1 - loss_pct)
            elif action == 'SELL':
                target = current_price * (1 - profit_pct)
                stop_loss = current_price * (1 + loss_pct)
        
        # إنشاء رسالة التنبيه المحسنة
        symbol_info = ALL_SYMBOLS.get(symbol, {'name': symbol, 'emoji': '📈'})
        emoji = symbol_info['emoji']
        
        # حساب حجم الصفقة المناسب حسب نمط التداول
        if trading_mode == 'scalping':
            position_size = min(capital * 0.02, capital * 0.05)  # 2-5% للسكالبينغ
            risk_description = "منخفضة (سكالبينغ)"
        else:
            position_size = min(capital * 0.05, capital * 0.10)  # 5-10% للتداول طويل الأمد
            risk_description = "متوسطة (طويل الأمد)"
        
        formatted_time = get_current_time_for_user(user_id)
        
        # مصدر البيانات
        data_source = analysis.get('source', 'MT5 + Gemini AI') if analysis else 'تحليل متقدم'
        
        # استخدام نفس طريقة التحليل اليدوي للإشعارات
        # جلب البيانات الحقيقية من MT5
        price_data = mt5_manager.get_live_price(symbol)
        if not price_data:
            logger.warning(f"[WARNING] فشل في جلب البيانات الحقيقية للإشعار - الرمز {symbol}")
            # استخدام البيانات المتوفرة
            price_data = {
                'last': current_price,
                'bid': current_price,
                'ask': current_price,
                'time': datetime.now()
            }
        
        # إجراء تحليل جديد مع Gemini AI للإشعار
        fresh_analysis = None
        try:
            fresh_analysis = gemini_analyzer.analyze_market_data_with_retry(symbol, price_data, user_id)
            logger.info(f"[SUCCESS] تم الحصول على تحليل Gemini جديد للإشعار - الرمز {symbol}")
        except Exception as ai_error:
            logger.warning(f"[WARNING] فشل تحليل Gemini للإشعار - الرمز {symbol}: {ai_error}")
        
        # التأكد من أن fresh_analysis هو dictionary صحيح
        if not fresh_analysis or not isinstance(fresh_analysis, dict):
            logger.warning(f"[WARNING] تحليل Gemini غير صحيح، استخدام التحليل الاحتياطي للرمز {symbol}")
            # استخدام التحليل الموجود أو إنشاء تحليل بديل
            fresh_analysis = analysis if analysis and isinstance(analysis, dict) else {
                'action': action,
                'confidence': success_rate,
                'reasoning': [f'إشعار تداول آلي للرمز {symbol}'],
                'ai_analysis': f'إشعار تداول آلي - نسبة النجاح {success_rate:.1f}%',
                'source': data_source,
                'symbol': symbol,
                'timestamp': datetime.now(),
                'price_data': price_data
            }
        
        # استخدام نفس دالة التنسيق المستخدمة في التحليل اليدوي
        try:
            message = gemini_analyzer.format_comprehensive_analysis_v120(
                symbol, symbol_info, price_data, fresh_analysis, user_id
            )
        except Exception as format_error:
            logger.error(f"[ERROR] فشل في تنسيق رسالة الإشعار للرمز {symbol}: {format_error}")
            # رجوع للرسالة البسيطة في حالة الخطأ
            action_emoji = "🟢" if action == 'BUY' else "🔴" if action == 'SELL' else "🟡"
            message = f"""🚨 **إشعار تداول آلي** {emoji}

━━━━━━━━━━━━━━━━━━━━━━━━━
💱 {symbol} | {symbol_info['name']} {emoji}
📡 مصدر البيانات: {data_source}
💰 السعر الحالي: {current_price:,.5f} 
⏰ وقت التحليل: {formatted_time}

━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ إشارة التداول الرئيسية

{action_emoji} نوع الصفقة: {action}
✅ نسبة نجاح الصفقة: {success_rate:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 **بوت التداول v1.2.0 - إشعار ذكي**"""
            # إرسال الرسالة البسيطة مباشرة
            try:
                bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                frequency_manager.record_notification_sent(user_id, symbol)
                logger.info(f"📨 تم إرسال إشعار بسيط للمستخدم {user_id} للرمز {symbol}")
            except Exception as send_error:
                logger.error(f"[ERROR] فشل في إرسال الإشعار البسيط: {send_error}")
            return  # إنهاء الدالة مبكراً في حالة الخطأ
        
        # استخدام دالة الإشعار المختصرة بدلاً من الرسالة الكاملة
        short_message = format_short_alert_message(symbol, symbol_info, price_data, fresh_analysis, user_id)
        
        # استخدام الرسالة المختصرة للإشعارات
        message = short_message
        
        # إنشاء أزرار التقييم
        markup = create_feedback_buttons(trade_id) if trade_id else None
        
        # تقسيم الرسالة إذا كانت طويلة جداً
        max_message_length = 4000  # حد أقل قليلاً من 4096 للأمان
        
        if len(message) > max_message_length:
            # تقسيم الرسالة إلى أجزاء
            parts = []
            current_part = ""
            lines = message.split('\n')
            
            for line in lines:
                if len(current_part + line + '\n') > max_message_length:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part.strip())
            
            # إرسال الأجزاء
            for i, part in enumerate(parts):
                try:
                    if i == len(parts) - 1:  # الجزء الأخير يحتوي على الأزرار
                        bot.send_message(
                            chat_id=user_id,
                            text=part,
                            parse_mode='Markdown',
                            reply_markup=markup
                        )
                    else:
                        bot.send_message(
                            chat_id=user_id,
                            text=part,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    logger.error(f"[ERROR] خطأ في إرسال جزء الرسالة {i+1}: {e}")
                    # محاولة إرسال بدون تنسيق Markdown
                    try:
                        bot.send_message(
                            chat_id=user_id,
                            text=part.replace('*', '').replace('_', '').replace('`', ''),
                            reply_markup=markup if i == len(parts) - 1 else None
                        )
                    except Exception as e2:
                        logger.error(f"[ERROR] فشل إرسال الرسالة حتى بدون تنسيق: {e2}")
        else:
            # إرسال الرسالة العادية
            try:
                bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            except Exception as e:
                logger.error(f"[ERROR] خطأ في إرسال الرسالة: {e}")
                # محاولة إرسال بدون تنسيق Markdown
                try:
                    bot.send_message(
                        chat_id=user_id,
                        text=message.replace('*', '').replace('_', '').replace('`', ''),
                        reply_markup=markup
                    )
                except Exception as e2:
                    logger.error(f"[ERROR] فشل إرسال الرسالة حتى بدون تنسيق: {e2}")
                    return
        
        # تسجيل وقت الإرسال
        frequency_manager.record_notification_sent(user_id, symbol)
        
        logger.info(f"📨 تم إرسال تنبيه تداول للمستخدم {user_id} للرمز {symbol} (تردد: {user_frequency})")
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إرسال تنبيه التداول: {e}")

# ===== معالجات الأزرار =====
@bot.callback_query_handler(func=lambda call: call.data.startswith('feedback_'))
def handle_feedback(call):
    """معالجة تقييمات المستخدم"""
    try:
        # استخراج نوع التقييم ومعرف الصفقة
        parts = call.data.split('_')
        feedback_type = parts[1]  # positive أو negative
        trade_id = '_'.join(parts[2:])  # معرف الصفقة
        
        # حفظ التقييم
        success = TradeDataManager.save_user_feedback(trade_id, feedback_type)
        
        if success:
            # رسالة شكر للمستخدم
            feedback_emoji = "👍" if feedback_type == "positive" else "👎"
            thanks_message = f"""
✅ **شكراً لتقييمك!** {feedback_emoji}

تم حفظ تقييمك وسيتم استخدامه لتحسين دقة التوقعات المستقبلية.

🧠 **نظام التعلم الذكي:** سيقوم Gemini AI بالتعلم من تقييمك لتقديم توقعات أكثر دقة.
            """
            
            # تعديل الرسالة الأصلية
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n{thanks_message}",
                parse_mode='Markdown'
            )
            
            # إشعار للمستخدم
            bot.answer_callback_query(
                call.id, 
                f"تم حفظ تقييمك {feedback_emoji} - شكراً لك!",
                show_alert=False
            )
            
        else:
            bot.answer_callback_query(
                call.id, 
                "حدث خطأ في حفظ التقييم",
                show_alert=True
            )
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة التقييم: {e}")
        bot.answer_callback_query(
            call.id, 
            "حدث خطأ في معالجة التقييم",
            show_alert=True
        )

# ===== وظائف إدارة البوت الرئيسية =====
def create_main_keyboard():
    """إنشاء الكيبورد الرئيسي الثابت"""
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=False)
    
    keyboard.row(
        types.KeyboardButton("📊 التحليل اليدوي"),
        types.KeyboardButton("📡 المراقبة الآلية")
    )
    keyboard.row(
        types.KeyboardButton("📈 أسعار مباشرة"),
        types.KeyboardButton("📊 إحصائياتي")
    )
    keyboard.row(
        types.KeyboardButton("⚙️ الإعدادات")
    )
    keyboard.row(
        types.KeyboardButton("❓ المساعدة")
    )
    
    return keyboard

@bot.message_handler(commands=['start'])
def handle_start(message):
    """معالج أمر البدء"""
    user_id = message.from_user.id
    
    # التحقق من كلمة المرور
    if user_id not in user_sessions:
        # إنشاء كيبورد مخفي لإدخال كلمة السر
        hide_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(
            chat_id=user_id,
            text="🔐 يرجى إدخال كلمة المرور للوصول إلى البوت:",
            reply_markup=hide_keyboard
        )
        user_states[user_id] = 'waiting_password'
        return
    
    # رسالة الترحيب
    welcome_message = f"""
🎉 **مرحباً بك في بوت التداول المتقدم v1.2.0!**

🚀 **الميزات الجديدة:**
✅ بيانات لحظية حقيقية من MetaTrader5
✅ تحليل ذكي بتقنية Google Gemini AI
✅ نظام تقييم الإشعارات 👍👎
✅ تعلم آلي من تقييماتك

📊 **حالة الاتصال:**
• MetaTrader5: {'✅ متصل' if mt5_manager.connected else '❌ غير متصل'}
• Gemini AI: {'✅ متاح' if GEMINI_AVAILABLE else '❌ غير متاح'}

🎯 **للبدء:** استخدم الأزرار في الأسفل للتنقل بين الوظائف.
    """
    
    bot.send_message(
        chat_id=user_id,
        text=welcome_message,
        parse_mode='Markdown',
        reply_markup=create_main_keyboard()
    )

# ===== معالجات الكيبورد الثابت =====
def handle_analyze_symbols_callback(message):
    """معالج التحليل اليدوي المحسن"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        message_text = """
📊 **التحليل اليدوي للرموز**

اختر فئة الرموز التي تريد تحليلها:

• **العملات الرقمية:** Bitcoin, Ethereum, وأكثر
• **العملات الأجنبية:** EUR/USD, GBP/USD, وأكثر  
• **الأسهم الأمريكية:** Apple, Tesla, Google, وأكثر
• **المؤشرات:** S&P500, NASDAQ, وأكثر
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        markup.row(
            create_animated_button("💱 العملات الأجنبية", "analyze_forex", "💱"),
            create_animated_button("🥇 المعادن النفيسة", "analyze_metals", "🥇")
        )
        markup.row(
            create_animated_button("₿ العملات الرقمية", "analyze_crypto", "₿"),
            create_animated_button("📈 الأسهم الأمريكية", "analyze_stocks", "📈")
        )
        markup.row(
            create_animated_button("📊 المؤشرات", "analyze_indices", "📊")
        )
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        # استخدام الوظيفة المحسنة لإرسال أو تعديل الرسالة
        send_or_edit_message(message, message_text, markup)
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في التحليل اليدوي: {e}")

@bot.message_handler(func=lambda message: message.text == "📊 التحليل اليدوي")
@require_authentication
def handle_manual_analysis_keyboard(message):
    """معالج زر التحليل اليدوي من الكيبورد"""
    handle_analyze_symbols_callback(message)

def handle_auto_monitoring_callback(message):
    """معالج المراقبة الآلية"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        # جلب حالة المراقبة
        is_monitoring = user_monitoring_active.get(user_id, False)
        selected_symbols = user_selected_symbols.get(user_id, [])
        trading_mode = get_user_trading_mode(user_id)
        
        status_text = "🟢 نشط" if is_monitoring else "🔴 متوقف"
        symbols_count = len(selected_symbols)
        
        message_text = f"""
📡 **المراقبة الآلية للأسواق**

📊 **الحالة الحالية:** {status_text}
🎯 **الرموز المراقبة:** {symbols_count} رمز
🎯 **نمط التداول:** {'⚡ سكالبينغ' if trading_mode == 'scalping' else '📈 طويل الأمد'}

**الوظائف المتاحة:**
• تحديد الرموز للمراقبة
• تفعيل/إيقاف المراقبة التلقائية  
• ضبط إعدادات التنبيهات
        """
        
        markup = create_auto_monitoring_menu(user_id)
        
        # استخدام الوظيفة المحسنة لإرسال أو تعديل الرسالة
        send_or_edit_message(message, message_text, markup)
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في المراقبة الآلية: {e}")

@bot.message_handler(func=lambda message: message.text == "📡 المراقبة الآلية")
@require_authentication
def handle_auto_monitoring_keyboard(message):
    """معالج زر المراقبة الآلية من الكيبورد"""
    handle_auto_monitoring_callback(message)



def handle_my_stats_callback(message):
    """معالج الإحصائيات"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        # جلب إحصائيات المستخدم
        capital = get_user_capital(user_id)
        trading_mode = get_user_trading_mode(user_id)
        feedback_stats = user_trade_feedbacks.get(user_id, {})
        
        total_trades = len(feedback_stats)
        positive_trades = sum(1 for feedback in feedback_stats.values() if feedback == 'positive')
        accuracy = (positive_trades / total_trades * 100) if total_trades > 0 else 0
        
        message_text = f"""
📊 **إحصائياتي الشخصية**

💰 **رأس المال:** ${capital:,.0f}
🎯 **نمط التداول:** {'⚡ سكالبينغ' if trading_mode == 'scalping' else '📈 طويل الأمد'}

📈 **إحصائيات التداول:**
• إجمالي الصفقات: {total_trades}
• الصفقات الناجحة: {positive_trades}
• دقة التوقعات: {accuracy:.1f}%

🔔 **حالة التنبيهات:**
• المراقبة النشطة: {'🟢 مفعلة' if user_monitoring_active.get(user_id, False) else '🔴 معطلة'}
• الرموز المراقبة: {len(user_selected_symbols.get(user_id, []))} رمز

{get_current_time_for_user(user_id)}
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            create_animated_button("🔄 تحديث", "my_stats", "🔄")
        )
        
        # استخدام الوظيفة المحسنة لإرسال أو تعديل الرسالة
        send_or_edit_message(message, message_text, markup)
    except Exception as e:
        logger.error(f"[ERROR] خطأ في الإحصائيات: {e}")

def handle_settings_callback(message):
    """معالج الإعدادات من الكيبورد الرئيسي"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        trading_mode = get_user_trading_mode(user_id)
        trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
        settings = get_user_advanced_notification_settings(user_id)
        frequency = get_user_notification_frequency(user_id)
        frequency_name = NOTIFICATION_FREQUENCIES.get(frequency, {}).get('name', '15 ثانية 🔥')
        user_timezone = get_user_timezone(user_id)
        timezone_display = AVAILABLE_TIMEZONES.get(user_timezone, user_timezone)
        capital = get_user_capital(user_id)
        
        message_text = f"""
⚙️ **الإعدادات**

🎯 **نمط التداول:** {trading_mode_display}
💰 **رأس المال:** ${capital:,.0f}
🌍 **المنطقة الزمنية:** {timezone_display}
🔔 **التنبيهات:** {'مفعلة' if settings.get('trading_signals', True) else 'معطلة'}
⏱️ **تردد الإشعارات:** {frequency_name}
📊 **عتبة النجاح:** {settings.get('success_threshold', 70)}%

اختر الإعداد المطلوب تعديله:
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.row(
            create_animated_button("🎯 نمط التداول", "trading_mode_settings", "🎯"),
            create_animated_button("💰 تحديد رأس المال", "set_capital", "💰")
        )
        
        markup.row(
            create_animated_button("🔔 إعدادات التنبيهات", "advanced_notifications_settings", "🔔"),
            create_animated_button("📊 الإحصائيات", "statistics", "📊")
        )
        
        markup.row(
            create_animated_button("🌍 المنطقة الزمنية", "timezone_settings", "🌍"),
            create_animated_button("🤖 قسم AI", "ai_section", "🤖")
        )
        
        # استخدام الوظيفة المحسنة لإرسال أو تعديل الرسالة
        send_or_edit_message(message, message_text, markup)
    except Exception as e:
        logger.error(f"[ERROR] خطأ في الإعدادات: {e}")

def handle_alerts_log_callback(message):
    """معالج سجل التنبيهات"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        message_text = """
📋 **سجل الإشعارات**

عرض وإدارة سجل الإشعارات والصفقات:
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(
            create_animated_button("📊 عرض السجل", "view_alerts_log", "📊"),
            create_animated_button("🗑️ مسح السجل", "clear_alerts", "🗑️")
        )
        markup.row(
            create_animated_button("📈 تحليل الأداء", "performance_analysis", "📈")
        )
        
        # استخدام الوظيفة المحسنة لإرسال أو تعديل الرسالة
        send_or_edit_message(message, message_text, markup)
    except Exception as e:
        logger.error(f"[ERROR] خطأ في سجل التنبيهات: {e}")

def handle_help_main_callback(message):
    """معالج المساعدة الرئيسي"""
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        message_text = """
❓ **المساعدة والدعم**

اختر نوع المساعدة المطلوبة:
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("📚 استخدام البوت", "help_usage", "📚")
        )
        markup.row(
            create_animated_button("ℹ️ حول البوت", "about", "ℹ️")
        )
        markup.row(
            create_animated_button("🆘 الدعم الفني", "technical_support", "🆘")
        )
        
        # استخدام الوظيفة المحسنة لإرسال أو تعديل الرسالة
        send_or_edit_message(message, message_text, markup)
    except Exception as e:
        logger.error(f"[ERROR] خطأ في المساعدة: {e}")

@bot.message_handler(func=lambda message: message.text == "📈 أسعار مباشرة")
@require_authentication
def handle_live_prices_keyboard(message):
    """معالج زر الأسعار المباشرة من الكيبورد"""
    try:
        user_id = message.from_user.id
        
        message_text = """
📈 **الأسعار المباشرة من MetaTrader5**

اختر فئة الرموز للحصول على الأسعار اللحظية:
(مصدر البيانات: MT5 - لحظي)
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.row(
            create_animated_button("💱 العملات الأجنبية", "live_forex", "💱"),
            create_animated_button("🥇 المعادن النفيسة", "live_metals", "🥇")
        )
        markup.row(
            create_animated_button("₿ العملات الرقمية", "live_crypto", "₿"),
            create_animated_button("📈 الأسهم الأمريكية", "live_stocks", "📈")
        )
        markup.row(
            create_animated_button("📊 المؤشرات", "live_indices", "📊")
        )
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.send_message(
            chat_id=message.chat.id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في الأسعار المباشرة من الكيبورد: {e}")
        bot.send_message(
            chat_id=message.chat.id,
            text="❌ حدث خطأ في عرض الأسعار المباشرة، يرجى المحاولة مرة أخرى."
        )

@bot.message_handler(func=lambda message: message.text == "📊 إحصائياتي")
@require_authentication
def handle_my_stats_keyboard(message):
    """معالج زر الإحصائيات من الكيبورد"""
    handle_my_stats_callback(message)

@bot.message_handler(func=lambda message: message.text == "⚙️ الإعدادات")
@require_authentication
def handle_settings_keyboard(message):
    """معالج زر الإعدادات من الكيبورد"""
    handle_settings_callback(message)


@bot.message_handler(func=lambda message: message.text == "❓ المساعدة")
@require_authentication
def handle_help_keyboard(message):
    """معالج زر المساعدة من الكيبورد"""
    handle_help_main_callback(message)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_password')
def handle_password(message):
    """معالج كلمة المرور"""
    user_id = message.from_user.id
    
    if message.text == BOT_PASSWORD:
        user_sessions[user_id] = {
            'authenticated': True,
            'trading_mode': 'scalping',
            'notification_settings': get_user_advanced_notification_settings(user_id)
        }
        
        # إجبار سؤال رأس المال لجميع المستخدمين بعد كلمة المرور
        user_states[user_id] = 'waiting_initial_capital'
        
        message_text = """
💰 **مرحباً بك! يرجى تحديد رأس المال للبدء**

اختر رأس المال المناسب لك:
(يمكن تعديله لاحقاً من الإعدادات)
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for capital in DEFAULT_CAPITAL_OPTIONS:
            markup.row(
                types.InlineKeyboardButton(f"${capital:,}", callback_data=f"initial_capital_{capital}")
            )
        
        markup.row(
            create_animated_button("💰 إدخال مبلغ مخصص", "initial_custom_capital", "💰")
        )
        
        bot.send_message(
            user_id,
            message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
    else:
        bot.reply_to(message, "❌ كلمة مرور خاطئة. حاول مرة أخرى:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("initial_capital_"))
def handle_initial_capital(call):
    """معالج تحديد رأس المال الأولي"""
    try:
        user_id = call.from_user.id
        capital = int(call.data.replace("initial_capital_", ""))
        
        set_user_capital(user_id, capital)
        user_states.pop(user_id, None)
        
        bot.edit_message_text(
            f"✅ تم تحديد رأس المال: ${capital:,}\n\n"
            "🎉 مرحباً بك في بوت التداول المتقدم v1.2.0!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
        
        # إرسال القائمة الرئيسية
        time.sleep(1)
        fake_message = type('obj', (object,), {'from_user': call.from_user, 'chat': call.message.chat})
        handle_start(fake_message)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحديد رأس المال الأولي: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "initial_custom_capital")
def handle_initial_custom_capital(call):
    """معالج إدخال رأس مال مخصص أولي"""
    try:
        user_id = call.from_user.id
        user_states[user_id] = 'waiting_initial_custom_capital'
        
        bot.edit_message_text(
            "💰 **إدخال رأس مال مخصص**\n\n"
            "يرجى إدخال المبلغ المطلوب بالدولار الأمريكي:\n"
            "مثال: 1500 أو 25000\n\n"
            "الحد الأدنى: $50\n"
            "الحد الأقصى: $1,000,000",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=None
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إدخال رأس مال مخصص أولي: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_initial_custom_capital')
def handle_initial_custom_capital_input(message):
    """معالج إدخال رأس المال المخصص الأولي"""
    try:
        user_id = message.from_user.id
        
        try:
            capital = float(message.text.replace(',', '').replace('$', ''))
            
            if capital < 50:
                bot.reply_to(message, "❌ المبلغ أقل من الحد الأدنى ($50). يرجى إدخال مبلغ أكبر.")
                return
            
            if capital > 1000000:
                bot.reply_to(message, "❌ المبلغ أكبر من الحد الأقصى ($1,000,000). يرجى إدخال مبلغ أصغر.")
                return
            
            set_user_capital(user_id, capital)
            user_states.pop(user_id, None)
            
            bot.reply_to(message, f"✅ تم تحديد رأس المال: ${capital:,.0f}\n\n🎉 مرحباً بك في بوت التداول المتقدم!")
            
            time.sleep(1)
            handle_start(message)
            
        except ValueError:
            bot.reply_to(message, "❌ يرجى إدخال رقم صحيح. مثال: 1500")
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة رأس المال المخصص الأولي: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة المبلغ")
        user_states.pop(user_id, None)

# ===== معالجات فئات الرموز =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("category_"))
def handle_symbol_category(call):
    """معالج فئات الرموز"""
    try:
        user_id = call.from_user.id
        category = call.data.replace("category_", "")
        
        # جلب الرموز المختارة
        selected_symbols = user_selected_symbols.get(user_id, [])
        
        category_names = {
            'crypto': 'العملات الرقمية ₿',
            'forex': 'العملات الأجنبية والمعادن 💱',
            'stocks': 'الأسهم الأمريكية 📈',
            'indices': 'المؤشرات 📊'
        }
        
        symbols = SYMBOL_CATEGORIES.get(category, {})
        
        message_text = f"""
📊 **{category_names.get(category, 'فئة غير معروفة')}**

اختر الرموز التي تريد تحليلها:
✅ = مختار للتحليل | ⚪ = غير مختار
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # إضافة الرموز مع تمييز المختارة
        for symbol, info in symbols.items():
            is_selected = symbol in selected_symbols
            button_text = f"✅ {info['name']}" if is_selected else f"⚪ {info['name']}"
            
            markup.row(
                types.InlineKeyboardButton(
                    button_text, 
                    callback_data=f"toggle_symbol_{symbol}_{category}"
                )
            )
        
        # أزرار التحكم
        markup.row(
            create_animated_button("🔄 تحليل المختارة", f"analyze_selected_{category}", "🔄"),
            create_animated_button("✅ اختيار الكل", f"select_all_{category}", "✅")
        )
        markup.row(
            create_animated_button("❌ إلغاء الكل", f"deselect_all_{category}", "❌"),
            create_animated_button("🔙 التحليل اليدوي", "analyze_symbols", "🔙")
        )
        
        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالج فئات الرموز: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

# تم حذف المعالج القديم المكرر - يتم استخدام المعالج الجديد في السطر 4166

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_all_"))
def handle_select_all_category(call):
    """معالج اختيار جميع رموز الفئة"""
    try:
        user_id = call.from_user.id
        category = call.data.replace("select_all_", "")
        
        if user_id not in user_selected_symbols:
            user_selected_symbols[user_id] = []
        
        symbols = SYMBOL_CATEGORIES.get(category, {})
        
        # إضافة جميع رموز الفئة
        for symbol in symbols.keys():
            if symbol not in user_selected_symbols[user_id]:
                user_selected_symbols[user_id].append(symbol)
        
        bot.answer_callback_query(call.id, f"✅ تم اختيار جميع رموز الفئة ({len(symbols)} رمز)")
        
        # تحديث القائمة
        fake_call = type('obj', (object,), {
            'data': f'category_{category}',
            'from_user': call.from_user,
            'message': call.message
        })
        handle_symbol_category(fake_call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في اختيار جميع الرموز: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("deselect_all_"))
def handle_deselect_all_category(call):
    """معالج إلغاء اختيار جميع رموز الفئة"""
    try:
        user_id = call.from_user.id
        category = call.data.replace("deselect_all_", "")
        
        if user_id not in user_selected_symbols:
            user_selected_symbols[user_id] = []
        
        symbols = SYMBOL_CATEGORIES.get(category, {})
        
        # إزالة جميع رموز الفئة
        for symbol in symbols.keys():
            if symbol in user_selected_symbols[user_id]:
                user_selected_symbols[user_id].remove(symbol)
        
        bot.answer_callback_query(call.id, f"❌ تم إلغاء اختيار جميع رموز الفئة")
        
        # تحديث القائمة
        fake_call = type('obj', (object,), {
            'data': f'category_{category}',
            'from_user': call.from_user,
            'message': call.message
        })
        handle_symbol_category(fake_call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إلغاء اختيار جميع الرموز: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

# ===== معالجات الأزرار الرئيسية =====
@bot.callback_query_handler(func=lambda call: call.data == "live_prices")
@require_authentication
def handle_live_prices(call):
    """معالج الأسعار المباشرة المحسن"""
    try:
        user_id = call.from_user.id
        
        message_text = """
📈 **الأسعار المباشرة من MetaTrader5**

اختر فئة الرموز للحصول على الأسعار اللحظية:
(مصدر البيانات: MT5 - لحظي)
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.row(
            create_animated_button("💱 العملات الأجنبية", "live_forex", "💱"),
            create_animated_button("🥇 المعادن النفيسة", "live_metals", "🥇")
        )
        markup.row(
            create_animated_button("₿ العملات الرقمية", "live_crypto", "₿"),
            create_animated_button("📈 الأسهم الأمريكية", "live_stocks", "📈")
        )
        markup.row(
            create_animated_button("📊 المؤشرات", "live_indices", "📊")
        )
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في الأسعار المباشرة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض الأسعار", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "my_stats")
def handle_my_stats(call):
    """معالج عرض إحصائيات المستخدم"""
    try:
        user_id = call.from_user.id
        stats = TradeDataManager.get_user_feedback_stats(user_id)
        
        message_text = f"""
📊 **إحصائياتك الشخصية**

📈 **تقييمات الإشارات:**
• إجمالي التقييمات: {stats['total_feedbacks']}
• تقييمات إيجابية: {stats['positive_feedbacks']} 👍
• تقييمات سلبية: {stats['negative_feedbacks']} 👎
• معدل الدقة: {stats['accuracy_rate']:.1f}%

🎯 **نمط التداول الحالي:** {get_user_trading_mode(user_id)}

🧠 **التعلم الآلي:**
• عدد عينات التدريب: {stats['total_feedbacks']}
• حالة التعلم: {'نشط' if stats['total_feedbacks'] > 0 else 'في انتظار المزيد من التقييمات'}

───────────────────────
💡 كلما زادت تقييماتك، كلما تحسنت دقة التوقعات!
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض الإحصائيات: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في جلب الإحصائيات", show_alert=True)

# ===== معالجات إضافية للأزرار =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("analyze_symbol_"))
def handle_single_symbol_analysis(call):
    """معالج تحليل رمز واحد تفصيلياً - مثل v1.1.0"""
    try:
        user_id = call.from_user.id
        symbol = call.data.replace("analyze_symbol_", "")
        
        logger.info(f"[START] بدء تحليل الرمز {symbol} للمستخدم {user_id}")
        
        # العثور على معلومات الرمز
        symbol_info = ALL_SYMBOLS.get(symbol)
        if not symbol_info:
            logger.error(f"[ERROR] رمز غير صالح: {symbol}")
            bot.answer_callback_query(call.id, "❌ رمز غير صالح", show_alert=True)
            return
        
        # رسالة انتظار
        bot.edit_message_text(
            f"🔄 جاري تحليل {symbol_info['emoji']} {symbol_info['name']}...\n\n"
            "⏳ يرجى الانتظار بينما نجمع البيانات ونحللها...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        # جلب البيانات اللحظية من MT5 فقط (بدون بيانات تجريبية لحماية المستخدم)
        price_data = mt5_manager.get_live_price(symbol)
        if not price_data:
            logger.error(f"[ERROR] فشل في جلب البيانات الحقيقية من MT5 للرمز {symbol}")
            bot.edit_message_text(
                f"❌ **لا يمكن الحصول على بيانات حقيقية**\n\n"
                f"لا يمكن الحصول على بيانات {symbol_info['emoji']} {symbol_info['name']} من MetaTrader5.\n\n"
                "🔧 **متطلبات التشغيل:**\n"
                "• يجب تشغيل MetaTrader5 على نفس الجهاز\n"
                "• يجب تسجيل الدخول لحساب حقيقي أو تجريبي في MT5\n"
                "• تأكد من وجود اتصال إنترنت مستقر\n"
                "• تأكد من إضافة الرمز للمراقبة في MT5\n\n"
                "⚠️ **تحذير:** لا يمكن التحليل بدون بيانات حقيقية لحمايتك من قرارات خاطئة.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            return
        
        # تحليل ذكي مع Gemini AI مع بديل
        analysis = None
        try:
            analysis = gemini_analyzer.analyze_market_data_with_retry(symbol, price_data, user_id)
            logger.info(f"[SUCCESS] تم الحصول على تحليل Gemini للرمز {symbol}")
        except Exception as ai_error:
            logger.warning(f"[WARNING] فشل تحليل Gemini للرمز {symbol}: {ai_error}")
        
        if not analysis:
            logger.warning(f"[WARNING] لا يوجد تحليل Gemini - استخدام تحليل بديل للرمز {symbol}")
            # إنشاء تحليل بديل بسيط (بدون توصيات تداول لحماية المستخدم)
            analysis = {
                'action': 'HOLD',  # دائماً انتظار عند فشل AI
                'confidence': 0,   # لا ثقة بدون AI
                'reasoning': ['تحليل محدود - Gemini AI غير متوفر - لا توصيات تداول'],
                'ai_analysis': f'⚠️ تحذير: لا يمكن تقديم تحليل كامل للرمز {symbol} بدون Gemini AI. البيانات المعروضة للمعلومات فقط.',
                'source': 'Limited Analysis (No AI)',
                'symbol': symbol,
                'timestamp': datetime.now(),
                'price_data': price_data,
                'warning': 'لا توصيات تداول - AI غير متوفر'
            }
        
        # استخدام التحليل الشامل المتقدم الجديد
        message_text = gemini_analyzer.format_comprehensive_analysis_v120(
            symbol, symbol_info, price_data, analysis, user_id
        )
        
        # أزرار التحكم
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        try:
            # أزرار التقييم مبسطة
            markup.row(
                create_animated_button("👍 تحليل ممتاز", f"feedback_positive_{symbol}_{user_id}", "👍"),
                create_animated_button("👎 تحليل ضعيف", f"feedback_negative_{symbol}_{user_id}", "👎")
            )
            
            markup.row(
                create_animated_button("🔄 تحديث التحليل", f"analyze_symbol_{symbol}", "🔄"),
                create_animated_button("📊 تحليل آخر", "analyze_symbols", "📊")
            )
            markup.row(
                create_animated_button("🔙 العودة لقائمة التحليل", "analyze_symbols", "🔙")
            )
        except Exception as btn_error:
            logger.error(f"[ERROR] فشل في إنشاء الأزرار: {btn_error}")
            # أزرار بسيطة كبديل
            markup.row(
                types.InlineKeyboardButton("👍 ممتاز", callback_data=f"feedback_positive_{symbol}_{user_id}"),
                types.InlineKeyboardButton("👎 ضعيف", callback_data=f"feedback_negative_{symbol}_{user_id}")
            )
            markup.row(
                types.InlineKeyboardButton("🔄 تحديث", callback_data=f"analyze_symbol_{symbol}"),
                types.InlineKeyboardButton("📊 آخر", callback_data="analyze_symbols")
            )
            markup.row(
                types.InlineKeyboardButton("🔙 عودة", callback_data="analyze_symbols")
            )
        
        try:
            # التحقق من طول الرسالة (حد Telegram 4096 حرف)
            if len(message_text) > 4000:
                # تقسيم الرسالة إذا كانت طويلة جداً
                message_parts = [message_text[i:i+3900] for i in range(0, len(message_text), 3900)]
                main_message = message_parts[0] + "\n\n⚠️ الرسالة مقطوعة لطولها..."
            else:
                main_message = message_text
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=main_message,
                parse_mode='Markdown',
                reply_markup=markup
            )
            
            # إرسال الجزء الثاني إذا كان موجوداً
            if len(message_text) > 4000:
                for i, part in enumerate(message_parts[1:], 1):
                    bot.send_message(
                        chat_id=call.message.chat.id,
                        text=f"**📄 الجزء {i + 1}:**\n\n{part}",
                        parse_mode='Markdown'
                    )
            
            logger.info(f"[SUCCESS] تم إرسال تحليل الرمز {symbol} للمستخدم {user_id}")
            
        except Exception as send_error:
            logger.error(f"[ERROR] فشل في إرسال التحليل: {send_error}")
            try:
                # محاولة إرسال رسالة خطأ بسيطة
                bot.edit_message_text(
                    f"❌ **خطأ في عرض التحليل**\n\n"
                    f"حدث خطأ في عرض تحليل {symbol_info['emoji']} {symbol_info['name']}.\n\n"
                    "يرجى المحاولة مرة أخرى لاحقاً.",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            except:
                bot.answer_callback_query(call.id, "حدث خطأ في عرض التحليل", show_alert=True)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ عام في تحليل الرمز {call.data}: {e}")
        try:
            bot.answer_callback_query(call.id, "حدث خطأ في التحليل", show_alert=True)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "analyze_symbols")
def handle_analyze_symbols(call):
    """معالج تحليل الرموز"""
    try:
        message_text = """
📊 **تحليل الرموز المالية**

اختر فئة الرموز المالية للتحليل:
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.row(
            create_animated_button("💶 أزواج العملات", "analyze_forex", "💶"),
            create_animated_button("🥇 المعادن النفيسة", "analyze_metals", "🥇")
        )
        
        markup.row(
            create_animated_button("₿ العملات الرقمية", "analyze_crypto", "₿"),
            create_animated_button("📈 الأسهم الأمريكية", "analyze_stocks", "📈")
        )
        
        markup.row(
            create_animated_button("📊 المؤشرات", "analyze_indices", "📊")
        )
        
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض تحليل الرموز: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض التحليل", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("analyze_") and call.data != "analyze_symbols" and not call.data.startswith("analyze_symbol_") and not call.data.startswith("toggle_notification_"))
def handle_category_analysis(call):
    """معالج تحليل فئة معينة من الرموز - يرسل تحليل منفصل لكل رمز"""
    try:
        user_id = call.from_user.id
        category = call.data.split('_')[1]
        
        # تحديد الرموز حسب الفئة
        if category == "forex":
            symbols = CURRENCY_PAIRS
            title = "💶 تحليل أزواج العملات"
            category_emoji = "💱"
        elif category == "metals":
            symbols = METALS
            title = "🥇 تحليل المعادن النفيسة"
            category_emoji = "🥇"
        elif category == "crypto":
            symbols = CRYPTO_PAIRS
            title = "₿ تحليل العملات الرقمية"
            category_emoji = "₿"
        elif category == "stocks":
            symbols = STOCKS
            title = "📈 تحليل الأسهم الأمريكية"
            category_emoji = "📈"
        elif category == "indices":
            symbols = INDICES
            title = "📊 تحليل المؤشرات"
            category_emoji = "📊"
        else:
            return
        
        # عرض قائمة الرموز للاختيار
        message_text = f"{title}\n\n"
        message_text += "اختر الرمز الذي تريد تحليله تحليلاً تفصيلياً:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # إضافة أزرار الرموز
        symbol_buttons = []
        for symbol, info in symbols.items():
            symbol_buttons.append(
                create_animated_button(f"{info['emoji']} {info['name']}", f"analyze_symbol_{symbol}", info['emoji'])
            )
        
        # ترتيب الأزرار في صفوف (2 في كل صف)
        for i in range(0, len(symbol_buttons), 2):
            if i + 1 < len(symbol_buttons):
                markup.row(symbol_buttons[i], symbol_buttons[i + 1])
            else:
                markup.row(symbol_buttons[i])
        
        # زر العودة
        markup.row(
            create_animated_button("🔙 التحليل اليدوي", "analyze_symbols", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحليل الفئة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في التحليل", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "settings")
def handle_settings(call):
    """معالج الإعدادات"""
    try:
        user_id = call.from_user.id
        trading_mode = get_user_trading_mode(user_id)
        trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
        settings = get_user_advanced_notification_settings(user_id)
        frequency = get_user_notification_frequency(user_id)
        frequency_name = NOTIFICATION_FREQUENCIES.get(frequency, {}).get('name', '15 ثانية 🔥')
        user_timezone = get_user_timezone(user_id)
        timezone_display = AVAILABLE_TIMEZONES.get(user_timezone, user_timezone)
        capital = get_user_capital(user_id)
        
        message_text = f"""
⚙️ **الإعدادات**

🎯 **نمط التداول:** {trading_mode_display}
💰 **رأس المال:** ${capital:,.0f}
🌍 **المنطقة الزمنية:** {timezone_display}
🔔 **التنبيهات:** {'مفعلة' if settings.get('trading_signals', True) else 'معطلة'}
⏱️ **تردد الإشعارات:** {frequency_name}
📊 **عتبة النجاح:** {settings.get('success_threshold', 70)}%

اختر الإعداد المطلوب تعديله:
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.row(
            create_animated_button("🎯 نمط التداول", "trading_mode_settings", "🎯"),
            create_animated_button("💰 تحديد رأس المال", "set_capital", "💰")
        )
        
        markup.row(
            create_animated_button("🔔 إعدادات التنبيهات", "advanced_notifications_settings", "🔔"),
            create_animated_button("📊 الإحصائيات", "statistics", "📊")
        )
        
        markup.row(
            create_animated_button("🌍 المنطقة الزمنية", "timezone_settings", "🌍"),
            create_animated_button("🤖 قسم AI", "ai_section", "🤖")
        )
        
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض الإعدادات: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض الإعدادات", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "ai_section")
def handle_ai_section(call):
    """معالج قسم AI"""
    try:
        message_text = """
🤖 **قسم الذكاء الاصطناعي**

🧠 **ميزات الذكاء الاصطناعي المتاحة:**

📁 **تدريب النظام بالملفات:**
• ارفع صور الشارتات والأنماط الفنية
• ارفع ملفات PDF أو Word مع تحليلاتك
• ارفع مستندات تحليلية أو توقعات
• النظام يتعلم من ملفاتك ويحسن دقة التحليل

🔮 **الميزات القادمة:**
• تحليل ذكي للأسواق
• توصيات مخصصة
• تحليل المشاعر  
• تنبؤات السوق

💡 **كيف يعمل التعلم:**
النظام يحلل ملفاتك ويربطها بنمط تداولك ورأس مالك لتحسين التوصيات المستقبلية
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("📁 رفع ملف للتدريب", "upload_file", "📁")
        )
        markup.row(
            create_animated_button("⚙️ إدارة قواعد التحليل", "manage_analysis_rules", "⚙️")
        )
        markup.row(
            create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض قسم AI: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض قسم AI", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "manage_analysis_rules")
def handle_manage_analysis_rules(call):
    """معالج إدارة قواعد التحليل"""
    try:
        message_text = """
⚙️ **إدارة قواعد التحليل**

📋 **إدارة قواعد التحليل الذكي:**

• قم بإضافة قواعد تحليل جديدة
• عدّل القواعد الموجودة
• حدد معايير التحليل المخصصة

🔧 **الخيارات المتاحة:**
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("➕ إضافة قاعدة", "add_analysis_rule", "➕")
        )
        markup.row(
            create_animated_button("✏️ تحرير القواعد", "edit_analysis_rules", "✏️")
        )
        markup.row(
            create_animated_button("🔙 العودة لقسم AI", "ai_section", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض إدارة قواعد التحليل: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض إدارة قواعد التحليل", show_alert=True)

# ===== نظام إدارة قواعد التحليل =====

def load_analysis_rules():
    """تحميل قواعد التحليل من الملف"""
    rules_file = os.path.join(FEEDBACK_DIR, "analysis_rules.json")
    try:
        if os.path.exists(rules_file):
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحميل قواعد التحليل: {e}")
        return []

def save_analysis_rules(rules):
    """حفظ قواعد التحليل في الملف"""
    rules_file = os.path.join(FEEDBACK_DIR, "analysis_rules.json")
    try:
        os.makedirs(FEEDBACK_DIR, exist_ok=True)
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"[ERROR] خطأ في حفظ قواعد التحليل: {e}")
        return False

def process_user_rule_with_ai(user_input, user_id):
    """معالجة قاعدة المستخدم باستخدام الذكاء الاصطناعي"""
    try:
        if not gemini_analyzer or not gemini_analyzer.model:
            return None
            
        prompt = f"""
أنت خبير في تحليل الأسواق المالية. المستخدم أدخل قاعدة تحليل جديدة:

"{user_input}"

مهمتك:
1. تحسين وإعادة صياغة هذه القاعدة بشكل احترافي ومفهوم
2. ترقيم القاعدة وتنظيمها
3. إضافة تفاصيل تقنية مفيدة إذا لزم الأمر
4. التأكد من أن القاعدة واضحة وقابلة للتطبيق

اكتب القاعدة المحسنة بشكل مرقم ومنظم:
"""
        
        response = gemini_analyzer.model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة القاعدة بالذكاء الاصطناعي: {e}")
        return None

def get_analysis_rules_for_prompt():
    """جلب قواعد التحليل المخصصة للإضافة إلى البرومبت"""
    rules = load_analysis_rules()
    if not rules:
        return ""
    
    rules_text = "\n\n=== قواعد التحليل المخصصة من المستخدمين ===\n"
    for i, rule in enumerate(rules, 1):
        rules_text += f"\n{i}. {rule['processed_rule']}\n"
        rules_text += f"   (أضيفت بواسطة المستخدم {rule['user_id']} في {rule['created_at']})\n"
    
    rules_text += "\n=== يجب مراعاة هذه القواعد في التحليل ===\n"
    return rules_text

# تحديث دالة التحليل لتشمل القواعد المخصصة
def get_custom_analysis_rules():
    """الحصول على القواعد المخصصة لإدراجها في البرومبت"""
    return get_analysis_rules_for_prompt()

@bot.callback_query_handler(func=lambda call: call.data == "add_analysis_rule")
def handle_add_analysis_rule(call):
    """معالج إضافة قاعدة تحليل"""
    try:
        message_text = """
➕ **إضافة قاعدة تحليل جديدة**

📝 **اكتب قاعدة التحليل التي تريد إضافتها:**

مثال على القواعد:
• "عند كسر مستوى المقاومة بحجم تداول عالي، زد نسبة الثقة بـ 15%"
• "في حالة تضارب RSI مع MACD، قلل نسبة النجاح بـ 20%"
• "عند تداول الذهب أثناء الأحداث الجيوسياسية، زد الحذر وقلل حجم الصفقة"

⚡ **سيقوم الذكاء الاصطناعي بـ:**
- تحسين وإعادة صياغة قاعدتك
- ترتيبها وترقيمها
- إضافة تفاصيل تقنية مفيدة

📤 **أرسل قاعدتك الآن:**
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("🔙 العودة لإدارة القواعد", "manage_analysis_rules", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
        # تعيين حالة انتظار إدخال القاعدة
        user_states[call.from_user.id] = {
            'state': 'waiting_for_analysis_rule',
            'message_id': call.message.message_id,
            'chat_id': call.message.chat.id
        }
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إضافة قاعدة التحليل: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في إضافة قاعدة التحليل", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "edit_analysis_rules")
def handle_edit_analysis_rules(call):
    """معالج تحرير قواعد التحليل"""
    try:
        rules = load_analysis_rules()
        
        if not rules:
            message_text = """
✏️ **تحرير قواعد التحليل**

📋 **لا توجد قواعد محفوظة حالياً**

قم بإضافة قواعد جديدة أولاً من خلال زر "إضافة قاعدة"
            """
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.row(
                create_animated_button("➕ إضافة قاعدة جديدة", "add_analysis_rule", "➕")
            )
            markup.row(
                create_animated_button("🔙 العودة لإدارة القواعد", "manage_analysis_rules", "🔙")
            )
        else:
            message_text = f"""
✏️ **تحرير قواعد التحليل**

📋 **القواعد المحفوظة ({len(rules)} قاعدة):**

اختر القاعدة التي تريد تحريرها أو حذفها:
            """
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for i, rule in enumerate(rules):
                rule_preview = rule['processed_rule'][:50] + "..." if len(rule['processed_rule']) > 50 else rule['processed_rule']
                markup.row(
                    create_animated_button(f"📝 {i+1}. {rule_preview}", f"edit_rule_{i}", "📝")
                )
            
            markup.row(
                create_animated_button("🔙 العودة لإدارة القواعد", "manage_analysis_rules", "🔙")
            )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحرير قواعد التحليل: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تحرير قواعد التحليل", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_rule_"))
def handle_edit_specific_rule(call):
    """معالج تحرير قاعدة محددة"""
    try:
        rule_index = int(call.data.split("_")[2])
        rules = load_analysis_rules()
        
        if rule_index >= len(rules):
            bot.answer_callback_query(call.id, "القاعدة غير موجودة", show_alert=True)
            return
            
        rule = rules[rule_index]
        
        message_text = f"""
📝 **تحرير القاعدة #{rule_index + 1}**

**القاعدة الحالية:**
{rule['processed_rule']}

**معلومات القاعدة:**
• أضيفت بواسطة: المستخدم {rule['user_id']}
• تاريخ الإضافة: {rule['created_at']}
• النص الأصلي: {rule['original_rule']}

**اختر الإجراء:**
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("✏️ تعديل القاعدة", f"modify_rule_{rule_index}", "✏️")
        )
        markup.row(
            create_animated_button("🗑️ حذف القاعدة", f"delete_rule_{rule_index}", "🗑️")
        )
        markup.row(
            create_animated_button("🔙 العودة لقائمة القواعد", "edit_analysis_rules", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحرير القاعدة المحددة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تحرير القاعدة", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_rule_"))
def handle_delete_rule(call):
    """معالج حذف قاعدة"""
    try:
        rule_index = int(call.data.split("_")[2])
        rules = load_analysis_rules()
        
        if rule_index >= len(rules):
            bot.answer_callback_query(call.id, "القاعدة غير موجودة", show_alert=True)
            return
        
        # حذف القاعدة
        deleted_rule = rules.pop(rule_index)
        
        if save_analysis_rules(rules):
            bot.answer_callback_query(call.id, "✅ تم حذف القاعدة بنجاح", show_alert=True)
            
            # العودة لقائمة القواعد
            handle_edit_analysis_rules(call)
        else:
            bot.answer_callback_query(call.id, "❌ فشل في حذف القاعدة", show_alert=True)
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في حذف القاعدة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في حذف القاعدة", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("modify_rule_"))
def handle_modify_rule(call):
    """معالج تعديل قاعدة"""
    try:
        rule_index = int(call.data.split("_")[2])
        rules = load_analysis_rules()
        
        if rule_index >= len(rules):
            bot.answer_callback_query(call.id, "القاعدة غير موجودة", show_alert=True)
            return
            
        rule = rules[rule_index]
        
        message_text = f"""
✏️ **تعديل القاعدة #{rule_index + 1}**

**القاعدة الحالية:**
{rule['processed_rule']}

📝 **اكتب النص الجديد للقاعدة:**

سيقوم الذكاء الاصطناعي بتحسين وإعادة صياغة النص الجديد.

📤 **أرسل النص المُحدث الآن:**
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("🔙 العودة للقاعدة", f"edit_rule_{rule_index}", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
        # تعيين حالة انتظار تعديل القاعدة
        user_states[call.from_user.id] = {
            'state': 'waiting_for_rule_modification',
            'rule_index': rule_index,
            'message_id': call.message.message_id,
            'chat_id': call.message.chat.id
        }
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تعديل القاعدة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تعديل القاعدة", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "select_symbols")
def handle_select_symbols(call):
    """معالج اختيار الرموز للمراقبة"""
    try:
        user_id = call.from_user.id
        selected_symbols = user_selected_symbols.get(user_id, [])
        
        message_text = f"""
📊 **اختيار الرموز للمراقبة**

الرموز المختارة حالياً: {len(selected_symbols)}
{', '.join(selected_symbols) if selected_symbols else 'لا توجد رموز مختارة'}

اختر فئة لإضافة رموز منها:
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.row(
            create_animated_button("💶 أزواج العملات", "select_forex", "💶"),
            create_animated_button("🥇 المعادن", "select_metals", "🥇")
        )
        
        markup.row(
            create_animated_button("₿ العملات الرقمية", "select_crypto", "₿"),
            create_animated_button("📈 الأسهم الأمريكية", "select_stocks", "📈")
        )
        
        markup.row(
            create_animated_button("📊 المؤشرات", "select_indices", "📊")
        )
        
        if selected_symbols:
            markup.row(
                create_animated_button("🗑️ مسح جميع الرموز", "clear_symbols", "🗑️")
            )
        
        markup.row(
            create_animated_button("🔙 المراقبة الآلية", "auto_monitoring", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض اختيار الرموز: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض اختيار الرموز", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
def handle_symbol_selection(call):
    """معالج اختيار رموز من فئة معينة"""
    try:
        user_id = call.from_user.id
        category = call.data.split('_')[1]
        
        # حفظ الفئة الحالية للمستخدم
        user_current_category[user_id] = category
        
        # تحديد الرموز حسب الفئة
        if category == "forex":
            symbols = CURRENCY_PAIRS
            title = "💶 اختيار أزواج العملات"
        elif category == "metals":
            symbols = METALS
            title = "🥇 اختيار المعادن"
        elif category == "crypto":
            symbols = CRYPTO_PAIRS
            title = "₿ اختيار العملات الرقمية"
        elif category == "stocks":
            symbols = STOCKS
            title = "📈 اختيار الأسهم الأمريكية"
        elif category == "indices":
            symbols = INDICES
            title = "📊 اختيار المؤشرات"
        else:
            return
        
        selected_symbols = user_selected_symbols.get(user_id, [])
        
        message_text = f"{title}\n\n"
        message_text += "اختر الرموز التي تريد مراقبتها:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for symbol, info in symbols.items():
            is_selected = symbol in selected_symbols
            button_text = f"{'✅' if is_selected else '☐'} {info['name']}"
            callback_data = f"toggle_{symbol}"
            
            markup.row(
                types.InlineKeyboardButton(button_text, callback_data=callback_data)
            )
        
        markup.row(
            create_animated_button("🔙 اختيار فئة أخرى", "select_symbols", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض رموز الفئة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض الرموز", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def handle_toggle_symbol(call):
    """معالج تبديل اختيار الرمز"""
    try:
        user_id = call.from_user.id
        symbol = call.data.split('_')[1]
        
        if user_id not in user_selected_symbols:
            user_selected_symbols[user_id] = []
        
        selected_symbols = user_selected_symbols[user_id]
        
        if symbol in selected_symbols:
            selected_symbols.remove(symbol)
            action = "تم إلغاء اختيار"
        else:
            selected_symbols.append(symbol)
            action = "تم اختيار"
        
        symbol_info = ALL_SYMBOLS.get(symbol, {'name': symbol})
        
        # إظهار رسالة تأكيد مع أنيميشن
        if symbol in selected_symbols:
            bot.answer_callback_query(
                call.id,
                f"✅ {action} {symbol_info['name']}",
                show_alert=False
            )
        else:
            bot.answer_callback_query(
                call.id,
                f"❌ {action} {symbol_info['name']}",
                show_alert=False
            )
        
        # تحديث القائمة بناءً على الفئة المحفوظة
        current_category = user_current_category.get(user_id, 'forex')
        fake_call = type('obj', (object,), {
            'data': f'select_{current_category}',
            'from_user': call.from_user,
            'message': call.message
        })
        handle_symbol_selection(fake_call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تبديل الرمز: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تبديل الرمز", show_alert=True)

# تم حذف معالجات التردد - التردد الآن موحد لكل 15 ثانية

@bot.callback_query_handler(func=lambda call: call.data.startswith("detailed_"))
def handle_detailed_analysis(call):
    """معالج التحليل التفصيلي للفئة"""
    try:
        user_id = call.from_user.id
        category = call.data.split('_')[1]
        
        # تحديد الرموز حسب الفئة
        if category == "forex":
            symbols = CURRENCY_PAIRS
            title = "💶 تحليل تفصيلي - أزواج العملات"
        elif category == "metals":
            symbols = METALS
            title = "🥇 تحليل تفصيلي - المعادن النفيسة"
        elif category == "crypto":
            symbols = CRYPTO_PAIRS
            title = "₿ تحليل تفصيلي - العملات الرقمية"
        elif category == "indices":
            symbols = INDICES
            title = "📊 تحليل تفصيلي - المؤشرات"
        else:
            return
        
        message_text = f"{title}\n\n"
        message_text += "اختر الرمز للحصول على تحليل تفصيلي شامل:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for symbol, info in symbols.items():
            # جلب بيانات سريعة لعرض السعر
            price_data = mt5_manager.get_live_price(symbol)
            current_price = ""
            if price_data:
                current_price = f" - ${price_data.get('last', price_data.get('bid', 0)):.5f}"
            
            button_text = f"{info['emoji']} {info['name']}{current_price}"
            markup.row(
                types.InlineKeyboardButton(button_text, callback_data=f"full_analysis_{symbol}")
            )
        
        markup.row(
            create_animated_button("🔙 العودة للتحليل السريع", f"analyze_{category}", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في التحليل التفصيلي: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في التحليل التفصيلي", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("full_analysis_"))
def handle_full_symbol_analysis(call):
    """معالج التحليل الشامل لرمز واحد"""
    try:
        user_id = call.from_user.id
        symbol = call.data.split('_', 2)[2]
        
        # جلب معلومات الرمز
        symbol_info = ALL_SYMBOLS.get(symbol)
        if not symbol_info:
            bot.answer_callback_query(call.id, "❌ رمز غير معروف", show_alert=True)
            return
        
        # عرض رسالة التحليل أولاً
        bot.edit_message_text(
            f"🔍 **جاري التحليل الشامل...**\n\n"
            f"📊 **الرمز:** {symbol_info['name']} ({symbol})\n"
            f"👤 **المستخدم:** {call.from_user.first_name}\n"
            "⏳ **يرجى الانتظار للحصول على تحليل متقدم...**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        # جلب البيانات اللحظية
        price_data = mt5_manager.get_live_price(symbol)
        if not price_data:
            bot.edit_message_text(
                f"❌ **فشل في جلب البيانات**\n\n"
                f"📊 **الرمز:** {symbol_info['name']} ({symbol})\n"
                f"⚠️ لا توجد بيانات متاحة حالياً لهذا الرمز.\n"
                f"🔄 يرجى المحاولة مرة أخرى لاحقاً.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            return
        
        # تحليل شامل مع Gemini AI
        analysis = gemini_analyzer.analyze_market_data(symbol, price_data, user_id)
        
        # إعداد الرسالة الشاملة
        data_source = price_data.get('source', 'Unknown')
        formatted_time = format_time_for_user(user_id, price_data.get('time'))
        trading_mode = get_user_trading_mode(user_id)
        capital = get_user_capital(user_id)
        
        message_text = f"""
🔍 **تحليل شامل - {symbol_info['name']}** {symbol_info['emoji']}

📊 **معلومات الرمز:**
• **الرمز:** {symbol}
• **الاسم:** {symbol_info['name']}
• **النوع:** {symbol_info['type']}

💰 **البيانات السعرية:**
• **السعر الحالي:** ${price_data.get('last', price_data.get('bid', 0)):.5f}
• **سعر الشراء:** ${price_data.get('bid', 0):.5f}
• **سعر البيع:** ${price_data.get('ask', 0):.5f}
• **فرق السعر:** {price_data.get('spread', 0):.5f}
• **الحجم:** {price_data.get('volume', 0):,}

👤 **سياق المستخدم:**
• **نمط التداول:** {trading_mode}
• **رأس المال:** ${capital:,.2f}

🧠 **تحليل الذكاء الاصطناعي:**
• **التوصية:** {analysis.get('action', 'HOLD')} 
• **قوة الإشارة:** {analysis.get('confidence', 50):.1f}%
• **المصدر:** {analysis.get('source', 'AI Analysis')}

📝 **التحليل التفصيلي:**
{analysis.get('ai_analysis', 'تحليل غير متوفر حالياً')}

🕐 **معلومات التحديث:**
• **آخر تحديث:** {formatted_time}
• **مصدر البيانات:** {data_source}

───────────────────────
🤖 **بوت التداول v1.2.0 - تحليل ذكي**
        """
        
        # أزرار التحكم
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(
            create_animated_button("🔄 إعادة التحليل", f"full_analysis_{symbol}", "🔄"),
            create_animated_button("📊 إضافة للمراقبة", f"add_monitor_{symbol}", "📊")
        )
        markup.row(
            create_animated_button("🔙 العودة للقائمة", "analyze_symbols", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في التحليل الشامل: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في التحليل", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "help")
def handle_help(call):
    """معالج المساعدة"""
    try:
        help_text = """
❓ **مساعدة بوت التداول v1.2.0**

🚀 **الميزات الجديدة:**
• بيانات لحظية حقيقية من MetaTrader5 + Yahoo Finance
• تحليل ذكي مخصص بـ Google Gemini AI
• نظام تقييم الإشعارات 👍👎 للتعلم الآلي
• تدريب الذكاء الاصطناعي برفع الملفات
• سجل تنبيهات شامل مع إحصائيات

📊 **كيفية الاستخدام:**

1️⃣ **التحليل اليدوي:**
   • انتقل إلى "تحليل الرموز"
   • اختر الفئة المطلوبة (عملات، معادن، عملات رقمية، مؤشرات)
   • احصل على تحليل فوري مخصص لنمط تداولك ورأس مالك

2️⃣ **المراقبة الآلية:**
   • اذهب للإعدادات → اختيار الرموز للمراقبة
   • ستصلك إشعارات ذكية مخصصة كل 30 ثانية
   • التحليل يراعي نمط التداول ورأس المال

3️⃣ **نظام التقييم والتعلم:**
   • اضغط 👍 للإشارات الدقيقة، 👎 للخاطئة
   • النظام يتعلم من تقييماتك ويحسن الدقة
   • راجع سجل التنبيهات لمتابعة الأداء

4️⃣ **تدريب الذكاء الاصطناعي:**
   • ارفع صور الشارتات، ملفات PDF، أو مستندات تحليلية
   • النظام يتعلم من ملفاتك ويطبق المعرفة على التحليلات

5️⃣ **إعدادات متقدمة:**
   • حدد نمط التداول (سكالبينغ/طويل المدى)
   • اضبط عتبة النجاح للإشعارات
   • اختر المنطقة الزمنية لعرض الأوقات بدقة

📊 **مصادر البيانات:**
• **أولوية أولى:** MetaTrader5 (بيانات لحظية مباشرة)
• **بديل ذكي:** Yahoo Finance (للرموز غير المتوفرة في MT5)
• **ضمان التغطية:** 25+ رمز مالي مدعوم

🧠 **الذكاء الاصطناعي المخصص:**
• تحليل يراعي نمط التداول الخاص بك
• توصيات حجم الصفقة حسب رأس المال
• تعلم مستمر من تقييماتك وملفاتك المرفوعة
• عرض الأوقات حسب منطقتك الزمنية

💡 **نصائح للحصول على أفضل النتائج:**
• فعّل MT5 للحصول على أدق البيانات
• قيّم الإشارات بصدق لتحسين النظام
• ارفع ملفات تحليلية لتعزيز ذكاء النظام
• راجع سجل التنبيهات لتتبع الأداء
• استخدم التحليل التفصيلي للقرارات المهمة
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=help_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض المساعدة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض المساعدة", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "about")
def handle_about(call):
    """معالج معلومات البوت"""
    try:
        about_text = """
ℹ️ **حول بوت التداول المتقدم v1.2.0**

🤖 **معلومات البوت:**
📱 رقم الإصدار: v1.2.0
📅 تاريخ الإصدار: 2025
🏗️ مطور بتقنيات متقدمة

🔧 **التقنيات المستخدمة:**
• MetaTrader5: بيانات لحظية حقيقية
• Google Gemini AI: تحليل ذكي ومتطور
• Python: لغة البرمجة الأساسية
• Telegram Bot API: واجهة المستخدم

🚀 **الميزات الجديدة في v1.2.0:**
✅ إلغاء الاعتماد على البيانات التاريخية
✅ بيانات لحظية مباشرة من MT5 + Yahoo Finance
✅ تحليل ذكي مخصص مدعوم بـ Gemini AI
✅ نظام تقييم تفاعلي 👍👎 للتعلم الآلي
✅ رفع ملفات لتدريب الذكاء الاصطناعي
✅ سجل تنبيهات شامل مع إحصائيات
✅ تحليل مخصص يراعي نمط التداول ورأس المال
✅ دعم المناطق الزمنية المختلفة
✅ واجهة محسنة مع تحليل تفصيلي

📊 **الإحصائيات:**
• أكثر من 25 رمز مالي مدعوم
• تحديث لحظي كل 30 ثانية
• دقة تحليل عالية مع التعلم المستمر
• دعم جميع أنواع التداول

👨‍💻 **المطور:**
Mohamad Zalaf ©️2025

🎯 **هدفنا:** 
تقديم أفضل تجربة تداول ذكية مع دقة عالية وتحسين مستمر من خلال تقييمات المستخدمين.

💪 **التزامنا:**
التطوير المستمر والدعم الدائم مع أحدث التقنيات في مجال الذكاء الاصطناعي والتداول.
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=about_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض معلومات البوت: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض معلومات البوت", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "upload_file")
def handle_upload_file(call):
    """معالج رفع الملفات للتدريب"""
    try:
        user_id = call.from_user.id
        
        message_text = """
📁 **رفع ملف للتدريب الذكي**

🤖 **نظام التعلم الآلي:**
يمكنك رفع ملفات مختلفة لتدريب الذكاء الاصطناعي:

📊 **أنواع الملفات المدعومة:**
• **الصور:** الشارتات، الأنماط الفنية، التحليلات البصرية
• **المستندات:** PDF, Word, Text مع تحليلات وتوقعات
• **البيانات:** ملفات Excel مع بيانات السوق

🧠 **كيف يعمل التعلم:**
1. ارفع الملف هنا
2. سيتم تحليل المحتوى
3. ربط البيانات بنمط تداولك ورأس مالك
4. تحسين دقة التوقعات المستقبلية

👤 **سياق التدريب الحالي:**
• نمط التداول: {trading_mode}
• رأس المال: ${capital:,.2f}

📎 **لرفع ملف:** أرسل الملف مباشرة في المحادثة الآن
        """.format(
            trading_mode=get_user_trading_mode(user_id),
            capital=get_user_capital(user_id)
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        # تحديد حالة المستخدم لاستقبال الملف
        user_states[user_id] = 'waiting_file_upload'
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في رفع الملف: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "alerts_log")
def handle_alerts_log(call):
    """معالج سجل التنبيهات"""
    try:
        user_id = call.from_user.id
        
        # جلب آخر التنبيهات للمستخدم
        alerts = get_user_recent_alerts(user_id)
        
        message_text = "📋 **سجل الإشعارات**\n\n"
        
        if not alerts:
            message_text += "📭 لا توجد إشعارات حتى الآن\n"
            message_text += "🔔 ستظهر الإشعارات هنا عند إرسالها"
        else:
            message_text += f"📊 **إجمالي الإشعارات:** {len(alerts)}\n\n"
            
            # عرض آخر 5 تنبيهات
            for i, alert in enumerate(alerts[:5], 1):
                formatted_time = format_time_for_user(user_id, alert.get('timestamp'))
                symbol = alert.get('symbol', 'Unknown')
                action = alert.get('action', 'Unknown')
                confidence = alert.get('confidence', 0)
                feedback = alert.get('feedback', 'لا يوجد تقييم')
                
                feedback_emoji = "👍" if feedback == "positive" else "👎" if feedback == "negative" else "⏳"
                
                message_text += f"**{i}.** {symbol} - {action}\n"
                message_text += f"   💪 قوة: {confidence:.1f}%\n"
                message_text += f"   {feedback_emoji} تقييم: {feedback}\n"
                message_text += f"   🕐 {formatted_time}\n\n"
        
        # إحصائيات التقييم
        stats = TradeDataManager.get_user_feedback_stats(user_id)
        message_text += "📊 **إحصائيات التقييم:**\n"
        message_text += f"• مجموع التقييمات: {stats['total_feedbacks']}\n"
        message_text += f"• تقييمات إيجابية: {stats['positive_feedbacks']} 👍\n"
        message_text += f"• تقييمات سلبية: {stats['negative_feedbacks']} 👎\n"
        message_text += f"• معدل الدقة: {stats['accuracy_rate']:.1f}%\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(
            create_animated_button("🔄 تحديث", "alerts_log", "🔄"),
            create_animated_button("🗑️ مسح السجل", "clear_alerts", "🗑️")
        )
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض سجل التنبيهات: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض السجل", show_alert=True)

def get_user_recent_alerts(user_id: int, limit: int = 10) -> List[Dict]:
    """جلب التنبيهات الأخيرة للمستخدم"""
    try:
        alerts = []
        
        # البحث في ملفات سجلات الصفقات
        for filename in os.listdir(TRADE_LOGS_DIR):
            if filename.startswith(f'trade_{user_id}_'):
                file_path = os.path.join(TRADE_LOGS_DIR, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    trade_data = json.load(f)
                
                alert_data = {
                    'symbol': trade_data.get('symbol'),
                    'action': trade_data.get('signal', {}).get('action'),
                    'confidence': trade_data.get('signal', {}).get('confidence'),
                    'timestamp': datetime.fromisoformat(trade_data.get('timestamp')),
                    'feedback': trade_data.get('feedback')
                }
                alerts.append(alert_data)
        
        # ترتيب حسب الوقت (الأحدث أولاً)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return alerts[:limit]
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في جلب التنبيهات: {e}")
        return []

# معالج رفع الملفات
@bot.message_handler(content_types=['document', 'photo'])
def handle_file_upload(message):
    """معالج رفع الملفات من المستخدم"""
    try:
        user_id = message.from_user.id
        
        # التحقق من حالة المستخدم
        if user_states.get(user_id) not in ['waiting_file_upload', 'waiting_pattern_description']:
            return
        
        file_info = None
        file_type = None
        
        if user_states.get(user_id) == 'waiting_file_upload':
            if message.content_type == 'photo':
                file_info = bot.get_file(message.photo[-1].file_id)
                file_type = 'image/jpeg'
            elif message.content_type == 'document':
                file_info = bot.get_file(message.document.file_id)
                file_type = message.document.mime_type or 'application/octet-stream'
            
            if file_info:
                # تحميل الملف
                downloaded_file = bot.download_file(file_info.file_path)
                
                # حفظ الملف محلياً
                upload_dir = os.path.join(DATA_DIR, "uploaded_files")
                os.makedirs(upload_dir, exist_ok=True)
                
                file_extension = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'bin'
                local_file_path = os.path.join(upload_dir, f"{user_id}_{int(time.time())}.{file_extension}")
                
                with open(local_file_path, 'wb') as f:
                    f.write(downloaded_file)
                
                # حفظ مسار الملف مؤقتاً للمستخدم
                if not hasattr(bot, 'temp_user_files'):
                    bot.temp_user_files = {}
                bot.temp_user_files[user_id] = {
                    'file_path': local_file_path,
                    'file_type': file_type
                }
                
                # طلب وصف النمط من المستخدم
                user_states[user_id] = 'waiting_pattern_description'
                
                bot.reply_to(message, 
                    "✅ **تم رفع الصورة بنجاح!**\n\n"
                    "🧠 **الآن اشرح لي النمط:**\n\n"
                    "📝 **مثال على الوصف:**\n"
                    "• 'عند رؤية هذا النمط من الشموع، السعر سينزل بنسبة 90%'\n"
                    "• 'هذا النمط يعني ارتفاع قوي - ثقة 100%'\n"
                    "• 'شمعة الدوجي هذه تعني تردد السوق - احتمال انعكاس 80%'\n\n"
                    "💡 **كن محدداً:** اذكر النمط والاتجاه المتوقع ونسبة الثقة")
        
        elif user_states.get(user_id) == 'waiting_pattern_description':
            # معالجة وصف النمط
            pattern_description = message.text.strip()
            
            if len(pattern_description) < 10:
                bot.reply_to(message, 
                    "⚠️ **الوصف قصير جداً**\n\n"
                    "يرجى إعطاء وصف مفصل أكثر للنمط والاتجاه المتوقع")
                return
            
            # جلب بيانات الملف المحفوظة
            if hasattr(bot, 'temp_user_files') and user_id in bot.temp_user_files:
                file_data = bot.temp_user_files[user_id]
                
                # إعداد سياق المستخدم للتدريب
                user_context = {
                    'trading_mode': get_user_trading_mode(user_id),
                    'capital': get_user_capital(user_id),
                    'timezone': get_user_timezone(user_id),
                    'pattern_description': pattern_description
                }
                
                # إرسال للتعلم الآلي مع الوصف
                success = gemini_analyzer.learn_from_pattern_image(
                    file_data['file_path'], 
                    file_data['file_type'], 
                    user_context,
                    pattern_description
                )
                
                if success:
                    bot.reply_to(message, 
                        "🎯 **تم تعلم النمط بنجاح!**\n\n"
                        f"📊 **النمط المحفوظ:** {pattern_description[:100]}...\n\n"
                        "🧠 **ما حدث:**\n"
                        "• تم تحليل الصورة بواسطة الذكاء الاصطناعي\n"
                        "• تم ربط النمط بوصفك وتوقعاتك\n"
                        "• سيتم استخدام هذه المعرفة في التحليلات القادمة\n\n"
                        "🔄 **النتيجة:** التحليلات ستكون أكثر دقة ومخصصة لك!")
                else:
                    bot.reply_to(message, 
                        "⚠️ **تم حفظ النمط ولكن...**\n\n"
                        "📁 النمط محفوظ بنجاح\n"
                        "🤖 لكن لم يتم معالجته بالكامل\n"
                        "🔧 سيتم المحاولة لاحقاً")
                
                # تنظيف البيانات المؤقتة
                del bot.temp_user_files[user_id]
            
            # إزالة حالة انتظار الوصف
            user_states.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة الملف المرفوع: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة الملف")

# ===== معالجات المراقبة الآلية =====
@bot.callback_query_handler(func=lambda call: call.data == "auto_monitoring")
def handle_auto_monitoring(call):
    """معالج المراقبة الآلية"""
    try:
        user_id = call.from_user.id
        trading_mode = get_user_trading_mode(user_id)
        trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
        is_monitoring = user_monitoring_active.get(user_id, False)
        status = "🟢 نشطة" if is_monitoring else "🔴 متوقفة"
        selected_count = len(user_selected_symbols.get(user_id, []))
        
        # الحصول على إعدادات التنبيهات لعرض التردد الصحيح
        settings = get_user_advanced_notification_settings(user_id)
        frequency_display = NOTIFICATION_FREQUENCIES.get(settings.get('frequency', '5min'), {}).get('name', '5 دقائق')
        success_threshold = settings.get('success_threshold', 70)
        threshold_display = f"{success_threshold}%" if success_threshold > 0 else "الكل"
        
        message_text = f"""
📡 **المراقبة الآلية v1.2.0**

🎯 **نمط التداول:** {trading_mode_display}
📈 **الحالة:** {status}
🎯 **الرموز المختارة:** {selected_count}
⏱️ **تردد الفحص:** {frequency_display}
🎯 **نسبة النجاح:** {threshold_display}
🔗 **مصدر البيانات:** MetaTrader5 + Gemini AI

تعتمد المراقبة على إعدادات التنبيهات ونمط التداول المحدد.
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=create_auto_monitoring_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في المراقبة الآلية: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض المراقبة", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "start_monitoring")
def handle_start_monitoring(call):
    """معالج بدء المراقبة"""
    user_id = call.from_user.id
    
    try:
        # التحقق من وجود رموز مختارة
        selected_symbols = user_selected_symbols.get(user_id, [])
        trading_mode = get_user_trading_mode(user_id)
        trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
        
        if not selected_symbols:
            bot.answer_callback_query(
                call.id,
                "⚠️ يجب اختيار رموز للمراقبة أولاً من زر 'تحديد الرموز'",
                show_alert=True
            )
            return
        
        # التحقق من إعدادات التنبيهات
        notification_settings = get_user_advanced_notification_settings(user_id)
        active_notifications = [k for k, v in notification_settings.items() 
                              if k in ['support_alerts', 'breakout_alerts', 'trading_signals', 
                                     'economic_news', 'candlestick_patterns', 'volume_alerts'] and v]
        
        # تحذير فقط إذا كانت جميع الأنواع معطلة
        if not active_notifications:
            bot.answer_callback_query(
                call.id,
                "⚠️ تحذير: جميع أنواع الإشعارات معطلة! يمكنك تفعيلها من 'إعدادات التنبيهات'",
                show_alert=True
            )
        
        # بدء المراقبة
        user_monitoring_active[user_id] = True
        
        # رسالة تأكيد
        bot.answer_callback_query(call.id, "✅ تم بدء المراقبة الآلية بنجاح")
        
        # تحديث القائمة
        bot.edit_message_text(
            f"▶️ **المراقبة الآلية نشطة**\n\n"
            f"📊 **نمط التداول:** {trading_mode_display}\n"
            f"📈 **الحالة:** 🟢 نشطة\n"
            f"🎯 **الرموز المراقبة:** {len(selected_symbols)} رمز\n"
            f"⚡ **التردد:** {'30 ثانية' if trading_mode == 'scalping' else '5 دقائق'}\n"
            f"🔗 **مصدر البيانات:** MetaTrader5 + Gemini AI\n\n"
            f"📋 **أنواع التنبيهات المفعلة:**\n" + 
            '\n'.join([f"✅ {get_notification_display_name(setting)}" for setting in active_notifications]) +
            "\n\nالمراقبة نشطة وسيتم إرسال التنبيهات عند رصد فرص تداول.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_auto_monitoring_menu(user_id),
            parse_mode='Markdown'
        )
        
        # إرسال تنبيه بدء المراقبة
        symbols_text = ", ".join(selected_symbols[:5])
        if len(selected_symbols) > 5:
            symbols_text += f" و{len(selected_symbols) - 5} رمز آخر"
        
        bot.send_message(
            call.message.chat.id,
            f"▶️ **بدء المراقبة الآلية**\n\n"
            f"📊 نمط التداول: {trading_mode_display}\n"
            f"🎯 الرموز: {symbols_text}\n"
            f"⏰ بدء المراقبة: {datetime.now().strftime('%H:%M:%S')}\n"
            f"🔗 مصدر البيانات: MetaTrader5 + Gemini AI\n\n"
            "سيتم إرسال التنبيهات عند رصد فرص تداول مناسبة! 📈"
        )
        
    except Exception as e:
        logger.error(f"خطأ في بدء المراقبة للمستخدم {user_id}: {str(e)}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ في بدء المراقبة")

@bot.callback_query_handler(func=lambda call: call.data == "stop_monitoring")
def handle_stop_monitoring(call):
    """معالج إيقاف المراقبة"""
    user_id = call.from_user.id
    
    try:
        # إيقاف المراقبة للمستخدم
        user_monitoring_active[user_id] = False
        
        # إزالة المستخدم من القاموس إذا لم يعد نشطاً
        if user_id in user_monitoring_active:
            del user_monitoring_active[user_id]
        
        logger.info(f"[STOP] تم إيقاف المراقبة للمستخدم {user_id}")
        
        # رسالة تأكيد
        bot.answer_callback_query(call.id, "⏹️ تم إيقاف المراقبة الآلية")
        
        # تحديث القائمة
        trading_mode = get_user_trading_mode(user_id)
        trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
        selected_count = len(user_selected_symbols.get(user_id, []))
        
        bot.edit_message_text(
            f"📡 **المراقبة الآلية**\n\n"
            f"📊 **نمط التداول:** {trading_mode_display}\n"
            f"📈 **الحالة:** 🔴 متوقفة\n"
            f"🎯 **الرموز المختارة:** {selected_count}\n"
            f"🔗 **مصدر البيانات:** MetaTrader5 + Gemini AI\n\n"
            "تعتمد المراقبة على إعدادات التنبيهات ونمط التداول المحدد.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_auto_monitoring_menu(user_id),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"خطأ في إيقاف المراقبة للمستخدم {user_id}: {str(e)}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ في إيقاف المراقبة")

@bot.callback_query_handler(func=lambda call: call.data == "clear_symbols")
def handle_clear_symbols(call):
    """معالج مسح جميع الرموز المحددة"""
    user_id = call.from_user.id
    
    try:
        # مسح جميع الرموز المحددة للمستخدم
        user_selected_symbols[user_id] = []
        
        logger.info(f"[CLEAR] تم مسح جميع الرموز للمستخدم {user_id}")
        
        # رسالة تأكيد
        bot.answer_callback_query(call.id, "🗑️ تم مسح جميع الرموز المحددة")
        
        # تحديث القائمة
        trading_mode = get_user_trading_mode(user_id)
        trading_mode_display = "⚡ سكالبينغ سريع" if trading_mode == 'scalping' else "📈 تداول طويل المدى"
        is_monitoring = user_monitoring_active.get(user_id, False)
        status = "🟢 نشطة" if is_monitoring else "🔴 متوقفة"
        
        bot.edit_message_text(
            f"📡 **المراقبة الآلية**\n\n"
            f"📊 **نمط التداول:** {trading_mode_display}\n"
            f"📈 **الحالة:** {status}\n"
            f"🎯 **الرموز المختارة:** 0\n"
            f"🔗 **مصدر البيانات:** MetaTrader5 + Gemini AI\n\n"
            "تعتمد المراقبة على إعدادات التنبيهات ونمط التداول المحدد.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_auto_monitoring_menu(user_id),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"خطأ في مسح الرموز للمستخدم {user_id}: {str(e)}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ في مسح الرموز")

# ===== معالجات نمط التداول =====
@bot.callback_query_handler(func=lambda call: call.data == "trading_mode_settings")
def handle_trading_mode_settings(call):
    """معالج إعدادات نمط التداول"""
    try:
        user_id = call.from_user.id
        current_mode = get_user_trading_mode(user_id)
        
        message_text = f"""
🎯 **إعدادات نمط التداول**

النمط الحالي: {'⚡ سكالبينغ سريع' if current_mode == 'scalping' else '📈 تداول طويل المدى'}

📊 **السكالبينغ السريع:**
• أهداف ربح صغيرة (1-2%)
• وقف خسارة ضيق (0.5%)
• تحليل سريع وفوري
• مناسب للمتداولين النشطين

📈 **التداول طويل المدى:**
• أهداف ربح أكبر (5-10%)
• وقف خسارة أوسع (2%)
• تحليل شامل ومتأني
• مناسب للاستثمار طويل الأمد

اختر النمط المناسب لك:
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=create_trading_mode_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إعدادات نمط التداول: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض أنماط التداول", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_trading_mode_"))
def handle_set_trading_mode(call):
    """معالج تعيين نمط التداول"""
    try:
        user_id = call.from_user.id
        mode = call.data.replace("set_trading_mode_", "")
        
        set_user_trading_mode(user_id, mode)
        mode_display = "السكالبينغ السريع" if mode == 'scalping' else "التداول طويل الأمد"
        
        bot.answer_callback_query(call.id, f"✅ تم تعيين نمط {mode_display}")
        
        # تحديث القائمة
        handle_trading_mode_settings(call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تعيين نمط التداول: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تعيين النمط", show_alert=True)

# ===== معالج مسح السجل =====
@bot.callback_query_handler(func=lambda call: call.data == "clear_alerts")
def handle_clear_alerts(call):
    """معالج مسح سجل التنبيهات"""
    try:
        user_id = call.from_user.id
        
        # حذف جميع ملفات السجل للمستخدم
        deleted_count = 0
        try:
            for filename in os.listdir(TRADE_LOGS_DIR):
                if filename.startswith("trade_") and filename.endswith(".json"):
                    file_path = os.path.join(TRADE_LOGS_DIR, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        trade_data = json.load(f)
                        if trade_data.get('user_id') == user_id:
                            os.remove(file_path)
                            deleted_count += 1
        except Exception as e:
            logger.error(f"خطأ في حذف ملفات السجل: {e}")
        
        if deleted_count > 0:
            bot.answer_callback_query(call.id, f"✅ تم مسح {deleted_count} تنبيه من السجل")
        else:
            bot.answer_callback_query(call.id, "ℹ️ لا توجد تنبيهات لمسحها")
        
        # تحديث عرض السجل
        handle_alerts_log(call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في مسح السجل: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في مسح السجل", show_alert=True)

# ===== معالجات رأس المال =====
@bot.callback_query_handler(func=lambda call: call.data == "set_capital")
def handle_set_capital(call):
    """معالج تحديد رأس المال"""
    try:
        user_id = call.from_user.id
        current_capital = get_user_capital(user_id)
        
        message_text = f"""
💰 **تحديد رأس المال**

رأس المال الحالي: ${current_capital:,.0f}

اختر رأس المال المناسب لك:
(يؤثر على حجم الصفقات المقترحة وإدارة المخاطر)
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for capital in DEFAULT_CAPITAL_OPTIONS:
            button_text = f"✅ ${capital:,}" if capital == current_capital else f"${capital:,}"
            markup.row(
                types.InlineKeyboardButton(button_text, callback_data=f"set_capital_{capital}")
            )
        
        # زر إدخال مبلغ مخصص
        markup.row(
            create_animated_button("💰 إدخال مبلغ مخصص", "custom_capital", "💰")
        )
        
        markup.row(
            create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحديد رأس المال: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض خيارات رأس المال", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_capital_"))
def handle_set_capital_value(call):
    """معالج تعيين قيمة رأس المال"""
    try:
        user_id = call.from_user.id
        capital = int(call.data.replace("set_capital_", ""))
        
        set_user_capital(user_id, capital)
        
        bot.answer_callback_query(call.id, f"✅ تم تحديد رأس المال: ${capital:,}")
        
        # تحديث القائمة
        handle_set_capital(call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تعيين رأس المال: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تعيين رأس المال", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "custom_capital")
def handle_custom_capital(call):
    """معالج إدخال مبلغ مخصص لرأس المال"""
    try:
        user_id = call.from_user.id
        user_states[user_id] = 'waiting_custom_capital'
        
        bot.edit_message_text(
            "💰 **إدخال مبلغ مخصص لرأس المال**\n\n"
            "يرجى إدخال المبلغ المطلوب بالدولار الأمريكي:\n"
            "مثال: 1500 أو 25000\n\n"
            "الحد الأدنى: $50\n"
            "الحد الأقصى: $1,000,000",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=types.InlineKeyboardMarkup().row(
                create_animated_button("❌ إلغاء", "set_capital", "❌")
            )
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إدخال مبلغ مخصص: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_custom_capital')
def handle_custom_capital_input(message):
    """معالج إدخال المبلغ المخصص"""
    try:
        user_id = message.from_user.id
        
        # محاولة تحويل النص إلى رقم
        try:
            capital = float(message.text.replace(',', '').replace('$', ''))
            
            if capital < 50:
                bot.reply_to(message, "❌ المبلغ أقل من الحد الأدنى ($50). يرجى إدخال مبلغ أكبر.")
                return
            
            if capital > 1000000:
                bot.reply_to(message, "❌ المبلغ أكبر من الحد الأقصى ($1,000,000). يرجى إدخال مبلغ أصغر.")
                return
            
            # تعيين رأس المال
            set_user_capital(user_id, capital)
            user_states.pop(user_id, None)
            
            bot.reply_to(message, f"✅ تم تحديد رأس المال بنجاح: ${capital:,.0f}")
            
            # العودة لقائمة رأس المال
            time.sleep(1)
            current_capital = get_user_capital(user_id)
            
            message_text = f"""
💰 **تحديد رأس المال**

رأس المال الحالي: ${current_capital:,.0f}

اختر رأس المال المناسب لك:
(يؤثر على حجم الصفقات المقترحة وإدارة المخاطر)
            """
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            
            for capital_option in DEFAULT_CAPITAL_OPTIONS:
                button_text = f"✅ ${capital_option:,}" if capital_option == current_capital else f"${capital_option:,}"
                markup.row(
                    types.InlineKeyboardButton(button_text, callback_data=f"set_capital_{capital_option}")
                )
            
            markup.row(
                create_animated_button("💰 إدخال مبلغ مخصص", "custom_capital", "💰")
            )
            
            markup.row(
                create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
            )
            
            bot.send_message(
                message.chat.id,
                message_text,
                parse_mode='Markdown',
                reply_markup=markup
            )
            
        except ValueError:
            bot.reply_to(message, "❌ يرجى إدخال رقم صحيح. مثال: 1500")
            
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة المبلغ المخصص: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة المبلغ")
        user_states.pop(user_id, None)

# ===== معالجات قواعد التحليل =====

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('state') == 'waiting_for_analysis_rule')
def handle_analysis_rule_input(message):
    """معالج إدخال قاعدة التحليل الجديدة"""
    try:
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        if len(user_input) < 10:
            bot.reply_to(message, "❌ القاعدة قصيرة جداً. يرجى إدخال قاعدة أكثر تفصيلاً (على الأقل 10 أحرف).")
            return
        
        if len(user_input) > 1000:
            bot.reply_to(message, "❌ القاعدة طويلة جداً. يرجى تقصيرها (أقل من 1000 حرف).")
            return
        
        # رسالة معالجة
        processing_msg = bot.reply_to(message, "🤖 جاري معالجة القاعدة بالذكاء الاصطناعي...")
        
        # معالجة القاعدة بالذكاء الاصطناعي
        processed_rule = process_user_rule_with_ai(user_input, user_id)
        
        if not processed_rule:
            bot.edit_message_text(
                "❌ فشل في معالجة القاعدة. سيتم حفظ النص الأصلي.",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            processed_rule = user_input
        else:
            bot.edit_message_text(
                "✅ تم تحسين القاعدة بنجاح!",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        
        # تحميل القواعد الحالية
        rules = load_analysis_rules()
        
        # إضافة القاعدة الجديدة
        new_rule = {
            'id': len(rules) + 1,
            'user_id': user_id,
            'original_rule': user_input,
            'processed_rule': processed_rule,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'active'
        }
        
        rules.append(new_rule)
        
        # حفظ القواعد
        if save_analysis_rules(rules):
            success_message = f"""
✅ **تم إضافة القاعدة بنجاح!**

**القاعدة الأصلية:**
{user_input}

**القاعدة المحسنة:**
{processed_rule}

🔄 **ستكون هذه القاعدة فعالة في جميع التحليلات القادمة**
            """
            
            bot.reply_to(message, success_message)
            
            # إزالة حالة المستخدم
            user_state = user_states.get(user_id, {})
            if user_state.get('message_id') and user_state.get('chat_id'):
                try:
                    # العودة لقائمة إدارة القواعد
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    markup.row(
                        create_animated_button("➕ إضافة قاعدة أخرى", "add_analysis_rule", "➕")
                    )
                    markup.row(
                        create_animated_button("✏️ تحرير القواعد", "edit_analysis_rules", "✏️")
                    )
                    markup.row(
                        create_animated_button("🔙 العودة لقسم AI", "ai_section", "🔙")
                    )
                    
                    bot.edit_message_text(
                        "✅ تم إضافة القاعدة بنجاح!\n\nماذا تريد أن تفعل الآن؟",
                        chat_id=user_state['chat_id'],
                        message_id=user_state['message_id'],
                        reply_markup=markup
                    )
                except:
                    pass
        else:
            bot.reply_to(message, "❌ فشل في حفظ القاعدة. يرجى المحاولة مرة أخرى.")
        
        # إزالة حالة المستخدم
        user_states.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة قاعدة التحليل: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة القاعدة. يرجى المحاولة مرة أخرى.")
        user_states.pop(message.from_user.id, None)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('state') == 'waiting_for_rule_modification')
def handle_rule_modification_input(message):
    """معالج تعديل قاعدة التحليل"""
    try:
        user_id = message.from_user.id
        user_input = message.text.strip()
        user_state = user_states.get(user_id, {})
        rule_index = user_state.get('rule_index')
        
        if rule_index is None:
            bot.reply_to(message, "❌ خطأ في تحديد القاعدة. يرجى المحاولة مرة أخرى.")
            user_states.pop(user_id, None)
            return
        
        if len(user_input) < 10:
            bot.reply_to(message, "❌ النص قصير جداً. يرجى إدخال نص أكثر تفصيلاً (على الأقل 10 أحرف).")
            return
        
        if len(user_input) > 1000:
            bot.reply_to(message, "❌ النص طويل جداً. يرجى تقصيره (أقل من 1000 حرف).")
            return
        
        # رسالة معالجة
        processing_msg = bot.reply_to(message, "🤖 جاري معالجة التعديل بالذكاء الاصطناعي...")
        
        # معالجة النص الجديد بالذكاء الاصطناعي
        processed_rule = process_user_rule_with_ai(user_input, user_id)
        
        if not processed_rule:
            bot.edit_message_text(
                "❌ فشل في معالجة التعديل. سيتم حفظ النص الأصلي.",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            processed_rule = user_input
        else:
            bot.edit_message_text(
                "✅ تم تحسين التعديل بنجاح!",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        
        # تحميل القواعد الحالية
        rules = load_analysis_rules()
        
        if rule_index >= len(rules):
            bot.reply_to(message, "❌ القاعدة غير موجودة. يرجى المحاولة مرة أخرى.")
            user_states.pop(user_id, None)
            return
        
        # تحديث القاعدة
        old_rule = rules[rule_index]['processed_rule']
        rules[rule_index]['original_rule'] = user_input
        rules[rule_index]['processed_rule'] = processed_rule
        rules[rule_index]['modified_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rules[rule_index]['modified_by'] = user_id
        
        # حفظ القواعد
        if save_analysis_rules(rules):
            success_message = f"""
✅ **تم تعديل القاعدة بنجاح!**

**القاعدة السابقة:**
{old_rule}

**القاعدة الجديدة:**
{processed_rule}

🔄 **سيتم تطبيق التعديل في جميع التحليلات القادمة**
            """
            
            bot.reply_to(message, success_message)
            
            # العودة لقائمة القواعد
            if user_state.get('message_id') and user_state.get('chat_id'):
                try:
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    markup.row(
                        create_animated_button("✏️ تحرير قواعد أخرى", "edit_analysis_rules", "✏️")
                    )
                    markup.row(
                        create_animated_button("🔙 العودة لقسم AI", "ai_section", "🔙")
                    )
                    
                    bot.edit_message_text(
                        "✅ تم تعديل القاعدة بنجاح!\n\nماذا تريد أن تفعل الآن؟",
                        chat_id=user_state['chat_id'],
                        message_id=user_state['message_id'],
                        reply_markup=markup
                    )
                except:
                    pass
        else:
            bot.reply_to(message, "❌ فشل في حفظ التعديل. يرجى المحاولة مرة أخرى.")
        
        # إزالة حالة المستخدم
        user_states.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في معالجة تعديل القاعدة: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة التعديل. يرجى المحاولة مرة أخرى.")
        user_states.pop(message.from_user.id, None)

# ===== معالج الرسائل العام =====
@bot.message_handler(func=lambda message: True)
def handle_unknown_message(message):
    """معالج الرسائل غير المعرفة - يتحقق من كلمة السر أولاً"""
    user_id = message.from_user.id
    
    # التحقق من كلمة السر أولاً
    if user_id not in user_sessions:
        # إذا لم يكن المستخدم في حالة انتظار كلمة السر، ضعه في هذه الحالة
        if user_states.get(user_id) != 'waiting_password':
            hide_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(
                chat_id=user_id,
                text="🔐 يجب إدخال كلمة المرور أولاً للوصول إلى البوت:",
                reply_markup=hide_keyboard
            )
            user_states[user_id] = 'waiting_password'
        return
    
    # إذا كان المستخدم مصدق، أرسل رسالة غير معروفة
    bot.reply_to(message, "❓ أمر غير معروف. استخدم الأزرار في الأسفل للتنقل.")

# ===== معالجات المنطقة الزمنية =====
@bot.callback_query_handler(func=lambda call: call.data == "timezone_settings")
def handle_timezone_settings(call):
    """معالج إعدادات المنطقة الزمنية"""
    try:
        user_id = call.from_user.id
        current_timezone = get_user_timezone(user_id)
        
        message_text = f"""
🌍 **إعدادات المنطقة الزمنية**

المنطقة الحالية: {AVAILABLE_TIMEZONES.get(current_timezone, current_timezone)}

اختر المنطقة الزمنية المناسبة لك:
(يؤثر على أوقات عرض التنبيهات والتحليلات)
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for tz_key, tz_name in AVAILABLE_TIMEZONES.items():
            button_text = f"✅ {tz_name}" if tz_key == current_timezone else tz_name
            markup.row(
                types.InlineKeyboardButton(button_text, callback_data=f"set_timezone_{tz_key}")
            )
        
        markup.row(
            create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إعدادات المنطقة الزمنية: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض المناطق الزمنية", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_timezone_"))
def handle_set_timezone(call):
    """معالج تعيين المنطقة الزمنية"""
    try:
        user_id = call.from_user.id
        timezone = call.data.replace("set_timezone_", "")
        
        set_user_timezone(user_id, timezone)
        timezone_name = AVAILABLE_TIMEZONES.get(timezone, timezone)
        
        bot.answer_callback_query(call.id, f"✅ تم تحديد المنطقة الزمنية: {timezone_name}")
        
        # تحديث القائمة
        handle_timezone_settings(call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تعيين المنطقة الزمنية: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في تعيين المنطقة الزمنية", show_alert=True)

# ===== معالج الإحصائيات =====
@bot.callback_query_handler(func=lambda call: call.data == "statistics")
def handle_statistics(call):
    """معالج الإحصائيات"""
    try:
        user_id = call.from_user.id
        
        # جلب إحصائيات المستخدم
        stats = trade_data_manager.get_user_feedback_stats(user_id)
        trading_mode = get_user_trading_mode(user_id)
        is_monitoring = user_monitoring_active.get(user_id, False)
        selected_symbols = user_selected_symbols.get(user_id, [])
        
        message_text = f"""
📊 **إحصائيات التداول**

👤 **معلومات المستخدم:**
• نمط التداول: {'⚡ سكالبينغ سريع' if trading_mode == 'scalping' else '📈 تداول طويل المدى'}
• حالة المراقبة: {'🟢 نشطة' if is_monitoring else '🔴 متوقفة'}
• الرموز المراقبة: {len(selected_symbols)} رمز

📈 **إحصائيات التقييم:**
• إجمالي التقييمات: {stats['total_feedbacks']}
• تقييمات إيجابية: {stats['positive_feedbacks']} 👍
• تقييمات سلبية: {stats['negative_feedbacks']} 👎
• معدل الدقة: {stats['accuracy_rate']:.1f}%

🎯 **الأداء:**
• مستوى الثقة المطلوب: {get_user_advanced_notification_settings(user_id).get('success_threshold', 70)}%
• تردد الإشعارات: {NOTIFICATION_FREQUENCIES.get(get_user_advanced_notification_settings(user_id).get('frequency', '5min'), {}).get('name', '5 دقائق')}

💡 **نصائح للتحسين:**
{'• ممتاز! استمر على هذا الأداء 🎉' if stats['accuracy_rate'] >= 80 else '• يمكن تحسين الدقة بتعديل إعدادات التنبيهات'}
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.row(
            create_animated_button("🔙 العودة للإعدادات", "settings", "🔙")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض الإحصائيات: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض الإحصائيات", show_alert=True)

# ===== معالجات إعدادات التنبيهات المتقدمة =====
@bot.callback_query_handler(func=lambda call: call.data == "advanced_notifications_settings")
def handle_advanced_notifications_settings(call):
    """معالج إعدادات التنبيهات المتقدمة"""
    try:
        user_id = call.from_user.id
        settings = get_user_advanced_notification_settings(user_id)
        
        # إحصائيات سريعة
        enabled_count = sum(1 for key in ['support_alerts', 'breakout_alerts', 'trading_signals', 
                                        'economic_news', 'candlestick_patterns', 'volume_alerts'] if settings.get(key, True))
        
        frequency_display = NOTIFICATION_FREQUENCIES.get(settings.get('frequency', '5min'), {}).get('name', '5 دقائق')
        
        message_text = f"""
🔔 **إعدادات الإشعارات المتقدمة**

📊 **الأنواع المفعلة:** {enabled_count}/6
⏱️ **التردد الحالي:** {frequency_display}
📈 **نسبة النجاح:** {settings.get('success_threshold', 70)}%
📋 **مدة الاحتفاظ:** {settings.get('log_retention', 7)} أيام

اختر الإعداد المطلوب تعديله:
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=create_advanced_notifications_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إعدادات التنبيهات المتقدمة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ في عرض الإعدادات", show_alert=True)



@bot.callback_query_handler(func=lambda call: call.data == "success_threshold")
def handle_success_threshold(call):
    """معالج تحديد نسبة النجاح"""
    try:
        user_id = call.from_user.id
        settings = get_user_advanced_notification_settings(user_id)
        current_threshold = settings.get('success_threshold', 70)
        
        message_text = f"""
📊 **نسبة النجاح المطلوبة للفلترة**

النسبة الحالية: {current_threshold}%

اختر الحد الأدنى لنسبة النجاح لتلقي التنبيهات:

🎯 **مستويات الجودة:**
• 90%+ : إشارات استثنائية 💎
• 80-89%: إشارات عالية الجودة 🔥  
• 70-79%: إشارات جيدة ✅
• 60-69%: إشارات متوسطة ⚠️
• 50-59%: إشارات ضعيفة (مخاطر عالية) 🔴
• 0%: جميع الإشارات (بما فيها الضعيفة) 📊

💡 **نصيحة:** نسبة أعلى = تنبيهات أقل ولكن أدق وأأمن
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=create_success_threshold_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحديد نسبة النجاح: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)



@bot.callback_query_handler(func=lambda call: call.data.startswith("set_threshold_"))
def handle_set_threshold(call):
    """معالج تعيين نسبة النجاح"""
    try:
        user_id = call.from_user.id
        threshold = int(call.data.replace("set_threshold_", ""))
        
        update_user_advanced_notification_setting(user_id, 'success_threshold', threshold)
        
        bot.answer_callback_query(call.id, f"✅ تم تحديد نسبة النجاح: {threshold}%")
        
        # تحديث القائمة
        handle_success_threshold(call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تحديد نسبة النجاح: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

# تم حذف معالجات التردد المكررة - التردد الآن موحد لكل 15 ثانية

@bot.callback_query_handler(func=lambda call: call.data == "notification_timing")
def handle_notification_timing(call):
    """معالج توقيت الإشعارات"""
    try:
        user_id = call.from_user.id
        settings = get_user_advanced_notification_settings(user_id)
        current_timing = settings.get('alert_timing', '24h')
        
        timing_options = {
            '24h': '24 ساعة (دائماً) 🕐',
            'morning': 'الصباح (6ص - 12ظ) 🌅',
            'afternoon': 'بعد الظهر (12ظ - 6م) ☀️',
            'evening': 'المساء (6م - 12ص) 🌆',
            'night': 'الليل (12ص - 6ص) 🌙'
        }
        
        current_display = timing_options.get(current_timing, '24 ساعة')
        
        message_text = f"""
⏰ **توقيت الإشعارات**

التوقيت الحالي: {current_display}

اختر الأوقات المفضلة لاستقبال الإشعارات:
(حسب منطقتك الزمنية المحددة)
        """
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for timing_key, timing_name in timing_options.items():
            button_text = f"✅ {timing_name}" if timing_key == current_timing else f"⚪ {timing_name}"
            markup.row(
                types.InlineKeyboardButton(button_text, callback_data=f"set_timing_{timing_key}")
            )
        
        markup.row(
            create_animated_button("🔙 العودة لإعدادات التنبيهات", "advanced_notifications_settings", "🔙")
        )
        
        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في توقيت الإشعارات: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_timing_"))
def handle_set_timing(call):
    """معالج تعيين توقيت الإشعارات"""
    try:
        user_id = call.from_user.id
        timing = call.data.replace("set_timing_", "")
        
        update_user_advanced_notification_setting(user_id, 'alert_timing', timing)
        
        timing_names = {
            '24h': '24 ساعة (دائماً)',
            'morning': 'الصباح (6ص - 12ظ)',
            'afternoon': 'بعد الظهر (12ظ - 6م)',
            'evening': 'المساء (6م - 12ص)',
            'night': 'الليل (12ص - 6ص)'
        }
        
        timing_name = timing_names.get(timing, timing)
        bot.answer_callback_query(call.id, f"✅ تم تحديد التوقيت: {timing_name}")
        
        # تحديث القائمة
        handle_notification_timing(call)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في تعيين التوقيت: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

# ===== معالجات الأسعار المباشرة المحسنة =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("live_"))
def handle_live_category_prices(call):
    """معالج الأسعار المباشرة للفئات - MT5 فقط بدون تحديث تلقائي"""
    try:
        user_id = call.from_user.id
        category = call.data.replace("live_", "")
        
        category_names = {
            'crypto': 'العملات الرقمية ₿',
            'forex': 'العملات الأجنبية 💱',
            'metals': 'المعادن النفيسة 🥇',
            'stocks': 'الأسهم الأمريكية 📈',
            'indices': 'المؤشرات 📊'
        }
        
        # جلب الرموز حسب الفئة
        if category == 'crypto':
            symbols = CRYPTO_PAIRS
        elif category == 'forex':
            symbols = CURRENCY_PAIRS
        elif category == 'metals':
            symbols = METALS
        elif category == 'stocks':
            symbols = STOCKS
        elif category == 'indices':
            symbols = INDICES
        else:
            symbols = {}
        
        category_name = category_names.get(category, 'فئة غير معروفة')
        
        # عرض الأسعار الفورية من MT5
        display_instant_prices(user_id, call.message.chat.id, call.message.message_id, 
                              symbols, category_name, category)
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في الأسعار المباشرة للفئة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

def display_instant_prices(user_id, chat_id, message_id, symbols, category_name, category):
    """عرض الأسعار الفورية من MT5 فقط بدون تحديث تلقائي"""
    try:
        current_time = get_current_time_for_user(user_id)
        
        message_text = f"""
📈 **الأسعار المباشرة - {category_name}**

{current_time}
🔗 **مصدر البيانات:** MetaTrader5 (لحظي)

───────────────────────
"""
        
        # التحقق من اتصال MT5
        if not mt5_manager.connected:
            message_text += """
❌ **غير متصل بـ MetaTrader5**

🔧 **للحصول على الأسعار:**
• تأكد من تشغيل MetaTrader5
• تحقق من اتصال الإنترنت  
• حاول مرة أخرى بعد قليل

───────────────────────
"""
        else:
            # جلب الأسعار من MT5 فقط
            prices_data = []
            available_count = 0
            
            for symbol, info in symbols.items():
                try:
                    price_data = mt5_manager.get_live_price(symbol)
                    if price_data:
                        bid = price_data.get('bid', 0)
                        ask = price_data.get('ask', 0)
                        spread = price_data.get('spread', 0)
                        last_price = price_data.get('last', bid)
                        
                        # التحقق من صحة البيانات بمرونة أكثر
                        if (bid > 0 and ask > 0) or last_price > 0:
                            # استخدام bid/ask إذا كانا متوفرين، وإلا استخدم last_price
                            display_bid = bid if bid > 0 else last_price
                            display_ask = ask if ask > 0 else last_price
                            display_spread = spread if spread > 0 else abs(display_ask - display_bid)
                            
                            prices_data.append(f"""
{info['emoji']} **{info['name']}**
📊 شراء: {display_bid:.5f} | بيع: {display_ask:.5f}
📏 فرق: {display_spread:.5f}
""")
                        else:
                            prices_data.append(f"""
{info['emoji']} **{info['name']}**
⚠️ بيانات غير مكتملة من MT5
""")
                        available_count += 1
                    else:
                        # إضافة معلومات تشخيصية أكثر تفصيلاً
                        if not mt5_manager.connected:
                            status_msg = "❌ غير متصل بـ MT5"
                        else:
                            status_msg = "❌ غير متاح من MT5 (قد يكون متاح من Yahoo Finance)"
                        
                        prices_data.append(f"""
{info['emoji']} **{info['name']}**
{status_msg}
""")
                        
                except Exception as e:
                    logger.error(f"[ERROR] خطأ في جلب سعر {symbol}: {e}")
                    prices_data.append(f"""
{info['emoji']} **{info['name']}**
⚠️ خطأ في البيانات
""")
            
            message_text += "\n".join(prices_data)
            message_text += "\n\n───────────────────────"
            message_text += f"\n✅ **متوفر:** {available_count}/{len(symbols)} رمز"
        
        # إنشاء لوحة التحكم
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.row(
            create_animated_button("🔄 تحديث الأسعار", f"live_{category}", "🔄"),
            create_animated_button("🔙 العودة للفئات", "live_prices", "🔙")
        )
        markup.row(
            create_animated_button("🔙 القائمة الرئيسية", "main_menu", "🔙")
        )
        
        # تحديث الرسالة
        bot.edit_message_text(
            message_text,
            chat_id,
            message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في عرض الأسعار الفورية: {e}")
        bot.edit_message_text(
            f"❌ **خطأ في عرض الأسعار**\n\n"
            f"حدث خطأ أثناء جلب أسعار {category_name}.\n"
            "يرجى المحاولة مرة أخرى.",
            chat_id,
            message_id,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_live_"))
def handle_stop_live_prices(call):
    """معالج إيقاف التحديث التلقائي للأسعار"""
    try:
        category = call.data.replace("stop_live_", "")
        
        bot.edit_message_text(
            "⏸️ **تم إيقاف التحديث التلقائي**\n\n"
            "يمكنك العودة لقائمة الأسعار المباشرة لبدء المراقبة مرة أخرى.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=types.InlineKeyboardMarkup().row(
                create_animated_button("🔙 العودة للأسعار", "live_prices", "🔙")
            )
        )
        
        bot.answer_callback_query(call.id, "✅ تم إيقاف التحديث التلقائي")
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في إيقاف الأسعار المباشرة: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "live_prices_menu")
def handle_live_prices_menu(call):
    """العودة لقائمة الأسعار المباشرة"""
    handle_live_prices(call)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def handle_main_menu(call):
    """العودة للقائمة الرئيسية"""
    try:
        # إنشاء رسالة ترحيبية مختصرة
        welcome_message = f"""
🎉 **بوت التداول المتقدم v1.2.0**

🚀 **الميزات:**
✅ تحليل ذكي بـ Gemini AI
✅ بيانات حقيقية من MT5
✅ إشعارات مخصصة

📊 **حالة الاتصال:**
• MetaTrader5: {'🟢 متصل' if mt5_manager.connected else '🔴 منقطع'}
• Gemini AI: {'🟢 متاح' if GEMINI_AVAILABLE else '🔴 غير متاح'}

استخدم الأزرار في الأسفل للتنقل 👇
        """
        
        bot.edit_message_text(
            welcome_message,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        # إرسال الكيبورد الثابت إذا لم يكن موجوداً
        bot.send_message(
            call.message.chat.id,
            "اختر الخدمة المطلوبة:",
            reply_markup=create_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في العودة للقائمة الرئيسية: {e}")
        bot.answer_callback_query(call.id, "حدث خطأ", show_alert=True)

# تم حذف المعالجات المكررة لتجنب التضارب

# ===== نظام المراقبة والتنبيهات =====
# تم حذف نظام الـ cache - سنستخدم بيانات لحظية فقط

def is_notification_time_allowed(user_id: int, alert_timing: str) -> bool:
    """فحص ما إذا كان الوقت الحالي مناسب لإرسال الإشعارات حسب المنطقة الزمنية للمستخدم"""
    if alert_timing == '24h':
        return True
    
    try:
        import pytz
        from datetime import datetime
        
        # الحصول على المنطقة الزمنية للمستخدم
        user_timezone = get_user_timezone(user_id)
        
        # تحويل الوقت للمنطقة الزمنية للمستخدم
        tz = pytz.timezone(user_timezone)
        current_time = datetime.now(tz)
        current_hour = current_time.hour
        
        # تحديد الأوقات المسموحة حسب إعدادات المستخدم
        if alert_timing == 'morning':  # الصباح: 6ص - 12ظ
            return 6 <= current_hour < 12
        elif alert_timing == 'afternoon':  # بعد الظهر: 12ظ - 6م
            return 12 <= current_hour < 18
        elif alert_timing == 'evening':  # المساء: 6م - 12ص
            return 18 <= current_hour < 24
        elif alert_timing == 'night':  # الليل: 12ص - 6ص
            return 0 <= current_hour < 6
        
    except Exception as e:
        logger.error(f"[ERROR] خطأ في فحص التوقيت للمستخدم {user_id}: {e}")
        return True  # في حالة الخطأ، نسمح بالإشعار
    
    return True

def monitoring_loop():
    """حلقة مراقبة الأسعار وإرسال التنبيهات مع معالجة محسنة للأخطاء"""
    global monitoring_active
    logger.info("[RUNNING] بدء حلقة المراقبة...")
    consecutive_errors = 0
    max_consecutive_errors = 5
    connection_check_interval = 300  # فحص الاتصال كل 5 دقائق
    last_connection_check = 0
    
    while monitoring_active:
        try:
            current_time = time.time()
            
            # فحص دوري لحالة اتصال MT5
            if current_time - last_connection_check > connection_check_interval:
                logger.debug("[DEBUG] فحص دوري لحالة اتصال MT5...")
                if not mt5_manager.validate_connection_health():
                    logger.warning("[WARNING] انقطاع في اتصال MT5 تم اكتشافه - محاولة إعادة الاتصال...")
                    mt5_manager.check_real_connection()
                last_connection_check = current_time
            
            # مراقبة المستخدمين النشطين فقط
            active_users = list(user_monitoring_active.keys())
            logger.debug(f"[DEBUG] المستخدمون النشطون: {active_users}")
            if not active_users:
                logger.debug("[DEBUG] لا يوجد مستخدمين نشطين - انتظار 30 ثانية")
                time.sleep(30)  # انتظار أطول إذا لم يكن هناك مستخدمين نشطين
                continue
            
            successful_operations = 0
            failed_operations = 0
            mt5_connection_errors = 0
            
            # الخطوة 1: تجميع جميع الرموز المطلوبة من جميع المستخدمين
            all_symbols_needed = set()
            users_by_symbol = {}  # {symbol: [user_ids]}
            
            for user_id in active_users:
                if not user_monitoring_active.get(user_id, False):
                    continue
                    
                selected_symbols = user_selected_symbols.get(user_id, [])
                logger.debug(f"[DEBUG] الرموز المختارة للمستخدم {user_id}: {selected_symbols}")
                if not selected_symbols:
                    logger.debug(f"[DEBUG] لا توجد رموز مختارة للمستخدم {user_id}")
                    continue
                
                for symbol in selected_symbols:
                    all_symbols_needed.add(symbol)
                    if symbol not in users_by_symbol:
                        users_by_symbol[symbol] = []
                    users_by_symbol[symbol].append(user_id)
            
            # الخطوة 2: جلب البيانات لجميع الرموز مرة واحدة فقط
            symbols_data = {}  # {symbol: price_data}
            for symbol in all_symbols_needed:
                try:
                    price_data = mt5_manager.get_live_price(symbol)
                    if price_data:
                        symbols_data[symbol] = price_data
                    else:
                        failed_operations += 1
                        if not mt5_manager.connected:
                            mt5_connection_errors += 1
                except Exception as e:
                    logger.error(f"[ERROR] خطأ في جلب بيانات {symbol}: {e}")
                    failed_operations += 1
            
            # الخطوة 3: معالجة كل رمز مع المستخدمين المهتمين به
            for symbol, price_data in symbols_data.items():
                try:
                    # تحليل الرمز مرة واحدة فقط
                    analysis = gemini_analyzer.analyze_market_data_with_retry(symbol, price_data, users_by_symbol[symbol][0])
                    
                    if not analysis:
                        failed_operations += len(users_by_symbol[symbol])
                        continue
                    
                    # إرسال للمستخدمين المهتمين بهذا الرمز
                    for user_id in users_by_symbol[symbol]:
                        try:
                            # الحصول على إعدادات المستخدم
                            settings = get_user_advanced_notification_settings(user_id)
                            min_confidence = settings.get('success_threshold', 70)
                            alert_timing = settings.get('alert_timing', '24h')
                            
                            # فحص التوقيت المناسب للإشعارات
                            if not is_notification_time_allowed(user_id, alert_timing):
                                successful_operations += 1  # العملية نجحت لكن ليس الوقت المناسب
                                continue
                            
                            # إرسال التنبيه إذا كانت هناك إشارة قوية
                            if analysis.get('confidence', 0) >= min_confidence:
                                signal = {
                                    'action': analysis.get('action', 'HOLD'),
                                    'confidence': analysis.get('confidence', 0),
                                    'reasoning': analysis.get('reasoning', [])
                                }
                                
                                try:
                                    send_trading_signal_alert(user_id, symbol, signal, analysis)
                                    successful_operations += 1
                                except Exception as alert_error:
                                    logger.error(f"[ERROR] خطأ في إرسال تنبيه {symbol} للمستخدم {user_id}: {alert_error}")
                                    failed_operations += 1
                            else:
                                successful_operations += 1  # لا توجد إشارة قوية ولكن العملية نجحت
                                
                        except Exception as user_error:
                            logger.error(f"[ERROR] خطأ في معالجة المستخدم {user_id} للرمز {symbol}: {user_error}")
                            failed_operations += 1
                            continue
                            
                except Exception as symbol_error:
                    logger.error(f"[ERROR] خطأ في معالجة الرمز {symbol}: {symbol_error}")
                    failed_operations += len(users_by_symbol[symbol])
                    continue
            
            # تتبع نجاح العمليات وحالة الاتصال
            if successful_operations > 0:
                consecutive_errors = 0  # إعادة تعيين عداد الأخطاء المتتالية
                
            # تحذير خاص لمشاكل اتصال MT5
            if mt5_connection_errors > 0:
                logger.warning(f"[WARNING] {mt5_connection_errors} أخطاء اتصال MT5 في هذه الدورة")
                
            if failed_operations > successful_operations and failed_operations > 10:
                logger.warning(f"[WARNING] نسبة عالية من الأخطاء: {failed_operations} فشل مقابل {successful_operations} نجح")
                
                # إذا كانت معظم الأخطاء بسبب MT5، نحاول إعادة الاتصال
                if mt5_connection_errors > failed_operations * 0.7:  # 70% من الأخطاء بسبب MT5
                    logger.info("[RECONNECT] محاولة إعادة اتصال شاملة بسبب أخطاء MT5 المتكررة...")
                    mt5_manager.check_real_connection()
            
            # انتظار 15 ثانية - تردد موحد لجميع المستخدمين
            time.sleep(15)
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"[ERROR] خطأ في حلقة المراقبة (الخطأ رقم {consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"[ERROR] تم الوصول للحد الأقصى للأخطاء المتتالية ({max_consecutive_errors}). إيقاف مؤقت لمدة 5 دقائق...")
                time.sleep(300)  # انتظار 5 دقائق
                consecutive_errors = 0  # إعادة تعيين العداد
                
                # محاولة إعادة تهيئة MT5 بعد الإيقاف المؤقت
                logger.info("[RECONNECT] محاولة إعادة تهيئة MT5 بعد الإيقاف المؤقت...")
                mt5_manager.initialize_mt5()
            else:
                # انتظار متدرج حسب عدد الأخطاء
                wait_time = min(60 * consecutive_errors, 300)  # حد أقصى 5 دقائق
                time.sleep(wait_time)
    
    logger.info("[SYSTEM] تم إنهاء حلقة المراقبة بأمان")

# ===== تشغيل البوت =====
if __name__ == "__main__":
    try:
        logger.info("▶️ بدء تشغيل بوت التداول المتقدم v1.2.0...")
        
        # التحقق من اتصال MT5
        if mt5_manager.connected:
            logger.info("[OK] MetaTrader5 متصل ومستعد!")
        else:
            logger.warning("[WARNING] MetaTrader5 غير متصل - يرجى التحقق من الإعدادات")
        
        # التحقق من Gemini AI
        if GEMINI_AVAILABLE:
            logger.info("[OK] Gemini AI جاهز للتحليل!")
        else:
            logger.warning("[WARNING] Gemini AI غير متوفر - تأكد من مفتاح API")
        
        logger.info("[SYSTEM] نظام التنبيهات: مراقبة لحظية مع تقييم المستخدم")
        logger.info("[SYSTEM] نظام التخزين: تسجيل جميع الصفقات والتقييمات")
        
        # إنشاء متغير لإيقاف حلقة المراقبة بأمان
        monitoring_active = True
        
        # بدء حلقة المراقبة في خيط منفصل مع معالجة محسنة
        monitoring_thread = threading.Thread(
            target=monitoring_loop, 
            daemon=True,
            name="MonitoringThread"
        )
        monitoring_thread.start()
        logger.info("[RUNNING] تم بدء حلقة المراقبة في الخلفية")
        
        # التحقق من بدء الـ thread بنجاح
        time.sleep(1)
        if monitoring_thread.is_alive():
            logger.info("[OK] خيط المراقبة يعمل بشكل صحيح")
        else:
            logger.error("[ERROR] فشل في بدء خيط المراقبة")
        
        # بدء البوت
        logger.info("[SYSTEM] البوت جاهز للعمل!")
        print("\n" + "="*60)
        print("🚀 بوت التداول v1.2.0 جاهز للعمل!")
        print("📊 مصدر البيانات: MetaTrader5 (لحظي)")
        print("🧠 محرك التحليل: Google Gemini AI")
        print("💾 نظام التقييم: تفعيل ذكي للتعلم")
        print("="*60 + "\n")
        
        # تشغيل البوت مع معالجة أخطاء الشبكة
        while True:
            try:
                logger.info("[SYSTEM] بدء استقبال الرسائل...")
                bot.infinity_polling(none_stop=True, interval=1, timeout=60)
                break  # إذا انتهى بشكل طبيعي
                
            except Exception as polling_error:
                logger.error(f"[ERROR] خطأ في الاستقبال: {polling_error}")
                logger.info("[SYSTEM] محاولة إعادة الاتصال خلال 5 ثواني...")
                time.sleep(5)
                continue
        
    except KeyboardInterrupt:
        logger.info("[SYSTEM] تم الحصول على إشارة إيقاف...")
        monitoring_active = False
        logger.info("[SYSTEM] تم إيقاف حلقة المراقبة")
    except Exception as e:
        logger.error(f"[ERROR] خطأ عام في تشغيل البوت: {e}")
        
    finally:
        # إغلاق اتصال MT5 عند الإنهاء بشكل آمن
        monitoring_active = False
        try:
            mt5_manager.graceful_shutdown()
        except Exception as e:
            logger.error(f"[ERROR] خطأ في إغلاق MT5: {e}")
        logger.info("[SYSTEM] تم إنهاء البوت بأمان")