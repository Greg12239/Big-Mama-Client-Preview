import type { Metadata } from "next";
import { LegalPage } from "@/components/legal/LegalPage";

export const metadata: Metadata = { title: "Privacy Policy | Big Mama" };

export default function PrivacyPolicyPage() {
  return <LegalPage title="Privacy Policy">
    <p>This draft explains the privacy approach for the Big Mama website. It is not a substitute for business-specific legal review.</p>
    <h2>What this website processes</h2>
    <p>Essential local storage records your cookie decision. Optional analytics and marketing technologies are disabled unless you actively enable them in Cookie Settings.</p>
    <h2>Your choices and rights</h2>
    <p>You can change or withdraw optional-cookie choices at any time using Cookie Settings in the website footer. The data controller is ONE MORE PLEASE Ε.Ε.; privacy requests can be sent to <a href="mailto:info@bigmama.gr">info@bigmama.gr</a>. Applicable lawful bases and retention periods require final legal confirmation.</p>
    <h2>Third parties</h2>
    <p>Google Analytics or advertising tags are not loaded by this implementation. If they are added later, this policy and the Cookie Policy must be updated with the approved provider, purpose, data-transfer safeguards, and retention information.</p>
  </LegalPage>;
}
