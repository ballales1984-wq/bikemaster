const { build } = require('vite');
const { VitePWA } = require('vite-plugin-pwa');
const fs = require('fs');
const path = require('path');

const outDir = path.resolve('test-dist');
if (fs.existsSync(outDir)) fs.rmSync(outDir, { recursive: true, force: true });

(async () => {
  try {
    await build({
      configFile: false,
      root: '.',
      plugins: [VitePWA({ registerType: 'autoUpdate' })],
      build: { outDir, emptyOutDir: true },
    });
    
    const html = fs.readFileSync(path.join(outDir, 'index.html'), 'utf-8');
    console.log('Has registerSW:', html.includes('registerSW'));
    console.log('Has sw.js:', fs.existsSync(path.join(outDir, 'sw.js')));
  } catch (e) {
    console.error('Error:', e.message);
  }
})();
