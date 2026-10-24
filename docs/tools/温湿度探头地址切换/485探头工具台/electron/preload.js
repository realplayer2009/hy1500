"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const bridge = {
    send: (cmd, payload = {}) => electron_1.ipcRenderer.invoke('bridge:send', cmd, payload),
    onEvent: (callback) => {
        const listener = (_, obj) => callback(obj);
        electron_1.ipcRenderer.on('bridge:event', listener);
        return () => electron_1.ipcRenderer.off('bridge:event', listener);
    },
    showError: (title, message) => electron_1.ipcRenderer.invoke('dialog:error', title, message),
};
electron_1.contextBridge.exposeInMainWorld('bridge', bridge);
