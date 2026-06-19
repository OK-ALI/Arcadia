// Set of file extensions to intercept
const INTERCEPT_EXTENSIONS = new Set([
    'zip', 'rar', '7z', 'tar', 'gz', 'exe', 'msi', 'iso', 'dmg', 'pkg', 'torrent'
]);

const INTERCEPT_MIME_TYPES = new Set([
    'application/octet-stream',
    'application/x-bittorrent',
    'application/zip',
    'application/x-zip-compressed',
    'application/x-rar-compressed',
    'application/vnd.rar',
    'application/x-7z-compressed',
    'application/x-msdownload',
    'application/x-msi',
    'application/x-iso9660-image'
]);

// Hostnames to intercept (matches host and all subdomains)
const INTERCEPT_HOSTS = [
    'datanodes.to',
    'gofile.io',
    'buzzheavier.com',
    'pixeldrain.com',
    'krakenfiles.com',
    'doodrive.com'
];

const LOCAL_CAPTURE_ENDPOINT = 'http://127.0.0.1:5000/api/app/focus';
const CAPTURED_DOWNLOAD_IDS_LIMIT = 200;
const CAPTURED_DOWNLOAD_URLS_LIMIT = 200;
const EXTENSION_START_TIME = Date.now();
const STARTUP_HISTORY_GRACE_MS = 5000;
const createdDownloadIds = new Set();
const capturedDownloadIds = new Set();
const capturedDownloadUrls = new Map();

function rememberCreatedDownload(id) {
    if (id === undefined || id === null) return;
    createdDownloadIds.add(id);
    while (createdDownloadIds.size > CAPTURED_DOWNLOAD_IDS_LIMIT) {
        createdDownloadIds.delete(createdDownloadIds.values().next().value);
    }
}

function rememberCapturedDownload(id) {
    if (id === undefined || id === null) return;
    capturedDownloadIds.add(id);
    while (capturedDownloadIds.size > CAPTURED_DOWNLOAD_IDS_LIMIT) {
        capturedDownloadIds.delete(capturedDownloadIds.values().next().value);
    }
}

function wasCaptured(id) {
    return capturedDownloadIds.has(id);
}

function wasCreatedThisSession(id) {
    return createdDownloadIds.has(id);
}

function downloadStartMs(item) {
    const value = item && item.startTime ? Date.parse(item.startTime) : NaN;
    return Number.isFinite(value) ? value : 0;
}

function isFreshSessionDownload(item, phase) {
    if (!item || item.id === undefined || item.id === null) return false;
    const state = String(item.state || '').toLowerCase();
    if (['complete', 'interrupted', 'cancelled', 'canceled'].includes(state)) {
        return false;
    }
    const startMs = downloadStartMs(item);
    if (startMs && startMs + 1000 < EXTENSION_START_TIME) {
        return false;
    }
    if (phase !== 'created' && !wasCreatedThisSession(item.id)) {
        return false;
    }
    if (phase !== 'created' && Date.now() - EXTENSION_START_TIME < STARTUP_HISTORY_GRACE_MS && startMs && startMs < EXTENSION_START_TIME) {
        return false;
    }
    return true;
}

function normalizeCaptureUrl(item) {
    return item.finalUrl || item.url || '';
}

function rememberCapturedUrl(url) {
    if (!url) return false;
    const now = Date.now();
    const previous = capturedDownloadUrls.get(url) || 0;
    capturedDownloadUrls.set(url, now);
    for (const [key, value] of capturedDownloadUrls) {
        if (capturedDownloadUrls.size <= CAPTURED_DOWNLOAD_URLS_LIMIT && now - value < 15000) break;
        if (capturedDownloadUrls.size > CAPTURED_DOWNLOAD_URLS_LIMIT || now - value >= 15000) {
            capturedDownloadUrls.delete(key);
        }
    }
    return previous && now - previous < 1200;
}

function shouldIntercept(item) {
    const url = item.url || '';
    
    // Ignore local files, browser extensions, or requests originating from Arcadia itself
    if (url.startsWith('chrome://') || url.startsWith('chrome-extension://') || url.startsWith('http://127.0.0.1:5000') || url.startsWith('http://localhost:5000')) {
        return false;
    }

    // 1. Check MIME type when the browser exposes it before the filename is final.
    const mime = (item.mime || '').toLowerCase().split(';', 1)[0].trim();
    if (INTERCEPT_MIME_TYPES.has(mime)) {
        return true;
    }

    // 2. Check tentative filename extension (best way, handles redirected files)
    const filename = item.filename || '';
    const extMatch = filename.match(/\.([a-zA-Z0-9]+)$/);
    if (extMatch) {
        const ext = extMatch[1].toLowerCase();
        if (INTERCEPT_EXTENSIONS.has(ext)) {
            return true;
        }
    }

    // 3. Check URL pathname extension
    try {
        const parsedUrl = new URL(item.finalUrl || url);
        const pathname = parsedUrl.pathname;
        const urlExtMatch = pathname.match(/\.([a-zA-Z0-9]+)$/);
        if (urlExtMatch) {
            const ext = urlExtMatch[1].toLowerCase();
            if (INTERCEPT_EXTENSIONS.has(ext)) {
                return true;
            }
        }

        // 4. Check hostname match
        const hostname = parsedUrl.hostname.toLowerCase();
        for (const host of INTERCEPT_HOSTS) {
            if (hostname === host || hostname.endsWith('.' + host)) {
                return true;
            }
        }
    } catch (e) {
        console.error("Arcadia Extension: URL parsing error:", e);
    }

    return false;
}

