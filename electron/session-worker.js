const { parentPort, workerData } = require('worker_threads');
const https = require('https');

const { supabaseUrl, supabaseAnonKey, userId, token, hostname } = workerData;
const INTERVALO_MS = 2 * 60 * 1000;
const TTL_LOCK_MS = 24 * 60 * 60 * 1000;
let rodando = true;

function fetchLock() {
  return new Promise((resolve) => {
    const path = `/storage/v1/object/vektorium-projetos/${userId}/.session_lock`;
    const url = new URL(supabaseUrl);
    const req = https.request({
      hostname: url.hostname,
      port: 443,
      path,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'apikey': supabaseAnonKey,
      },
      timeout: 5000,
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          try { resolve(JSON.parse(body)); } catch (_) { resolve(null); }
        } else {
          resolve(null);
        }
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
    req.end();
  });
}

async function verificar() {
  const lock = await fetchLock();
  if (!lock) return;

  if (lock.ts) {
    const idade = Date.now() - new Date(lock.ts).getTime();
    if (idade > TTL_LOCK_MS) return;
  }

  if (lock.hostname && lock.hostname !== hostname) {
    parentPort.postMessage({ tipo: 'sessao-tomada', hostname: lock.hostname });
  }
}

async function loop() {
  while (rodando) {
    await verificar();
    await new Promise(r => setTimeout(r, INTERVALO_MS));
  }
}

parentPort.on('message', (msg) => {
  if (msg === 'parar') {
    rodando = false;
  }
});

loop();
