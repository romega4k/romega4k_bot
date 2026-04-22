"""
Ro Mega 4K — Bot Notificări Telegram + OneSignal Push
Trimite notificări personalizate fiecărui user pe Telegram SI push notifications.
"""

import os
import asyncio
from datetime import date, datetime
import httpx
from supabase import create_client

SUPABASE_URL     = os.environ["SUPABASE_URL"]
SUPABASE_KEY     = os.environ["SUPABASE_SERVICE_KEY"]
TG_BOT_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
ONESIGNAL_APP_ID = "ed44b50b-7a45-47d5-bf64-15ba99836e30"
ONESIGNAL_KEY    = os.environ["ONESIGNAL_API_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def days_until(expiry_str: str) -> int:
    today = date.today()
    exp   = date.fromisoformat(expiry_str)
    return (exp - today).days

def flag(country: str) -> str:
    flags = {"GB":"🇬🇧","IT":"🇮🇹","FR":"🇫🇷","DE":"🇩🇪","AT":"🇦🇹","ES":"🇪🇸","GR":"🇬🇷","RO":"🇷🇴"}
    return flags.get(country or "GB", "🌍")

def is_eu(country: str) -> bool:
    return country not in ("GB", "RO", None, "")

def bold_num(n: int) -> str:
    bold = {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵'}
    return ''.join(bold.get(c, c) for c in str(n))

def price(n: int, country: str) -> str:
    if is_eu(country):
        return f"{bold_num(n)}€"
    return f"£{bold_num(n)}"

def build_wa_message(c: dict) -> str:
    d     = days_until(c["expiry"])
    multi = (c.get("max_con") or 1) >= 2
    eu    = is_eu(c.get("country", "GB"))

    if d < 0:
        urg = f"⚠️ *Serviciul tău a EXPIRAT acum {abs(d)} {'zi' if abs(d)==1 else 'zile'}!*"
    elif d == 0:
        urg = "⚠️ *Serviciul tău EXPIRĂ AZI!*"
    elif d == 1:
        urg = "⏰ *Serviciul tău expiră MÂINE!*"
    else:
        urg = f"⏰ *Serviciul tău expiră în {d} zile*"

    country = c.get("country", "GB")
    prices  = [15,46,75,120] if multi else [13,36,65,100]
    footer  = "_(2-3 televizoare pe aceeași rețea/casă)_" if multi else "_(1 televizor / 1 adresă IP)_"

    return (
        f"Bună ziua *{c['name']}* 👋\n\n"
        f"{urg}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 *REÎNNOIRE ABONAMENT:*\n\n"
        f"• 1 lună → {price(prices[0], country)}\n"
        f"• 3 luni → {price(prices[1], country)} _(+1 GRATIS)_\n"
        f"• 5 luni → {price(prices[2], country)} _(+2 GRATUITE)_\n"
        f"• 8 luni → {price(prices[3], country)} _(+4 GRATUITE)_\n\n"
        f"{footer}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 Alegeți opțiunea dorită și revenim cu detalii de plată!\n\n"
        f"— *Ro Mega 4K Team* 📺"
    )

async def send_telegram(chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })

async def send_push(user_id: str, title: str, message: str, url: str = "https://manager-clienti-pro.netlify.app"):
    """Trimite push notification prin OneSignal către un user specific"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.onesignal.com/notifications",
            headers={
                "Authorization": f"Key {ONESIGNAL_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "app_id": ONESIGNAL_APP_ID,
                "filters": [
                    {"field": "tag", "key": "user_id", "relation": "=", "value": user_id}
                ],
                "headings": {"en": title, "ro": title},
                "contents": {"en": message, "ro": message},
                "url": url,
                "web_push_topic": "expiry_alert"
            }
        )
        return resp.json()

async def run_check():
    print(f"[{datetime.now()}] Verificare clienți pentru toți userii...")

    profiles_result = sb.table("profiles").select("id, telegram_chat_id, full_name").execute()
    profiles = profiles_result.data or []

    if not profiles:
        print("Niciun user găsit.")
        return

    print(f"Găsiți {len(profiles)} useri.")

    for profile in profiles:
        user_id   = profile["id"]
        chat_id   = profile.get("telegram_chat_id", "")
        user_name = profile.get("full_name") or "User"

        result  = sb.table("clients").select("*").eq("user_id", user_id).execute()
        clients = result.data or []

        expired   = [c for c in clients if days_until(c["expiry"]) < 0]
        urgent_24 = [c for c in clients if days_until(c["expiry"]) in (0, 1)]
        warn_3d   = [c for c in clients if days_until(c["expiry"]) in (2, 3)]

        total_alert = len(expired) + len(urgent_24) + len(warn_3d)

        if total_alert == 0:
            print(f"[{user_name}] Nicio alertă.")
            continue

        print(f"[{user_name}] {total_alert} alerte — trimitem notificări...")

        # ── PUSH NOTIFICATION ──
        if expired:
            push_msg = f"💀 {len(expired)} expirați"
            if urgent_24:
                push_msg += f" · 🔴 {len(urgent_24)} azi/mâine"
            if warn_3d:
                push_msg += f" · ⚡ {len(warn_3d)} în 3 zile"
            
            await send_push(
                user_id=user_id,
                title=f"🔔 Ro Mega 4K — {total_alert} alerte",
                message=push_msg
            )
        
        if urgent_24:
            names = ", ".join([c["name"] for c in urgent_24[:3]])
            if len(urgent_24) > 3:
                names += f" +{len(urgent_24)-3} alții"
            await send_push(
                user_id=user_id,
                title=f"🔴 Expiră azi/mâine ({len(urgent_24)})",
                message=f"{names} — trimite mesaj WhatsApp acum!"
            )

        if warn_3d:
            names = ", ".join([c["name"] for c in warn_3d[:3]])
            if len(warn_3d) > 3:
                names += f" +{len(warn_3d)-3} alții"
            await send_push(
                user_id=user_id,
                title=f"⚡ Expiră în 3 zile ({len(warn_3d)})",
                message=f"{names}"
            )

        # ── TELEGRAM (dacă are Chat ID configurat) ──
        if chat_id:
            lines = [f"🔔 *Ro Mega 4K — Alertele tale {date.today().strftime('%d.%m.%Y')}*\n"]

            if expired:
                lines.append(f"💀 *EXPIRATE ({len(expired)}):*")
                for c in expired:
                    d = abs(days_until(c["expiry"]))
                    lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — expirat de {d}z | {c.get('phone','fără nr')}")

            if urgent_24:
                lines.append(f"\n🔴 *AZI/MÂINE ({len(urgent_24)}):*")
                for c in urgent_24:
                    d = days_until(c["expiry"])
                    when = "AZI" if d == 0 else "mâine"
                    lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — {when} | {c.get('phone','fără nr')}")

            if warn_3d:
                lines.append(f"\n🟡 *3 ZILE ({len(warn_3d)}):*")
                for c in warn_3d:
                    d = days_until(c["expiry"])
                    lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — în {d} zile | {c.get('phone','fără nr')}")

            await send_telegram(chat_id, "\n".join(lines))

            for c in urgent_24 + warn_3d:
                wa_msg = build_wa_message(c)
                label = "azi/mâine" if days_until(c["expiry"]) <= 1 else "3 zile"
                tg_text = (
                    f"📤 *{c['name']}* — expiră {label}\n"
                    f"📞 {c.get('phone', 'fără număr')}\n\n"
                    f"```\n{wa_msg}\n```"
                )
                await send_telegram(chat_id, tg_text)
                await asyncio.sleep(0.5)

        await asyncio.sleep(1)

    print("Gata!")

if __name__ == "__main__":
    asyncio.run(run_check())
