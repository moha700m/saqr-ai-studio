import { useRef, useState } from 'react';
import { Badge, Notice, Panel, PanelHead, Slider, Stat } from '../components/ui';
import { IconDownload, IconImage, IconRefresh } from '../components/icons';
import { bridge } from '../lib/bridge';
import { useBridge } from '../lib/bridge-context';
import { downloadDataUrl, fileToDataUrl, stripDataUrl } from '../lib/utils';

export default function ImageStudio() {
  const { paired } = useBridge();
  const [source, setSource] = useState<string | null>(null);
  const [input, setInput] = useState<string | null>(null);
  const [output, setOutput] = useState<string | null>(null);
  const [info, setInfo] = useState<{ name: string; size: number; width: number; height: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quality, setQuality] = useState(0.92);
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sourceRef = useRef<HTMLInputElement>(null);

  const pickInput = async (file?: File) => {
    if (!file) return;
    setError(null);
    setOutput(null);
    const url = await fileToDataUrl(file);
    const image = new Image();
    image.onload = () => setInfo({ name: file.name, size: file.size, width: image.naturalWidth, height: image.naturalHeight });
    image.src = url;
    setInput(url);
  };

  const process = async () => {
    if (!input) return;
    setBusy(true);
    setError(null);
    try {
      if (!paired) throw new Error('المعالجة تحتاج اقترانًا بمحرك سطح المكتب.');
      if (!source) throw new Error('اختر صورة مصدر أولًا (وجه واحد واضح).');
      await bridge.setSource(stripDataUrl(source), 'image-studio');
      const response = await bridge.processFrame(stripDataUrl(input), true, 1);
      setOutput(`data:image/jpeg;base64,${response.image}`);
      setMetrics(response.metrics);
      if (response.error) setError(response.error);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid" style={{ gap: 18 }}>
      <Notice tone={paired ? 'violet' : 'warn'}>
        {paired ? 'المعالجة تجري في المحرك المحلي. النتيجة تعود كـ JPEG بجودة 90.' : 'الواجهة جاهزة، لكن المعالجة تحتاج المحرك المكتبي. يمكنك اختيار الصور وتجهيزها الآن.'}
      </Notice>

      <div className="split">
        <Panel>
          <PanelHead title="الصورة" hint="PNG · JPEG · WebP · BMP"
            action={<Badge tone={output ? 'ok' : ''}>{output ? 'جاهزة' : 'اختر ملفًا'}</Badge>} />
          <div className="viewport" style={{ aspectRatio: '16/9' }}>
            {output ? <img src={output} alt="النتيجة" /> : input ? <img src={input} alt="المدخل" /> : (
              <div className="empty">
                <IconImage />
                <div style={{ marginTop: 8 }}>اسحب صورة هنا أو اختر ملفًا</div>
                <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }} onClick={() => inputRef.current?.click()}>اختيار صورة</button>
              </div>
            )}
            {metrics && (
              <div className="metrics-strip">
                <span>{metrics.faces} وجه</span>
                <span>{metrics.total_ms.toFixed(0)} ms</span>
                <span>{metrics.swap_ms.toFixed(0)} ms تبديل</span>
                <span>{output ? 'مخرج' : 'مدخل'}</span>
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            <button className="btn btn-sm" onClick={() => inputRef.current?.click()}>تغيير الصورة</button>
            <button className="btn btn-primary" onClick={() => void process()} disabled={!input || busy}>
              {busy ? 'جارٍ التنفيذ…' : 'معالجة الصورة'}
            </button>
            {output && (
              <button className="btn btn-sm" onClick={() => downloadDataUrl(output, `saqr-${info?.name ?? 'result'}.jpg`)}>
                <IconDownload /> تنزيل
              </button>
            )}
            <button className="btn btn-ghost btn-sm" onClick={() => { setOutput(null); setMetrics(null); }} disabled={!output}>
              <IconRefresh /> قبل/بعد
            </button>
          </div>
          <input ref={inputRef} type="file" accept="image/*" hidden onChange={(e) => void pickInput(e.target.files?.[0])} />
          {error && <div className="notice notice-warn" style={{ marginTop: 12 }}>{error}</div>}
        </Panel>

        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="صورة المصدر" hint="الوجه الذي سيظهر في النتيجة" />
            <div className="dropzone" onClick={() => sourceRef.current?.click()} style={{ padding: 16 }}>
              {source ? <img src={source} alt="المصدر" style={{ width: 120, height: 120, objectFit: 'cover', borderRadius: 12 }} /> : (
                <>
                  <IconImage />
                  <div style={{ fontSize: 12.5 }}>اختر صورة وجه واضحة</div>
                  <small>إضاءة أمامية، بلا نظارات شمسية</small>
                </>
              )}
            </div>
            <input ref={sourceRef} type="file" accept="image/*" hidden onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void fileToDataUrl(file).then(setSource);
            }} />
            {source && <button className="btn btn-sm btn-ghost btn-block" style={{ marginTop: 8 }} onClick={() => setSource(null)}>إزالة</button>}
          </Panel>

          <Panel>
            <PanelHead title="ملف المخرج" />
            <div className="grid grid-2">
              <Stat label="الأبعاد" value={info ? `${info.width}×${info.height}` : '—'} />
              <Stat label="الحجم" value={info ? `${(info.size / 1024).toFixed(0)}` : '—'} unit="KB" />
            </div>
            <div style={{ marginTop: 16 }}>
              <Slider label="جودة JPEG" value={quality} min={0.5} max={1} step={0.01} onChange={setQuality} format={(v) => `${Math.round(v * 100)}%`} />
            </div>
            <p style={{ color: 'var(--muted-2)', fontSize: 11.5, marginBottom: 0 }}>
              الجودة تُطبَّق على التصدير. PNG متاح من استوديو الفيديو للصور الثابتة عبر المحرك.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}
