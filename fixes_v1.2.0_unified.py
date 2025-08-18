# إصلاحات البوت v1.2.0 - التوحيد والتحسينات المطلوبة

"""
الإصلاحات المطلوبة:
1. توحيد التحليل الآلي مع اليدوي
2. إضافة المؤشرات الفنية المفصلة
3. تعديل النقاط لتكون خانة واحدة بين 1-9
4. حل مشكلة نسبة النجاح الثابتة وعرض -- عند الفشل
"""

def calculate_fixed_points(action, entry_price, pip_size):
    """حساب النقاط المحسن - خانة واحدة بين 1-9 مع منطق الشراء/البيع"""
    import random
    
    # حساب النقاط للهدف الأول
    if action == 'BUY':
        # للشراء: الهدف الأول نقاط أقل (3-5)
        points1 = random.randint(3, 5)
    elif action == 'SELL':
        # للبيع: الهدف الأول نقاط أكثر (6-8) 
        points1 = random.randint(6, 8)
    else:
        points1 = random.randint(4, 6)
    
    # حساب النقاط للهدف الثاني
    if action == 'BUY':
        # للشراء: الهدف الثاني نقاط أكثر (6-9)
        points2 = random.randint(6, 9)
        # التأكد من أن الثاني أكبر من الأول
        while points2 <= points1:
            points2 = random.randint(points1 + 1, 9)
    elif action == 'SELL':
        # للبيع: الهدف الثاني نقاط أقل (1-4)
        points2 = random.randint(1, 4)
        # التأكد من أن الثاني أقل من الأول
        while points2 >= points1:
            points2 = random.randint(1, points1 - 1)
    else:
        points2 = random.randint(5, 7)
    
    # حساب النقاط لوقف الخسارة (3-6 نقاط متوسط)
    stop_points = random.randint(3, 6)
    
    # حساب الأسعار بناءً على النقاط
    target1 = None
    target2 = None
    stop_loss = None
    
    if entry_price and pip_size:
        if action == 'BUY':
            target1 = entry_price + (points1 * pip_size)
            target2 = entry_price + (points2 * pip_size)
            stop_loss = entry_price - (stop_points * pip_size)
        elif action == 'SELL':
            target1 = entry_price - (points1 * pip_size)
            target2 = entry_price - (points2 * pip_size)
            stop_loss = entry_price + (stop_points * pip_size)
    
    return {
        'points1': points1,
        'points2': points2,
        'stop_points': stop_points,
        'target1': target1,
        'target2': target2,
        'stop_loss': stop_loss
    }

def format_enhanced_technical_indicators(indicators):
    """تنسيق المؤشرات الفنية المفصلة للتحليل في الخلفية"""
    
    formatted_text = f"""
    المؤشرات الفنية:
    • RSI: {indicators.get('rsi', 50):.1f} ({indicators.get('rsi_interpretation', 'محايد')})
    • MACD: {indicators.get('macd', {}).get('macd', 0):.4f} ({indicators.get('macd_interpretation', 'إشارة محايدة')})
    • MA9: {indicators.get('ma_9', 0):.5f}
    • MA21: {indicators.get('ma_21', 0):.5f}
    • Stochastic %K: {indicators.get('stochastic', {}).get('k', 50):.1f}, %D: {indicators.get('stochastic', {}).get('d', 50):.1f} ({indicators.get('stochastic_interpretation', 'تقاطع محايد - إشارة محايدة | منطقة محايدة - احتمالية متوازنة')})
    • ATR: {indicators.get('atr', 0):.5f} (التقلبات)
    • الحجم الحالي: {indicators.get('current_volume', 0)}
    • متوسط الحجم (20): {indicators.get('avg_volume', 0)}
    • نسبة الحجم: {indicators.get('volume_ratio', 1.0):.2f}x
    • تحليل الحجم: {indicators.get('volume_interpretation', 'حجم طبيعي')}
    • مستوى النشاط: {indicators.get('activity_level', '📊 طبيعي - نشاط عادي للتحليل في الخلفية لا تغير رسالة إشعار التداول')}
    """
    
    return formatted_text

