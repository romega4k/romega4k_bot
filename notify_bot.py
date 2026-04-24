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

DEFAULT_PKG_LINES = "• 1 luna -> £13\n• 3 luni -> £36 (+1 GRATIS)\n• 5 luni -> £65 (+2 GRATUITE)\n• 8 luni -> £100 (+4 GRATUITE)"


def escape_html(text):
    """Scapa caracterele speciale HTML pentru Telegram HTML mode."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
        result = r.json()
        if result.get("ok"):
            print(f"Telegram {chat_id}: OK (msg_id={result['result']['message_id']})")
        else:
            print(f"Telegram {chat_id}: ERROR {result}")
        return result.get("ok", False)
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def send_onesignal(user_id, message):
    if not ONESIGNAL_APP_ID or not ONESIGNAL_API_KEY:
        return
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


def get_pkg_lines(user_id):
    try:
        resp = sb.from_("prices").select("*").eq("user_id", user_id).execute()
        prices = resp.data if resp.data else []
        if not prices:
            return DEFAULT_PKG_LINES
        lines = []
        for p in prices:
            label = escape_html(p.get("label", ""))
            price = escape_html(p.get("price", ""))
            bonus = escape_html(p.get("bonus", ""))
            if bonus:
                lines.append(f"• {label} -> £{price} <i>({bonus})</i>")
            else:
                lines.append(f"• {label} -> £{price}")
        return "\n".join(lines)
    except Exception as e:
        print(f"prices table error (using default): {e}")
        return DEFAULT_PKG_LINES


def notify_user(user_id, chat_id, notif_7d, notif_3d, notif_24h):
    today = datetime.now().date()

    max_days = 0
    if notif_7d:
        max_days = max(max_days, 7)
    if notif_3d:
        max_days = max(max_days, 3)
    if notif_24h:
        max_days = max(max_days, 1)
    if not max_days:
        max_days = 3

    try:
        clients = sb.from_("clients").select("name,expiry").eq("user_id", user_id).execute().data
    except Exception as e:
        print(f"Error fetching clients for {user_id}: {e}")
        return

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

    pkg_lines = get_pkg_lines(user_id)
    sent_ok = 0
    sent_err = 0

    for client in expiring:
        name = escape_html(client["name"])
        days = client["days"]

        if days < 0:
            title = f"🔴 Expirat — {name}"
            status = "⚠️ <b>Serviciul tau A EXPIRAT!</b>"
        elif days == 0:
            title = f"🔴 Expira AZI — {name}"
            status = "⚠️ <b>Serviciul tau EXPIRA AZI!</b>"
        elif days == 1:
            title = f"🔴 Reinnoire in 1 zi — {name}"
            status = "⚠️ <b>Serviciul tau expira MAINE!</b>"
        elif days <= 3:
            title = f"🟡 Reinnoire in {days} zile — {name}"
            status = f"⚠️ <b>Serviciul tau expira in {days} zile!</b>"
        else:
            title = f"🕐 Reinnoire in {days} zile — {name}"
            status = f"⚠️ <b>Serviciul tau expira in {days} zile!</b>"

        msg = (
            f"<b>{title}</b>\n\n"
            f"Buna ziua <b>{name}</b> 👋\n\n"
            f"{status}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>REINNOIRE ABONAMENT:</b>\n\n"
            f"{pkg_lines}\n\n"
            f"<i>(1 conexiune / 1 adresa IP)</i>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 Alegeti optiunea dorita si revenim cu detalii de plata!\n"
            f"— <b>Ro Mega 4K Team</b> 📺"
        )

        if send_telegram(chat_id, msg):
            sent_ok += 1
        else:
            sent_err += 1

    print(f"Sent: {sent_ok} OK, {sent_err} errors")
    send_onesignal(user_id, f"🔔 {len(expiring)} client(i) trebuie reinnoiti azi!")


def should_notify_now(notif_time, notif_tz):
    try:
        tz = pytz.timezone(notif_tz or "UTC")
        now_local = datetime.now(tz)
        h, m = map(int, (notif_time or "09:00").split(":"))
        now_min = now_local.hour * 60 + now_local.minute
        target_min = h * 60 + m
        diff = abs(now_min - target_min)
        diff = min(diff, 1440 - diff)
        print(f"  Time: {notif_time} {notif_tz} | Now: {now_local.strftime('%H:%M')} | Diff: {diff}min")
        return diff <= 59
    except Exception as e:
        print(f"  Timezone error: {e}, sending anyway")
        return True


def run_all():
    print("🚀 Ro Mega 4K Bot — hourly check")
    try:
        users = sb.from_("profiles").select(
            "id,telegram_chat_id,notif_time,notif_timezone,notif_7d,notif_3d,notif_24h"
        ).execute().data
        print(f"Found {len(users)} users")

        for u in users:
            uid = u.get("id")
            chat_id = u.get("telegram_chat_id")
            notif_time = u.get("notif_time") or "09:00"
            notif_tz = u.get("notif_timezone") or "UTC"
            notif_7d = u.get("notif_7d", False)
            notif_3d = u.get("notif_3d", True)
            notif_24h = u.get("notif_24h", True)

            print(f"\nUser {uid}: chat_id={chat_id}, time={notif_time}, tz={notif_tz}")

            if not chat_id:
                print(f"  No Telegram chat_id, skipping")
                continue

            if should_notify_now(notif_time, notif_tz):
                print(f"  -> IN WINDOW - Sending notifications")
                notify_user(uid, chat_id, notif_7d, notif_3d, notif_24h)
            else:
                print(f"  -> Not time yet, skipping")

    except Exception as e:
        print(f"Error run_all: {e}")
        raise

    print("\n✅ Done!")


if __name__ == "__main__":
    run_all()
