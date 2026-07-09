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
  }
}
