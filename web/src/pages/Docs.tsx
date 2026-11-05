import { Link } from 'react-router-dom';
import { Notice, Panel, PanelHead } from '../components/ui';

export default function Docs() {
  return (
    <div className="split">
      <div className="grid" style={{ gap: 18 }}>
        <Panel className="doc">
          <h2 style={{ marginTop: 0 }}>البداية في خمس دقائق</h2>
          <p>SAQR AI Studio مكوّن من ثلاثة أجزاء تعمل معًا:</p>
          <ul>
            <li><b>المحرك</b> (Python + ONNX Runtime): كشف العتاد، النماذج، خط أنابيب الوجه، الكاميرا، الفيديو.</li>
            <li><b>سطح المكتب</b> (PySide6): يشغّل المحرك ويعرض رمز الاقتران.</li>
            <li><b>الويب</b> (React): واجهة الاستوديو، الكاميرا، والمعالجة عبر الجسر المحلي.</li>
          </ul>

          <h3>1. تثبيت المحرك</h3>
          <pre className="code">{`git clone <repo> saqr-ai-studio
cd saqr-ai-studio
python -m venv .venv && source .venv/bin/activate
pip install -e "engine[desktop,dev]"
saqr doctor`}</pre>
          <p><code>saqr doctor</code> يطبع المعالج، الكرت، الذاكرة، ونتيجة فحص كل مزوّد ONNX بجلسة حقيقية.</p>

          <h3>2. النماذج</h3>
          <pre className="code">{`saqr models download yunet-2023mar
saqr models import ./inswapper_128.onnx --kind swapper --accept-license`}</pre>
          <p>لا تُوزّع SAQR نموذج التبديل. راجع <Link to="/models">المكتبة</Link> للتراخيص.</p>

          <h3>3. تشغيل المحرك والاقتران</h3>
          <pre className="code">{`saqr serve --pair
# SAQR bridge on http://127.0.0.1:8765
# Pairing code: 123456 (valid 180s)`}</pre>
          <p>افتح <Link to="/settings">الإعدادات</Link>، أدخل الرمز، ثم <Link to="/studio">استوديو الوجه</Link>.</p>

          <h3>4. المعالجة</h3>
          <pre className="code">{`# صورة
saqr process image in.jpg out.png --source face.jpg

# فيديو (يحافظ على الصوت)
saqr process video in.mp4 out.mp4 --source face.jpg

# قياس حقيقي
saqr benchmark --frames 60 --image portrait.jpg --swap`}</pre>

          <h3>5. الواجهة المكتبية</h3>
          <pre className="code">{`python -m saqr_desktop`}</pre>
          <p>تضم لوحة التحكم، استوديو الوجه، الكاميرا، الصور، الفيديو، المكتبة، التشخيص، والإعدادات. تعمل دون الويب.</p>
        </Panel>

        <Panel className="doc">
          <h2 style={{ marginTop: 0 }}>الجسر المحلي — واجهة API</h2>
          <p>كل النقاط (عدا <code>/api/health</code> و<code>/api/pair</code>) تتطلب <code>Authorization: Bearer</code>.</p>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>النقطة</th><th>الطريقة</th><th>الوظيفة</th></tr></thead>
              <tbody>
                <tr><td><code>/api/health</code></td><td>GET</td><td>حالة عامة بلا أسرار</td></tr>
                <tr><td><code>/api/pair</code></td><td>POST</td><td>استبدال رمز لمرة واحدة بجلسة</td></tr>
                <tr><td><code>/api/hardware</code></td><td>GET</td><td>تقرير العتاد والقرار</td></tr>
                <tr><td><code>/api/models</code></td><td>GET</td><td>الكتالوج وحالة التثبيت</td></tr>
                <tr><td><code>/api/source</code></td><td>POST</td><td>تسجيل وجه المصدر (base64)</td></tr>
                <tr><td><code>/api/frame</code></td><td>POST</td><td>معالجة إطار وإرجاع JPEG + مقاييس</td></tr>
                <tr><td><code>/api/engine/status</code></td><td>GET</td><td>حالة النماذج والجلسات</td></tr>
              </tbody>
            </table>
          </div>
          <h3>مثال</h3>
          <pre className="code">{`TOKEN=$(curl -s -X POST http://127.0.0.1:8765/api/pair \\
  -H 'Content-Type: application/json' \\
  -d '{"code":"123456"}' | jq -r .token)

curl -s http://127.0.0.1:8765/api/hardware \\
  -H "Authorization: Bearer $TOKEN" | jq .decision`}</pre>
          <Notice tone="warn">
            لا تضع الرمز في عنوان URL أو في سجلات. الجلسة صالحة 12 ساعة ويمكن إلغاؤها من التطبيق.
          </Notice>
        </Panel>
      </div>

      <div className="grid" style={{ gap: 18 }}>
        <Panel className="doc">
          <h2 style={{ marginTop: 0 }}>Safari على iPhone</h2>
          <ul>
            <li>يجب أن تُفتح الصفحة عبر HTTPS؛ Safari يمنع الكاميرا على HTTP.</li>
            <li>الإذن يُطلب بعد الضغط على «تشغيل» — لا يوجد طلب تلقائي.</li>
            <li>استخدم <code>playsInline</code> (مطبّق) لمنع ملء الشاشة التلقائي.</li>
            <li>الجسر المحلي من هاتف على الشبكة يحتاج عنوان جهاز الكمبيوتر، وليس 127.0.0.1، مع HTTPS. الافتراضي مغلق.</li>
          </ul>

          <h2>استكشاف الأخطاء</h2>
          <h3>«المحرك غير متصل»</h3>
          <p>شغّل <code>saqr serve</code>، وتأكد أن المنفذ 8765 غير محجوب، وأن الصفحة على origin مسموح في <code>settings.allowed_origins</code>.</p>
          <h3>«no detector model installed»</h3>
          <p><code>saqr models download yunet-2023mar</code> ثم أعد تشغيل المحرك.</p>
          <h3>«CUDA unavailable»</h3>
          <p>ثبّت <code>onnxruntime-gpu</code> المتوافق مع إصدار CUDA لديك، أو اترك الاختيار التلقائي يستخدم DirectML/CPU.</p>
          <h3>الكاميرا سوداء على Windows</h3>
          <p>يستخدم المحرك <code>CAP_DSHOW</code>. أغلق أي تطبيق آخر يحجز الكاميرا، وجرّب مؤشرًا مختلفًا من قائمة الأجهزة.</p>

          <h2>البناء والاختبار</h2>
          <pre className="code">{`cd engine && python -m pytest ../tests -q
cd web && npm ci && npm run build
bash scripts/build_windows.sh   # على Windows فقط`}</pre>
        </Panel>

        <Panel>
          <PanelHead title="مراجع" />
          <div className="grid" style={{ gap: 8 }}>
            {[
              ['المعمارية', 'ARCHITECTURE.md'],
              ['قرارات العتاد', 'TECHNICAL_RESEARCH.md'],
              ['تراخيص النماذج', 'MODEL_LICENSES.md'],
              ['تقرير الاختبار', 'TEST_REPORT.md'],
              ['حالة المشروع', 'PROJECT_STATE.md'],
            ].map(([label, file]) => (
              <div key={file} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                <span style={{ color: 'var(--muted)' }}>{label}</span>
                <code style={{ direction: 'ltr', color: 'var(--muted-2)' }}>{file}</code>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
