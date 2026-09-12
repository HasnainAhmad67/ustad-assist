import type {
  CatalogResponse,
  TroubleshootRequest,
  TroubleshootResponse,
  VisionExtractResponse,
} from '../types/api';

const API_BASE = 'http://localhost:8001';

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

export async function getCatalog(signal?: AbortSignal): Promise<CatalogResponse> {
  return parse<CatalogResponse>(
    await fetch(`${API_BASE}/api/catalog`, { signal }),
  );
}

export async function extractVision(
  file: File,
  signal?: AbortSignal,
): Promise<VisionExtractResponse> {
  const body = new FormData();
  body.append('file', file);

  return parse<VisionExtractResponse>(
    await fetch(`${API_BASE}/api/vision/extract`, {
      method: 'POST',
      body,
      signal,
    }),
  );
}

export async function troubleshoot(
  request: TroubleshootRequest,
  signal?: AbortSignal,
): Promise<TroubleshootResponse> {
  return parse<TroubleshootResponse>(
    await fetch(`${API_BASE}/api/troubleshoot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    }),
  );
}
