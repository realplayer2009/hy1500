import type { AppState } from '../bridge';

interface Props {
  state: AppState;
}

const WINDOW_MS = 5 * 60 * 1000; // 5 分钟
const CHART_W = 800;
const CHART_H = 220;
const PAD = { left: 44, right: 16, top: 12, bottom: 24 };

function Chart({ samples }: { samples: AppState['samples'] }) {
  if (samples.length < 2) {
    return <div className="chart-empty">连接后自动显示温湿度趋势（最近 5 分钟）</div>;
  }
  const now = Date.now();
  const points = samples.filter((s) => now - s.t <= WINDOW_MS);
  if (points.length < 2) {
    return <div className="chart-empty">连接后自动显示温湿度趋势（最近 5 分钟）</div>;
  }
  const plotW = CHART_W - PAD.left - PAD.right;
  const plotH = CHART_H - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + plotW * (1 - (now - t) / WINDOW_MS);
  // 固定量纲：湿度 0~100 %RH，温度 0~50 ℃
  const yH = (v: number) => PAD.top + plotH * (1 - Math.min(Math.max(v, 0), 100) / 100);
  const yT = (v: number) => PAD.top + plotH * (1 - Math.min(Math.max(v, 0), 50) / 50);
  const path = (getY: (v: number) => number, get: (s: AppState['samples'][number]) => number) =>
    points.map((s, i) => `${i === 0 ? 'M' : 'L'}${x(s.t).toFixed(1)},${getY(get(s)).toFixed(1)}`).join(' ');

  return (
    <svg width="100%" height={CHART_H} viewBox={`0 0 ${CHART_W} ${CHART_H}`} preserveAspectRatio="none">
      {[0, 0.25, 0.5, 0.75, 1].map((p) => (
        <line
          key={p}
          x1={PAD.left} x2={CHART_W - PAD.right}
          y1={PAD.top + plotH * p} y2={PAD.top + plotH * p}
          stroke="var(--color-border)" strokeWidth={1}
        />
      ))}
      <text x={PAD.left - 8} y={PAD.top + 10} textAnchor="end" fill="var(--color-text-tertiary)" fontSize={10}>100</text>
      <text x={PAD.left - 8} y={PAD.top + plotH} textAnchor="end" fill="var(--color-text-tertiary)" fontSize={10}>0</text>
      <text x={PAD.left} y={CHART_H - 6} fill="var(--color-text-tertiary)" fontSize={10}>-5 分钟</text>
      <text x={CHART_W - PAD.right} y={CHART_H - 6} textAnchor="end" fill="var(--color-text-tertiary)" fontSize={10}>现在</text>
      <path d={path(yT, (s) => s.temperature)} fill="none" stroke="var(--color-warning)" strokeWidth={2} strokeLinejoin="round" />
      <path d={path(yH, (s) => s.humidity)} fill="none" stroke="var(--color-success)" strokeWidth={2} strokeLinejoin="round" />
    </svg>
  );
}

export default function MonitorPanel({ state }: Props) {
  return (
    <>
      <div className="monitor-cards">
        <div className="metric-card humidity">
          <div className="label">相对湿度</div>
          <div>
            <span className="value">{state.reading ? state.reading.humidity.toFixed(1) : '--.-'}</span>
            <span className="unit">%RH</span>
          </div>
        </div>
        <div className="metric-card temperature">
          <div className="label">温度</div>
          <div>
            <span className="value">{state.reading ? state.reading.temperature.toFixed(1) : '--.-'}</span>
            <span className="unit">℃</span>
          </div>
        </div>
        <div className="metric-card id-card">
          <div className="label">设备 ID</div>
          <div className="value">{state.currentId ?? '—'}</div>
        </div>
      </div>

      <div className="panel chart-panel">
        <div className="chart-legend">
          <span className="item"><span className="swatch" style={{ background: 'var(--color-success)' }} />湿度 %RH</span>
          <span className="item"><span className="swatch" style={{ background: 'var(--color-warning)' }} />温度 ℃</span>
        </div>
        <Chart samples={state.samples} />
      </div>
    </>
  );
}
