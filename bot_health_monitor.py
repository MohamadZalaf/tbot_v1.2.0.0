#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
مراقب صحة البوت - يتحقق من حالة البوت ويعيد تشغيله عند الحاجة
"""

import time
import subprocess
import sys
import logging
import os
from datetime import datetime

# إعداد السجل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - BOT_MONITOR - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotHealthMonitor:
    def __init__(self, bot_script_path="tbot_v1.2.0.py"):
        self.bot_script_path = bot_script_path
        self.bot_process = None
        self.restart_count = 0
        self.max_restarts_per_hour = 10
        self.restart_times = []
        
    def is_bot_running(self):
        """فحص ما إذا كان البوت يعمل"""
        if self.bot_process is None:
            return False
        
        # فحص حالة العملية
        poll_result = self.bot_process.poll()
        return poll_result is None
    
    def start_bot(self):
        """بدء تشغيل البوت"""
        try:
            logger.info("🚀 بدء تشغيل البوت...")
            self.bot_process = subprocess.Popen([
                sys.executable, self.bot_script_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            logger.info(f"✅ تم بدء البوت - PID: {self.bot_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل في بدء البوت: {e}")
            return False
    
    def stop_bot(self):
        """إيقاف البوت بأمان"""
        if self.bot_process:
            try:
                logger.info("🛑 إيقاف البوت...")
                self.bot_process.terminate()
                
                # انتظار الإغلاق الآمن
                try:
                    self.bot_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("⚠️ البوت لم يتوقف - إجبار الإغلاق...")
                    self.bot_process.kill()
                    self.bot_process.wait()
                
                logger.info("✅ تم إيقاف البوت")
                self.bot_process = None
                return True
                
            except Exception as e:
                logger.error(f"❌ خطأ في إيقاف البوت: {e}")
                return False
        return True
    
    def restart_bot(self):
        """إعادة تشغيل البوت"""
        current_time = datetime.now()
        
        # تنظيف قائمة أوقات الإعادة (الساعة الماضية فقط)
        self.restart_times = [
            t for t in self.restart_times 
            if (current_time - t).total_seconds() < 3600
        ]
        
        # فحص عدد مرات الإعادة
        if len(self.restart_times) >= self.max_restarts_per_hour:
            logger.error("🚨 تم الوصول للحد الأقصى من إعادة التشغيل في الساعة - توقف")
            return False
        
        logger.info("🔄 إعادة تشغيل البوت...")
        
        # إيقاف البوت أولاً
        self.stop_bot()
        
        # انتظار قصير
        time.sleep(5)
        
        # بدء البوت مرة أخرى
        if self.start_bot():
            self.restart_times.append(current_time)
            self.restart_count += 1
            logger.info(f"✅ تم إعادة التشغيل بنجاح (المرة #{self.restart_count})")
            return True
        else:
            logger.error("❌ فشل في إعادة التشغيل")
            return False
    
    def monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        logger.info("👁️ بدء مراقبة صحة البوت...")
        
        # بدء البوت أولاً
        if not self.start_bot():
            logger.error("❌ فشل في بدء البوت - إنهاء المراقب")
            return
        
        last_health_check = datetime.now()
        
        while True:
            try:
                time.sleep(30)  # فحص كل 30 ثانية
                
                current_time = datetime.now()
                
                # فحص حالة البوت
                if not self.is_bot_running():
                    logger.warning("⚠️ البوت متوقف - إعادة التشغيل...")
                    if not self.restart_bot():
                        logger.error("❌ فشل في إعادة التشغيل - إنهاء المراقب")
                        break
                
                # فحص دوري (كل 5 دقائق)
                if (current_time - last_health_check).total_seconds() > 300:
                    logger.info(f"💚 البوت يعمل بشكل طبيعي - PID: {self.bot_process.pid}")
                    last_health_check = current_time
                
            except KeyboardInterrupt:
                logger.info("🛑 تم الحصول على إشارة إيقاف...")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في المراقب: {e}")
                time.sleep(10)
        
        # إيقاف البوت عند الإنهاء
        self.stop_bot()
        logger.info("✅ تم إنهاء المراقب")

def main():
    """الدالة الرئيسية"""
    monitor = BotHealthMonitor()
    
    try:
        monitor.monitor_loop()
    except Exception as e:
        logger.error(f"❌ خطأ عام في المراقب: {e}")
    finally:
        monitor.stop_bot()

if __name__ == "__main__":
    main()