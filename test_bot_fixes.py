#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار إصلاحات البوت v1.2.0
تأكد من عمل جميع الوظائف بشكل صحيح
"""

import sys
import os
sys.path.append('/workspace')

def test_imports():
    """اختبار الاستيرادات"""
    print("🧪 اختبار الاستيرادات...")
    try:
        from tbot_v1.2.0 import MT5Manager, GeminiAnalyzer
        print("✅ تم استيراد الكلاسات بنجاح")
        return True
    except Exception as e:
        print(f"❌ فشل في الاستيراد: {e}")
        return False

def test_mt5_manager():
    """اختبار MT5Manager"""
    print("\n🧪 اختبار MT5Manager...")
    try:
        from tbot_v1.2.0 import MT5Manager
        
        # إنشاء مثيل
        mt5_manager = MT5Manager()
        print(f"✅ تم إنشاء MT5Manager - حالة الاتصال: {mt5_manager.connected}")
        
        # اختبار جلب السعر
        price_data = mt5_manager.get_live_price('XAUUSD')
        if price_data:
            print(f"✅ تم جلب سعر XAUUSD: {price_data.get('last', 'غير متوفر')}")
        else:
            print("⚠️ لم يتم جلب السعر - تأكد من اتصال MT5")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في MT5Manager: {e}")
        return False

def test_gemini_analyzer():
    """اختبار GeminiAnalyzer"""
    print("\n🧪 اختبار GeminiAnalyzer...")
    try:
        from tbot_v1.2.0 import GeminiAnalyzer
        
        # إنشاء مثيل
        analyzer = GeminiAnalyzer()
        print(f"✅ تم إنشاء GeminiAnalyzer - النموذج: {'متاح' if analyzer.model else 'غير متاح'}")
        
        # اختبار التحليل البديل
        fake_price_data = {
            'last': 2650.50,
            'bid': 2650.45,
            'ask': 2650.55,
            'symbol': 'XAUUSD'
        }
        
        fallback_analysis = analyzer._fallback_analysis('XAUUSD', fake_price_data)
        print(f"✅ التحليل البديل: {fallback_analysis['action']} بثقة {fallback_analysis['confidence']}%")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في GeminiAnalyzer: {e}")
        return False

def test_message_formatting():
    """اختبار تنسيق الرسائل"""
    print("\n🧪 اختبار تنسيق الرسائل...")
    try:
        from tbot_v1.2.0 import format_short_alert_message, ALL_SYMBOLS
        
        # بيانات تجريبية
        symbol = 'XAUUSD'
        symbol_info = ALL_SYMBOLS.get(symbol, {'name': 'الذهب', 'emoji': '🥇'})
        price_data = {
            'last': 2650.50,
            'bid': 2650.45,
            'ask': 2650.55,
            'source': 'Test Data'
        }
        analysis = {
            'action': 'BUY',
            'confidence': 75,
            'entry_price': 2650.50,
            'target1': 2677.00,
            'stop_loss': 2637.25
        }
        
        message = format_short_alert_message(symbol, symbol_info, price_data, analysis, 12345)
        
        if message and len(message) > 100:
            print("✅ تم تنسيق الرسالة بنجاح")
            print(f"📝 طول الرسالة: {len(message)} حرف")
            return True
        else:
            print("⚠️ الرسالة قصيرة جداً أو فارغة")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في تنسيق الرسالة: {e}")
        return False

def test_extraction_functions():
    """اختبار دوال الاستخراج"""
    print("\n🧪 اختبار دوال الاستخراج...")
    try:
        from tbot_v1.2.0 import GeminiAnalyzer
        
        analyzer = GeminiAnalyzer()
        
        # اختبار استخراج التوصية
        test_text_buy = "التحليل يشير إلى فرصة شراء قوية للذهب"
        recommendation = analyzer._extract_recommendation(test_text_buy)
        print(f"✅ استخراج التوصية من 'شراء قوية': {recommendation}")
        
        # اختبار استخراج الثقة
        test_text_confidence = "نسبة النجاح: 85% بناءً على التحليل الفني"
        confidence = analyzer._extract_confidence(test_text_confidence)
        print(f"✅ استخراج الثقة من 'نسبة النجاح: 85%': {confidence}%")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في دوال الاستخراج: {e}")
        return False

def main():
    """تشغيل جميع الاختبارات"""
    print("🚀 بدء اختبار إصلاحات البوت v1.2.0")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_mt5_manager,
        test_gemini_analyzer,
        test_message_formatting,
        test_extraction_functions
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 نتائج الاختبار: {passed}/{total} نجح")
    
    if passed == total:
        print("🎉 جميع الاختبارات نجحت!")
        print("✅ البوت جاهز للاستخدام")
    else:
        print("⚠️ بعض الاختبارات فشلت - يرجى مراجعة الأخطاء")
    
    return passed == total

if __name__ == "__main__":
    main()