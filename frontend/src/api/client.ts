/**
 * HTTP client for the Fuel API.
 * IIS/LAN: relative /api paths (same origin).
 * Vercel + CrazyDomains tunnel: calls https://fuelapp-api.mteinc.net directly.
 */

const PRODUCTION_API_BASE = "https://fuelapp-api.mteinc.net";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ??
  (import.meta.env.PROD ? PRODUCTION_API_BASE : "");

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
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
