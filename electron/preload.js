const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('vektorium', {
  electron: true,
  escolherPasta: (opcoes) => ipcRenderer.invoke('escolher-pasta', opcoes),
  abrirImpressao: (html) => ipcRenderer.invoke('abrir-impressao', html),
  abrirArquivo: () => ipcRenderer.invoke('abrir-arquivo'),
  salvarArquivoComo: (opcoes) => ipcRenderer.invoke('salvar-arquivo-como', opcoes),
  sair: () => ipcRenderer.invoke('app-sair')
});