function captureDownload(item, phase) {
    if (!item || item.id === undefined || item.id === null || wasCaptured(item.id)) {
        return false;
    }

    if (!isFreshSessionDownload(item, phase)) {
        return false;
    }

    if (!shouldIntercept(item)) {
        return false;
    }

    rememberCapturedDownload(item.id);
    const url = item.finalUrl || item.url;
    if (rememberCapturedUrl(url)) {
        rememberCapturedDownload(item.id);
        return true;
    }
    chrome.downloads.cancel(item.id, () => {
        if (chrome.runtime.lastError) {
            console.warn("Arcadia Extension: Browser cancel warning:", chrome.runtime.lastError.message);
        }
    });

    console.log(`Arcadia Extension: Intercepted browser download during ${phase}:`, url);
    sendToArcadia(buildCapturePayload(item, phase));
    return true;
}

function buildCapturePayload(item, phase) {
    const url = normalizeCaptureUrl(item);
    return {
        url,
        original_url: item.url || url,
        final_url: item.finalUrl || url,
        filename: item.filename || '',
        mime: item.mime || '',
        referrer: item.referrer || '',
        source: 'extension',
        phase
    };
}

// Capture as early as possible so repeated downloads do not fall through to the browser.
chrome.downloads.onCreated.addListener((item) => {
    rememberCreatedDownload(item.id);
    captureDownload(item, 'created');
});

// Some hosts only expose filename, MIME type, or final URL after the download is created.
chrome.downloads.onChanged.addListener((delta) => {
    if (!delta || delta.id === undefined || delta.id === null || wasCaptured(delta.id)) {
        return;
    }
    const becameClassifiable = delta.filename || delta.mime || delta.url || delta.finalUrl;
    if (!becameClassifiable) {
        return;
    }
    chrome.downloads.search({ id: delta.id }, (items) => {
        if (chrome.runtime.lastError) {
            console.warn("Arcadia Extension: Download lookup warning:", chrome.runtime.lastError.message);
            return;
        }
        if (items && items[0] && wasCreatedThisSession(delta.id)) {
            captureDownload(items[0], 'changed');
        }
    });
});

// Keep filename determination as a fallback for redirects where the final filename reveals the file type.
chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
    if (wasCreatedThisSession(item.id)) {
        captureDownload(item, 'filename');
    }
    suggest();
});

async function sendToArcadia(payload) {
    const url = payload.url;
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2500 + attempt * 1000);
            const response = await fetch(LOCAL_CAPTURE_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            const data = await response.json().catch(() => ({}));
            if (data.success) {
                console.log("Arcadia Extension: Sent capture to Arcadia client.");
                return;
            }
            console.warn("Arcadia Extension API warning:", data.error || data.message || 'not ready');
        } catch (err) {
            console.warn(`Arcadia Extension: Local capture attempt ${attempt} failed:`, err);
        }
        await new Promise(resolve => setTimeout(resolve, 350 * attempt));
    }
    console.warn("Arcadia Extension: Local client is offline. Triggering custom protocol fallback.");
    triggerProtocolLaunch(url);
}

async function legacySendToArcadia(url) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const response = await fetch(LOCAL_CAPTURE_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        const data = await response.json().catch(() => ({}));
        if (data.success) {
            console.log("Arcadia Extension: Sent capture to Arcadia client.");
        } else {
            console.error("Arcadia Extension API error:", data.error);
            triggerProtocolLaunch(url);
        }
    } catch (err) {
        console.warn("Arcadia Extension: Local client is offline. Triggering custom protocol fallback:", err);
        triggerProtocolLaunch(url);
    }
}

function triggerProtocolLaunch(url) {
    const protocolUrl = `arcadia://add-url?url=${encodeURIComponent(url)}`;
    
    // Attempt to navigate the current active tab to register protocol
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].id && tabs[0].url && !tabs[0].url.startsWith('chrome://') && !tabs[0].url.startsWith('edge://')) {
            chrome.tabs.update(tabs[0].id, { url: protocolUrl });
        } else {
            // Fallback: open a temporary tab in the background to execute
            chrome.tabs.create({ url: protocolUrl, active: false }, (tab) => {
                setTimeout(() => {
                    chrome.tabs.remove(tab.id);
                }, 1500);
            });
        }
    });
}
