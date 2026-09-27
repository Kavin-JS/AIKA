/**
 * Minimal API client for v0.1.
 *
 * The backend base URL is read from an environment variable so it can
 * differ between local dev (localhost) and Docker Compose (service name
 * `backend`) without any code change. As feature routers are added to
 * the backend, add typed functions here rather than calling `fetch`
 * directly from components.
 */

const API_BASE_URL = process.env.BACKEND_API_URL ?? "http://localhost:8000";

export interface ReadinessStatus {
  status: string;
  database?: string;
}

export async function getBackendReadiness(): Promise<{
  ok: boolean;
  data: ReadinessStatus | null;
  error: string | null;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/ready`, {
      cache: "no-store",
    });
    const data = (await res.json()) as ReadinessStatus;
    return { ok: res.ok, data, error: null };
  } catch (err) {
    return {
      ok: false,
      data: null,
      error: err instanceof Error ? err.message : "Unknown error",
    };
  }
}
