from datetime import datetime
import os
import pytz
from supabase import create_client
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def send_telegram(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
        print(f"Telegram {chat_id}: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")


def send_onesignal(user_id, message):
    try:
        url = "https://onesignal.com/api/v1/notifications"
        headers = {"Authorization": f"Basic {ONESIGNAL_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "app_id": ONESIGNAL_APP_ID,
            "filters": [{"field": "tag", "key": "user_id", "value": user_id}],
            "headings": {"en": "Ro Mega 4K"},
            "contents": {"en": message}
        }
        r = requests.post(url, json=payload, headers=headers)
        print(f"OneSignal {user_id}: {r.status_code}")
    except Exception as e:
        print(f"OneSignal error: {e}")


def notify_user(user_id, chat_id, notif_7d, notif_3d, notif_24h):
    try:
        today = datetime.now().date()
        max_days = 0
        if notif_7d:
            max_days = max(max_days, 7)
        if notif_3d:
            max_days = max(max_days, 3)
        if notif_24h:
            max_days = max(max_days, 1)
        if not max_days:
            print(f"No periods active for {user_id}")
            return

        clients = sb.from_("clients").select("name,expiry").eq("user_id", user_id).execute().data
        prices_resp = sb.from_("prices").select("*").eq("user_id", user_id).execute()
        prices = prices_resp.data if prices_resp.data else []

        if not prices:
            pkg_lines = "• 1 luna -> £13\n• 3 luni -> £36 _(+1 GRATIS)_\n• 5 luni -> £65 _(+2 GRATUITE)_\n• 8 luni -> £100 _(+4 GRATUITE)_"
        else:
            lines = []
            for p in prices:
                label = p.get("label", "")
                price = p.get("price", "")
                bonus = p.get("bonus", "")
                if bonus:
                    lines.append(f"• {label} -> £{price} _({bonus})_")
                else:
                    lines.append(f"• {label} -> £{price}")
            pkg_lines = "\n".join(lines)

        expiring = []
        for c in clients:
            try:
                days = (datetime.fromisoformat(c["expiry"]).date() - today).days
                if days <= max_days:
                    expiring.append({"name": c["name"], "days": days})
            except Exception:
                continue

        if not expiring:
            print(f"No expiring clients for {user_id}")
            return

        print(f"Found {len(expiring)} expiring clients for {user_id}")

        for client in expiring:
            name = client["name"]
            days = client["days"]
            if days < 0:
                title = f"🔴 Expirat — {name}"
                status = "⚠️ *Serviciul tau A EXPIRAT!*"
            elif days == 0:
                title = f"🔴 Expira AZI — {name}"
                status = "⚠️ *Serviciul tau EXPIRA AZI!*"
            elif days == 1:
                title = f"🔴 Reinnoire in 1 zi — {name}"
                status = "⚠️ *Serviciul tau expira MAINE!*"
            elif days <= 3:
                title = f"🟡 Reinnoire in {days} zile — {name}"
                status = f"⚠️ *Serviciul tau expira in {days} zile!*"
            else:
                title = f"🕐 Reinnoire in {days} zile — {name}"
                status = f"⚠️ *Serviciul tau expira in {days} zile!*"

            msg = (
                f"{title}\n\n"
                f"Buna ziua *{name}* 👋\n\n"
                f"{status}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 *REINNOIRE ABONAMENT:*\n\n"
                f"{pkg_lines}\n\n"
                f"*(1 conexiune / 1 adresa IP)*\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💬 Alegeti optiunea dorita si revenim cu detalii de plata!\n"
                f"— *Ro Mega 4K Team* 📺"
            )
            send_telegram(chat_id, msg)

        send_onesignal(user_id, f"🔔 {len(expiring)} client(i) trebuie reinnoiti azi!")

    except Exception as e:
        print(f"Error notify_user {user_id}: {e}")


def run_all():
    print("🚀 Ro Mega 4K Bot — running")
    try:
        users = sb.from_("profiles").select(
            "id,telegram_chat_id,notif_7d,notif_3d,notif_24h"
        ).execute().data
        print(f"Found {len(users)} users")

        for u in users:
            uid = u.get("id")
            chat_id = u.get("telegram_chat_id")
            notif_7d = u.get("notif_7d", False)
            notif_3d = u.get("notif_3d", True)
            notif_24h = u.get("notif_24h", True)

            if not chat_id:
                print(f"No chat_id for {uid}")
                continue

            notify_user(uid, chat_id, notif_7d, notif_3d, notif_24h)

    except Exception as e:
        print(f"Error run_all: {e}")
        raise

    print("✅ Done!")


if __name__ == "__main__":
    run_all()
