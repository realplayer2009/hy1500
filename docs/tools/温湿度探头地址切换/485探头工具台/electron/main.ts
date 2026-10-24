import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

let mainWindow: BrowserWindow | null = null;
let bridgeProcess: ChildProcess | null = null;
let bridgeBuffer = '';
let requestCounter = 0;
const pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>();

// ---------------------------------------------------------------- Python 桥

function findPython(): string {
  const candidates = ['/usr/bin/python3', '/usr/local/bin/python3', '/opt/homebrew/bin/python3', 'python3'];
  for (const candidate of candidates) {
    try {
      const result = require('child_process').execFileSync(candidate, ['-c', 'import serial'], {
        stdio: 'pipe', timeout: 5000,
      });
      void result;
      return candidate;
    } catch {
      continue;
    }
  }
  return '/usr/bin/python3';
}

function findBridgeScript(): string {
  const candidates = [
    path.join(__dirname, 'backend', 'serial_bridge.py'),               // 开发模式
    path.join(app.getAppPath(), '..', 'backend', 'serial_bridge.py'),  // 打包模式（extraResources）
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return candidates[candidates.length - 1];
}

function startBridge() {
  const python = findPython();
  const script = findBridgeScript();
  console.log(`[bridge] ${python} ${script}`);
  bridgeProcess = spawn(python, ['-u', script], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  bridgeProcess.stdout?.on('data', (data: Buffer) => {
    bridgeBuffer += data.toString();
    const lines = bridgeBuffer.split('\n');
    bridgeBuffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.trim()) continue;
      let obj: Record<string, unknown>;
      try {
        obj = JSON.parse(line);
      } catch {
        console.warn('[bridge] 非 JSON 输出:', line);
        continue;
      }
      // 事件对象（含 event 字段）也可能带 id（探头设备 ID），不能当响应匹配
      const isEvent = typeof obj.event === 'string';
      if (!isEvent && typeof obj.id === 'number' && pending.has(obj.id as number)) {
        const entry = pending.get(obj.id as number)!;
        pending.delete(obj.id as number);
        if (obj.ok) entry.resolve(obj);
        else entry.reject(new Error(String(obj.error ?? '未知错误')));
      } else {
        mainWindow?.webContents.send('bridge:event', obj);
      }
    }
  });

  bridgeProcess.stderr?.on('data', (data: Buffer) => {
    console.warn('[bridge stderr]', data.toString());
  });

  bridgeProcess.on('exit', (code) => {
    console.log(`[bridge] 退出 code=${code}`);
    for (const [, entry] of pending) entry.reject(new Error('串口桥进程已退出'));
    pending.clear();
  });
}

function bridgeSend(cmd: string, payload: Record<string, unknown> = {}): Promise<unknown> {
  return new Promise((resolve, reject) => {
    if (!bridgeProcess?.stdin?.writable) {
      reject(new Error('串口桥未启动'));
      return;
    }
    const id = ++requestCounter;
    pending.set(id, { resolve, reject });
    bridgeProcess.stdin.write(JSON.stringify({ id, cmd, ...payload }) + '\n');
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error('串口桥响应超时'));
      }
    }, 15000);
  });
}

// ---------------------------------------------------------------- 窗口

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: '485 探头工具台',
    backgroundColor: '#1a1a1c',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  if (process.env.PROBE_DEV) {
    mainWindow.loadURL('http://localhost:5174');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }
}

app.whenReady().then(() => {
  startBridge();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (bridgeProcess) {
    bridgeProcess.stdin?.write(JSON.stringify({ id: 999, cmd: 'exit' }) + '\n');
    setTimeout(() => bridgeProcess?.kill(), 500);
  }
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  bridgeProcess?.kill();
});

// ---------------------------------------------------------------- IPC

ipcMain.handle('bridge:send', (_event, cmd: string, payload: Record<string, unknown>) =>
  bridgeSend(cmd, payload)
);

ipcMain.handle('dialog:error', async (_event, title: string, message: string) => {
  if (!mainWindow) return;
  await dialog.showMessageBox(mainWindow, { type: 'error', title, message, buttons: ['好'] });
});
