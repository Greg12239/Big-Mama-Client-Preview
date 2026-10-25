import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const root = join(process.cwd(), "out");
const port = Number(process.env.PORT || 3000);
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

createServer((request, response) => {
  const requestedPath = decodeURIComponent(new URL(request.url || "/", `http://localhost:${port}`).pathname);
  const relativePath = requestedPath === "/" ? "index.html" : requestedPath.replace(/^\/+/, "");
  const resolvedPath = normalize(join(root, relativePath));
  const routePath = requestedPath === "/"
    ? join(root, "index.html")
    : join(root, `${relativePath.replace(/\/+$/, "")}.html`);
  const directoryIndexPath = join(resolvedPath, "index.html");
  const candidates = [resolvedPath, routePath, directoryIndexPath];
  const filePath = candidates.find((candidate) => {
    try {
      return existsSync(candidate) && statSync(candidate).isFile();
    } catch {
      return false;
    }
  });

  if (!filePath || !filePath.startsWith(root)) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }

  response.writeHead(200, { "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream" });
  createReadStream(filePath).pipe(response);
}).listen(port, () => {
  console.log(`Static preview available at http://localhost:${port}`);
});
