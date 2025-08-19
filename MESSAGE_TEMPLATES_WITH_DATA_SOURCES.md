# نماذج رسائل الإشعارات مع مصادر البيانات - البوت v1.2.0

## 🤖 نموذج رسالة التحليل الآلي (format_short_alert_message)

### هيكل الرسالة:
```
🚨 إشعار تداول آلي {symbol_emoji}

🚀 إشارة تداول ذكية

━━━━━━━━━━━━━━━━━━━━━━━━━
💱 {SYMBOL} | {symbol_name} {symbol_emoji}
📡 مصدر البيانات: 🔗 MetaTrader5 (لحظي - بيانات حقيقية)

💰 السعر الحالي: {current_price}
📊 شراء: {bid} | بيع: {ask} | فرق: {spread} ({spread_points} نقطة)
➡️ التغيير اليومي: {daily_change}
⏰ وقت التحليل: {formatted_time}

━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ إشارة التداول الرئيسية

{action_color} نوع الصفقة: {action_text}
📍 سعر الدخول المقترح: {entry_price}
🎯 الهدف الأول: ({points1} نقطة)
🎯 الهدف الثاني: ({points2} نقطة)
🛑 وقف الخسارة: ({stop_points} نقطة)
📊 نسبة المخاطرة/المكافأة: 1:{risk_reward_ratio}
✅ نسبة نجاح الصفقة: {confidence}%

━━━━━━━━━━━━━━━━━━━━━━━━━
📰 تحديث إخباري:
{news}

━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 🕐 🕐 {formatted_time} | 🤖 تحليل ذكي آلي
```

### مصادر البيانات للتحليل الآلي:

| القيمة | المصدر | الوظيفة/المتغير | الملاحظات |
|---------|---------|------------------|------------|
| **symbol_emoji** | `ALL_SYMBOLS[symbol]['emoji']` | معرف داخلياً | رموز تعبيرية ثابتة |
| **symbol_name** | `ALL_SYMBOLS[symbol]['name']` | معرف داخلياً | أسماء الأصول بالعربية |
| **current_price** | `price_data.get('last', price_data.get('bid', 0))` | MetaTrader5 | سعر آخر صفقة أو سعر الشراء |
| **bid** | `price_data.get('bid', 0)` | MetaTrader5 | سعر الشراء اللحظي |
| **ask** | `price_data.get('ask', 0)` | MetaTrader5 | سعر البيع اللحظي |
| **spread** | `price_data.get('spread', 0)` | MetaTrader5 محسوب | ask - bid |
| **spread_points** | `price_data.get('spread_points', 0)` | حساب داخلي | spread ÷ pip_size |
| **daily_change** | حساب داخلي | مقارنة أسعار | نسبة التغيير من بداية اليوم |
| **formatted_time** | `format_time_for_user(user_id)` | دالة داخلية | حسب منطقة المستخدم الزمنية |
| **action_text** | `analysis.get('action')` | Google Gemini AI | BUY/SELL/HOLD |
| **entry_price** | `analysis.get('entry_price') or current_price` | Gemini AI أو السعر الحالي | سعر الدخول المقترح |
| **points1** | حساب من `target1` | pip_value_detector | عدد النقاط للهدف الأول |
| **points2** | حساب من `target2` | pip_value_detector | عدد النقاط للهدف الثاني |
| **stop_points** | حساب من `stop_loss` | pip_value_detector | عدد نقاط وقف الخسارة |
| **risk_reward_ratio** | `analysis.get('risk_reward')` | Gemini AI أو حساب داخلي | نسبة المخاطرة للمكافأة |
| **confidence** | `analysis.get('confidence')` | Google Gemini AI | نسبة نجاح الصفقة |
| **news** | `gemini_analyzer.get_symbol_news(symbol)` | Google Gemini AI | أخبار اقتصادية متعلقة |

---

## 👤 نموذج رسالة التحليل اليدوي (format_comprehensive_analysis_v120)

### هيكل الرسالة:
```
📊 **تحليل شامل - {symbol_emoji} {symbol_name}**

💰 **السعر الحالي:** `{current_price}`
💳 **رأس المال المحدد للتداول:** ${user_capital}
📊 **حجم المركز المقترح:** {recommended_lot_size} لوت
📈 **التوصية:** {action_emoji} **{action_text}**
{confidence_emoji} **مستوى الثقة:** {confidence}% ({confidence_text})

🔍 **التحليل التفصيلي:**
{ai_analysis}

⚠️ **تنبيه:** هذا تحليل للمعلومات فقط وليس نصيحة استثمارية.

🕒 **وقت التحليل:** {timestamp}
📊 **مصدر البيانات:** {data_source}
```

