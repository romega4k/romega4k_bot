# FIX TIMEZONE PENTRU NOTIFICĂRI EXACTE
from datetime import datetime
import pytz
from supabase import create_client
import requests
import os
from apscheduler.schedulers.background import BackgroundScheduler

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
scheduler = BackgroundScheduler()

def get_expiring_clients(user_id):
    try:
        response = sb.from_("clients").select("*").eq("user_id", user_id).execute()
        return response.data or []
    except Exception as e:
        print(f"Error: {e}")
        return []

def send_telegram_notification(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
        print(f"Telegram sent to {chat_id}")
    except Exception as e:
        print(f"Error: {e}")

def send_onesignal_notification(user_id, message):
    try:
        url = "https://onesignal.com/api/v1/notifications"
        headers = {"Authorization": f"Basic {ONESIGNAL_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "app_id": ONESIGNAL_APP_ID,
            "filters": [{"field": "tag", "key": "user_id", "value": user_id}],
            "headings": {"en": "Ro Mega 4K"},
            "contents": {"en": message, "ro": message}
        }
        requests.post(url, json=payload, headers=headers)
        print(f"OneSignal sent to {user_id}")
    except Exception as e:
        print(f"Error: {e}")

def send_notifications_for_user(user_id):
    try:
        profile_response = sb.from_("profiles").select("telegram_chat_id").eq("id", user_id).single().execute()
        profile = profile_response.data
        
        if not profile or not profile.get("telegram_chat_id"):
            return
        
        clients = get_expiring_clients(user_id)
        today = datetime.now().date()
        expiring = []
        
        for c in clients:
            try:
                d = (datetime.fromisoformat(c.get("expiry", "")).date() - today).days
                if 0 <= d <= 3:
                    expiring.append({"name": c.get("name"), "days": d})
            except:
                continue
        
        if not expiring:
            return
        
        msg = f"🔔 {len(expiring)} client(i) trebuie reînnoiți:\n\n"
        for c in expiring:
            msg += f"• {c['name']} - {c['days']} zile\n"
        
        send_telegram_notification(profile.get("telegram_chat_id"), msg)
        send_onesignal_notification(user_id, f"{len(expiring)} client(i) trebuie reînnoiți!")
    except Exception as e:
        print(f"Error: {e}")

def schedule_notifications():
    try:
        users = sb.from_("profiles").select("id,notif_time,notif_timezone").execute().data or []
        
        for job in scheduler.get_jobs():
            scheduler.remove_job(job.id)
        
        for u in users:
            uid, time, tz = u.get("id"), u.get("notif_time", "09:00"), u.get("notif_timezone", "UTC")
            if not time or not tz:
                continue
            
            try:
                h, m = map(int, time.split(':'))
                now = datetime.now(pytz.timezone(tz))
                sched = now.replace(hour=h, minute=m, second=0, microsecond=0).astimezone(pytz.UTC)
                
                scheduler.add_job(
                    send_notifications_for_user,
                    'cron',
                    hour=sched.hour,
                    minute=sched.minute,
                    id=f"notif_{uid}",
                    replace_existing=True,
                    args=[uid]
                )
                print(f"✅ {uid}: {time} {tz} → {sched.hour}:{sched.minute} UTC")
            except:
                continue
        
        if not scheduler.running:
            scheduler.start()
            print("✅ Scheduler started!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("🚀 Bot starting...")
    schedule_notifications()
    
    scheduler.add_job(schedule_notifications, 'interval', minutes=30, id='refresh', replace_existing=True)
    
    try:
        while True:
            import time
            time.sleep(60)
    except:
        scheduler.shutdown()
