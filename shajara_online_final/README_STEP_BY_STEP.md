# SHAJARA – Online Starter (FINAL)

هذا الحزمة جاهزة للرفع على GitHub لحساب جديد. الملفات الموجودة:
- collectors/telegram_collector.py
- collectors/facebook_collector.py
- utils/supabase_client.py
- app/app_streamlit_online.py
- .github/workflows/collectors.yml
- requirements.txt (Streamlit app)
- collectors/requirements.txt (collector hints)
- supabase_schema.sql
- README_STEP_BY_STEP.md (هذا الملف)

## خطوات سريعة (بسيطة)
1) **افتح حساب GitHub جديد** (github.com). أنشئ Repo جديد (مثلاً `shajara-online`).
2) **ارفع ملفات هذه الحزمة** (فك zip وارفع المحتوى كما هو) إلى الريبو في نفس الهيكل.
3) **أضف GitHub Secrets** (Settings → Secrets and variables → Actions):
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - TELEGRAM_API_ID
   - TELEGRAM_API_HASH
   - TELEGRAM_STRING_SESSION
   - FB_COOKIES_JSON (إن رغبت بجمع من فيسبوك)
4) **إنشئ مشروع على Supabase** (free) ثم شغّل SQL الموجود في `supabase_schema.sql` (SQL Editor) لإنشاء جدول `posts`.
5) **شغّل الـWorkflow يدوياً** (Actions → Collectors → Run workflow) لمرة اختبارية.
6) **نشر الداشبورد**: على Streamlit Community Cloud → New app → اختر هذا الريبو → file path: `app/app_streamlit_online.py`.
   - أضف Secrets في Streamlit Settings: SUPABASE_URL & SUPABASE_ANON_KEY.
7) افتح الرابط وشارك المدير.

## أمن وحماية
- **لا ترفع** أي ملف يحتوي على مفاتيح أو string session إلى الريبو. اعمل GitHub Secrets فقط.
- إن انكشف أي secret: Regenerate (Supabase) أو Terminate sessions (Telegram) فورًا.
- استخدم حساب Facebook تجريبي أو صفحات عامة عند الإمكان.

## ملاحظة تقنية
- Collector يعمل من GitHub Actions scheduled (cron) أو يدوي عبر Run workflow.
- Data is stored centrally in Supabase (Postgres). Streamlit reads from Supabase for the dashboard.

إذا بدك، أقدر أزوّدك بصيغة رسالة جاهزة ترسلها للمدير مع الرابط والتعليمات السريعة.
