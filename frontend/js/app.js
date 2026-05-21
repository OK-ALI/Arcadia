/**
 * app.js - Main frontend orchestration for Arcadia Core.
 */

document.addEventListener('DOMContentLoaded', () => {
    const STORAGE = {
        wishlist: 'arcadia_wishlist',
        wishlistGames: 'arcadia_wishlist_games',
        searchHistory: 'arcadia_search_history',
        sidebarCollapsed: 'arcadia_sidebar_collapsed',
        sidebarWidth: 'arcadia_sidebar_width',
        theme: 'arcadia_theme'
    };

    const state = {
        currentPage: 1,
        currentQuery: '',
        searchPage: 1,
        activeView: 'home',
        searchHistory: [],
        compatibilityOnly: false,
        downloadsPoller: null,
        newsPoller: null,
        newsFilter: 'All',
        lastPreparedDownload: null,
        galleryGames: [],
        galleryLetter: 'all',
        galleryPage: 1,
        galleryTotalPages: 1,
        galleryIndexerPoller: null,
        galleryArtworkPoller: null,
        galleryRequirementsLoading: false,
        preparePoller: null,
        lastDownloadData: null
    };

    window.userSpecs = {
        cpu: 'Scanning CPU...',
        ram: 0,
        ram_gb: 0,
        gpu_vram_gb: 0,
        gpu: 'Scanning GPU...',
        drives: []
    };

    const elements = {
        sidebar: document.getElementById('app-sidebar'),
        sidebarToggle: document.getElementById('btn-sidebar-toggle'),
        sidebarResizer: document.getElementById('sidebar-resizer'),
        navHome: document.getElementById('nav-home'),
        navGallery: document.getElementById('nav-gallery'),
        navNews: document.getElementById('nav-news'),
        navWishlist: document.getElementById('nav-wishlist'),
        navDownloads: document.getElementById('nav-downloads'),
        navDownloadBadge: document.getElementById('nav-download-badge'),
        navCatalog: document.getElementById('nav-catalog'),
        navHistory: document.getElementById('nav-search-history'),
        navUpcoming: document.getElementById('nav-upcoming'),
        btnClearCache: document.getElementById('btn-clear-cache'),
        searchInput: document.getElementById('search-input'),
        btnClearSearch: document.getElementById('btn-clear-search'),
        themeToggle: document.getElementById('btn-theme-toggle'),
        toggleCompatibility: document.getElementById('toggle-compatibility'),
        popularContainer: document.getElementById('popular-container'),
        latestContainer: document.getElementById('latest-repacks-container'),
        upcomingContainer: document.getElementById('upcoming-container'),
        galleryContainer: document.getElementById('gallery-container'),
        btnGalleryRefresh: document.getElementById('btn-gallery-refresh'),
        galleryLetterFilter: document.getElementById('gallery-letter-filter'),
        galleryIndexPanel: document.getElementById('gallery-index-panel'),
        galleryIndexMessage: document.getElementById('gallery-index-message'),
        galleryIndexCount: document.getElementById('gallery-index-count'),
        galleryIndexProgressFill: document.getElementById('gallery-index-progress-fill'),
        btnGalleryPrev: document.getElementById('btn-gallery-prev'),
        btnGalleryNext: document.getElementById('btn-gallery-next'),
        galleryCurrentPage: document.getElementById('gallery-current-page'),
        galleryTotalPages: document.getElementById('gallery-total-pages'),
        newsContainer: document.getElementById('news-container'),
        newsUpdatedAt: document.getElementById('news-updated-at'),
        newsTabs: document.getElementById('news-tabs'),
        btnNewsRefresh: document.getElementById('btn-news-refresh'),
        upcomingGamesNews: document.getElementById('upcoming-games-news'),
        upcomingEventsNews: document.getElementById('upcoming-events-news'),
        viewHome: document.getElementById('view-home'),
        viewGallery: document.getElementById('view-gallery'),
        viewNews: document.getElementById('view-news'),
        viewSearch: document.getElementById('view-search'),
        viewWishlist: document.getElementById('view-wishlist'),
        viewDownloads: document.getElementById('view-downloads'),
        viewCatalog: document.getElementById('view-catalog'),
        wishlistContainer: document.getElementById('wishlist-container'),
        wishlistSavings: document.getElementById('wishlist-savings-panel'),
        downloadsList: document.getElementById('downloads-list'),
        downloadsEngineAlert: document.getElementById('downloads-engine-alert'),
        btnDownloadsPauseAll: document.getElementById('btn-downloads-pause-all'),
        btnDownloadsResumeAll: document.getElementById('btn-downloads-resume-all'),
        btnDownloadsClearCompleted: document.getElementById('btn-downloads-clear-completed'),
        downloadMaxActive: document.getElementById('download-max-active'),
        downloadDefaultPath: document.getElementById('download-default-path'),
        btnBrowseDownloadPath: document.getElementById('btn-browse-download-path'),
        downloadLimit: document.getElementById('download-limit'),
        uploadLimit: document.getElementById('upload-limit'),
        btnSaveDownloadSettings: document.getElementById('btn-save-download-settings'),
        catalogContainer: document.getElementById('catalog-container'),
        offlineStatsGrid: document.getElementById('offline-stats-grid'),
        btnExportOffline: document.getElementById('btn-export-offline'),
        btnPruneMedia: document.getElementById('btn-prune-media'),
        btnPrevPage: document.getElementById('btn-prev-page'),
        btnNextPage: document.getElementById('btn-next-page'),
        pageIndicator: document.getElementById('current-page'),
        searchQueryHighlight: document.getElementById('search-query-highlight'),
        searchResultsContainer: document.getElementById('search-results-container'),
        btnBackHome: document.getElementById('btn-back-home'),
        btnSearchPrev: document.getElementById('btn-search-prev'),
        btnSearchNext: document.getElementById('btn-search-next'),
        searchPageIndicator: document.getElementById('search-current-page'),
        gameModal: document.getElementById('game-modal'),
        modalContentBody: document.getElementById('modal-content-body'),
        btnModalClose: document.getElementById('btn-modal-close'),
        confirmModal: document.getElementById('confirm-modal'),
        confirmIcon: document.getElementById('confirm-icon'),
        confirmTitle: document.getElementById('confirm-title'),
        confirmMessage: document.getElementById('confirm-message'),
        btnConfirmCancel: document.getElementById('btn-confirm-cancel'),
        btnConfirmOk: document.getElementById('btn-confirm-ok'),
        sysCpu: document.getElementById('sys-cpu'),
        sysRam: document.getElementById('sys-ram'),
        sysGpu: document.getElementById('sys-gpu'),
        sysDrives: document.getElementById('sys-drives-box'),
        pingStatus: document.getElementById('ping-status-indicator')
    };

    function readJSON(key, fallback) {
        try {
            return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
        } catch {
            return fallback;
        }
    }

    function applyTheme(theme) {
        const nextTheme = theme === 'light-mode' ? 'light-mode' : 'dark-mode';
        const isLight = nextTheme === 'light-mode';
        document.body.classList.toggle('light-mode', isLight);
        document.body.classList.toggle('dark-mode', !isLight);
        localStorage.setItem(STORAGE.theme, nextTheme);

        if (elements.themeToggle) {
            elements.themeToggle.innerHTML = `<i class="fa-solid ${isLight ? 'fa-moon' : 'fa-sun'}"></i>`;
            elements.themeToggle.title = 'Toggle theme';
            elements.themeToggle.setAttribute('aria-label', 'Toggle theme');
            elements.themeToggle.setAttribute('data-theme', nextTheme);
        }
    }

    function initTheme() {
        applyTheme(localStorage.getItem(STORAGE.theme) || 'dark-mode');
    }


    function setSidebarWidth(width) {
        const next = Math.max(210, Math.min(380, Number(width) || 250));
        document.documentElement.style.setProperty('--sidebar-width', `${next}px`);
        localStorage.setItem(STORAGE.sidebarWidth, String(next));
    }

    function initSidebarResize() {
        const saved = Number(localStorage.getItem(STORAGE.sidebarWidth) || 250);
        setSidebarWidth(saved);
        if (!elements.sidebarResizer) return;
        let resizing = false;
        elements.sidebarResizer.addEventListener('mousedown', e => {
            if (elements.sidebar.classList.contains('collapsed')) return;
            resizing = true;
            document.body.classList.add('sidebar-resizing');
            e.preventDefault();
        });
        window.addEventListener('mousemove', e => {
            if (!resizing) return;
            setSidebarWidth(e.clientX);
        });
        window.addEventListener('mouseup', () => {
            if (!resizing) return;
            resizing = false;
            document.body.classList.remove('sidebar-resizing');
        });
    }
    function migrateStorage() {
        const mappings = [
            ['fg_wishlist', STORAGE.wishlist],
            ['fg_wishlist_games', STORAGE.wishlistGames],
            ['fg_search_history', STORAGE.searchHistory]
        ];
        mappings.forEach(([oldKey, newKey]) => {
            if (!localStorage.getItem(newKey) && localStorage.getItem(oldKey)) {
                localStorage.setItem(newKey, localStorage.getItem(oldKey));
            }
        });
        state.searchHistory = readJSON(STORAGE.searchHistory, []);
    }

    function escapeHTML(value) {
        return Components.escape(value);
    }

    async function chooseFolder(initialPath = '') {
        try {
            if (window.pywebview?.api?.choose_folder) {
                return await window.pywebview.api.choose_folder(initialPath || '');
            }
        } catch {
            // Manual path typing remains available when native bridge is unavailable.
        }
        return '';
    }

    function showConfirmDialog({ title, message, confirmText = 'Confirm', danger = false }) {
        return new Promise(resolve => {
            if (!elements.confirmModal) {
                resolve(window.confirm(message));
                return;
            }
            elements.confirmTitle.textContent = title;
            elements.confirmMessage.textContent = message;
            elements.btnConfirmOk.textContent = confirmText;
            elements.btnConfirmOk.classList.toggle('btn-danger', danger);
            elements.confirmIcon.classList.toggle('danger', danger);
            elements.confirmModal.classList.add('active');

            const close = value => {
                elements.confirmModal.classList.remove('active');
                elements.btnConfirmCancel.removeEventListener('click', onCancel);
                elements.btnConfirmOk.removeEventListener('click', onOk);
                elements.confirmModal.removeEventListener('click', onBackdrop);
                resolve(value);
            };
            const onCancel = () => close(false);
            const onOk = () => close(true);
            const onBackdrop = event => {
                if (event.target === elements.confirmModal) close(false);
            };
            elements.btnConfirmCancel.addEventListener('click', onCancel);
            elements.btnConfirmOk.addEventListener('click', onOk);
            elements.confirmModal.addEventListener('click', onBackdrop);
        });
    }

    function formatBytes(bytes) {
        const value = Number(bytes) || 0;
        if (value <= 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const idx = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
        return `${(value / Math.pow(1024, idx)).toFixed(idx >= 3 ? 2 : 1)} ${units[idx]}`;
    }

    function formatSpeed(bytes) {
        return `${formatBytes(bytes)}/s`;
    }

    function updateNavDownloadBadge(downloads = []) {
        if (!elements.navDownloadBadge) return;
        const active = downloads.filter(item => ['downloading', 'queued', 'metadata', 'checking', 'paused'].includes(item.status || ''));
        if (!active.length) {
            elements.navDownloadBadge.classList.remove('active');
            elements.navDownloadBadge.textContent = '0%';
            elements.navDownloads?.removeAttribute('data-download-progress');
            return;
        }
        const totals = active.reduce((acc, item) => {
            acc.done += Number(item.completed_length || 0);
            acc.total += Number(item.total_length || 0);
            acc.speed += Number(item.download_speed || 0);
            return acc;
        }, { done: 0, total: 0, speed: 0 });
        const pct = totals.total > 0 ? Math.min(100, Math.round((totals.done / totals.total) * 100)) : 0;
        elements.navDownloadBadge.textContent = totals.total > 0 ? `${pct}%` : active.length.toString();
        elements.navDownloadBadge.classList.add('active');
        elements.navDownloads?.setAttribute('data-download-progress', `${active.length} active · ${totals.total > 0 ? `${pct}%` : 'metadata'} · ${formatSpeed(totals.speed)}`);
    }
    function formatEta(done, total, speed) {
        if (!speed || !total || done >= total) return '--';
        const seconds = Math.max(0, Math.round((total - done) / speed));
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        if (hrs > 0) return `${hrs}h ${mins}m`;
        return `${mins}m`;
    }

    function showSkeleton(container, count = 10) {
        if (!container) return;
        container.innerHTML = '';
        for (let i = 0; i < count; i++) container.appendChild(Components.createSkeletonCard());
    }

    function mergeGames(...lists) {
        const seen = new Set();
        const merged = [];
        lists.flat().forEach(game => {
            if (game?.slug && !seen.has(game.slug)) {
                seen.add(game.slug);
                merged.push(game);
            }
        });
        return merged;
    }

    function parseSizeGB(sizeStr) {
        const matches = String(sizeStr || '').match(/(\d+(?:\.\d+)?)\s*(GB|MB)/i);
        if (!matches) return 0;
        let val = parseFloat(matches[1]);
        return matches[2].toUpperCase() === 'MB' ? val / 1024 : val;
    }

    async function loadDiagnostics() {
        try {
            const specs = await API.getSystemSpecs();
            window.userSpecs.cpu = specs.cpu || 'Unknown CPU';
            window.userSpecs.ram = parseInt(specs.ram_installed_gb ?? specs.ram_gb ?? specs.ram, 10) || 0;
            window.userSpecs.ram_gb = window.userSpecs.ram;
            window.userSpecs.ram_usable_gb = parseInt(specs.ram_usable_gb, 10) || window.userSpecs.ram;
            window.userSpecs.gpu = specs.gpu || 'Unknown GPU';
            window.userSpecs.gpu_vram_gb = Number(specs.gpu_vram_gb || 0);
            elements.sysCpu.textContent = window.userSpecs.cpu;
            elements.sysRam.textContent = `${window.userSpecs.ram || '?'} GB RAM`;
            if (window.userSpecs.ram_usable_gb && window.userSpecs.ram_usable_gb !== window.userSpecs.ram) {
                elements.sysRam.textContent = `${window.userSpecs.ram} GB RAM (${window.userSpecs.ram_usable_gb} GB usable)`;
            }
            elements.sysGpu.textContent = `${window.userSpecs.gpu}${window.userSpecs.gpu_vram_gb ? ` (${window.userSpecs.gpu_vram_gb} GB VRAM)` : ''}`;
            elements.sysCpu.parentNode.title = window.userSpecs.cpu;
            elements.sysRam.parentNode.title = `${window.userSpecs.ram} GB installed, ${window.userSpecs.ram_usable_gb} GB usable`;
            elements.sysGpu.parentNode.title = elements.sysGpu.textContent;
        } catch (err) {
            console.error('Failed to load specs:', err);
            elements.sysCpu.textContent = 'Error scanning CPU';
            elements.sysRam.textContent = 'Error scanning RAM';
            elements.sysGpu.textContent = 'Error scanning GPU';
        }
        await loadDrivesInfo();
    }

    async function loadDrivesInfo() {
        try {
            const drives = await API.getDrivesInfo();
            window.userSpecs.drives = drives || [];
            elements.sysDrives.innerHTML = '';
            window.userSpecs.drives.forEach(drive => {
                const usagePercent = Math.round(((drive.total_gb - drive.free_gb) / drive.total_gb) * 100);
                const barClass = usagePercent >= 90 ? 'critical' : usagePercent >= 75 ? 'warning' : '';
                const driveItem = document.createElement('div');
                driveItem.className = 'drive-progress-item';
                driveItem.innerHTML = `
                    <div class="drive-labels">
                        <span class="drive-name">${escapeHTML(drive.name)}</span>
                        <span>${escapeHTML(drive.free_gb)} GB free</span>
                    </div>
                    <div class="drive-bar-bg">
                        <div class="drive-bar-fill ${barClass}" style="width: ${usagePercent}%"></div>
                    </div>
                `;
                elements.sysDrives.appendChild(driveItem);
            });
        } catch (err) {
            console.error('Failed to load drives:', err);
            elements.sysDrives.innerHTML = '<div style="color:var(--text-muted); font-size:10px;">Drives scan failed</div>';
        }
    }

    async function startPingMonitor() {
        const checkPing = async () => {
            try {
                const status = await API.getPingStatus();
                elements.pingStatus.innerHTML = status.online
                    ? `<span class="status-dot online"></span><span class="status-text text-green">Online (${status.latency} ms)</span>`
                    : '<span class="status-dot offline"></span><span class="status-text text-pink">Offline Mode</span>';
            } catch {
                elements.pingStatus.innerHTML = '<span class="status-dot offline"></span><span class="status-text text-pink">Offline Mode</span>';
            }
        };
        await checkPing();
        setInterval(checkPing, 15000);
    }

    function filterCompatibility(games) {
        if (!state.compatibilityOnly) return games;
        return games.filter(game => {
            const comp = Components.getCompatibility(game.requirements);
            return comp && ['pass', 'minimum'].includes(comp.status);
        });
    }

    function renderCards(container, games, emptyText) {
        container.innerHTML = '';
        const filtered = filterCompatibility(games);
        if (!filtered.length) {
            const hasPendingSpecs = state.compatibilityOnly && games.some(game => game.requirements?.pending);
            const text = hasPendingSpecs ? 'Checking accurate system requirements for this page...' : emptyText;
            container.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><p>${escapeHTML(text)}</p></div>`;
            return;
        }
        filtered.forEach(game => {
            const card = Components.createGameCard(game);
            card.addEventListener('click', () => openGameDetails(game.slug));
            container.appendChild(card);
        });
    }

    async function loadHomepage() {
        API.getPopular().then(data => {
            elements.popularContainer.innerHTML = '';
            const games = filterCompatibility(data || []);
            if (!games.length) {
                elements.popularContainer.innerHTML = '<div class="empty-state">No popular games found</div>';
                return;
            }
            games.forEach(item => {
                const card = Components.createPopularCard(item);
                card.addEventListener('click', () => openGameDetails(item.slug));
                elements.popularContainer.appendChild(card);
            });
        }).catch(() => {
            elements.popularContainer.innerHTML = '<div class="empty-state">Failed to load popular list</div>';
        });

        API.getUpcoming().then(data => {
            elements.upcomingContainer.innerHTML = '';
            (data || []).forEach(item => elements.upcomingContainer.appendChild(Components.createUpcomingItem(item)));
            if (!data?.length) elements.upcomingContainer.innerHTML = '<div class="empty-state">No upcoming games found</div>';
        }).catch(() => {
            elements.upcomingContainer.innerHTML = '<div class="empty-state">Failed to load upcoming games</div>';
        });

        await loadLatestRepacks();
    }

    async function loadLatestRepacks() {
        showSkeleton(elements.latestContainer, 10);
        try {
            const data = await API.getLatest(state.currentPage);
            renderCards(elements.latestContainer, data.games || [], 'No games found on this page.');
            state.hasLatestNext = data.has_next;
            elements.pageIndicator.textContent = state.currentPage;
            elements.btnPrevPage.disabled = state.currentPage <= 1;
            elements.btnNextPage.disabled = !data.has_next;
        } catch {
            elements.latestContainer.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>Failed to load latest games.</p></div>';
            elements.btnPrevPage.disabled = true;
            elements.btnNextPage.disabled = true;
        }
    }

    async function executeSearch() {
        if (!state.currentQuery) return;
        showSkeleton(elements.searchResultsContainer, 10);
        switchView('search');
        elements.searchQueryHighlight.textContent = `"${state.currentQuery}"`;
        try {
            const data = await API.search(state.currentQuery, state.searchPage);
            renderCards(elements.searchResultsContainer, data.games || [], 'No games match this query.');
            state.hasSearchNext = data.has_next;
            elements.searchPageIndicator.textContent = state.searchPage;
            elements.btnSearchPrev.disabled = state.searchPage <= 1;
            elements.btnSearchNext.disabled = !data.has_next;
        } catch {
            const fallback = await searchOfflineCatalogLocally(state.currentQuery);
            renderCards(elements.searchResultsContainer, fallback, 'No offline games match this query.');
        }
    }

    async function searchOfflineCatalogLocally(query) {
        try {
            const data = await API.getOfflineCatalog();
            return filterCompatibility((data.games || []).filter(g => g.title?.toLowerCase().includes(query.toLowerCase())));
        } catch {
            return [];
        }
    }

    function renderGalleryLetters() {
        if (!elements.galleryLetterFilter || elements.galleryLetterFilter.dataset.ready) return;
        const letters = ['all', '0-9', ...'abcdefghijklmnopqrstuvwxyz'.split('')];
        elements.galleryLetterFilter.innerHTML = letters.map(letter => `
            <button class="az-chip ${letter === state.galleryLetter ? 'active' : ''}" data-letter="${letter}">${letter === 'all' ? 'All' : letter.toUpperCase()}</button>
        `).join('');
        elements.galleryLetterFilter.dataset.ready = '1';
        elements.galleryLetterFilter.addEventListener('click', e => {
            const btn = e.target.closest('.az-chip');
            if (!btn) return;
            state.galleryLetter = btn.dataset.letter;
            state.galleryPage = 1;
            elements.galleryLetterFilter.querySelectorAll('.az-chip').forEach(chip => chip.classList.toggle('active', chip === btn));
            loadGallery(false);
        });
    }

    function renderGalleryIndexStatus(status = {}) {
        if (!elements.galleryIndexPanel) return;
        const total = status.total || 0;
        const page = status.page || 0;
        const max = status.max_pages || 140;
        const pct = status.done ? 100 : Math.min(100, Math.round((page / Math.max(1, max)) * 100));
        const artworkCached = status.artwork_cached || 0;
        elements.galleryIndexMessage.textContent = status.message || (status.running ? 'Building A-Z catalog index' : 'Catalog index ready');
        elements.galleryIndexCount.textContent = `${total} games indexed · artwork cached ${artworkCached}/${total}${status.running ? ` · page ${page}` : ''}`;
        if (elements.galleryIndexProgressFill) elements.galleryIndexProgressFill.style.width = `${pct}%`;
        elements.galleryIndexPanel.classList.toggle('running', !!status.running);
        elements.galleryIndexPanel.classList.toggle('error', !!status.error);
    }


    function renderGalleryArtworkStatus(status = {}) {
        if (!elements.galleryIndexPanel || !status.message) return;
        const indexed = status.indexed || state.galleryGames.length || 0;
        const cached = status.cached || 0;
        if (status.running || status.updated) {
            elements.galleryIndexMessage.textContent = status.running ? status.message : 'Artwork cache updated';
            elements.galleryIndexCount.textContent = `${indexed} games indexed · artwork cached ${cached}/${indexed} · current batch ${status.processed || 0}/${status.total || 0}`;
            if (elements.galleryIndexProgressFill && indexed) {
                elements.galleryIndexProgressFill.style.width = `${Math.min(100, Math.max(status.percent || 0, 2))}%`;
            }
        }
    }

    async function pollGalleryArtwork() {
        try {
            const status = await API.getLibraryArtworkStatus();
            renderGalleryArtworkStatus(status);
            if (!status.running) {
                if (state.galleryArtworkPoller) {
                    clearInterval(state.galleryArtworkPoller);
                    state.galleryArtworkPoller = null;
                }
                if ((status.updated || 0) > 0) await loadGallery(false);
            }
        } catch {
            // Artwork hydration is progressive; cards can still use fallback art.
        }
    }

    async function startGalleryArtworkHydration(games = []) {
        try {
            const missingVisibleSlugs = games
                .filter(game => game.slug && !game.thumbnail && !game.cover)
                .map(game => game.slug);
            const status = await API.startLibraryArtwork(144, missingVisibleSlugs);
            renderGalleryArtworkStatus(status);
            if (!state.galleryArtworkPoller) state.galleryArtworkPoller = setInterval(pollGalleryArtwork, 3500);
        } catch {
            // Leave fallback images in place if artwork loading fails.
        }
    }

    async function hydrateVisibleGalleryRequirements(games = []) {
        if (state.galleryRequirementsLoading) return;
        const slugs = games
            .filter(game => game.slug && game.requirements?.pending)
            .map(game => game.slug)
            .slice(0, 24);
        if (!slugs.length) return;
        state.galleryRequirementsLoading = true;
        try {
            const data = await API.hydrateLibraryRequirements(slugs, slugs.length);
            const requirements = data.requirements || {};
            state.galleryGames = state.galleryGames.map(game => (
                requirements[game.slug] ? { ...game, requirements: requirements[game.slug] } : game
            ));
            renderCards(elements.galleryContainer, state.galleryGames, 'No compatible games match after checking accurate requirements.');
        } catch {
            // Keep pending badges if detailed requirement scraping fails.
        } finally {
            state.galleryRequirementsLoading = false;
        }
    }

    async function pollGalleryIndex() {
        try {
            const status = await API.getLibraryIndexStatus();
            renderGalleryIndexStatus(status);
            if (!status.running && state.galleryIndexerPoller) {
                clearInterval(state.galleryIndexerPoller);
                state.galleryIndexerPoller = null;
                await loadGallery(false);
            }
        } catch {
            // Progress is helpful, not critical.
        }
    }

    async function loadGallery(force = false) {
        renderGalleryLetters();
        showSkeleton(elements.galleryContainer, 12);
        try {
            if (force) {
                await API.startLibraryIndex(true);
                if (!state.galleryIndexerPoller) state.galleryIndexerPoller = setInterval(pollGalleryIndex, 2500);
            }
            const data = await API.getLibrary(state.galleryLetter, state.galleryPage, 24);
            state.galleryGames = data.games || [];
            state.galleryPage = data.page || state.galleryPage;
            state.galleryTotalPages = data.total_pages || 1;
            renderGalleryIndexStatus(data.indexing || {});
            renderGalleryArtworkStatus(data.artwork || {});
            renderCards(elements.galleryContainer, state.galleryGames, 'No games match this gallery page yet. The index may still be loading.');
            hydrateVisibleGalleryRequirements(state.galleryGames);
            if (state.galleryGames.some(game => !game.thumbnail && !game.cover)) startGalleryArtworkHydration(state.galleryGames);
            if (elements.galleryCurrentPage) elements.galleryCurrentPage.textContent = state.galleryPage;
            if (elements.galleryTotalPages) elements.galleryTotalPages.textContent = state.galleryTotalPages;
            if (elements.btnGalleryPrev) elements.btnGalleryPrev.disabled = !data.has_prev;
            if (elements.btnGalleryNext) elements.btnGalleryNext.disabled = !data.has_next;
            if (force) Components.showToast('Games Gallery refresh started.', 'success');
        } catch (err) {
            elements.galleryContainer.innerHTML = `<div class="empty-state"><p>Failed to load gallery: ${escapeHTML(err.message)}</p></div>`;
        }
    }

    function renderSourceLinks(container, items) {
        container.innerHTML = (items || []).map(item => `
            <a class="source-link-item" href="${escapeHTML(item.url)}" target="_blank">
                <span><strong>${escapeHTML(item.title)}</strong><small>${escapeHTML(item.source)} Â· ${escapeHTML(item.category)}</small></span>
                <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
        `).join('');
    }

    async function loadNews(force = false) {
        if (!elements.newsContainer) return;
        elements.newsContainer.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading live gaming news...</p></div>';
        try {
            const data = await API.getNews(force);
            const updated = data.updated_at ? new Date(data.updated_at * 1000) : null;
            elements.newsUpdatedAt.textContent = updated ? `${data.stale ? 'Cached' : 'Updated'} ${updated.toLocaleTimeString()}` : 'Not updated';
            renderSourceLinks(elements.upcomingGamesNews, data.upcoming_games || []);
            renderSourceLinks(elements.upcomingEventsNews, data.upcoming_events || []);
            const articles = (data.articles || []).filter(item => {
                if (state.newsFilter === 'All') return true;
                if (state.newsFilter === 'Official') return item.is_official || item.category === 'Official';
                return item.category === state.newsFilter;
            });
            elements.newsContainer.innerHTML = '';
            if (!articles.length) {
                elements.newsContainer.innerHTML = '<div class="empty-state"><p>No articles match this filter yet.</p></div>';
                return;
            }
            articles.forEach(item => elements.newsContainer.appendChild(Components.createNewsCard(item)));
        } catch (err) {
            elements.newsContainer.innerHTML = `<div class="empty-state"><p>News refresh failed: ${escapeHTML(err.message)}</p></div>`;
        }
    }

    function startNewsPolling() {
        if (state.newsPoller) clearInterval(state.newsPoller);
        state.newsPoller = setInterval(() => {
            if (state.activeView === 'news') loadNews(false);
        }, 15 * 60 * 1000);
    }

    async function openGameDetails(slug) {
        elements.modalContentBody.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading game details...</p></div>';
        elements.gameModal.classList.add('active');
        try {
            let game = null;
            try {
                game = await API.getGameDetails(slug);
            } catch {
                const wlGames = readJSON(STORAGE.wishlistGames, []);
                game = wlGames.find(g => g.slug === slug);
                if (!game) {
                    const offlineData = await API.getOfflineCatalog();
                    game = (offlineData.games || []).find(g => g.slug === slug);
                }
            }
            if (!game) throw new Error('Game is not available offline.');
            elements.modalContentBody.innerHTML = Components.renderGameDetails(game);

            const dlBtn = document.getElementById('modal-download-btn');
            dlBtn?.addEventListener('click', async () => {
                dlBtn.disabled = true;
                dlBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparing...';
                try {
                    const prepared = await API.prepareDownload(slug);
                    renderPrepareDownloadModal(prepared);
                } catch (err) {
                    Components.showToast(`Failed to prepare built-in download: ${err.message}`, 'error');
                } finally {
                    dlBtn.disabled = false;
                    dlBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Download inside App';
                }
            });

            document.getElementById('modal-save-offline-btn')?.addEventListener('click', async e => {
                const btn = e.currentTarget;
                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
                try {
                    await API.saveGameOffline(slug);
                    Components.showToast('Saved for offline library.', 'success');
                } catch (err) {
                    Components.showToast(`Offline save failed: ${err.message}`, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-box-archive"></i> Save Offline';
                }
            });

            document.getElementById('modal-wishlist-btn')?.addEventListener('click', () => toggleWishlistItem(game));
            initCalculator(game);
        } catch (err) {
            elements.modalContentBody.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>Failed to load game details: ${escapeHTML(err.message)}</p></div>`;
        }
    }

    function initCalculator(game) {
        const speedVal = document.getElementById('calc-speed-val');
        const speedUnit = document.getElementById('calc-speed-unit');
        if (!speedVal || !speedUnit) return;
        const repackGB = parseSizeGB(game.repack_size);
        const originalGB = parseSizeGB(game.original_size);
        const formatTime = secs => {
            if (isNaN(secs) || secs <= 0) return '--';
            const hrs = Math.floor(secs / 3600);
            const mins = Math.floor((secs % 3600) / 60);
            return hrs > 0 ? `${hrs} hr ${mins} min` : `${mins} min`;
        };
        const updateCalc = () => {
            const val = parseFloat(speedVal.value) || 100;
            const speedMBs = speedUnit.value === 'Mbps' ? val / 8 : val;
            const repackSecs = (repackGB * 1024) / speedMBs;
            const originalSecs = (originalGB * 1024) / speedMBs;
            document.getElementById('calc-repack-time').textContent = formatTime(repackSecs);
            document.getElementById('calc-original-time').textContent = formatTime(originalSecs);
            const savingsSecs = originalSecs - repackSecs;
            if (savingsSecs > 60) {
                const compressionPct = originalGB > 0 ? Math.round(((originalGB - repackGB) / originalGB) * 100) : 0;
                document.getElementById('calc-savings-box').innerHTML = `<i class="fa-solid fa-bolt"></i> Estimated ${formatTime(savingsSecs)} saved (${compressionPct}% smaller). Real speed depends on seeders and network.`;
            }
        };
        speedVal.addEventListener('input', updateCalc);
        speedUnit.addEventListener('change', updateCalc);
        updateCalc();
    }

    function getSelectedIndexesFromModal() {
        return [...document.querySelectorAll('.file-select-checkbox:checked')].map(cb => cb.value);
    }

    function updatePreparedSelectionStats() {
        const prepared = state.lastPreparedDownload;
        if (!prepared) return;
        const selected = new Set(getSelectedIndexesFromModal());
        const files = prepared.files || [];
        const selectedBytes = files.reduce((sum, file) => selected.has(String(file.index)) ? sum + (Number(file.length) || 0) : sum, 0);
        const el = document.getElementById('prepared-selection-stats');
        if (el) el.textContent = `${selected.size} files selected - ${formatBytes(selectedBytes)}`;
    }

    function renderPrepareDownloadModal(prepared) {
        state.lastPreparedDownload = prepared;
        const files = prepared.files || [];
        const metadataReady = prepared.metadata_ready !== false && files.length > 0;
        const existing = prepared.existing || null;
        const defaultPath = prepared.save_path || (existing && existing.save_path) || '';
        const title = prepared.game?.title || prepared.title || 'Prepared Download';
        const selectedSet = new Set(files.filter(f => f.selected || ['Downloaded', 'Partial', 'Selected'].includes(f.state)).map(f => String(f.index)));
        const fileRows = files.map(file => {
            const checked = selectedSet.has(String(file.index)) ? 'checked' : '';
            const disabled = file.state === 'Downloaded' ? 'checked disabled' : checked;
            return `
                <label class="download-file-row" data-file-name="${escapeHTML(file.path).toLowerCase()}">
                    <input type="checkbox" class="file-select-checkbox" value="${escapeHTML(file.index)}" ${disabled}>
                    <span class="file-state ${String(file.state || 'not-selected').toLowerCase().replace(/\s+/g, '-')}">${escapeHTML(file.state || 'Not selected')}</span>
                    <span class="file-name" title="${escapeHTML(file.path)}">${escapeHTML(file.path || file.name || `File ${file.index}`)}</span>
                    <span class="file-size">${formatBytes(file.length)}</span>
                </label>
            `;
        }).join('');

        elements.modalContentBody.innerHTML = `
            <div class="prepare-download-modal">
                <div class="prepare-header">
                    <div>
                        <span class="hero-badge">${prepared.mode === 'update' ? 'UPDATE SELECTED FILES' : 'PREPARE DOWNLOAD'}</span>
                        <h2 class="modal-title">${escapeHTML(title)}</h2>
                        <p>${metadataReady ? 'Choose files before the real download starts. Arcadia Core keeps speed uncapped by default.' : 'Torrent metadata is still loading. Try preparing again in a moment.'}</p>
                    </div>
                    <div class="prepared-total" id="prepared-selection-stats">--</div>
                </div>
                ${prepared.engine && !prepared.engine.available ? '<div class="modal-alert-warning"><i class="fa-solid fa-triangle-exclamation"></i><span>Built-in downloader is not available. Reinstall app dependencies.</span></div>' : ''}
                ${!metadataReady ? '<div class="modal-alert-warning"><i class="fa-solid fa-spinner fa-spin"></i><span>Only torrent metadata placeholders were available. Real game files are not selectable yet.</span></div>' : ''}
                <div class="prepare-options-grid">
                    <label><span>Save folder</span><div class="path-input-row"><input id="prepare-save-path" type="text" value="${escapeHTML(defaultPath)}" placeholder="Download folder"><button class="icon-btn path-browse-btn" id="btn-browse-prepare-path" title="Browse save folder" type="button"><i class="fa-solid fa-folder-open"></i></button></div></label>
                    <label><span>Priority</span><select id="prepare-priority"><option>Urgent</option><option>High</option><option selected>Normal</option><option>Low</option><option>Paused</option></select></label>
                    <label><span>Queue</span><select id="prepare-queue-position"><option value="normal" selected>Normal position</option><option value="top">Top of queue</option></select></label>
                </div>
                <div class="file-toolbar">
                    <input id="file-filter-input" type="text" placeholder="Search files, language packs, optional extras...">
                    <button class="btn btn-secondary" id="btn-select-all-files"><i class="fa-solid fa-check-double"></i> All</button>
                    <button class="btn btn-secondary" id="btn-select-no-files"><i class="fa-regular fa-square"></i> None</button>
                    <button class="btn btn-secondary" id="btn-select-required-files"><i class="fa-solid fa-box"></i> Required</button>
                    <button class="btn btn-secondary" id="btn-select-language-files"><i class="fa-solid fa-language"></i> Languages</button>
                </div>
                <div class="download-file-list">${fileRows || '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Fetching torrent metadata.</p></div>'}</div>
                <div class="prepare-footer">
                    <button class="btn btn-secondary" id="btn-prepare-external"><i class="fa-solid fa-arrow-up-right-from-square"></i> External Client</button>
                    <button class="btn btn-primary" id="btn-confirm-prepared-download" ${metadataReady ? '' : 'disabled'}><i class="fa-solid fa-cloud-arrow-down"></i> Add Selected Files to Downloads</button>
                </div>
            </div>
        `;
        elements.gameModal.classList.add('active');

        document.querySelectorAll('.file-select-checkbox').forEach(cb => cb.addEventListener('change', updatePreparedSelectionStats));
        document.getElementById('btn-select-all-files')?.addEventListener('click', () => {
            document.querySelectorAll('.file-select-checkbox:not(:disabled)').forEach(cb => cb.checked = true);
            updatePreparedSelectionStats();
        });
        document.getElementById('btn-select-no-files')?.addEventListener('click', () => {
            document.querySelectorAll('.file-select-checkbox:not(:disabled)').forEach(cb => cb.checked = false);
            updatePreparedSelectionStats();
        });
        document.getElementById('btn-select-required-files')?.addEventListener('click', () => {
            document.querySelectorAll('.download-file-row').forEach(row => {
                const cb = row.querySelector('.file-select-checkbox');
                if (cb && !cb.disabled) {
                    const name = row.dataset.fileName || '';
                    cb.checked = !/(optional|bonus|ost|soundtrack|credits|wallpaper|artbook|language|voiceover|voice|fg-optional|fg-selective)/i.test(name);
                }
            });
            updatePreparedSelectionStats();
        });
        document.getElementById('btn-select-language-files')?.addEventListener('click', () => {
            document.querySelectorAll('.download-file-row').forEach(row => {
                const cb = row.querySelector('.file-select-checkbox');
                if (cb && !cb.disabled) cb.checked = /(language|voice|voiceover|english|french|german|spanish|italian|russian|polish|japanese|korean|chinese)/i.test(row.dataset.fileName || '');
            });
            updatePreparedSelectionStats();
        });
        document.getElementById('file-filter-input')?.addEventListener('input', e => {
            const query = e.target.value.trim().toLowerCase();
            document.querySelectorAll('.download-file-row').forEach(row => {
                row.style.display = !query || (row.dataset.fileName || '').includes(query) ? 'grid' : 'none';
            });
        });
        if (state.preparePoller) clearInterval(state.preparePoller);
        document.getElementById('btn-browse-prepare-path')?.addEventListener('click', async () => {
            const input = document.getElementById('prepare-save-path');
            const folder = await chooseFolder(input?.value || defaultPath);
            if (folder && input) input.value = folder;
        });
        if (!metadataReady && prepared.prepared_id) {
            const started = Date.now();
            state.preparePoller = setInterval(async () => {
                try {
                    const next = await API.getPrepareStatus(prepared.prepared_id);
                    const elapsed = Math.round((Date.now() - started) / 1000);
                    const waitingText = document.querySelector('.download-file-list .empty-state p');
                    if (waitingText) waitingText.textContent = `Fetching torrent metadata... ${elapsed}s`;
                    if (next.metadata_ready) {
                        clearInterval(state.preparePoller);
                        state.preparePoller = null;
                        next.game = prepared.game;
                        renderPrepareDownloadModal(next);
                    }
                } catch {
                    clearInterval(state.preparePoller);
                    state.preparePoller = null;
                }
            }, 3000);
        }
        document.getElementById('btn-confirm-prepared-download')?.addEventListener('click', confirmPreparedDownload);
        document.getElementById('btn-prepare-external')?.addEventListener('click', async () => {
            if (prepared.game?.slug) {
                await API.triggerDownload(prepared.game.slug);
                Components.showToast('Opened in external client.', 'success');
            }
        });
        updatePreparedSelectionStats();
    }

    async function confirmPreparedDownload() {
        const prepared = state.lastPreparedDownload;
        if (!prepared) return;
        const selected = getSelectedIndexesFromModal();
        if (!selected.length) {
            Components.showToast('Select at least one file first.', 'error');
            return;
        }
        const btn = document.getElementById('btn-confirm-prepared-download');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Adding...';
        try {
            await API.confirmDownload({
                prepared_id: prepared.prepared_id,
                info_hash: prepared.info_hash,
                selected_indexes: selected,
                save_path: document.getElementById('prepare-save-path').value.trim(),
                priority: document.getElementById('prepare-priority').value,
                queue_position: document.getElementById('prepare-queue-position').value
            });
            elements.gameModal.classList.remove('active');
            Components.showToast('Download added to the built-in queue.', 'success');
            switchView('downloads');
            await loadDownloads();
        } catch (err) {
            Components.showToast(`Could not add download: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Add Selected Files to Downloads';
        }
    }

    function toggleWishlistItem(game) {
        const wishlist = readJSON(STORAGE.wishlist, []);
        const wlGames = readJSON(STORAGE.wishlistGames, []);
        const idx = wishlist.indexOf(game.slug);
        const starBtn = document.getElementById('modal-wishlist-btn');
        if (idx > -1) {
            wishlist.splice(idx, 1);
            const gameIdx = wlGames.findIndex(g => g.slug === game.slug);
            if (gameIdx > -1) wlGames.splice(gameIdx, 1);
            starBtn?.classList.remove('active');
            if (starBtn) starBtn.innerHTML = '<i class="fa-regular fa-star"></i> Add to Wishlist';
            Components.showToast('Removed from wishlist.', 'success');
        } else {
            wishlist.push(game.slug);
            wlGames.push(game);
            starBtn?.classList.add('active');
            if (starBtn) starBtn.innerHTML = '<i class="fa-solid fa-star"></i> Wishlisted';
            Components.showToast('Added to wishlist.', 'success');
        }
        localStorage.setItem(STORAGE.wishlist, JSON.stringify(wishlist));
        localStorage.setItem(STORAGE.wishlistGames, JSON.stringify(wlGames));
        if (state.activeView === 'wishlist') renderWishlist();
    }

    function renderWishlist() {
        const wlGames = readJSON(STORAGE.wishlistGames, []);
        elements.wishlistContainer.innerHTML = '';
        if (!wlGames.length) {
            elements.wishlistContainer.innerHTML = '<div class="empty-state" style="grid-column:1/-1;"><i class="fa-regular fa-star"></i><p>Your wishlist is empty.</p></div>';
            elements.wishlistSavings.style.display = 'none';
            return;
        }
        elements.wishlistSavings.style.display = 'flex';
        const repackTotal = wlGames.reduce((sum, game) => sum + parseSizeGB(game.repack_size), 0);
        const originalTotal = wlGames.reduce((sum, game) => sum + parseSizeGB(game.original_size), 0);
        const bandwidthSaved = Math.max(originalTotal - repackTotal, 0);
        const savingsPct = originalTotal > 0 ? Math.round((bandwidthSaved / originalTotal) * 100) : 0;
        elements.wishlistSavings.innerHTML = `
            <div class="saving-item"><span class="saving-label">Source Size</span><span class="saving-val">${repackTotal.toFixed(1)} GB</span></div>
            <div class="saving-item"><span class="saving-label">Original Size</span><span class="saving-val" style="color: var(--text-muted);">${originalTotal.toFixed(1)} GB</span></div>
            <div class="saving-item"><span class="saving-label">Bandwidth Saved</span><span class="saving-val text-green">+ ${bandwidthSaved.toFixed(1)} GB (${savingsPct}% Saved)</span></div>
        `;
        renderCards(elements.wishlistContainer, wlGames, 'No compatible games match in wishlist.');
    }


    function renderDownloadsFromData(data) {
        const engine = data.engine || {};
        const settings = data.settings || {};
        elements.downloadMaxActive.value = settings.max_active_downloads || 3;
        elements.downloadDefaultPath.value = settings.default_save_path || '';
        elements.downloadLimit.value = settings.download_limit || '0';
        elements.uploadLimit.value = settings.upload_limit || '0';
        elements.downloadsEngineAlert.style.display = 'flex';
        elements.downloadsEngineAlert.innerHTML = engine.available
            ? `<i class="fa-solid fa-gauge-high"></i><span>Built-in downloader ready. Speed is uncapped unless limits are set; real speed depends on seeders, ISP, and disk.</span>`
            : '<i class="fa-solid fa-triangle-exclamation"></i><span>Built-in downloader is not available. Reinstall app dependencies.</span>';

        const downloads = data.downloads || [];
        updateNavDownloadBadge(downloads);
        if (!downloads.length) {
            elements.downloadsList.innerHTML = '<div class="empty-state"><i class="fa-solid fa-cloud-arrow-down"></i><p>No downloads yet.</p></div>';
            return;
        }
        elements.downloadsList.innerHTML = downloads.map(item => {
            const total = Number(item.total_length || 0);
            const done = Number(item.completed_length || 0);
            const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
            const selectedCount = (item.selected_file_indexes || []).length || (item.files || []).filter(f => f.selected).length;
            const status = String(item.status || 'queued').toLowerCase();
            const isPaused = status === 'paused' || item.user_paused || item.priority === 'Paused';
            const canRetry = status === 'error' || Boolean(item.last_error);
            const canOpenFolder = Boolean(item.save_path);
            const pauseAction = isPaused ? 'resume' : 'pause';
            const pauseIcon = isPaused ? 'fa-play' : 'fa-pause';
            const pauseTitle = isPaused ? 'Resume' : 'Pause';
            return `
                <article class="download-row ${escapeHTML(item.status || 'queued')}" data-info-hash="${escapeHTML(item.info_hash)}">
                    <div class="download-main">
                        <div class="download-title-line"><h3 title="${escapeHTML(item.title)}">${escapeHTML(item.title)}</h3><span class="download-status-pill ${escapeHTML(item.status || 'queued')}">${escapeHTML(item.status || 'queued')}</span></div>
                        <div class="download-path">${escapeHTML(item.save_path || 'No folder set')}</div>
                        <div class="download-progress"><div class="download-progress-fill" style="width:${pct}%"></div></div>
                        <div class="download-metrics">
                            <span>${pct}%</span><span>${formatBytes(done)} / ${formatBytes(total)}</span>
                            <span><i class="fa-solid fa-down-long"></i> ${formatSpeed(item.download_speed)}</span>
                            <span><i class="fa-solid fa-up-long"></i> ${formatSpeed(item.upload_speed)}</span>
                            <span>${item.seeders || 0} seeders</span><span>ETA ${formatEta(done, total, item.download_speed)}</span><span>${selectedCount} files selected</span>
                        </div>
                        ${item.last_error ? `<div class="download-error">${escapeHTML(item.last_error)}</div>` : ''}
                    </div>
                    <div class="download-controls">
                        <select class="download-priority-select" title="Priority">${['Urgent', 'High', 'Normal', 'Low', 'Paused'].map(p => `<option ${item.priority === p ? 'selected' : ''}>${p}</option>`).join('')}</select>
                        <div class="download-action-group" aria-label="Queue controls">
                            <button class="icon-btn download-up" title="Move up" aria-label="Move up"><i class="fa-solid fa-arrow-up"></i></button>
                            <button class="icon-btn download-down" title="Move down" aria-label="Move down"><i class="fa-solid fa-arrow-down"></i></button>
                        </div>
                        <div class="download-action-group" aria-label="Download controls">
                            <button class="icon-btn download-toggle-pause" data-action="${pauseAction}" title="${pauseTitle}" aria-label="${pauseTitle}"><i class="fa-solid ${pauseIcon}"></i></button>
                            <button class="icon-btn download-retry" title="Retry" aria-label="Retry" ${canRetry ? '' : 'disabled'}><i class="fa-solid fa-rotate-right"></i></button>
                        </div>
                        <div class="download-action-group" aria-label="File controls">
                            <button class="icon-btn download-open-folder" title="Open folder" aria-label="Open folder" ${canOpenFolder ? '' : 'disabled'}><i class="fa-solid fa-folder-open"></i></button>
                            <button class="icon-btn download-copy" title="Copy magnet" aria-label="Copy magnet"><i class="fa-solid fa-copy"></i></button>
                        </div>
                        <div class="download-action-group danger" aria-label="Removal controls">
                            <button class="icon-btn download-remove" title="Remove from queue" aria-label="Remove from queue"><i class="fa-solid fa-xmark"></i></button>
                            <button class="icon-btn danger download-delete-files" title="Delete files" aria-label="Delete files"><i class="fa-solid fa-trash-can"></i></button>
                        </div>
                    </div>
                </article>
            `;
        }).join('');
        bindDownloadRowActions();
    }
    async function loadDownloads() {
        try {
            const data = await API.getTorrentStatus();
            state.lastDownloadData = data;
            updateNavDownloadBadge(data.downloads || []);
            if (state.activeView === 'downloads') renderDownloadsFromData(data);
        } catch (err) {
            updateNavDownloadBadge([]);
            if (state.activeView === 'downloads') {
                elements.downloadsList.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>Failed to load downloads: ${escapeHTML(err.message)}</p></div>`;
            }
        }
    }
    function bindDownloadRowActions() {
        document.querySelectorAll('.download-row').forEach(row => {
            const infoHash = row.dataset.infoHash;
            row.querySelector('.download-priority-select')?.addEventListener('change', async e => {
                await API.setTorrentPriority(infoHash, e.target.value);
                await loadDownloads();
            });
            ['up', 'down'].forEach(direction => row.querySelector(`.download-${direction}`)?.addEventListener('click', async () => {
                await API.reorderTorrent(infoHash, direction);
                await loadDownloads();
            }));
            row.querySelector('.download-toggle-pause')?.addEventListener('click', async e => {
                await API.controlTorrent(infoHash, e.currentTarget.dataset.action || 'pause');
                await loadDownloads();
            });
            row.querySelector('.download-retry')?.addEventListener('click', async e => {
                if (e.currentTarget.disabled) return;
                await API.controlTorrent(infoHash, 'retry');
                await loadDownloads();
            });
            row.querySelector('.download-remove')?.addEventListener('click', async () => {
                const ok = await showConfirmDialog({
                    title: 'Remove Download',
                    message: 'Remove this download from the queue? Local files on disk will be kept.',
                    confirmText: 'Remove',
                    danger: false
                });
                if (!ok) return;
                await API.controlTorrent(infoHash, 'remove');
                await loadDownloads();
            });
            row.querySelector('.download-delete-files')?.addEventListener('click', async () => {
                const ok = await showConfirmDialog({
                    title: 'Delete Download Files',
                    message: 'Delete this download and its local files? This cannot be undone.',
                    confirmText: 'Delete Files',
                    danger: true
                });
                if (!ok) return;
                await API.controlTorrent(infoHash, 'delete-files');
                await loadDownloads();
            });
            row.querySelector('.download-open-folder')?.addEventListener('click', e => {
                if (!e.currentTarget.disabled) API.controlTorrent(infoHash, 'open-folder');
            });
            row.querySelector('.download-copy')?.addEventListener('click', async () => {
                const data = await API.getTorrentStatus();
                const item = (data.downloads || []).find(d => d.info_hash === infoHash);
                if (item?.magnet) {
                    await navigator.clipboard.writeText(item.magnet);
                    Components.showToast('Magnet copied.', 'success');
                }
            });
        });
    }

    function startDownloadsPolling() {
        if (state.downloadsPoller) clearInterval(state.downloadsPoller);
        loadDownloads();
        state.downloadsPoller = setInterval(loadDownloads, 2500);
    }

    async function renderOfflineCatalog() {
        showSkeleton(elements.catalogContainer, 8);
        loadOfflineStats();
        try {
            const data = await API.getOfflineCatalog();
            renderCards(elements.catalogContainer, data.games || [], 'No offline catalog files found.');
        } catch {
            elements.catalogContainer.innerHTML = '<div class="empty-state"><p>Failed to load offline catalog.</p></div>';
        }
    }

    async function loadOfflineStats() {
        try {
            const stats = await API.getOfflineStats();
            elements.offlineStatsGrid.innerHTML = `
                <div class="offline-stat"><span>Saved Games</span><strong>${stats.saved_games || 0}</strong></div>
                <div class="offline-stat"><span>Source Size</span><strong>${stats.repack_total_gb || 0} GB</strong></div>
                <div class="offline-stat"><span>Bandwidth Saved</span><strong>${stats.bandwidth_saved_gb || 0} GB</strong></div>
                <div class="offline-stat"><span>Queue Left</span><strong>${stats.remaining_queue || 0}</strong></div>
                <div class="offline-stat"><span>Media Cache</span><strong>${stats.media_size_mb || 0} MB</strong></div>
            `;
        } catch {
            elements.offlineStatsGrid.innerHTML = '';
        }
    }

    function switchView(viewName) {
        state.activeView = viewName;
        [elements.viewHome, elements.viewGallery, elements.viewNews, elements.viewSearch, elements.viewWishlist, elements.viewDownloads, elements.viewCatalog].forEach(el => el?.classList.remove('active'));
        [elements.navHome, elements.navGallery, elements.navNews, elements.navWishlist, elements.navDownloads, elements.navCatalog, elements.navHistory, elements.navUpcoming].forEach(el => el?.classList.remove('active'));
        if (viewName === 'home') {
            elements.viewHome.classList.add('active');
            elements.navHome.classList.add('active');
        } else if (viewName === 'gallery') {
            elements.viewGallery.classList.add('active');
            elements.navGallery.classList.add('active');
            loadGallery();
        } else if (viewName === 'news') {
            elements.viewNews.classList.add('active');
            elements.navNews.classList.add('active');
            loadNews();
            startNewsPolling();
        } else if (viewName === 'search') {
            elements.viewSearch.classList.add('active');
        } else if (viewName === 'wishlist') {
            elements.viewWishlist.classList.add('active');
            elements.navWishlist.classList.add('active');
            renderWishlist();
        } else if (viewName === 'downloads') {
            elements.viewDownloads.classList.add('active');
            elements.navDownloads.classList.add('active');
            if (state.lastDownloadData) renderDownloadsFromData(state.lastDownloadData);
            loadDownloads();
        } else if (viewName === 'catalog') {
            elements.viewCatalog.classList.add('active');
            elements.navCatalog.classList.add('active');
            renderOfflineCatalog();
        }
    }

    function addToHistory(query) {
        if (!query) return;
        state.searchHistory = state.searchHistory.filter(q => q.toLowerCase() !== query.toLowerCase());
        state.searchHistory.unshift(query);
        state.searchHistory = state.searchHistory.slice(0, 20);
        localStorage.setItem(STORAGE.searchHistory, JSON.stringify(state.searchHistory));
    }

    function bindEvents() {
        let searchTimeout;
        elements.themeToggle?.addEventListener('click', () => {
            const nextTheme = document.body.classList.contains('light-mode') ? 'dark-mode' : 'light-mode';
            applyTheme(nextTheme);
        });
        elements.searchInput.addEventListener('input', e => {
            const value = e.target.value.trim();
            elements.btnClearSearch.style.display = value ? 'block' : 'none';
            clearTimeout(searchTimeout);
            if (!value) {
                if (state.activeView === 'search') switchView('home');
                return;
            }
            searchTimeout = setTimeout(() => {
                state.currentQuery = value;
                state.searchPage = 1;
                addToHistory(value);
                executeSearch();
            }, 400);
        });
        elements.btnClearSearch.addEventListener('click', () => {
            elements.searchInput.value = '';
            elements.btnClearSearch.style.display = 'none';
            state.currentQuery = '';
            switchView('home');
        });
        elements.toggleCompatibility.addEventListener('change', e => {
            state.compatibilityOnly = e.target.checked;
            Components.showToast(state.compatibilityOnly ? 'Compatible Specs Filter Enabled' : 'Compatible Specs Filter Disabled', 'success');
            if (state.activeView === 'home') loadHomepage();
            if (state.activeView === 'search') executeSearch();
            if (state.activeView === 'wishlist') renderWishlist();
            if (state.activeView === 'downloads') loadDownloads();
            if (state.activeView === 'catalog') renderOfflineCatalog();
            if (state.activeView === 'gallery') renderCards(elements.galleryContainer, state.galleryGames, 'No compatible games match.');
        });
        elements.btnPrevPage.addEventListener('click', () => {
            if (state.currentPage > 1) {
                state.currentPage--;
                loadLatestRepacks();
                document.querySelector('.content-scrollable').scrollTop = 0;
            }
        });
        elements.btnNextPage.addEventListener('click', () => {
            if (state.hasLatestNext) {
                state.currentPage++;
                loadLatestRepacks();
                document.querySelector('.content-scrollable').scrollTop = 0;
            }
        });
        elements.btnSearchPrev.addEventListener('click', () => {
            if (state.searchPage > 1) {
                state.searchPage--;
                executeSearch();
                document.querySelector('.content-scrollable').scrollTop = 0;
            }
        });
        elements.btnSearchNext.addEventListener('click', () => {
            if (state.hasSearchNext) {
                state.searchPage++;
                executeSearch();
                document.querySelector('.content-scrollable').scrollTop = 0;
            }
        });
        elements.btnBackHome.addEventListener('click', () => switchView('home'));
        elements.btnClearCache.addEventListener('click', async () => {
            if (!confirm('Clear the local scraping/news cache?')) return;
            await API.clearCache();
            Components.showToast('Local cache cleared.', 'success');
            if (state.activeView === 'news') loadNews(true);
            else if (state.activeView === 'gallery') loadGallery(true);
            else loadHomepage();
        });
        elements.btnModalClose.addEventListener('click', () => elements.gameModal.classList.remove('active'));
        elements.gameModal.addEventListener('click', e => {
            if (e.target === elements.gameModal) elements.gameModal.classList.remove('active');
        });
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') elements.gameModal.classList.remove('active');
        });
        elements.navHome.addEventListener('click', () => switchView('home'));
        elements.navGallery.addEventListener('click', () => switchView('gallery'));
        elements.navNews.addEventListener('click', () => switchView('news'));
        elements.navWishlist.addEventListener('click', () => switchView('wishlist'));
        elements.navDownloads.addEventListener('click', () => switchView('downloads'));
        elements.navCatalog.addEventListener('click', () => switchView('catalog'));
        elements.navUpcoming.addEventListener('click', () => {
            switchView('news');
            setTimeout(() => elements.upcomingGamesNews?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 200);
        });
        elements.btnGalleryRefresh?.addEventListener('click', () => loadGallery(true));
        elements.btnGalleryPrev?.addEventListener('click', () => {
            if (state.galleryPage > 1) {
                state.galleryPage -= 1;
                loadGallery(false);
            }
        });
        elements.btnGalleryNext?.addEventListener('click', () => {
            if (state.galleryPage < state.galleryTotalPages) {
                state.galleryPage += 1;
                loadGallery(false);
            }
        });
        elements.btnNewsRefresh?.addEventListener('click', () => loadNews(true));
        elements.newsTabs?.addEventListener('click', e => {
            const btn = e.target.closest('.news-tab');
            if (!btn) return;
            state.newsFilter = btn.dataset.newsFilter;
            document.querySelectorAll('.news-tab').forEach(tab => tab.classList.remove('active'));
            btn.classList.add('active');
            loadNews(false);
        });
        elements.btnDownloadsPauseAll.addEventListener('click', async () => {
            await API.controlTorrent('', 'pause-all');
            await loadDownloads();
        });
        elements.btnDownloadsResumeAll.addEventListener('click', async () => {
            await API.controlTorrent('', 'resume-all');
            await loadDownloads();
        });
        elements.btnDownloadsClearCompleted.addEventListener('click', async () => {
            await API.controlTorrent('', 'clear-completed');
            await loadDownloads();
        });
        elements.btnSaveDownloadSettings.addEventListener('click', async () => {
            try {
                await API.updateTorrentSettings({
                    max_active_downloads: parseInt(elements.downloadMaxActive.value, 10) || 3,
                    default_save_path: elements.downloadDefaultPath.value.trim(),
                    download_limit: elements.downloadLimit.value.trim() || '0',
                    upload_limit: elements.uploadLimit.value.trim() || '0'
                });
                Components.showToast('Downloader settings saved.', 'success');
                await loadDownloads();
            } catch (err) {
                Components.showToast(`Failed to save settings: ${err.message}`, 'error');
            }
        });
        elements.btnBrowseDownloadPath?.addEventListener('click', async () => {
            const folder = await chooseFolder(elements.downloadDefaultPath.value);
            if (folder) elements.downloadDefaultPath.value = folder;
        });
        elements.btnExportOffline.addEventListener('click', async () => {
            const data = await API.exportOfflineData();
            await navigator.clipboard.writeText(JSON.stringify(data));
            Components.showToast('Offline export copied to clipboard.', 'success');
        });
        elements.btnPruneMedia.addEventListener('click', async () => {
            const result = await API.pruneOfflineMedia();
            Components.showToast(`Pruned ${result.removed || 0} unused media files.`, 'success');
            loadOfflineStats();
        });
        elements.navHistory.addEventListener('click', () => {
            if (!state.searchHistory.length) {
                Components.showToast('Search history is empty.', 'error');
                return;
            }
            elements.modalContentBody.innerHTML = `
                <div style="padding: 16px;">
                    <h2 class="modal-title" style="margin-bottom: 20px;"><i class="fa-solid fa-clock-rotate-left"></i> Search History</h2>
                    <div style="display:flex; flex-direction:column; gap:10px;">
                        ${state.searchHistory.map(q => `<button class="btn btn-secondary quick-history-btn" style="text-align:left; justify-content:flex-start; width:100%;"><i class="fa-solid fa-magnifying-glass text-pink"></i> ${escapeHTML(q)}</button>`).join('')}
                    </div>
                </div>
            `;
            elements.gameModal.classList.add('active');
            document.querySelectorAll('.quick-history-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const q = btn.textContent.trim();
                    elements.gameModal.classList.remove('active');
                    elements.searchInput.value = q;
                    elements.btnClearSearch.style.display = 'block';
                    state.currentQuery = q;
                    state.searchPage = 1;
                    executeSearch();
                });
            });
        });
        elements.sidebarToggle?.addEventListener('click', () => {
            const collapsed = !elements.sidebar.classList.contains('collapsed');
            elements.sidebar.classList.toggle('collapsed', collapsed);
            localStorage.setItem(STORAGE.sidebarCollapsed, collapsed ? '1' : '0');
        });
    }

    function initSidebar() {
        const collapsed = localStorage.getItem(STORAGE.sidebarCollapsed) === '1';
        elements.sidebar?.classList.toggle('collapsed', collapsed);
    }

    migrateStorage();
    initTheme();
    initSidebar();
    bindEvents();
    loadHomepage();
    loadDiagnostics();
    startPingMonitor();
    startDownloadsPolling();
});










