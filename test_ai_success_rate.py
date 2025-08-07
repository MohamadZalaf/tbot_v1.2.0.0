#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار استخراج نسبة النجاح من نص الذكاء الاصطناعي
"""

import re

def _extract_success_rate_from_ai(text: str) -> float:
    """استخراج نسبة النجاح المحددة من الذكاء الاصطناعي"""
    try:
        # البحث عن نص "نسبة نجاح الصفقة" متبوعاً برقم ونسبة مئوية
        patterns = [
            r'نسبة نجاح الصفقة:?\s*(\d+)%',
            r'نسبة النجاح:?\s*(\d+)%',
            r'احتمالية النجاح:?\s*(\d+)%',
            r'معدل النجاح:?\s*(\d+)%',
            r'success rate:?\s*(\d+)%',
            r'نسبة\s+نجاح\s+(?:الصفقة|التداول):?\s*(\d+)%',
            # البحث في نهاية النص
            r'النسبة:?\s*(\d+)%',
            r'التوقع:?\s*(\d+)%'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
            if matches:
                success_rate = float(matches[-1])  # أخذ آخر نتيجة
                # التأكد من أن النسبة في النطاق المطلوب
                if 10 <= success_rate <= 95:
                    print(f"✅ تم استخراج نسبة نجاح من AI: {success_rate}%")
                    return success_rate
        
        # البحث عن أرقام في نهاية النص (آخر 200 حرف)
        text_end = text[-200:].lower()
        numbers_at_end = re.findall(r'(\d+)%', text_end)
        
        for num_str in reversed(numbers_at_end):  # البدء من النهاية
            num = float(num_str)
            if 10 <= num <= 95:
                print(f"✅ تم استخراج نسبة من نهاية النص: {num}%")
                return num
        
        # إذا لم نجد شيئاً محدداً
        return None
        
    except Exception as e:
        print(f"❌ خطأ في استخراج نسبة النجاح من AI: {e}")
        return None

# أمثلة للاختبار
test_examples = [
    """
    بناءً على التحليل الفني الشامل:
    - RSI في منطقة جيدة (65)
    - MACD إيجابي وفوق الإشارة
    - حجم تداول عالي
    - الاتجاه العام صاعد
    
    التوصية: شراء
    نسبة نجاح الصفقة: 78%
    """,
    
    """
    التحليل يشير إلى فرصة بيع قوية:
    • المؤشرات تدعم الهبوط
    • مستوى مقاومة قوي
    • أخبار سلبية متوقعة
    
    معدل النجاح: 85%
    """,
    
    """
    تحليل متحفظ للزوج:
    - إشارات متضاربة
    - تقلبات عالية
    - عدم وضوح الاتجاه
    
    احتمالية النجاح: 45%
    """,
    
    """
    Strong bullish signal detected.
    Technical indicators align perfectly.
    Success rate: 82%
    """
]

print("🧪 اختبار استخراج نسبة النجاح من نصوص الذكاء الاصطناعي\n")
print("=" * 60)

for i, example in enumerate(test_examples, 1):
    print(f"\n📝 مثال {i}:")
    print("-" * 40)
    success_rate = _extract_success_rate_from_ai(example)
    if success_rate:
        print(f"✅ النتيجة: {success_rate}%")
    else:
        print("❌ لم يتم العثور على نسبة نجاح صحيحة")
    print()

print("=" * 60)
print("📊 ملخص: النظام الجديد يستخرج نسبة النجاح من تحليل Gemini AI")
print("🎯 هذا يعني أن كل تحليل سيحصل على نسبة نجاح مخصصة ومحسوبة!")