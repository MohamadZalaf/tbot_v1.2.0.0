#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار تدفق الإشعارات الآلية للمراقبة
"""

import random
from datetime import datetime

def simulate_ai_analysis_failure():
    """محاكاة فشل تحليل الذكاء الاصطناعي"""
    print("🤖 محاكاة سيناريو فشل تحليل AI")
    print("=" * 40)
    
    # هذا ما يحدث عند فشل تحليل Gemini AI
    fresh_analysis = None  # فشل في التحليل
    
    # التحليل الاحتياطي (كما في السطر 8015-8024 من الكود الأصلي)
    success_rate = 34.0  # قيمة افتراضية محتملة
    
    analysis = {
        'action': 'BUY',
        'confidence': success_rate,
        'reasoning': [f'إشعار تداول آلي للرمز EURUSD'],
        'ai_analysis': f'إشعار تداول آلي - نسبة النجاح {success_rate:.1f}%',
        'source': 'MT5 + Gemini AI',
        'symbol': 'EURUSD',
        'timestamp': datetime.now(),
        'price_data': {'last': 1.0500}
    }
    
    print(f"النتيجة: {success_rate}%")
    print(f"التحليل الاحتياطي: {analysis}")
    
    return analysis

def simulate_confidence_extraction_issue():
    """محاكاة مشكلة في استخراج نسبة الثقة من AI"""
    print("\n🔍 محاكاة مشكلة استخراج نسبة الثقة")
    print("=" * 40)
    
    # نص تحليل AI قد يحتوي على مشاكل
    ai_texts = [
        "تحليل فني للزوج مع إشارة متوسطة",  # لا يحتوي على نسبة
        "الاتجاه العام إيجابي ولكن هناك مخاطر",  # لا يحتوي على نسبة
        "نسبة النجاح: غير محددة",  # نسبة غير رقمية
        "تحليل معقد بدون نتيجة واضحة",  # لا يحتوي على نسبة
        "إشارة ضعيفة جداً 🚨 - تجنب التداول"  # قد يفسر كـ 34% بناءً على النطاق المذكور في التعليمات
    ]
    
    for i, text in enumerate(ai_texts, 1):
        print(f"\nمثال {i}: {text}")
        
        # محاكاة استخراج نسبة الثقة
        confidence = extract_confidence_simulation(text)
        print(f"نسبة الثقة المستخرجة: {confidence}%")

def extract_confidence_simulation(text):
    """محاكاة استخراج نسبة الثقة من النص"""
    import re
    
    # البحث عن أنماط النسب المئوية
    patterns = [
        r'نسبة\s+النجاح\s*:?\s*(\d+(?:\.\d+)?)%',
        r'احتمالية\s+النجاح\s*:?\s*(\d+(?:\.\d+)?)%',
        r'معدل\s+النجاح\s*:?\s*(\d+(?:\.\d+)?)%',
        r'success\s+rate\s*:?\s*(\d+(?:\.\d+)?)%',
        r'(\d+(?:\.\d+)?)\s*%'  # أي نسبة مئوية
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                rate = float(matches[-1])
                if 0 <= rate <= 100:
                    return rate
            except ValueError:
                continue
    
    # إذا لم نجد نسبة، قد نستخدم التحليل الذكي
    text_lower = text.lower()
    
    # الكلمات الإيجابية والسلبية
    positive_keywords = ['إيجابي', 'جيد', 'قوي', 'ممتاز', 'واضح']
    negative_keywords = ['ضعيف', 'سلبي', 'مخاطر', 'تجنب', 'سيء']
    
    positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
    negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
    
    if positive_count > negative_count:
        return 55 + positive_count * 5  # نسبة إيجابية
    elif negative_count > positive_count:
        return max(45 - negative_count * 5, 15)  # نسبة سلبية
    else:
        return 50  # متوسط

def check_specific_34_percent_scenario():
    """فحص السيناريو المحدد الذي يؤدي إلى 34%"""
    print("\n🎯 فحص السيناريو المحدد لـ 34%")
    print("=" * 40)
    
    # السيناريو: AI يرجع تحليل ضعيف بناءً على التعليمات
    ai_response = """
    بناءً على التحليل الفني:
    - المؤشرات متضاربة
    - الاتجاه غير واضح
    - مخاطر عالية
    - إشارة ضعيفة جداً
    
    التوصية: تجنب التداول
    النسبة: في نطاق 20-34%
    """
    
    print(f"نص AI: {ai_response}")
    
    # استخراج النسبة
    confidence = extract_confidence_simulation(ai_response)
    print(f"نسبة الثقة المستخرجة: {confidence}%")
    
    # إذا كان النص يشير إلى نطاق 20-34%، قد يختار AI القيمة 34%
    if "20-34%" in ai_response:
        print("⚠️ النص يحتوي على نطاق 20-34% - قد يفسر AI هذا كـ 34%")
        return 34.0
    
    return confidence

if __name__ == "__main__":
    simulate_ai_analysis_failure()
    simulate_confidence_extraction_issue()
    result = check_specific_34_percent_scenario()
    
    print(f"\n🎯 النتيجة النهائية: {result}%")
    print("\n📋 التوصيات:")
    print("1. فحص سجلات AI للتأكد من نوع الاستجابات")
    print("2. تحسين استخراج نسبة الثقة من نصوص AI")
    print("3. إضافة آليات احتياطية أفضل عند فشل AI")
    print("4. مراجعة تعليمات AI لتجنب التفسير الخاطئ للنطاقات")