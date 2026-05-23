// Set of file extensions to intercept
const INTERCEPT_EXTENSIONS = new Set([
    'zip', 'rar', '7z', 'tar', 'gz', 'exe', 'msi', 'iso', 'dmg', 'pkg', 'torrent'
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

function shouldIntercept(item) {
    const url = item.url || '';
    
    // Ignore local files, browser extensions, or requests originating from Arcadia itself
    if (url.startsWith('chrome://') || url.startsWith('chrome-extension://') || url.startsWith('http://127.0.0.1:5000')) {
        return false;
    }

    // 1. Check tentative filename extension (best way, handles redirected files)
    const filename = item.filename || '';
    const extMatch = filename.match(/\.([a-zA-Z0-9]+)$/);
    if (extMatch) {
        const ext = extMatch[1].toLowerCase();
        if (INTERCEPT_EXTENSIONS.has(ext)) {
            return true;
        }
    }

    // 2. Check URL pathname extension
    try {
        const parsedUrl = new URL(url);
        const pathname = parsedUrl.pathname;
        const urlExtMatch = pathname.match(/\.([a-zA-Z0-9]+)$/);
        if (urlExtMatch) {
            const ext = urlExtMatch[1].toLowerCase();
            if (INTERCEPT_EXTENSIONS.has(ext)) {
                return true;
            }
        }

        // 3. Check hostname match
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

// Intercept the download during filename determination
chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
    if (shouldIntercept(item)) {
        // Cancel the browser's download
        chrome.downloads.cancel(item.id);
        
        // Finalize the determination (required to prevent freezing)
        suggest();

        console.log("Arcadia Extension: Intercepted and cancelled browser download:", item.url);

        // Send to Arcadia Core API asynchronously
        sendToArcadia(item.url);
    } else {
        // Let normal browser downloads proceed
        suggest();
    }
});

async function sendToArcadia(url) {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/app/focus', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });
        const data = await response.json();
        if (data.success) {
            console.log("Arcadia Extension: Sent capture to Arcadia client.");
        } else {
            console.error("Arcadia Extension API error:", data.error);
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
