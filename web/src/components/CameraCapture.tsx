import { useEffect, useRef, useState } from 'react';

export default function CameraCapture({ onCapture, buttonLabel = 'التقاط إطار' }: {
  onCapture: (dataUrl: string) => void;
  buttonLabel?: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stop = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setActive(false);
  };

  useEffect(() => () => stop(), []);

  const start = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setActive(true);
    } catch (err) {
      setError((err as Error).name === 'NotAllowedError' ? 'تم رفض إذن الكاميرا من المتصفح.' : 'تعذّر فتح الكاميرا.');
    }
  };

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    onCapture(canvas.toDataURL('image/jpeg', 0.92));
    stop();
  };

  return (
    <div>
      <div className="viewport" style={{ aspectRatio: '4/3' }}>
        <video ref={videoRef} muted playsInline style={{ display: active ? 'block' : 'none' }} />
        {!active && (
          <div className="empty">
            <div style={{ marginBottom: 10 }}>الكاميرا متوقفة</div>
            <button className="btn btn-primary btn-sm" onClick={() => void start()}>تشغيل الكاميرا</button>
          </div>
        )}
        {active && (
          <div className="overlay-tag">
            <span className="badge badge-ok"><span className="dot" />مباشر</span>
          </div>
        )}
      </div>
      {error && <div className="notice notice-warn" style={{ marginTop: 10 }}>{error}</div>}
      {active && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <button className="btn btn-primary btn-sm" onClick={capture}>{buttonLabel}</button>
          <button className="btn btn-sm" onClick={stop}>إيقاف</button>
        </div>
      )}
      <p style={{ color: 'var(--muted-2)', fontSize: 11.5, margin: '10px 0 0' }}>
        الفيديو يبقى في ذاكرة المتصفح. يُرسل إطار واحد فقط إلى المحرك عند الضغط على «التقاط» أو عند تفعيل البث.
      </p>
    </div>
  );
}
