import { useCallback, useEffect, useRef, useState } from 'react';
import { Badge, Notice, Panel, PanelHead, Stat } from '../components/ui';
import { IconCamera, IconPlay, IconRefresh, IconStop } from '../components/icons';
import { bridge } from '../lib/bridge';
import { useBridge } from '../lib/bridge-context';
import { loadFaceDetector, type BrowserFace } from '../lib/faceDetector';
import { stripDataUrl, videoFrame } from '../lib/utils';

interface Metrics {
  detect_ms: number;
  swap_ms: number;
  total_ms: number;
  fps: number;
  faces: number;
}

export default function Live() {
  const { paired } = useBridge();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const detectorRef = useRef<Awaited<ReturnType<typeof loadFaceDetector>> | null>(null);
  const lastVideoTime = useRef(-1);
  const frames = useRef<number[]>([]);
  const streamingBusy = useRef(false);
  const streamTimer = useRef<number | null>(null);

  const [running, setRunning] = useState(false);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState('');
  const [detecting, setDetecting] = useState(false);
  const [detectorError, setDetectorError] = useState<string | null>(null);
  const [faces, setFaces] = useState<BrowserFace[]>([]);
  const [fps, setFps] = useState(0);
  const [snapshot, setSnapshot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamToEngine, setStreamToEngine] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [engineBusy, setEngineBusy] = useState(false);

  const draw = useCallback((detections: BrowserFace[]) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = Math.max(2, canvas.width / 640);
    ctx.strokeStyle = '#8b5cf6';
    ctx.fillStyle = 'rgba(139,92,246,.14)';
    detections.forEach((face, index) => {
      const box = face.boundingBox ?? { originX: face.x, originY: face.y, width: face.width, height: face.height };
      ctx.beginPath();
      ctx.roundRect(box.originX, box.originY, box.width, box.height, 10);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#e9d5ff';
      ctx.font = `${Math.max(12, canvas.width / 55)}px Tajawal, sans-serif`;
      ctx.fillText(`وجه ${index + 1} · ${(face.score * 100).toFixed(0)}%`, box.originX + 6, Math.max(16, box.originY - 8));
      ctx.fillStyle = 'rgba(139,92,246,.14)';
    });
  }, []);

  const loop = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.readyState >= 2 && video.currentTime !== lastVideoTime.current) {
      lastVideoTime.current = video.currentTime;
      const now = performance.now();
      frames.current.push(now);
      while (frames.current.length && now - frames.current[0] > 1000) frames.current.shift();
      setFps(frames.current.length);
      const detector = detectorRef.current;
      if (detector) {
        try {
          const detections = detector.detectForVideo(video, now).detections as BrowserFace[];
          setFaces(detections);
          draw(detections);
        } catch {
          /* one bad frame must not kill the preview */
        }
      }
    }
    rafRef.current = requestAnimationFrame(loop);
  }, [draw]);

  const stop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (streamTimer.current) window.clearTimeout(streamTimer.current);
    streamTimer.current = null;
    setRunning(false);
    setFaces([]);
    setFps(0);
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx && canvasRef.current) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      const constraints: MediaStreamConstraints = {
        video: deviceId ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } } : { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      const list = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput');
      setDevices(list);
      if (!deviceId && list[0]) setDeviceId(list[0].deviceId);
      setRunning(true);
      rafRef.current = requestAnimationFrame(loop);
    } catch (err) {
      const name = (err as Error).name;
      setError(name === 'NotAllowedError' ? 'رفض المتصفح إذن الكاميرا. افتح إعدادات الموقع واسمح بالكاميرا، وتأكد أن الصفحة تعمل عبر HTTPS أو localhost.' : name === 'NotFoundError' ? 'لا توجد كاميرا متاحة.' : 'تعذّر تشغيل الكاميرا.');
    }
  }, [deviceId, loop]);

  const enableDetector = async () => {
    setDetectorError(null);
    try {
      detectorRef.current = await loadFaceDetector();
      setDetecting(true);
    } catch {
      setDetectorError('تعذّر تحميل نموذج كشف الوجوه في المتصفح (wasm/model). الكاميرا تعمل، لكن بدون صناديق كشف.');
    }
  };

  const takeSnapshot = () => {
    if (!videoRef.current) return;
    const frame = videoFrame(videoRef.current);
    setSnapshot(frame);
    setResult(null);
  };

  useEffect(() => () => stop(), [stop]);

  useEffect(() => {
    if (!streamToEngine || !paired || !running) {
      if (streamTimer.current) window.clearTimeout(streamTimer.current);
      streamTimer.current = null;
      return;
    }
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      if (!streamingBusy.current && videoRef.current) {
        const frame = videoFrame(videoRef.current, 960);
        if (frame) {
          streamingBusy.current = true;
          setEngineBusy(true);
          try {
            const response = await bridge.processFrame(stripDataUrl(frame), true, 1);
            if (!cancelled) {
              setResult(`data:image/jpeg;base64,${response.image}`);
              setMetrics(response.metrics);
              setError(null);
            }
          } catch (err) {
            if (!cancelled) setError((err as Error).message);
          } finally {
            streamingBusy.current = false;
            setEngineBusy(false);
          }
        }
      }
      if (!cancelled) streamTimer.current = window.setTimeout(tick, 120);
    };
    void tick();
    return () => {
      cancelled = true;
      if (streamTimer.current) window.clearTimeout(streamTimer.current);
    };
  }, [streamToEngine, paired, running]);

  return (
    <div className="grid" style={{ gap: 18 }}>
      <Notice tone="violet">
        <div>
          <b>ما تراه هنا حقيقي:</b> كشف الوجوه يعمل داخل المتصفح (MediaPipe). تبديل الوجه العصبي لا يعمل في المتصفح —
          إنه يتطلب المحرك المكتبي عبر الجسر المحلي، ولا يُرسل أي إطار إلى الإنترنت.
        </div>
      </Notice>

      <div className="split">
        <Panel pad={false}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <Badge tone={running ? 'ok' : ''}>{running ? 'كاميرا تعمل' : 'متوقفة'}</Badge>
            <select className="select" style={{ width: 'auto', minWidth: 170 }} value={deviceId} onChange={(e) => setDeviceId(e.target.value)} disabled={running}>
              <option value="">الكاميرا الافتراضية</option>
              {devices.map((device, index) => (
                <option key={device.deviceId || index} value={device.deviceId}>{device.label || `كاميرا ${index + 1}`}</option>
              ))}
            </select>
            <span className="spacer" />
            {!running ? (
              <button className="btn btn-primary btn-sm" onClick={() => void start()}><IconPlay /> تشغيل</button>
            ) : (
              <>
                <button className="btn btn-sm" onClick={takeSnapshot}><IconCamera /> لقطة</button>
                <button className="btn btn-danger btn-sm" onClick={stop}><IconStop /> إيقاف</button>
              </>
            )}
          </div>
          <div className="viewport" style={{ aspectRatio: '16/9', borderRadius: 0, border: 'none' }}>
            <video ref={videoRef} playsInline muted style={{ display: running ? 'block' : 'none', transform: 'scaleX(-1)' }} />
            <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'scaleX(-1)', pointerEvents: 'none' }} />
            {!running && (
              <div className="empty">
                <IconCamera />
                <div style={{ marginTop: 10 }}>اضغط «تشغيل» لطلب إذن الكاميرا</div>
                <small style={{ color: 'var(--muted-2)' }}>يعمل على Safari iPhone وChrome وEdge</small>
              </div>
            )}
            <div className="metrics-strip">
              <span>{fps} FPS معاينة</span>
              <span>{faces.length} وجه</span>
              <span>{engineBusy ? 'المحرك يعالج…' : metrics ? `${metrics.total_ms.toFixed(0)} ms` : 'بدون محرك'}</span>
              <span>{detecting ? 'كشف مفعّل' : 'كشف متوقف'}</span>
            </div>
          </div>
          <div style={{ padding: 14, display: 'flex', gap: 8, flexWrap: 'wrap', borderTop: '1px solid var(--line)' }}>
            <button className="btn btn-sm" onClick={() => void enableDetector()} disabled={detecting}>
              {detecting ? 'كشف الوجوه مفعّل' : 'تفعيل كشف الوجوه في المتصفح'}
            </button>
            <label className="btn btn-sm" style={{ cursor: 'pointer' }}>
              <input type="checkbox" checked={streamToEngine} disabled={!paired} onChange={(e) => setStreamToEngine(e.target.checked)} style={{ accentColor: '#8b5cf6' }} />
              بث الإطارات إلى المحرك
            </label>
            {!paired && <span className="badge badge-warn"><span className="dot" />يتطلب اقترانًا</span>}
            <button className="btn btn-ghost btn-sm" onClick={() => { setResult(null); setMetrics(null); setError(null); }}><IconRefresh /> مسح المخرج</button>
          </div>
          {detectorError && <div style={{ padding: '0 14px 14px' }}><Notice tone="warn">{detectorError}</Notice></div>}
          {error && <div style={{ padding: '0 14px 14px' }}><Notice tone="warn">{error}</Notice></div>}
        </Panel>

        <div className="grid" style={{ gap: 16 }}>
          <Panel>
            <PanelHead title="مخرج المحرك" hint={paired ? 'آخر إطار عاد من سطح المكتب' : 'غير متصل'} action={<Badge tone={result ? 'ok' : ''}>{result ? 'مباشر' : 'بانتظار'}</Badge>} />
            <div className="viewport" style={{ aspectRatio: '4/3' }}>
              {result ? <img src={result} alt="مخرج المحرك" /> : (
                <div className="empty">
                  <div>شغّل الكاميرا وفعّل «بث الإطارات إلى المحرك»</div>
                  <small style={{ color: 'var(--muted-2)', display: 'block', marginTop: 6 }}>يتطلب التطبيق المكتبي مقترنًا</small>
                </div>
              )}
              {metrics && (
                <div className="metrics-strip">
                  <span>{metrics.fps.toFixed(1)} FPS</span>
                  <span>كشف {metrics.detect_ms.toFixed(0)} ms</span>
                  <span>تبديل {metrics.swap_ms.toFixed(0)} ms</span>
                </div>
              )}
            </div>
          </Panel>

          <Panel>
            <PanelHead title="لقطة" hint="إطار واحد من المعاينة" />
            {snapshot ? <img src={snapshot} alt="لقطة" style={{ borderRadius: 12, width: '100%' }} /> : <div className="notice">التقط إطارًا من الكاميرا لعرضه هنا.</div>}
          </Panel>

          <div className="grid grid-2">
            <Stat label="دقة المعاينة" value={videoRef.current?.videoWidth ? `${videoRef.current.videoWidth}×${videoRef.current.videoHeight}` : '—'} />
            <Stat label="أجهزة الكاميرا" value={devices.length || '—'} foot="بعد منح الإذن" />
          </div>
        </div>
      </div>
    </div>
  );
}
