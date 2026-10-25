"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type ConsentPreferences = {
  analytics: boolean;
  marketing: boolean;
  version: 1;
};

type ConsentPhase = "unresolved" | "banner-visible" | "settings-open" | "saved" | "hidden";

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

const storageKey = "big-mama-consent-v1";
const consentChangeEvent = "big-mama-consent-change";
const defaultPreferences: ConsentPreferences = { analytics: false, marketing: false, version: 1 };
const dialogMotionDuration = 260;
let initialSnapshot: ConsentPreferences | null | undefined;
let lastAppliedSignature: string | null = null;

function parsePreferences(value: string | null): ConsentPreferences | null {
  if (!value) return null;

  try {
    const parsed: unknown = JSON.parse(value);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "version" in parsed &&
      "analytics" in parsed &&
      "marketing" in parsed &&
      parsed.version === 1 &&
      typeof parsed.analytics === "boolean" &&
      typeof parsed.marketing === "boolean"
    ) {
      return parsed as ConsentPreferences;
    }
  } catch {
    // Invalid storage is intentionally treated as no recorded consent.
  }

  return null;
}

function resolveInitialSnapshot(): ConsentPreferences | null {
  if (initialSnapshot !== undefined) return initialSnapshot;
  initialSnapshot = parsePreferences(window.localStorage.getItem(storageKey));
  return initialSnapshot;
}

function preferencesSignature(preferences: ConsentPreferences) {
  return `${preferences.version}:${preferences.analytics}:${preferences.marketing}`;
}

function samePreferences(left: ConsentPreferences | null, right: ConsentPreferences) {
  return left !== null && preferencesSignature(left) === preferencesSignature(right);
}

function applyGoogleConsent(preferences: ConsentPreferences) {
  const signature = preferencesSignature(preferences);
  if (signature === lastAppliedSignature) return;

  lastAppliedSignature = signature;
  window.gtag?.("consent", "update", {
    analytics_storage: preferences.analytics ? "granted" : "denied",
    ad_storage: preferences.marketing ? "granted" : "denied",
    ad_user_data: preferences.marketing ? "granted" : "denied",
    ad_personalization: preferences.marketing ? "granted" : "denied",
    functionality_storage: "denied",
    personalization_storage: preferences.marketing ? "granted" : "denied",
  });
}

