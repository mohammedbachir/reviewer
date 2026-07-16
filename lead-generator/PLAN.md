# Lead Generator — خطة البناء

## الفكرة
سكربت Python يلقى محلات ما ترد على مراجعاتها في Google Maps، يجمع ايميلاتهم، ويرسل لهم ايميل يشرح فيه أداة Reviewer.

---

## الخطوة 1: العثور على المحلات (finder.py)

**المدخل:** مدينة + نوع نشاط
**المخرج:** CSV فيه اسم المحل، العنوان، التقييم، عدد المراجعات، رقم الهاتف، الموقع

**الخدمة:** Outscraper Google Maps API
**التكلفة:** مجاني (100 طلب/شهر)

```
المدخل: "دبي" + "عيادات أسنان"
    ↓
Outscraper API
    ↓
CSV: [{ name, address, rating, review_count, phone, website, google_url }]
```

---

## الخطوة 2: تحليل المراجعات (analyzer.py)

**المدخل:** قائمة المحلات
**المخرج:** قائمة المحلات اللي نسبة ردودها أقل من 30%

**الطريقة:**
- نسحب مراجعات كل محل من Outscraper
- نتحقق: هل صاحب المحل كتب رد رسمي (Owner reply)؟
- نسبة الرد = عدد الردود الرسمية / عدد المراجعات
- اللي نسبة ردوده < 30% = lead مثالي

```
لكل محل:
  - مراجعاته: 50
  - ردود صاحبه: 5
  - نسبة الرد: 10% ✅ (lead مثالي)
```

---

## الخطوة 3: العثور على اليميلات (contact.py)

**المدخل:** موقع المحل الإلكتروني
**المخرج:** ايميل التواصل

**الطريقة (بترتيب):**
1. من Outscraper (مع بيانات المحل)
2. من صفحة "تواصل معنا" في الموقع
3. من صفحة footer في الموقع
4. من صفحة Privacy Policy / Terms
5. بحث Google: "[اسم المحل] [المدينة] email"

```
محل → www.cafe.com
    ↓
Scrape /contact-us → info@cafe.com
```

---

## الخطوة 4: إرسال الايميلات (sender.py)

**المدخل:** ايميل المحل + اسمه
**المخرج:** ايميل مرسل ✅

**الخدمة:** Gmail SMTP (مجاني)
**التكلفة:** مجاني

**محتوى الايميل:**
```
Subject: Your customers are waiting for a reply

Hi [Name],

I noticed you have [X] unanswered reviews on Google Maps.
Customers often decide based on reviews — and no reply 
can look like you don't care.

I built a free tool that writes human-like replies to 
Google reviews in 10 seconds. No robot talk, no 
corporate speak.

Worth checking out: [link]

— [Your name]
```

---

## الخطوة 5: حفظ النتائج (leads.csv)

```csv
name,address,rating,review_count,response_rate,phone,email,status,sent_at
Cafe Moon,Dubai Marina,4.2,45,8%,+971501234567,info@cafe.com,sent,2024-01-15
Dental Care,Deira,3.8,32,3%,+971509876543,dental@gmail.com,pending,
```

---

## هيكل الملفات

```
lead-generator/
├── config.py              # API keys + الإعدادات
├── finder.py              # الخطوة 1: يلاقي المحلات
├── analyzer.py            # الخطوة 2: يحلل المراجعات
├── contact.py             # الخطوة 3: يلاقي اليميلات
├── sender.py              # الخطوة 4: يرسل الايميلات
├── main.py                # يربط كل الخطوات
├── leads.csv              # النتائج
├── requirements.txt       # المكتبات
└── templates/
    └── outreach.html      # قالب الايميل
```

---

## المكتبات المطلوبة

```
requests              # HTTP requests
beautifulsoup4        # HTML parsing
pandas                # Data management
smtplib (built-in)    # Email sending
jinja2                # Email templates
outscraper (optional) # Official API client
```

---

## التكلفة الإجمالية

| العنصر | التكلفة |
|---|---|
| Outscraper | مجاني (100 طلب/شهر) |
| Gmail SMTP | مجاني |
| Python | مجاني |
| الاستضافة | محلي (مجاني) |
| **المجموع** | **$0/شهر** |

---

## سير التنفيذ

```
python main.py --city "Dubai" --type "dental clinic" --limit 50
```

**النتيجة:**
```
[1/3] Finding businesses... 50 found
[2/3] Analyzing reviews... 23 have low response rate
[3/3] Finding emails... 18 emails found
[✓] Sending emails... 18 sent

Results saved to leads.csv
Summary: 50 scanned → 23 leads → 18 emails sent
```

---

## ملاحظات مهمة

1. **لا نرسل spam** — نرسل بس لأصحاب المحلات فعلاً
2. **نحترم rate limits** — ننتظر بين كل ايميل (30 ثانية)
3. **نحفظ كل شيء** — عشان ما نرسل لنفس الشخص مرتين
4. **نخلي unsubscribe** — رابط إلغاء الاشتراك في كل ايميل

---

## بعد البناء

1. نجرب على 10 محلات أولاً
2. نشوف النتيجة ونعدّل
3. بعدها نوسع
