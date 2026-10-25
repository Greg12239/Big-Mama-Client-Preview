"use client";

import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { useRef } from "react";

type KineticBrandmarkProps = {
  heroElement: HTMLElement;
};

export function KineticBrandmark({ heroElement }: KineticBrandmarkProps) {
  const heroRef = useRef<HTMLElement | null>(heroElement);
  const shouldReduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 120,
    damping: 28,
    mass: 0.3,
    restDelta: 0.0005,
  });
  const rotation = useTransform(smoothProgress, [0, 0.34, 0.5, 0.65, 1], [-5, 1.2, 0.2, 0, 5.5]);
  const scale = useTransform(smoothProgress, [0, 0.34, 0.5, 0.65, 1], [0.95, 1.025, 1.032, 1.035, 1.075]);
  const x = useTransform(smoothProgress, [0, 0.34, 0.65, 1], [0, 1, 0, 14]);
  const y = useTransform(smoothProgress, [0, 0.34, 0.5, 0.65, 1], [18, 0, 0.5, 1, 52]);
  const opacity = useTransform(smoothProgress, [0, 0.65, 1], [1, 1, 0]);

  const staticStyle = {
    opacity: 1,
    rotate: -4,
    scale: 0.97,
    x: 0,
    y: 12,
  };

  return (
    <motion.div className="hero-brand-stage" aria-hidden="true">
      <motion.img
        className="hero-brandmark"
        src="/assets/big-mama-logo.png"
        alt=""
        width={834}
        height={860}
        decoding="async"
        fetchPriority="high"
        style={shouldReduceMotion ? staticStyle : { opacity, rotate: rotation, scale, x, y }}
      />
    </motion.div>
  );
}
