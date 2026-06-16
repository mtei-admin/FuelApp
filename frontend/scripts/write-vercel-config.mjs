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

/** @param {string} targetPath @param {string} outputDirectory */
function writeConfig(targetPath, outputDirectory) {
  const config = {
    $schema: "https://openapi.vercel.sh/vercel.json",
    framework: "vite",
    outputDirectory,
    rewrites: buildRewrites(),
  };
  fs.writeFileSync(targetPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
}

writeConfig(path.join(frontendRoot, "vercel.json"), "dist");
writeConfig(path.join(repoRoot, "vercel.json"), "frontend/dist");

if (apiProxy) {
  const rootConfig = JSON.parse(fs.readFileSync(path.join(repoRoot, "vercel.json"), "utf8"));
  rootConfig.installCommand = "cd frontend && npm install";
  rootConfig.buildCommand = "cd frontend && npm run build";
  fs.writeFileSync(
    path.join(repoRoot, "vercel.json"),
    `${JSON.stringify(rootConfig, null, 2)}\n`,
    "utf8",
  );
} else {
  fs.writeFileSync(
    path.join(repoRoot, "vercel.json"),
    `${JSON.stringify(
      {
        $schema: "https://openapi.vercel.sh/vercel.json",
        installCommand: "cd frontend && npm install",
        buildCommand: "cd frontend && npm run build",
        outputDirectory: "frontend/dist",
        framework: "vite",
        rewrites: [],
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
}

console.log(
  apiProxy
    ? `[vercel] API proxy -> ${apiProxy}/api/*`
    : "[vercel] SPA only (set API_PROXY_URL in Vercel for API proxy)",
);
