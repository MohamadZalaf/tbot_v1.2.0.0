#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pip_value_detector.py

نظام كشف وحساب قيم النقاط للأصول المالية المختلفة
يدعم أزواج العملات، المعادن الثمينة، والعملات الرقمية
حسب النظام المتبع في التداول

تم إنشاؤه لبوت التداول المتقدم v1.2.0
"""

def get_pip_value(asset_name: str) -> float:
    """
    Returns the pip value for a given asset name.
    Supports forex pairs, metals, and cryptocurrencies.
    
    Args:
        asset_name (str): اسم الأصل المالي (مثل: EURUSD, XAUUSD, BTCUSD)
    
    Returns:
        float: قيمة النقطة للأصل المحدد
    
    Raises:
        ValueError: إذا كان الأصل غير معروف أو غير مدعوم
    """

    asset_name = asset_name.strip().upper().replace('/', '')

    # 💱 أزواج العملات
    forex_pips = {
        "EURUSD": 0.0001,   # يورو/دولار
        "USDJPY": 0.01,     # دولار/ين
        "USDGBP": 0.0001,   # دولار/جنيه
        "GBPUSD": 0.0001,   # جنيه/دولار
        "AUDUSD": 0.0001,   # دولار أسترالي/دولار
        "USDCAD": 0.0001,   # دولار/دولار كندي
        "USDCHF": 0.0001,   # دولار/فرنك سويسري
        "NZDUSD": 0.0001,   # دولار نيوزيلندي/دولار
        "EURGBP": 0.0001,   # يورو/جنيه
        "EURJPY": 0.01,     # يورو/ين
        "GBPJPY": 0.01      # جنيه/ين
    }

    # 🪙 المعادن الثمينة
    metals_pips = {
        "XAUUSD": 0.01,  # ذهب
        "XAGUSD": 0.01,  # فضة
        "XPTUSD": 0.01,  # بلاتين
        "XPDUSD": 0.01   # بلاديوم
    }

    # ₿ العملات الرقمية
    crypto_pips = {
        "BTCUSD": 1.00,     # بيتكوين - كل 1 دولار = نقطة واحدة
        "ETHUSD": 0.10,     # إيثريوم - كل 0.10 دولار = نقطة واحدة
        "BNBUSD": 0.01,     # بينانس كوين
        "XRPUSD": 0.0001,   # ريبل - عملة منخفضة السعر
        "ADAUSD": 0.0001,   # كاردانو
        "SOLUSD": 0.01,     # سولانا
        "DOTUSD": 0.01,     # بولكادوت
        "DOGEUSD": 0.0001,  # دوجكوين
        "AVAXUSD": 0.01,    # أفالانش
        "LINKUSD": 0.01,    # تشين لينك
        "LTCUSD": 0.10,     # لايتكوين
        "BCHUSD": 0.10      # بيتكوين كاش
    }

    # دمج جميع الأصول
    all_assets = {**forex_pips, **metals_pips, **crypto_pips}

    # التحقق من الأصل
    if asset_name in all_assets:
        return all_assets[asset_name]
    else:
        raise ValueError(f"الأصل '{asset_name}' غير معروف أو غير مدعوم حالياً.")


def get_asset_category(asset_name: str) -> str:
    """
    تحديد فئة الأصل المالي
    
    Args:
        asset_name (str): اسم الأصل المالي
    
    Returns:
        str: فئة الأصل (forex, metals, crypto)
    """
    asset_name = asset_name.strip().upper().replace('/', '')
    
    # التحقق من الفئة
    forex_pairs = ["EURUSD", "USDJPY", "USDGBP", "GBPUSD", "AUDUSD", 
                   "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY"]
    
    metals = ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"]
    
    crypto = ["BTCUSD", "ETHUSD", "BNBUSD", "XRPUSD", "ADAUSD", "SOLUSD",
              "DOTUSD", "DOGEUSD", "AVAXUSD", "LINKUSD", "LTCUSD", "BCHUSD"]
    
    if asset_name in forex_pairs:
        return "forex"
    elif asset_name in metals:
        return "metals"
    elif asset_name in crypto:
        return "crypto"
    else:
        return "unknown"


def list_supported_assets() -> dict:
    """
    عرض جميع الأصول المدعومة مع قيم النقاط
    
    Returns:
        dict: قاموس بجميع الأصول المدعومة وقيم النقاط
    """
    return {
        "forex": {
            "EURUSD": 0.0001, "USDJPY": 0.01, "USDGBP": 0.0001, "GBPUSD": 0.0001,
            "AUDUSD": 0.0001, "USDCAD": 0.0001, "USDCHF": 0.0001, "NZDUSD": 0.0001,
            "EURGBP": 0.0001, "EURJPY": 0.01, "GBPJPY": 0.01
        },
        "metals": {
            "XAUUSD": 0.01, "XAGUSD": 0.01, "XPTUSD": 0.01, "XPDUSD": 0.01
        },
        "crypto": {
            "BTCUSD": 1.00, "ETHUSD": 0.10, "BNBUSD": 0.01, "XRPUSD": 0.0001,
            "ADAUSD": 0.0001, "SOLUSD": 0.01, "DOTUSD": 0.01, "DOGEUSD": 0.0001,
            "AVAXUSD": 0.01, "LINKUSD": 0.01, "LTCUSD": 0.10, "BCHUSD": 0.10
        }
    }


def calculate_points_from_price_difference(price_diff: float, asset_name: str) -> float:
    """
    حساب عدد النقاط من فرق السعر
    
    Args:
        price_diff (float): فرق السعر
        asset_name (str): اسم الأصل المالي
    
    Returns:
        float: عدد النقاط
    """
    try:
        pip_value = get_pip_value(asset_name)
        if pip_value > 0:
            return abs(price_diff) / pip_value
        else:
            return 0
    except ValueError:
        return 0


# مثال استخدام ودالة اختبار
def test_pip_detector():
    """اختبار شامل لنظام كشف النقاط"""
    print("=" * 60)
    print("🧪 اختبار نظام كشف قيم النقاط")
    print("=" * 60)
    
    # اختبار الأصول المختلفة
    test_assets = [
        "EURUSD", "USDJPY", "XAUUSD", "BTCUSD", "ETHUSD", 
        "XRPUSD", "DOGEUSD", "XAGUSD", "GBPJPY"
    ]
    
    for asset in test_assets:
        try:
            pip_value = get_pip_value(asset)
            category = get_asset_category(asset)
            print(f"✅ {asset}: {pip_value} ({category})")
        except ValueError as e:
            print(f"❌ {asset}: {e}")
    
    print("\n" + "=" * 60)
    print("📊 اختبار حساب النقاط من فرق السعر")
    print("=" * 60)
    
    # اختبار حساب النقاط
    test_calculations = [
        ("EURUSD", 0.0050),  # 50 نقطة
        ("USDJPY", 1.00),    # 100 نقطة
        ("XAUUSD", 5.00),    # 500 نقطة
        ("BTCUSD", 1000.0),  # 1000 نقطة
        ("ETHUSD", 50.0)     # 500 نقطة
    ]
    
    for asset, price_diff in test_calculations:
        points = calculate_points_from_price_difference(price_diff, asset)
        print(f"📈 {asset}: فرق السعر {price_diff} = {points:.0f} نقطة")


if __name__ == "__main__":
    # تشغيل الاختبار
    test_pip_detector()
    
    print("\n" + "=" * 60)
    print("🔍 مثال على الاستخدام:")
    print("=" * 60)
    
    try:
        # مثال عملي
        asset = "XAUUSD"
        pip_value = get_pip_value(asset)
        category = get_asset_category(asset)
        
        print(f"الأصل: {asset}")
        print(f"قيمة النقطة: {pip_value}")
        print(f"الفئة: {category}")
        
        # حساب النقاط من فرق سعري
        price_difference = 10.50  # مثال: فرق 10.50 دولار في الذهب
        points = calculate_points_from_price_difference(price_difference, asset)
        print(f"فرق السعر {price_difference} دولار = {points:.0f} نقطة")
        
    except ValueError as e:
        print(f"خطأ: {e}")