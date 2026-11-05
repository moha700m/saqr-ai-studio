import { useRef, useState } from 'react';
import { Badge, Notice, Panel, PanelHead, Slider, Toggle } from '../components/ui';
import CameraCapture from '../components/CameraCapture';
import { IconFace, IconRefresh } from '../components/icons';
import { bridge } from '../lib/bridge';
import { useBridge } from '../lib/bridge-context';
import { fileToDataUrl, stripDataUrl } from '../lib/utils';

export default function Studio() {
  const { paired } = useBridge();
  const [source, setSource] = useState<string | null>(null);
  const [sourceName, setSourceName] = useState('');
  const [target, setTarget] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceState, setSourceState] = useState<'idle' | 'registered' | 'error'>('idle');
  const [strength, setStrength] = useState(1);
  const [feather, setFeather] = useState(21);
  const [keepMouth, setKeepMouth] = useState(true);
  const [keepEyes, setKeepEyes] = useState(false);
  const [enhance, setEnhance] = useState(false);
  const sourceInput = useRef<HTMLInputElement>(null);
  const targetInput = useRef<HTMLInputElement>(null);

  const registerSource = async (dataUrl: string, name: string) => {
    setSource(dataUrl);
    setSourceName(name);
    setResult(null);
    setSourceState('idle');
    if (!paired) return;
    try {
      setBusy(true);
      await bridge.setSource(stripDataUrl(dataUrl), name);
      setSourceState('registered');
    } catch (err) {
      setSourceState('error');
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onSourceFile = async (file?: File) => {
    if (!file) return;
    setError(null);
    await registerSource(await fileToDataUrl(file), file.name);
  };

  const process = async () => {
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      if (!paired) throw new Error('المحرك المكتبي غير مقترن. افتح الإعدادات وأدخل رمز الاقتران أولًا.');
      const response = await bridge.processFrame(stripDataUrl(target), true, {
        strength, mouthMask: keepMouth, keepEyes, feather, enhance,
      });
      setResult(`data:image/jpeg;base64,${response.image}`);
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
        <div>
          <b>{paired ? 'المحرك جاهز.' : 'وضع المعاينة بدون اقتران.'}</b>{' '}
          {paired
            ? 'الصورة المصدر مسجّلة في المحرك، والمعالجة تتم على جهازك. لا يُرفع شيء إلى الإنترنت.'
            : 'يمكنك تجهيز الصور وضبط الإعدادات، لكن زر المعالجة يحتاج اقترانًا بمحرك سطح المكتب (127.0.0.1).'}
        </div>
      </Notice>

      <div className="split">
        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="الإطار الهدف" hint="صورة أو إطار كاميرا تتم معالجته"
              action={<Badge tone={result ? 'ok' : ''}>{result ? 'تمت المعالجة' : 'بانتظار الهدف'}</Badge>} />
            <div className="viewport">
              {result ? <img src={result} alt="النتيجة" /> : target ? <img src={target} alt="الهدف" /> : (
                <div className="empty">
                  <IconFace /><div style={{ marginTop: 8 }}>اختر صورة هدف أو التقط من الكاميرا</div>
                </div>
              )}
              {metrics && (
                <div className="metrics-strip">
                  <span>{metrics.fps.toFixed(1)} FPS</span>
                  <span>كشف {metrics.detect_ms.toFixed(0)} ms</span>
                  <span>تبديل {metrics.swap_ms.toFixed(0)} ms</span>
                  <span>{metrics.faces} وجه</span>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <button className="btn btn-sm" onClick={() => targetInput.current?.click()}>صورة هدف</button>
              <button className="btn btn-primary" onClick={() => void process()} disabled={!target || busy}>
                {busy ? 'جارٍ التنفيذ…' : 'معالجة الآن'}
              </button>
              <button className="btn btn-ghost" onClick={() => { setResult(null); setMetrics(null); }} disabled={!result}>
                <IconRefresh /> إعادة
              </button>
              <input ref={targetInput} type="file" accept="image/*" hidden onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void fileToDataUrl(file).then((url) => { setTarget(url); setResult(null); });
              }} />
            </div>
            {error && <div className="notice notice-warn" style={{ marginTop: 12 }}>{error}</div>}
          </Panel>

          <Panel>
            <PanelHead title="التقاط مباشر" hint="إطار واحد فقط يغادر المتصفح" />
            <CameraCapture onCapture={(dataUrl) => { setTarget(dataUrl); setResult(null); }} />
          </Panel>
        </div>

        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="صورة المصدر" hint="وجه واحد واضح، إضاءة أمامية"
              action={<Badge tone={sourceState === 'registered' ? 'ok' : sourceState === 'error' ? 'danger' : ''}>
                {sourceState === 'registered' ? 'مسجّلة' : sourceState === 'error' ? 'فشل التسجيل' : 'محلية'}
              </Badge>} />
            <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
              <div style={{ width: 108, height: 108, borderRadius: 14, overflow: 'hidden', border: '1px solid var(--line)', background: '#0a0a12', flex: 'none' }}>
                {source ? <img src={source} alt="المصدر" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <div style={{ display: 'grid', placeItems: 'center', height: '100%', color: 'var(--muted-2)' }}><IconFace /></div>}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sourceName || 'لم تُختر صورة'}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <button className="btn btn-sm" onClick={() => sourceInput.current?.click()}>اختيار</button>
                  <button className="btn btn-sm btn-ghost" onClick={() => { setSource(null); setSourceName(''); setSourceState('idle'); }}>مسح</button>
                </div>
                <input ref={sourceInput} type="file" accept="image/*" hidden onChange={(e) => void onSourceFile(e.target.files?.[0])} />
              </div>
            </div>
            <div style={{ marginTop: 14 }}>
              <CameraCapture buttonLabel="استخدام كصورة مصدر" onCapture={(url) => void registerSource(url, 'كاميرا')} />
            </div>
          </Panel>

          <Panel>
            <PanelHead title="الضبط" hint="يُطبَّق على العملية التالية" />
            <div className="grid" style={{ gap: 16 }}>
              <Slider label="قوة التبديل" value={strength} onChange={setStrength} />
              <Slider label="نعومة الحافة" value={feather} min={3} max={61} step={2} onChange={setFeather} format={(v) => `${v}px`} />
              <Toggle title="قناع الفم" desc="يحافظ على حركة فمك أثناء الكلام" checked={keepMouth} onChange={setKeepMouth} />
              <Toggle title="حماية العينين" desc="يقلل وميض العين في الإطارات المتتابعة" checked={keepEyes} onChange={setKeepEyes} />
              <Toggle title="تحسين الوجه" desc="يتطلب نموذج enhancer مثبتًا" checked={enhance} onChange={setEnhance} />
            </div>
            <div className="notice" style={{ marginTop: 14 }}>
              هذه القيم تُرسل مع كل إطار. قناع الفم والعينان يقللان القطع عند الحركة السريعة.
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
