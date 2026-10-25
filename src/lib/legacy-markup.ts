import { readFileSync } from "node:fs";
import { join } from "node:path";

let cachedMarkup: string | undefined;

function extractBodyMarkup(documentMarkup: string) {
  const bodyMatch = documentMarkup.match(/<body>([\s\S]*?)<\/body>/i);
  if (!bodyMatch) throw new Error("The legacy page body could not be found.");

  return bodyMatch[1]
    .replace(/\s*<script[\s\S]*?<\/script>/gi, "")
    .replaceAll("public/assets/", "/assets/");
}

export function getLegacyPageMarkup() {
  if (!cachedMarkup) {
    const legacyIndex = readFileSync(join(process.cwd(), "index.html"), "utf8");
    cachedMarkup = extractBodyMarkup(legacyIndex);
  }

  return cachedMarkup;
}
