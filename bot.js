// ================================================
// Ro Mega 4K - Bot Telegram via GitHub Actions
// Citeste din tabelul clients, trimite la profiles
// Timezone referinta: Europe/Bucharest (Romania)
// ================================================

const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY;
const BOT_TOKEN    = process.env.TELEGRAM_BOT_TOKEN;

if (!SUPABASE_URL || !SUPABASE_KEY || !BOT_TOKEN) {
  console.error('❌ Lipsesc variabilele de mediu!');
  process.exit(1);
}

const sb = createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: { persistSession: false }
});

function daysUntil(expiryStr) {
  if (!expiryStr) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exp = new Date(expiryStr);
  exp.setHours(0, 0, 0, 0);
  return Math.round((exp - today) / 86400000);
}

function flag(cc) {
  if (!cc || cc.length !== 2) return '';
  return [...cc.toUpperCase()].map(c =>
    String.fromCodePoint(0x1F1E0 - 65 + c.charCodeAt(0))
  ).join('');
}

function salut() {
  const h = new Date(new Date().toLocaleString('en-US', {
    timeZone: 'Europe/Bucharest'
  })).getHours();
  if (h >= 5  && h < 12) return 'Bună dimineața';
  if (h >= 12 && h < 18) return 'Bună ziua';
  return 'Bună seara';
}

async function tgSend(chatId, text) {
  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [[
          {
            text: '📱 Deschide Ro Mega 4K',
            url: 'https://manager-clienti-pro.netlify.app'
          }
        ]]
      }
    })
  });
  const j = await r.json();
  if (!j.ok) console.error('TG error:', j.description);
}

async function main() {
  console.log(`🚀 Bot pornit — ${new Date().toISOString()}`);

  // Ora curenta Romania
  const nowRO  = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Bucharest' }));
  const horaRO = `${String(nowRO.getHours()).padStart(2,'0')}:${String(nowRO.getMinutes()).padStart(2,'0')}`;
  console.log(`🕐 Ora curentă Romania: ${horaRO}`);

  // Citeste profilele cu Telegram
  const { data: profiles, error: profErr } = await sb
    .from('profiles')
    .select('id, full_name, telegram_chat_id, notif_time, notif_7d, notif_3d, notif_24h')
    .not('telegram_chat_id', 'is', null);

  if (profErr) { console.error('❌ profiles error:', profErr.message); process.exit(1); }
  console.log(`👥 Profiluri cu Telegram: ${profiles.length}`);

  let sent = 0;

  for (const profile of profiles) {
    const notifTime = (profile.notif_time || '').substring(0, 5);

    if (false) {
      console.log(`⏭ ${profile.full_name} | ora setată: ${notifTime} | ora RO: ${horaRO} — sărim`);
      continue;
    }

    // Citeste clientii acestui user
    const { data: clients, error: cliErr } = await sb
      .from('clients')
      .select('name, expiry, country, pkg_type')
      .eq('user_id', profile.id);

    if (cliErr) { console.error('❌ clients error:', cliErr.message); continue; }

    // Filtreaza dupa setarile de notificare
    const relevant = (clients || []).filter(c => {
      const d = daysUntil(c.expiry);
      if (d === null || d < 0) return false;
      if (profile.notif_7d  && d <= 7) return true;
      if (profile.notif_3d  && d <= 3) return true;
      if (profile.notif_24h && d <= 1) return true;
      if (!profile.notif_7d && !profile.notif_3d && !profile.notif_24h) return true;
      return false;
    });

    console.log(`👤 ${profile.full_name} | clienti relevanti: ${relevant.length}`);

    if (!relevant.length) continue;

    // Construieste mesajul
   

    const today = new Date().toLocaleDateString('ro-RO', {
  timeZone: 'Europe/Bucharest',
  day: '2-digit', month: '2-digit', year: 'numeric'
});

const lines = relevant.map(c => {
  const d = daysUntil(c.expiry);
  const bar = d <= 1 ? '🔴' : d <= 3 ? '🟡' : '🟢';
  return `${bar} ${c.name} — ${d} zile`;
}).join('\n');

const text = `${salut()} *${profile.full_name}* 👋\n\n📊 *Raport zilnic — ${today}:*\n\n${lines}\n\n__Mergi în app pentru a copia mesajul WhatsApp__ 📲`;
    await tgSend(profile.telegram_chat_id, text);
    console.log(`✅ Trimis: ${profile.full_name} (${relevant.length} clienti)`);
    sent++;

    await new Promise(r => setTimeout(r, 300));
  }

  console.log(`🏁 Gata! Mesaje trimise: ${sent}`);
}

main().catch(e => {
  console.error('💥 Eroare fatala:', e.message);
  process.exit(1);
});
