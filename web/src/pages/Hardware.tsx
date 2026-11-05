import { useEffect, useState } from 'react';
import { Badge, KV, Notice, Panel, PanelHead, Stat } from '../components/ui';
import { IconRefresh } from '../components/icons';
import { useBridge } from '../lib/bridge-context';
import type { HardwarePayload } from '../lib/bridge';

interface BrowserInfo {
  cores: number;
  memory: number | null;
  renderer: string;
  vendor: string;
  platform: string;
}

function readBrowserInfo(): BrowserInfo {
  const nav = navigator as Navigator & { deviceMemory?: number; userAgentData?: { platform?: string } };
  let renderer = 'غير متاح';
  let vendor = 'غير متاح';
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    const debug = gl?.getExtension('WEBGL_debug_renderer_info');
    if (gl && debug) {
      renderer = String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL));
      vendor = String(gl.getParameter(debug.UNMASKED_VENDOR_WEBGL));
    }
  } catch {
    /* blocked */
  }
  return {
    cores: nav.hardwareConcurrency || 0,
    memory: nav.deviceMemory ?? null,
    renderer,
    vendor,
    platform: nav.userAgentData?.platform ?? navigator.platform,
  };
}

export default function Hardware() {
  const { paired, hardware, loadHardware } = useBridge();
  const [data, setData] = useState<HardwarePayload | null>(hardware);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const browser = readBrowserInfo();

  const load = async () => {
    setLoading(true);
    try {
      await loadHardware();
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { setData(hardware); }, [hardware]);

  return (
    <div className="grid" style={{ gap: 18 }}>
      {!paired && (
        <Notice tone="warn">
          <div>
            <b>قراءة المتصفح فقط.</b> كشف العتاد الكامل (المزودات، VRAM، سلسلة الاحتياط) يحتاج المحرك المكتبي.
            هذه بيانات حقيقية من المتصفح وليست تقديرات.
          </div>
        </Notice>
      )}

      <div className="grid grid-4">
        <Stat label="أنوية المعالج" value={paired && data ? data.profile.cpu.physical_cores : browser.cores || '—'} foot={paired && data ? data.profile.cpu.brand : 'navigator.hardwareConcurrency'} />
        <Stat label="الذاكرة" value={paired && data ? `${(data.profile.system.ram_total_mb / 1024).toFixed(1)}` : browser.memory ?? '—'} unit={paired && data ? 'GB' : browser.memory ? 'GB' : ''} foot={paired && data ? `${data.profile.system.ram_available_mb} MB متاحة` : 'تقدير المتصفح'} />
        <Stat label="الخلفية" value={paired && data ? data.decision.label : '—'} foot={paired && data ? data.decision.tier : 'يتطلب المحرك'} />
        <Stat label="كرت الشاشة" value={paired && data ? (data.profile.gpus[0]?.name ?? 'لا يوجد') : '—'} foot={paired && data ? (data.profile.gpus[0]?.vram_mb ? `${data.profile.gpus[0].vram_mb} MB VRAM` : '') : 'WebGL'} />
      </div>

      <div className="split">
        <Panel>
          <PanelHead title="تقرير المحرك" hint="قراءة مباشرة عبر /api/hardware"
            action={<button className="btn btn-sm" onClick={() => void load()} disabled={!paired || loading}><IconRefresh /> {loading ? '…' : 'تحديث'}</button>} />
          {paired && data ? (
            <div>
              <KV k="المعالج" v={`${data.profile.cpu.brand} (${data.profile.cpu.architecture})`} />
              <KV k="الأنوية" v={`${data.profile.cpu.physical_cores} فيزيائي / ${data.profile.cpu.logical_cores} منطقي`} />
              <KV k="مجموعة التعليمات" v={data.profile.cpu.isa.length ? data.profile.cpu.isa.join(' · ') : 'غير متاحة'} />
              <KV k="مصدر التعليمات" v={data.profile.cpu.isa_source} />
              <KV k="نظام التشغيل" v={`${data.profile.system.os_name} ${data.profile.system.os_release}`} />
              <KV k="المعمارية" v={data.profile.system.machine} />
              <KV k="مساحة القرص" v={`${data.profile.system.disk_free_gb} GB`} />
              <KV k="Python" v={data.profile.system.python} />
              {data.profile.gpus.map((gpu) => (
                <KV key={gpu.name} k={`GPU · ${gpu.vendor}`} v={`${gpu.name} · ${gpu.vram_mb ?? '?'} MB · ${gpu.driver ?? 'driver ?'}`} />
              ))}
              {data.profile.notes.map((note) => <div key={note} style={{ marginTop: 10 }}><Notice tone="warn">{note}</Notice></div>)}
            </div>
          ) : (
            <div>
              <KV k="المتصفح" v={navigator.userAgent.split(') ')[0] + ')'} />
              <KV k="المنصة" v={browser.platform} />
              <KV k="WebGL Renderer" v={browser.renderer} />
              <KV k="WebGL Vendor" v={browser.vendor} />
              <KV k="أنوية مرئية" v={browser.cores || '—'} />
              {error && <div className="notice notice-warn" style={{ marginTop: 10 }}>{error}</div>}
            </div>
          )}
        </Panel>

        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="اختيار الخلفية" hint="التحقق يتم بجلسة ONNX حقيقية" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(data?.decision.probes ?? []).map((probe) => (
                <div key={probe.provider} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 10, border: '1px solid var(--line)' }}>
                  <Badge tone={probe.verified ? 'ok' : ''}>{probe.verified ? '✓' : '—'}</Badge>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600 }}>{probe.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{probe.reason}</div>
                  </div>
                </div>
              ))}
              {!data && <div className="notice">اقترن بالمحرك لعرض نتائج فحص المزوّدات الفعلية.</div>}
            </div>
          </Panel>

          <Panel>
            <PanelHead title="سلسلة الاحتياط" hint="لا انهيار عند تعطّل السائق" />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {(data?.decision.chain ?? ['CPUExecutionProvider']).map((provider, index) => (
                <span key={provider} className="badge badge-violet">{index === 0 ? '→ ' : ''}{provider.replace('ExecutionProvider', '')}</span>
              ))}
            </div>
            <p style={{ color: 'var(--muted-2)', fontSize: 11.5 }}>
              عند فشل المزوّد الأول، ينتقل المحرك تلقائيًا إلى التالي دون إعادة تشغيل التطبيق.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}
