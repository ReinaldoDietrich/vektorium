const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('vektorium', {
  electron: true,
  escolherPasta: (opcoes) => ipcRenderer.invoke('escolher-pasta', opcoes),
  abrirImpressao: (html) => ipcRenderer.invoke('abrir-impressao', html),
  abrirArquivo: () => ipcRenderer.invoke('abrir-arquivo'),
  salvarArquivoComo: (opcoes) => ipcRenderer.invoke('salvar-arquivo-como', opcoes),
  sair: () => ipcRenderer.invoke('app-sair'),
  escolherArquivoDB: () => ipcRenderer.invoke('escolher-arquivo-db'),
  backupPreLogout: () => ipcRenderer.invoke('backup-pre-logout'),
  getHostname: () => ipcRenderer.invoke('get-hostname'),
  iniciarVerificacaoSessao: (dados) => ipcRenderer.invoke('iniciar-verificacao-sessao', dados),
  pararVerificacaoSessao: () => ipcRenderer.invoke('parar-verificacao-sessao'),
  onSessaoTomada: (callback) => ipcRenderer.on('sessao-tomada', (_event, dados) => callback(dados)),
});
