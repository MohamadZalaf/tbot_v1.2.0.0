#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اختبار سريع لنافذة عدد المستخدمين في bot_ui.py
"""

import os
import sys

# إضافة المجلد الحالي للمسار
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_ui import TradingBotUI

def test_users_count():
    """اختبار دالة حساب عدد المستخدمين"""
    ui = TradingBotUI()
    
    # اختبار دالة حساب المستخدمين
    count = ui.get_users_count()
    print(f"عدد المستخدمين المكتشف: {count}")
    
    # إنشاء بعض ملفات الاختبار
    os.makedirs("trading_data/users", exist_ok=True)
    os.makedirs("trading_data/user_settings", exist_ok=True)
    
    # إنشاء ملفات مستخدمين وهميين
    test_users = [
        "trading_data/users/user_6891599955.json",
        "trading_data/users/user_1234567890.json", 
        "trading_data/users/user_9876543210.json",
        "trading_data/user_settings/settings_6891599955.json"
    ]
    
    for user_file in test_users:
        with open(user_file, 'w', encoding='utf-8') as f:
            f.write('{"test": "data"}')
    
    # اختبار مرة أخرى
    count = ui.get_users_count()
    print(f"عدد المستخدمين بعد إضافة الملفات: {count}")
    
    # تنظيف
    for user_file in test_users:
        try:
            os.remove(user_file)
        except:
            pass
    
    # عدم تشغيل الواجهة في الاختبار
    return count

if __name__ == "__main__":
    test_users_count()
    print("اختبار مكتمل!")