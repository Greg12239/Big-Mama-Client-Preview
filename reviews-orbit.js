(() => {
  const mobileQuery = window.matchMedia("(max-width: 767px)");
  const reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

  class ReviewOrbitController {
    constructor(deck) {
      this.deck = deck;
      this.activeIndex = 0;
      this.settledStep = 0;
      this.visualStep = 0;
      this.phase = "idle";
      this.animationGeneration = 0;
      this.activeAnimations = [];
      this.settleFallbackTimer = 0;
      this.settleProgressFrame = 0;
      this.currentTargetStep = null;
      this.pointerState = null;
      this.dragFrame = 0;
      this.clickSuppressionUntil = 0;
      this.detailOpacityValues = [];
      this.arrivalTimer = 0;
      this.effectiveWidth = 0;
      this.maxNaturalCardHeight = 0;
      this.cardNaturalHeights = [];
      this.cardWidth = 0;
      this.resolvedCardWidth = 0;
      this.pixelXCorrection = 0;
      this.pixelYCorrection = 0;
      this.pendingResize = false;
      this.componentVisible = true;
      this.widthFrame = 0;
      this.resizeObserver = null;
      this.intersectionObserver = null;
      this.abortController = new AbortController();
    }

    init() {
      this.collectElements();
      if (!this.validateMarkup()) return;

      this.activeIndex = Math.max(
        0,
        this.cards.findIndex((card) => card.classList.contains("is-active")),
      );
      this.settledStep = this.activeIndex;
      this.visualStep = this.settledStep;
      this.cards.forEach((card, index) => {
        card.dataset.reviewIndex = String(index);
        card.style.setProperty("--review-float-duration", `${5.6 + index * 0.31}s`);
        card.style.setProperty("--review-float-delay", `${-index * 0.67}s`);
        card.style.setProperty("--review-float-distance", `${2 + (index % 3)}px`);
      });

      this.bindEvents();
      this.handleModeChange();
      document.fonts?.ready?.then(() => this.handleWidthChange(true));
      this.deck.reviewOrbitController = this;
    }

    collectElements() {
      this.scene = this.deck.querySelector("[data-review-scene]");
      this.orbit = this.deck.querySelector("[data-review-orbit]");
      this.slots = Array.from(this.deck.querySelectorAll("[data-review-slot]"));
      this.cards = this.slots.map((slot) => slot.querySelector("[data-review-card]"));
      this.detailOpacityValues = Array(this.cards.length).fill(null);
      this.detailGroups = this.cards.map((card) => Array.from(card.querySelectorAll(
        ".review-card__meta, .review-card__rating-row, .review-card__text",
      )));
      this.status = this.deck.querySelector("[data-review-status]");
    }

    validateMarkup() {
      return this.scene
        && this.orbit
        && this.cards.length === 5
        && this.slots.length === this.cards.length
        && this.cards.every(Boolean);
    }

    getMode() {
      return reducedQuery.matches ? "reduced" : "orbit";
    }

    isMobileLayout() {
      return mobileQuery.matches;
    }

    isAnimatedMode() {
      return this.getMode() === "orbit";
    }

    normalizeIndex(index) {
      return ((index % this.cards.length) + this.cards.length) % this.cards.length;
    }

    relativeAt(index, step = this.settledStep) {
      let value = this.normalizeIndex(index - this.normalizeIndex(Math.round(step)));
      if (value > Math.floor(this.cards.length / 2)) value -= this.cards.length;
      return value;
    }

    resolveTargetStep(index, referenceStep) {
      const referenceIndex = this.normalizeIndex(Math.round(referenceStep));
      let delta = this.normalizeIndex(index - referenceIndex);
      if (delta > Math.floor(this.cards.length / 2)) delta -= this.cards.length;
      return Math.round(referenceStep) + delta;
    }

    setPhase(phase) {
      this.phase = phase;
      this.deck.dataset.reviewPhase = phase;
      this.deck.classList.toggle("is-dragging", phase === "dragging");
      this.deck.classList.toggle("is-settling", phase === "settling");
      this.syncStateAttributes();
    }

    syncStateAttributes() {
      this.deck.dataset.reviewSettledStep = String(this.settledStep);
      this.deck.dataset.reviewVisualStep = String(
        Math.round(this.visualStep * 10000) / 10000,
      );
      this.deck.dataset.reviewActiveIndex = String(this.activeIndex);
      this.deck.dataset.reviewPendingTargetStep = "";
      this.deck.dataset.reviewAnimationCount = String(this.activeAnimations.length);
    }

    handleModeChange() {
      this.cancelPointer(false);
      this.cancelAnimations(true);
      if (this.arrivalTimer) {
        window.clearTimeout(this.arrivalTimer);
        this.arrivalTimer = 0;
      }
      this.cards.forEach((card) => card.classList.remove("is-arriving"));
      this.currentTargetStep = null;
      this.setPhase("idle");
      this.deck.dataset.reviewMode = this.getMode();
      this.syncVisualStates();
      this.syncContentStates();

      if (this.getMode() === "orbit" || this.getMode() === "reduced") {
        this.handleWidthChange(true);
      }
    }

    handleWidthChange(force = false) {
      const mode = this.getMode();
      if (mode !== "orbit" && mode !== "reduced") return;
      if (this.phase !== "idle") {
        this.pendingResize = true;
        return;
      }

      const initialDeckRect = this.deck.getBoundingClientRect();
      const width = Math.round(initialDeckRect.width);
      if (!force && Math.abs(width - this.effectiveWidth) < 2) return;
      this.effectiveWidth = width;
      this.applyResolvedCardWidth(width);
      this.measureAllCards();
      this.pixelXCorrection = 0;
      this.pixelYCorrection = 0;
      this.applyStableGeometry();

      const deckRect = this.deck.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const rawActiveLeft = deckRect.left + deckRect.width / 2 - this.cardWidth / 2;
      this.pixelXCorrection = Math.round(rawActiveLeft * dpr) / dpr - rawActiveLeft;
      const rawActiveTop = deckRect.top + this.metrics().safeTop;
      this.pixelYCorrection = Math.round(rawActiveTop * dpr) / dpr - rawActiveTop;
      if (mode === "orbit") this.applyAllPoses(this.settledStep, this.metrics(), false);
    }

    resolveCardWidth(deckWidth) {
      if (this.isMobileLayout()) {
        const viewportWidth = window.visualViewport?.width || window.innerWidth;
        return Math.round(Math.min(330, Math.max(0, viewportWidth - 40)));
      }

      return Math.round(Math.min(440, Math.max(280, deckWidth - 24)));
    }

    applyResolvedCardWidth(deckWidth) {
      const width = this.resolveCardWidth(deckWidth);
      if (width === this.resolvedCardWidth) return;
      this.resolvedCardWidth = width;
      this.deck.style.setProperty("--review-card-width", `${width}px`);
    }

    measureAllCards() {
      this.cards.forEach((card) => card.style.removeProperty("height"));
      const reduced = this.getMode() === "reduced";
      this.cardNaturalHeights = this.cards.map((card) => Math.ceil(
        reduced
          ? Math.max(card.offsetHeight, card.scrollHeight)
          : card.offsetHeight,
      ));
      this.maxNaturalCardHeight = Math.max(...this.cardNaturalHeights);
      this.cardWidth = Math.ceil(this.cards[0].offsetWidth);
      if (this.getMode() === "orbit") {
        this.cards.forEach((card, index) => {
          card.style.height = `${this.cardNaturalHeights[index]}px`;
        });
      }
    }

    applyStableGeometry() {
      if (this.getMode() === "reduced") {
        const sceneHeight = this.maxNaturalCardHeight + 336;
        this.deck.style.setProperty("--review-scene-height", `${sceneHeight}px`);
        this.deck.style.removeProperty("--review-card-anchor");
        return;
      }

      const metrics = this.metrics();
      this.deck.style.removeProperty("--review-card-anchor");

      let maximumBottom = 0;
      for (let activeStep = 0; activeStep < this.cards.length; activeStep += 1) {
        this.cards.forEach((_, index) => {
          const pose = this.calculatePose(index, activeStep, metrics);
          maximumBottom = Math.max(
            maximumBottom,
            pose.y + this.cardNaturalHeights[index] * pose.scale,
          );
        });
      }

      for (let fromStep = 0; fromStep < this.cards.length; fromStep += 1) {
        const targetStep = fromStep + 1;
        for (let frame = 0; frame <= 12; frame += 1) {
          const progress = this.easedProgress(frame / 12);
          this.cards.forEach((_, index) => {
            const pose = this.calculateTransitionPose(
              index,
              fromStep,
              targetStep,
              progress,
              metrics,
            );
            maximumBottom = Math.max(
              maximumBottom,
              pose.y + this.cardNaturalHeights[index] * pose.scale,
            );
          });
        }
      }

      this.deck.style.setProperty(
        "--review-scene-height",
        `${Math.ceil(maximumBottom + 48)}px`,
      );
    }

    metrics() {
      const width = this.effectiveWidth || this.deck.getBoundingClientRect().width || window.innerWidth;
      const clamp = (min, value, max) => Math.min(max, Math.max(min, value));
      if (this.isMobileLayout()) {
        return {
          radiusX: clamp(210, width * 0.55, 240),
          radiusY: clamp(125, width * 0.3, 132),
          depthRadius: 24,
          safeTop: 24,
          scaleReduction: 0.3,
          rearScaleBoost: 0.06,
          rearCurvePower: 2,
          horseshoeSpread: 0,
          rearVerticalOffset: 0,
          transitionLift: clamp(28, width * 0.08, 44),
          transitionDepth: 36,
          maxYaw: 0,
          maxRoll: 0,
          pixelXCorrection: this.pixelXCorrection,
          pixelYCorrection: this.pixelYCorrection,
        };
      }

      const cardWidth = this.cardWidth || Math.min(440, width * 0.78);
      const deckRect = this.deck.getBoundingClientRect();
      const viewportWidth = window.visualViewport?.width || window.innerWidth;
      const centerX = deckRect.left + deckRect.width / 2;
      const viewportClearance = Math.max(0, Math.min(centerX, viewportWidth - centerX) - 10);
      const sideDepth = (1 - Math.cos((Math.PI * 2) / this.cards.length)) / 2;
      const rearDepth = (1 - Math.cos((Math.PI * 4) / this.cards.length)) / 2;
      const sideScale = 1 - sideDepth * 0.24;
      const desiredRearGap = clamp(12, width * 0.025, 24);
      const rearScaleLimit = (viewportClearance - desiredRearGap / 2) / cardWidth;
      const rearScale = clamp(0.42, Math.min(0.66, rearScaleLimit), 0.66);
      const rearWidth = cardWidth * rearScale;
      const rearOffset = rearWidth / 2 + desiredRearGap / 2;
      const sideOffsetLimit = Math.max(0, viewportClearance - (cardWidth * sideScale) / 2 - 16);
      const sideOffset = clamp(0, Math.min(96, sideOffsetLimit), 96);
      const rearCurvePower = 2;
      const sideCurve = sideDepth ** rearCurvePower;
      const rearCurve = rearDepth ** rearCurvePower;
      const rearBaseScale = 1 - rearDepth * 0.24;
      const sideAngle = (Math.PI * 2) / this.cards.length;
      const rearAngle = (Math.PI * 4) / this.cards.length;
      const horseshoeSpread = Math.max(
        0,
        (rearOffset / Math.sin(rearAngle) - sideOffset / Math.sin(sideAngle))
          / (rearCurve - sideCurve),
      );

      return {
        radiusX: Math.max(0, sideOffset / Math.sin(sideAngle) - horseshoeSpread * sideCurve),
        radiusY: clamp(82, width * 0.18, 112),
        depthRadius: 32,
        safeTop: 18,
        scaleReduction: 0.24,
        rearScaleBoost: Math.max(0, (rearBaseScale - rearScale) / rearCurve),
        rearCurvePower,
        horseshoeSpread,
        rearVerticalOffset: 8,
        transitionLift: clamp(52, this.maxNaturalCardHeight * 0.2, 86),
        transitionDepth: 56,
        maxYaw: 0,
        maxRoll: 0,
        pixelXCorrection: this.pixelXCorrection,
        pixelYCorrection: this.pixelYCorrection,
      };
    }

    calculatePose(index, step, metrics) {
      const theta = (index - step) * ((Math.PI * 2) / this.cards.length);
      const cosine = Math.cos(theta);
      const sine = Math.sin(theta);
      const depthFactor = (1 - cosine) / 2;
      const horseshoeFactor = depthFactor ** (metrics.rearCurvePower || 2);

      return {
        x: sine * (metrics.radiusX + (metrics.horseshoeSpread || 0) * horseshoeFactor) + metrics.pixelXCorrection,
        y: metrics.safeTop + metrics.pixelYCorrection + (1 - cosine) * metrics.radiusY + (metrics.rearVerticalOffset || 0) * horseshoeFactor,
        z: (cosine - 1) * metrics.depthRadius,
        scale: 1 - depthFactor * metrics.scaleReduction - (metrics.rearScaleBoost || 0) * horseshoeFactor,
        opacity: 1,
        yaw: -sine * metrics.maxYaw,
        roll: sine * metrics.maxRoll,
      };
    }

    interpolatePose(fromPose, toPose, progress) {
      const mix = (from, to) => from + (to - from) * progress;
      return {
        x: mix(fromPose.x, toPose.x),
        y: mix(fromPose.y, toPose.y),
        z: mix(fromPose.z, toPose.z),
        scale: mix(fromPose.scale, toPose.scale),
        opacity: mix(fromPose.opacity, toPose.opacity),
        yaw: mix(fromPose.yaw, toPose.yaw),
        roll: mix(fromPose.roll, toPose.roll),
      };
    }

    calculateTransitionPose(index, fromStep, toStep, progress, metrics) {
      const sourcePose = this.calculatePose(index, fromStep, metrics);
      const targetPose = this.calculatePose(index, toStep, metrics);
      const sourceActiveIndex = this.normalizeIndex(Math.round(fromStep));
      const targetActiveIndex = this.normalizeIndex(Math.round(toStep));
      const outgoing = index === sourceActiveIndex && sourceActiveIndex !== targetActiveIndex;
      const incoming = index === targetActiveIndex && sourceActiveIndex !== targetActiveIndex;
      const sourceRelative = this.relativeAt(index, Math.round(fromStep));
      const targetRelative = this.relativeAt(index, Math.round(toStep));
      const wrapsBehindOrbit = Math.abs(sourceRelative) === 2 && Math.abs(targetRelative) === 2;
      const clampProgress = (value) => Math.min(1, Math.max(0, value));

      let localProgress = progress;
      if (outgoing) {
        localProgress = clampProgress(progress / 0.72);
      } else if (incoming) {
        localProgress = clampProgress((progress - 0.18) / 0.82);
      }

      const pose = this.interpolatePose(sourcePose, targetPose, localProgress);
      if (wrapsBehindOrbit) {
        const laneProgress = Math.sin(Math.PI * progress);
        pose.y += laneProgress * metrics.transitionLift;
        pose.z -= laneProgress * metrics.transitionDepth;
        pose.scale = Math.max(0.42, pose.scale - laneProgress * 0.08);
      }

      return pose;
    }

    poseTransform(pose) {
      if (
        Math.abs(pose.z) < 0.0001
        && Math.abs(pose.yaw) < 0.0001
        && Math.abs(pose.roll) < 0.0001
        && Math.abs(pose.scale - 1) < 0.0001
      ) {
        return `translate(${pose.x}px, ${pose.y}px)`;
      }

      return `translate3d(${pose.x}px, ${pose.y}px, ${pose.z}px) rotateY(${pose.yaw}deg) rotateZ(${pose.roll}deg) scale(${pose.scale})`;
    }

    poseFrame(index, step, offset, metrics) {
      const pose = this.calculatePose(index, step, metrics);
      return {
        offset,
        transform: this.poseTransform(pose),
      };
    }

    transitionPoseFrame(index, fromStep, toStep, progress, metrics) {
      const pose = this.calculateTransitionPose(index, fromStep, toStep, progress, metrics);
      return {
        offset: progress,
        transform: this.poseTransform(pose),
      };
    }

    easedProgress(progress) {
      if (progress <= 0 || progress >= 1) return progress;

      const x1 = 0.16;
      const y1 = 1;
      const x2 = 0.3;
      const y2 = 1;
      const sampleX = (t) => 3 * (1 - t) ** 2 * t * x1
        + 3 * (1 - t) * t ** 2 * x2 + t ** 3;
      const sampleY = (t) => 3 * (1 - t) ** 2 * t * y1
        + 3 * (1 - t) * t ** 2 * y2 + t ** 3;
      const sampleDerivative = (t) => 3 * (1 - t) ** 2 * x1
        + 6 * (1 - t) * t * (x2 - x1) + 3 * t ** 2 * (1 - x2);

      let estimate = progress;
      for (let iteration = 0; iteration < 5; iteration += 1) {
        const derivative = sampleDerivative(estimate);
        if (Math.abs(derivative) < 0.0001) break;
        estimate -= (sampleX(estimate) - progress) / derivative;
        estimate = Math.min(1, Math.max(0, estimate));
      }

      return sampleY(estimate);
    }

    depthZIndex(pose, index) {
      return String(100000 + Math.round(pose.z * 1000) - index);
    }

    transitionZIndex(index, fromStep, toStep, progress, metrics) {
      const pose = this.calculateTransitionPose(index, fromStep, toStep, progress, metrics);
      const sourceActiveIndex = this.normalizeIndex(Math.round(fromStep));
      const targetActiveIndex = this.normalizeIndex(Math.round(toStep));
      const ownershipProgress = 0.66;

      if (index === sourceActiveIndex && sourceActiveIndex !== targetActiveIndex && progress < ownershipProgress) {
        return String(200000 - Math.round(progress * 1000) - index);
      }

      if (index === targetActiveIndex && sourceActiveIndex !== targetActiveIndex && progress >= ownershipProgress) {
        return String(200000 + Math.round(progress * 1000) - index);
      }

      return this.depthZIndex(pose, index);
    }

    applyPose(index, step, metrics) {
      const pose = this.calculatePose(index, step, metrics);
      const slot = this.slots[index];
      slot.style.transform = this.poseTransform(pose);
      slot.style.opacity = "1";
      slot.style.zIndex = this.depthZIndex(pose, index);
    }

    syncInterpolatedLayerOrder(step, metrics = this.metrics(), transition = null) {
      this.slots.forEach((slot, index) => {
        slot.style.zIndex = transition
          ? this.transitionZIndex(
            index,
            transition.fromStep,
            transition.toStep,
            transition.progress,
            metrics,
          )
          : this.depthZIndex(this.calculatePose(index, step, metrics), index);
      });
    }

    applyAllPoses(step, metrics = this.metrics(), updateDetails = false) {
      if (!this.isAnimatedMode()) return;
      this.visualStep = step;
      this.cards.forEach((card, index) => {
        this.applyPose(index, step, metrics);
        if (updateDetails) {
          this.setDetailOpacity(card, 1);
        }
      });
    }

    setDetailOpacity(card, opacity) {
      const value = Math.round(opacity * 1000) / 1000;
      const index = Number(card.dataset.reviewIndex);
      if (this.detailOpacityValues[index] === value) return;
      this.detailOpacityValues[index] = value;
      card.style.setProperty("--review-detail-opacity", String(value));
    }

    syncContentStates(step = this.settledStep) {
      const mode = this.getMode();
      if (mode === "reduced") {
        this.cards.forEach((card) => this.setDetailOpacity(card, 1));
        return;
      }

      this.cards.forEach((card) => this.setDetailOpacity(card, 1));
    }

    syncVisualStates() {
      const mode = this.getMode();

      this.cards.forEach((card, index) => {
        const relative = this.relativeAt(index);
        const depth = Math.abs(relative);
        const selectable = mode === "reduced" || depth <= 1;
        const slot = this.slots[index];

        card.dataset.reviewRelative = slot.dataset.reviewRelative = String(relative);
        card.dataset.reviewDepth = slot.dataset.reviewDepth = String(depth);

        [card, slot].forEach((node) => {
          node.classList.toggle("is-active", depth === 0);
          node.classList.toggle("is-left", relative === -1);
          node.classList.toggle("is-right", relative === 1);
          node.classList.toggle("is-depth-2", depth === 2);
          node.classList.toggle("is-rear", depth === Math.floor(this.cards.length / 2));
          node.classList.remove("is-offscreen");
        });

        card.setAttribute("aria-pressed", String(depth === 0));
        card.tabIndex = mode === "reduced"
          ? 0
          : (this.isMobileLayout() ? -1 : (selectable ? 0 : -1));
        card.inert = !selectable;
        if (selectable) card.removeAttribute("aria-hidden");
        else card.setAttribute("aria-hidden", "true");
      });
    }

    announceActive() {
      if (!this.status) return;
      const name = this.cards[this.activeIndex]
        .querySelector(".review-card__name")
        ?.textContent
        ?.trim() || "";
      this.status.textContent = `Review ${this.activeIndex + 1} of ${this.cards.length}: ${name}`;
    }

    requestDelta(delta, source = "manual") {
      if (!delta) return;
      this.requestStep(this.settledStep + delta, source);
    }

    requestTarget(index, source = "manual") {
      this.requestStep(this.resolveTargetStep(index, this.settledStep), source);
    }

    requestStep(targetStep, source = "manual") {
      if (!Number.isFinite(targetStep)) return;
      const target = Math.round(targetStep);

      if (this.phase !== "idle") {
        return;
      }

      if (!this.isAnimatedMode()) {
        this.commitImmediate(target);
        return;
      }

      this.startSettle(target, source);
    }

    commitImmediate(step) {
      this.settledStep = step;
      this.visualStep = step;
      this.activeIndex = this.normalizeIndex(step);
      this.syncVisualStates();
      this.syncContentStates();
      if (this.isAnimatedMode()) this.applyAllPoses(step, this.metrics(), false);
      this.announceActive();
      this.syncStateAttributes();
    }

    buildKeyframes(index, fromStep, toStep, metrics) {
      const frameCount = 13;
      return Array.from({ length: frameCount }, (_, frame) => {
        const progress = this.easedProgress(frame / (frameCount - 1));
        return this.transitionPoseFrame(
          index,
          fromStep,
          toStep,
          progress,
          metrics,
        );
      });
    }

    durationFor() {
      return 620;
    }

    startProgressClock(generation, fromStep, targetStep, duration, metrics) {
      const startedAt = performance.now();
      const tick = (now) => {
        if (generation !== this.animationGeneration || this.phase !== "settling") return;
        const progress = Math.min(1, Math.max(0, (now - startedAt) / duration));
        const eased = this.easedProgress(progress);
        this.visualStep = fromStep + (targetStep - fromStep) * eased;
        this.syncInterpolatedLayerOrder(this.visualStep, metrics, {
          fromStep,
          toStep: targetStep,
          progress: eased,
        });
        if (progress < 1) this.settleProgressFrame = requestAnimationFrame(tick);
      };
      this.settleProgressFrame = requestAnimationFrame(tick);
    }

    async startSettle(targetStep, source = "manual") {
      if (this.phase !== "idle") {
        return;
      }

      const fromStep = this.visualStep;
      const target = Math.round(targetStep);
      const distance = Math.abs(target - fromStep);

      if (distance < 0.001 || !this.isAnimatedMode()) {
        this.commitImmediate(target);
        return;
      }

      const metrics = this.metrics();
      const duration = this.durationFor();
      const targetIndex = this.normalizeIndex(target);
      const generation = ++this.animationGeneration;
      this.currentTargetStep = target;
      this.setPhase("settling");
      this.syncInterpolatedLayerOrder(fromStep, metrics);
      this.slots.forEach((slot) => {
        slot.style.willChange = "transform";
      });

      const slotAnimations = this.slots.map((slot, index) => slot.animate(
        this.buildKeyframes(index, fromStep, target, metrics),
        {
          duration,
          easing: "cubic-bezier(0.16, 1, 0.3, 1)",
          fill: "both",
        },
      ));
      this.activeAnimations = slotAnimations;
      this.syncStateAttributes();
      this.startProgressClock(generation, fromStep, target, duration, metrics);

      const finished = Promise.allSettled(
        this.activeAnimations.map((animation) => animation.finished),
      );
      const fallback = new Promise((resolve) => {
        this.settleFallbackTimer = window.setTimeout(resolve, duration + 150);
      });

      try {
        await Promise.race([finished, fallback]);
        if (generation !== this.animationGeneration || this.phase !== "settling") return;

        this.applyAllPoses(target, metrics, false);
        this.syncContentStates(target);
        this.releaseAnimations();

        this.settledStep = target;
        this.visualStep = target;
        this.activeIndex = targetIndex;
        this.currentTargetStep = null;
        this.syncVisualStates();
        this.syncContentStates();
        this.announceActive();
        this.triggerArrival(targetIndex);
        this.setPhase("idle");

        if (this.pendingResize) {
          this.pendingResize = false;
          this.handleWidthChange(true);
        }

        this.syncStateAttributes();
      } catch {
        if (generation !== this.animationGeneration) return;
        this.recoverToSettledState();
      }
    }

    releaseAnimations() {
      if (this.settleFallbackTimer) {
        window.clearTimeout(this.settleFallbackTimer);
        this.settleFallbackTimer = 0;
      }
      if (this.settleProgressFrame) {
        window.cancelAnimationFrame(this.settleProgressFrame);
        this.settleProgressFrame = 0;
      }
      this.activeAnimations.forEach((animation) => animation.cancel());
      this.activeAnimations = [];
      this.slots.forEach((slot) => {
        slot.style.removeProperty("will-change");
      });
      this.syncStateAttributes();
    }

    cancelAnimations(restore = false) {
      this.animationGeneration += 1;
      this.releaseAnimations();
      this.currentTargetStep = null;
      if (restore && this.isAnimatedMode() && this.slots) {
        this.applyAllPoses(this.settledStep, this.metrics(), false);
        this.syncContentStates();
      }
    }

    recoverToSettledState() {
      this.releaseAnimations();
      this.currentTargetStep = null;
      this.visualStep = this.settledStep;
      this.activeIndex = this.normalizeIndex(this.settledStep);
      if (this.isAnimatedMode()) {
        this.applyAllPoses(this.settledStep, this.metrics(), false);
      }
      this.syncVisualStates();
      this.syncContentStates();
      this.setPhase("idle");
    }

    triggerArrival(index) {
      if (!this.isAnimatedMode()) return;
      if (this.arrivalTimer) window.clearTimeout(this.arrivalTimer);
      this.cards.forEach((card) => card.classList.remove("is-arriving"));
      const card = this.cards[index];
      card.classList.add("is-arriving");
      this.arrivalTimer = window.setTimeout(() => {
        card.classList.remove("is-arriving");
        this.arrivalTimer = 0;
      }, 220);
    }

    setTemporaryWillChange(enabled) {
      this.slots.forEach((slot) => {
        if (enabled) slot.style.willChange = "transform";
        else slot.style.removeProperty("will-change");
      });
    }

    scheduleDragRender() {
      if (this.dragFrame || !this.pointerState) return;
      this.dragFrame = window.requestAnimationFrame(() => {
        this.dragFrame = 0;
        const pointer = this.pointerState;
        if (!pointer || pointer.axisIntent !== "horizontal") return;
        this.applyAllPoses(this.visualStep, pointer.cachedMetrics, true);
      });
    }

    handlePointerDown(event) {
      if (!this.isAnimatedMode() || this.phase !== "idle") return;
      if (event.isPrimary === false) return;
      if (event.pointerType === "mouse" && event.button !== 0) return;

      this.pointerState = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        latestX: event.clientX,
        latestTime: event.timeStamp,
        velocityX: 0,
        axisIntent: null,
        cachedSceneWidth: this.effectiveWidth || this.deck.getBoundingClientRect().width,
        cachedMetrics: this.metrics(),
        dragProgress: 0,
      };
    }

    handlePointerMove(event) {
      const pointer = this.pointerState;
      if (!pointer || pointer.pointerId !== event.pointerId) return;

      const dx = event.clientX - pointer.startX;
      const dy = event.clientY - pointer.startY;
      const absoluteX = Math.abs(dx);
      const absoluteY = Math.abs(dy);

      if (!pointer.axisIntent) {
        if (absoluteX >= 12 && absoluteX > absoluteY * 1.2) {
          pointer.axisIntent = "horizontal";
          this.setPhase("dragging");
          this.setTemporaryWillChange(true);
          if (event.pointerType !== "touch") {
            try {
              this.deck.setPointerCapture(event.pointerId);
            } catch {
              // Document-level recovery still clears the gesture if capture is unavailable.
            }
          }
        } else if (absoluteY >= 12 && absoluteY > absoluteX * 1.2) {
          pointer.axisIntent = "vertical";
          return;
        } else {
          return;
        }
      }

      if (pointer.axisIntent !== "horizontal") return;
      event.preventDefault();

      const elapsed = Math.max(1, event.timeStamp - pointer.latestTime);
      const instantaneousVelocity = (event.clientX - pointer.latestX) / elapsed;
      pointer.velocityX = pointer.velocityX * 0.62 + instantaneousVelocity * 0.38;
      pointer.latestX = event.clientX;
      pointer.latestTime = event.timeStamp;

      const rawProgress = -dx / Math.max(1, pointer.cachedSceneWidth * 0.55);
      const magnitude = Math.abs(rawProgress);
      const resistanceStart = 0.64;
      const dragCap = 0.96;
      const resistedMagnitude = magnitude <= resistanceStart
        ? magnitude
        : resistanceStart + (dragCap - resistanceStart)
          * (1 - Math.exp(-(magnitude - resistanceStart) * 2.4));
      const resistedProgress = Math.sign(rawProgress) * Math.min(dragCap, resistedMagnitude);

      pointer.dragProgress = resistedProgress;
      this.visualStep = this.settledStep + resistedProgress;
      this.scheduleDragRender();
    }

    handlePointerEnd(event, cancelled = false) {
      const pointer = this.pointerState;
      if (!pointer || (event.pointerId != null && pointer.pointerId !== event.pointerId)) return;

      this.pointerState = null;
      if (this.dragFrame) {
        window.cancelAnimationFrame(this.dragFrame);
        this.dragFrame = 0;
        if (pointer.axisIntent === "horizontal") {
          this.applyAllPoses(this.visualStep, pointer.cachedMetrics, true);
        }
      }

      try {
        if (this.deck.hasPointerCapture(pointer.pointerId)) {
          this.deck.releasePointerCapture(pointer.pointerId);
        }
      } catch {
        // Capture may already have been released by the browser.
      }

      if (pointer.axisIntent !== "horizontal") {
        this.setTemporaryWillChange(false);
        this.setPhase("idle");
        return;
      }

      const endX = event.clientX ?? pointer.latestX;
      const distance = Math.abs(endX - pointer.startX);
      const velocity = Math.abs(pointer.velocityX);
      const passesDistance = distance >= pointer.cachedSceneWidth * 0.16;
      const passesFlick = distance >= 26 && velocity >= 0.45;
      const shouldCommit = !cancelled && (passesDistance || passesFlick);
      let targetStep = this.settledStep;

      if (shouldCommit) {
        const direction = Math.sign(
          pointer.dragProgress || -pointer.velocityX || -(endX - pointer.startX),
        );
        if (direction) targetStep = this.settledStep + direction;
      }

      if (distance >= 12) this.clickSuppressionUntil = performance.now() + 420;
      this.setPhase("idle");
      this.startSettle(targetStep, shouldCommit ? "drag" : "drag-cancel");
    }

    cancelPointer(settle = true) {
      const pointer = this.pointerState;
      if (!pointer) return;

      this.pointerState = null;
      if (this.dragFrame) {
        window.cancelAnimationFrame(this.dragFrame);
        this.dragFrame = 0;
      }
      try {
        if (this.deck.hasPointerCapture(pointer.pointerId)) {
          this.deck.releasePointerCapture(pointer.pointerId);
        }
      } catch {
        // Capture cleanup is best effort.
      }

      if (
        settle
        && pointer.axisIntent === "horizontal"
        && this.isAnimatedMode()
      ) {
        this.setPhase("idle");
        this.startSettle(this.settledStep, "pointer-cancel");
      } else {
        this.visualStep = this.settledStep;
        if (this.isAnimatedMode()) {
          this.applyAllPoses(this.settledStep, pointer.cachedMetrics || this.metrics(), false);
        }
        this.syncContentStates();
        this.setTemporaryWillChange(false);
        this.setPhase("idle");
      }
    }

    handleCardClick(event) {
      const card = event.target.closest("[data-review-card]");
      if (!card || !this.orbit.contains(card)) return;
      if (performance.now() < this.clickSuppressionUntil) {
        event.preventDefault();
        return;
      }
      const index = Number(card.dataset.reviewIndex);
      if (index === this.activeIndex) return;
      this.requestTarget(index, "card-tap");
    }

    handleKeyDown(event) {
      const card = event.target.closest?.("[data-review-card]");
      if (card && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        this.handleCardClick(event);
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        this.requestDelta(1, "keyboard");
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        this.requestDelta(-1, "keyboard");
      } else if (event.key === "Home") {
        event.preventDefault();
        this.requestTarget(0, "keyboard");
      } else if (event.key === "End") {
        event.preventDefault();
        this.requestTarget(this.cards.length - 1, "keyboard");
      }
    }

    bindEvents() {
      const { signal } = this.abortController;

      this.deck.addEventListener("click", (event) => this.handleCardClick(event), { signal });
      this.deck.addEventListener("keydown", (event) => this.handleKeyDown(event), { signal });
      this.deck.addEventListener("pointerdown", (event) => this.handlePointerDown(event), { signal });
      this.deck.addEventListener("pointermove", (event) => this.handlePointerMove(event), {
        signal,
        passive: false,
      });
      this.deck.addEventListener("pointerup", (event) => this.handlePointerEnd(event), { signal });
      this.deck.addEventListener(
        "pointercancel",
        (event) => this.handlePointerEnd(event, true),
        { signal },
      );
      this.deck.addEventListener(
        "lostpointercapture",
        (event) => this.handlePointerEnd(event, true),
        { signal },
      );
      window.addEventListener("blur", () => this.cancelPointer(true), { signal });

      mobileQuery.addEventListener?.("change", () => this.handleModeChange(), { signal });
      reducedQuery.addEventListener?.("change", () => this.handleModeChange(), { signal });
      window.addEventListener("orientationchange", () => {
        this.cancelPointer(true);
        this.handleWidthChange(true);
      }, { signal });
      document.addEventListener("visibilitychange", () => {
        this.deck.classList.toggle(
          "is-paused-visibility",
          document.visibilityState !== "visible" || !this.componentVisible,
        );
      }, { signal });

      this.resizeObserver = new ResizeObserver((entries) => {
        const width = Math.round(entries[0].contentRect.width);
        if (Math.abs(width - this.effectiveWidth) < 2 || this.widthFrame) return;
        if (this.phase === "dragging") {
          this.cancelPointer(true);
          return;
        }
        this.widthFrame = window.requestAnimationFrame(() => {
          this.widthFrame = 0;
          this.handleWidthChange();
        });
      });
      this.resizeObserver.observe(this.deck);

      this.intersectionObserver = new IntersectionObserver(([entry]) => {
        this.componentVisible = entry.isIntersecting;
        this.deck.classList.toggle(
          "is-paused-visibility",
          !this.componentVisible || document.visibilityState !== "visible",
        );
      }, { threshold: 0.12 });
      this.intersectionObserver.observe(this.deck);
    }
  }

  document.querySelectorAll("[data-review-deck]").forEach((deck) => {
    new ReviewOrbitController(deck).init();
  });
})();
