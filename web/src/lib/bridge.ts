/** Typed client for the local SAQR bridge (127.0.0.1:8765). */

const configured = import.meta.env.VITE_BRIDGE_URL as string | undefined;

export const BRIDGE_BASE =
  configured ??
  (typeof window !== 'undefined' && window.location.port === '8765' ? '' : 'http://127.0.0.1:8765');

const TOKEN_KEY = 'saqr.bridge.token';

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode */
  }
}

export class BridgeError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 20000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    const response = await fetch(`${BRIDGE_BASE}${path}`, { ...options, headers, signal: controller.signal });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new BridgeError(data.detail ?? `HTTP ${response.status}`, response.status);
    }
    return data as T;
  } catch (error) {
    if (error instanceof BridgeError) throw error;
    if ((error as Error).name === 'AbortError') throw new BridgeError('انتهت مهلة الاتصال بالمحرك المحلي', 408);
    throw new BridgeError('تعذّر الوصول إلى المحرك المحلي. شغّل التطبيق المكتبي أولًا.', 0);
  } finally {
    clearTimeout(timer);
  }
}

export interface Health {
  ok: boolean;
  app: string;
  version: string;
  paired_sessions: number;
  engine_ready: boolean;
}

export interface HardwarePayload {
  profile: {
    cpu: { brand: string; physical_cores: number; logical_cores: number; isa: string[]; isa_source: string; architecture: string };
    system: { os_name: string; os_release: string; ram_total_mb: number; ram_available_mb: number; disk_free_gb: number; machine: string; python: string };
    gpus: { name: string; vendor: string; vram_mb: number | null; driver: string | null; source: string }[];
    notes: string[];
  };
  decision: {
    provider: string; label: string; chain: string[]; reason: string; tier: string; manual: boolean;
    probes: { provider: string; label: string; offered: boolean; verified: boolean; reason: string; device: string | null }[];
  };
  summary: string;
}

export interface ModelRow {
  id: string;
  name: string;
  kind: string;
  filename: string;
  license_id: string;
  license_name: string;
  commercial_use: boolean;
  requires_acceptance: boolean;
  downloadable: boolean;
  installed: boolean;
  license_accepted: boolean;
  notes: string;
  source_url: string;
  size_bytes: number | null;
}

export interface FaceBox {
  bbox: number[];
  landmarks: number[][];
  score: number;
  track_id: number | null;
}

export interface FrameResult {
  image: string;
  metrics: { detect_ms: number; swap_ms: number; total_ms: number; fps: number; faces: number };
  faces: FaceBox[];
  swapped_faces: number;
  error: string | null;
}

export const bridge = {
  health: () => request<Health>('/api/health', {}, 4000),

  pair: (code: string, client = 'web') =>
    request<{ token: string; expires_in: number; scopes: string[] }>('/api/pair', {
      method: 'POST',
      body: JSON.stringify({ code, client }),
    }),

  session: () => request<{ client: string; expires_at: number; scopes: string[] }>('/api/session', {}, 5000),

  revoke: () => request<{ revoked: boolean }>('/api/session/revoke', { method: 'POST' }),

  hardware: () => request<HardwarePayload>('/api/hardware', {}, 30000),

  models: () => request<{ catalog: ModelRow[]; installed: unknown[] }>('/api/models'),

  acceptLicense: (id: string) =>
    request<{ accepted: string }>(`/api/models/${id}/accept`, { method: 'POST', body: JSON.stringify({ accepted_by: 'operator' }) }),

  engineStatus: () => request<{ loaded: boolean; status?: Record<string, unknown>; error?: string }>('/api/engine/status'),

  setSource: (image: string, name = 'source') =>
    request<{ name: string; thumbnail: string }>('/api/source', { method: 'POST', body: JSON.stringify({ image, name }) }, 45000),

  processFrame: (
    image: string,
    swap = true,
    options: { strength?: number; mouthMask?: boolean | null; keepEyes?: boolean; feather?: number; enhance?: boolean } = {},
  ) =>
    request<FrameResult>('/api/frame', {
      method: 'POST',
      body: JSON.stringify({
        image,
        swap,
        strength: options.strength ?? 1,
        mouth_mask: options.mouthMask ?? null,
        keep_eyes: options.keepEyes ?? false,
        feather: options.feather ?? 21,
        enhance: options.enhance ?? false,
      }),
    }, 45000),
};
