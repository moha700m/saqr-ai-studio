import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useBridge } from '../lib/bridge-context';
import {
  IconBook, IconBox, IconCamera, IconChip, IconDownload, IconFace, IconFilm, IconGrid,
  IconImage, IconShield, IconSliders,
} from './icons';

const groups = [
  {
    label: 'الاستوديو',
    items: [
      { to: '/app', label: 'لوحة التحكم', icon: IconGrid },
      { to: '/studio', label: 'استوديو الوجه', icon: IconFace },
      { to: '/live', label: 'الكاميرا المباشرة', icon: IconCamera },
      { to: '/image', label: 'استوديو الصور', icon: IconImage },
      { to: '/video', label: 'استوديو الفيديو', icon: IconFilm },
    ],
  },
  {
    label: 'النظام',
    items: [
      { to: '/models', label: 'مكتبة النماذج', icon: IconBox },
      { to: '/hardware', label: 'العتاد والتشخيص', icon: IconChip },
      { to: '/settings', label: 'الإعدادات', icon: IconSliders },
    ],
  },
  {
    label: 'المزيد',
    items: [
      { to: '/downloads', label: 'التنزيلات', icon: IconDownload },
      { to: '/docs', label: 'التوثيق', icon: IconBook },
      { to: '/privacy', label: 'الخصوصية', icon: IconShield },
    ],
  },
];

const titles: Record<string, { title: string; sub: string }> = {
  '/': { title: 'SAQR AI Studio', sub: 'استوديو تبديل الوجوه — محلي أولًا' },
  '/app': { title: 'لوحة التحكم', sub: 'نظرة شاملة على العتاد والمحرك' },
  '/studio': { title: 'استوديو الوجه', sub: 'صورة مصدر، هدف، وضبط دقيق' },
  '/live': { title: 'الكاميرا المباشرة', sub: 'معاينة فورية مع كشف الوجوه' },
  '/image': { title: 'استوديو الصور', sub: 'معالجة صورة واحدة بجودة كاملة' },
  '/video': { title: 'استوديو الفيديو', sub: 'مقاطع، إطارات، وتصدير' },
  '/models': { title: 'مكتبة النماذج', sub: 'تراخيص واضحة وتحميل موثّق' },
  '/hardware': { title: 'العتاد والتشخيص', sub: 'كشف تلقائي واختيار الخلفية' },
  '/settings': { title: 'الإعدادات', sub: 'الاقتران والخصوصية والمحرك' },
  '/downloads': { title: 'التنزيلات', sub: 'سطح المكتب والويب والبناء من المصدر' },
  '/docs': { title: 'التوثيق', sub: 'من التثبيت إلى أول إطار' },
  '/privacy': { title: 'الخصوصية', sub: 'أين تذهب بياناتك — بالتفصيل' },
};

export default function Layout() {
  const location = useLocation();
  const { status, paired } = useBridge();
  const meta = titles[location.pathname] ?? titles['/app'];

  const statusTone = status === 'online' ? (paired ? 'badge-ok' : 'badge-warn') : status === 'checking' ? '' : 'badge-danger';
  const statusLabel = status === 'online' ? (paired ? 'المحرك مقترن' : 'المحرك متاح') : status === 'checking' ? 'جارٍ الفحص' : 'المحرك غير متصل';

  return (
    <div className="shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-title">SAQR <span style={{ color: 'var(--violet)' }}>AI</span></div>
            <div className="brand-sub">Face Studio</div>
          </div>
        </NavLink>

        <nav className="nav">
          {groups.map((group) => (
            <div key={group.label}>
              <div className="nav-label">{group.label}</div>
              {group.items.map((item) => (
                <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                  <item.icon className="ico" />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="mode-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <h4>وضع المعالجة</h4>
            <span className={`badge ${statusTone}`}><span className="dot" />{statusLabel}</span>
          </div>
          <p>المعالجة محلية افتراضيًا. لا يُرفع أي ملف دون طلب صريح منك.</p>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div>
            <h1>{meta.title}</h1>
            <div className="sub">{meta.sub}</div>
          </div>
          <div className="topbar-actions">
            <span className={`badge ${statusTone}`}><span className="dot" />{statusLabel}</span>
            <span className="badge badge-violet"><span className="dot" />محلي</span>
            <NavLink to="/settings" className="btn btn-sm btn-ghost">اقتران</NavLink>
          </div>
        </header>

        <main className="page">
          <Outlet />
        </main>

        <nav className="bottom-nav">
          <NavLink to="/app" className={({ isActive }) => (isActive ? 'active' : '')}><IconGrid /><span>الرئيسية</span></NavLink>
          <NavLink to="/studio" className={({ isActive }) => (isActive ? 'active' : '')}><IconFace /><span>الاستوديو</span></NavLink>
          <NavLink to="/live" className={({ isActive }) => (isActive ? 'active' : '')}><IconCamera /><span>الكاميرا</span></NavLink>
          <NavLink to="/models" className={({ isActive }) => (isActive ? 'active' : '')}><IconBox /><span>النماذج</span></NavLink>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? 'active' : '')}><IconSliders /><span>الإعدادات</span></NavLink>
        </nav>
      </div>
    </div>
  );
}
