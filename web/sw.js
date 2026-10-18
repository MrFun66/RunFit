// Service Worker：离线兜底，缓存版本随构建变化
const CACHE_NAME = 'grf-20261018141029';
const ASSETS = ['/', '/manifest.json', '/assets/style.css'];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS).catch(() => {})));
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (e) => {
    if (e.request.method !== 'GET' || e.request.url.includes('/api/')) return;
    // 网络优先，失败才用缓存
    e.respondWith(
        fetch(e.request).then(res => {
            if (res && res.ok && e.request.url.includes('/assets/')) {
                const copy = res.clone();
                caches.open(CACHE_NAME).then(c => c.put(e.request, copy));
            }
            return res;
        }).catch(() => caches.match(e.request))
    );
});