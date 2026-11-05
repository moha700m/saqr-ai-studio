/**
 * Copy MediaPipe wasm from node_modules and fetch the face detector model.
 * Runs before `vite build`; both files are ignored by git.
 */
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'web');
const target = join(root, 'public', 'mediapipe');
mkdirSync(join(target, 'wasm'), { recursive: true });

const wasmSource = join(root, 'node_modules', '@mediapipe', 'tasks-vision', 'wasm');
if (existsSync(wasmSource)) {
  for (const file of readdirSync(wasmSource)) {
    copyFileSync(join(wasmSource, file), join(target, 'wasm', file));
  }
  console.log('mediapipe wasm copied');
} else {
  console.warn('mediapipe wasm missing: run npm install first');
}

const modelPath = join(target, 'blaze_face_short_range.tflite');
const modelUrl = 'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite';
if (!existsSync(modelPath)) {
  execFileSync('curl', ['-sL', '--max-time', '120', '-o', modelPath, modelUrl], { stdio: 'inherit' });
}
const digest = createHash('sha256').update(readFileSync(modelPath)).digest('hex');
console.log('face detector sha256:', digest);
if (digest !== 'b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f') {
  console.warn('model hash differs from the recorded one; verify the source before shipping');
}
