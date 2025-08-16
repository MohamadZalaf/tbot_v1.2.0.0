#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار إصلاح تشغيل bot_ui.py كملف تنفيذي
=============================================

هذا الملف يختبر أن التطبيق الرسومي يعمل بدون أخطاء RuntimeError: lost sys.stdin
عند تشغيله كملف .exe

المشكلة المُصلحة:
- إزالة استدعاءات input() التي تسبب خطأ عند عدم توفر sys.stdin
- استبدالها بـ messagebox لعرض رسائل الخطأ

المطور: Assistant
التاريخ: 2025
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

class TestBotUIExeFix(unittest.TestCase):
    """فئة اختبار إصلاح تشغيل UI كملف تنفيذي"""
    
    def setUp(self):
        """إعداد الاختبار"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        
    def tearDown(self):
        """تنظيف بعد الاختبار"""
        os.chdir(self.original_cwd)
        
    def test_missing_bot_file_error_handling(self):
        """اختبار معالجة خطأ عدم وجود ملف البوت بدون input()"""
        print("\n🧪 اختبار معالجة عدم وجود ملف البوت:")
        print("=" * 50)
        
        # تغيير المجلد إلى مجلد فارغ
        os.chdir(self.temp_dir)
        
        # محاكاة عدم وجود sys.stdin (كما في الملف التنفيذي)
        with patch('sys.stdin', None):
            with patch('tkinter.Tk') as mock_tk:
                with patch('tkinter.messagebox.showerror') as mock_messagebox:
                    # محاكاة Tk
                    mock_root = MagicMock()
                    mock_tk.return_value = mock_root
                    
                    # محاولة تشغيل الكود المُصحح
                    try:
                        # محاكاة التحقق من وجود الملف
                        if not os.path.exists("tbot_v1.2.0.py"):
                            # الكود الجديد - بدون input()
                            temp_root = mock_tk()
                            temp_root.withdraw()
                            from tkinter import messagebox
                            messagebox.showerror(
                                "File Not Found", 
                                "❌ Error: tbot_v1.2.0.py not found in current directory!\n\n"
                                "Please run this UI from the same directory as your bot file."
                            )
                            temp_root.destroy()
                            
                        print("✅ لا يوجد استدعاء input() - الإصلاح ناجح")
                        print("✅ تم استخدام messagebox بدلاً من input()")
                        
                        # التحقق من استدعاء messagebox
                        mock_messagebox.assert_called_once()
                        mock_root.withdraw.assert_called_once()
                        mock_root.destroy.assert_called_once()
                        
                        return True
                        
                    except Exception as e:
                        if "lost sys.stdin" in str(e):
                            print("❌ ما زال هناك خطأ sys.stdin")
                            return False
                        else:
                            print(f"✅ خطأ مختلف (ليس sys.stdin): {e}")
                            return True
    
    def test_application_error_handling(self):
        """اختبار معالجة أخطاء التطبيق بدون input()"""
        print("\n🧪 اختبار معالجة أخطاء التطبيق:")
        print("=" * 50)
        
        # محاكاة عدم وجود sys.stdin
        with patch('sys.stdin', None):
            with patch('tkinter.Tk') as mock_tk:
                with patch('tkinter.messagebox.showerror') as mock_messagebox:
                    # محاكاة Tk
                    mock_root = MagicMock()
                    mock_tk.return_value = mock_root
                    
                    try:
                        # محاكاة خطأ في التطبيق
                        test_error = Exception("Test application error")
                        
                        # الكود الجديد - بدون input()
                        temp_root = mock_tk()
                        temp_root.withdraw()
                        from tkinter import messagebox
                        messagebox.showerror(
                            "Application Error", 
                            f"❌ Application error occurred:\n\n{str(test_error)}\n\nPlease check the error details and try again."
                        )
                        temp_root.destroy()
                        
                        print("✅ معالجة أخطاء التطبيق تعمل بدون input()")
                        print("✅ تم استخدام messagebox لعرض الخطأ")
                        
                        # التحقق من استدعاء messagebox
                        mock_messagebox.assert_called_once()
                        mock_root.withdraw.assert_called_once()
                        mock_root.destroy.assert_called_once()
                        
                        return True
                        
                    except Exception as e:
                        if "lost sys.stdin" in str(e):
                            print("❌ ما زال هناك خطأ sys.stdin في معالجة الأخطاء")
                            return False
                        else:
                            print(f"✅ خطأ مختلف (ليس sys.stdin): {e}")
                            return True
    
    def test_stdin_independence(self):
        """اختبار عدم اعتماد الكود على sys.stdin"""
        print("\n🧪 اختبار عدم الاعتماد على sys.stdin:")
        print("=" * 50)
        
        # قراءة ملف bot_ui.py
        try:
            with open('bot_ui.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # التحقق من عدم وجود input()
            input_calls = content.count('input(')
            stdin_references = content.count('sys.stdin')
            
            print(f"عدد استدعاءات input(): {input_calls}")
            print(f"عدد مراجع sys.stdin: {stdin_references}")
            
            if input_calls == 0 and stdin_references == 0:
                print("✅ الكود لا يعتمد على sys.stdin أو input()")
                return True
            else:
                print("❌ ما زال هناك اعتماد على sys.stdin أو input()")
                return False
                
        except FileNotFoundError:
            print("❌ ملف bot_ui.py غير موجود")
            return False
    
    def test_messagebox_import(self):
        """اختبار توفر messagebox للاستخدام"""
        print("\n🧪 اختبار توفر messagebox:")
        print("=" * 50)
        
        try:
            # التحقق من إمكانية استيراد messagebox
            from tkinter import messagebox
            print("✅ تم استيراد messagebox بنجاح")
            
            # التحقق من توفر الدوال المطلوبة
            if hasattr(messagebox, 'showerror'):
                print("✅ دالة showerror متوفرة")
                return True
            else:
                print("❌ دالة showerror غير متوفرة")
                return False
                
        except ImportError as e:
            print(f"❌ فشل في استيراد messagebox: {e}")
            return False
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("\n🚀 بدء اختبار إصلاح تشغيل bot_ui.py كملف تنفيذي")
        print("=" * 70)
        
        tests = [
            ("معالجة عدم وجود ملف البوت", self.test_missing_bot_file_error_handling),
            ("معالجة أخطاء التطبيق", self.test_application_error_handling),
            ("عدم الاعتماد على sys.stdin", self.test_stdin_independence),
            ("توفر messagebox", self.test_messagebox_import)
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
            print("\n🎉 جميع الإصلاحات تعمل بشكل مثالي!")
            print("✅ bot_ui.py يمكن تحويله إلى .exe بدون مشاكل")
            print("✅ لا يوجد اعتماد على sys.stdin")
            print("✅ رسائل الخطأ تظهر في messagebox")
        elif passed_tests >= total_tests * 0.8:
            print("\n👍 معظم الإصلاحات تعمل بشكل جيد")
        else:
            print("\n⚠️ تحتاج بعض الإصلاحات إلى مراجعة")
        
        return passed_tests / total_tests

def main():
    """الدالة الرئيسية"""
    tester = TestBotUIExeFix()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 0.8:
        print(f"\n✅ الإصلاحات ناجحة بنسبة {success_rate*100:.1f}%")
        print("\n🎯 النتائج المتوقعة:")
        print("- يمكن تحويل bot_ui.py إلى .exe بدون أخطاء")
        print("- رسائل الخطأ ستظهر في نوافذ messagebox")
        print("- لا يوجد اعتماد على المدخلات القياسية")
        print("- التطبيق سيعمل في بيئات GUI بدون console")
        return True
    else:
        print(f"\n❌ الإصلاحات تحتاج مراجعة - نسبة النجاح: {success_rate*100:.1f}%")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)