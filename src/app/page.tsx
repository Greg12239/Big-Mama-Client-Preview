import { HeroMotion } from "@/components/sections/Hero";
import { LegacyPageMarkup } from "@/components/LegacyPageMarkup";
import { LegacyRuntime } from "@/components/runtime/LegacyRuntime";

export default function HomePage() {
  return (
    <>
      <LegacyPageMarkup />
      <HeroMotion />
      <LegacyRuntime />
    </>
  );
}
