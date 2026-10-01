const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');
const http = require('http');

const PORTA = 8842;
const URL_APP = `http://127.0.0.1:${PORTA}/`;

let janelaPrincipal = null;
let processoBackend = null;
let fechandoApp = false;
let _stderrBuffer = [];

function caminhoRecurso(rel) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, rel);
  }
  return path.join(__dirname, '..', rel);
}

function pastaAppData() {
  const dir = path.join(process.env.APPDATA || path.join(require('os').homedir(), 'AppData', 'Roaming'), 'Vektorium');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function prepararDadosUsuario() {
  if (!app.isPackaged) return;
  const appData = pastaAppData();
  const dbDir = path.join(appData, 'database');
  const uploadsDir = path.join(appData, 'uploads');
  if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir, { recursive: true });
  if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });
  const dbDest = path.join(dbDir, 'carga_termica.db');
  if (!fs.existsSync(dbDest)) {
    const dbOrigem = path.join(process.resourcesPath, 'database', 'carga_termica.db');
    if (fs.existsSync(dbOrigem)) {
      fs.copyFileSync(dbOrigem, dbDest);
    }
  }
}

function portaOcupada() {
  try {
    const saida = execSync(
      `netstat -ano | findstr ":${PORTA}" | findstr "LISTENING"`,
      { encoding: 'utf8', windowsHide: true, timeout: 5000 }
    ).trim();
    return saida.length > 0;
  } catch (_) { return false; }
}

function matarOrfaoNaPorta() {
  for (let tentativa = 0; tentativa < 3; tentativa++) {
    if (!portaOcupada()) return;
    try {
      const saida = execSync(
        `netstat -ano | findstr ":${PORTA}" | findstr "LISTENING"`,
        { encoding: 'utf8', windowsHide: true, timeout: 5000 }
      ).trim();
      for (const linha of saida.split('\n')) {
        const pid = linha.trim().split(/\s+/).pop();
        if (pid && /^\d+$/.test(pid) && pid !== '0') {
          console.log(`Matando processo órfão PID ${pid} na porta ${PORTA} (tentativa ${tentativa + 1})`);
          try { execSync(`taskkill /F /T /PID ${pid}`, { windowsHide: true, timeout: 5000 }); } catch (_) {}
        }
      }
    } catch (_) {}
    const inicio = Date.now();
    while (portaOcupada() && Date.now() - inicio < 3000) {
      execSync('ping -n 1 -w 300 127.0.0.1 >nul 2>&1', { windowsHide: true, timeout: 2000 });
    }
  }
  if (portaOcupada()) {
    console.error(`FALHA: porta ${PORTA} ainda ocupada após 3 tentativas de limpeza`);
  }
}

function iniciarBackend() {
  matarOrfaoNaPorta();

  let python, cwd, env;

  if (app.isPackaged) {
    python = path.join(process.resourcesPath, 'python-embed', 'python.exe');
    cwd = process.resourcesPath;
    const appData = pastaAppData();
    env = {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: '1',
      ELECTRON: '1',
      VEKTORIUM_APPDATA: appData,
      PYTHONPATH: process.resourcesPath,
      VEKTORIUM_VERSION: app.getVersion()
    };
  } else {
    python = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe');
    cwd = path.join(__dirname, '..');
    env = {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: '1',
      ELECTRON: '1',
      VEKTORIUM_VERSION: app.getVersion()
    };
  }

  processoBackend = spawn(python, ['-u', 'iniciar_app.py'], {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    env
  });

  processoBackend.stdout.on('data', (d) => {
    const msg = d.toString().trim();
    if (msg) console.log('[backend]', msg);
  });

  processoBackend.stderr.on('data', (d) => {
    const msg = d.toString().trim();
    if (msg) {
      console.log('[backend:err]', msg);
      _stderrBuffer.push(msg);
      if (_stderrBuffer.length > 50) _stderrBuffer.shift();
    }
  });

  processoBackend.on('error', (err) => {
    console.error('Falha ao iniciar backend:', err);
    dialog.showErrorBox('Erro', `Não foi possível iniciar o servidor:\n${err.message}`);
    app.quit();
  });

  processoBackend.on('exit', (code) => {
    console.log('Backend encerrou com código', code);
    if (!fechandoApp) {
      if (code !== 0 && code !== null) {
        const detalhe = _stderrBuffer.length
          ? '\n\nDetalhes:\n' + _stderrBuffer.slice(-20).join('\n')
          : '';
        dialog.showErrorBox('Erro', 'O servidor encerrou inesperadamente (código ' + code + ').' + detalhe);
      }
      app.quit();
    }
  });
}

