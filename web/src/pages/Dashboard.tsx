import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Panel, PanelHead, Stat, Badge, Notice, KV } from '../components/ui';
import { IconCamera, IconChip, IconFace, IconImage } from '../components/icons';
import { useBridge } from '../lib/bridge-context';
import { bridge } from '../lib/bridge';

export default function Dashboard() {
  const { status, paired, health, hardware, loadHardware } = useBridge();
  const [engine, setEngine] = useState<{ loaded: boolean; error?: string; status?: any } | null>(null);
  const [models, setModels] = useState<number | null>(null);

  useEffect(() => {
    if (!paired) return;
    if (!hardware) void loadHardware().catch(() => undefined);
    bridge.engineStatus().then(setEngine).catch(() => setEngine(null));
    bridge.models().then((data) => setModels(data.catalog.filter((m) => m.installed).length)).catch(() => setModels(null));
  }, [paired, hardware, loadHardware]);

  const provider = hardware?.decision;
  const gpu = hardware?.profile.gpus?.[0];

  return (
    <div className="grid" style={{ gap: 18 }}>
      <section className="panel panel-pad" style={{ background: 'linear-gradient(120deg, rgba(139,92,246,.14), rgba(34,211,238,.05) 60%, transparent)' }}>
        <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <Badge tone={paired ? 'ok' : status === 'online' ? 'warn' : 'danger'}>
              {paired ? 'المحرك المكتبي مقترن' : status === 'online' ? 'المحرك متاح — بانتظار الاقتران' : 'محلي فقط في المتصفح'}
            </Badge>
            <h2 style={{ margin: '12px 0 6px', fontSize: 24 }}>جاهز للعمل، على جهازك.</h2>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13.5, maxWidth: 620 }}>
              ابدأ بصورة مصدر أو جرّب الكاميرا. كل المعالجة العصبية تحدث في المحرك المكتبي؛
              واجهة المتصفح تعرض وتتحكم فقط.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Link to="/studio" className="btn btn-primary"><IconFace /> استوديو الوجه</Link>
            <Link to="/live" className="btn"><IconCamera /> الكاميرا</Link>
          </div>
        </div>
      </section>

      <div className="grid grid-4">
        <Stat label="الخلفية المختارة" value={provider ? provider.label : '—'} foot={provider?.reason ?? 'شغّل المحرك لعرض القرار'} />
        <Stat label="كرت الشاشة" value={gpu ? gpu.name : 'لا يوجد / غير معروف'} foot={gpu ? `${gpu.vendor} · ${gpu.vram_mb ?? '?'} MB` : 'CPU backend'} />
        <Stat label="المعالج" value={hardware ? `${hardware.profile.cpu.physical_cores}C` : '—'} unit={hardware ? `/ ${hardware.profile.cpu.logical_cores}T` : ''} foot={hardware?.profile.cpu.brand} />
        <Stat label="نماذج مثبتة" value={models ?? '—'} unit={models !== null ? 'من 3' : ''} foot="مكتبة النماذج" />
      </div>

      <div className="split">
        <Panel>
          <PanelHead title="حالة النظام" hint="قراءة مباشرة من المحرك عند الاقتران"
            action={<Link to="/hardware" className="btn btn-sm">التشخيص الكامل</Link>} />
          {paired && hardware ? (
            <div>
              <KV k="المعالج" v={hardware.profile.cpu.brand} />
              <KV k="الأنوية" v={`${hardware.profile.cpu.physical_cores} فيزيائي / ${hardware.profile.cpu.logical_cores} منطقي`} />
              <KV k="تعليمات" v={hardware.profile.cpu.isa.length ? hardware.profile.cpu.isa.join(', ') : 'غير متاحة على هذه المنصة'} />
              <KV k="الذاكرة" v={`${hardware.profile.system.ram_total_mb} MB`} />
              <KV k="نظام التشغيل" v={`${hardware.profile.system.os_name} (${hardware.profile.system.machine})`} />
              <KV k="سلسلة الاحتياط" v={provider?.chain.join(' → ')} />
              <KV k="المحرك" v={engine?.loaded ? <Badge tone="ok">محمل</Badge> : <Badge tone="warn">{engine?.error ?? 'لم يُحمَّل بعد'}</Badge>} />
              {hardware.profile.notes.map((note) => <div key={note} style={{ marginTop: 8 }}><Notice tone="warn">{note}</Notice></div>)}
            </div>
          ) : (
            <div>
              <Notice tone="violet">
                <div>
                  <b>لم يتم الاقتران بعد.</b> شغّل التطبيق المكتبي ثم أدخل رمز الاقتران من صفحة الإعدادات.
                  يمكنك تجربة الكاميرا وكشف الوجوه في المتصفح الآن دون اقتران.
                </div>
              </Notice>
              <div style={{ marginTop: 14 }}>
                <KV k="العنوان المتوقع" v="http://127.0.0.1:8765" />
                <KV k="حالة الجسر" v={status === 'online' ? 'متاح' : health ? 'متاح' : 'غير متاح'} />
                <KV k="المعالجة" v={<Badge tone="violet">محلية فقط</Badge>} />
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
                <Link to="/settings" className="btn btn-primary btn-sm">إدخال رمز الاقتران</Link>
                <Link to="/live" className="btn btn-sm"><IconCamera /> تجربة الكاميرا</Link>
              </div>
            </div>
          )}
        </Panel>

        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="ابدأ بسرعة" />
            <div className="grid" style={{ gap: 10 }}>
              {[
                { to: '/studio', icon: IconFace, title: 'استوديو الوجه', body: 'ارفع صورة المصدر واضبط القناع' },
                { to: '/live', icon: IconCamera, title: 'الكاميرا المباشرة', body: 'معاينة، كشف، وبث للمحرك' },
                { to: '/image', icon: IconImage, title: 'استوديو الصور', body: 'معالجة وتصدير PNG/JPEG' },
                { to: '/models', icon: IconChip, title: 'النماذج', body: 'ثبّت YuNet وراجع التراخيص' },
              ].map((item) => (
                <Link key={item.to} to={item.to} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: 11, borderRadius: 12, border: '1px solid var(--line)' }}>
                  <span style={{ width: 34, height: 34, borderRadius: 10, display: 'grid', placeItems: 'center', background: 'var(--violet-soft)', color: '#c4b5fd' }}><item.icon /></span>
                  <span style={{ minWidth: 0 }}>
                    <b style={{ display: 'block', fontSize: 13 }}>{item.title}</b>
                    <small style={{ color: 'var(--muted-2)', fontSize: 11.5 }}>{item.body}</small>
                  </span>
                </Link>
              ))}
            </div>
          </Panel>
          <Panel>
            <PanelHead title="تعريف المحتوى الاصطناعي" />
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12.5 }}>
              عند مشاركة أي مخرج، أضف إشارة واضحة إلى أنه محتوى مُولّد. لا تستخدم وجوه أشخاص دون موافقتهم،
              ولا تنشر مواد غير رضائية. هذه مسؤوليتك القانونية والأخلاقية.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}
