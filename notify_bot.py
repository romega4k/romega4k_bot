"""
Ro Mega 4K — Bot Notificări Telegram
Rulează zilnic la 09:00 și trimite alerte pentru clienții ce expiră în 3 zile și 24h.
Deploy pe Render.com (gratuit).
"""

import os
import asyncio
from datetime import date, datetime
import httpx
from supabase import create_client

# ══ CONFIG din variabile de mediu ══
SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_SERVICE_KEY"]
TG_BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

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
        f"🔢 *Alege pachetul dorit — răspunde cu numărul:*\n\n"
        f"1️⃣  1 Lună ———————————— {price(prices[0], country)}\n"
        f"2️⃣  3 Luni + 1 GRATIS ——— {price(prices[1], country)}\n"
        f"3️⃣  5 Luni + 2 GRATUITE — {price(prices[2], country)}\n"
        f"4️⃣  8 Luni + 4 GRATUITE — {price(prices[3], country)}\n\n"
        f"{footer}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 Răspunde cu *1, 2, 3 sau 4* și te contactăm imediat!\n\n"
        f"— *Ro Mega 4K Team* 📺"
    )

async def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": TG_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })

async def run_check():
    print(f"[{datetime.now()}] Verificare clienți...")

    result = sb.table("clients").select("*").execute()
    clients = result.data or []

    expired   = [c for c in clients if days_until(c["expiry"]) < 0]
    urgent_24 = [c for c in clients if days_until(c["expiry"]) in (0, 1)]
    warn_3d   = [c for c in clients if days_until(c["expiry"]) in (2, 3)]

    total_alert = len(expired) + len(urgent_24) + len(warn_3d)

    if total_alert == 0:
        print("Nicio alertă astăzi.")
        return

    # ── Mesaj sumar pe Telegram ──
    lines = [f"🔔 *Ro Mega 4K — Alerte {date.today().strftime('%d.%m.%Y')}*\n"]

    if expired:
        lines.append(f"💀 *EXPIRATE ({len(expired)}):*")
        for c in expired:
            d = abs(days_until(c["expiry"]))
            lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — expirat de {d}z | {c.get('phone','fără nr')}")

    if urgent_24:
        lines.append(f"\n🔴 *24H — EXPIRĂ AZI/MÂINE ({len(urgent_24)}):*")
        for c in urgent_24:
            d = days_until(c["expiry"])
            when = "AZI" if d == 0 else "mâine"
            lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — {when} | {c.get('phone','fără nr')}")

    if warn_3d:
        lines.append(f"\n🟡 *3 ZILE ({len(warn_3d)}):*")
        for c in warn_3d:
            d = days_until(c["expiry"])
            lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — în {d} zile | {c.get('phone','fără nr')}")

    lines.append(f"\n📱 Deschide aplicația pentru a trimite mesajele WhatsApp.")
    summary = "\n".join(lines)

    await send_telegram(summary)
    print(f"Trimis sumar: {total_alert} alerte")

    # ── Mesaje individuale pentru fiecare client urgent ──
    for c in urgent_24:
        wa_msg = build_wa_message(c)
        tg_text = (
            f"📤 *Mesaj gata pentru {c['name']}*\n"
            f"📞 {c.get('phone', 'fără număr')}\n\n"
            f"Copiază și trimite pe WhatsApp:\n\n"
            f"```\n{wa_msg}\n```"
        )
        await send_telegram(tg_text)
        await asyncio.sleep(1)  # evită rate limit Telegram

    # ── Mesaje individuale pentru 3 zile ──
    for c in warn_3d:
        wa_msg = build_wa_message(c)
        tg_text = (
            f"⏰ *Reînnoire în 3 zile — {c['name']}*\n"
            f"📞 {c.get('phone', 'fără număr')}\n\n"
            f"Copiază și trimite pe WhatsApp:\n\n"
            f"```\n{wa_msg}\n```"
        )
        await send_telegram(tg_text)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_check())
