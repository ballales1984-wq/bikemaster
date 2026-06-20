import { chromium } from 'playwright'

export default async function installBrowsers() {
  try {
    await chromium.launch({ headless: true }).then(b => b.close())
  } catch {}
}
