import { spawn } from 'node:child_process'
import { rm, stat } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

const MAX_ATTEMPTS = 5
const RETRY_DELAY_MS = 3000

// Best-effort: Defender on Windows may keep dist/ locked for a while.
// Never throw here — vite's --emptyOutDir will retry the removal itself.
async function clearDist() {
  const dist = resolve(root, 'dist')
  try {
    await stat(dist)
  } catch {
    return
  }
  try {
    await rm(dist, { recursive: true, force: true, maxRetries: 5, retryDelay: 500 })
  } catch {
    /* ignore — will retry on next loop or let vite handle it */
  }
}

function runViteBuild() {
  return new Promise((resolvePromise) => {
    const child = spawn(
      process.execPath,
      [resolve(root, 'node_modules/vite/bin/vite.js'), 'build', '--emptyOutDir'],
      { cwd: root, stdio: 'inherit', windowsHide: true }
    )
    child.on('exit', (code, signal) => resolvePromise({ code, signal }))
  })
}

async function main() {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    await clearDist()
    const { code, signal } = await runViteBuild()
    if (code === 0 && !signal) {
      process.exit(0)
    }
    if (attempt < MAX_ATTEMPTS) {
      console.warn(
        `[safe-build] Build attempt ${attempt}/${MAX_ATTEMPTS} failed ` +
          `(EPERM/lock on dist is common with Windows Defender). Retrying in ${RETRY_DELAY_MS}ms…`
      )
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS))
      continue
    }
    console.error('[safe-build] Build failed after all retries.')
    process.exit(code ?? 1)
  }
}

main().catch((err) => {
  console.error('[safe-build]', err)
  process.exit(1)
})
