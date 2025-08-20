#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إصلاح بسيط لمشكلة نسبة النجاح 34%
"""

def apply_fixes():
    filename = 'tbot_v1.2.0.py'
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        
        print("تطبيق الإصلاحات...")
        
        # إصلاح 1: تغيير النطاق المشكوك فيه
        content = content.replace('- 20-34%:', '- 25-34%:')
        content = content.replace('- أقل من 20%:', '- 15-24%: "إشارة سيئة جداً 🛑"\n            - أقل من 15%:')
        
        # إصلاح 2: إضافة تحذير في التعليمات
        old_mandatory = '**🚨 MANDATORY - يجب أن تنهي تحليلك بـ:**'
        new_mandatory = '''**🚨 MANDATORY - يجب أن تنهي تحليلك بـ:**
            
            ⚠️ **مهم:** اعط رقماً محدداً دقيقاً (مثل 67%) وليس نطاقاً (مثل 20-34%)'''
        
        content = content.replace(old_mandatory, new_mandatory)
        
        print("حفظ الملف...")
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print("✅ تم تطبيق الإصلاحات بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    apply_fixes()