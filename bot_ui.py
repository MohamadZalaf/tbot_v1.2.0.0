#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 Trading Bot UI Controller v1.2.0
==================================
English GUI Interface for Advanced Trading Bot Control

Features:
- Start/Stop Bot Control
- Real-time Status Monitoring
- Event Logging with Timestamps
- Password Protection
- Process Management
- User-friendly Interface

Developer: Mohamad Zalaf ©️2025
Compatible with: tbot_v1.2.0.py
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import datetime
import os
import sys
import threading
import time

class TradingBotUI:
    def __init__(self):
        self.bot_process = None
        self.PASSWORD = "tra12345678"  # Same as bot password
        self.is_logged_in = False
        self.monitoring_thread = None
        self.is_monitoring = False
        
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
        self.root.title("🤖 Advanced Trading Bot Controller v1.2.0")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Set window icon (if available)
        try:
            self.root.iconbitmap("bot_icon.ico")
        except:
            pass
        
        # Configure colors and styles
        self.colors = {
            'bg_main': '#f0f0f0',
            'bg_frame': '#ffffff',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8',
            'primary': '#007bff',
            'dark': '#343a40'
        }
        
        self.root.configure(bg=self.colors['bg_main'])
    
    def create_login_interface(self):
        """Create login interface"""
        self.login_frame = tk.Frame(self.root, bg=self.colors['bg_main'], padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            self.login_frame,
            text="🔐 Trading Bot Access Control",
            font=("Arial", 16, "bold"),
            bg=self.colors['bg_main'],
            fg=self.colors['dark']
        )
        title_label.pack(pady=20)
        
        # Subtitle
        subtitle_label = tk.Label(
            self.login_frame,
            text="Enter password to access bot controls",
            font=("Arial", 10),
            bg=self.colors['bg_main'],
            fg=self.colors['dark']
        )
        subtitle_label.pack(pady=5)
        
        # Password frame
        password_frame = tk.Frame(self.login_frame, bg=self.colors['bg_main'])
        password_frame.pack(pady=20)
        
        tk.Label(
            password_frame,
            text="Password:",
            font=("Arial", 12),
            bg=self.colors['bg_main']
        ).pack(side=tk.LEFT, padx=5)
        
        self.password_entry = tk.Entry(
            password_frame,
            show="*",
            font=("Arial", 12),
            width=20,
            relief=tk.RIDGE,
            bd=2
        )
        self.password_entry.pack(side=tk.LEFT, padx=5)
        self.password_entry.bind('<Return>', lambda e: self.check_password())
        
        # Login button
        login_button = tk.Button(
            self.login_frame,
            text="🚀 Access Control Panel",
            command=self.check_password,
            font=("Arial", 12, "bold"),
            bg=self.colors['primary'],
            fg='white',
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10,
            cursor='hand2'
        )
        login_button.pack(pady=20)
        
        # Info label
        info_label = tk.Label(
            self.login_frame,
            text="⚠️ Authorized Personnel Only",
            font=("Arial", 9),
            bg=self.colors['bg_main'],
            fg=self.colors['warning']
        )
        info_label.pack(pady=10)
    
    def create_control_interface(self):
        """Create main control interface"""
        self.control_frame = tk.Frame(self.root, bg=self.colors['bg_main'], padx=10, pady=10)
        
        # Header
        header_frame = tk.Frame(self.control_frame, bg=self.colors['bg_frame'], relief=tk.RIDGE, bd=2)
        header_frame.pack(fill=tk.X, pady=5)
        
        header_label = tk.Label(
            header_frame,
            text="🤖 Advanced Trading Bot Control Center",
            font=("Arial", 14, "bold"),
            bg=self.colors['bg_frame'],
            fg=self.colors['dark'],
            pady=10
        )
        header_label.pack()
        
        # Control buttons frame
        buttons_frame = tk.Frame(self.control_frame, bg=self.colors['bg_main'])
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Start Bot Button
        self.start_button = tk.Button(
            buttons_frame,
            text="▶️ Start Trading Bot",
            command=self.start_bot,
            font=("Arial", 12, "bold"),
            bg='#28a745',
            fg='white',
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10,
            cursor='hand2',
            width=20
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Pause/Resume Button
        self.toggle_button = tk.Button(
            buttons_frame,
            text="⏸️ Pause/Resume",
            command=self.toggle_bot,
            font=("Arial", 12, "bold"),
            bg=self.colors['warning'],
            fg='white',
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10,
            cursor='hand2',
            width=20
        )
        self.toggle_button.pack(side=tk.LEFT, padx=5)
        
        # Stop Bot Button
        self.stop_button = tk.Button(
            buttons_frame,
            text="⏹️ Stop Bot",
            command=self.stop_bot,
            font=("Arial", 12, "bold"),
            bg=self.colors['danger'],
            fg='white',
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=10,
            cursor='hand2',
            width=20
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status frame
        status_frame = tk.Frame(self.control_frame, bg=self.colors['bg_frame'], relief=tk.RIDGE, bd=2)
        status_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            status_frame,
            text="📊 Bot Status:",
            font=("Arial", 12, "bold"),
            bg=self.colors['bg_frame'],
            fg=self.colors['dark']
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="⚠️ Bot not started yet",
            font=("Arial", 11),
            bg=self.colors['bg_frame'],
            fg=self.colors['warning'],
            padx=10,
            pady=5
        )
        self.status_label.pack(anchor=tk.W)
        
        # Process info frame
        process_frame = tk.Frame(self.control_frame, bg=self.colors['bg_frame'], relief=tk.RIDGE, bd=2)
        process_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            process_frame,
            text="🔧 Process Information:",
            font=("Arial", 12, "bold"),
            bg=self.colors['bg_frame'],
            fg=self.colors['dark']
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        self.process_label = tk.Label(
            process_frame,
            text="Process ID: None | Uptime: 00:00:00",
            font=("Arial", 10),
            bg=self.colors['bg_frame'],
            fg=self.colors['info'],
            padx=10,
            pady=5
        )
        self.process_label.pack(anchor=tk.W)
        
        # Event log frame
        log_frame = tk.Frame(self.control_frame, bg=self.colors['bg_frame'], relief=tk.RIDGE, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(
            log_frame,
            text="📝 Event Log:",
            font=("Arial", 12, "bold"),
            bg=self.colors['bg_frame'],
            fg=self.colors['dark']
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Scrolled text for logs
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=70,
            font=("Consolas", 9),
            bg='#f8f9fa',
            fg=self.colors['dark'],
            relief=tk.SUNKEN,
            bd=2
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Clear log button
        clear_button = tk.Button(
            log_frame,
            text="🗑️ Clear Log",
            command=self.clear_log,
            font=("Arial", 9),
            bg=self.colors['info'],
            fg='white',
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=2,
            cursor='hand2'
        )
        clear_button.pack(anchor=tk.E, padx=10, pady=5)
        
        # Footer
        footer_label = tk.Label(
            self.control_frame,
            text="🚀 Advanced Trading Bot v1.2.0 | Developer: Mohamad Zalaf ©️2025",
            font=("Arial", 8),
            bg=self.colors['bg_main'],
            fg=self.colors['dark']
        )
        footer_label.pack(pady=5)
    
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
        if self.password_entry.get() == self.PASSWORD:
            self.is_logged_in = True
            self.show_control()
            self.log_event("✅ Login successful - Access granted", "success")
            self.password_entry.delete(0, tk.END)
        else:
            messagebox.showerror("❌ Access Denied", "Incorrect password!\nAccess to bot controls denied.")
            self.password_entry.delete(0, tk.END)
            self.log_event("❌ Login failed - Invalid password", "danger")
    
    def start_bot(self):
        """Start the trading bot"""
        if self.bot_process is None or self.bot_process.poll() is not None:
            try:
                # Check if bot file exists
                bot_file = "tbot_v1.2.0.py"
                if not os.path.exists(bot_file):
                    self.log_event(f"❌ Bot file not found: {bot_file}", "danger")
                    messagebox.showerror("Error", f"Bot file '{bot_file}' not found in current directory!")
                    return
                
                # Start bot process
                self.bot_process = subprocess.Popen(
                    [sys.executable, bot_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.getcwd()
                )
                
                self.start_time = datetime.datetime.now()
                self.update_status("✅ Trading bot started successfully", "success")
                self.start_button.config(bg='#6c757d', text="🔄 Bot Running")
                self.log_event(f"🚀 Bot started - PID: {self.bot_process.pid}", "success")
                
            except Exception as e:
                self.log_event(f"❌ Failed to start bot: {str(e)}", "danger")
                messagebox.showerror("Error", f"Failed to start bot:\n{str(e)}")
        else:
            self.log_event("ℹ️ Bot is already running", "info")
            messagebox.showinfo("Info", "Bot is already running!")
    
    def toggle_bot(self):
        """Toggle bot pause/resume"""
        if self.bot_process and self.bot_process.poll() is None:
            # For demonstration - actual pause/resume would need bot cooperation
            self.log_event("⏸️ Bot pause/resume requested", "warning")
            messagebox.showinfo("Info", "Pause/Resume functionality requires bot cooperation.\nUse Stop and Start for now.")
        else:
            self.log_event("⚠️ Cannot toggle - Bot is not running", "warning")
            messagebox.showwarning("Warning", "Bot is not running!\nStart the bot first.")
    
    def stop_bot(self):
        """Stop the trading bot"""
        if self.bot_process and self.bot_process.poll() is None:
            try:
                self.bot_process.terminate()
                
                # Wait for process to terminate
                try:
                    self.bot_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.bot_process.kill()
                    self.log_event("🔪 Bot process killed (forced termination)", "warning")
                
                self.update_status("❌ Trading bot stopped", "danger")
                self.start_button.config(bg='#28a745', text="▶️ Start Trading Bot")
                self.log_event("⏹️ Bot stopped successfully", "info")
                self.bot_process = None
                
            except Exception as e:
                self.log_event(f"❌ Error stopping bot: {str(e)}", "danger")
                messagebox.showerror("Error", f"Error stopping bot:\n{str(e)}")
        else:
            self.log_event("ℹ️ Bot is not running", "info")
            messagebox.showinfo("Info", "Bot is not running!")
    
    def update_status(self, text, status_type="info"):
        """Update status label"""
        color_map = {
            "success": self.colors['success'],
            "warning": self.colors['warning'],
            "danger": self.colors['danger'],
            "info": self.colors['info']
        }
        
        self.status_label.config(text=text, fg=color_map.get(status_type, self.colors['dark']))
        self.log_event(text, status_type)
    
    def log_event(self, text, event_type="info"):
        """Add event to log"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Color coding for different event types
        color_tags = {
            "success": "green",
            "warning": "orange",
            "danger": "red",
            "info": "blue"
        }
        
        # Configure text tags for colors
        for tag, color in color_tags.items():
            self.log_text.tag_config(tag, foreground=color)
        
        # Insert log entry
        log_entry = f"[{timestamp}] {text}\n"
        self.log_text.insert(tk.END, log_entry, event_type)
        self.log_text.see(tk.END)
        
        # Limit log size (keep last 1000 lines)
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete("1.0", "100.0")
    
    def clear_log(self):
        """Clear event log"""
        self.log_text.delete("1.0", tk.END)
        self.log_event("🗑️ Event log cleared", "info")
    
    def update_process_info(self):
        """Update process information"""
        if self.bot_process and self.bot_process.poll() is None:
            uptime = datetime.datetime.now() - self.start_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            process_info = f"Process ID: {self.bot_process.pid} | Uptime: {uptime_str}"
        else:
            process_info = "Process ID: None | Uptime: 00:00:00"
        
        self.process_label.config(text=process_info)
    
    def start_monitoring(self):
        """Start monitoring thread"""
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self.monitor_bot, daemon=True)
        self.monitoring_thread.start()
    
    def monitor_bot(self):
        """Monitor bot process in background"""
        while self.is_monitoring:
            if self.is_logged_in:
                self.update_process_info()
                
                # Check if bot process died unexpectedly
                if self.bot_process and self.bot_process.poll() is not None:
                    if hasattr(self, 'start_time'):  # Bot was running
                        self.update_status("⚠️ Bot process terminated unexpectedly", "warning")
                        self.start_button.config(bg='#28a745', text="▶️ Start Trading Bot")
                        self.bot_process = None
            
            time.sleep(1)  # Update every second
    
    def on_closing(self):
        """Handle window closing"""
        if self.bot_process and self.bot_process.poll() is None:
            if messagebox.askokcancel("Quit", "Bot is still running!\nDo you want to stop it and quit?"):
                self.stop_bot()
                self.is_monitoring = False
                self.root.destroy()
        else:
            self.is_monitoring = False
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        # Initial log entry
        self.log_event("🤖 Trading Bot UI Controller v1.2.0 initialized", "success")
        self.log_event("👨‍💻 Developer: Mohamad Zalaf ©️2025", "info")
        self.log_event("🔐 Please login to access bot controls", "warning")
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start main loop
        self.root.mainloop()

if __name__ == "__main__":
    # Check if running in correct directory
    if not os.path.exists("tbot_v1.2.0.py"):
        print("❌ Error: tbot_v1.2.0.py not found in current directory!")
        print("Please run this UI from the same directory as your bot file.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Create and run the UI
    try:
        app = TradingBotUI()
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Application terminated by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
        input("Press Enter to exit...")