### مصادر البيانات للتحليل اليدوي:

| القيمة | المصدر | الوظيفة/المتغير | الملاحظات |
|---------|---------|------------------|------------|
| **symbol_emoji** | `symbol_info['emoji']` | معرف داخلياً | من قاموس ALL_SYMBOLS |
| **symbol_name** | `symbol_info['name']` | معرف داخلياً | اسم الأصل بالعربية |
| **current_price** | `price_data.get('last', price_data.get('bid', 0))` | MetaTrader5 (force_fresh=True) | بيانات لحظية مباشرة |
| **user_capital** | `get_user_capital(user_id)` | إعدادات المستخدم | رأس المال المحفوظ |
| **recommended_lot_size** | `calculate_position_size(user_capital)` | حساب داخلي | حسب رأس المال |
| **action_emoji** | حساب داخلي | حسب نوع الإجراء | 🟢 شراء، 🔴 بيع، 🟡 انتظار |
| **action_text** | `analysis.get('action', 'HOLD')` | Google Gemini AI | شراء/بيع/انتظار |
| **confidence_emoji** | حساب داخلي | حسب نسبة الثقة | 🎯🔴⚖️⚠️🚫 |
| **confidence** | `analysis.get('confidence', 50)` | Google Gemini AI | نسبة الثقة 0-100% |
| **confidence_text** | حساب داخلي | ترجمة النسبة | عالية جداً/عالية/متوسطة/منخفضة |
| **ai_analysis** | `analysis.get('ai_analysis', 'تحليل غير متوفر')` | Google Gemini AI | التحليل المفصل |
| **timestamp** | `datetime.now().strftime('%Y-%m-%d %H:%M:%S')` | وقت النظام | وقت إنشاء التحليل |
| **data_source** | `price_data.get('source', 'MT5')` | MetaTrader5 | مصدر بيانات الأسعار |

---

## 📊 مقارنة بين النوعين:

### التحليل الآلي:
- **الغرض**: إشعارات سريعة للفرص التجارية
- **التكرار**: كل دقيقة (حسب إعدادات المستخدم)
- **مصدر البيانات**: كاش + تحديثات دورية
- **طول الرسالة**: مختصر (حوالي 15-20 سطر)
- **التفاعل**: أزرار تقييم 👍👎
- **الهدف**: سرعة الإشعار بالفرص

### التحليل اليدوي:
- **الغرض**: تحليل شامل مفصل
- **التكرار**: عند الطلب فقط
- **مصدر البيانات**: لحظي مباشر (force_fresh=True)
- **طول الرسالة**: مفصل (حوالي 10-15 سطر + تحليل AI)
- **التفاعل**: تقييم + تحديث + تحليل آخر
- **الهدف**: فهم عميق للوضع

---

## 🔧 دوال المساعدة وأصولها:

### دوال التوقيت:
- `format_time_for_user(user_id)` - تنسيق الوقت حسب منطقة المستخدم
- `get_user_timezone(user_id)` - جلب منطقة المستخدم الزمنية

### دوال إعدادات المستخدم:
- `get_user_capital(user_id)` - رأس المال المحدد
- `get_user_trading_mode(user_id)` - نمط التداول (scalping/long_term)

### دوال حساب النقاط:
- `pip_calculate_points(price_diff, symbol)` - من pip_value_detector
- `calculate_points_accurately(price_diff, symbol, capital, current_price)` - حساب شامل
- `get_pip_value(asset_name)` - من pip_value_detector
- `get_asset_category(asset_name)` - من pip_value_detector

### دوال AI:
- `gemini_analyzer.analyze_market_data_with_retry()` - التحليل الرئيسي
- `gemini_analyzer.get_symbol_news()` - الأخبار الاقتصادية
- `calculate_ai_success_rate()` - حساب نسبة النجاح الديناميكية

---

## 🚀 تحسينات مع pip_value_detector:

1. **دقة أكبر**: قيم نقاط محددة لكل أصل
2. **تصنيف واضح**: forex, metals, crypto
3. **سهولة التطوير**: ملف منفصل للتحديثات
4. **توافق عكسي**: يعمل مع النظام القديم
5. **اختبارات شاملة**: دوال اختبار مدمجة

---

*تم إنشاء هذا الدليل لمساعدة المطورين في فهم نظام الرسائل ومصادر البيانات في البوت v1.2.0*