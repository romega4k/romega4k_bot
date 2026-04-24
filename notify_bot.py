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
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        print(f"Telegram sent to {chat_id}: {response.status_code}")
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

def build_whatsapp_message(client_name, days_until, packages):
    """Construiește mesajul WhatsApp în formatul original"""
    if days_until < 0:
        status = "⚠️ *Serviciul tău A EXPIRAT!*"
    elif days_until == 0:
        status = "⚠️ *Serviciul tău EXPIRĂ AZI!*"
    elif days_until == 1:
        status = "⚠️ *Serviciul tău expiră MÂINE!*"
    else:
        status = f"⚠️ *Serviciul tău expiră în {days_until} zile!*"

    # Construiește lista pachete
    pkg_lines = ""
    for pkg in packages:
        label = pkg.get("label", "")
        price_s = pkg.get("ds", 0)
        price_m = pkg.get("dm", 0)
        if price_s <= 0:
            continue
        # Detectează bonus
        parts = label.split("+")
        if len(parts) == 2:
            base = parts[0].strip()
            bonus = parts[1].replace("Luni", "").replace("Lună", "").strip()
            months = int(parts[0].strip().split()[0])
            if bonus == "1":
                bonus_text = f" _(+1 GRATIS)_"
            elif bonus == "2":
                bonus_text = f" _(+2 GRATUITE)_"
            elif bonus == "3":
                bonus_text = f" _(+3 GRATUITE)_"
            elif bonus == "4":
                bonus_text = f" _(+4 GRATUITE)_"
            else:
                bonus_text = ""
            pkg_lines += f"• {months} luni → {price_m}€{bonus_text}\n"
        else:
            months = label.replace("Luni", "").replace("Lună", "").strip().split()[0]
            pkg_lines += f"• {months} lun{'ă' if months=='1' else 'i'} → {price_m}€\n"

    msg = f"""Bună ziua *{client_name}* 👋

{status}

━━━━━━━━━━━━━━━━━━
📦 *REÎNNOIRE ABONAMENT:*

{pkg_lines.strip()}

_(2-3 conexiuni pe aceeași rețea/casă)_
━━━━━━━━━━━━━━━━━━
💬 Alegeți opțiunea dorită și revenim cu detalii de plată!

— *Ro Mega 4K Team* 📺"""
    return msg

def send_notifications_for_user(user_id):
    """Trimite notificări pentru un user specific"""
    try:
        # Obține profilul user-ului
        profile_response = sb.from_("profiles").select("telegram_chat_id,notif_3d,notif_7d,notif_24h").eq("id", user_id).single().execute()
        profile = profile_response.data

        if not profile or not profile.get("telegram_chat_id"):
            print(f"No telegram_chat_id for user {user_id}")
            return

        # Obține perioadele setate
        notif_24h = profile.get("notif_24h", True)
        notif_3d = profile.get("notif_3d", True)
        notif_7d = profile.get("notif_7d", False)

        max_days = 0
        if notif_7d: max_days = 7
        if notif_3d: max_days = max(max_days, 3)
        if notif_24h: max_days = max(max_days, 1)

        if max_days == 0:
            return

        # Obține pachetele user-ului
        prices_response = sb.from_("user_prices").select("*").eq("user_id", user_id).execute()
        packages = prices_response.data or []

        # Dacă nu are pachete custom, folosește pachetele default
        if not packages:
            packages = [
                {"label": "1 Lună", "ds": 13, "dm": 15},
                {"label": "3+1 Luni", "ds": 36, "dm": 46},
                {"label": "5+2 Luni", "ds": 65, "dm": 75},
                {"label": "8+4 Luni", "ds": 100, "dm": 120},
            ]

        # Obține clienții care expiră
        all_clients = get_expiring_clients(user_id)
        today = datetime.now().date()
        expiring_clients = []

        for client in all_clients:
            try:
                expiry_date = datetime.fromisoformat(client.get("expiry", "")).date()
                days_until = (expiry_date - today).days
                if days_until <= max_days:
                    expiring_clients.append({
                        "name": client.get("name"),
                        "days": days_until
                    })
            except:
                continue

        if not expiring_clients:
            print(f"No expiring clients for user {user_id}")
            return

        chat_id = profile.get("telegram_chat_id")

        # Trimite mesaj SEPARAT pentru fiecare client (formatul original)
        for client in expiring_clients:
            msg = build_whatsapp_message(client["name"], client["days"], packages)
            send_telegram_notification(chat_id, msg)

        # OneSignal push - un singur mesaj sumar
        summary = f"🔔 {len(expiring_clients)} client(i) trebuie reînnoiți azi!"
        send_onesignal_notification(user_id, summary)

        print(f"✅ Sent {len(expiring_clients)} notifications for user {user_id}")

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
