/**
 * HTTP client for the Fuel API.
 * IIS/LAN: relative /api paths (same origin).
 * Vercel + tunnel: set VITE_API_BASE_URL=https://fuelapp-api.mteinc.net at build time.
 */

function isPrivateLanHost(hostname: string): boolean {
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return true;
  }
  if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(hostname)) {
    return true;
  }
  if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(hostname)) {
    return true;
  }
  return /^172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}$/.test(hostname);
}

/** Hostnames where IIS (or LAN FastAPI) proxies /api on the same origin. */
const SAME_ORIGIN_API_HOSTS = new Set(["fuelapp.mteinc.net"]);

function usesSameOriginApi(hostname: string): boolean {
  return isPrivateLanHost(hostname) || SAME_ORIGIN_API_HOSTS.has(hostname);
}

/** Resolve API base URL for Vercel (cross-origin) vs LAN/IIS (same-origin /api). */
function getApiBase(): string {
  const configured = (
    import.meta.env.VITE_API_BASE_URL as string | undefined
  )?.replace(/\/$/, "");

  if (typeof window !== "undefined" && configured) {
    try {
      if (new URL(configured).origin === window.location.origin) {
        return "";
      }
    } catch {
      // Fall through to configured or defaults below.
    }
    if (usesSameOriginApi(window.location.hostname)) {
      return "";
    }
    return configured;
  }

  if (configured) {
    return configured;
  }

  // IIS/LAN default: same-origin /api. Vercel sets VITE_API_BASE_URL at build time.
  return "";
}

const API_BASE = getApiBase();

let unauthorizedHandler: (() => void) | null = null;

/** Register a callback when any API call returns 401 (session lost). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

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
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Network error contacting API";
    throw new ApiError(
      0,
      `Cannot reach API at ${API_BASE || "same origin"}. ${message}`,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as {
        detail?: string | { msg?: string }[];
      };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail) && body.detail.length > 0) {
        const first = body.detail[0];
        const msg = typeof first?.msg === "string" ? first.msg : "";
        detail = msg.replace(/^Value error,\s*/i, "") || detail;
      }
    } catch {
      if (response.status === 404) {
        detail =
          "API route not found. Redeploy Vercel with Root Directory = frontend, or check vercel.json rewrites.";
      } else if (response.status === 502) {
        detail =
          "Cannot reach API server. Check https://fuelapp-api.mteinc.net/api/health and VITE_API_BASE_URL on Vercel.";
      }
    }
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
