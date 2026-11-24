# اعلان فوری (Web Push) پنل Polychem — راهنمای نصب و استقرار

## ۱. معماری

```
رویداد پنل ──► notifications.services.notify()   (همان نقطهٔ موجود؛ تراکنش ماژول)
                       │ commit
                       ▼
        hook روی Session ──► صف خروجی push_deliveries (هر اعلان × هر دستگاه، یکتا)
                       │ after_request (ترد پس‌زمینه) / cron
                       ▼
   بررسی لحظهٔ ارسال ► pywebpush (VAPID) ► FCM / Mozilla / Apple / WNS ► Service Worker ► نمایش اعلان
```

* **اعلان درون‌برنامه‌ای (زنگوله) دست‌نخورده است**؛ push فقط روی همان `notify()` سوار شده، پس هر ماژولی که اعلان می‌سازد خودکار push هم می‌گیرد.
* رویدادهای متصل: امور محوله (جدید/ارجاع/منشن)، موعد و سررسید، نتیجه و درخواست بررسی ثبت‌ها، درخواست نمونه و یادآوری‌ها، پیگیری مشتری، مکاتبات، و **مراحل درخواست خرید** (ثبت جدید ← تدارکات، ارسال برای مدیر ← مدیران، تأیید مدیر ← مالی، بازگشت مدیر/پرداخت ← تدارکات، برگشت/ابطال/تأمین/حمل/تحویل/تکمیل ← ثبت‌کننده؛ کد در `purchases/notifications.py`).
* **مرخصی**: در پنل فعلی ماژول مرخصی وجود ندارد، بنابراین تولیدکننده‌ای ندارد. دستهٔ «مرخصی» و پیشوند `LEAVE_` در `catalog.py` آماده است؛ هر نوعی که با `LEAVE_` شروع شود و با `notify()` ساخته شود خودکار push می‌شود.
* یادآوری‌های زمان‌محور (موعد امور، نمونه، پیگیری مشتری) قبلاً فقط وقتی ساخته می‌شدند که پنل باز بود؛ حالا `push-tick` (cron) آن‌ها را برای کاربران دارای دستگاه می‌سازد.

### جداول جدید (مایگریشن `b4c7d1e9f2a3`)
`push_subscriptions` (دستگاه‌ها)، `push_deliveries` (صف/تاریخچهٔ ارسال)، `notification_settings` (تنظیمات کاربر)، `notification_preferences` (دسته‌های خاموش) و یک ایندکس روی `notifications(user_id, type)`. جدول‌های موجود تغییر نکرده‌اند.

### API
| مسیر | کار |
|---|---|
| `GET /api/push/config` | فعال بودن + کلید عمومی VAPID |
| `GET/POST /api/push/subscriptions` | فهرست / ثبت دستگاه (idempotent) |
| `POST /api/push/subscriptions/detach` | حذف دستگاه این مرورگر (هنگام خروج) |
| `DELETE /api/push/subscriptions/<id>` | حذف دستگاه خود کاربر |
| `POST /api/push/subscriptions/<id>/test` | اعلان آزمایشی |
| `GET/PUT /api/notifications/preferences` | تنظیمات و دسته‌ها |
| `GET /api/notifications?q=&category=&read=` | جستجو و فیلتر مرکز اعلان‌ها |
| `POST /api/push/cron` | ورودی cron از راه HTTP (با `X-Cron-Token`) |

## ۲. نصب روی cPanel (Passenger)

۱. **آپلود کد** بک‌اند و فرانت (جایگزین فایل‌های قبلی؛ `.env` و `uploads/` را حفظ کنید).

۲. **وابستگی**: در Setup Python App، همان virtualenv برنامه:
```bash
source /home/USER/virtualenv/APP/3.x/bin/activate
pip install -r requirements.txt        # pywebpush جدید است
```
اگر نصب `cryptography` روی هاست خطا داد، از «Run Pip Install» خود cPanel یا نسخهٔ wheel استفاده کنید.

۳. **کلیدهای VAPID** (یک‌بار):
```bash
cd /home/USER/APP && flask --app wsgi push-generate-keys
```
سه خط خروجی را در **Environment Variables** برنامهٔ Python (یا `.env`) بگذارید:
`VAPID_PUBLIC_KEY`، `VAPID_PRIVATE_KEY`، `VAPID_SUBJECT=mailto:you@your-domain`.
کلید خصوصی را در گیت یا چت نگذارید. **بعد از ثبت دستگاه‌ها کلید را عوض نکنید** (همهٔ دستگاه‌ها باید دوباره فعال شوند؛ اپ خودش دوباره‌ثبت می‌کند).

