import { build } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';
import fs from 'fs';
import path from 'path';

const outDir = path.resolve('test-dist');
if (fs.existsSync(outDir)) fs.rmSync(outDir, { recursive: true, force: true });

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
