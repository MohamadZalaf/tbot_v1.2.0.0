#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 Trading Bot UI Controller v1.2.0 - EMBEDDED VERSION
====================================================
English GUI Interface for Advanced Trading Bot Control with Embedded Bot

Features:
- Start/Stop Bot Control
- Real-time Status Monitoring
- Event Logging with Timestamps
- Password Protection
- Process Management
- User-friendly Interface
- Users Count Window (Maroon background, Red text)
- Embedded Bot Code (No external .py files needed)

Developer: Mohamad Zalaf ©️2025
Compatible with: Embedded tbot_v1.2.0.py
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import subprocess
import datetime
import os
import sys
import threading
import time
import json
import sqlite3
from typing import Dict, List, Optional, Any

# ===============================================
# EMBEDDED BOT CODE START
# ===============================================

# Import all required libraries for the embedded bot
import telebot
from telebot import apihelper
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import google.generativeai as genai
from telebot import types
import logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from datetime import datetime, timedelta
import ta
from PIL import Image, ImageDraw, ImageFont
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Bot configuration (embedded)
BOT_TOKEN = '7703327028:AAHLqgR1HtVPsq6LfUKEWzNEgLZjJPLa6YU'
BOT_PASSWORD = 'tra12345678'
GEMINI_API_KEY = 'AIzaSyDAOp1ARgrkUvPcmGmXddFx8cqkzhy-3O8'
GEMINI_API_KEYS = [GEMINI_API_KEY]

# Bot settings
MONITORING_INTERVAL = 30
MIN_CONFIDENCE_THRESHOLD = 70
MAX_DAILY_ALERTS = 50
GEMINI_MODEL = 'gemini-2.0-flash'

class EmbeddedTradingBot:
    """Embedded Trading Bot Class"""
    
    def __init__(self):
        self.bot = None
        self.is_running = False
        self.users_data = {}
        self.authenticated_users = set()
        self.user_stats = {}
        self.setup_logging()
        self.init_database()
        
    def setup_logging(self):
        """Setup logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                RotatingFileHandler('bot.log', maxBytes=10*1024*1024, backupCount=5),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def init_database(self):
        """Initialize SQLite database for user data"""
        try:
            self.conn = sqlite3.connect('bot_users.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    join_date TEXT,
                    last_active TEXT,
                    is_authenticated INTEGER DEFAULT 0
                )
            ''')
            
            # Create user stats table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_requests INTEGER DEFAULT 0,
                    successful_trades INTEGER DEFAULT 0,
                    total_points REAL DEFAULT 0.0
                )
            ''')
            
            self.conn.commit()
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
    
    def get_users_count(self):
        """Get total number of users"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users")
            count = self.cursor.fetchone()[0]
            return count
        except Exception as e:
            self.logger.error(f"Error getting users count: {e}")
            return 0
    
    def add_user(self, user_id, username=None, first_name=None):
        """Add new user to database"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if user exists
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if self.cursor.fetchone():
                # Update last active
                self.cursor.execute(
                    "UPDATE users SET last_active = ? WHERE user_id = ?",
                    (current_time, user_id)
                )
            else:
                # Add new user
                self.cursor.execute(
                    "INSERT INTO users (user_id, username, first_name, join_date, last_active) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, first_name, current_time, current_time)
                )
                
                # Add user stats entry
                self.cursor.execute(
                    "INSERT INTO user_stats (user_id) VALUES (?)",
                    (user_id,)
                )
            
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error adding user: {e}")
    
    def authenticate_user(self, user_id):
        """Mark user as authenticated"""
        try:
            self.cursor.execute(
                "UPDATE users SET is_authenticated = 1 WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
            self.authenticated_users.add(user_id)
            
        except Exception as e:
            self.logger.error(f"Error authenticating user: {e}")
    
    def start_bot(self):
        """Start the trading bot"""
        if self.is_running:
            return False, "Bot is already running"
            
        try:
            # Initialize bot
            apihelper.CONNECT_TIMEOUT = 60
            apihelper.READ_TIMEOUT = 60
            apihelper.RETRY_TIMEOUT = 5
            
            self.bot = telebot.TeleBot(BOT_TOKEN)
            self.setup_handlers()
            
            # Start polling in a separate thread
            self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
            self.is_running = True
            self.bot_thread.start()
            
            self.logger.info("Trading bot started successfully")
            return True, "Bot started successfully"
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            return False, f"Error starting bot: {e}"
    
    def stop_bot(self):
        """Stop the trading bot"""
        if not self.is_running:
            return False, "Bot is not running"
            
        try:
            self.is_running = False
            if self.bot:
                self.bot.stop_polling()
            
            self.logger.info("Trading bot stopped")
            return True, "Bot stopped successfully"
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
            return False, f"Error stopping bot: {e}"
    
    def _run_bot(self):
        """Run bot polling"""
        try:
            self.bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            self.logger.error(f"Bot polling error: {e}")
            self.is_running = False
    
    def setup_handlers(self):
        """Setup bot message handlers"""
        
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            user_id = message.from_user.id
            username = message.from_user.username
            first_name = message.from_user.first_name
            
            # Add user to database
            self.add_user(user_id, username, first_name)
            
            welcome_text = """
