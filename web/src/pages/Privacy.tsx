import { Notice, Panel, PanelHead } from '../components/ui';
import { IconLock, IconShield } from '../components/icons';

export default function Privacy() {
  return (
    <div className="split doc">
      <div className="grid" style={{ gap: 18 }}>
        <Panel>
          <span className="badge badge-ok"><span className="dot" />محلي أولًا</span>
          <h2 style={{ margin: '12px 0 8px' }}>بياناتك لا تغادر جهازك افتراضيًا.</h2>
          <p>
            كل المعالجة العصبية تحدث في المحرك على جهازك. الواجهة لا ترفع الصور أو الفيديو إلى خادم SAQR،
            ولا يوجد خادم SAQR مركزي في هذه النسخة. الجسر المحلي يستمع على <code>127.0.0.1</code> فقط.
          </p>
          <div className="grid grid-2" style={{ marginTop: 14 }}>
            {[
              ['المعالجة المحلية', 'مفعّلة', 'ok'],
              ['المعالجة السحابية', 'معطّلة', ''],
              ['رفع تلقائي للوسائط', 'معطّل', ''],
              ['تسجيل تلقائي', 'معطّل', ''],
              ['تشغيل الكاميرا تلقائيًا', 'معطّل', ''],
              ['تليمترية', 'لا يوجد', ''],
            ].map(([label, value, tone]) => (
              <div key={label} className="toggle-row">
                <div className="txt"><b>{label}</b></div>
                <span className={`badge ${tone ? 'badge-ok' : ''}`}><span className="dot" />{value}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelHead title="ما الذي يُخزَّن وأين" />
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>البيانات</th><th>المكان</th><th>المدة</th></tr></thead>
              <tbody>
                <tr><td>صورة المصدر</td><td>ذاكرة المحرك + <code>SAQR_HOME/media</code> إن اخترت الحفظ</td><td>حتى إغلاق الجلسة أو الحذف</td></tr>
                <tr><td>إطارات الكاميرا</td><td>ذاكرة فقط</td><td>لا تُحفظ</td></tr>
                <tr><td>مخرجات المعالجة</td><td>تنزيل يدوي في المتصفح</td><td>أنت تتحكم</td></tr>
                <tr><td>رمز الجلسة</td><td>sessionStorage</td><td>حتى إغلاق التبويب (12 ساعة كحد أقصى)</td></tr>
                <tr><td>إعدادات الواجهة</td><td>localStorage</td><td>حتى تحذفها</td></tr>
                <tr><td>السجلات</td><td><code>SAQR_HOME/logs</code></td><td>دوران تلقائي عند الإغلاق</td></tr>
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel>
          <PanelHead title="المعالجة السحابية (اختيارية)" />
          <p>
            SAQR لا يوفّر مزوّد سحابة ولا يملك مفاتيح لأي خدمة. يمكنك ربط endpoint تملكه أنت في
            <code> cloud.json</code>. عندها فقط:
          </p>
          <ul>
            <li>يُطلب منك تأكيد صريح يذكر اسم الملف والوجهة قبل كل رفع.</li>
            <li>يُعرض تقدم الرفع ويمكنك الإلغاء.</li>
            <li>يُحذف الملف المؤقت بعد المعالجة، ولا يُحتفظ بنسخة محلية.</li>
            <li>لا تُرفع feeds الكاميرا أبدًا في الوضع السحابي.</li>
          </ul>
          <Notice tone="warn">
            <b>تحذير قانوني:</b> قد تمنع قوانين بعض الدول إنشاء أو نشر محتوى اصطناعي لشخص حقيقي دون موافقة.
            أنت مسؤول عن الالتزام. لا تستخدم SAQR لإنشاء مواد جنسية غير رضائية أو انتحال هوية.
          </Notice>
        </Panel>
      </div>

      <div className="grid" style={{ gap: 18 }}>
        <Panel>
          <div style={{ width: 40, height: 40, borderRadius: 12, display: 'grid', placeItems: 'center', background: 'var(--violet-soft)', color: '#c4b5fd' }}><IconShield /></div>
          <h3 style={{ margin: '12px 0 6px' }}>ضوابط الجسر</h3>
          <ul style={{ color: 'var(--muted)', fontSize: 12.5, paddingRight: 18 }}>
            <li>رمز اقتران 6 أرقام، صالح 3 دقائق، لمرة واحدة.</li>
            <li>حد لمحاولات الاقتران (6/دقيقة) لمنع التخمين.</li>
            <li>الرموز تُخزَّن مُهشّرة (SHA-256) في الذاكرة فقط.</li>
            <li>تحقق من Origin قبل تنفيذ أي معالج.</li>
            <li>رفض أي طلب من عنوان غير loopback.</li>
            <li>حد أقصى 12 MB للجسم، وفك ترميز دفاعي للصور.</li>
          </ul>
        </Panel>

        <Panel>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <IconLock />
            <b style={{ fontSize: 13.5 }}>لا بصمات وجه</b>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 12.5, marginBottom: 0 }}>
            لا يستخرج SAQR embeddings ولا يحفظها. المقارنة بين الوجوه تتم هندسيًا داخل الإطار فقط،
            ولا تُنشأ قاعدة بيانات هوية. حذف مجلد <code>SAQR_HOME</code> يمحو كل ما خزّنه المحرك.
          </p>
        </Panel>

        <Panel>
          <PanelHead title="إفصاح المحتوى الاصطناعي" />
          <p style={{ color: 'var(--muted)', fontSize: 12.5 }}>
            عند نشر أي مخرج، أضف وصفًا صريحًا بأنه مُولّد أو مُعدّل رقميًا. لا تستخدم SAQR لانتحال شخصية
            أو للإضرار بسمعة شخص. بعض المنصات تفرض علامات مائية تلقائية.
          </p>
        </Panel>
      </div>
    </div>
  );
}