export function ConsentManager() {
  const [phase, setPhase] = useState<ConsentPhase>("unresolved");
  const [draft, setDraft] = useState<ConsentPreferences>(defaultPreferences);
  const [bannerClosing, setBannerClosing] = useState(false);
  const [dialogClosing, setDialogClosing] = useState(false);
  const consentRef = useRef<ConsentPreferences | null>(null);
  const settingsDialog = useRef<HTMLDialogElement>(null);
  const settingsOpener = useRef<HTMLElement | null>(null);
  const pendingDialogPhase = useRef<ConsentPhase | null>(null);
  const closeTimer = useRef<number | null>(null);
  const saveInProgress = useRef(false);
  const initialized = useRef(false);
  const openSettingsRef = useRef<(opener: HTMLElement) => void>(() => undefined);

  const restoreSettingsOpenerFocus = () => {
    const opener = settingsOpener.current;
    settingsOpener.current = null;
    if (opener?.isConnected) {
      window.requestAnimationFrame(() => opener.focus({ preventScroll: true }));
    }
  };

  const finishDialogClose = () => {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }

    const nextPhase = pendingDialogPhase.current ?? (consentRef.current ? "hidden" : "banner-visible");
    pendingDialogPhase.current = null;
    setDialogClosing(false);
    setPhase(nextPhase);
    restoreSettingsOpenerFocus();
  };

  const requestDialogClose = (nextPhase: ConsentPhase) => {
    const dialog = settingsDialog.current;
    pendingDialogPhase.current = nextPhase;

    if (!dialog?.open) {
      finishDialogClose();
      return;
    }

    setDialogClosing(true);
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => {
      if (dialog.open) dialog.close();
    }, dialogMotionDuration);
  };

  const openSettings = useCallback((opener: HTMLElement) => {
    if (phase === "unresolved" || dialogClosing) return;
    settingsOpener.current = opener;
    setDraft(consentRef.current ?? defaultPreferences);
    setPhase("settings-open");
  }, [dialogClosing, phase]);

  const save = (nextPreferences: ConsentPreferences) => {
    if (saveInProgress.current) return;
    saveInProgress.current = true;

    const hasChanged = !samePreferences(consentRef.current, nextPreferences);
    if (hasChanged) {
      window.localStorage.setItem(storageKey, JSON.stringify(nextPreferences));
      initialSnapshot = nextPreferences;
      consentRef.current = nextPreferences;
      applyGoogleConsent(nextPreferences);
      window.dispatchEvent(new CustomEvent<ConsentPreferences>(consentChangeEvent, { detail: nextPreferences }));
    }

    setDraft(nextPreferences);
    setPhase("saved");

    if (settingsDialog.current?.open) {
      requestDialogClose("hidden");
    } else {
      setBannerClosing(true);
      window.setTimeout(() => {
        setBannerClosing(false);
        setPhase("hidden");
      }, dialogMotionDuration);
    }

    window.setTimeout(() => {
      saveInProgress.current = false;
    }, 0);
  };

  useEffect(() => {
    openSettingsRef.current = openSettings;
  }, [openSettings]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const initializationFrame = window.requestAnimationFrame(() => {
      const resolved = resolveInitialSnapshot();
      consentRef.current = resolved;
      if (resolved) {
        setDraft(resolved);
        applyGoogleConsent(resolved);
        setPhase("hidden");
      } else {
        setPhase("banner-visible");
      }
    });

    return () => window.cancelAnimationFrame(initializationFrame);
  }, []);

  useEffect(() => {
    const handleFooterSettings = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const trigger = target.closest<HTMLElement>("[data-cookie-settings]");
      if (trigger) openSettingsRef.current(trigger);
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== storageKey) return;
      const nextPreferences = parsePreferences(event.newValue);
      consentRef.current = nextPreferences;
      setDraft(nextPreferences ?? defaultPreferences);
      if (nextPreferences) {
        initialSnapshot = nextPreferences;
        applyGoogleConsent(nextPreferences);
        setPhase("hidden");
      } else {
        initialSnapshot = null;
        setPhase("banner-visible");
      }
    };

    const handleConsentChange = (event: Event) => {
      const nextPreferences = event instanceof CustomEvent ? parsePreferences(JSON.stringify(event.detail)) : null;
      if (!nextPreferences || samePreferences(consentRef.current, nextPreferences)) return;
      consentRef.current = nextPreferences;
      initialSnapshot = nextPreferences;
      setDraft(nextPreferences);
      applyGoogleConsent(nextPreferences);
      setPhase("hidden");
    };

    document.addEventListener("click", handleFooterSettings);
    window.addEventListener("storage", handleStorage);
    window.addEventListener(consentChangeEvent, handleConsentChange);

    return () => {
      document.removeEventListener("click", handleFooterSettings);
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener(consentChangeEvent, handleConsentChange);
    };
  }, []);

  useEffect(() => {
    const dialog = settingsDialog.current;
    if (phase === "settings-open" && dialog?.isConnected && !dialog.open) {
      dialog.showModal();
    }
  }, [phase]);

  useEffect(() => () => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
  }, []);

  const showBanner = phase === "banner-visible" || (phase === "saved" && bannerClosing);

  return (
    <>
      {showBanner && (
        <section className="cookie-consent" data-state={bannerClosing ? "closing" : "open"} aria-label="Cookie consent" role="region">
          <div className="cookie-consent__copy">
            <p className="cookie-consent__eyebrow">YOUR PRIVACY</p>
            <h2>Cookies, your choice.</h2>
            <p>
              We use essential technologies to run this site. Optional analytics and marketing cookies stay off unless you choose otherwise. Read our{" "}
              <a href="/cookie-policy">Cookie Policy</a> and <a href="/privacy-policy">Privacy Policy</a>.
            </p>
          </div>
          <div className="cookie-consent__actions">
            <button className="cookie-consent__button cookie-consent__button--secondary" type="button" onClick={() => save(defaultPreferences)}>
              Reject all
            </button>
            <button className="cookie-consent__button cookie-consent__button--secondary" type="button" onClick={(event) => openSettings(event.currentTarget)}>
              Settings
            </button>
            <button className="cookie-consent__button" type="button" onClick={() => save({ analytics: true, marketing: true, version: 1 })}>
              Accept all
            </button>
          </div>
        </section>
      )}

      <dialog
        className="cookie-settings"
        data-state={dialogClosing ? "closing" : "open"}
        ref={settingsDialog}
        aria-labelledby="cookie-settings-title"
        onCancel={(event) => {
          event.preventDefault();
          requestDialogClose(consentRef.current ? "hidden" : "banner-visible");
        }}
        onClose={finishDialogClose}
      >
        <form className="cookie-settings__panel" method="dialog" onSubmit={(event) => event.preventDefault()}>
          <div className="cookie-settings__header">
            <div>
              <p className="cookie-consent__eyebrow">COOKIE SETTINGS</p>
              <h2 id="cookie-settings-title">Control optional cookies</h2>
            </div>
            <button className="cookie-settings__close" type="button" aria-label="Close cookie settings" onClick={() => requestDialogClose(consentRef.current ? "hidden" : "banner-visible")}>
              ×
            </button>
          </div>
          <p className="cookie-settings__intro">Essential storage is always on because it remembers this choice and enables core website functions.</p>
          <label className="cookie-settings__option">
            <span><strong>Essential</strong><small>Required to remember your privacy choice.</small></span>
            <input type="checkbox" checked disabled aria-label="Essential cookies are always active" />
          </label>
          <label className="cookie-settings__option">
            <span><strong>Analytics</strong><small>Helps us understand site use if Google Analytics is enabled in future.</small></span>
            <input type="checkbox" checked={draft.analytics} onChange={(event) => setDraft((current) => ({ ...current, analytics: event.target.checked }))} />
          </label>
          <label className="cookie-settings__option">
            <span><strong>Marketing</strong><small>Allows advertising and personalised marketing technologies if enabled in future.</small></span>
            <input type="checkbox" checked={draft.marketing} onChange={(event) => setDraft((current) => ({ ...current, marketing: event.target.checked }))} />
          </label>
          <div className="cookie-settings__actions">
            <button className="cookie-consent__button cookie-consent__button--secondary" type="button" onClick={() => save(defaultPreferences)}>Reject all</button>
            <button className="cookie-consent__button" type="button" onClick={() => save(draft)}>Save choices</button>
          </div>
          <p className="cookie-settings__legal"><a href="/cookie-policy">Cookie Policy</a> <a href="/privacy-policy">Privacy Policy</a></p>
        </form>
      </dialog>
    </>
  );
}
