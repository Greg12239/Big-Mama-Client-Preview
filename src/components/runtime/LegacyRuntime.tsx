"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    L?: unknown;
    __bigMamaRuntimeStarted?: boolean;
  }
}

const leafletSource = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";

export function LegacyRuntime() {
  useEffect(() => {
    let cancelled = false;

    const startRuntime = async () => {
      if (cancelled || window.__bigMamaRuntimeStarted) return;
      window.__bigMamaRuntimeStarted = true;
      // @ts-expect-error Legacy browser script intentionally has no module exports.
      await import("../../../app.js");
      // @ts-expect-error Legacy browser script intentionally has no module exports.
      await import("../../../reviews-orbit.js");
    };

    const existingScript = document.querySelector<HTMLScriptElement>(`script[src="${leafletSource}"]`);
    if (window.L) {
      void startRuntime();
    } else if (existingScript) {
      existingScript.addEventListener("load", () => void startRuntime(), { once: true });
    } else {
      const script = document.createElement("script");
      script.src = leafletSource;
      script.integrity = "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";
      script.crossOrigin = "anonymous";
      script.addEventListener("load", () => void startRuntime(), { once: true });
      document.body.append(script);
    }

    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
