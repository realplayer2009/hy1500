import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { send } from '../bridge';
import type { AppState, LogEntry, StatusLevel } from '../bridge';

interface Props {
  state: AppState;
  addLog: (message: string, level?: string) => void;
  setStatus: (text: string, level: StatusLevel) => void;
}

interface ModalState {
  kind: 'confirm' | 'ok' | 'error' | 'warn';
  title: string;
  message: string;
  onConfirm?: () => void;
}

export default function IdPanel({ state, addLog, setStatus }: Props) {
  const [newId, setNewId] = useState('');
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState<ModalState | null>(null);

  const closeModal = () => setModal(null);

  const runChange = async (targetId: number) => {
    closeModal();
    setBusy(true);
    setStatus(`正在写入新 ID ${targetId} …`, 'warn');
    try {
      const res = await send('change_id', { new_id: targetId });
      if (res.ok && res.result) {
        const r = res.result;
        setModal({
          kind: 'ok',
          title: '修改成功',
          message:
            `探头 ID 已从 ${r.old_id} 修改为 ${r.new_id}，并验证通过。\n\n` +
            `修改前：湿度 ${r.before.humidity.toFixed(1)} %RH，温度 ${r.before.temperature.toFixed(1)} ℃\n` +
            `修改后：湿度 ${r.after.humidity.toFixed(1)} %RH，温度 ${r.after.temperature.toFixed(1)} ℃\n\n` +
            `后续读取帧：${String(r.new_id).padStart(2, '0')} 03 00 00 00 02 …`,
        });
        if (r.old_id_still_alive) {
          addLog(`警告：旧 ID ${r.old_id} 仍有响应，总线上可能还有第二根同 ID 探头`, 'warn');
        }
      } else {
        setModal({ kind: 'error', title: '修改失败', message: res.error ?? '未知错误，请重新连接后重试。' });
        setStatus('修改失败', 'error');
      }
    } catch (err) {
      setModal({ kind: 'error', title: '修改失败', message: (err as Error).message });
      setStatus('修改失败', 'error');
    } finally {
      setBusy(false);
    }
  };

  const onChangeId = () => {
    if (!state.connected || state.currentId == null) {
      setModal({ kind: 'warn', title: '提示', message: '请先连接探头并等待识别出当前 ID。' });
      return;
    }
    const raw = newId.trim();
    if (!/^\d+$/.test(raw) || Number(raw) < 1 || Number(raw) > 247) {
      setModal({ kind: 'error', title: '输入错误', message: '新 ID 必须是 1~247 的整数。' });
      return;
    }
    const target = Number(raw);
    if (target === state.currentId) {
      setModal({ kind: 'warn', title: '无需修改', message: `探头当前已经是 ID ${target}。` });
      return;
    }
    setModal({
      kind: 'confirm',
      title: '确认修改设备 ID',
      message:
        `将把探头 ID 从 ${state.currentId} 修改为 ${target}。\n\n` +
        '请确认总线上只连接了这一根探头，否则可能误改其他设备。\n\n是否继续？',
      onConfirm: () => void runChange(target),
    });
  };

  return (
    <>
      <div className="id-layout">
        <div className="panel">
          <h2 className="panel-title"><ShieldCheck size={14} /> 当前探头（总线上每次只接一根）</h2>
          <dl className="info-grid">
            <dt>当前设备 ID</dt>
            <dd className="big" style={{ color: 'var(--color-accent)' }}>
              {state.currentId ?? '—'}
            </dd>
            <dt>湿度</dt>
            <dd>{state.reading ? `${state.reading.humidity.toFixed(1)} %RH` : '—'}</dd>
            <dt>温度</dt>
            <dd>{state.reading ? `${state.reading.temperature.toFixed(1)} ℃` : '—'}</dd>
            <dt>波特率</dt>
            <dd>9600 8N1</dd>
          </dl>
        </div>

        <div className="panel">
          <h2 className="panel-title">修改设备 ID</h2>
          <div className="field-row">
            <div className="field">
              <span>新 ID（1~247）</span>
              <input
                className="mono"
                style={{ width: 90 }}
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onChangeId(); }}
                placeholder="例如 2"
                inputMode="numeric"
              />
            </div>
            <button className="btn primary" onClick={onChangeId} disabled={busy || !state.connected} style={{ alignSelf: 'flex-end' }}>
              写入并验证
            </button>
          </div>
          <p className="panel-hint">
            写入后自动验证：旧 ID 不再响应、新 ID 正常且读数不变。探头切换 ID 后首次读取会超时，工具会自动重试，请勿断电。
          </p>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title">操作日志</h2>
        <div className="log-box">
          {state.logs.length === 0 && <div className="log-line info"><span className="msg">等待操作…</span></div>}
          {state.logs.map((entry: LogEntry, i) => (
            <div key={i} className={`log-line ${entry.level}`}>
              <span className="ts">{entry.ts}</span>
              <span className="msg">{entry.message}</span>
            </div>
          ))}
        </div>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={modal.kind === 'confirm' ? closeModal : undefined}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className={`modal-icon ${modal.kind}`}>
              <ShieldCheck size={18} />
              <h3>{modal.title}</h3>
            </div>
            <p>{modal.message}</p>
            <div className="modal-actions">
              {modal.kind === 'confirm' ? (
                <>
                  <button className="btn" onClick={closeModal}>取消</button>
                  <button className="btn primary" onClick={modal.onConfirm}>确认修改</button>
                </>
              ) : (
                <button className="btn primary" onClick={closeModal}>好</button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
