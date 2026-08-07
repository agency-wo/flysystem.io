/* Server statico per l'anteprima locale, con supporto alle richieste Range.
 * Serve perche `python -m http.server` NON risponde 206 e con quello i video
 * non partono su Safari: un falso allarme che costa tempo.
 *
 * usage: node tools/serve.mjs [porta]
 */
import { createServer } from "node:http";
import { createReadStream, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = normalize(join(fileURLToPath(new URL(".", import.meta.url)), ".."));
const PORT = Number(process.argv[2] || 8050);
const TYPES = {
  ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
  ".mp4": "video/mp4", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
  ".avif": "image/avif", ".woff2": "font/woff2", ".svg": "image/svg+xml",
  ".pdf": "application/pdf", ".ico": "image/x-icon",
};

createServer((req, res) => {
  let path = join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  let st;
  try {
    st = statSync(path);
    if (st.isDirectory()) {
      path = join(path, "index.html");
      st = statSync(path);
    }
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain" }).end("404");
    return;
  }
  const type = TYPES[extname(path)] || "application/octet-stream";
  const range = req.headers.range;
  if (range) {
    const m = /bytes=(\d*)-(\d*)/.exec(range);
    const start = m[1] ? parseInt(m[1], 10) : 0;
    const end = m[2] ? parseInt(m[2], 10) : st.size - 1;
    res.writeHead(206, {
      "Content-Type": type,
      "Content-Range": `bytes ${start}-${end}/${st.size}`,
      "Accept-Ranges": "bytes",
      "Content-Length": end - start + 1,
    });
    createReadStream(path, { start, end }).pipe(res);
  } else {
    res.writeHead(200, { "Content-Type": type, "Content-Length": st.size, "Accept-Ranges": "bytes" });
    createReadStream(path).pipe(res);
  }
}).listen(PORT, () => console.log(`http://127.0.0.1:${PORT}/`));
