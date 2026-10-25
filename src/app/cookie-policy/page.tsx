import type { Metadata } from "next";
import { LegalPage } from "@/components/legal/LegalPage";

export const metadata: Metadata = { title: "Cookie Policy | Big Mama" };

export default function CookiePolicyPage() {
  return <LegalPage title="Cookie Policy">
    <p>This website uses essential local storage to remember your cookie preference. It is necessary to provide and retain your consent choice. The data controller is ONE MORE PLEASE Ε.Ε., Λεωφόρος Δεκελείας 114, 14341 Νέα Φιλαδέλφεια, Ελλάδα. Contact: <a href="mailto:info@bigmama.gr">info@bigmama.gr</a>.</p>
    <h2>Optional categories</h2>
    <p>Analytics and marketing technologies are optional and default to off. They can be enabled independently through Cookie Settings and can be withdrawn at any time.</p>
    <h2>Google Consent Mode</h2>
    <p>Google Consent Mode defaults are set to denied. No Google Analytics or marketing tag is installed by this implementation. Any future Google integration must respect the preference selected here and be recorded in this policy before release.</p>
    <h2>How to update your choice</h2>
    <p>Use the Cookie Settings link in the footer on the home page. You can also clear local website storage in your browser to remove the saved preference.</p>
  </LegalPage>;
}
