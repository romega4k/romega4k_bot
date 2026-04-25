// ══════════════════════════════════════════════════
//  Ro Mega 4K — Bot Telegram via GitHub Actions
//  Notificări zilnice în format WhatsApp + COPY CODE
// ══════════════════════════════════════════════════

const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY;
const BOT_TOKEN    = process.env.TELEGRAM_BOT_TOKEN;

if (!SUPABASE_URL || !SUPABASE_KEY || !BOT_TOKEN) {
  console.error('❌ Lipsesc variabilele de mediu! Verifică secretele GitHub.');
  process.exit(1);
}

const sb = createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: { persistSession: false }
});

// ── Calculează zile până la expirare ───────────────
function daysUntil(expiryStr) {
  if (!expiryStr) return null;
  const today  = new Date(); today.setHours(0,0,0,0);
  const expiry = new Date(expiryStr); expiry.setHours(0,0,0,0);
  return Math.round((expiry - today) / 86400000);
}

// ── Simbol monedă ───────────────────────────────────
function sym(price, isEuCountry) {
  if (!price) return '';
  return isEuCountry ? `€${price}` : `£${price}`;
}

// ── Emoji flag ──────────────────────────────────────
function flag(country) {
  const F = {GB:'🇬🇧',IT:'🇮🇹',FR:'🇫🇷',DE:'🇩🇪',AT:'🇦🇹',ES:'🇪🇸',
             GR:'🇬🇷',RO:'🇷🇴',NL:'🇳🇱',BE:'🇧🇪',PT:'🇵🇹',SE:'🇸🇪',
             NO:'🇳🇴',DK:'🇩🇰',FI:'🇫🇮',CH:'🇨🇭',PL:'🇵🇱',CZ:'🇨🇿',
             HU:'🇭🇺',SK:'🇸🇰',HR:'🇭🇷',IE:'🇮🇪',LU:'🇱🇺',CY:'🇨🇾',
             MT:'🇲🇹',SI:'🇸🇮',BG:'🇧🇬',LT:'🇱🇹',LV:'🇱🇻',EE:'🇪🇪'};
  return F[country] || '🌍';
}

const EU_COUNTRIES = ['IT','FR','DE','AT','ES','GR','NL','BE','PT','SE',
                      'NO','DK','FI','CH','PL','CZ','HU','SK','HR','IE',
                      'LU','CY','MT','SI','BG','LT','LV','EE','RO'];

// ── Construiește mesajul WhatsApp exact ca în aplicație ──
function buildWaMsg(client, packages) {
  const d     = daysUntil(client.expiry);
  const eu    = EU_COUNTRIES.includes(client.country);
  const multi = (client.max_con || 1) >= 2;
  const s     = n => sym(n, eu);

  let urgLine;
  if (d === null)  urgLine = `⚠️ *Serviciul tău — dată necunoscută*`;
  else if (d < 0)  urgLine = `⚠️ *Serviciul tău a EXPIRAT acum ${Math.abs(d)} ${Math.abs(d)===1?'zi':'zile'}!*`;
  else if (d === 0) urgLine = `⚠️ *Serviciul tău EXPIRă AZI!*`;
  else if (d === 1) urgLine = `⏰ *Serviciul tău expiră MÂINE!*`;
  else              urgLine = `⏰ *Serviciul tău expiră în ${d} zile*`;

  const footer = multi
    ? `_(2-3 conexiuni pe aceeași rețea/casă)_`
    : `_(1 conexiune / 1 adresă IP)_`;

  const ALL_PACKAGES = [
    {id:'1m',  label:'1 Lună',   ds:13,  dm:15,  on:true },
    {id:'2m',  label:'2 Luni',   ds:0,   dm:0,   on:false},
    {id:'3m',  label:'3 Luni',   ds:0,   dm:0,   on:false},
    {id:'3p1', label:'3+1 Luni', ds:36,  dm:46,  on:true },
    {id:'5p1', label:'5+1 Luni', ds:0,   dm:0,   on:false},
    {id:'5p2', label:'5+2 Luni', ds:65,  dm:75,  on:true },
    {id:'6m',  label:'6 Luni',   ds:0,   dm:0,   on:false},
    {id:'9p3', label:'9+3 Luni', ds:0,   dm:0,   on:false},
    {id:'8p4', label:'8+4 Luni', ds:100, dm:120, on:true },
    {id:'12m', label:'12 Luni',  ds:0,   dm:0,   on:false},
  ];

  let pkgLines = '';
  ALL_PACKAGES.forEach(p => {
    const pkg  = packages[p.id];
    const isOn = pkg ? pkg.on : p.on;
    if (!isOn) return;
    const price = multi ? (pkg ? pkg.multi : p.dm) : (pkg ? pkg.single : p.ds);
    if (!price) return;
    let bonus = '';
    if (p.label.includes('+')) {
      const n = parseInt(p.label.split('+')[1]);
      if (n === 1)      bonus = ' _(+1 GRATIS)_';
      else if (n === 2) bonus = ' _(+2 GRATUITE)_';
      else if (n === 3) bonus = ' _(+3 GRATUITE)_';
      else if (n === 4) bonus = ' _(+4 GRATUITE)_';
    }
    pkgLines += `• ${p.label} → ${s(price)}${bonus}\n`;
  });

  if (!pkgLines) {
    const [a,b,c2,dd] = multi ? [15,46,75,120] : [13,36,65,100];
    pkgLines = `• 1 Lună → ${s(a)}\n• 3+1 Luni → ${s(b)} _(+1 GRATIS)_\n• 5+2 Luni → ${s(c2)} _(+2 GRATUITE)_\n• 8+4 Luni → ${s(dd)} _(+4 GRATUITE)_\n`;
  }

  return `Bună ziua *${client.name}* 👋\n\n${urgLine}\n\n━━━━━━━━━━━━━━━━━━\n📦 *REÎNNOIRE ABONAMENT:*\n\n${pkgLines}\n${footer}\n━━━━━━━━━━━━━━━━━━\n💬 Alegeți opțiunea dorită și revenim cu detalii de plată!\n\n— *Ro Mega 4K Team* 📺`;
}

