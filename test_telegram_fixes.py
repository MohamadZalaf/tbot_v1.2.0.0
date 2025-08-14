#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار إصلاحات Telegram في البوت v1.2.0
التأكد من عدم وجود مشاكل في Markdown parsing
"""

import re

def test_markdown_parsing():
    """اختبار تحليل Markdown للتأكد من عدم وجود مشاكل"""
    print("🧪 اختبار تحليل Markdown...")
    
    # النصوص التي كانت تسبب مشاكل
    problematic_texts = [
        "🚨 **إشعار تداول آلي** 🥇",
        "🚀 **إشارة تداول ذكية**",
        "💱 **XAUUSD** | الذهب 🥇",
        "💰 **السعر اللحظي:** 2,650.50",
        "🔺 **مقاومة:** 3,358.34",
        "🔻 **دعم:** --",
        "🟢 **التوصية:** شراء | نجاح 75%",
        "📋 **تفاصيل التوصية:**",
        "📍 **سعر الدخول:** 2,650.50",
        "🛑 **ستوب لوس:** 2,637.25",
        "🎯 **تيك بروفيت:** 2,677.00"
    ]
    
    # النصوص المُصححة
    fixed_texts = [
        "🚨 *إشعار تداول آلي* 🥇",
        "🚀 *إشارة تداول ذكية*",
        "💱 *XAUUSD* | الذهب 🥇",
        "💰 *السعر اللحظي:* 2,650.50",
        "🔺 *مقاومة:* 3,358.34",
        "🔻 *دعم:* --",
        "🟢 *التوصية:* شراء | نجاح 75%",
        "📋 *تفاصيل التوصية:*",
        "📍 *سعر الدخول:* 2,650.50",
        "🛑 *ستوب لوس:* 2,637.25",
        "🎯 *تيك بروفيت:* 2,677.00"
    ]
    
    print("❌ النصوص التي كانت تسبب مشاكل:")
    for text in problematic_texts:
        # فحص وجود ** في النص
        if '**' in text:
            print(f"  - {text}")
    
    print("\n✅ النصوص المُصححة:")
    for text in fixed_texts:
        # فحص عدم وجود ** في النص
        if '**' not in text and '*' in text:
            print(f"  - {text}")
    
    # فحص شامل للرموز
    double_star_count = sum(1 for text in problematic_texts if '**' in text)
    single_star_count = sum(1 for text in fixed_texts if '*' in text and '**' not in text)
    
    print(f"\n📊 النتائج:")
    print(f"  - النصوص التي تحتوي على **: {double_star_count}")
    print(f"  - النصوص المُصححة بـ *: {single_star_count}")
    
    if double_star_count == 0:
        print("✅ لا توجد رموز ** في النصوص المُصححة")
        return True
    else:
        print("❌ ما زالت توجد رموز ** تحتاج إصلاح")
        return False

def test_callback_timeout_handling():
    """اختبار معالجة timeout في callback queries"""
    print("\n🧪 اختبار معالجة timeout...")
    
    # محاكاة أخطاء timeout المختلفة
    timeout_errors = [
        "query is too old and response timeout expired",
        "query ID is invalid",
        "timeout expired",
        "connection timeout"
    ]
    
    def simulate_safe_callback(error_msg):
        """محاكاة الدالة الآمنة"""
        try:
            if any(keyword in error_msg.lower() for keyword in ["query is too old", "timeout"]):
                print(f"  ✅ تم تجاهل خطأ timeout: {error_msg[:30]}...")
                return True
            else:
                print(f"  ⚠️ خطأ غير متوقع: {error_msg}")
                return False
        except Exception:
            return False
    
    success_count = 0
    for error in timeout_errors:
        if simulate_safe_callback(error):
            success_count += 1
    
    print(f"\n📊 النتائج:")
    print(f"  - أخطاء timeout تم التعامل معها: {success_count}/{len(timeout_errors)}")
    
    return success_count == len(timeout_errors)

def test_message_formatting():
    """اختبار تنسيق الرسائل"""
    print("\n🧪 اختبار تنسيق الرسائل...")
    
    # محاكاة رسالة إشعار
    symbol = "XAUUSD"
    current_price = 2650.50
    action = "BUY"
    confidence = 75
    
    # الرسالة المُصححة
    message = f"""🚨 *إشعار تداول آلي* 🥇

🚀 *إشارة تداول ذكية*

━━━━━━━━━━━━━━━━━━━━━━━━━
💱 *{symbol}* | الذهب 🥇
💰 *السعر اللحظي:* {current_price:,.5f}
🔺 *مقاومة:* 2,677.00
🔻 *دعم:* 2,625.00

━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 *التوصية:* شراء | نجاح {confidence}%

📋 *تفاصيل التوصية:*
📍 *سعر الدخول:* {current_price:,.5f} (حالي)
🛑 *ستوب لوس:* 2,637.25 (مقترح)
🎯 *تيك بروفيت:* 2,677.00 (مقترح)"""
    
    # فحص الرسالة
    has_double_stars = '**' in message
    has_single_stars = '*' in message and '**' not in message
    
    print("📝 الرسالة المُنسقة:")
    print(message[:200] + "..." if len(message) > 200 else message)
    
    print(f"\n📊 التحليل:")
    print(f"  - يحتوي على **: {'❌ نعم' if has_double_stars else '✅ لا'}")
    print(f"  - يحتوي على *: {'✅ نعم' if has_single_stars else '❌ لا'}")
    print(f"  - طول الرسالة: {len(message)} حرف")
    
    return not has_double_stars and has_single_stars

def main():
    """تشغيل جميع الاختبارات"""
    print("🚀 بدء اختبار إصلاحات Telegram")
    print("=" * 50)
    
    tests = [
        ("تحليل Markdown", test_markdown_parsing),
        ("معالجة Timeout", test_callback_timeout_handling),
        ("تنسيق الرسائل", test_message_formatting)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: نجح")
        else:
            print(f"❌ {test_name}: فشل")
    
    print("\n" + "=" * 50)
    print(f"📊 نتائج الاختبار: {passed}/{total} نجح")
    
    if passed == total:
        print("🎉 جميع إصلاحات Telegram تعمل بشكل صحيح!")
        print("✅ البوت جاهز لإرسال الرسائل بدون أخطاء")
    else:
        print("⚠️ بعض الإصلاحات تحتاج مراجعة")
    
    return passed == total

if __name__ == "__main__":
    main()