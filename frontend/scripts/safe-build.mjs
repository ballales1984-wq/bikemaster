import { spawn } from "node:child_process";
import { rm, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const MAX_ATTEMPTS = 3;
const RETRY_DELAY_MS = 3000;
const ATTEMPT_TIMEOUT_MS = 150000;

// Best-effort: Defender on Windows may keep dist/ locked for a while.
// Never throw here — vite's --emptyOutDir will retry the removal itself.
async function clearDist() {
  const dist = resolve(root, "dist");
  try {
    await stat(dist);
  } catch {
    return;
  }
  try {
    await rm(dist, {
      recursive: true,
      force: true,
      maxRetries: 5,
      retryDelay: 500,
    });
  } catch {
    /* ignore — will retry on next loop or let vite handle it */
  }
}

function runViteBuild() {
  return new Promise((resolvePromise) => {
    const child = spawn(
      process.execPath,
      [
        resolve(root, "node_modules/vite/bin/vite.js"),
        "build",
        "--emptyOutDir",
      ],
      { cwd: root, stdio: "inherit", windowsHide: true },
    );
    let settled = false;
    const finalize = (result) => {
      if (settled) return;
      settled = true;
      resolvePromise(result);
    };
    child.on("exit", (code, signal) =>
      finalize({ code, signal, timedOut: false }),
    );
    child.on("error", () =>
      finalize({ code: 1, signal: null, timedOut: false }),
    );

    // If vite hangs on a persistent lock instead of failing, kill it and retry.
    const killTimer = setTimeout(() => {
      try {
        child.kill("SIGKILL");
      } catch {
        /* ignore */
      }
      finalize({ code: null, signal: "SIGKILL", timedOut: true });
    }, ATTEMPT_TIMEOUT_MS);
    child.on("exit", () => clearTimeout(killTimer));
  });
}

async function main() {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    await clearDist();
    const { code, signal, timedOut } = await runViteBuild();
    if (code === 0 && !signal) {
      process.exit(0);
    }
    if (attempt < MAX_ATTEMPTS) {
      console.warn(
        `[safe-build] Build attempt ${attempt}/${MAX_ATTEMPTS} ` +
          `${timedOut ? "timed out" : "failed"} ` +
          `(EPERM/lock on dist is common with Windows Defender). Retrying in ${RETRY_DELAY_MS}ms…`,
      );
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      continue;
    }
    console.error("[safe-build] Build failed after all retries.");
    process.exit(typeof code === "number" ? code : 1);
  }
}

main().catch((err) => {
  console.error("[safe-build]", err);
  process.exit(1);
});
