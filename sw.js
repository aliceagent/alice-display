/**
 * Alice Display Service Worker
 * Enables offline support with intelligent caching
 */

const CACHE_NAME = 'alice-display-v1';
const STATIC_CACHE = 'alice-static-v1';
const IMAGE_CACHE = 'alice-images-v1';

// Static assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/index-dynamic.html',
  '/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Static assets cached');
        return self.skipWaiting();
      })
      .catch((err) => {
        console.error('[SW] Failed to cache static assets:', err);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old versions of our caches
              return name.startsWith('alice-') && 
                     name !== STATIC_CACHE && 
                     name !== IMAGE_CACHE &&
                     name !== CACHE_NAME;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Skip cross-origin requests (except images from our CDN)
  if (url.origin !== location.origin && !url.hostname.includes('cloudinary')) {
    return;
  }
  
  // Handle different resource types
  if (url.pathname.endsWith('.json')) {
    // JSON files: Network first, cache fallback
    event.respondWith(networkFirstStrategy(event.request, CACHE_NAME));
  } else if (url.pathname.includes('/images/') || url.pathname.endsWith('.png') || url.pathname.endsWith('.jpg') || url.pathname.endsWith('.webp')) {
    // Images: Cache first, network fallback (with background update)
    event.respondWith(cacheFirstStrategy(event.request, IMAGE_CACHE));
  } else {
    // Static assets: Cache first, network fallback
    event.respondWith(cacheFirstStrategy(event.request, STATIC_CACHE));
  }
});

/**
 * Network first strategy - try network, fall back to cache
 * Good for frequently updated data like display-control.json
 */
async function networkFirstStrategy(request, cacheName) {
  try {
    const networkResponse = await fetchWithTimeout(request, 10000);
    
    if (networkResponse.ok) {
      // Clone and cache the response
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
    
    throw new Error(`HTTP ${networkResponse.status}`);
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('[SW] Serving from cache:', request.url);
      return cachedResponse;
    }
    
    // Return error response if nothing in cache
    return new Response(JSON.stringify({
      error: 'Offline',
      message: 'No cached data available',
      offline: true
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Cache first strategy - try cache, fall back to network
 * Good for static assets and images
 */
async function cacheFirstStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    // Return cached response immediately
    // Also update cache in background
    updateCacheInBackground(request, cacheName);
    return cachedResponse;
  }
  
  // Not in cache, fetch from network
  try {
    const networkResponse = await fetchWithTimeout(request, 30000);
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Failed to fetch:', request.url, error);
    
    // Return a placeholder response for images
    if (request.url.includes('/images/')) {
      return new Response('Image not available offline', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' }
      });
    }
    
    throw error;
  }
}

/**
 * Update cache in background without blocking
 */
function updateCacheInBackground(request, cacheName) {
  fetchWithTimeout(request, 30000)
    .then((response) => {
      if (response.ok) {
        caches.open(cacheName)
          .then((cache) => cache.put(request, response));
      }
    })
    .catch(() => {
      // Ignore background update failures
    });
}

/**
 * Fetch with timeout
 */
function fetchWithTimeout(request, timeout) {
  return new Promise((resolve, reject) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
      reject(new Error('Request timeout'));
    }, timeout);
    
    fetch(request, { signal: controller.signal })
      .then((response) => {
        clearTimeout(timeoutId);
        resolve(response);
      })
      .catch((error) => {
        clearTimeout(timeoutId);
        reject(error);
      });
  });
}

// Listen for messages from the main app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_IMAGE') {
    // Manually cache an image
    const imageUrl = event.data.url;
    caches.open(IMAGE_CACHE)
      .then((cache) => fetch(imageUrl))
      .then((response) => {
        if (response.ok) {
          return caches.open(IMAGE_CACHE)
            .then((cache) => cache.put(imageUrl, response));
        }
      })
      .catch((err) => console.error('[SW] Failed to cache image:', err));
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    // Clear all caches
    caches.keys()
      .then((names) => Promise.all(names.map((name) => caches.delete(name))))
      .then(() => console.log('[SW] All caches cleared'));
  }
});

console.log('[SW] Service worker loaded');
