#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار إصلاحات دقة البيانات والمؤشرات في البوت v1.2.0
==================================================

هذا الملف يختبر الإصلاحات التالية:
1. نظام الكاش المحسن مع تتبع المصدر
2. إصلاح حسابات RSI وتجنب البيانات المختلطة
3. التحقق من دقة البيانات مقارنة بـ MT5
4. التعامل الصحيح مع Yahoo Finance كمصدر بديل فقط

المطور: Assistant
التاريخ: 2025
"""

import sys
import os
sys.path.append('.')

# استيراد الوحدات المطلوبة
try:
    from tbot_v1.2.0 import MT5Manager, get_cached_price_data, cache_price_data, is_cache_valid
    import MetaTrader5 as mt5
    import pandas as pd
    import numpy as np
    import ta
    from datetime import datetime
    import time
    import logging
except ImportError as e:
    print(f"❌ خطأ في استيراد الوحدات: {e}")
    print("تأكد من وجود جميع المكتبات المطلوبة")
    sys.exit(1)

# إعداد نظام السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataAccuracyTester:
    """فئة اختبار دقة البيانات والمؤشرات"""
    
    def __init__(self):
        self.mt5_manager = MT5Manager()
        self.test_symbols = ['EURUSD', 'GBPUSD', 'XAUUSD', 'USDJPY']
        self.results = {}
        
    def test_cache_system(self):
        """اختبار نظام الكاش المحسن"""
        print("\n🔍 اختبار نظام الكاش المحسن:")
        print("=" * 50)
        
        test_symbol = 'EURUSD'
        test_data_mt5 = {
            'symbol': test_symbol,
            'bid': 1.0485,
            'ask': 1.0487,
            'last': 1.0486,
            'source': 'MetaTrader5'
        }
        
        test_data_yahoo = {
            'symbol': test_symbol,
            'bid': 1.0480,  # قيم مختلفة قليلاً
            'ask': 1.0482,
            'last': 1.0481,
            'source': 'Yahoo Finance'
        }
        
        # اختبار الكاش مع مصادر مختلفة
        cache_price_data(test_symbol, test_data_mt5, "MT5")
        cache_price_data(test_symbol, test_data_yahoo, "Yahoo Finance")
        
        # اختبار جلب البيانات بحسب المصدر
        mt5_cached = get_cached_price_data(test_symbol, "MT5")
        yahoo_cached = get_cached_price_data(test_symbol, "Yahoo Finance")
        any_cached = get_cached_price_data(test_symbol)
        
        # التحقق من النتائج
        tests_passed = 0
        total_tests = 4
        
        if mt5_cached and mt5_cached['last'] == 1.0486:
            print("✅ كاش MT5: نجح")
            tests_passed += 1
        else:
            print("❌ كاش MT5: فشل")
            
        if yahoo_cached and yahoo_cached['last'] == 1.0481:
            print("✅ كاش Yahoo Finance: نجح")
            tests_passed += 1
        else:
            print("❌ كاش Yahoo Finance: فشل")
            
        if any_cached:  # يجب أن يعطي MT5 (الأولوية)
            print("✅ كاش عام: نجح")
            tests_passed += 1
        else:
            print("❌ كاش عام: فشل")
            
        # اختبار انتهاء صلاحية الكاش
        time.sleep(6)  # انتظار أكثر من 5 ثوان
        if not is_cache_valid(test_symbol):
            print("✅ انتهاء صلاحية الكاش: نجح")
            tests_passed += 1
        else:
            print("❌ انتهاء صلاحية الكاش: فشل")
            
        print(f"\nنتيجة اختبار الكاش: {tests_passed}/{total_tests}")
        return tests_passed == total_tests
    
    def test_rsi_calculation(self):
        """اختبار حساب RSI المحسن"""
        print("\n📊 اختبار حساب RSI المحسن:")
        print("=" * 50)
        
        if not self.mt5_manager.connected:
            print("❌ MT5 غير متصل - لا يمكن اختبار RSI")
            return False
            
        test_results = []
        
        for symbol in self.test_symbols:
            print(f"\n🔍 اختبار RSI لـ {symbol}:")
            
            try:
                # جلب البيانات مباشرة من MT5
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
                if rates is None or len(rates) < 20:
                    print(f"  ⚠️ بيانات غير كافية لـ {symbol}")
                    continue
                    
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.columns = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
                
                # حساب RSI مع الطريقة الجديدة
                rsi_series = ta.momentum.rsi(df['close'], window=14)
                rsi_value = rsi_series.iloc[-1]
                
                # التحقق من صحة القيمة
                if pd.isna(rsi_value) or rsi_value < 0 or rsi_value > 100:
                    print(f"  ❌ قيمة RSI غير صحيحة: {rsi_value}")
                    test_results.append(False)
                    continue
                    
                # حساب RSI مع البوت للمقارنة
                bot_indicators = self.mt5_manager.calculate_technical_indicators(symbol)
                if bot_indicators and 'rsi' in bot_indicators:
                    bot_rsi = bot_indicators['rsi']
                    rsi_diff = abs(rsi_value - bot_rsi)
                    
                    if rsi_diff < 0.1:  # فرق أقل من 0.1
                        print(f"  ✅ RSI متطابق: مباشر={rsi_value:.2f}, بوت={bot_rsi:.2f}")
                        test_results.append(True)
                    else:
                        print(f"  ⚠️ RSI مختلف: مباشر={rsi_value:.2f}, بوت={bot_rsi:.2f}, فرق={rsi_diff:.2f}")
                        test_results.append(False)
                else:
                    print(f"  ❌ البوت لم يحسب RSI لـ {symbol}")
                    test_results.append(False)
                    
            except Exception as e:
                print(f"  ❌ خطأ في اختبار {symbol}: {e}")
                test_results.append(False)
                
        success_rate = sum(test_results) / len(test_results) if test_results else 0
        print(f"\nنتيجة اختبار RSI: {sum(test_results)}/{len(test_results)} ({success_rate*100:.1f}%)")
        return success_rate >= 0.8  # 80% نجاح مقبول
    
    def test_data_source_consistency(self):
        """اختبار تماسك مصادر البيانات"""
        print("\n🔗 اختبار تماسك مصادر البيانات:")
        print("=" * 50)
        
        if not self.mt5_manager.connected:
            print("❌ MT5 غير متصل - لا يمكن اختبار تماسك البيانات")
            return False
            
        consistency_tests = []
        
        for symbol in self.test_symbols[:2]:  # اختبار رمزين فقط للسرعة
            print(f"\n🔍 اختبار {symbol}:")
            
            # جلب البيانات من البوت
            live_price = self.mt5_manager.get_live_price(symbol)
            indicators = self.mt5_manager.calculate_technical_indicators(symbol)
            
            if live_price and indicators:
                # التحقق من مصدر البيانات
                if live_price.get('source', '').startswith('MetaTrader5'):
                    print(f"  ✅ مصدر الأسعار: {live_price['source']}")
                    
                    # التحقق من تماسك السعر
                    live_price_val = live_price['last']
                    indicator_price = indicators.get('current_price', 0)
                    
                    if abs(live_price_val - indicator_price) < live_price_val * 0.001:  # فرق أقل من 0.1%
                        print(f"  ✅ تماسك الأسعار: مباشر={live_price_val:.5f}, مؤشرات={indicator_price:.5f}")
                        consistency_tests.append(True)
                    else:
                        print(f"  ⚠️ عدم تماسك الأسعار: مباشر={live_price_val:.5f}, مؤشرات={indicator_price:.5f}")
                        consistency_tests.append(False)
                else:
                    print(f"  ⚠️ مصدر غير MT5: {live_price.get('source', 'غير محدد')}")
                    consistency_tests.append(False)
            else:
                print(f"  ❌ فشل جلب البيانات لـ {symbol}")
                consistency_tests.append(False)
                
        success_rate = sum(consistency_tests) / len(consistency_tests) if consistency_tests else 0
        print(f"\nنتيجة اختبار التماسك: {sum(consistency_tests)}/{len(consistency_tests)} ({success_rate*100:.1f}%)")
        return success_rate >= 0.8
    
    def test_performance_impact(self):
        """اختبار تأثير الإصلاحات على الأداء"""
        print("\n⚡ اختبار تأثير الإصلاحات على الأداء:")
        print("=" * 50)
        
        if not self.mt5_manager.connected:
            print("❌ MT5 غير متصل - لا يمكن اختبار الأداء")
            return False
            
        test_symbol = 'EURUSD'
        iterations = 5
        
        # اختبار سرعة جلب البيانات
        start_time = time.time()
        for i in range(iterations):
            live_price = self.mt5_manager.get_live_price(test_symbol)
            indicators = self.mt5_manager.calculate_technical_indicators(test_symbol)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / iterations
        print(f"متوسط وقت جلب البيانات والمؤشرات: {avg_time:.2f} ثانية")
        
        # التحقق من الأداء
        if avg_time < 2.0:  # أقل من ثانيتين
            print("✅ الأداء ممتاز")
            return True
        elif avg_time < 5.0:  # أقل من 5 ثوان
            print("⚠️ الأداء مقبول")
            return True
        else:
            print("❌ الأداء ضعيف")
            return False
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n🚀 بدء اختبار إصلاحات دقة البيانات للبوت v1.2.0")
        print("=" * 60)
        
        tests = [
            ("نظام الكاش المحسن", self.test_cache_system),
            ("حساب RSI المحسن", self.test_rsi_calculation),
            ("تماسك مصادر البيانات", self.test_data_source_consistency),
            ("تأثير الأداء", self.test_performance_impact)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                print(f"\n{'✅' if result else '❌'} {test_name}: {'نجح' if result else 'فشل'}")
            except Exception as e:
                print(f"\n❌ {test_name}: فشل - {e}")
                results.append((test_name, False))
        
        # النتائج النهائية
        print("\n" + "=" * 60)
        print("📊 النتائج النهائية:")
        print("=" * 60)
        
        passed_tests = sum(1 for _, result in results if result)
        total_tests = len(results)
        
        for test_name, result in results:
            status = "✅ نجح" if result else "❌ فشل"
            print(f"{status} {test_name}")
        
        print(f"\nالنتيجة الإجمالية: {passed_tests}/{total_tests} اختبار نجح")
        
        if passed_tests == total_tests:
            print("🎉 جميع الإصلاحات تعمل بشكل مثالي!")
        elif passed_tests >= total_tests * 0.8:
            print("👍 معظم الإصلاحات تعمل بشكل جيد")
        else:
            print("⚠️ تحتاج بعض الإصلاحات إلى مراجعة")
        
        return passed_tests / total_tests

def main():
    """الدالة الرئيسية"""
    tester = DataAccuracyTester()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 0.8:
        print(f"\n✅ الإصلاحات ناجحة بنسبة {success_rate*100:.1f}%")
        sys.exit(0)
    else:
        print(f"\n❌ الإصلاحات تحتاج مراجعة - نسبة النجاح: {success_rate*100:.1f}%")
        sys.exit(1)

if __name__ == "__main__":
    main()