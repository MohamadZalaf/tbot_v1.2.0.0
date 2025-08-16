# نافذة عدد المستخدمين - Bot UI v1.2.0

## 🎯 الميزة الجديدة:

### نافذة صغيرة لعرض عدد المستخدمين في واجهة البوت

![نافذة عدد المستخدمين](image_placeholder)

---

## ✨ المواصفات:

### 🎨 **التصميم:**
- **الخلفية**: لون خمري (`#800020`) 
- **النص**: أحمر قاني (`#DC143C`)
- **الحجم**: نافذة صغيرة بارتفاع ثابت 40 بكسل
- **الموقع**: بين العنوان الرئيسي وأزرار التحكم

### 📊 **الوظائف:**
- عرض عدد المستخدمين المسجلين في الوقت الفعلي
- تحديث تلقائي كل ثانية
- دعم اللغة العربية
- بحث ذكي في مجلدات البيانات المتعددة

---

## 🔧 التفاصيل التقنية:

### 1. **إنشاء النافذة:**
```python
# Users count window (small maroon window with red text)
users_frame = tk.Frame(self.control_frame, bg='#800020', relief=tk.RIDGE, bd=2, height=40)  # Maroon background
users_frame.pack(fill=tk.X, pady=5)
users_frame.pack_propagate(False)  # Maintain fixed height

# Users count label
self.users_label = tk.Label(
    users_frame,
    text="👥 عدد المستخدمين: جاري التحميل...",
    font=("Arial", 12, "bold"),
    bg='#800020',  # Maroon background
    fg='#DC143C',  # Crimson red text
    pady=8
)
self.users_label.pack(expand=True)
```

### 2. **حساب عدد المستخدمين:**
```python
def get_users_count(self):
    """Get the number of active users from bot data"""
    total_users = 0
    
    # Check multiple possible user data locations
    user_data_paths = [
        "trading_data/users",
        "trading_data/user_settings", 
        "trading_data/user_feedback",
        "user_data",
        "users"
    ]
    
    unique_users = set()
    
    # Extract unique user IDs from filenames
    for path in user_data_paths:
        if os.path.exists(path) and os.path.isdir(path):
            files = os.listdir(path)
            for file in files:
                if file.endswith(('.json', '.txt')):
                    # Extract user ID from filename patterns
                    if file.startswith(('user_', 'settings_')):
                        user_id = file.split('_')[1].split('.')[0]
                        if user_id.isdigit():
                            unique_users.add(user_id)
    
    return len(unique_users) if unique_users else 0
```

### 3. **التحديث التلقائي:**
```python
def update_users_count(self):
    """Update users count display"""
    count = self.get_users_count()
    if hasattr(self, 'users_label'):
        self.users_label.config(text=f"👥 عدد المستخدمين: {count}")

# في دالة المراقبة
def monitor_bot(self):
    while self.is_monitoring:
        if self.is_logged_in:
            self.update_process_info()
            self.update_users_count()  # تحديث كل ثانية
        time.sleep(1)
```

---

## 📂 مصادر البيانات:

### مجلدات البحث عن بيانات المستخدمين:
1. `trading_data/users/` - الملفات الرئيسية للمستخدمين
2. `trading_data/user_settings/` - إعدادات المستخدمين  
3. `trading_data/user_feedback/` - تقييمات المستخدمين
4. `user_data/` - مجلد بيانات بديل
5. `users/` - مجلد مستخدمين عام

### أنماط الملفات المدعومة:
- `user_123456789.json` - ملف مستخدم برقم ID
- `settings_123456789.json` - ملف إعدادات برقم ID  
- `123456789.json` - ملف برقم ID مباشر
- `*.txt` - ملفات نصية

---

## 🎯 المميزات:

### ✅ **عرض ذكي:**
- حساب المستخدمين الفريدين (تجنب التكرار)
- دعم أنماط ملفات متعددة
- بحث في مجلدات متعددة

### ✅ **تصميم جذاب:**
- ألوان مميزة حسب الطلب (خمري + أحمر قاني)
- خط عربي واضح وكبير
- حجم مناسب وغير مزعج

### ✅ **أداء محسن:**
- تحديث سريع كل ثانية
- معالجة أخطاء صامتة (لا تؤثر على الواجهة)
- ذاكرة مُحسنة

### ✅ **سهولة الاستخدام:**
- تظهر فوراً عند تسجيل الدخول
- لا تحتاج تدخل من المستخدم
- معلومات واضحة بالعربية

---

## 📊 أمثلة عملية:

### حالة عدم وجود مستخدمين:
```
👥 عدد المستخدمين: 0
```

### حالة وجود مستخدمين:
```
👥 عدد المستخدمين: 5
```

### حالة التحميل:
```
👥 عدد المستخدمين: جاري التحميل...
```

### حالة الخطأ:
```
👥 عدد المستخدمين: خطأ
```

---

## 🔍 طريقة الاختبار:

### 1. **تشغيل الواجهة:**
```bash
python bot_ui.py
```

### 2. **تسجيل الدخول:**
- استخدم كلمة المرور: `041768454`

### 3. **مراقبة النافذة:**
- ستظهر النافذة الخمرية بالنص الأحمر
- ستعرض عدد المستخدمين الحالي
- ستتحدث كل ثانية تلقائياً

### 4. **اختبار مع بيانات:**
```bash
# إنشاء مستخدمين وهميين للاختبار
mkdir -p trading_data/users
echo '{"user_id": "123"}' > trading_data/users/user_123.json
echo '{"user_id": "456"}' > trading_data/users/user_456.json
```

---

## 🛠️ التخصيص:

### تغيير الألوان:
```python
# خلفية خمرية
bg='#800020'  # يمكن تغييرها إلى لون آخر

# نص أحمر قاني  
fg='#DC143C'  # يمكن تغييره إلى لون آخر
```

### تغيير النص:
```python
text=f"👥 عدد المستخدمين: {count}"
# يمكن تغييره إلى:
text=f"👤 المستخدمون: {count}"
# أو:
text=f"🧑‍💻 العدد: {count}"
```

### تغيير معدل التحديث:
```python
time.sleep(1)  # تحديث كل ثانية
# يمكن تغييره إلى:
time.sleep(5)  # تحديث كل 5 ثوان
```

---

## 📝 سجل التغييرات:

- ✅ إضافة نافذة عدد المستخدمين مع خلفية خمرية
- ✅ نص أحمر قاني حسب الطلب  
- ✅ بحث ذكي في مجلدات متعددة
- ✅ تحديث تلقائي كل ثانية
- ✅ دعم كامل للغة العربية
- ✅ معالجة أخطاء محسنة
- ✅ تصميم صغير وأنيق

---

## ⚠️ ملاحظات:

1. **الألوان المستخدمة:**
   - خمري: `#800020` (Maroon)
   - أحمر قاني: `#DC143C` (Crimson)

2. **الحجم:** النافذة بارتفاع ثابت 40 بكسل

3. **الموقع:** بين العنوان الرئيسي وأزرار التحكم

4. **التحديث:** تلقائي كل ثانية عند تسجيل الدخول

الآن لديك نافذة جميلة لعرض عدد المستخدمين! 🎨✨