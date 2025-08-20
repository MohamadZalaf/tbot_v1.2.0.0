#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
البحث عن مصدر نسبة 34% في الكود
"""

import re
import os

def search_for_34_percent():
    """البحث عن جميع الأماكن التي قد تحتوي على 34% أو 0.34"""
    
    patterns_to_search = [
        r'34',
        r'0\.34',
        r'34%',
        r'confidence.*=.*34',
        r'success.*rate.*=.*34',
        r'base.*score.*=.*34',
        r'default.*34',
        r'fallback.*34',
    ]
    
    files_to_search = [
        'tbot_v1.2.0.py',
        'tbot_v1.2.1.py',
        'tbot_v1.2.0_temp.py',
        'tbot_v1.2.0_backup.py'
    ]
    
    print("🔍 البحث عن مصدر نسبة 34%")
    print("=" * 50)
    
    for filename in files_to_search:
        if not os.path.exists(filename):
            continue
            
        print(f"\n📄 فحص الملف: {filename}")
        print("-" * 30)
        
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
            for pattern in patterns_to_search:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        print(f"السطر {line_num}: {line.strip()}")
                        
        except Exception as e:
            print(f"خطأ في قراءة الملف {filename}: {e}")

def search_specific_calculations():
    """البحث عن الحسابات المحددة التي قد تؤدي إلى 34%"""
    
    print("\n🧮 البحث عن حسابات محددة")
    print("=" * 50)
    
    # محاكاة حسابات قد تؤدي إلى 34%
    base_scores = [30, 25, 35, 20]
    additional_scores = [4, 5, 6, 8, 9, 10, 14]
    
    print("الحسابات المحتملة التي تؤدي إلى 34%:")
    
    for base in base_scores:
        for add in additional_scores:
            if base + add == 34:
                print(f"  {base} + {add} = 34")
    
    # فحص النسب المئوية
    percentages = [30, 40, 50, 60, 70, 80, 90]
    multipliers = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    
    print("\nالنسب المئوية المحتملة:")
    for pct in percentages:
        for mult in multipliers:
            result = pct * mult
            if abs(result - 34) < 1:  # قريب من 34
                print(f"  {pct} * {mult} = {result:.1f}")

if __name__ == "__main__":
    search_for_34_percent()
    search_specific_calculations()