🤖 أهلاً بك في بوت التداول المتقدم v1.2.0

للوصول إلى الميزات المتقدمة، يرجى إدخال كلمة المرور:
            """
            
            self.bot.reply_to(message, welcome_text)
        
        @self.bot.message_handler(func=lambda message: message.from_user.id not in self.authenticated_users)
        def handle_password(message):
            user_id = message.from_user.id
            
            if message.text == BOT_PASSWORD:
                self.authenticate_user(user_id)
                
                # Create main keyboard
                keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                keyboard.add(
                    types.KeyboardButton("📊 تحليل الأسواق"),
                    types.KeyboardButton("💰 الأسعار المباشرة"),
                    types.KeyboardButton("📈 توصيات التداول"),
                    types.KeyboardButton("⚙️ الإعدادات")
                )
                
                self.bot.reply_to(
                    message, 
                    "✅ تم تسجيل الدخول بنجاح!\n\nاختر من القائمة أدناه:",
                    reply_markup=keyboard
                )
            else:
                self.bot.reply_to(message, "❌ كلمة مرور خاطئة. حاول مرة أخرى.")
        
        @self.bot.message_handler(func=lambda message: message.from_user.id in self.authenticated_users)
        def handle_authenticated_messages(message):
            user_id = message.from_user.id
            text = message.text
            
            if text == "📊 تحليل الأسواق":
                self.bot.reply_to(message, "🔄 جاري تحليل الأسواق... يرجى الانتظار")
                # Add market analysis logic here
                
            elif text == "💰 الأسعار المباشرة":
                self.bot.reply_to(message, "📈 جاري جلب الأسعار المباشرة...")
                # Add live prices logic here
                
            elif text == "📈 توصيات التداول":
                self.bot.reply_to(message, "🤖 جاري تحليل التوصيات...")
                # Add trading recommendations logic here
                
            elif text == "⚙️ الإعدادات":
                settings_keyboard = types.InlineKeyboardMarkup()
                settings_keyboard.add(
                    types.InlineKeyboardButton("🔔 الإشعارات", callback_data="settings_notifications"),
                    types.InlineKeyboardButton("📊 التفضيلات", callback_data="settings_preferences")
                )
                
                self.bot.reply_to(
                    message,
                    "⚙️ إعدادات البوت:",
                    reply_markup=settings_keyboard
                )
            
            else:
                self.bot.reply_to(message, "استخدم القائمة للتنقل في البوت")

# ===============================================
# EMBEDDED BOT CODE END
# ===============================================

class TradingBotUI:
    def __init__(self):
        self.embedded_bot = EmbeddedTradingBot()
        self.PASSWORD = "041768454"  # Custom UI password
        self.is_logged_in = False
        self.monitoring_thread = None
        self.is_monitoring = False
        self.users_count_window = None
        
        # Initialize main window
        self.setup_main_window()
        self.create_login_interface()
        self.create_control_interface()
        
        # Start with login screen
        self.show_login()
        
        # Start monitoring thread
        self.start_monitoring()
    
    def setup_main_window(self):
        """Setup main application window"""
        self.root = tk.Tk()
        self.root.title("🤖 Trading Bot Controller v1.2.0 - EMBEDDED")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Set window icon (optional)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Configure main style
        self.root.configure(bg='#2b2b2b')
        
        # Create main frame
        self.main_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_login_interface(self):
        """Create login interface"""
        self.login_frame = tk.Frame(self.main_frame, bg='#2b2b2b')
        
        # Title
        title_label = tk.Label(
            self.login_frame,
            text="🤖 Trading Bot Controller",
            font=("Arial", 24, "bold"),
            fg='#00ff00',
            bg='#2b2b2b'
        )
        title_label.pack(pady=30)
        
        # Subtitle
        subtitle_label = tk.Label(
            self.login_frame,
            text="Advanced Trading Bot Control Panel v1.2.0",
            font=("Arial", 12),
            fg='#cccccc',
            bg='#2b2b2b'
        )
        subtitle_label.pack(pady=10)
        
        # Password frame
        password_frame = tk.Frame(self.login_frame, bg='#2b2b2b')
        password_frame.pack(pady=40)
        
        # Password label
        password_label = tk.Label(
            password_frame,
            text="🔐 Enter Password:",
            font=("Arial", 14),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        password_label.pack(pady=10)
        
        # Password entry
        self.password_entry = tk.Entry(
            password_frame,
            font=("Arial", 14),
            show="*",
            width=20,
            justify='center'
        )
        self.password_entry.pack(pady=10)
        self.password_entry.bind('<Return>', lambda event: self.check_password())
        
        # Login button
        self.login_button = tk.Button(
            password_frame,
            text="🚀 LOGIN",
            font=("Arial", 12, "bold"),
            bg='#00aa00',
            fg='white',
            width=15,
            height=2,
            command=self.check_password
        )
        self.login_button.pack(pady=20)
        
        # Status label
        self.login_status_label = tk.Label(
            self.login_frame,
            text="",
            font=("Arial", 10),
            fg='#ff6666',
            bg='#2b2b2b'
        )
        self.login_status_label.pack(pady=10)
    
    def create_control_interface(self):
        """Create main control interface"""
        self.control_frame = tk.Frame(self.main_frame, bg='#2b2b2b')
        
        # Header frame
        header_frame = tk.Frame(self.control_frame, bg='#2b2b2b')
        header_frame.pack(fill=tk.X, pady=10)
        
        # Title
        header_label = tk.Label(
            header_frame,
            text="🤖 Trading Bot Control Panel - EMBEDDED VERSION",
            font=("Arial", 18, "bold"),
            fg='#00ff00',
            bg='#2b2b2b'
        )
        header_label.pack(side=tk.LEFT)
        
        # Users count button
        self.users_count_button = tk.Button(
            header_frame,
            text="👥 Users Count",
            font=("Arial", 10, "bold"),
            bg='#800020',  # Maroon color
            fg='#ff0000',  # Red text
            command=self.show_users_count_window
        )
        self.users_count_button.pack(side=tk.RIGHT, padx=10)
        
        # Logout button
        logout_button = tk.Button(
            header_frame,
            text="🚪 Logout",
            font=("Arial", 10),
            bg='#666666',
            fg='white',
            command=self.logout
        )
        logout_button.pack(side=tk.RIGHT, padx=5)
        
        # Control buttons frame
        control_buttons_frame = tk.Frame(self.control_frame, bg='#2b2b2b')
        control_buttons_frame.pack(pady=20)
        
        # Start Bot button
        self.start_button = tk.Button(
            control_buttons_frame,
            text="🚀 START BOT",
            font=("Arial", 14, "bold"),
            bg='#00aa00',
            fg='white',
            width=15,
            height=2,
            command=self.start_bot
        )
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        # Stop Bot button
        self.stop_button = tk.Button(
            control_buttons_frame,
            text="🛑 STOP BOT",
            font=("Arial", 14, "bold"),
            bg='#aa0000',
            fg='white',
            width=15,
            height=2,
            command=self.stop_bot,
            state='disabled'
        )
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        # Status frame
        status_frame = tk.Frame(self.control_frame, bg='#2b2b2b')
        status_frame.pack(fill=tk.X, pady=20)
        
        # Status label
        status_label = tk.Label(
            status_frame,
            text="📊 Bot Status:",
            font=("Arial", 12, "bold"),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        status_label.pack(anchor=tk.W)
        
        # Status indicator
        self.status_indicator = tk.Label(
            status_frame,
            text="⚫ Stopped",
            font=("Arial", 12),
            fg='#ff6666',
            bg='#2b2b2b'
        )
        self.status_indicator.pack(anchor=tk.W, padx=20)
        
        # Log frame
        log_frame = tk.Frame(self.control_frame, bg='#2b2b2b')
        log_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Log label
        log_label = tk.Label(
            log_frame,
            text="📝 Event Log:",
            font=("Arial", 12, "bold"),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        log_label.pack(anchor=tk.W)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=80,
            bg='#1a1a1a',
            fg='#00ff00',
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Add initial log message
        self.add_log("🔧 Bot Controller Initialized - EMBEDDED VERSION")
        self.add_log("ℹ️  All bot code is embedded - no external files needed")
        self.add_log("🔐 Please login to access controls")
    
    def show_users_count_window(self):
        """Show users count in a separate window"""
        if self.users_count_window and self.users_count_window.winfo_exists():
            self.users_count_window.lift()
            return
        
        # Create users count window
        self.users_count_window = tk.Toplevel(self.root)
        self.users_count_window.title("👥 Users Count")
        self.users_count_window.geometry("300x150")
        self.users_count_window.resizable(False, False)
        self.users_count_window.configure(bg='#800020')  # Maroon background
        
        # Center the window
        self.users_count_window.transient(self.root)
        self.users_count_window.grab_set()
        
        # Main frame
        main_frame = tk.Frame(self.users_count_window, bg='#800020')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title label
        title_label = tk.Label(
            main_frame,
            text="👥 Total Users",
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#800020'
        )
        title_label.pack(pady=10)
        
        # Users count label
        users_count = self.embedded_bot.get_users_count()
        self.users_count_label = tk.Label(
            main_frame,
            text=str(users_count),
            font=("Arial", 32, "bold"),
            fg='#ff0000',  # Red text
            bg='#800020'
        )
        self.users_count_label.pack(pady=10)
        
        # Last updated label
        last_updated = tk.Label(
            main_frame,
            text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}",
            font=("Arial", 10),
            fg='#ffcccc',
            bg='#800020'
        )
        last_updated.pack(pady=5)
        
        # Auto-refresh the count every 5 seconds
        def refresh_count():
            if self.users_count_window and self.users_count_window.winfo_exists():
                users_count = self.embedded_bot.get_users_count()
                self.users_count_label.config(text=str(users_count))
                last_updated.config(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
                self.users_count_window.after(5000, refresh_count)
        
        refresh_count()
    
    def show_login(self):
        """Show login interface"""
        self.control_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.password_entry.focus()
    
    def show_control(self):
        """Show control interface"""
        self.login_frame.pack_forget()
        self.control_frame.pack(fill=tk.BOTH, expand=True)
    
    def check_password(self):
        """Check entered password"""
        entered_password = self.password_entry.get()
        
        if entered_password == self.PASSWORD:
            self.is_logged_in = True
            self.login_status_label.config(text="✅ Login successful!", fg='#00ff00')
            self.add_log("🔐 User authenticated successfully")
            self.root.after(1000, self.show_control)
        else:
            self.login_status_label.config(text="❌ Invalid password!", fg='#ff6666')
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()
    
    def logout(self):
        """Logout user"""
        self.is_logged_in = False
        self.password_entry.delete(0, tk.END)
        self.login_status_label.config(text="")
        self.add_log("🚪 User logged out")
        self.show_login()
        
        # Close users count window if open
        if self.users_count_window and self.users_count_window.winfo_exists():
            self.users_count_window.destroy()
    
    def start_bot(self):
        """Start the embedded bot"""
        if not self.is_logged_in:
            messagebox.showerror("Access Denied", "Please login first!")
            return
        
        self.add_log("🚀 Starting embedded trading bot...")
        success, message = self.embedded_bot.start_bot()
        
        if success:
            self.status_indicator.config(text="🟢 Running", fg='#00ff00')
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.add_log(f"✅ {message}")
        else:
            self.add_log(f"❌ {message}")
            messagebox.showerror("Error", message)
    
    def stop_bot(self):
        """Stop the embedded bot"""
        if not self.is_logged_in:
            messagebox.showerror("Access Denied", "Please login first!")
            return
        
        self.add_log("🛑 Stopping embedded trading bot...")
        success, message = self.embedded_bot.stop_bot()
        
        if success:
            self.status_indicator.config(text="⚫ Stopped", fg='#ff6666')
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.add_log(f"✅ {message}")
        else:
            self.add_log(f"❌ {message}")
            messagebox.showerror("Error", message)
    
    def add_log(self, message):
        """Add message to log"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Keep only last 1000 lines
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete("1.0", f"{len(lines)-1000}.0")
    
    def start_monitoring(self):
        """Start monitoring thread"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
            self.monitoring_thread.start()
    
    def monitor_system(self):
        """Monitor system status"""
        while self.is_monitoring:
            try:
                # Update users count button
                if hasattr(self, 'users_count_button'):
                    users_count = self.embedded_bot.get_users_count()
                    self.root.after(0, lambda: self.users_count_button.config(
                        text=f"👥 Users: {users_count}"
                    ))
                
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(10)
    
    def on_closing(self):
        """Handle window closing"""
        if self.embedded_bot.is_running:
            if messagebox.askokcancel("Quit", "Bot is still running. Stop bot and quit?"):
                self.embedded_bot.stop_bot()
                self.is_monitoring = False
                self.root.destroy()
        else:
            self.is_monitoring = False
            self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start main loop
        self.root.mainloop()

if __name__ == "__main__":
    # Create and run the UI with embedded bot
    try:
        app = TradingBotUI()
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Application terminated by user")
    except Exception as e:
        # Create a temporary root window for messagebox
        temp_root = tk.Tk()
        temp_root.withdraw()  # Hide the temporary window
        messagebox.showerror(
            "Application Error", 
            f"❌ Application error occurred:\n\n{str(e)}\n\nPlease check the error details and try again."
        )
        temp_root.destroy()