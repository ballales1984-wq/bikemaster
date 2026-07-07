// Build wrapper that retries `vite build` to survive transient EPERM errors
// caused by Windows Defender / Antivirus locking freshly-written files
// (e.g. dist/registerSW.js or source files during transformation).
// See AGENTS.md -> "Build su Windows (problema EPERM)".

import { spawnSync } from 'node:child_process'
import { rmSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const MAX_ATTEMPTS = 3
const RETRY_DELAY_MS = 4000

const buildArgs = process.argv.slice(2)
const outDirArg = buildArgs.find((a) => a.startsWith('--outDir'))
const outDir = outDirArg ? outDirArg.split('=')[1] : 'dist'
const outDirPath = resolve(process.cwd(), outDir)

function tryBuild() {
  const result = spawnSync('vite', ['build', ...buildArgs], {
    stdio: 'inherit',
    shell: true,
  })
  return result
}

let attempt = 0
while (attempt < MAX_ATTEMPTS) {
  attempt += 1
  const result = tryBuild()
  if (result.status === 0) {
    process.exit(0)
  }
  const output = (result.stderr?.toString?.() || '') + (result.stdout?.toString?.() || '')
  const isEperm = /EPERM/i.test(output)
  if (!isEperm) {
    process.exit(result.status ?? 1)
  }
  console.warn(
    `[build] EPERM detected (attempt ${attempt}/${MAX_ATTEMPTS}). ` +
      `Possibly a Defender/Antivirus lock on ${outDirPath}. Retrying after ${RETRY_DELAY_MS}ms...`,
  )
  // Best-effort: clear the output dir so a stale locked file doesn't block the next pass.
  try {
    if (existsSync(outDirPath)) rmSync(outDirPath, { recursive: true, force: true })
  } catch {
    // ignore - the lock itself may prevent deletion; the retry may still succeed
  }
  if (attempt < MAX_ATTEMPTS) {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, RETRY_DELAY_MS)
  }
}

console.error(`[build] Build failed after ${MAX_ATTEMPTS} attempts due to persistent EPERM.`)
console.error('[build] Mitigation: exclude the frontend directory from Windows Defender, e.g.')
console.error('  Add-MpPreference -ExclusionPath "' + process.cwd() + '"')
process.exit(1)
