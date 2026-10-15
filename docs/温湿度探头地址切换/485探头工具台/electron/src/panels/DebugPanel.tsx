import { useEffect, useRef, useState } from 'react';
import { send } from '../bridge';
import type { AppState } from '../bridge';

interface Props {
  state: AppState;
  addLog: (message: string, level?: string) => void;
}

interface RxEntry {
  ts: string;
  text: string;
  kind: 'tx' | 'rx' | 'err';
}

function pad2(n: number): string {
  return n.toString(16).toUpperCase().padStart(2, '0');
}

export default function DebugPanel({ state, addLog }: Props) {
  const [tx, setTx] = useState('01 03 00 00 00 02');
  const [appendCrc, setAppendCrc] = useState(true);
  const [entries, setEntries] = useState<RxEntry[]>([]);
  const [busy, setBusy] = useState(false);

  const disabled = !state.connected;
  const probeId = state.currentId ?? 1;
  // 快捷帧跟随当前探头 ID，改完 ID 后依然可用
  const quickFrames = [
    { label: `读温湿度（ID ${probeId}）`, hex: `${pad2(probeId)} 03 00 00 00 02` },
    { label: `读 ID 寄存器（ID ${probeId}）`, hex: `${pad2(probeId)} 03 01 00 00 01` },
    { label: '读 ID 寄存器（ID 1，排障）', hex: '01 03 01 00 00 01' },
  ];
  // 默认发送帧跟随当前 ID
  const defaultTx = `${pad2(probeId)} 03 00 00 00 02`;
  const defaultTxRef = useRef(defaultTx);
  useEffect(() => {
    // 用户没手动改过输入框时，默认帧跟随当前 ID
    setTx((prev) => (prev === defaultTxRef.current ? defaultTx : prev));
    defaultTxRef.current = defaultTx;
  }, [defaultTx]);

  const push = (text: string, kind: RxEntry['kind']) => {
    setEntries((prev) => [...prev.slice(-199), {
      ts: new Date().toTimeString().slice(0, 8), text, kind,
    }]);
  };

  const onSend = async (hexText?: string) => {
    const text = (hexText ?? tx).trim();
    if (!/^([0-9a-fA-F]{2}\s*)+$/.test(text)) {
      push('HEX 格式无效，请用空格分隔的两位十六进制，如：01 03 00 00 00 02', 'err');
      return;
    }
    setBusy(true);
    try {
      const res = await send('send_raw', { hex: text, append_crc: appendCrc });
      if (res.ok) {
        push(`TX → ${res.tx ?? ''}`, 'tx');
        if (res.rx) {
          push(`RX ← ${res.rx}`, 'rx');
          const bytes = res.rx.split(' ');
          if (bytes.length >= 3 && (parseInt(bytes[1], 16) & 0x80) !== 0) {
            push(`设备返回异常码 0x${bytes[2]}`, 'err');
          }
        } else {
          push('RX ← （无响应，超时）', 'err');
        }
      } else {
        push(res.error ?? '发送失败', 'err');
      }
    } catch (err) {
      push((err as Error).message, 'err');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="panel">
        <h2 className="panel-title">快捷帧</h2>
        <div className="field-row">
          {quickFrames.map((f) => (
            <button key={f.label} className="btn small" disabled={disabled || busy} onClick={() => { setTx(f.hex); void onSend(f.hex); }}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title">发送（HEX，空格分隔；默认自动追加 CRC）</h2>
        <div className="field-row">
          <input
            className="mono"
            style={{
              flex: 1, minWidth: 260, background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-primary)', padding: '8px 12px', fontSize: '0.875rem', outline: 'none',
            }}
            value={tx}
            onChange={(e) => setTx(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void onSend(); }}
            placeholder={defaultTx}
            spellCheck={false}
          />
          <label className="checkbox">
            <input type="checkbox" checked={appendCrc} onChange={(e) => setAppendCrc(e.target.checked)} />
            自动 CRC
          </label>
          <button className="btn primary" onClick={() => void onSend()} disabled={disabled || busy}>发送</button>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title">收发记录</h2>
        <div className="debug-log">
          {entries.length === 0 && <div style={{ color: 'var(--color-text-tertiary)' }}>等待发送…</div>}
          {entries.map((e, i) => (
            <div key={i} className={e.kind}>
              <span className="ts">{e.ts}</span>
              <span>{e.text}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
