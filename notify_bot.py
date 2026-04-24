from datetime import datetime
import pytz
from supabase import create_client
import requests
import os
from apscheduler.schedulers.background import BackgroundScheduler

SUPABASE_URL = os.getenv(“SUPABASE_URL”)
SUPABASE_KEY = os.getenv(“SUPABASE_KEY”)
TELEGRAM_BOT_TOKEN = os.getenv(“TELEGRAM_BOT_TOKEN”)
ONESIGNAL_APP_ID = os.getenv(“ONESIGNAL_APP_ID”)
ONESIGNAL_API_KEY = os.getenv(“ONESIGNAL_API_KEY”)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
scheduler = BackgroundScheduler()

def send_telegram(chat_id, message):
try:
url = f”https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage”
r = requests.post(url, json={“chat_id”: chat_id, “text”: message, “parse_mode”: “Markdown”})
print(f”Telegram {chat_id}: {r.status_code}”)
except Exception as e:
print(f”Telegram error: {e}”)

def send_onesignal(user_id, message):
try:
url = “https://onesignal.com/api/v1/notifications”
headers = {“Authorization”: f”Basic {ONESIGNAL_API_KEY}”, “Content-Type”: “application/json”}
payload = {
“app_id”: ONESIGNAL_APP_ID,
“filters”: [{“field”: “tag”, “key”: “user_id”, “value”: user_id}],
“headings”: {“en”: “Ro Mega 4K”},
“contents”: {“en”: message}
}
r = requests.post(url, json=payload, headers=headers)
print(f”OneSignal {user_id}: {r.status_code} - {r.text}”)
except Exception as e:
print(f”OneSignal error: {e}”)

def notify_user(user_id, chat_id):
try:
today = datetime.now().date()
clients = sb.from_(“clients”).select(“name,expiry”).eq(“user_id”, user_id).execute().data or []

```
    expiring = []
    for c in clients:
        try:
            days = (datetime.fromisoformat(c["expiry"]).date() - today).days
            if days <= 3:
                expiring.append({"name": c["name"], "days": days})
        except:
            continue

    if not expiring:
        print(f"No expiring clients for {user_id}")
        return

    print(f"Found {len(expiring)} expiring clients for {user_id}")

    for c in expiring:
        name = c["name"]
        days = c["days"]

        if days < 0:
            status = "⚠️ *Serviciul tău A EXPIRAT!*"
        elif days == 0:
            status = "⚠️ *Serviciul tău EXPIRĂ AZI!*"
        elif days == 1:
            status = "⚠️ *Serviciul tău expiră MÂINE!*"
        else:
            status = f"⚠️ *Serviciul tău expiră în {days} zile!*"

        msg = f"""Bună ziua *{name}* 👋
```

{status}

━━━━━━━━━━━━━━━━━━
📦 *REÎNNOIRE ABONAMENT:*

• 1 lună → 15€
• 3 luni → 46€ *(+1 GRATIS)*
• 5 luni → 75€ *(+2 GRATUITE)*
• 8 luni → 120€ *(+4 GRATUITE)*

*(2-3 conexiuni pe aceeași rețea/casă)*
━━━━━━━━━━━━━━━━━━
💬 Alegeți opțiunea dorită și revenim cu detalii de plată!

— *Ro Mega 4K Team* 📺”””

```
        send_telegram(chat_id, msg)

    send_onesignal(user_id, f"🔔 {len(expiring)} client(i) trebuie reînnoiți azi!")

except Exception as e:
    print(f"Error notify_user {user_id}: {e}")
```

def schedule_all():
try:
print(“🔄 Refreshing schedules…”)
users = sb.from_(“profiles”).select(“id,notif_time,notif_timezone,telegram_chat_id”).execute().data or []
print(f”Found {len(users)} users”)

```
    for job in scheduler.get_jobs():
        if job.id != 'refresh':
            scheduler.remove_job(job.id)

    for u in users:
        uid = u.get("id")
        chat_id = u.get("telegram_chat_id")
        notif_time = u.get("notif_time") or "09:00"
        notif_tz = u.get("notif_timezone") or "UTC"

        if not chat_id:
            print(f"No chat_id for {uid}")
            continue

        try:
            h, m = map(int, notif_time.split(':'))
            tz = pytz.timezone(notif_tz)
            now = datetime.now(tz)
            sched = now.replace(hour=h, minute=m, second=0, microsecond=0).astimezone(pytz.UTC)

            scheduler.add_job(
                notify_user,
                'cron',
                hour=sched.hour,
                minute=sched.minute,
                id=f"notif_{uid}",
                replace_existing=True,
                args=[uid, chat_id]
            )
            print(f"✅ {uid}: {notif_time} {notif_tz} → {sched.hour}:{sched.minute:02d} UTC")

        except Exception as e:
            print(f"Error scheduling {uid}: {e}")

except Exception as e:
    print(f"Error schedule_all: {e}")
```

if **name** == “**main**”:
print(“🚀 Ro Mega 4K Bot Starting…”)

```
scheduler.start()
print("✅ Scheduler started!")

schedule_all()

scheduler.add_job(schedule_all, 'interval', minutes=5, id='refresh', replace_existing=True)
print("🔄 Auto-refresh la fiecare 5 minute")

try:
    while True:
        import time
        time.sleep(60)
except:
    scheduler.shutdown()
    print("Bot stopped.")
```
