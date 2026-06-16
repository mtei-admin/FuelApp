/**
 * Vercel Edge proxy: forwards /api/* to API_PROXY_URL at runtime.
 * Reads env var on each request (unlike vercel.json rewrites baked at deploy).
 */
export const config = {
  runtime: "edge",
};

/** @param {Request} request */
export default async function handler(request) {
  const base = process.env.API_PROXY_URL?.replace(/\/$/, "");
  if (!base) {
    return new Response(
      JSON.stringify({ detail: "API_PROXY_URL is not configured on Vercel" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  const incoming = new URL(request.url);
  const target = `${base}${incoming.pathname}${incoming.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body:
        request.method === "GET" || request.method === "HEAD"
          ? undefined
          : request.body,
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: upstream.headers,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Upstream API unreachable";
    return new Response(
      JSON.stringify({
        detail: `Cannot reach API at ${base}. ${message}`,
      }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }
}
