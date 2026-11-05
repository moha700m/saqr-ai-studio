import { useEffect, useState } from 'react';
import { Badge, Notice, Panel, PanelHead } from '../components/ui';
import { IconBox, IconDownload, IconLock } from '../components/icons';
import { bridge, type ModelRow } from '../lib/bridge';
import { useBridge } from '../lib/bridge-context';
import { formatBytes } from '../lib/utils';

const fallback: ModelRow[] = [
  {
    id: 'yunet-2023mar', name: 'YuNet face detector', kind: 'detector', filename: 'face_detection_yunet_2023mar.onnx',
    license_id: 'MIT', license_name: 'MIT License', commercial_use: true, requires_acceptance: false,
    downloadable: true, installed: false, license_accepted: false, size_bytes: 232589,
    notes: 'كشف الوجه ونقاط المحاذاة الخمس. صغير وسريع على المعالج.', source_url: 'https://github.com/opencv/opencv_zoo',
  },
  {
    id: 'gfpgan-1.4', name: 'GFPGAN v1.4 enhancer', kind: 'enhancer', filename: 'GFPGANv1.4.onnx',
    license_id: 'Apache-2.0', license_name: 'Apache License 2.0', commercial_use: true, requires_acceptance: false,
    downloadable: false, installed: false, license_accepted: false, size_bytes: null,
    notes: 'يُستورد يدويًا بصيغة ONNX. لا تعيد SAQR توزيعه.', source_url: 'https://github.com/TencentARC/GFPGAN',
  },
  {
    id: 'inswapper-128', name: 'InsightFace inswapper_128', kind: 'swapper', filename: 'inswapper_128.onnx',
    license_id: 'InsightFace-NC', license_name: 'أبحاث غير تجارية فقط', commercial_use: false, requires_acceptance: true,
    downloadable: false, installed: false, license_accepted: false, size_bytes: null,
    notes: 'غير قابل للتنزيل من SAQR. استورده بنفسك بعد قراءة الترخيص.', source_url: 'https://github.com/deepinsight/insightface',
  },
];

export default function Models() {
  const { paired } = useBridge();
  const [rows, setRows] = useState<ModelRow[]>(fallback);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = async () => {
    if (!paired) return;
    try {
      const data = await bridge.models();
      setRows(data.catalog);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => { void refresh(); /* eslint-disable-line react-hooks/exhaustive-deps */ }, [paired]);

  const accept = async (id: string) => {
    setBusy(id);
    try {
      await bridge.acceptLicense(id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid" style={{ gap: 18 }}>
      <Notice tone={paired ? 'violet' : 'warn'}>
        {paired ? 'هذه القائمة تأتي من مدير النماذج في المحرك، مع حالة التثبيت الفعلية.' : 'قائمة مرجعية. بعد الاقتران ستظهر حالة التثبيت والترخيص الحقيقية من جهازك.'}
      </Notice>

      {error && <Notice tone="warn">{error}</Notice>}

      <div className="grid grid-3">
        {rows.map((model) => (
          <Panel key={model.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ width: 38, height: 38, borderRadius: 11, display: 'grid', placeItems: 'center', background: 'var(--violet-soft)', color: '#c4b5fd' }}><IconBox /></div>
              <Badge tone={model.installed ? 'ok' : model.commercial_use ? '' : 'warn'}>
                {model.installed ? 'مثبّت' : model.commercial_use ? 'متاح' : 'غير تجاري'}
              </Badge>
            </div>
            <h3 style={{ margin: '12px 0 2px', fontSize: 14.5 }}>{model.name}</h3>
            <div style={{ color: 'var(--muted-2)', fontSize: 11.5, fontFamily: 'var(--mono)', direction: 'ltr', textAlign: 'left' }}>{model.filename}</div>
            <p style={{ color: 'var(--muted)', fontSize: 12.5, minHeight: 54 }}>{model.notes}</p>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
              <Badge tone="cyan">{model.license_id}</Badge>
              <Badge>{model.kind}</Badge>
              {model.size_bytes ? <Badge>{formatBytes(model.size_bytes)}</Badge> : <Badge><IconLock /> استيراد يدوي</Badge>}
            </div>
            {model.requires_acceptance && (
              <div className="notice notice-warn" style={{ fontSize: 11.5, marginBottom: 10 }}>
                ترخيص غير تجاري. لا تستخدمه في منتج تجاري. راجع docs/MODEL_LICENSES.md.
              </div>
            )}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <a className="btn btn-sm btn-ghost" href={model.source_url} target="_blank" rel="noreferrer">المصدر</a>
              {model.requires_acceptance && !model.license_accepted && (
                <button className="btn btn-sm" disabled={!paired || busy === model.id} onClick={() => void accept(model.id)}>
                  {busy === model.id ? '…' : 'أقبل الترخيص'}
                </button>
              )}
              {model.license_accepted && <Badge tone="ok">الترخيص مقبول</Badge>}
            </div>
          </Panel>
        ))}
      </div>

      <Panel>
        <PanelHead title="التثبيت من الطرفية" hint="كل تنزيل يتحقق من SHA-256" />
        <pre className="code">{`# كاشف الوجه (MIT) — قابل للتنزيل
saqr models download yunet-2023mar

# محوّل الوجه (ترخيص غير تجاري) — استيراد فقط
saqr models import ./inswapper_128.onnx --kind swapper --accept-license

# محسّن الوجه (Apache-2.0) — استيراد فقط
saqr models import ./GFPGANv1.4.onnx --kind enhancer`}</pre>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <button className="btn btn-sm" onClick={() => void refresh()} disabled={!paired}><IconDownload /> تحديث الحالة</button>
        </div>
      </Panel>
    </div>
  );
}
