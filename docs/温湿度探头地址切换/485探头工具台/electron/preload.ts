import { contextBridge, ipcRenderer } from 'electron';

export interface BridgeResponse {
  ok: boolean;
  error?: string;
  [key: string]: unknown;
}

const bridge = {
  send: (cmd: string, payload: Record<string, unknown> = {}): Promise<BridgeResponse> =>
    ipcRenderer.invoke('bridge:send', cmd, payload),
  onEvent: (callback: (event: Record<string, unknown>) => void) => {
    const listener = (_: unknown, obj: Record<string, unknown>) => callback(obj);
    ipcRenderer.on('bridge:event', listener);
    return () => ipcRenderer.off('bridge:event', listener);
  },
  showError: (title: string, message: string) => ipcRenderer.invoke('dialog:error', title, message),
};

contextBridge.exposeInMainWorld('bridge', bridge);
