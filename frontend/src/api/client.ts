/**
 * HTTP client for the Fuel API.
 * Uses relative /api paths in production (IIS or Vercel rewrites).
 * Set VITE_API_BASE_URL when the API is on a different public origin.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
  /\/$/,
  "",
) ?? "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      if (response.status === 404) {
        detail = "API not found. Ensure the backend is running and API_PROXY_URL is set.";
      } else if (response.status === 502) {
        detail = "Cannot reach the API server. Check that FastAPI is running and publicly reachable.";
      }
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