۴. **مایگریشن** (قبل از آن از دیتابیس بک‌آپ بگیرید):
```bash
flask --app wsgi db upgrade
```

۵. **Restart** برنامه در Setup Python App (یا `touch tmp/restart.txt`).

۶. **Cron** (cPanel ← Cron Jobs، هر ۲ دقیقه):
```
*/2 * * * * cd /home/USER/APP && /home/USER/virtualenv/APP/3.x/bin/flask --app wsgi push-tick >> /home/USER/push-cron.log 2>&1
```
اگر دسترسی shell/cron ندارید: `PUSH_CRON_TOKEN` را با یک رشتهٔ تصادفی طولانی تنظیم کنید و از یک cron سرویس خارجی هر ۲–۵ دقیقه صدا بزنید:
`curl -fsS -X POST -H "X-Cron-Token: TOKEN" https://API-DOMAIN/api/push/cron`

۷. **فرانت**: `pnpm install && pnpm build` و انتشار خروجی. موارد زیر الزامی است:
   * **HTTPS** برای هر دو دامنه؛
   * `sw.js` و `manifest.webmanifest` با `Cache-Control: no-cache`؛
   * `sw.js` از ریشهٔ سایت (`/sw.js`) سرو شود؛
   * پروکسی/CDN نباید `/api/*` را کش کند.

۸. **بررسی**: در پنل با یک کاربر: تنظیمات ← اعلان‌ها ← «فعال‌سازی روی این دستگاه» ← «ارسال آزمایشی». سپس با کاربر دوم یک امور محوله برای او بسازید، در حالی که مرورگر بسته است.

### نکات Passenger
* ارسال با یک ترد کوتاه بعد از پاسخ انجام می‌شود؛ اگر هاست پردازه را سریع می‌کُشد، ردیف‌های `PENDING` در صف می‌مانند و `push-tick` آن‌ها را می‌فرستد. اگر ترد را نمی‌خواهید `PUSH_ASYNC=false`.
* Rate limit برنامه `memory://` است؛ با چند پردازه شمارنده‌ها مشترک نیستند (رفتار قبلی پروژه).

## ۳. پشتیبانی پلتفرم‌ها
| پلتفرم | وضعیت |
|---|---|
| Android (Chrome/Edge/Firefox) | کامل، حتی با بسته بودن مرورگر |
| Windows (Chrome/Edge/Firefox) | کامل؛ مرورگر باید در پس‌زمینه اجازهٔ اجرا داشته باشد (برای بسته بودن کامل مرورگر، گزینهٔ «ادامهٔ اجرای برنامه‌های پس‌زمینه» روشن باشد) |
| iPhone/iPad | **فقط iOS ۱۶٫۴+ و فقط پس از افزودن به صفحهٔ اصلی**؛ در Safari معمولی کار نمی‌کند. نشست برنامهٔ نصب‌شده جدا از Safari است و باید یک‌بار وارد شد |
| macOS Safari | از macOS 13 به بعد |

محدودیت‌ها: در محیط توسعه (`nuxt dev`) سرویس‌ورکر ثبت نمی‌شود، پس push فقط روی نسخهٔ build تست می‌شود؛ ارسال به سرویس‌های Apple/Google در شبکه‌هایی که این دامنه‌ها فیلتر هستند ممکن است از سرور شما نرسد (خروجی سرور باید به `fcm.googleapis.com`، `*.push.apple.com`، `updates.push.services.mozilla.com` و `*.notify.windows.com` دسترسی داشته باشد).

