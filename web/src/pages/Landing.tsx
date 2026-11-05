import { Link } from 'react-router-dom';
import { IconCamera, IconChip, IconFace, IconLock, IconShield, IconSpark } from '../components/icons';
import { useBridge } from '../lib/bridge-context';

const features = [
  { icon: IconChip, title: 'كشف عتاد تلقائي', body: 'يفحص المعالج، كرت الشاشة، الذاكرة، والمزوّدات الفعلية قبل اختيار الخلفية — لا تخمين ولا إعداد يدوي.' },
  { icon: IconFace, title: 'محرك تبديل ONNX', body: 'كشف، محاذاة، تبديل، وتحسين في خط أنابيب واحد مع أقنعة فم وعين وجبهة قابلة للضبط.' },
  { icon: IconCamera, title: 'كاميرا مباشرة', body: 'طابور إطارات محدود يُسقط القديم بدل أن يتأخر، مع مقاييس FPS وزمن استجابة حقيقية.' },
  { icon: IconLock, title: 'محلي أولًا', body: 'المعالجة على جهازك. السحابة معطّلة افتراضيًا ولا تعمل إلا بعنوان تختاره أنت وموافقة صريحة.' },
  { icon: IconShield, title: 'جسر محلي مُقفل', body: 'رمز اقتران لمرة واحدة، رموز جلسات مُهشّرة، تحقق من الأصل، وربط على 127.0.0.1 فقط.' },
  { icon: IconSpark, title: 'واجهة ويب حقيقية', body: 'تعمل على الهاتف وسطح المكتب، تلتقط الكاميرا عبر HTTPS، وتتصل بالمحرك المكتبي عند الحاجة.' },
];

export default function Landing() {
  const { status } = useBridge();
  return (
    <div style={{ maxWidth: 1240, margin: '0 auto', padding: '22px 20px 80px' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '6px 0 26px' }}>
        <Link to="/" className="brand" style={{ padding: 0 }}>
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-title">SAQR <span style={{ color: 'var(--violet)' }}>AI</span></div>
            <div className="brand-sub">Face Studio</div>
          </div>
        </Link>
        <nav className="spacer landing-nav" style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
          <Link to="/docs" style={{ color: 'var(--muted)', fontSize: 13 }}>التوثيق</Link>
          <Link to="/models" style={{ color: 'var(--muted)', fontSize: 13 }}>النماذج</Link>
          <Link to="/privacy" style={{ color: 'var(--muted)', fontSize: 13 }}>الخصوصية</Link>
          <Link to="/app" className="btn btn-primary btn-sm">افتح الاستوديو</Link>
        </nav>
      </header>

      <section className="brand-hero">
        <div className="hero-grid">
          <div>
            <span className="badge badge-violet"><span className="dot" />إصدار المعاينة 0.9 — محرك حقيقي</span>
            <h1>استوديو الوجوه<br />الذي يعرف جهازك.</h1>
            <p>
              بديل DeepLiveCam مبني من الصفر: كشف عتاد، اختيار خلفية موثّق، تبديل وجوه ONNX،
              كاميرا مباشرة، ومعالجة صور وفيديو — كل ذلك محليًا على جهازك، مع جسر آمن للواجهة.
            </p>
            <div className="hero-actions">
              <Link to="/app" className="btn btn-primary">ابدأ الآن</Link>
              <Link to="/downloads" className="btn btn-ghost">تثبيت سطح المكتب</Link>
              <span className={`badge ${status === 'online' ? 'badge-ok' : 'badge-warn'}`}>
                <span className="dot" />{status === 'online' ? 'المحرك المحلي متاح' : 'المحرك المحلي غير مشغّل'}
              </span>
            </div>
            <div className="tiles" style={{ marginTop: 26 }}>
              <div className="tile"><b>خلفيات</b><span>CUDA · TRT · DML</span></div>
              <div className="tile"><b>خط الأنابيب</b><span>ONNX</span></div>
              <div className="tile"><b>الخصوصية</b><span>محلي</span></div>
              <div className="tile"><b>الجسر</b><span>مقترن</span></div>
            </div>
          </div>
          <div className="hero-orbit" aria-hidden>
            <div className="ring" />
            <div className="ring" />
            <div className="ring" />
            <div className="core">S</div>
          </div>
        </div>
      </section>

      <section style={{ marginTop: 46 }}>
        <div className="panel-head">
          <div>
            <h2 style={{ fontSize: 22 }}>ما الذي يجعله مختلفًا</h2>
            <div className="hint">ليست إعادة تغليف. كل زر هنا متصل بمحرك فعلي.</div>
          </div>
        </div>
        <div className="grid grid-3">
          {features.map((feature) => (
            <div className="feature" key={feature.title}>
              <div className="ic"><feature.icon /></div>
              <h3>{feature.title}</h3>
              <p>{feature.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 46 }} className="grid grid-3">
        {[
          { tag: 'MODE A', title: 'محلي', body: 'المحرك على جهازك، الكاميرا لا تغادر الذاكرة. الافتراضي والأسرع.', tone: 'badge-ok' },
          { tag: 'MODE B', title: 'سحابي', body: 'معطّل افتراضيًا. يتطلب عنوان endpoint تملكه أنت وموافقة صريحة لكل ملف.', tone: 'badge-warn' },
          { tag: 'MODE C', title: 'هجين', body: 'كاميرا محلية ومعاينة محلية، مع إرسال ملف محدد فقط عند طلبك.', tone: 'badge-cyan' },
        ].map((mode) => (
          <div className="panel panel-pad" key={mode.title}>
            <span className={`badge ${mode.tone}`}><span className="dot" />{mode.tag}</span>
            <h3 style={{ margin: '12px 0 6px' }}>{mode.title}</h3>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>{mode.body}</p>
          </div>
        ))}
      </section>

      <footer style={{ marginTop: 56, borderTop: '1px solid var(--line)', paddingTop: 20, display: 'flex', gap: 16, flexWrap: 'wrap', color: 'var(--muted-2)', fontSize: 12 }}>
        <span>SAQR AI Studio — معاينة 0.9</span>
        <span>·</span>
        <Link to="/privacy">الخصوصية</Link>
        <span>·</span>
        <Link to="/docs">التوثيق</Link>
        <span className="spacer" />
        <span>ابحث عن شارة «محتوى اصطناعي» عند المشاركة.</span>
      </footer>
    </div>
  );
}
