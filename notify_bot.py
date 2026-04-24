# FIX TIMEZONE PENTRU NOTIFICĂRI EXACTE
# Botul Telegram care trimite notificări la ora exactă setată de user

from datetime import datetime
import pytz
from supabase import create_client
import requests
import os
from apscheduler.schedulers.background import BackgroundScheduler

# Configurare Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Inițializare scheduler
scheduler = BackgroundScheduler()

def get_expiring_clients(user_id):
    """Obține clienții care expiră în 24h sau 3 zile"""
    try:
        response = sb.from_("clients").select("*").eq("user_id", user_id).execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching clients: {e}")
        return []

def send_telegram_notification(chat_id, message):
    """Trimite notificare pe Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload)
        print(f"Telegram notification sent to {chat_id}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def send_onesignal_notification(user_id, message):
    """Trimite notificare OneSignal push"""
    try:
        url = "https://onesignal.com/api/v1/notifications"
        headers = {
            "Authorization": f"Basic {ONESIGNAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "app_id": ONESIGNAL_APP_ID,
            "filters": [{"field": "tag", "key": "user_id", "value": user_id}],
            "headings": {"en": "Ro Mega 4K", "ro": "Ro Mega 4K"},
            "contents": {
                "en": message,
                "ro": message
            },
            "big_picture": "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&q=80"
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"OneSignal notification sent to user {user_id}")
        else:
            print(f"OneSignal error: {response.text}")
    except Exception as e:
        print(f"Error sending OneSignal notification: {e}")

def send_notifications_for_user(user_id):
    """Trimite notificări pentru un user specific"""
    try:
        # Obține profilul user-ului (notif_time și notif_timezone)
        profile_response = sb.from_("profiles").select("telegram_chat_id").eq("id", user_id).single().execute()
        profile = profile_response.data
        
        if not profile or not profile.get("telegram_chat_id"):
            return
        
        # Obține clienții care expiră
        clients = get_expiring_clients(user_id)
        
        # Filtrează clienți care expiră în 24h sau 3 zile
        from datetime import timedelta
        today = datetime.now().date()
        expiring_clients = []
        
        for client in clients:
            expiry_date = datetime.fromisoformat(client.get("expiry", "")).date()
            days_until = (expiry_date - today).days
            
            if 0 <= days_until <= 3:
                expiring_clients.append({
                    "name": client.get("name"),
                    "days": days_until
                })
        
        if not expiring_clients:
            return
        
        # Construiește mesaj
        message = f"<b>🔔 Notificări Ro Mega 4K</b>\n\n"
        message += f"<b>{len(expiring_clients)} client(i) trebuie reînnoiți:</b>\n\n"
        
        for client in expiring_clients:
            if client["days"] == 0:
                message += f"🔴 <b>{client['name']}</b> - AZI\n"
            elif client["days"] == 1:
                message += f"🔴 <b>{client['name']}</b> - MÂINE\n"
            else:
                message += f"🟡 <b>{client['name']}</b> - în {client['days']} zile\n"
        
        message += f"\n<i>Mergi în app pentru a copia mesajul WhatsApp</i>"
        
        # Trimite notificări
        chat_id = profile.get("telegram_chat_id")
        send_telegram_notification(chat_id, message)
        send_onesignal_notification(user_id, f"{len(expiring_clients)} client(i) trebuie reînnoiți azi!")
        
    except Exception as e:
        print(f"Error sending notifications for user {user_id}: {e}")

def schedule_user_notifications():
    """Programează notificări pentru toți userii la orele lor setate"""
    try:
        # Obține toți userii
        users_response = sb.from_("profiles").select("id,notif_time,notif_timezone").execute()
        users = users_response.data or []
        
        # Sterge job-urile vechi
        for job in scheduler.get_jobs():
            scheduler.remove_job(job.id)
        
        # Programează notificări pentru fiecare user
        for user in users:
            user_id = user.get("id")
            notif_time = user.get("notif_time", "09:00")  # Default 09:00
            notif_timezone = user.get("notif_timezone", "UTC")  # Default UTC
            
            if not notif_time or not notif_timezone:
                continue
            
            try:
                # Parse ora (HH:MM)
                hour, minute = map(int, notif_time.split(':'))
                
                # Convertim la UTC
                tz = pytz.timezone(notif_timezone)
                now = datetime.now(tz)
                scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                utc_scheduled = scheduled.astimezone(pytz.UTC)
                
                # Programează job-ul la ora UTC
                scheduler.add_job(
                    send_notifications_for_user,
                    'cron',
                    hour=utc_scheduled.hour,
                    minute=utc_scheduled.minute,
                    id=f"notif_{user_id}",
                    replace_existing=True,
                    args=[user_id]
                )
                
                print(f"✅ Notificare programată pentru {user_id}: {notif_time} {notif_timezone} → {utc_scheduled.hour}:{utc_scheduled.minute} UTC")
                
            except ValueError as e:
                print(f"Error parsing notif_time for user {user_id}: {e}")
                continue
        
        if not scheduler.running:
            scheduler.start()
            print("✅ Scheduler started!")
        
    except Exception as e:
        print(f"Error scheduling notifications: {e}")

# Inițializare la start
if __name__ == "__main__":
    print("🚀 Ro Mega 4K Notification Bot - Starting...")
    
    # Pornește scheduler
    if not scheduler.running:
        scheduler.start()
    
    # Programează orele inițial
    schedule_user_notifications()
    
    # Re-verifică orele din Supabase la fiecare 30 minute
    # Astfel dacă un user schimbă ora, botul o preia automat
    scheduler.add_job(
        schedule_user_notifications,
        'interval',
        minutes=30,
        id='refresh_schedules',
        replace_existing=True
    )
    print("🔄 Auto-refresh activ: orele se actualizează la fiecare 30 minute")
    
    # Keep running
    try:
        while True:
            import time
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Bot stopped.")
