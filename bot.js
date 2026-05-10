// ================================================
// Ro Mega 4K - Bot Telegram via GitHub Actions
// ================================================

const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL      = process.env.SUPABASE_URL;
const SUPABASE_KEY      = process.env.SUPABASE_SERVICE_KEY;
const BOT_TOKEN         = process.env.TELEGRAM_BOT_TOKEN;
const ONESIGNAL_APP_ID  = 'ed44b50b-7a45-47d5-bf64-15ba99836e30';
const ONESIGNAL_API_KEY = process.env.ONESIGNAL_API_KEY;

if (!SUPABASE_URL || !SUPABASE_KEY || !BOT_TOKEN) {
  console.error('Lipsesc variabilele de mediu!');
  process.exit(1);
}

const sb = createClient(SUPABASE_URL, SUPABASE_KEY, { auth: { persistSession: false } });

function daysUntil(expiryStr) {
  if (!expiryStr) return null;
  const today = new Date(); today.setHours(0,0,0,0);
  const exp = new Date(expiryStr); exp.setHours(0,0,0,0);
  return Math.round((exp - today) / 86400000);
}

function escMd(text) {
  if (!text) return '';
  return String(text).replace(/[_*[\]()~`>#+\-=|{}.!]/g, '\\$&');
}

function salut() {
  const h = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Bucharest' })).getHours();
  if (h >= 5 && h < 12) return 'Buna dimineata';
  if (h >= 12 && h < 18) return 'Buna ziua';
  return 'Buna seara';
}

async function fetchWithRetry(url, options, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await fetch(url, options);
    } catch (e) {
      console.warn(`fetch attempt ${i+1}/${retries} failed: ${e.message}`);
      if (i < retries - 1) await new Promise(r => setTimeout(r, 3000));
    }
  }
  throw new Error(`fetch failed after ${retries} attempts`);
}

async function tgSend(chatId, text) {
  try {
    const r = await fetchWithRetry(
      `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text,
          parse_mode: 'MarkdownV2',
          reply_markup: { inline_keyboard: [[{ text: 'Deschide Ro Mega 4K', url: 'https://manager-clienti-pro.netlify.app' }]] }
        })
      }
    );
    const j = await r.json();
    if (!j.ok) console.error('TG error:', j.description);
    else console.log('TG ok');
  } catch (e) {
    console.error('tgSend failed:', e.message);
  }
}

async function sendPush(userId, count) {
  if (!ONESIGNAL_API_KEY) { console.warn('ONESIGNAL_API_KEY lipsa'); return; }
  try {
    const r = await fetchWithRetry('https://api.onesignal.com/notifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Key ${ONESIGNAL_API_KEY}` },
      body: JSON.stringify({
        app_id: ONESIGNAL_APP_ID,
        include_aliases: { external_id: [userId] },
        target_channel: 'push',
        headings: { en: 'Ro Mega 4K' },
        contents: { en: `${count} client(i) expira curand!` },
        url: 'https://manager-clienti-pro.netlify.app'
      })
    });
    const j = await r.json();
    if (j.errors) console.error('OneSignal error:', JSON.stringify(j.errors));
    else console.log(`Push trimis (${j.recipients ?? '?'} recipients)`);
  } catch (e) {
    console.error('sendPush failed:', e.message);
  }
}

async function main() {
  console.log(`Bot pornit - ${new Date().toISOString()}`);
  const nowRO = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Bucharest' }));
  console.log(`Ora Romania: ${String(nowRO.getHours()).padStart(2,'0')}:${String(nowRO.getMinutes()).padStart(2,'0')}`);

  const { data: profiles, error: profErr } = await sb
    .from('profiles')
    .select('id, full_name, telegram_chat_id, notif_7d, notif_3d, notif_24h')
    .not('telegram_chat_id', 'is', null);

  if (profErr) { console.error('profiles error:', profErr.message); process.exit(1); }
  console.log(`Profiluri cu Telegram: ${profiles.length}`);

  let sent = 0;

  for (const profile of profiles) {
    const { data: clients, error: cliErr } = await sb
      .from('clients').select('name, expiry').eq('user_id', profile.id);
    if (cliErr) { console.error('clients error:', cliErr.message); continue; }

    const relevant = (clients || []).filter(c => {
      const d = daysUntil(c.expiry);
      if (d === null || d < 0) return false;
      if (profile.notif_7d && d <= 7) return true;
      if (profile.notif_3d && d <= 3) return true;
      if (profile.notif_24h && d <= 1) return true;
      if (!profile.notif_7d && !profile.notif_3d && !profile.notif_24h) return true;
      return false;
    });

    console.log(`${profile.full_name} | relevanti: ${relevant.length}`);
    if (!relevant.length) continue;

    const today = new Date().toLocaleDateString('ro-RO', { timeZone: 'Europe/Bucharest', day: '2-digit', month: '2-digit', year: 'numeric' });
    const lines = relevant.map(c => {
      const d = daysUntil(c.expiry);
      return `${d <= 1 ? '🔴' : d <= 3 ? '🟡' : '🟢'} ${escMd(c.name)} — ${d} zile`;
    }).join('\n');

    const text = `${salut()} *${escMd(profile.full_name)}* 👋\n\n📊 *Raport zilnic — ${escMd(today)}:*\n\n${lines}\n\nMergi în app pentru a copia mesajul WhatsApp 📲`;

    await tgSend(profile.telegram_chat_id, text);
    console.log(`Telegram trimis: ${profile.full_name} (${relevant.length} clienti)`);

    await sendPush(profile.id, relevant.length);

    sent++;
    await new Promise(r => setTimeout(r, 500));
  }

  console.log(`Gata! Mesaje trimise: ${sent}`);
}

main().catch(e => {
  console.error('Eroare fatala:', e.message);
  process.exit(1);
});
