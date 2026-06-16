/**
 * Optional: inject API proxy rewrites into vercel.json when API_PROXY_URL is set.
 * SPA routing is handled automatically by Vercel for Vite projects.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.join(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const apiProxy = (process.env.API_PROXY_URL ?? "").replace(/\/$/, "");

/** @returns {object[]} */
function buildRewrites() {
  if (!apiProxy) {
    return [];
  }
  return [
    {
      source: "/api/:path*",
      destination: `${apiProxy}/api/:path*`,
    },
  ];
}

/** @param {string} targetPath @param {string} outputDirectory @param {boolean} isRepoRoot */
function writeConfig(targetPath, outputDirectory, isRepoRoot = false) {
  const rewrites = buildRewrites();
  const config = {
    $schema: "https://openapi.vercel.sh/vercel.json",
    framework: "vite",
    outputDirectory,
    rewrites,
  };
  if (isRepoRoot) {
    config.installCommand = "cd frontend && npm install";
    config.buildCommand = "cd frontend && npm run build:vercel";
  } else {
    config.buildCommand = "npm run build:vercel";
  }
  fs.writeFileSync(targetPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
}

writeConfig(path.join(frontendRoot, "vercel.json"), "dist", false);
writeConfig(path.join(repoRoot, "vercel.json"), "frontend/dist", true);

console.log(
  apiProxy
    ? `[vercel] API proxy -> ${apiProxy}/api/*`
    : "[vercel] SPA only (set API_PROXY_URL in Vercel for API proxy)",
);
