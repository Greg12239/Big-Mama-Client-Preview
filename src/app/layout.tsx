import type { Metadata } from "next";
import Script from "next/script";
import { ConsentManager } from "@/components/consent/ConsentManager";
import "./globals.css";

const siteOrigin = "https://www.bigmama.gr";
const siteName = "Big Mama";
const siteDescription = "Big Mama Burgers n' Fries premium animated landing page.";
const logoPath = "/assets/logo/big-mama-logo-transparent.png";

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin),
  title: "Big Mama | Burgers n' Fries",
  description: siteDescription,
  alternates: { canonical: "/" },
  openGraph: {
    title: "Big Mama | Burgers n' Fries",
    description: siteDescription,
    url: "/",
    siteName,
    type: "website",
    images: [{ url: logoPath, alt: siteName }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Big Mama | Burgers n' Fries",
    description: siteDescription,
    images: [logoPath],
  },
  icons: {
    icon: logoPath,
    apple: logoPath,
  },
};

const restaurantSchema = {
  "@context": "https://schema.org",
  "@type": "Restaurant",
  "@id": `${siteOrigin}/#restaurant`,
  name: siteName,
  url: `${siteOrigin}/`,
  image: `${siteOrigin}${logoPath}`,
  logo: `${siteOrigin}${logoPath}`,
  telephone: "+30 21 6003 3303",
  address: {
    "@type": "PostalAddress",
    streetAddress: "Λεωφόρος Δεκελείας 114",
    addressLocality: "Νέα Φιλαδέλφεια",
    postalCode: "14341",
    addressCountry: "GR",
  },
  geo: {
    "@type": "GeoCoordinates",
    latitude: 38.0349902,
    longitude: 23.7386331,
  },
  openingHoursSpecification: [
    { "@type": "OpeningHoursSpecification", dayOfWeek: ["Monday", "Tuesday", "Wednesday", "Thursday"], opens: "16:00", closes: "00:00" },
    { "@type": "OpeningHoursSpecification", dayOfWeek: "Friday", opens: "16:00", closes: "01:00" },
    { "@type": "OpeningHoursSpecification", dayOfWeek: "Saturday", opens: "15:00", closes: "02:00" },
    { "@type": "OpeningHoursSpecification", dayOfWeek: "Sunday", opens: "14:00", closes: "00:00" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-hero-motion="motion">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(restaurantSchema) }} />
        <Script id="google-consent-mode-defaults" strategy="beforeInteractive">
          {`window.dataLayer=window.dataLayer||[];window.gtag=window.gtag||function(){window.dataLayer.push(arguments)};window.gtag('consent','default',{ad_storage:'denied',analytics_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',functionality_storage:'denied',personalization_storage:'denied',security_storage:'granted',wait_for_update:500});`}
        </Script>
        {children}
        <ConsentManager />
      </body>
    </html>
  );
}
