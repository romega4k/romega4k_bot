// ================================================
// Ro Mega 4K - Bot Telegram via GitHub Actions
// Notificari zilnice in format WhatsApp + COPY CODE
// Timezone referinta: Europe/Bucharest (Romania)
// ================================================

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

// -- Calculează zile până la expirare --------
function daysUntil(expiryStr) {
  if (!expiryStr) return null;
  const today = new Date(); today.setHours(0,0,0,0);
  const exp   = new Date(expiryStr); exp.setHours(0,0,0,0);
  return Math.round((exp - today) / 86400000);
}

// -- Emoji steag din country code ------------
function flag(cc) {
  if (!cc || cc.length !== 2) return '';
  return [...cc.toUpperCase()].map(c => String.fromCodePoint(0x1F1E0 - 65 + c.charCodeAt(0))).join('');
}

// -- Simbol abonament ------------------------
function sym(label) {
  const l = (label || '').toLowerCase();
  if (l.includes('basico') || l.includes('basic')) return '🥉';
  if (l.includes('standard'))                       return '🥈';
  if (l.includes('premium') || l.includes('full'))  return '🥇';
  return '📦';
}

// -- Salut dinamic dupa ora Romania ----------
function salut() {
  const h = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Bucharest' })).getHours();
  if (h >= 5  && h < 12) return 'Bună dimineața';
  if (h >= 12 && h < 18) return 'Bună ziua';
  return 'Bună seara';
}

// -- Escape Markdown -------------------------
function esc(t) {
  return String(t ?? '').replace(/[_*[]()~`>#+-=|{}.!\\]/g, '\\$&');
}

// -- Construieste mesaj WhatsApp -------------
function buildWaMsg(c, clients) {
  const prices = Array.isArray(c.prices) ? c.prices : [];
  const lines = prices.map(p => {
    const d = daysUntil(p.expiry);
    if (d === null || d < 0) return null;
    const bar = d <= 3 ? '🔴' : d <= 7 ? '🟡' : '🟢';
    return `${sym(p.label)} ${esc(p.label)} — ${bar} *${d} zile*`;
  }).filter(Boolean);

  if (!lines.length) return null;

  const header = `${salut()} ${esc(c.full_name)} ${flag(c.country_code)} 👋`;
  const body   = lines.join('\n');
  const wa     = `${c.full_name?.split(' ')[0] || 'Salut'}! Abonamentul tău expiră în curând.\n\nDetalii:\n${prices.map(p => `- ${p.label}: ${p.expiry}`).join('\n')}\n\nPentru reînnoire contactează-ne.`;

  return { header, body, wa };
}

// -- Trimite mesaj Telegram ------------------
async function tgSend(chatId, text) {
  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' })
  });
  const j = await r.json();
  if (!j.ok) console.error('TG error:', j.description);
  return j;
}

// -- MAIN ------------------------------------
async function main() {
  console.log(`🚀 Bot pornit — ${new Date().toISOString()}`);

  // Ora curenta in Romania
  const nowRO  = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Bucharest' }));
  const horaRO = `${String(nowRO.getHours()).padStart(2,'0')}:${String(nowRO.getMinutes()).padStart(2,'0')}`;
  console.log(`🕐 Ora curentă Romania: ${horaRO}`);

  // Citeste profilurile cu notif_time
  const { data: profiles, error } = await sb
    .from('profiles')
    .select('*')
    .not('telegram_chat_id', 'is', null);

  if (error) { console.error('❌ Supabase error:', error.message); process.exit(1); }

  const active = profiles.filter(p => p.telegram_chat_id);
  console.log(`👥 Useri cu Telegram: ${active.length}`);

  let sent = 0;

  for (const p of active) {
    const notifTime = (p.notif_time || '').substring(0, 5); // "HH:MM"

    // Verifica daca acum e ora setata in Romania
    if (notifTime && notifTime !== horaRO) {
      console.log(`⏭ ${p.id} | ora setată: ${notifTime} | ora RO acum: ${horaRO} — sărim`);
      continue;
    }

    // Verifica setarile de notificare (7z/3z/24h)
    const prices = Array.isArray(p.prices) ? p.prices : [];
    const relevant = prices.filter(pr => {
      const d = daysUntil(pr.expiry);
      if (d === null || d < 0) return false;
      if (p.notif_7d && d <= 7)  return true;
      if (p.notif_3d && d <= 3)  return true;
      if (p.notif_24h && d <= 1) return true;
      // Daca nu are setari specifice, trimite oricum
      if (!p.notif_7d && !p.notif_3d && !p.notif_24h) return true;
      return false;
    });

    if (!relevant.length) {
      console.log(`⏭ ${p.id} | niciun abonament relevant`);
      continue;
    }

    const msg = buildWaMsg({ ...p, prices: relevant }, active);
    if (!msg) continue;

    const text = `${msg.header}\n\n${msg.body}\n\n` +
      `📋 *Mesaj WhatsApp:*\n\`\`\`\n${msg.wa}\n\`\`\``;

    await tgSend(p.telegram_chat_id, text);
    console.log(`✅ Trimis: ${p.full_name}`);
    sent++;

    await new Promise(r => setTimeout(r, 300));
  }

  console.log(`🏁 Gata! Mesaje trimise: ${sent}`);
}

main().catch(e => { console.error('💥 Eroare fatala:', e.message); process.exit(1); });
