const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('vektorium', {
  versao: require('./package.json').version,
  electron: true,
  escolherPasta: (opcoes) => ipcRenderer.invoke('escolher-pasta', opcoes),
  exportarPdf: (opcoes) => ipcRenderer.invoke('exportar-pdf', opcoes),
  sair: () => ipcRenderer.invoke('app-sair')
});