## ۴. امنیت
* کلید خصوصی فقط در متغیر محیطی؛ کلید عمومی تنها چیزی است که به مرورگر می‌رسد.
* **SSRF**: سرور فقط به میزبان‌های سرویس push معتبر (فهرست `PUSH_ENDPOINT_ALLOWED_HOSTS`) و فقط HTTPS درخواست می‌زند.
* هر دستگاه متعلق به یک کاربر است. با ورود کاربر دیگر روی همان مرورگر، دستگاه به او منتقل می‌شود؛ هنگام ارسال دوباره بررسی می‌شود که دستگاه هنوز مال گیرندهٔ اعلان است. هنگام خروج، دستگاه از سرور حذف و اشتراک مرورگر لغو می‌شود.
* در لحظهٔ ارسال بررسی می‌شود: اعلان خوانده نشده باشد، کاربر فعال باشد، تنظیمات او اجازه بدهد و دسترسی او به همان تسک (واحد) هنوز برقرار باشد (همان قاعدهٔ زنگوله).
* «عدم نمایش متن» فقط عنوان عمومی می‌فرستد. محتوای payload بین سرور و دستگاه رمز است (RFC 8291).
* ثبت دستگاه و آزمایش rate-limit دارند؛ endpoint مربوط به cron بدون توکن ۴۰۴ می‌دهد.
* service worker هیچ پاسخ API یا توکنی را کش نمی‌کند.

## ۵. خطا و جلوگیری از تکرار
* جفت (اعلان، دستگاه) یکتاست و ارسال با claim اتمیک انجام می‌شود؛ تکرار cron/ترد، اعلان دوباره نمی‌فرستد. روی دستگاه هم `tag` و روی سرویس push هم `Topic` یکسان است.
* `404/410` ← دستگاه غیرفعال؛ `401/403` ← غیرفعال (معمولاً کلید VAPID عوض شده)؛ `400/413` ← شکست؛ `429/5xx`/شبکه ← تلاش مجدد با فاصلهٔ ۱، ۵، ۳۰، ۱۲۰ و ۳۶۰ دقیقه و پس از `PUSH_MAX_ATTEMPTS` شکست. ۱۰ خطای پیاپی دستگاه را غیرفعال می‌کند.
* بررسی وضعیت: `SELECT status, COUNT(*) FROM push_deliveries GROUP BY status;` و ستون‌های `last_error` / `disabled_reason` در `push_subscriptions`. ردیف‌های قدیمی (۳۰ روز) خودکار پاک می‌شوند.

## ۶. عیب‌یابی
| نشانه | علت محتمل |
|---|---|
| دکمهٔ فعال‌سازی نیست / «روی سرور راه‌اندازی نشده» | سه متغیر VAPID خالی است یا برنامه Restart نشده |
| هیچ اعلانی نمی‌آید ولی `SENT` است | مجوز اعلان سیستم‌عامل/حالت Do Not Disturb؛ در Windows تنظیمات Focus |
| `FAILED` با `rejected_403` | کلید VAPID بعد از ثبت دستگاه عوض شده؛ دستگاه را دوباره فعال کنید |
| `last_error=pywebpush_missing` | `pip install -r requirements.txt` در virtualenv درست اجرا نشده |
| موعدها فقط وقتی پنل باز است می‌آید | cron اجرا نمی‌شود (`push-cron.log` را ببینید) |
| iPhone: گزینه فعال نمی‌شود | برنامه از صفحهٔ اصلی باز نشده یا iOS < 16.4 |

## ۷. فایل‌ها
**Backend (جدید):** `app/modules/notifications/{push.py, push_routes.py, cli.py, catalog.py}`، `app/modules/purchases/notifications.py`، `migrations/versions/b4c7d1e9f2a3_web_push.py`، `tests/modules/notifications/test_push.py`
**Backend (ویرایش):** `notifications/{models,services,routes}.py`، `purchases/flow.py` (یک خط در `_ev`)، `app/__init__.py`، `app/config.py`، `core/models_registry.py`، `requirements.txt`، `.env.example`
**Frontend (جدید):** `composables/usePush.ts`، `plugins/push.client.ts`، `utils/push.ts`، `utils/notificationMeta.ts`
**Frontend (ویرایش):** `public/sw.js`، `pages/notifications.vue`، `pages/(settings)/settings/notifications.vue`، `stores/{auth,notifications}.ts`، `components/header/HeaderNotifications.vue`

## ۸. تست
```bash
cd backend && pytest tests/modules/notifications -q
```
تست‌ها ارسال شبکه را شبیه‌سازی می‌کنند (ثبت و SSRF، یکتایی، تکرار، تنظیمات، ساعات سکوت، 410/403/5xx، انتقال دستگاه بین کاربران، cron، فیلترهای مرکز اعلان).
