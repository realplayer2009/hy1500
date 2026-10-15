"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
let mainWindow = null;
let bridgeProcess = null;
let bridgeBuffer = '';
let requestCounter = 0;
const pending = new Map();
// ---------------------------------------------------------------- Python 桥
function findPython() {
    const candidates = ['/usr/bin/python3', '/usr/local/bin/python3', '/opt/homebrew/bin/python3', 'python3'];
    for (const candidate of candidates) {
        try {
            const result = require('child_process').execFileSync(candidate, ['-c', 'import serial'], {
                stdio: 'pipe', timeout: 5000,
            });
            void result;
            return candidate;
        }
        catch {
            continue;
        }
    }
    return '/usr/bin/python3';
}
function findBridgeScript() {
    const candidates = [
        path.join(__dirname, 'backend', 'serial_bridge.py'), // 开发模式
        path.join(electron_1.app.getAppPath(), '..', 'backend', 'serial_bridge.py'), // 打包模式（extraResources）
    ];
    for (const candidate of candidates) {
        if (fs.existsSync(candidate))
            return candidate;
    }
    return candidates[candidates.length - 1];
}
function startBridge() {
    const python = findPython();
    const script = findBridgeScript();
    console.log(`[bridge] ${python} ${script}`);
    bridgeProcess = (0, child_process_1.spawn)(python, ['-u', script], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });
    bridgeProcess.stdout?.on('data', (data) => {
        bridgeBuffer += data.toString();
        const lines = bridgeBuffer.split('\n');
        bridgeBuffer = lines.pop() ?? '';
        for (const line of lines) {
            if (!line.trim())
                continue;
            let obj;
            try {
                obj = JSON.parse(line);
            }
            catch {
                console.warn('[bridge] 非 JSON 输出:', line);
                continue;
            }
            // 事件对象（含 event 字段）也可能带 id（探头设备 ID），不能当响应匹配
            const isEvent = typeof obj.event === 'string';
            if (!isEvent && typeof obj.id === 'number' && pending.has(obj.id)) {
                const entry = pending.get(obj.id);
                pending.delete(obj.id);
                if (obj.ok)
                    entry.resolve(obj);
                else
                    entry.reject(new Error(String(obj.error ?? '未知错误')));
            }
            else {
                mainWindow?.webContents.send('bridge:event', obj);
            }
        }
    });
    bridgeProcess.stderr?.on('data', (data) => {
        console.warn('[bridge stderr]', data.toString());
    });
    bridgeProcess.on('exit', (code) => {
        console.log(`[bridge] 退出 code=${code}`);
        for (const [, entry] of pending)
            entry.reject(new Error('串口桥进程已退出'));
        pending.clear();
    });
}
function bridgeSend(cmd, payload = {}) {
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
    mainWindow = new electron_1.BrowserWindow({
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
    }
    else {
        mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
    }
}
electron_1.app.whenReady().then(() => {
    startBridge();
    createWindow();
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0)
            createWindow();
    });
});
electron_1.app.on('window-all-closed', () => {
    if (bridgeProcess) {
        bridgeProcess.stdin?.write(JSON.stringify({ id: 999, cmd: 'exit' }) + '\n');
        setTimeout(() => bridgeProcess?.kill(), 500);
    }
    if (process.platform !== 'darwin')
        electron_1.app.quit();
});
electron_1.app.on('before-quit', () => {
    bridgeProcess?.kill();
});
// ---------------------------------------------------------------- IPC
electron_1.ipcMain.handle('bridge:send', (_event, cmd, payload) => bridgeSend(cmd, payload));
electron_1.ipcMain.handle('dialog:error', async (_event, title, message) => {
    if (!mainWindow)
        return;
    await electron_1.dialog.showMessageBox(mainWindow, { type: 'error', title, message, buttons: ['好'] });
});
