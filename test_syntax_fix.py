#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار إصلاح الخطأ النحوي في tbot_v1.2.0.py
===============================================

هذا الملف يختبر أن الخطأ النحوي SyntaxError تم إصلاحه بنجاح

الخطأ المُصحح:
- إزالة except مكرر في السطر 956
- دمج معالجة الأخطاء في except واحد صحيح

المطور: Assistant
التاريخ: 2025
"""

import ast
import sys

def test_syntax_fix():
    """اختبار إصلاح الخطأ النحوي"""
    print("🔍 اختبار إصلاح الخطأ النحوي في tbot_v1.2.0.py")
    print("=" * 60)
    
    try:
        # محاولة قراءة وتحليل الملف
        with open('tbot_v1.2.0.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ تم قراءة الملف بنجاح")
        
        # محاولة تحليل البنية النحوية
        try:
            ast.parse(content)
            print("✅ البنية النحوية صحيحة - لا توجد أخطاء SyntaxError")
            return True
            
        except SyntaxError as e:
            print(f"❌ ما زال هناك خطأ نحوي: {e}")
            print(f"   السطر: {e.lineno}")
            print(f"   النص: {e.text}")
            return False
            
    except FileNotFoundError:
        print("❌ ملف tbot_v1.2.0.py غير موجود")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

def test_try_except_structure():
    """اختبار بنية try/except"""
    print("\n🔍 اختبار بنية try/except:")
    print("=" * 40)
    
    try:
        with open('tbot_v1.2.0.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # عد عدد try و except
        try_count = content.count('try:')
        except_count = content.count('except ')
        
        print(f"عدد try: {try_count}")
        print(f"عدد except: {except_count}")
        
        # البحث عن except مكرر
        lines = content.split('\n')
        duplicate_except = []
        
        for i, line in enumerate(lines):
            if 'except Exception as e:' in line:
                # تحقق من السطر التالي والسابق
                if i > 0 and 'except Exception as e:' in lines[i-1]:
                    duplicate_except.append(i+1)
                if i < len(lines)-1 and 'except Exception as e:' in lines[i+1]:
                    duplicate_except.append(i+2)
        
        if duplicate_except:
            print(f"❌ except مكرر في السطور: {duplicate_except}")
            return False
        else:
            print("✅ لا توجد except مكررة")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في فحص البنية: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار إصلاح الخطأ النحوي")
    print("=" * 70)
    
    tests = [
        ("فحص البنية النحوية", test_syntax_fix),
        ("فحص بنية try/except", test_try_except_structure)
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
    print("\n" + "=" * 70)
    print("📊 النتائج النهائية:")
    print("=" * 70)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{status} {test_name}")
    
    print(f"\nالنتيجة الإجمالية: {passed_tests}/{total_tests} اختبار نجح")
    
    if passed_tests == total_tests:
        print("\n🎉 تم إصلاح الخطأ النحوي بنجاح!")
        print("✅ يمكن الآن تشغيل tbot_v1.2.0.py بدون أخطاء")
        print("✅ البنية النحوية صحيحة ومتوافقة")
        return True
    else:
        print("\n❌ ما زال هناك مشاكل نحوية")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)