// ── Escape HTML pentru Telegram ─────────────────────
function esc(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Trimite mesaj simplu Telegram ───────────────────
async function tgSend(chatId, text, extra = {}) {
  const res = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML', ...extra })
  });
  const data = await res.json();
  if (!data.ok) console.error(`❌ Telegram error:`, data.description);
  return data.ok;
}

// ── MAIN ────────────────────────────────────────────
async function main() {
  console.log('🚀 Bot pornit —', new Date().toISOString());

  const currentHourUTC = new Date().getUTCHours();
  const isManual = process.env.GITHUB_EVENT_NAME === 'workflow_dispatch';
  console.log(`⏰ Ora curentă UTC: ${currentHourUTC}:00`);
  if (isManual) console.log('🔧 Run manual — se trimit notificări indiferent de oră');

  const { data: profiles, error: profErr } = await sb
    .from('profiles')
    .select('id, telegram_chat_id, full_name, notif_time, notif_timezone, notif_7d, notif_3d, notif_24h, prices')
    .not('telegram_chat_id', 'is', null)
    .neq('telegram_chat_id', '');

  if (profErr) { console.error('❌ Profiles error:', profErr.message); process.exit(1); }
  console.log(`👥 Useri cu Telegram: ${profiles?.length || 0}`);
  if (!profiles?.length) { console.log('⚠️ Niciun user. Ieșire.'); return; }

  let totalSent = 0;

  for (const profile of profiles) {
    const chatId = profile.telegram_chat_id;
    const notifH = parseInt(profile.notif_time ?? '9', 10);
    const tz     = profile.notif_timezone || 'UTC';
    // Dacă e NULL în Supabase = dezactivat (false), nu activat
    const want7d = profile.notif_7d  === true;
    const want3d = profile.notif_3d  === true;
    const want1d = profile.notif_24h === true;

    let targetHourUTC = notifH;
    try {
      const now = new Date();
      const localMs = new Date(now.toLocaleString('en-US', { timeZone: tz })).getTime();
      const utcMs2  = new Date(now.toLocaleString('en-US', { timeZone: 'UTC' })).getTime();
      const offsetH = Math.round((localMs - utcMs2) / 3600000);
      targetHourUTC = ((notifH - offsetH) % 24 + 24) % 24;
    } catch(e) { console.warn(`⚠️ Timezone invalid "${tz}"`); }

    console.log(`\n👤 ${profile.id} | ora: ${notifH}:00 ${tz} → ${targetHourUTC}:00 UTC | acum: ${currentHourUTC}:00`);

    if (!isManual && currentHourUTC !== targetHourUTC) {
      console.log(`⏭️  Sărim — nu e ora notificării (${targetHourUTC}:00 UTC).`);
      continue;
    }

    console.log(`🔕 want7d: ${want7d} | want3d: ${want3d} | want1d: ${want1d}`);
    console.log(`🔛 notif_7d: ${profile.notif_7d} | notif_3d: ${profile.notif_3d} | notif_24h: ${profile.notif_24h}`);

    const packages = (profile.prices?.packages) || {};

    const { data: clients, error: cliErr } = await sb
      .from('clients')
      .select('name, phone, expiry, country, max_con')
      .eq('user_id', profile.id);

    if (cliErr) { console.error('❌ Clienți error:', cliErr.message); continue; }
    console.log(`📋 Clienți: ${clients?.length || 0}`);

    const expired=[], in1d=[], in3d=[], in7d=[];
    for (const c of (clients || [])) {
      const d = daysUntil(c.expiry);
      if (d === null) continue;
      if (d < 0)               expired.push(c);          // expirați: mereu incluși
      else if (d <= 1 && want1d) in1d.push(c);           // 24h: doar dacă ON
      else if (d <= 3 && want3d) in3d.push(c);           // 3 zile: doar dacă ON
      else if (d <= 7 && want7d) in7d.push(c);           // 7 zile: doar dacă ON
    }

    const sortAsc = (a,b) => new Date(a.expiry) - new Date(b.expiry);
    [expired, in1d, in3d, in7d].forEach(arr => arr.sort(sortAsc));
    const allAlerts = [...expired, ...in1d, ...in3d, ...in7d];

    console.log(`🔔 ${expired.length} expirate | ${in1d.length} în 24h | ${in3d.length} în 3z | ${in7d.length} în 7z`);

    if (allAlerts.length === 0) {
      await tgSend(chatId, `✅ <b>Ro Mega 4K — Totul în regulă!</b>\n\nNu ai clienți care expiră în curând.\n\n<i>— Ro Mega 4K Manager 📺</i>`);
      totalSent++;
      continue;
    }

    let summary = `📺 <b>Ro Mega 4K — Raport zilnic</b>\n`;
    if (profile.full_name) summary += `👤 ${esc(profile.full_name)}\n`;
    summary += `\n`;
    if (expired.length) summary += `🔴 <b>${expired.length} expirat${expired.length>1?'e':''}</b>\n`;
    if (in1d.length)    summary += `🟠 <b>${in1d.length} expiră azi/mâine</b>\n`;
    if (in3d.length)    summary += `🟡 <b>${in3d.length} expiră în 2-3 zile</b>\n`;
    if (in7d.length)    summary += `🔵 <b>${in7d.length} expiră în 4-7 zile</b>\n`;
    summary += `\n<i>Mesajele WhatsApp gata de trimis 👇</i>`;
    await tgSend(chatId, summary);

    for (const c of allAlerts) {
      const d   = daysUntil(c.expiry);
      const fl  = flag(c.country);
      let label;
      if (d < 0)       label = `🔴 Reînnoire în ${Math.abs(d)}z — ${fl} <b>${esc(c.name)}</b>`;
      else if (d === 0) label = `🟠 Reînnoire AZI — ${fl} <b>${esc(c.name)}</b>`;
      else if (d === 1) label = `🟠 Reînnoire MÂINE — ${fl} <b>${esc(c.name)}</b>`;
      else if (d <= 3)  label = `🟡 Reînnoire în ${d}z — ${fl} <b>${esc(c.name)}</b>`;
      else              label = `🔵 Reînnoire în ${d}z — ${fl} <b>${esc(c.name)}</b>`;
      if (c.phone) label += `\n📱 ${esc(c.phone)}`;

      await tgSend(chatId, label);

      // Tap pe textul din <code> = copiat instant în Telegram
      const waMsg  = buildWaMsg(c, packages);
      const waText = `📋 <b>Copiază și trimite pe WhatsApp:</b>\n<i>(apasă pe text pentru a copia)</i>\n\n<code>${esc(waMsg)}</code>`;

      await tgSend(chatId, waText);

      totalSent++;
      console.log(`  inclusya ${c.name}`);
      await new Promise(r => setTimeout(r, 400));
    }
  }

  console.log(`\n🏁 Gata! Mesaje trimise: ${totalSent}`);
}

main().catch(err => {
  console.error('💥 Eroare fatală:', err);
  process.exit(1);
});
