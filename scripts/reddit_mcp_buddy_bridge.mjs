import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

function packageCandidates() {
  const explicit = process.env.REDDIT_MCP_BUDDY_PACKAGE_ROOT;
  const candidates = [];
  if (explicit) {
    candidates.push(explicit);
  }

  const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
  const npxRoot = path.join(localAppData, "npm-cache", "_npx");
  if (fs.existsSync(npxRoot)) {
    for (const entry of fs.readdirSync(npxRoot)) {
      candidates.push(path.join(npxRoot, entry, "node_modules", "reddit-mcp-buddy"));
    }
  }
  return candidates;
}

function findPackageRoot() {
  for (const candidate of packageCandidates()) {
    const packageJson = path.join(candidate, "package.json");
    if (!fs.existsSync(packageJson)) {
      continue;
    }
    try {
      const parsed = JSON.parse(fs.readFileSync(packageJson, "utf8"));
      if (parsed.name === "reddit-mcp-buddy") {
        return candidate;
      }
    } catch {
      // Keep scanning.
    }
  }
  throw new Error("Could not find reddit-mcp-buddy in REDDIT_MCP_BUDDY_PACKAGE_ROOT or local npx cache.");
}

function readStdinJson() {
  const raw = fs.readFileSync(0, "utf8").trim();
  if (!raw) {
    return { calls: [] };
  }
  return JSON.parse(raw);
}

async function main() {
  const packageRoot = findPackageRoot();
  const serverModule = await import(pathToFileURL(path.join(packageRoot, "dist", "mcp-server.js")));
  const { cacheManager, handlers } = await serverModule.createMCPServer();
  const request = readStdinJson();
  const results = [];

  try {
    for (const call of request.calls || []) {
      const name = call.name;
      const args = call.arguments || {};
      try {
        const response = await handlers["tools/call"]({ name, arguments: args });
        const first = response.content?.[0]?.text || "{}";
        let parsed;
        try {
          parsed = JSON.parse(first);
        } catch {
          parsed = { text: first };
        }
        results.push({ name, ok: !response.isError, result: parsed });
      } catch (error) {
        results.push({
          name,
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }
  } finally {
    cacheManager?.destroy?.();
  }

  process.stdout.write(JSON.stringify({ packageRoot, results }));
}

main().catch((error) => {
  process.stdout.write(JSON.stringify({
    error: error instanceof Error ? error.message : String(error),
  }));
  process.exitCode = 1;
});
