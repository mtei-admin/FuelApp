/**
 * Writes vercel.json rewrites before build so API_PROXY_URL can be set in Vercel env.
 * When API_PROXY_URL is set, /api/* is proxied same-origin (session cookies work).
 * When unset, only SPA fallback is configured; set VITE_API_BASE_URL instead.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const apiProxy = (process.env.API_PROXY_URL ?? "").replace(/\/$/, "");

const rewrites = [];

if (apiProxy) {
  rewrites.push({
    source: "/api/:path*",
    destination: `${apiProxy}/api/:path*`,
  });
}

rewrites.push({
  source: "/((?!assets/).*)",
  destination: "/index.html",
});

const config = {
  $schema: "https://openapi.vercel.sh/vercel.json",
  framework: "vite",
  buildCommand: "node scripts/write-vercel-config.mjs && vite build",
  outputDirectory: "dist",
  rewrites,
};

fs.writeFileSync(
  path.join(root, "vercel.json"),
  `${JSON.stringify(config, null, 2)}\n`,
  "utf8",
);

console.log(
  apiProxy
    ? `[vercel] API proxy -> ${apiProxy}/api/*`
    : "[vercel] No API_PROXY_URL; configure VITE_API_BASE_URL or add API_PROXY_URL in Vercel",
);
