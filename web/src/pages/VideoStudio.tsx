import { useEffect, useRef, useState } from 'react';
import { Badge, Notice, Panel, PanelHead, Slider } from '../components/ui';
import { IconDownload, IconFilm, IconPlay, IconStop } from '../components/icons';
import { downloadDataUrl } from '../lib/utils';

interface Meta {
  name: string;
  size: number;
  duration: number;
  width: number;
  height: number;
}

export default function VideoStudio() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const rafRef = useRef<number | null>(null);
  const chunks = useRef<Blob[]>([]);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [time, setTime] = useState(0);
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [clipUrl, setClipUrl] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const drawFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
  };

  const pick = async (file?: File) => {
    if (!file) return;
    setError(null);
    setClipUrl(null);
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    const video = videoRef.current;
    if (video) {
      video.src = url;
      video.load();
    }
  };

  const seekTo = (value: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = value;
    setTime(value);
  };

  const exportClip = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !meta) return;
    if (!('MediaRecorder' in window)) {
      setError('هذا المتصفح لا يدعم MediaRecorder. استخدم Chrome أو Edge، أو صدّر الإطار كصورة.');
      return;
    }
    setExporting(true);
    setProgress(0);
    setError(null);
    setClipUrl(null);
    chunks.current = [];
    try {
      const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm';
      const stream = canvas.captureStream(30);
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'video/webm' });
        setClipUrl(URL.createObjectURL(blob));
        setExporting(false);
        setProgress(1);
      };
      recorder.start(250);
      video.muted = true;
      video.currentTime = start;
      await video.play();
      const stopWatch = () => {
        if (!video || video.currentTime >= end) {
          video.pause();
          if (recorder.state !== 'inactive') recorder.stop();
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
          return;
        }
        drawFrame();
        setProgress(Math.min(1, (video.currentTime - start) / Math.max(0.1, end - start)));
        rafRef.current = requestAnimationFrame(stopWatch);
      };
      rafRef.current = requestAnimationFrame(stopWatch);
    } catch (err) {
      setError((err as Error).message);
      setExporting(false);
    }
  };

  const cancelExport = () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    videoRef.current?.pause();
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setExporting(false);
  };

  useEffect(() => () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    if (clipUrl) URL.revokeObjectURL(clipUrl);
  }, [fileUrl, clipUrl]);

  return (
    <div className="grid" style={{ gap: 18 }}>
      <Notice tone="warn">
        <div>
          <b>المتصفح ليس محركًا للفيديو.</b> هنا تقطيع وتصدير إطار/مقطع محليًا (WebM). المعالجة العصبية الكاملة للفيديو
          تتم في المحرك المكتبي عبر <code>saqr process video</code>، مع الحفاظ على الصوت وتصدير MP4.
        </div>
      </Notice>

      <div className="split">
        <Panel>
          <PanelHead title="المقطع" hint="MP4 · MOV · WebM · MKV"
            action={<Badge tone={meta ? 'ok' : ''}>{meta ? 'محمل' : 'لم يُحمّل'}</Badge>} />
          <div className="viewport" style={{ aspectRatio: '16/9' }}>
            <video ref={videoRef} playsInline muted onLoadedMetadata={() => {
              const video = videoRef.current;
              if (!video) return;
              const seconds = Number.isFinite(video.duration) ? video.duration : 0;
              setMeta({ name: 'clip', size: 0, duration: seconds, width: video.videoWidth, height: video.videoHeight });
              setEnd(Math.min(seconds, 10));
              setStart(0);
              drawFrame();
            }} onTimeUpdate={() => { setTime(videoRef.current?.currentTime ?? 0); drawFrame(); }} style={{ display: fileUrl ? 'block' : 'none' }} />
            {!fileUrl && (
              <div className="empty">
                <IconFilm />
                <div style={{ marginTop: 8 }}>اختر مقطع فيديو لبدء التقطيع</div>
                <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }} onClick={() => fileRef.current?.click()}>اختيار فيديو</button>
              </div>
            )}
            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>
          <input ref={fileRef} type="file" accept="video/*" hidden onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              void pick(file).then(() => {
                const video = videoRef.current;
                if (video) {
                  video.onloadedmetadata = () => {
                    const seconds = Number.isFinite(video.duration) ? video.duration : 0;
                    setMeta({ name: file.name, size: file.size, duration: seconds, width: video.videoWidth, height: video.videoHeight });
                    setEnd(Math.min(seconds, 10));
                    setStart(0);
                  };
                }
              });
            }
          }} />

          {meta && (
            <div style={{ marginTop: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--muted)', marginBottom: 6 }}>
                <span>{meta.name}</span>
                <span>{time.toFixed(1)}s / {meta.duration.toFixed(1)}s</span>
              </div>
              <input type="range" min={0} max={Math.max(meta.duration, 0.1)} step={0.05} value={time}
                style={{ ['--fill' as string]: `${(time / Math.max(meta.duration, 0.1)) * 100}%` }}
                onChange={(e) => seekTo(Number(e.target.value))} />
              <div className="grid grid-2" style={{ marginTop: 14 }}>
                <Slider label="بداية المقطع" value={start} min={0} max={Math.max(meta.duration, 0.2)} step={0.1} onChange={(v) => setStart(Math.min(v, end - 0.2))} format={(v) => `${v.toFixed(1)}s`} />
                <Slider label="نهاية المقطع" value={end} min={0.2} max={Math.max(meta.duration, 0.3)} step={0.1} onChange={(v) => setEnd(Math.max(v, start + 0.2))} format={(v) => `${v.toFixed(1)}s`} />
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={() => void exportClip()} disabled={exporting}>
                  {exporting ? `تصدير… ${Math.round(progress * 100)}%` : <><IconPlay /> تصدير المقطع</>}
                </button>
                {exporting && <button className="btn btn-danger btn-sm" onClick={cancelExport}><IconStop /> إلغاء</button>}
                <button className="btn btn-sm" onClick={() => {
                  const canvas = canvasRef.current;
                  if (canvas) downloadDataUrl(canvas.toDataURL('image/png'), `saqr-frame-${time.toFixed(1)}s.png`);
                }}><IconDownload /> تصدير الإطار PNG</button>
                {clipUrl && <a className="btn btn-cyan btn-sm" href={clipUrl} download="saqr-clip.webm"><IconDownload /> تنزيل WebM</a>}
              </div>
            </div>
          )}
          {error && <div className="notice notice-warn" style={{ marginTop: 12 }}>{error}</div>}
        </Panel>

        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="بيانات المقطع" />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[
                ['الأبعاد', meta ? `${meta.width}×${meta.height}` : '—'],
                ['المدة', meta ? `${meta.duration.toFixed(2)}s` : '—'],
                ['الحجم', meta ? `${(meta.size / 1024 / 1024).toFixed(1)} MB` : '—'],
                ['الناتج', 'WebM (بدون صوت)'],
              ].map(([label, value]) => (
                <div className="stat" key={label}>
                  <div className="label">{label}</div>
                  <div className="value" style={{ fontSize: 17 }}>{value}</div>
                </div>
              ))}
            </div>
            <p style={{ color: 'var(--muted-2)', fontSize: 11.5, marginBottom: 0 }}>
              التصدير في المتصفح يعيد ترميز الإطارات فقط. لمعالجة كاملة مع الصوت، استخدم المحرك المكتبي.
            </p>
          </Panel>

          <Panel>
            <PanelHead title="المعالجة الكاملة" hint="سطر أوامر واحد" />
            <pre className="code">{`saqr process video input.mp4 output.mp4 --source face.jpg`}</pre>
            <div className="notice" style={{ marginTop: 12 }}>
              يستخدم FFmpeg لكتابة H.264 مع إعادة دمج الصوت الأصلي. التقدم والإلغاء متاحان في واجهة سطح المكتب.
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
