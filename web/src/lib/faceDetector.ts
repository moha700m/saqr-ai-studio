/**
 * In-browser face detection via MediaPipe Tasks Vision (Apache-2.0).
 * Model + wasm are served from /mediapipe; if they cannot load we report it
 * instead of drawing fake boxes.
 */
export interface BrowserFace {
  x: number;
  y: number;
  width: number;
  height: number;
  score: number;
  keypoints: { x: number; y: number }[];
  boundingBox?: { originX: number; originY: number; width: number; height: number };
}

type Detector = {
  detectForVideo: (video: HTMLVideoElement, ts: number) => { detections: BrowserFace[] };
};

let detectorPromise: Promise<Detector> | null = null;

export async function loadFaceDetector(): Promise<Detector> {
  if (!detectorPromise) {
    detectorPromise = (async () => {
      const vision = await import('@mediapipe/tasks-vision');
      const fileset = await vision.FilesetResolver.forVisionTasks('/mediapipe/wasm');
      const detector = await vision.FaceDetector.createFromOptions(fileset, {
        baseOptions: {
          modelAssetPath: '/mediapipe/blaze_face_short_range.tflite',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        minDetectionConfidence: 0.5,
      });
      return detector as unknown as Detector;
    })().catch((error) => {
      detectorPromise = null;
      throw error;
    });
  }
  return detectorPromise;
}
