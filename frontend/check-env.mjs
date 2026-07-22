import { loadEnv } from 'vite';
const env = loadEnv('production', process.cwd(), '');
console.log('DEV:', env.DEV, typeof env.DEV);
console.log('NODE_ENV:', env.NODE_ENV, typeof env.NODE_ENV);
console.log('TAURI:', env.TAURI, typeof env.TAURI);
