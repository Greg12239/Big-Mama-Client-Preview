import Link from "next/link";

type LegalPageProps = { title: string; children: React.ReactNode };

export function LegalPage({ title, children }: LegalPageProps) {
  return (
    <main className="legal-page">
      <div className="legal-page__card">
        <Link className="legal-page__back" href="/">← Back to Big Mama</Link>
        <p className="legal-page__eyebrow">LEGAL INFORMATION</p>
        <h1>{title}</h1>
        <div className="legal-page__content">{children}</div>
        <p className="legal-page__notice"><strong>Data controller:</strong> ONE MORE PLEASE Ε.Ε.<br />Λεωφόρος Δεκελείας 114, 14341 Νέα Φιλαδέλφεια, Ελλάδα<br />Privacy contact: <a href="mailto:info@bigmama.gr">info@bigmama.gr</a><br />Phone: <a href="tel:+302160033303">+30 21 6003 3303</a><br /><br /><strong>Still requiring legal confirmation:</strong> lawful bases, retention periods, and the complete processor list.</p>
      </div>
    </main>
  );
}
