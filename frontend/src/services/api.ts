import type {
  CatalogResponse,
  TroubleshootRequest,
  TroubleshootResponse,
  VisionExtractResponse,
} from '../types/api';

// Prefer an explicit deployment URL when provided. Otherwise use same-origin
// requests so Vite's /api proxy handles local development without hardcoding
// localhost into the browser bundle.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Preserve the transport-level message when the body is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await parse<T>(await fetch(`${API_BASE}${path}`, init));
  } catch (cause) {
    if (cause instanceof TypeError) {
      throw new Error(
        'Cannot connect to the Ustad Assist backend. Start FastAPI on port 8001 or set VITE_API_BASE_URL.',
      );
    }
    throw cause;
  }
}

export async function getCatalog(signal?: AbortSignal): Promise<CatalogResponse> {
  return request<CatalogResponse>('/api/catalog', { signal });
}

export async function extractVision(
  file: File,
  signal?: AbortSignal,
): Promise<VisionExtractResponse> {
  const body = new FormData();
  body.append('file', file);

  return request<VisionExtractResponse>('/api/vision/extract', {
    method: 'POST',
    body,
    signal,
  });
}

export async function troubleshoot(
  requestBody: TroubleshootRequest,
  signal?: AbortSignal,
): Promise<TroubleshootResponse> {
  return request<TroubleshootResponse>('/api/troubleshoot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
    signal,
  });
}
