import { useState } from 'react';
import { Badge, KV, Panel, PanelHead, Toggle } from '../components/ui';
import { IconLock, IconWifiOff } from '../components/icons';
import { useBridge } from '../lib/bridge-context';
import { BRIDGE_BASE } from '../lib/bridge';

const STORAGE_KEY = 'saqr.settings.v1';

interface LocalSettings {
  autoCamera: boolean;
}

const defaults: LocalSettings = { autoCamera: false };

function loadSettings(): LocalSettings {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') };
  } catch {
    return defaults;
  }
}

export default function Settings() {
  const { status, paired, health, connect, disconnect } = useBridge();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<LocalSettings>(loadSettings);

  const update = (patch: Partial<LocalSettings>) => {
    const next = { ...settings, ...patch };
    setSettings(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const pair = async () => {
    setBusy(true);
    setError(null);
    try {
      await connect(code.trim());
      setCode('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid" style={{ gap: 18 }}>
      <div className="split">
        <div className="grid" style={{ gap: 18 }}>
          <Panel>
            <PanelHead title="الجسر المحلي" hint="رمز لمرة واحدة من التطبيق المكتبي"
              action={<Badge tone={paired ? 'ok' : status === 'online' ? 'warn' : 'danger'}>{paired ? 'مقترن' : status === 'online' ? 'متاح' : 'غير متصل'}</Badge>} />
            {paired ? (
              <>
                <KV k="الحالة" v="جلسة نشطة" />
                <KV k="العنوان" v={BRIDGE_BASE || window.location.origin} />
                <KV k="الإصدار" v={health?.version ?? '—'} />
                <KV k="الجلسات" v={health?.paired_sessions ?? '—'} />
                <button className="btn btn-danger btn-sm" style={{ marginTop: 12 }} onClick={() => void disconnect()}>إنهاء الاقتران</button>
              </>
            ) : (
              <>
                <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 0 }}>
                  شغّل تطبيق سطح المكتب، افتح صفحة الجسر، وانسخ الرمز المكوّن من 6 أرقام. الرمز صالح 3 دقائق ويُستخدم مرة واحدة.
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input className="input" inputMode="numeric" placeholder="000000" value={code} maxLength={6}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                    onKeyDown={(e) => { if (e.key === 'Enter') void pair(); }} />
                  <button className="btn btn-primary" disabled={code.length < 4 || busy} onClick={() => void pair()}>
                    {busy ? '…' : 'اقتران'}
                  </button>
                </div>
                <div className="notice" style={{ marginTop: 12 }}>
                  <IconLock />
                  <span>لا يفتح المحرك أي منفذ عام. يستمع على 127.0.0.1 فقط، ويرفض أي Origin غير مسجّل.</span>
                </div>
              </>
            )}
            {error && <div className="notice notice-warn" style={{ marginTop: 12 }}>{error}</div>}
          </Panel>

          <Panel>
            <PanelHead title="الخصوصية" hint="محفوظة في هذا المتصفح فقط" />
            <Toggle title="تشغيل الكاميرا تلقائيًا" desc="إن فعّلته، تفتح صفحة الكاميرا الطلب فورًا. المتصفح قد يطلبه مرة أخرى." checked={settings.autoCamera} onChange={(v) => update({ autoCamera: v })} />
            {[
              ['المعالجة السحابية', 'معطّلة — لا مزوّد مضمّن'],
              ['حفظ الوسائط المعالجة', 'يدوي فقط'],
              ['رفع تلقائي', 'غير موجود'],
              ['تليمترية', 'غير موجودة'],
            ].map(([title, value]) => (
              <div className="toggle-row" key={title}>
                <div className="txt"><b>{title}</b><small>{value}</small></div>
                <span className="badge"><span className="dot" />{value}</span>
              </div>
            ))}
            <div className="notice" style={{ marginTop: 12 }}>
              <IconWifiOff />
              <span>هذه الخيارات تخص واجهة الويب. إعدادات المحرك المكتبي تُدار من التطبيق نفسه.</span>
            </div>
          </Panel>
        </div>

        <div className="grid" style={{ gap: 18 }}>
          <Panel>
            <PanelHead title="معلومات النظام" />
            <KV k="عنوان الجسر" v={<code style={{ direction: 'ltr', fontSize: 11.5 }}>{BRIDGE_BASE || window.location.origin}</code>} />
            <KV k="المنفذ" v="8765" />
            <KV k="الاستضافة" v={window.location.host} />
            <KV k="HTTPS" v={window.location.protocol === 'https:' ? 'نعم' : 'لا'} />
            <KV k="حالة الكاميرا" v={navigator.mediaDevices ? 'مدعومة' : 'غير مدعومة'} />
            <KV k="اللغة" v={navigator.language} />
          </Panel>

          <Panel>
            <PanelHead title="مساحة البيانات" />
            <p style={{ color: 'var(--muted)', fontSize: 12.5 }}>
              الواجهة تحفظ إعدادات العرض والرمز المؤقت فقط. لا تخزّن صورًا ولا فيديوهات ولا بصمات وجوه.
            </p>
            <button className="btn btn-sm btn-danger" onClick={() => {
              sessionStorage.clear();
              localStorage.removeItem(STORAGE_KEY);
              localStorage.removeItem('saqr.bridge.token');
              setSettings(defaults);
            }}>حذف بيانات المتصفح</button>
          </Panel>

          <Panel>
            <PanelHead title="Safari على iPhone" />
            <ul style={{ color: 'var(--muted)', fontSize: 12.5, paddingRight: 18, margin: 0 }}>
              <li>افتح الصفحة عبر HTTPS. الكاميرا لا تعمل على HTTP خارج localhost.</li>
              <li>اضغط «تشغيل» — سيظهر طلب إذن الكاميرا؛ اختر «السماح».</li>
              <li>استخدم زر تبديل الكاميرا الأمامية/الخلفية من قائمة الأجهزة.</li>
              <li>لتشغيل المحرك، يجب أن يكون التطبيق المكتبي على نفس الشبكة ومقترنًا.</li>
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}
