#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مثال عملي لاستخدام pip_value_detector مع البوت v1.2.0

هذا المثال يوضح كيفية:
1. استخدام دوال pip_value_detector
2. التكامل مع البوت
3. حساب النقاط والأرباح
4. اختبار الأصول المختلفة
"""

# استيراد pip_value_detector
try:
    from pip_value_detector import (
        get_pip_value, 
        get_asset_category, 
        list_supported_assets, 
        calculate_points_from_price_difference
    )
    PIP_DETECTOR_AVAILABLE = True
    print("✅ تم تحميل pip_value_detector بنجاح")
except ImportError:
    PIP_DETECTOR_AVAILABLE = False
    print("❌ pip_value_detector غير متوفر")

def demonstrate_pip_value_detector():
    """عرض توضيحي لاستخدام pip_value_detector"""
    
    if not PIP_DETECTOR_AVAILABLE:
        print("⚠️ لا يمكن تشغيل العرض التوضيحي - pip_value_detector غير متوفر")
        return
    
    print("=" * 80)
    print("🧪 عرض توضيحي لاستخدام pip_value_detector مع البوت v1.2.0")
    print("=" * 80)
    
    # 1. عرض جميع الأصول المدعومة
    print("\n📋 الأصول المدعومة:")
    supported_assets = list_supported_assets()
    
    for category, assets in supported_assets.items():
        print(f"\n🔹 {category.upper()}:")
        for asset, pip_value in assets.items():
            category_name = get_asset_category(asset)
            print(f"   {asset}: {pip_value} نقطة ({category_name})")
    
    # 2. أمثلة عملية لحساب النقاط
    print("\n" + "=" * 80)
    print("💡 أمثلة عملية لحساب النقاط")
    print("=" * 80)
    
    examples = [
        # (رمز الأصل, فرق السعر, الوصف)
        ("EURUSD", 0.0050, "حركة 50 نقطة في اليورو/دولار"),
        ("USDJPY", 1.00, "حركة 100 نقطة في الدولار/ين"),
        ("XAUUSD", 10.00, "حركة 1000 نقطة في الذهب"),
        ("BTCUSD", 500.0, "حركة 500 نقطة في البيتكوين"),
        ("ETHUSD", 25.0, "حركة 250 نقطة في الإيثريوم"),
        ("XRPUSD", 0.0100, "حركة 100 نقطة في الريبل"),
    ]
    
    for asset, price_diff, description in examples:
        try:
            # حساب النقاط
            points = calculate_points_from_price_difference(price_diff, asset)
            
            # جلب قيمة النقطة ونوع الأصل
            pip_value = get_pip_value(asset)
            category = get_asset_category(asset)
            
            print(f"\n📊 {asset} ({category}):")
            print(f"   📈 {description}")
            print(f"   💰 فرق السعر: {price_diff}")
            print(f"   🎯 عدد النقاط: {points:.0f} نقطة")
            print(f"   💎 قيمة النقطة: {pip_value}")
            print(f"   ✅ التحقق: {price_diff} ÷ {pip_value} = {points:.0f}")
            
        except Exception as e:
            print(f"   ❌ خطأ في {asset}: {e}")

def simulate_bot_integration():
    """محاكاة التكامل مع البوت"""
    
    if not PIP_DETECTOR_AVAILABLE:
        return
    
    print("\n" + "=" * 80)
    print("🤖 محاكاة التكامل مع البوت v1.2.0")
    print("=" * 80)
    
    # محاكاة بيانات من MetaTrader5
    sample_price_data = {
        "EURUSD": {"last": 1.0850, "bid": 1.0849, "ask": 1.0851, "spread": 0.0002},
        "XAUUSD": {"last": 2020.50, "bid": 2020.30, "ask": 2020.70, "spread": 0.40},
        "BTCUSD": {"last": 45000.0, "bid": 44990.0, "ask": 45010.0, "spread": 20.0}
    }
    
    # محاكاة تحليل من Gemini AI
    sample_analysis = {
        "EURUSD": {"action": "BUY", "confidence": 75, "entry_price": 1.0850},
        "XAUUSD": {"action": "SELL", "confidence": 68, "entry_price": 2020.50},
        "BTCUSD": {"action": "HOLD", "confidence": 45, "entry_price": 45000.0}
    }
    
    for symbol in sample_price_data.keys():
        print(f"\n🔍 تحليل {symbol}:")
        
        # جلب البيانات
        price_data = sample_price_data[symbol]
        analysis = sample_analysis[symbol]
        current_price = price_data["last"]
        
        # استخدام pip_value_detector
        try:
            pip_value = get_pip_value(symbol)
            category = get_asset_category(symbol)
            
            print(f"   📊 السعر الحالي: {current_price}")
            print(f"   🏷️ فئة الأصل: {category}")
            print(f"   💎 قيمة النقطة: {pip_value}")
            print(f"   🎯 توصية AI: {analysis['action']}")
            print(f"   ✅ ثقة AI: {analysis['confidence']}%")
            
            # حساب أهداف افتراضية
            if analysis['action'] == 'BUY':
                target1_price = current_price + (20 * pip_value)  # 20 نقطة
                target2_price = current_price + (40 * pip_value)  # 40 نقطة
                stop_loss_price = current_price - (15 * pip_value)  # 15 نقطة
            elif analysis['action'] == 'SELL':
                target1_price = current_price - (20 * pip_value)
                target2_price = current_price - (40 * pip_value)
                stop_loss_price = current_price + (15 * pip_value)
            else:
                target1_price = target2_price = stop_loss_price = current_price
            
            # حساب النقاط
            if analysis['action'] != 'HOLD':
                points1 = calculate_points_from_price_difference(abs(target1_price - current_price), symbol)
                points2 = calculate_points_from_price_difference(abs(target2_price - current_price), symbol)
                stop_points = calculate_points_from_price_difference(abs(stop_loss_price - current_price), symbol)
                
                print(f"   🎯 الهدف الأول: {target1_price:.5f} ({points1:.0f} نقطة)")
                print(f"   🎯 الهدف الثاني: {target2_price:.5f} ({points2:.0f} نقطة)")
                print(f"   🛑 وقف الخسارة: {stop_loss_price:.5f} ({stop_points:.0f} نقطة)")
                
                if stop_points > 0:
                    risk_reward = points1 / stop_points
                    print(f"   📊 نسبة المخاطرة/المكافأة: 1:{risk_reward:.2f}")
            
        except Exception as e:
            print(f"   ❌ خطأ في معالجة {symbol}: {e}")

def test_integration_with_bot_functions():
    """اختبار التكامل مع دوال البوت"""
    
    print("\n" + "=" * 80)
    print("🔬 اختبار التكامل مع دوال البوت")
    print("=" * 80)
    
    # محاكاة دوال البوت
    def mock_get_user_capital(user_id):
        """محاكاة دالة جلب رأس المال"""
        return 10000  # 10,000 دولار
    
    def mock_format_time_for_user(user_id):
        """محاكاة دالة تنسيق الوقت"""
        from datetime import datetime
        return f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (التوقيت المحلي)"
    
    # اختبار مع رموز مختلفة
    test_symbols = ["EURUSD", "XAUUSD", "BTCUSD"]
    
    for symbol in test_symbols:
        if not PIP_DETECTOR_AVAILABLE:
            print(f"⚠️ تخطي {symbol} - pip_value_detector غير متوفر")
            continue
            
        try:
            print(f"\n🧪 اختبار {symbol}:")
            
            # بيانات وهمية
            current_price = 1.0850 if symbol == "EURUSD" else 2020.50 if symbol == "XAUUSD" else 45000.0
            price_diff = 0.0050 if symbol == "EURUSD" else 10.0 if symbol == "XAUUSD" else 500.0
            
            # استخدام pip_value_detector
            pip_value = get_pip_value(symbol)
            category = get_asset_category(symbol)
            points = calculate_points_from_price_difference(price_diff, symbol)
            
            # محاكاة إعدادات المستخدم
            user_capital = mock_get_user_capital(12345)
            formatted_time = mock_format_time_for_user(12345)
            
            print(f"   💰 السعر: {current_price}")
            print(f"   📊 فرق السعر: {price_diff}")
            print(f"   🎯 النقاط: {points:.0f}")
            print(f"   💎 قيمة النقطة: {pip_value}")
            print(f"   🏷️ فئة الأصل: {category}")
            print(f"   💳 رأس المال: ${user_capital:,}")
            print(f"   ⏰ الوقت: {formatted_time}")
            
            # حساب الربح المحتمل
            potential_profit = points * pip_value * 0.01  # افتراض 0.01 لوت
            print(f"   💵 الربح المحتمل: ${potential_profit:.2f} (0.01 لوت)")
            
        except Exception as e:
            print(f"   ❌ خطأ في {symbol}: {e}")

if __name__ == "__main__":
    # تشغيل جميع الأمثلة
    demonstrate_pip_value_detector()
    simulate_bot_integration()
    test_integration_with_bot_functions()
    
    print("\n" + "=" * 80)
    print("✅ انتهى العرض التوضيحي")
    print("=" * 80)
    print("\n💡 لاستخدام pip_value_detector مع البوت:")
    print("1. تأكد من وجود pip_value_detector.py في نفس المجلد")
    print("2. قم بتشغيل البوت - سيتم التكامل تلقائياً")
    print("3. في حالة عدم وجود الملف، سيعمل البوت بالنظام القديم")
    print("4. استخدم test_pip_values() لاختبار التكامل")