import { getLegacyPageMarkup } from "@/lib/legacy-markup";

export function LegacyPageMarkup() {
  return <div dangerouslySetInnerHTML={{ __html: getLegacyPageMarkup() }} />;
}
