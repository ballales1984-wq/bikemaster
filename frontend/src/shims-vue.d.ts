/**
 * Dichiarazioni TypeScript per Vue e API globali.
 *
 * Abilita l'import di componenti .vue e definisce le interfacce
 * per Window.BikeTracking, toast e google.
 */

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

declare global {
  interface Window {
    BikeTracking: {
      startTracking: () => Promise<void>;
      stopTracking: () => Promise<{ gpxPath: string | null }>;
      pauseTracking: () => Promise<void>;
      resumeTracking: () => Promise<void>;
      checkPermissions: () => Promise<{ granted: boolean }>;
    };
    __toast?: {
      add: (msg: string, type?: string, ms?: number) => void;
      remove: (id: number) => void;
    };
    google?: any;
  }
}

export {};
