"""
Ro Mega 4K — Bot Notificări
Trimite notificări Telegram + OneSignal push pentru fiecare user.
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
ONESIGNAL_KEY    = os.environ.get("ONESIGNAL_API_KEY", "")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

EU_COUNTRIES = {"IT","FR","DE","AT","ES","GR","NL","BE","PT","SE","NO","DK",
                "FI","CH","PL","CZ","HU","SK","HR","IE","LU","CY","MT","SI",
                "BG","LT","LV","EE","EU"}

def days_until(expiry_str):
    return (date.fromisoformat(expiry_str) - date.today()).days

def is_eu(country):
    return (country or "GB") in EU_COUNTRIES

def flag(country):
    flags = {"GB":"🇬🇧","IT":"🇮🇹","FR":"🇫🇷","DE":"🇩🇪","AT":"🇦🇹","ES":"🇪🇸",
             "GR":"🇬🇷","RO":"🇷🇴","NL":"🇳🇱","BE":"🇧🇪","PT":"🇵🇹","SE":"🇸🇪",
             "NO":"🇳🇴","DK":"🇩🇰","FI":"🇫🇮","CH":"🇨🇭","PL":"🇵🇱","CZ":"🇨🇿",
             "HU":"🇭🇺","SK":"🇸🇰","HR":"🇭🇷","IE":"🇮🇪","BG":"🇧🇬"}
    return flags.get(country or "GB", "🌍")

def bold_num(n):
    m = {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵'}
    return ''.join(m.get(c,c) for c in str(n))

def sym(n, eu):
    return f"{bold_num(n)}€" if eu else f"£{bold_num(n)}"

def build_wa_message(c, user_packages=None):
    d = days_until(c["expiry"])
    multi = (c.get("max_con") or 1) >= 2
    eu = is_eu(c.get("country","GB"))
    country = c.get("country","GB")

    if d < 0:
        urg = f"⚠️ *Serviciul tău a EXPIRAT acum {abs(d)} {'zi' if abs(d)==1 else 'zile'}!*"
    elif d == 0:
        urg = "⚠️ *Serviciul tău EXPIRĂ AZI!*"
    elif d == 1:
        urg = "⏰ *Serviciul tău expiră MÂINE!*"
    else:
        urg = f"⏰ *Serviciul tău expiră în {d} zile*"

    # Build package lines from user's custom packages
    pkg_lines = ""
    if user_packages and user_packages.get("packages"):
        pkgs = user_packages["packages"]
        pkg_order = [
            ("1m","1 Lună"),("2m","2 Luni"),("3m","3 Luni"),("3p1","3+1 Luni"),
            ("5p1","5+1 Luni"),("5p2","5+2 Luni"),("6m","6 Luni"),
            ("8p4","8+4 Luni"),("9p3","9+3 Luni"),("12m","12 Luni"),
        ]
        for pid, plabel in pkg_order:
            pkg = pkgs.get(pid)
            if not pkg or not pkg.get("on"):
                continue
            price = pkg.get("multi" if multi else "single", 0)
            if price:
                pkg_lines += f"• {plabel} → {sym(price, eu)}\n"

    # Fallback to defaults
    if not pkg_lines:
        prices = [15,46,75,120] if multi else [13,36,65,100]
        pkg_lines = (
            f"• 1 lună → {sym(prices[0], eu)}\n"
            f"• 3+1 luni → {sym(prices[1], eu)}\n"
            f"• 5+2 luni → {sym(prices[2], eu)}\n"
            f"• 8+4 luni → {sym(prices[3], eu)}\n"
        )

    footer = "_(2-3 televizoare pe aceeași rețea/casă)_" if multi else "_(1 televizor / 1 adresă IP)_"

    return (
        f"Bună ziua *{c['name']}* 👋\n\n"
        f"{urg}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 *REÎNNOIRE ABONAMENT:*\n\n"
        f"{pkg_lines}\n"
        f"{footer}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 Alegeți opțiunea dorită și revenim cu detalii de plată!\n\n"
        f"— *Ro Mega 4K Team* 📺"
    )

async def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
        return r.json()

async def send_push(user_id, title, message, url="https://manager-clienti-pro.netlify.app/#notif"):
    if not ONESIGNAL_KEY:
        return
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            "https://api.onesignal.com/notifications",
            headers={"Authorization": f"Key {ONESIGNAL_KEY}", "Content-Type": "application/json"},
            json={
                "app_id": ONESIGNAL_APP_ID,
                "filters": [{"field":"tag","key":"user_id","relation":"=","value":user_id}],
                "headings": {"en": title, "ro": title},
                "contents": {"en": message, "ro": message},
                "url": url
            }
        )

async def run_check():
    print(f"[{datetime.now()}] Verificare clienți...")

    # Get all profiles
    profiles = sb.table("profiles").select("id, telegram_chat_id, full_name, prices").execute().data or []

    if not profiles:
        print("Niciun profil găsit.")
        return

    for profile in profiles:
        user_id   = profile["id"]
        chat_id   = profile.get("telegram_chat_id","")
        user_name = profile.get("full_name") or "User"
        user_prices = profile.get("prices") or {}

        # Get clients for this user
        clients = sb.table("clients").select("*").eq("user_id", user_id).execute().data or []

        expired   = [c for c in clients if days_until(c["expiry"]) < 0]
        urgent_24 = [c for c in clients if days_until(c["expiry"]) in (0,1)]
        warn_3d   = [c for c in clients if days_until(c["expiry"]) in (2,3)]
        all_alert = urgent_24 + warn_3d

        total = len(expired) + len(urgent_24) + len(warn_3d)
        if total == 0:
            print(f"[{user_name}] Nicio alertă.")
            continue

        print(f"[{user_name}] {total} alerte — urgent:{len(urgent_24)}, 3zile:{len(warn_3d)}, expirat:{len(expired)}")

        # ── TELEGRAM ──
        if chat_id:
            # Main summary message
            lines = [f"🔔 *Notificări Ro Mega 4K*\n"]

            if len(all_alert) > 0:
                lines.append(f"{len(all_alert)} {'client' if len(all_alert)==1 else 'clienți'} trebuie reînnoiți:\n")
                for c in urgent_24:
                    d = days_until(c["expiry"])
                    when = "AZI" if d==0 else "mâine"
                    lines.append(f"🔴 *{c['name']}* - {when}")
                for c in warn_3d:
                    d = days_until(c["expiry"])
                    lines.append(f"🟡 *{c['name']}* - în {d} zile")

            if expired:
                lines.append(f"\n💀 *Expirați ({len(expired)}):*")
                for c in expired[:5]:
                    d = abs(days_until(c["expiry"]))
                    lines.append(f"  {flag(c.get('country','GB'))} {c['name']} — {d}z | {c.get('phone','fără nr')}")

            lines.append(f"\n📱 Mergi în app pentru a copia mesajul WhatsApp")
            lines.append(f"👉 https://manager-clienti-pro.netlify.app")

            result = await send_telegram(chat_id, "\n".join(lines))
            if result.get("ok"):
                print(f"[{user_name}] ✅ Telegram trimis")
            else:
                print(f"[{user_name}] ❌ Telegram eroare: {result}")

            # Individual WA messages for urgent clients
            for c in urgent_24 + warn_3d:
                wa_msg = build_wa_message(c, user_prices)
                d = days_until(c["expiry"])
                label = "AZI" if d==0 else "mâine" if d==1 else f"în {d} zile"
                tg = (
                    f"📤 *{c['name']}* — expiră {label}\n"
                    f"📞 {c.get('phone','fără număr')} {flag(c.get('country','GB'))}\n\n"
                    f"```\n{wa_msg}\n```"
                )
                await send_telegram(chat_id, tg)
                await asyncio.sleep(0.5)

        # ── ONESIGNAL PUSH ──
        if all_alert or expired:
            # Build push message
            names_urgent = [c["name"] for c in urgent_24]
            names_3d = [c["name"] for c in warn_3d]
            
            push_parts = []
            if names_urgent:
                push_parts.append("🔴 " + ", ".join(names_urgent[:3]))
            if names_3d:
                push_parts.append("🟡 " + ", ".join(names_3d[:3]))
            
            push_title = f"🔔 Ro Mega 4K — {total} alerte"
            push_msg = " · ".join(push_parts) if push_parts else f"{total} clienți necesită atenție"
            
            # Build URL with all urgent client IDs
            all_ids = ",".join([str(c.get("id","")) for c in urgent_24+warn_3d])
            push_url = f"https://manager-clienti-pro.netlify.app/#urgent-{all_ids}"
            
            await send_push(user_id, push_title, push_msg, push_url)
            print(f"[{user_name}] ✅ Push trimis")

        await asyncio.sleep(1)

    print("✅ Gata!")

if __name__ == "__main__":
    asyncio.run(run_check())
