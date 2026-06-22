import { chromium } from 'playwright'

export default async function installBrowsers() {
  const browsers = ['chromium', 'firefox']
  for (const name of browsers) {
    try {
      const product = name === 'chromium' ? 'chromium' : 'firefox'
      const { chromium: ch, firefox } = await import('playwright')
      const browser = name === 'chromium' ? await ch.launch({ headless: true }) : await firefox.launch({ headless: true })
      await browser.close()
    } catch {}
  }
}
