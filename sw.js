// 나의 일상 - 오프라인용 서비스 워커 (화면 파일만 저장, 데이터는 Firebase/기기에 저장)
const CACHE = "naui-ilsang-v3";
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

// ---------- 아침 알림 (Firebase 메시지) ----------
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : "" }; }
  const m = Object.assign({}, d.data || {}, d.notification || {});
  const title = m.title || "나의 일상";
  const opts = { body: m.body || "", icon: "icon-192.png", badge: "icon-192.png", tag: m.tag || "naui-morning", renotify: true, data: { url: self.registration.scope } };
  e.waitUntil(self.registration.showNotification(title, opts));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || self.registration.scope;
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then(ws => {
    for (const w of ws) { if (w.url.startsWith(self.registration.scope) && "focus" in w) return w.focus(); }
    return clients.openWindow(url);
  }));
});
