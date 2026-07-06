import { spawn } from 'node:child_process'
import { rm, stat } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

const MAX_ATTEMPTS = 3
const RETRY_DELAY_MS = 1500

async function clearDist() {
  const dist = resolve(root, 'dist')
  try {
    await stat(dist)
  } catch {
    return
  }
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      await rm(dist, { recursive: true, force: true, maxRetries: 3, retryDelay: 500 })
      return
    } catch (err) {
      if (attempt === MAX_ATTEMPTS) throw err
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS))
    }
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
  await clearDist()
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const { code, signal } = await runViteBuild()
    if (code === 0 && !signal) {
      process.exit(0)
    }
    const locked = code !== 0
    if (attempt < MAX_ATTEMPTS && locked) {
      console.warn(
        `[safe-build] Build failed (attempt ${attempt}/${MAX_ATTEMPTS}). ` +
          `If this is an EPERM/lock on dist/registerSW.js (Windows Defender), retrying…`
      )
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS))
      await clearDist()
      continue
    }
    process.exit(code ?? 1)
  }
}

main().catch((err) => {
  console.error('[safe-build]', err)
  process.exit(1)
})
