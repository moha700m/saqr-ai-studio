export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('تعذّر قراءة الملف'));
    reader.readAsDataURL(file);
  });
}

export function videoFrame(video: HTMLVideoElement, maxWidth = 1280): string | null {
  if (!video.videoWidth) return null;
  const scale = Math.min(1, maxWidth / video.videoWidth);
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.85);
}

export function stripDataUrl(dataUrl: string): string {
  return dataUrl.includes(',') ? dataUrl.split(',', 2)[1] : dataUrl;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export function relativeTime(ts: number): string {
  const diff = Math.max(0, Date.now() / 1000 - ts);
  if (diff < 60) return 'الآن';
  if (diff < 3600) return `قبل ${Math.round(diff / 60)} دقيقة`;
  return `قبل ${Math.round(diff / 3600)} ساعة`;
}

export function downloadDataUrl(dataUrl: string, filename: string) {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}
