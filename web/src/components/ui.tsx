import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export function Panel({ children, className = '', pad = true }: { children: ReactNode; className?: string; pad?: boolean }) {
  return <section className={`panel ${pad ? 'panel-pad' : ''} ${className}`}>{children}</section>;
}

export function PanelHead({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="panel-head">
      <div>
        <h2>{title}</h2>
        {hint && <div className="hint">{hint}</div>}
      </div>
      {action && <div className="spacer" style={{ display: 'flex', justifyContent: 'flex-end' }}>{action}</div>}
    </div>
  );
}

export function Stat({ label, value, unit, foot }: { label: string; value: ReactNode; unit?: string; foot?: string }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}{unit && <small> {unit}</small>}</div>
      {foot && <div className="foot">{foot}</div>}
    </div>
  );
}

export function Badge({ children, tone = '' }: { children: ReactNode; tone?: '' | 'ok' | 'warn' | 'danger' | 'violet' | 'cyan' }) {
  return <span className={`badge ${tone ? `badge-${tone}` : ''}`}><span className="dot" />{children}</span>;
}

export function Notice({ children, tone = '' }: { children: ReactNode; tone?: '' | 'warn' | 'violet' }) {
  return <div className={`notice ${tone ? `notice-${tone}` : ''}`}>{children}</div>;
}

export function Slider({ label, value, onChange, min = 0, max = 1, step = 0.01, format }: {
  label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number;
  format?: (v: number) => string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="field">
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <label>{label}</label>
        <span style={{ fontSize: 12, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>
          {format ? format(value) : value.toFixed(2)}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        style={{ ['--fill' as string]: `${pct}%` }}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

export function Toggle({ title, desc, checked, onChange, disabled }: {
  title: string; desc?: string; checked: boolean; onChange: (v: boolean) => void; disabled?: boolean;
}) {
  return (
    <div className="toggle-row" style={disabled ? { opacity: 0.55 } : undefined}>
      <div className="txt">
        <b>{title}</b>
        {desc && <small>{desc}</small>}
      </div>
      <label className="switch">
        <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
        <span />
      </label>
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: { label: string; to: string } }) {
  return (
    <div style={{ textAlign: 'center', padding: '36px 18px', color: 'var(--muted)' }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>{title}</div>
      <p style={{ maxWidth: 460, margin: '8px auto 16px', fontSize: 13 }}>{body}</p>
      {action && <Link className="btn btn-primary" to={action.to}>{action.label}</Link>}
    </div>
  );
}

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '9px 0', borderBottom: '1px solid rgba(255,255,255,.045)' }}>
      <span style={{ color: 'var(--muted-2)', fontSize: 12.5 }}>{k}</span>
      <span style={{ fontSize: 13, textAlign: 'left', wordBreak: 'break-word' }}>{v}</span>
    </div>
  );
}
