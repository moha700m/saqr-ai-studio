import { Badge, Notice, Panel, PanelHead } from '../components/ui';
import { IconDownload } from '../components/icons';

const cards = [
  {
    title: 'Windows 10/11 (64-bit)', tag: 'المسار الأساسي', tone: 'violet' as const,
    status: 'يُبنى على windows-latest', body: 'مثبّت Inno Setup + PyInstaller، يكتشف العتاد ويثبّت النموذج المسموح فقط. لا يحتاج Python أو CUDA Toolkit.',
    steps: ['شغّل SAQR-AI-Setup.exe', 'اترك «تشغيل التشخيص» محددًا', 'اختر النموذج (YuNet تلقائيًا)', 'انتهِ — سيُفتح التطبيق'],
  },
  {
    title: 'macOS (Apple Silicon)', tag: 'من المصدر', tone: 'cyan' as const,
    status: 'مدعوم نظريًا — لم يُختبر على عتاد حقيقي', body: 'يستخدم CoreML إن توفر، وإلا CPU. حزمة PySide6 تعمل على arm64.',
    steps: ['python3 -m venv .venv', 'pip install -e engine[desktop]', 'python -m saqr_desktop'],
  },
  {
    title: 'Linux (x86_64 / arm64)', tag: 'مُختبر هنا', tone: 'ok' as const,
    status: 'مُختبر في بيئة البناء', body: 'المحرك والاختبارات تعمل على Linux arm64. واجهة سطح المكتب تحتاج PySide6 ومكتبات نظام.',
    steps: ['pip install -e engine', 'saqr doctor', 'saqr serve --pair'],
  },
  {
    title: 'الويب', tag: 'Cloudflare Pages', tone: 'warn' as const,
    status: 'جاهز للبناء — لا نشر تلقائي', body: 'بناء ثابت (Vite) مع رؤوس أمان. النشر يحتاج حساب Cloudflare وربط المستودع.',
    steps: ['cd web && npm ci', 'npm run build', 'wrangler pages deploy dist'],
  },
];

export default function Downloads() {
  return (
    <div className="grid" style={{ gap: 18 }}>
      <Notice tone="warn">
        <div>
          <b>لا روابط وهمية.</b> هذه النسخة بُنيت داخل بيئة Linux بلا Windows ولا حساب GitHub/Cloudflare، لذلك لا يوجد
          ملف <code>.exe</code> موقّع ولا رابط نشر عام. الأوامر أدناه تنتج الحزم فعليًا، وسير العمل في
          <code> .github/workflows</code> يبني المثبّت على GitHub.
        </div>
      </Notice>

      <div className="grid grid-2">
        {cards.map((card) => (
          <Panel key={card.title}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
              <h3 style={{ margin: 0, fontSize: 16 }}>{card.title}</h3>
              <Badge tone={card.tone}>{card.tag}</Badge>
            </div>
            <div style={{ color: 'var(--muted-2)', fontSize: 11.5, margin: '6px 0 10px' }}>{card.status}</div>
            <p style={{ color: 'var(--muted)', fontSize: 12.5 }}>{card.body}</p>
            <ol style={{ color: 'var(--muted)', fontSize: 12.5, paddingRight: 18, marginBottom: 0 }}>
              {card.steps.map((step) => <li key={step} style={{ marginBottom: 4 }}>{step}</li>)}
            </ol>
          </Panel>
        ))}
      </div>

      <Panel>
        <PanelHead title="بناء مثبّت Windows" hint="على جهاز Windows أو عبر GitHub Actions" />
        <pre className="code">{`# 1) بناء المحرك والواجهة
py -3.12 -m venv .venv
.venv\\Scripts\\pip install -e engine[desktop] pyinstaller
cd web && npm ci && npm run build && cd ..

# 2) حزمة التطبيق
pyinstaller installer/saqr-studio.spec

# 3) المثبّت (Inno Setup 6)
iscc installer/saqr-studio.iss

# الناتج: installer/Output/SAQR-AI-Setup.exe`}</pre>
        <div className="notice" style={{ marginTop: 12 }}>
          <IconDownload />
          <span>التوقيع الرقمي (Authenticode) غير مُهيأ في المستودع؛ يتطلب شهادة code-signing خاصة بك. المثبّت يعمل بدونها لكن Windows SmartScreen سيحذّر.</span>
        </div>
      </Panel>

      <Panel>
        <PanelHead title="متطلبات التشغيل" />
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>المكوّن</th><th>الحد الأدنى</th><th>الموصى به</th></tr></thead>
            <tbody>
              <tr><td>نظام التشغيل</td><td>Windows 10 64-bit</td><td>Windows 11 23H2+</td></tr>
              <tr><td>المعالج</td><td>x86_64 بأربع أنوية</td><td>8 أنوية حديثة مع AVX2</td></tr>
              <tr><td>الذاكرة</td><td>8 GB</td><td>16 GB</td></tr>
              <tr><td>كرت الشاشة</td><td>DirectX 12 (DirectML) أو CPU</td><td>NVIDIA RTX 20-series+ (CUDA)</td></tr>
              <tr><td>القرص</td><td>1.5 GB</td><td>3 GB (نماذج إضافية)</td></tr>
              <tr><td>الكاميرا</td><td>720p USB</td><td>1080p</td></tr>
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
