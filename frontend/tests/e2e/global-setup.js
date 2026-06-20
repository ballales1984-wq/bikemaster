async function installBrowsers() {
  try {
    const { chromium } = require('playwright')
    await chromium.launch({ headless: true })
  } catch {}
}

installBrowsers()
