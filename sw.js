// 나의 일상 - 오프라인용 서비스 워커 (화면 파일만 저장, 데이터는 Firebase/기기에 저장)
const CACHE = "naui-ilsang-v2";
const SHELL = ["./", "index.html", "manifest.webmanifest", "firebase-config.js", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/__/")) return;
  // 항상 서버에 새 버전이 있는지 확인하고(no-cache), 인터넷이 없으면 저장된 화면을 씀
  e.respondWith(fetch(e.request, { cache: "no-cache" }).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match("index.html"))));
});
