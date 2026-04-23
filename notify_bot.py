# FIX TIMEZONE PENTRU NOTIFICĂRI EXACTE

## Ce s-a adăugat pe frontend:
1. Selector fus orar în Setări - salvează `notif_timezone` în Supabase (coloana profiles)
2. Funcția loadNotifTime() - detectează timezone din browser cu `Intl.DateTimeFormat().resolvedOptions().timeZone`
3. Funcția saveNotifTime() - salvează ora + timezone

## Ce trebuie modificat pe BACKEND (notify_bot.py):

Botul Telegram trebuie să:
1. Citească `notif_time` și `notif_timezone` din tabelul profiles
2. Convertească ora setată de user (în timezone-ul lui) la UTC
3. Programeze job-ul să ruleze la ora UTC calculată

### Exemplu Python pentru conversie ora:
```python
from datetime import datetime, time
import pytz

# User a setat: notif_time="09:00", notif_timezone="Europe/Bucharest"
user_time = "09:00"  # HH:MM
user_tz = "Europe/Bucharest"

# Convertim la UTC
tz = pytz.timezone(user_tz)
# Luam ora din astazi în timezone-ul user
now = datetime.now(tz)
scheduled_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

# Convertim la UTC
utc_time = scheduled_time.astimezone(pytz.UTC)
print(f"User time: {scheduled_time}")  # 2025-04-23 09:00:00+02:00 (Bucharest)
print(f"UTC time: {utc_time}")         # 2025-04-23 07:00:00+00:00
```

### Modificări notify_bot.py:
1. Import `pytz`
2. În funcția care programează notificări zilnice, adaugă:
```python
import pytz
from datetime import datetime

# Din Supabase - citim notif_time și notif_timezone pentru fiecare user
notif_time = profile['notif_time']  # "09:00"
notif_timezone = profile['notif_timezone']  # "Europe/Bucharest"

# Parse ora
hour, minute = map(int, notif_time.split(':'))

# Convertim la UTC
tz = pytz.timezone(notif_timezone)
now = datetime.now(tz)
scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
utc_scheduled = scheduled.astimezone(pytz.UTC)

# Schedule job-ul la ora UTC
# (depinde de sistemul de scheduling folosit - APScheduler, Celery, etc)
scheduler.add_job(send_notification, 'cron', 
                  hour=utc_scheduled.hour, 
                  minute=utc_scheduled.minute,
                  id=f"notif_{user_id}")
```

## Rezultat final:
- User din România (GMT+2) setează 9:00 → notificarea vine la 9:00 ora României ✅
- User din UK (GMT) setează 9:00 → notificarea vine la 9:00 ora UK ✅
- User din USA (EST) setează 9:00 → notificarea vine la 9:00 ora USA ✅
