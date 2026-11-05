import type { SVGProps } from 'react';

const base = (props: SVGProps<SVGSVGElement>) => ({
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  ...props,
});

export const IconHome = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></svg>
);
export const IconGrid = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></svg>
);
export const IconFace = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M9 10h.01M15 10h.01M8.5 15c1 1.2 2.2 1.8 3.5 1.8s2.5-.6 3.5-1.8" /></svg>
);
export const IconCamera = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M4 8h3l1.5-2h7L17 8h3v12H4z" /><circle cx="12" cy="13.5" r="3.5" /></svg>
);
export const IconImage = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8.5" cy="9" r="1.6" /><path d="m21 16-5-5-8 9" /></svg>
);
export const IconFilm = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" /></svg>
);
export const IconBox = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z" /><path d="m4 7.5 8 4.5 8-4.5M12 21v-9" /></svg>
);
export const IconChip = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="6" y="6" width="12" height="12" rx="2" /><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" /></svg>
);
export const IconSliders = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M4 6h8M16 6h4M4 12h3M11 12h9M4 18h11M19 18h1" /><circle cx="14" cy="6" r="2" /><circle cx="9" cy="12" r="2" /><circle cx="17" cy="18" r="2" /></svg>
);
export const IconDownload = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M12 3v12" /><path d="m7 11 5 5 5-5" /><path d="M4 19h16" /></svg>
);
export const IconBook = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 1-2-2z" /><path d="M8 3v18M12 7h4M12 11h4" /></svg>
);
export const IconShield = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M12 3 5 6v5c0 4.5 2.9 8.3 7 10 4.1-1.7 7-5.5 7-10V6z" /><path d="m9.5 12 1.8 1.8 3.4-3.6" /></svg>
);
export const IconPlay = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M7 4.5v15l12-7.5z" /></svg>
);
export const IconStop = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
);
export const IconRefresh = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M20 11a8 8 0 0 0-14-4.5L3 9" /><path d="M3 4v5h5" /><path d="M4 13a8 8 0 0 0 14 4.5L21 15" /><path d="M21 20v-5h-5" /></svg>
);
export const IconLock = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="4.5" y="10" width="15" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></svg>
);
export const IconSpark = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" /></svg>
);
export const IconChevron = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="m9 6 6 6-6 6" /></svg>
);
export const IconLink = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7L11.5 6.8" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1.5-1.5" /></svg>
);
export const IconWifiOff = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M3 3l18 18M8.5 8.5A10 10 0 0 1 21 9M3 9a10 10 0 0 1 4-2.8M6.5 13a6 6 0 0 1 3-1.5M10 17a2 2 0 0 1 2-.6" /></svg>
);