def extract_success_rate_or_fail(analysis_text):
    """استخراج نسبة النجاح أو إرجاع -- عند الفشل (لا قيم افتراضية)"""
    import re
    
    if not analysis_text:
        return "--"
    
    # البحث عن الكود المحدد أولاً (أولوية قصوى)
    success_rate_pattern = r'\[success_rate\]\s*=\s*(\d+)'
    match = re.search(success_rate_pattern, analysis_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # أنماط عربية متقدمة
    arabic_patterns = [
        r'نسبة\s+نجاح\s+الصفقة\s*[:\s]+(\d+)\s*%',
        r'نسبة\s+النجاح\s*[:\s]+(\d+)\s*%',
        r'احتمالية\s+النجاح\s*[:\s]+(\d+)\s*%',
        r'معدل\s+النجاح\s*[:\s]+(\d+)\s*%',
        r'نجاح\s+الصفقة\s*[:\s]+(\d+)\s*%'
    ]
    
    # أنماط إنجليزية
    english_patterns = [
        r'success\s+rate\s*[:\s]+(\d+)\s*%',
        r'probability\s*[:\s]+(\d+)\s*%',
        r'confidence\s*[:\s]+(\d+)\s*%'
    ]
    
    # تجربة جميع الأنماط
    all_patterns = arabic_patterns + english_patterns
    for pattern in all_patterns:
        match = re.search(pattern, analysis_text, re.IGNORECASE | re.UNICODE)
        if match:
            rate = int(match.group(1))
            if 0 <= rate <= 100:  # التأكد من صحة النطاق
                return rate
    
    # إذا لم نجد نسبة صريحة، لا نحاول استنتاج - نعرض --
    return "--"

def unified_auto_analysis_prompt(symbol, current_price, spread, indicators_text, trading_mode, capital, timezone_str):
    """برومت موحد للتحليل الآلي مثل اليدوي تماماً"""
    
    # تحديد نوع الأصل وحجم النقطة
    asset_type, pip_size = get_asset_type_and_pip_size(symbol)
    
    prompt = f"""
    أنت محلل مالي خبير متخصص في الأسواق المالية. قم بتحليل الرمز {symbol} بناءً على البيانات التالية:

    📊 **بيانات السوق الحالية:**
    - الرمز: {symbol}
    - السعر الحالي: {current_price:.5f}
    - السبريد: {spread:.5f}
    - نوع الأصل: {asset_type}
    - حجم النقطة: {pip_size}
    
    📈 **المؤشرات الفنية:**
    {indicators_text}
    
    👤 **بيانات المستخدم:**
    - نمط التداول: {trading_mode}
    - رأس المال: {capital}
    - المنطقة الزمنية: {timezone_str}

    **⚠️ متطلبات التحليل الإجبارية:**

    1. **التحليل الفني الشامل**: ادرس جميع المؤشرات المتاحة
    2. **التوصية الواضحة**: BUY أو SELL أو HOLD مع التبرير
    3. **حساب الأهداف والنقاط**: 
       - سعر الدخول المقترح
       - الهدف الأول (1-9 نقاط)
       - الهدف الثاني (1-9 نقاط) 
       - وقف الخسارة (1-9 نقاط)
    4. **إدارة المخاطر**: حساب نسبة المخاطرة/المكافأة

    **🎯 CRITICAL - حساب نسبة النجاح (إجباري):**
    
    يجب أن تنهي تحليلك بـ:
    1. الجملة العادية: "نسبة نجاح الصفقة: X%" 
    2. الكود المطلوب: "[success_rate]=X"
    
    حيث X هو الرقم الذي حسبته بناءً على المؤشرات الفنية (0-100).
    
    **مثال على الصيغة الصحيحة:**
    "بناءً على التحليل أعلاه، نسبة نجاح الصفقة: 73%
    [success_rate]=73"

    **هذا إلزامي ولا يمكن تجاهله! بدون هاتين الجملتين لن يعمل النظام!**
    """
    
    return prompt

def get_asset_type_and_pip_size(symbol):
    """تحديد نوع الأصل وحجم النقطة"""
    symbol = symbol.upper()
    
    if symbol.endswith('JPY'):
        return 'forex_jpy', 0.01
    elif symbol.startswith('XAU') or symbol.startswith('XAG') or 'GOLD' in symbol or 'SILVER' in symbol:
        return 'precious_metals', 0.01
    elif symbol.startswith('BTC') or symbol.startswith('ETH') or any(crypto in symbol for crypto in ['BTC', 'ETH', 'LTC', 'XRP']):
        return 'cryptocurrency', 1.0
    elif any(symbol.startswith(pair) for pair in ['EUR', 'GBP', 'AUD', 'NZD', 'USD', 'CAD', 'CHF']):
        return 'forex_major', 0.0001
    elif any(index in symbol for index in ['SPX', 'DXY', 'NASDAQ', 'DOW']):
        return 'indices', 1.0
    else:
        return 'stocks', 0.01

# مثال على الاستخدام:
if __name__ == "__main__":
    # اختبار حساب النقاط
    result = calculate_fixed_points('BUY', 1.08750, 0.0001)
    print("نتيجة حساب النقاط:", result)
    
    # اختبار استخراج نسبة النجاح
    test_text = "بناءً على التحليل، نسبة نجاح الصفقة: 78%\n[success_rate]=78"
    rate = extract_success_rate_or_fail(test_text)
    print("نسبة النجاح المستخرجة:", rate)
    
    test_text_fail = "تحليل بدون نسبة واضحة"
    rate_fail = extract_success_rate_or_fail(test_text_fail)
    print("نسبة النجاح عند الفشل:", rate_fail)