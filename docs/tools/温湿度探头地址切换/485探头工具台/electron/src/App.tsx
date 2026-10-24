import { useCallback, useEffect, useRef, useState } from 'react';
import { Cable, Gauge, Radio, ScanLine, TerminalSquare } from 'lucide-react';
import { send } from './bridge';
import type { AppState, LogEntry, Sample, StatusLevel } from './bridge';
import IdPanel from './panels/IdPanel';
import MonitorPanel from './panels/MonitorPanel';
import RegisterPanel from './panels/RegisterPanel';
import DebugPanel from './panels/DebugPanel';

const BAUDRATES = [9600, 19200, 38400, 57600, 115200, 4800, 2400];
const TABS = [
  { key: 'id', label: 'ID 配置', icon: ScanLine },
  { key: 'monitor', label: '实时监视', icon: Gauge },
  { key: 'register', label: '寄存器读写', icon: Radio },
  { key: 'debug', label: '串口调试', icon: TerminalSquare },
] as const;

type TabKey = (typeof TABS)[number]['key'];

function now(): string {
  return new Date().toTimeString().slice(0, 8);
}

export default function App() {
  const [ports, setPorts] = useState<string[]>([]);
  const [port, setPort] = useState('');
  const [baud, setBaud] = useState('9600');
  const [activeTab, setActiveTab] = useState<TabKey>('id');
  const [state, setState] = useState<AppState>({
    connected: false,
    currentId: null,
    status: { text: '未连接', level: 'idle' },
    reading: null,
    samples: [],
    logs: [],
  });
  const [busy, setBusy] = useState(false);
  const samplesRef = useRef<Sample[]>([]);

  const addLog = useCallback((message: string, level = 'info') => {
    setState((prev) => ({
      ...prev,
      logs: [...prev.logs.slice(-199), { ts: now(), message, level }],
    }));
  }, []);

  const setStatus = useCallback((text: string, level: StatusLevel) => {
    setState((prev) => ({ ...prev, status: { text, level } }));
  }, []);

  // 订阅桥事件
  useEffect(() => {
    const off = window.bridge.onEvent((e) => {
      if (e.event === 'log') {
        addLog(e.message ?? '', e.level ?? 'info');
      } else if (e.event === 'id') {
        setState((prev) => ({ ...prev, currentId: e.id ?? null }));
        if (e.id != null) setStatus(`正常通信中，ID = ${e.id}`, 'ok');
      } else if (e.event === 'reading') {
        const humidity = e.humidity ?? 0;
        const temperature = e.temperature ?? 0;
        setState((prev) => ({ ...prev, reading: { humidity, temperature } }));
        samplesRef.current = [...samplesRef.current.slice(-599), { t: Date.now(), humidity, temperature }];
        setState((prev) => ({ ...prev, samples: samplesRef.current }));
      } else if (e.event === 'error') {
        addLog(e.message ?? '', 'error');
        setStatus(e.message ?? '发生错误', 'error');
        if (e.stage === 'detect') {
          setState((prev) => ({ ...prev, connected: false, currentId: null }));
        }
      }
    });
    return off;
  }, [addLog, setStatus]);

  // 启动时刷新端口
  const refreshPorts = useCallback(async () => {
    try {
      const res = await send('list_ports');
      if (res.ok) {
        const list = res.ports ?? [];
        setPorts(list);
        if (res.default) setPort(res.default);
        else if (list.length === 0) addLog('未发现 USB 串口，请检查 USB-RS485 转换器', 'warn');
      }
    } catch (err) {
      addLog(`刷新端口失败：${(err as Error).message}`, 'error');
    }
  }, [addLog]);

  useEffect(() => {
    void refreshPorts();
  }, [refreshPorts]);

  const onConnect = useCallback(async () => {
    if (!port) {
      await window.bridge.showError('连接失败', '请先选择串口设备');
      return;
    }
    setBusy(true);
    try {
      const res = await send('connect', { port, baud: Number(baud) });
      if (res.ok) {
        setState((prev) => ({ ...prev, connected: true, currentId: null, reading: null, samples: [] }));
        samplesRef.current = [];
        setStatus('已连接，正在识别探头…', 'warn');
      } else {
        await window.bridge.showError('连接失败', res.error ?? '未知错误');
      }
    } catch (err) {
      await window.bridge.showError('连接失败', (err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [port, baud, setStatus]);

  const onDisconnect = useCallback(async () => {
    setBusy(true);
    try {
      await send('disconnect');
    } catch {
      /* 断开失败不阻塞界面 */
    }
    samplesRef.current = [];
    setState((prev) => ({
      ...prev,
      connected: false,
      currentId: null,
      reading: null,
      samples: [],
      status: { text: '未连接', level: 'idle' },
    }));
    setBusy(false);
  }, []);

  return (
    <div className="app">
      <div className="titlebar">
        <Cable size={16} color="var(--color-accent)" />
        <h1>485 探头工具台</h1>
        <div className="spacer" />
        <span className={`status-pill ${state.status.level}`}>
          <span className="dot" />
          {state.status.text}
        </span>
      </div>

      <div className="conn-bar">
        <label htmlFor="port">串口</label>
        <input
          id="port"
          list="port-list"
          value={port}
          onChange={(e) => setPort(e.target.value)}
          disabled={state.connected}
          placeholder="/dev/cu.usbserial-…"
          spellCheck={false}
        />
        <datalist id="port-list">
          {ports.map((p) => (
            <option key={p} value={p} />
          ))}
        </datalist>
        <button className="btn small ghost" onClick={refreshPorts} disabled={state.connected}>刷新</button>
        <label htmlFor="baud">波特率</label>
        <select id="baud" className="baud" value={baud} onChange={(e) => setBaud(e.target.value)} disabled={state.connected}>
          {BAUDRATES.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
        {!state.connected ? (
          <button className="btn primary" onClick={onConnect} disabled={busy || ports.length === 0}>连接</button>
        ) : (
          <button className="btn" onClick={onDisconnect} disabled={busy}>断开</button>
        )}
      </div>

      <div className="tabs">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            className={`tab ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      <div className="tab-body">
        {activeTab === 'id' && (
          <IdPanel state={state} addLog={addLog} setStatus={setStatus} />
        )}
        {activeTab === 'monitor' && <MonitorPanel state={state} />}
        {activeTab === 'register' && (
          <RegisterPanel state={state} addLog={addLog} />
        )}
        {activeTab === 'debug' && <DebugPanel state={state} addLog={addLog} />}
      </div>
    </div>
  );
}
