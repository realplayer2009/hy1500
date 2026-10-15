import { useState } from 'react';
import { send } from '../bridge';
import type { AppState } from '../bridge';

interface Props {
  state: AppState;
  addLog: (message: string, level?: string) => void;
}

const QUICK_READS = [
  { label: '读温湿度 0x0000×2', start: 0x0000, count: 2 },
  { label: '读 ID/波特率代码 0x0100×2', start: 0x0100, count: 2 },
];

function parseNum(text: string): number | null {
  const t = text.trim();
  if (!t) return null;
  return /^0x/i.test(t) ? parseInt(t.slice(2), 16) : parseInt(t, 10);
}

export default function RegisterPanel({ state, addLog }: Props) {
  const [start, setStart] = useState('0x0000');
  const [count, setCount] = useState('4');
  const [rows, setRows] = useState<{ address: number; value: number }[]>([]);
  const [wAddr, setWAddr] = useState('0x0100');
  const [wValue, setWValue] = useState('');
  const [busy, setBusy] = useState(false);

  const disabled = !state.connected || state.currentId == null;

  const doRead = async (s: number, c: number) => {
    setBusy(true);
    try {
      const res = await send('read_registers', { start: s, count: c });
      if (res.ok && res.registers) {
        setRows(res.registers);
        addLog(`读取 0x${s.toString(16).padStart(4, '0')}×${c}：` +
          res.registers.map((r) => `0x${r.value.toString(16).padStart(4, '0')}`).join(', '));
      } else {
        addLog(`读取失败：${res.error ?? '未知错误'}`, 'error');
      }
    } catch (err) {
      addLog(`读取失败：${(err as Error).message}`, 'error');
    } finally {
      setBusy(false);
    }
  };

  const onRead = () => {
    const s = parseNum(start);
    const c = parseNum(count);
    if (s == null || c == null || s < 0 || s > 0xffff || c < 1 || c > 125) {
      addLog('地址/数量无效：地址 0~0xFFFF，数量 1~125', 'error');
      return;
    }
    void doRead(s, c);
  };

  const onWrite = async () => {
    const a = parseNum(wAddr);
    const v = parseNum(wValue);
    if (a == null || v == null || a < 0 || a > 0xffff || v < 0 || v > 0xffff) {
      addLog('地址/值无效：地址 0~0xFFFF，值 0~0xFFFF', 'error');
      return;
    }
    if (!window.confirm(
      `将向 ID ${state.currentId} 的寄存器 0x${a.toString(16).padStart(4, '0')} 写入 ${v}（0x${v.toString(16).padStart(4, '0')}）。\n\n` +
      '误写可能改变探头通信参数（如 ID、波特率）。是否继续？',
    )) return;
    setBusy(true);
    try {
      const res = await send('write_register', { addr: a, value: v });
      if (res.ok) {
        addLog(`写入成功：ID ${state.currentId} 0x${a.toString(16).padStart(4, '0')} = ${v}`);
      } else {
        addLog(`写入失败：${res.error ?? '未知错误'}`, 'error');
      }
    } catch (err) {
      addLog(`写入失败：${(err as Error).message}`, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="panel">
        <h2 className="panel-title">快捷读取（按文档寄存器表）</h2>
        <div className="field-row">
          {QUICK_READS.map((q) => (
            <button key={q.start} className="btn" disabled={disabled || busy} onClick={() => { setStart(`0x${q.start.toString(16).padStart(4, '0')}`); setCount(String(q.count)); void doRead(q.start, q.count); }}>
              {q.label}
            </button>
          ))}
        </div>
        <p className="panel-hint">文档寄存器：0x0000 湿度÷10 ／ 0x0001 温度÷10（有符号）／ 0x0100 设备 ID ／ 0x0101 波特率代码（4 = 9600）</p>
      </div>

      <div className="panel">
        <h2 className="panel-title">读取保持寄存器（0x03）</h2>
        <div className="field-row">
          <div className="field">
            <span>起始地址</span>
            <input className="mono" style={{ width: 110 }} value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="field">
            <span>数量</span>
            <input className="mono" style={{ width: 70 }} value={count} onChange={(e) => setCount(e.target.value)} />
          </div>
          <button className="btn primary" onClick={onRead} disabled={disabled || busy} style={{ alignSelf: 'flex-end' }}>读取</button>
        </div>
        <table className="reg-table" style={{ marginTop: 14 }}>
          <thead>
            <tr><th>地址</th><th>十进制</th><th>十六进制</th></tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={3} style={{ color: 'var(--color-text-tertiary)' }}>暂无数据，点击“读取”</td></tr>
            )}
            {rows.map((r) => (
              <tr key={r.address}>
                <td>0x{r.address.toString(16).padStart(4, '0')}</td>
                <td>{r.value}</td>
                <td>0x{r.value.toString(16).padStart(4, '0')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2 className="panel-title">写保持寄存器（0x06，仅用于探头配置寄存器）</h2>
        <div className="field-row">
          <div className="field">
            <span>地址</span>
            <input className="mono" style={{ width: 110 }} value={wAddr} onChange={(e) => setWAddr(e.target.value)} />
          </div>
          <div className="field">
            <span>值</span>
            <input className="mono" style={{ width: 110 }} value={wValue} onChange={(e) => setWValue(e.target.value)} placeholder="0~65535" />
          </div>
          <button className="btn danger" onClick={onWrite} disabled={disabled || busy} style={{ alignSelf: 'flex-end' }}>写入</button>
        </div>
        <p className="panel-hint">误写可能改变探头通信参数；改 ID 请用「ID 配置」页（带完整验证流程）。</p>
      </div>
    </>
  );
}
