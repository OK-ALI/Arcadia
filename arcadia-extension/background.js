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
const capturedDownloadIds = [];

function rememberCapturedDownload(id) {
    if (id === undefined || id === null) return;
    capturedDownloadIds.push(id);
    while (capturedDownloadIds.length > CAPTURED_DOWNLOAD_IDS_LIMIT) {
        capturedDownloadIds.shift();
    }
}

function wasCaptured(id) {
    return capturedDownloadIds.includes(id);
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

    if (!shouldIntercept(item)) {
        return false;
    }

    rememberCapturedDownload(item.id);
    const url = item.finalUrl || item.url;
    chrome.downloads.cancel(item.id, () => {
        if (chrome.runtime.lastError) {
            console.warn("Arcadia Extension: Browser cancel warning:", chrome.runtime.lastError.message);
        }
    });

    console.log(`Arcadia Extension: Intercepted browser download during ${phase}:`, url);
    sendToArcadia(url);
    return true;
}

// Capture as early as possible so repeated downloads do not fall through to the browser.
chrome.downloads.onCreated.addListener((item) => {
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
        if (items && items[0]) {
            captureDownload(items[0], 'changed');
        }
    });
});

// Keep filename determination as a fallback for redirects where the final filename reveals the file type.
chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
    captureDownload(item, 'filename');
    suggest();
});

async function sendToArcadia(url) {
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
