"use client";

import { createRoot, type Root } from "react-dom/client";
import { useEffect } from "react";
import { KineticBrandmark } from "./hero/KineticBrandmark";

const HEADLINE_SETS = [
  ["Big taste.", "Big Mama", "Attitude."],
  ["Smashed fresh.", "Stacked high.", "Served loud."],
] as const;

const HEADLINE_CADENCE = 3300;

type HeadlineReelController = {
  destroy: () => void;
};

type HeadlineReelElement = HTMLHeadingElement & {
  __headlineReelController?: HeadlineReelController;
};

const REEL_TRANSITION_MS = 1000;
const REEL_LAST_ROW_DELAY_MS = 260;
const REEL_SAFETY_MS = 180;

function initializeHeadlineReel(headline: HeadlineReelElement) {
  if (headline.__headlineReelController) return;

  const lines = Array.from(headline.querySelectorAll<HTMLElement>(".headline-reel__line"));
  const drums = lines.map((line) => line.querySelector<HTMLElement>(".headline-reel__drum"));
  if (lines.length !== HEADLINE_SETS[0].length || drums.some((drum) => !drum)) return;

  const lastDrum = drums[drums.length - 1]!;
  const hero = headline.closest<HTMLElement>(".hero");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let activeIndex = 0;
  let heroIsVisible = true;
  let pageIsVisible = !document.hidden;
  let transitioning = false;
  let destroyed = false;
  let cycleTimer: number | undefined;
  let completionTimer: number | undefined;
  let scheduledAt = 0;
  let fitRaf: number | undefined;

  const clearCycle = () => {
    if (cycleTimer !== undefined) window.clearTimeout(cycleTimer);
    cycleTimer = undefined;
  };
  const clearCompletion = () => {
    if (completionTimer !== undefined) window.clearTimeout(completionTimer);
    completionTimer = undefined;
    lastDrum.removeEventListener("transitionend", onTransitionEnd);
  };
  const canRun = () => !destroyed && !reducedMotion.matches && heroIsVisible && pageIsVisible;

  // Recalculate only on resize/font readiness, never while painting frames.
  const fitHeadlineToViewport = () => {
    fitRaf = undefined;
    const isDesktop = window.matchMedia("(min-width: 901px)").matches;
    const available = headline.clientWidth * (isDesktop ? 0.94 : 0.95) - (isDesktop ? 18 : 8);
    if (available <= 0) return;
    const style = window.getComputedStyle(headline);
    const baseSize = parseFloat(style.fontSize);
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) return;
    context.font = `${style.fontStyle} ${style.fontWeight} ${baseSize}px ${style.fontFamily}`;
    const maxWidth = Math.max(...HEADLINE_SETS.flat().map((phrase) => context.measureText(phrase.toUpperCase()).width));
    const targetFontSize = Math.min(baseSize, (baseSize * available / Math.max(maxWidth, 1)) * 0.975);
    lines.forEach((line) => { line.style.fontSize = `${targetFontSize.toFixed(2)}px`; });
  };
  const requestFit = () => {
    if (fitRaf !== undefined) return;
    fitRaf = window.requestAnimationFrame(fitHeadlineToViewport);
  };

  const schedule = (at: number) => {
    clearCycle();
    if (!canRun() || transitioning) return;
    scheduledAt = at;
    cycleTimer = window.setTimeout(() => {
      cycleTimer = undefined;
      if (canRun() && !transitioning) startTransition();
    }, Math.max(0, at - performance.now()));
  };

  const finishTransition = () => {
    if (!transitioning) return;
    clearCompletion();
    transitioning = false;
    activeIndex = (activeIndex + 1) % HEADLINE_SETS.length;
    headline.classList.remove("is-transitioning");
    if (canRun()) {
      const now = performance.now();
      schedule(Math.max(scheduledAt, now + 500));
    }
  };

  function onTransitionEnd(event: TransitionEvent) {
    if (event.target === lastDrum && event.propertyName === "transform") finishTransition();
  }

  const startTransition = () => {
    if (!canRun() || transitioning) return;
    transitioning = true;
    headline.classList.add("is-transitioning");
    const nextIndex = (activeIndex + 1) % HEADLINE_SETS.length;
    lastDrum.addEventListener("transitionend", onTransitionEnd);
    headline.dataset.headlinePhase = nextIndex === 0 ? "base" : "alternate";
    scheduledAt = performance.now() + HEADLINE_CADENCE;
    completionTimer = window.setTimeout(finishTransition, REEL_TRANSITION_MS + REEL_LAST_ROW_DELAY_MS + REEL_SAFETY_MS);
  };

  const fastForwardIfActive = () => {
    if (!transitioning) return;
    headline.classList.add("reel-instant");
    // Allow the destination transform to settle without a visible return sweep.
    void headline.offsetWidth;
    finishTransition();
    window.requestAnimationFrame(() => headline.classList.remove("reel-instant"));
  };

  const handleVisibility = () => {
    pageIsVisible = !document.hidden;
    if (!pageIsVisible) {
      clearCycle();
      fastForwardIfActive();
    } else if (canRun() && !transitioning) {
      schedule(performance.now() + HEADLINE_CADENCE);
    }
  };

  const handleMotionPreference = () => {
    if (reducedMotion.matches) {
      clearCycle();
      fastForwardIfActive();
    } else if (canRun() && !transitioning) {
      schedule(performance.now() + HEADLINE_CADENCE);
    }
  };

  const observer = hero && "IntersectionObserver" in window
    ? new IntersectionObserver((entries) => {
        heroIsVisible = entries[0]?.isIntersecting ?? true;
        if (!heroIsVisible) clearCycle();
        else if (canRun() && !transitioning) schedule(performance.now() + HEADLINE_CADENCE);
      })
    : undefined;
  if (hero) observer?.observe(hero);

  const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(requestFit) : undefined;
  resizeObserver?.observe(headline);
  window.addEventListener("resize", requestFit);
  document.fonts?.ready.then(() => { if (!destroyed) requestFit(); });
  requestFit();

  document.addEventListener("visibilitychange", handleVisibility);
  reducedMotion.addEventListener("change", handleMotionPreference);
  headline.dataset.headlinePhase = "base";
  if (canRun()) schedule(performance.now() + HEADLINE_CADENCE);

  const controller: HeadlineReelController = {
    destroy: () => {
      destroyed = true;
      clearCycle();
      clearCompletion();
      if (fitRaf !== undefined) window.cancelAnimationFrame(fitRaf);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", requestFit);
      observer?.disconnect();
      document.removeEventListener("visibilitychange", handleVisibility);
      reducedMotion.removeEventListener("change", handleMotionPreference);
      headline.classList.remove("is-transitioning");
      transitioning = false;
      if (headline.__headlineReelController === controller) delete headline.__headlineReelController;
    },
  };
  headline.__headlineReelController = controller;
  return controller;
}

export function HeroMotion() {
  useEffect(() => {
    const hero = document.querySelector<HTMLElement>(".hero");
    const visual = hero?.querySelector<HTMLElement>(".hero__visual");
    if (!hero || !visual) return;

    let root: Root | undefined;

    visual.replaceChildren();
    root = createRoot(visual);
    root.render(<KineticBrandmark heroElement={hero} />);

    return () => root?.unmount();
  }, []);

  useEffect(() => {
    const headline = document.querySelector<HeadlineReelElement>("[data-headline-reel]");
    const controller = headline ? initializeHeadlineReel(headline) : undefined;
    return () => controller?.destroy();
  }, []);

  return null;
}