function aguardarServidor(tentativas = 0) {
  return new Promise((resolve, reject) => {
    if (tentativas > 30) {
      reject(new Error('Servidor não respondeu após 30 tentativas'));
      return;
    }
    const req = http.get(URL_APP, (res) => {
      res.resume();
      resolve();
    });
    req.on('error', () => {
      setTimeout(() => resolve(aguardarServidor(tentativas + 1)), 500);
    });
    req.setTimeout(2000, () => {
      req.destroy();
      setTimeout(() => resolve(aguardarServidor(tentativas + 1)), 500);
    });
  });
}

async function criarJanela() {
  const { screen } = require('electron');
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

  janelaPrincipal = new BrowserWindow({
    width: Math.min(1400, sw),
    height: Math.min(900, sh),
    minWidth: 1024,
    minHeight: 700,
    title: 'Vektorium',
    icon: path.join(__dirname, '..', 'frontend', 'img', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    show: false
  });

  janelaPrincipal.maximize();

  janelaPrincipal.setMenuBarVisibility(false);

  await janelaPrincipal.webContents.session.clearCache();
  janelaPrincipal.loadURL(URL_APP);

  const fatorDPI = screen.getPrimaryDisplay().scaleFactor;
  const zoomBase = fatorDPI > 1 ? 1 / fatorDPI : 1;

  janelaPrincipal.webContents.on('did-finish-load', () => {
    janelaPrincipal.webContents.executeJavaScript(
      `localStorage.getItem('vektorium_zoom')`
    ).then(salvo => {
      const zoom = salvo ? parseFloat(salvo) : zoomBase;
      janelaPrincipal.webContents.setZoomFactor(zoom);
    }).catch(() => {
      janelaPrincipal.webContents.setZoomFactor(zoomBase);
    });
  });

  janelaPrincipal.webContents.on('zoom-changed', (_e, dir) => {
    const atual = janelaPrincipal.webContents.getZoomFactor();
    const novo = dir === 'in' ? atual + 0.05 : atual - 0.05;
    const limitado = Math.max(0.3, Math.min(2.0, novo));
    janelaPrincipal.webContents.setZoomFactor(limitado);
    janelaPrincipal.webContents.executeJavaScript(
      `localStorage.setItem('vektorium_zoom', '${limitado.toFixed(4)}')`
    ).catch(() => {});
  });

  janelaPrincipal.once('ready-to-show', () => {
    janelaPrincipal.show();
  });

  janelaPrincipal.on('close', async (e) => {
    if (!fechandoApp) {
      e.preventDefault();
      const fecharTodos = janelaPrincipal.webContents.executeJavaScript(`
        (async () => {
          const ac = new AbortController();
          setTimeout(() => ac.abort(), 10000);
          for (let tentativa = 0; tentativa < 3; tentativa++) {
            try {
              const r = await fetch('/api/workspace/fechar-todos', {
                method: 'POST', signal: ac.signal
              });
              const j = await r.json();
              if (j.ok) return true;
            } catch (_) {}
          }
          return false;
        })()
      `, true).catch(() => false);
      const timeoutSalvar = new Promise(r => setTimeout(() => r(false), 12000));
      await Promise.race([fecharTodos, timeoutSalvar]);

      const timeout = new Promise(r => setTimeout(r, 5000));
      const logout = janelaPrincipal.webContents.executeJavaScript(`
        (async () => {
          if (typeof AUTH !== 'undefined') {
            const uid = AUTH._sessao && AUTH._sessao.user ? AUTH._sessao.user.id : null;
            const jwt = AUTH.token ? AUTH.token() : null;
            if (uid && jwt) {
              const ac = new AbortController();
              setTimeout(() => ac.abort(), 3000);
              try { await fetch('/api/cloud/delete-lock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: uid, token: jwt}),
                signal: ac.signal
              }); } catch(_) {}
            }
            try { await AUTH.logout(); } catch (_) {}
            AUTH.limpar();
          }
        })()
      `, true).catch(() => {});
      await Promise.race([logout, timeout]);
      encerrarApp();
    }
  });
}

async function encerrarApp() {
  if (fechandoApp) return;
  fechandoApp = true;
  if (processoBackend) processoBackend.removeAllListeners('exit');

  let portaLivre = matarBackend();
  for (let i = 0; i < 3 && !portaLivre; i++) {
    console.log(`[ENCERRAR] Porta ${PORTA} ainda ocupada, tentativa ${i + 1}/3...`);
    matarOrfaoNaPorta();
    portaLivre = !portaOcupada();
    if (!portaLivre) {
      await new Promise(r => setTimeout(r, 1000));
      portaLivre = matarBackend();
    }
  }
  console.log('[ENCERRAR] Processos backend encerrados confirmado');

  if (janelaPrincipal && !janelaPrincipal.isDestroyed()) {
    janelaPrincipal.destroy();
  }
  app.quit();
}

function matarBackend() {
  if (processoBackend) {
    try {
      execSync(`taskkill /F /T /PID ${processoBackend.pid}`, { windowsHide: true, timeout: 5000 });
    } catch (_) {}
    processoBackend = null;
  }
  try {
    const saida = execSync(
      `netstat -ano | findstr ":${PORTA}" | findstr "LISTENING"`,
      { encoding: 'utf8', windowsHide: true, timeout: 5000 }
    ).trim();
    for (const linha of saida.split('\n')) {
      const pid = linha.trim().split(/\s+/).pop();
      if (pid && /^\d+$/.test(pid) && pid !== '0') {
        try { execSync(`taskkill /F /T /PID ${pid}`, { windowsHide: true, timeout: 5000 }); } catch (_) {}
      }
    }
  } catch (_) {}
  return !portaOcupada();
}

ipcMain.handle('app-sair', async () => {
  await encerrarApp();
});

ipcMain.handle('abrir-impressao', async (_event, html) => {
  const tmpHtml = path.join(app.getPath('temp'), `vektorium-print-${Date.now()}.html`);
  fs.writeFileSync(tmpHtml, html, 'utf8');
  const printWin = new BrowserWindow({
    show: false, width: 1024, height: 768,
    webPreferences: { nodeIntegration: false, contextIsolation: true }
  });

  return new Promise((resolve) => {
    let resolvido = false;
    function resolver(val) {
      if (resolvido) return;
      resolvido = true;
      if (timer) clearTimeout(timer);
      resolve(val);
      setTimeout(() => {
        if (!printWin.isDestroyed()) printWin.close();
        try { fs.unlinkSync(tmpHtml); } catch (_) {}
      }, 500);
    }

    const timer = setTimeout(() => {
      resolver({ ok: false, erro: 'Tempo limite excedido ao gerar PDF.' });
    }, 15000);

    printWin.webContents.on('did-fail-load', (_e, code, desc) => {
      resolver({ ok: false, erro: `Falha ao carregar HTML: ${desc} (${code})` });
    });

    printWin.webContents.on('did-finish-load', async () => {
      try {
        const pdfBuf = await printWin.webContents.printToPDF({
          landscape: false,
          pageSize: 'A4',
          printBackground: true,
          preferCSSPageSize: true,
          margins: { top: 0, bottom: 0, left: 0, right: 0 }
        });
        const tmpPdf = path.join(app.getPath('temp'), `vektorium-print-${Date.now()}.pdf`);
        fs.writeFileSync(tmpPdf, pdfBuf);
        const openErr = await shell.openPath(tmpPdf);
        if (openErr) {
          resolver({ ok: false, erro: `PDF gerado mas não abriu: ${openErr}` });
        } else {
          resolver({ ok: true });
        }
      } catch (e) {
        resolver({ ok: false, erro: e.message });
      }
    });

    printWin.loadFile(tmpHtml);
  });
});

ipcMain.handle('escolher-pasta', async (_event, opcoes) => {
  const opts = {
    title: opcoes?.titulo || 'Escolher pasta',
    properties: ['openDirectory', 'dontAddToRecent']
  };
  if (opcoes?.inicial && fs.existsSync(opcoes.inicial)) {
    opts.defaultPath = opcoes.inicial;
  }
  const result = await dialog.showOpenDialog(janelaPrincipal, opts);
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('abrir-arquivo', async () => {
  const result = await dialog.showOpenDialog(janelaPrincipal, {
    title: 'Abrir Projeto (.vek)',
    filters: [{ name: 'Projeto Vektorium', extensions: ['vek'] }],
    properties: ['openFile', 'dontAddToRecent']
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('salvar-arquivo-como', async (_event, opcoes) => {
  const opts = {
    title: opcoes?.titulo || 'Salvar Projeto Como...',
    filters: [{ name: 'Projeto Vektorium', extensions: ['vek'] }],
  };
  if (opcoes?.nomeDefault) opts.defaultPath = opcoes.nomeDefault;
  const result = await dialog.showSaveDialog(janelaPrincipal, opts);
  return result.canceled ? null : result.filePath;
});

process.on('exit', () => { matarBackend(); });
process.on('SIGTERM', () => { fechandoApp = true; if (processoBackend) processoBackend.removeAllListeners('exit'); matarBackend(); app.quit(); });
process.on('SIGINT',  () => { fechandoApp = true; if (processoBackend) processoBackend.removeAllListeners('exit'); matarBackend(); app.quit(); });

app.whenReady().then(async () => {
  prepararDadosUsuario();
  iniciarBackend();

  try {
    await aguardarServidor();
  } catch (err) {
    dialog.showErrorBox('Erro', err.message);
    app.quit();
    return;
  }

  await criarJanela();
  configurarAutoUpdate();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    encerrarApp();
  }
});

function criarJanelaProgresso() {
  const progWin = new BrowserWindow({
    width: 420, height: 160,
    parent: janelaPrincipal,
    modal: true,
    resizable: false,
    minimizable: false,
    maximizable: false,
    closable: false,
    frame: false,
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false }
  });
  progWin.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(`
    <html><head><style>
      *{margin:0;padding:0;box-sizing:border-box}
      body{font-family:Segoe UI,sans-serif;background:#f4f7fb;display:flex;align-items:center;justify-content:center;height:100vh;padding:24px}
      .box{width:100%;text-align:center}
      h3{font-size:14px;color:#16283b;margin-bottom:12px}
      .bar-bg{width:100%;height:22px;background:#dbe3ec;border-radius:11px;overflow:hidden;margin-bottom:8px}
      .bar-fill{height:100%;width:0%;background:linear-gradient(90deg,#1668c7,#2e8bf0);border-radius:11px;transition:width .3s}
      .info{font-size:12px;color:#5c7186}
    </style></head><body>
      <div class="box">
        <h3>Baixando atualização...</h3>
        <div class="bar-bg"><div class="bar-fill" id="bar"></div></div>
        <div class="info" id="info">Iniciando download...</div>
      </div>
    </body></html>
  `));
  progWin.once('ready-to-show', () => progWin.show());
  return progWin;
}

function configurarAutoUpdate() {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;
  let janelaProgresso = null;

  autoUpdater.on('update-available', (info) => {
    dialog.showMessageBox(janelaPrincipal, {
      type: 'info',
      title: 'Atualização disponível',
      message: `Nova versão ${info.version} disponível. Deseja baixar agora?`,
      buttons: ['Sim', 'Depois']
    }).then(({ response }) => {
      if (response === 0) {
        janelaProgresso = criarJanelaProgresso();
        if (janelaPrincipal) janelaPrincipal.setProgressBar(0);
        autoUpdater.downloadUpdate().catch(err => {
          console.log('Erro ao baixar atualização:', err);
          if (janelaProgresso && !janelaProgresso.isDestroyed()) janelaProgresso.close();
          janelaProgresso = null;
          if (janelaPrincipal) janelaPrincipal.setProgressBar(-1);
          dialog.showMessageBox(janelaPrincipal, {
            type: 'error',
            title: 'Erro ao baixar atualização',
            message: `Não foi possível baixar a atualização.\n\n${err.message || err}`,
            buttons: ['OK']
          });
        });
      }
    });
  });

  autoUpdater.on('download-progress', (prog) => {
    const mb = (prog.transferred / 1048576).toFixed(1);
    const total = (prog.total / 1048576).toFixed(1);
    const pct = Math.round(prog.percent);
    if (janelaProgresso && !janelaProgresso.isDestroyed()) {
      janelaProgresso.webContents.executeJavaScript(
        `document.getElementById('bar').style.width='${pct}%';` +
        `document.getElementById('info').textContent='${pct}% — ${mb} MB de ${total} MB';`
      ).catch(() => {});
    }
    if (janelaPrincipal) janelaPrincipal.setProgressBar(prog.percent / 100);
  });

  autoUpdater.on('update-downloaded', () => {
    if (janelaProgresso && !janelaProgresso.isDestroyed()) janelaProgresso.close();
    janelaProgresso = null;
    if (janelaPrincipal) janelaPrincipal.setProgressBar(-1);
    dialog.showMessageBox(janelaPrincipal, {
      type: 'info',
      title: 'Atualização pronta',
      message: 'A atualização foi baixada. Será instalada ao fechar o aplicativo.',
      buttons: ['Instalar agora', 'Depois']
    }).then(({ response }) => {
      if (response === 0) {
        autoUpdater.quitAndInstall();
      }
    });
  });

  autoUpdater.on('error', (err) => {
    console.log('Auto-update erro:', err);
    if (janelaProgresso && !janelaProgresso.isDestroyed()) janelaProgresso.close();
    janelaProgresso = null;
    if (janelaPrincipal) janelaPrincipal.setProgressBar(-1);
    if (janelaPrincipal) {
      dialog.showMessageBox(janelaPrincipal, {
        type: 'error',
        title: 'Erro na atualização',
        message: `Falha no processo de atualização.\n\n${err.message || err}`,
        buttons: ['OK']
      });
    }
  });

  if (app.isPackaged) {
    autoUpdater.checkForUpdates().catch(err => console.log('Auto-update check falhou:', err));
  }
}
