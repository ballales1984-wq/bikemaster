import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

try {
  const config = (await import(`file://${resolve(__dirname, "vite.config.js")}`)).default;
  console.log("plugins count:", config.plugins.length);
  const pwaPlugin = config.plugins.find((p) => p && p.name === "vite-plugin-pwa");
  console.log("pwa plugin present:", !!pwaPlugin);
} catch (e) {
  console.log("error:", e.message);
}
