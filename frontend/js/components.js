/**
 * components.js - UI components renderer for Arcadia Core.
 */

const Components = {
    fallbackCover: '/assets/game-cover-placeholder.png',

    escape(value) {
        return String(value ?? '').replace(/[&<>"']/g, ch => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[ch]));
    },

    resolveImage(game = {}) {
        const shot = Array.isArray(game.screenshots) && game.screenshots.length ? game.screenshots[0] : {};
        return game.thumbnail_cached || game.thumbnail || game.cover_cached || game.cover ||
            shot.thumb_cached || shot.thumb || shot.full || this.fallbackCover;
    },

    parseGpuTier(value = '') {
        const gpu = String(value).toLowerCase();
        if (!gpu || /unknown|n\/a|integrated/.test(gpu)) return null;

        const nvidia = gpu.match(/\b(?:rtx|gtx)\s*([0-9]{3,4})(?:\s*ti|\s*super)?/i);
        if (nvidia) {
            const model = parseInt(nvidia[1], 10);
            const series = Math.floor(model / 1000);
            const cls = model % 1000;
            return 1000 + series * 100 + cls / 10 + (/ti|super/i.test(gpu) ? 12 : 0);
        }

        const amd = gpu.match(/\brx\s*([0-9]{3,4})(?:\s*xt)?/i);
        if (amd) {
            const model = parseInt(amd[1], 10);
            const series = Math.floor(model / 1000);
            const cls = model % 1000;
            return 900 + series * 100 + cls / 10 + (/xt/i.test(gpu) ? 10 : 0);
        }

        const intel = gpu.match(/\barc\s*a?([0-9]{3,4})/i);
        if (intel) return 850 + parseInt(intel[1], 10) / 10;

        return null;
    },

    bestUserGpuTier() {
        const candidates = [];
        if (window.userSpecs?.gpu) candidates.push(window.userSpecs.gpu);
        if (Array.isArray(window.userSpecs?.gpus)) candidates.push(...window.userSpecs.gpus);
        if (Array.isArray(window.userSpecs?.gpu_details)) {
            candidates.push(...window.userSpecs.gpu_details.map(item => item?.name).filter(Boolean));
        }
        const tiers = candidates.map(value => this.parseGpuTier(value)).filter(value => value !== null);
        return tiers.length ? Math.max(...tiers) : null;
    },

    getCompatibility(reqs) {
        if (!reqs || !window.userSpecs) return null;
        if (reqs.pending) {
            return {
                status: 'unknown',
                label: 'Checking Specs',
                notes: ['Requirements are loading'],
                ram: { user: parseInt(window.userSpecs.ram ?? window.userSpecs.ram_gb, 10) || 0, min: 0, rec: 0 },
                gpu: { user: window.userSpecs.gpu || 'Unknown GPU', required: 'Loading...', status: 'unknown' }
            };
        }
        const userRam = parseInt(window.userSpecs.ram ?? window.userSpecs.ram_gb, 10);
        const ramMin = parseInt(reqs.ram_min, 10) || 0;
        const ramRec = parseInt(reqs.ram_rec, 10) || ramMin || 0;
        const userGpuTier = this.bestUserGpuTier();
        const reqGpuTier = this.parseGpuTier(reqs.gpu);
        const hasRamRequirement = ramMin > 0 || ramRec > 0;
        const hasGpuRequirement = Boolean(String(reqs.gpu || '').trim());

        if (!hasRamRequirement && !hasGpuRequirement) {
            return {
                status: 'unknown',
                label: 'Unknown Specs',
                notes: ['No hardware requirements found'],
                ram: { user: userRam || 0, min: 0, rec: 0 },
                gpu: { user: window.userSpecs.gpu || 'Unknown GPU', required: 'N/A', status: 'unknown' }
            };
        }

        let status = 'pass';
        let label = 'Compatible';
        const notes = [];

        if (ramMin && userRam && userRam < ramMin) {
            status = 'fail';
            label = 'Below Specs';
            notes.push('RAM below minimum');
        } else if (ramRec && userRam && userRam < ramRec) {
            status = 'minimum';
            label = 'Min Specs';
            notes.push('RAM below recommended');
        }

        let gpuStatus = 'unknown';
        if (userGpuTier && reqGpuTier) {
            if (userGpuTier + 1 < reqGpuTier) {
                status = 'fail';
                label = 'Below Specs';
                gpuStatus = 'fail';
                notes.push('GPU below listed target');
            } else if (userGpuTier < reqGpuTier + 45 && status !== 'fail') {
                status = 'minimum';
                label = 'Min Specs';
                gpuStatus = 'minimum';
                notes.push('GPU near listed target');
            } else {
                gpuStatus = 'pass';
            }
        } else if (hasGpuRequirement) {
            gpuStatus = 'unknown';
            if (status !== 'fail') {
                status = 'unknown';
                label = 'Unknown Specs';
            }
            notes.push('GPU requirement could not be compared accurately');
        }

        return {
            status,
            label,
            notes,
            ram: { user: userRam || 0, min: ramMin, rec: ramRec },
            gpu: { user: window.userSpecs.gpu || 'Unknown GPU', required: reqs.gpu || 'N/A', status: gpuStatus }
        };
    },

    createGameCard(game) {
        const coverImg = this.resolveImage(game);
        const hasArtwork = Boolean(game.thumbnail_cached || game.thumbnail || game.cover_cached || game.cover ||
            (Array.isArray(game.screenshots) && game.screenshots.length && (game.screenshots[0].thumb_cached || game.screenshots[0].thumb || game.screenshots[0].full)));
        const safeTitle = this.escape(game.title || 'Untitled Game');
        const card = document.createElement('div');
        card.className = 'game-card';
        card.dataset.slug = game.slug || '';

        const comp = this.getCompatibility(game.requirements);
        const library = game.library || game.offline_user || null;
        const libraryStatus = library ? this.libraryStatus(library) : null;
        const artworkSource = this.escape(library?.artwork_source || game.artwork_source || 'placeholder');
        if (libraryStatus && libraryStatus.className !== 'backlog') card.classList.add(`library-${libraryStatus.className}`);
        const badgeHTML = comp ? `<div class="card-compatibility-badge ${comp.status}">${this.escape(comp.label)}</div>` : '';
        const libraryBadgeHTML = libraryStatus && libraryStatus.className !== 'backlog' ? `
            <div class="card-library-badge ${libraryStatus.className}">
                <i class="fa-solid ${libraryStatus.icon}"></i> ${libraryStatus.label}
            </div>
        ` : '';
        const sourceHTML = game.official_site ? `
            <a class="card-official-link" href="${this.escape(game.official_site)}" target="_blank" title="Official game site" onclick="event.stopPropagation()">
                <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
        ` : '';
        const sizeText = game.repack_size || (game.summary && game.summary.includes('Size:') ? game.summary.split('Size:')[1].trim() : '');

        card.innerHTML = `
            <div class="card-img-wrapper">
                ${badgeHTML}
                ${libraryBadgeHTML}
                ${sourceHTML}
                ${hasArtwork ? `<img src="${this.escape(coverImg)}" alt="${safeTitle}" loading="lazy" onerror="this.src='${this.fallbackCover}'">` : `
                    <div class="artwork-loading">
                        <i class="fa-solid fa-spinner fa-spin"></i>
                        <span>Artwork loading</span>
                    </div>
                `}
            </div>
            <div class="card-info">
                <span class="card-category">${this.escape(game.category || 'Game Source')}</span>
                <h3 class="card-title" title="${safeTitle}">${safeTitle}</h3>
                <div class="card-footer">
                    <span>${game.date ? new Date(game.date).toLocaleDateString() : ''}</span>
                    <span class="card-size">${this.escape(sizeText)}</span>
                </div>
            </div>
        `;
        return card;
    },

    formatPlaytime(seconds = 0) {
        const total = Math.max(0, Number(seconds) || 0);
        if (total <= 0) return 'Not played';
        if (total < 60) return `${Math.floor(total)}s`;
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        if (hours <= 0) return `${minutes}m`;
        return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
    },

    formatStorage(bytes = 0, gb = 0) {
        const rawBytes = Number(bytes) || 0;
        const rawGb = Number(gb) || 0;
        if (rawBytes <= 0 && rawGb <= 0) return 'Not scanned';
        const valueGb = rawBytes > 0 ? rawBytes / (1024 ** 3) : rawGb;
        if (valueGb >= 1) return `${valueGb.toFixed(valueGb >= 100 ? 0 : 2)} GB`;
        return `${Math.max(1, Math.round(valueGb * 1024))} MB`;
    },

    libraryStatus(library = {}) {
        if (library.running) return { label: 'Running', icon: 'fa-spinner fa-spin', className: 'running' };
        const status = String(library.install_status || 'backlog');
        if (status === 'installed') return { label: 'Installed', icon: 'fa-circle-play', className: 'installed' };
        if (status === 'unlinked') return { label: 'Needs Link', icon: 'fa-link-slash', className: 'unlinked' };
        if (status === 'missing') return { label: 'Missing', icon: 'fa-triangle-exclamation', className: 'missing' };
        return { label: 'Backlog', icon: 'fa-bookmark', className: 'backlog' };
    },

    librarySourceLabel(game = {}, library = {}) {
        const source = String(library.library_source || '').toLowerCase();
        const installPath = String(library.install_path || '').toLowerCase().replace(/\//g, '\\');
        if (source === 'steam') return 'Steam Library';
        if (source === 'epic') return 'Epic Games';
        if (source === 'folder_scan') return 'Local Install';
        if (source === 'start_menu') return 'Windows Shortcut';
        if (source === 'arcadia_download') return 'Arcadia Download';
        if (installPath.includes('\\steamapps\\common\\')) return 'Steam Library';
        if (installPath.includes('\\epic games\\') || installPath.includes('\\epicgames\\')) return 'Epic Games';
        if (library.install_status === 'installed' && installPath && ['saved', 'manual', ''].includes(source)) return 'Local Install';
        if (String(game.slug || '').startsWith('local-')) return 'Local Game';
        return game.category || source || 'My Library';
    },

    createLibraryCard(game) {
        const coverImg = this.resolveImage(game);
        const safeTitle = this.escape(game.title || 'Untitled Game');
        const library = game.library || game.offline_user || {};
        const status = this.libraryStatus(library);
        const canLaunch = library.install_status === 'installed' && library.executable_path && !library.running;
        const launchLabel = library.running ? 'Running' : 'Launch';
        const launchIcon = library.running ? 'fa-spinner fa-spin' : 'fa-play';
        const playtime = this.formatPlaytime(library.playtime_seconds);
        const lastPlayed = library.last_played_at ? new Date(library.last_played_at * 1000).toLocaleDateString() : 'Never';
        const installedSize = this.formatStorage(library.installed_size_bytes, library.installed_size_gb);
        const installedSizeHTML = library.install_status === 'installed' ? `
            <div class="library-size-line"><span>Installed Size</span><strong>${this.escape(installedSize)}</strong></div>
        ` : '';
        const card = document.createElement('article');
        card.className = `library-card ${status.className}`;
        card.dataset.slug = game.slug || '';
        card.tabIndex = 0;
        card.innerHTML = `
            <div class="library-art">
                <img class="library-art-backdrop" src="${this.escape(coverImg)}" alt="" loading="lazy" aria-hidden="true" onerror="this.src='${this.fallbackCover}'">
                <img class="library-art-main" src="${this.escape(coverImg)}" alt="${safeTitle}" loading="lazy" onerror="this.src='${this.fallbackCover}'">
                <span class="library-status-pill ${status.className}"><i class="fa-solid ${status.icon}"></i> ${status.label}</span>
                <div class="library-card-actions" aria-label="Library actions">
                    <button class="btn btn-success library-launch ${library.running ? 'is-running' : ''}" ${canLaunch ? '' : 'disabled'} title="${library.running ? 'Game is running' : (canLaunch ? 'Launch game' : 'Link executable first')}" aria-label="${library.running ? 'Game is running' : (canLaunch ? `Launch ${safeTitle}` : 'Link executable first')}">
                        <i class="fa-solid ${launchIcon}"></i><span>${launchLabel}</span>
                    </button>
                    <button class="icon-btn library-open-folder" title="Open install folder" aria-label="Open install folder" ${library.install_path ? '' : 'disabled'}><i class="fa-solid fa-folder-open"></i></button>
                    <button class="icon-btn library-relink" title="Relink executable" aria-label="Relink executable"><i class="fa-solid fa-link"></i></button>
                    <button class="icon-btn library-backlog" title="Mark backlog" aria-label="Mark backlog"><i class="fa-solid fa-bookmark"></i></button>
                    <button class="icon-btn danger library-remove" title="Remove from My Library" aria-label="Remove from My Library"><i class="fa-solid fa-trash-can"></i></button>
                </div>
            </div>
            <div class="library-body">
                <span class="card-category">${this.escape(this.librarySourceLabel(game, library))}</span>
                <h3 class="card-title" title="${safeTitle}">${safeTitle}</h3>
                ${installedSizeHTML}
                <div class="library-metrics">
                    <span><strong>${this.escape(playtime)}</strong><small>Playtime</small></span>
                    <span><strong>${this.escape(lastPlayed)}</strong><small>Last played</small></span>
                </div>
            </div>
        `;
        return card;
    },

    createSkeletonCard() {
        const card = document.createElement('div');
        card.className = 'skeleton-card';
        return card;
    },

    createPopularCard(game) {
        const card = document.createElement('div');
        card.className = 'popular-card';
        card.dataset.slug = game.slug || '';
        const coverImg = this.resolveImage(game);
        const safeTitle = this.escape(game.title || 'Untitled Game');
        card.innerHTML = `
            <div class="popular-img-wrapper">
                <img src="${this.escape(coverImg)}" alt="${safeTitle}" loading="lazy" onerror="this.src='${this.fallbackCover}'">
            </div>
            <div class="popular-info">
                <h3 class="popular-title" title="${safeTitle}">${safeTitle}</h3>
            </div>
        `;
        return card;
    },

    createUpcomingItem(gameText) {
        const item = document.createElement('div');
        item.className = 'upcoming-item';
        item.innerHTML = `
            <span class="upcoming-bullet"><i class="fa-solid fa-angles-right"></i></span>
            <span class="upcoming-text">${this.escape(gameText)}</span>
        `;
        return item;
    },

    createNewsCard(item) {
        const card = document.createElement('article');
        card.className = 'news-card';
        card.dataset.category = item.category || 'All';
        const image = item.image || this.fallbackCover;
        const date = item.published_at ? new Date(item.published_at * 1000).toLocaleString() : '';
        card.innerHTML = `
            <a href="${this.escape(item.url)}" target="_blank" class="news-image">
                <img src="${this.escape(image)}" alt="${this.escape(item.title)}" loading="lazy" onerror="this.src='${this.fallbackCover}'">
            </a>
            <div class="news-body">
                <div class="news-meta">
                    <span>${this.escape(item.source || 'Source')}</span>
                    <span>${this.escape(item.category || 'News')}</span>
                    ${item.is_official ? '<span>Official</span>' : ''}
                </div>
                <h3><a href="${this.escape(item.url)}" target="_blank">${this.escape(item.title)}</a></h3>
                <p>${this.escape(item.summary || '')}</p>
                <div class="news-footer">
                    <span>${this.escape(date)}</span>
                    <a href="${this.escape(item.url)}" target="_blank">Open source <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>
            </div>
        `;
        return card;
    },

    renderGameDetails(game) {
        const coverImg = this.resolveImage(game);
        const safeTitle = this.escape(game.title || 'Untitled Game');
        const wishlist = JSON.parse(localStorage.getItem('arcadia_wishlist') || localStorage.getItem('fg_wishlist') || '[]');
        const isWishlisted = wishlist.includes(game.slug);
        const comp = this.getCompatibility(game.requirements);
        const library = game.library || game.offline_user || null;
        const libraryStatus = library ? this.libraryStatus(library) : null;
        const artworkSource = this.escape(library?.artwork_source || game.artwork_source || 'placeholder');
        const isInstalledLinked = Boolean(library?.install_status === 'installed' && library?.executable_path);
        const canLaunchLibrary = Boolean(library?.install_status === 'installed' && library?.executable_path && !library?.running);
        const libraryRunning = Boolean(library?.running);
        const downloadBtnDisabled = (!game.magnet_link || isInstalledLinked) ? 'disabled' : '';
        const downloadBtnText = isInstalledLinked
            ? 'Already Installed'
            : (game.magnet_link ? 'Download inside App' : 'No Magnet Link Available');
        const downloadBtnClass = isInstalledLinked ? 'btn-secondary installed-disabled' : (game.magnet_link ? 'btn-success' : 'btn-secondary');
        const primaryLaunchHTML = (canLaunchLibrary || libraryRunning) ? `
            <button id="modal-library-launch-primary-btn" class="btn btn-success ${libraryRunning ? 'is-running' : ''}" ${libraryRunning ? 'disabled' : ''}><i class="fa-solid ${libraryRunning ? 'fa-spinner fa-spin' : 'fa-play'}"></i> ${libraryRunning ? 'Running' : 'Launch'}</button>
        ` : '';

        const officialLinks = [
            game.official_site ? `<a href="${this.escape(game.official_site)}" class="mirror-link" target="_blank"><i class="fa-solid fa-globe"></i><span>Official game site</span></a>` : '',
            game.publisher_site ? `<a href="${this.escape(game.publisher_site)}" class="mirror-link" target="_blank"><i class="fa-solid fa-building"></i><span>Publisher site</span></a>` : '',
            game.steam_page ? `<a href="${this.escape(game.steam_page)}" class="mirror-link" target="_blank"><i class="fa-brands fa-steam"></i><span>Steam page</span></a>` : ''
        ].filter(Boolean).join('');

        const torrentMirrorsHTML = game.torrent_links?.length ? `
            <div class="detail-section">
                <h3>Source Links</h3>
                <div class="mirrors-list">
                    ${game.torrent_links.map(l => `
                        <a href="${this.escape(l.url)}" class="mirror-link" target="_blank">
                            <i class="fa-solid fa-magnet"></i>
                            <span>${this.escape(l.name)}</span>
                        </a>
                    `).join('')}
                </div>
            </div>
        ` : '';

        const directMirrorsHTML = game.direct_links?.length ? `
            <div class="detail-section">
                <h3>Direct Source Mirrors</h3>
                <div class="mirrors-list">
                    ${game.direct_links.map(l => `
                        <a href="${this.escape(l.url)}" class="mirror-link" target="_blank">
                            <i class="fa-solid fa-cloud-arrow-down"></i>
                            <span>${this.escape(l.name)}</span>
                        </a>
                    `).join('')}
                </div>
            </div>
        ` : '';

        const screenshotsHTML = game.screenshots?.length ? `
            <div class="detail-section">
                <h3>Screenshots</h3>
                <div class="screenshots-gallery">
                    ${game.screenshots.map(s => `
                        <div class="screenshot-item" onclick="window.open('${this.escape(s.full || s.thumb)}', '_blank')">
                            <img src="${this.escape(s.thumb_cached || s.thumb || s.full)}" alt="Screenshot" onerror="this.src='${this.fallbackCover}'">
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : '';

        const featuresHTML = game.features?.length ? `
            <div class="detail-section">
                <h3>Source Features</h3>
                <ul class="feature-list">${game.features.map(f => `<li>${this.escape(f)}</li>`).join('')}</ul>
            </div>
        ` : '';

        let compatibilityPanelHTML = '';
        let spaceWarningHTML = '';
        if (game.requirements && window.userSpecs) {
            const reqs = game.requirements;
            const userRam = comp?.ram.user || 0;
            const ramMin = comp?.ram.min || 0;
            const ramRec = comp?.ram.rec || 0;
            let spacePass = true;
            let spaceAvailableText = 'No drives scan';
            if (window.userSpecs.drives?.length) {
                const requiredSpace = parseInt(reqs.space, 10) || 0;
                const okDrive = window.userSpecs.drives.find(d => d.free_gb >= requiredSpace);
                if (okDrive) {
                    spaceAvailableText = `${okDrive.free_gb} GB free (${okDrive.name})`;
                } else {
                    spacePass = false;
                    const bestDrive = [...window.userSpecs.drives].sort((a, b) => b.free_gb - a.free_gb)[0];
                    spaceAvailableText = `${bestDrive.free_gb} GB free (${bestDrive.name})`;
                }
            }
            if (reqs.space > 0 && !spacePass) {
                spaceWarningHTML = `
                    <div class="modal-alert-warning">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <span>Insufficient disk space on all drives. Needs ${this.escape(reqs.space)} GB; best available has ${this.escape(spaceAvailableText)}.</span>
                    </div>
                `;
            }
            compatibilityPanelHTML = `
                <div class="compatibility-details-panel">
                    <div class="comp-panel-header">
                        <div class="comp-panel-title"><i class="fa-solid fa-laptop-code text-pink"></i> Hardware Compatibility Check</div>
                        <div class="comp-status-badge ${comp?.status || 'unknown'}">${this.escape(comp?.label || 'Unknown Specs')}</div>
                    </div>
                    <div class="comp-specs-grid">
                        <div class="comp-spec-item">
                            <span class="comp-spec-label">System RAM</span>
                            <div class="comp-spec-compare">
                                <span class="comp-spec-user">${userRam || 'Unknown'} GB</span>
                                <span class="comp-spec-req">(Min: ${ramMin || 'N/A'}GB / Rec: ${ramRec || 'N/A'}GB)</span>
                            </div>
                        </div>
                        <div class="comp-spec-item">
                            <span class="comp-spec-label">Graphics / GPU</span>
                            <div class="comp-spec-compare">
                                <span class="comp-spec-user">${this.escape(comp?.gpu.user || 'Unknown GPU')}</span>
                                <span class="comp-spec-req">Target: ${this.escape(comp?.gpu.required || 'N/A')}</span>
                            </div>
                        </div>
                        <div class="comp-spec-item">
                            <span class="comp-spec-label">Disk Storage</span>
                            <div class="comp-spec-compare">
                                <span class="comp-spec-user">${this.escape(spaceAvailableText)}</span>
                                <span class="comp-spec-req">Required: ${this.escape(reqs.space || 0)} GB</span>
                            </div>
                        </div>
                        <div class="comp-spec-item">
                            <span class="comp-spec-label">Processor / CPU</span>
                            <span class="comp-spec-req">${this.escape(reqs.cpu || 'N/A')}</span>
                        </div>
                    </div>
                </div>
            `;
        }

        const parseSizeGB = (sizeStr) => {
            const matches = String(sizeStr || '').match(/(\d+(?:\.\d+)?)\s*(GB|MB)/i);
            if (!matches) return 0;
            let val = parseFloat(matches[1]);
            return matches[2].toUpperCase() === 'MB' ? val / 1024 : val;
        };
        const repackGB = parseSizeGB(game.repack_size);
        const originalGB = parseSizeGB(game.original_size);
        const downloadCalculatorHTML = repackGB > 0 ? `
            <div class="download-calc-panel">
                <div class="calc-header"><i class="fa-solid fa-gauge-high text-pink"></i> High-Speed Download Estimate</div>
                <div class="calc-inputs-row">
                    <span class="calc-time-label">Your Connection Speed:</span>
                    <div class="calc-input-wrapper calc-speed-value"><input type="number" id="calc-speed-val" value="100" min="1" step="10"></div>
                    <div class="calc-input-wrapper calc-speed-unit"><select id="calc-speed-unit"><option value="Mbps" selected>Mbps</option><option value="MBs">MB/s</option></select></div>
                </div>
                <div class="calc-results">
                    <div class="calc-time-item"><span class="calc-time-label">Selected source estimate</span><span class="calc-time-val repack" id="calc-repack-time">--</span></div>
                    <div class="calc-time-item"><span class="calc-time-label">Original-size estimate</span><span class="calc-time-val original" id="calc-original-time">--</span></div>
                    <div class="calc-savings-note" id="calc-savings-box">Seeder count, trackers, ISP, and disk speed can change real speed.</div>
                </div>
            </div>
        ` : '';

        let updatesHTML = '';
        if (game.updates && (game.updates.instructions || (game.updates.links && game.updates.links.length > 0))) {
            const instructionsHTML = game.updates.instructions ? `
                <div class="updates-instructions">
                    <i class="fa-solid fa-circle-info"></i>
                    <span>${this.escape(game.updates.instructions)}</span>
                </div>
            ` : '';
            const linksHTML = game.updates.links && game.updates.links.length > 0 ? `
                <div class="updates-links-list">
                    ${game.updates.links.map(l => `
                        <a href="${this.escape(l.url)}" class="btn-update-link" target="_blank" title="${this.escape(l.name)}">
                            <i class="fa-solid fa-cloud-arrow-down"></i>
                            <span>${this.escape(l.name)}</span>
                        </a>
                    `).join('')}
                </div>
            ` : '<div class="updates-empty">No update packages listed. Check source site.</div>';

            updatesHTML = `
                <div class="detail-section updates-section">
                    <div class="section-header-row">
                        <h3>Game Updates (Direct Links)</h3>
                        <span class="badge badge-update"><i class="fa-solid fa-bell"></i> Updates Available</span>
                    </div>
                    ${instructionsHTML}
                    <div class="updates-box">
                        ${linksHTML}
                    </div>
                    <div class="updates-notice">
                        <i class="fa-solid fa-triangle-exclamation text-orange"></i>
                        <span>These updates point to external hosts. Open the link to solve the captcha/timer, copy the final download link, and paste it into the <b>Paste Direct Link</b> bar on the Downloads tab to download in-app.</span>
                    </div>
                </div>
            `;
        }

        const libraryHTML = library ? `
            <div class="detail-section library-detail-panel">
                <div class="section-header-row">
                    <h3>My Library</h3>
                    <span class="library-status-pill ${libraryStatus.className}"><i class="fa-solid ${libraryStatus.icon}"></i> ${libraryStatus.label}</span>
                </div>
                <div class="library-detail-grid">
                    <div><span>Playtime</span><strong>${this.escape(this.formatPlaytime(library.playtime_seconds))}</strong></div>
                    <div><span>Last Played</span><strong>${library.last_played_at ? new Date(library.last_played_at * 1000).toLocaleDateString() : 'Never'}</strong></div>
                    <div><span>Installed Size</span><strong>${this.escape(this.formatStorage(library.installed_size_bytes, library.installed_size_gb))}</strong></div>
                    <div><span>Artwork</span><strong>${artworkSource}</strong></div>
                    <div><span>Install Folder</span><strong title="${this.escape(library.install_path || '')}">${this.escape(library.install_path || 'Not linked')}</strong></div>
                </div>
                <div class="modal-actions library-detail-actions">
                    <button id="modal-library-launch-btn" class="btn btn-success ${library.running ? 'is-running' : ''}" ${library.install_status === 'installed' && library.executable_path && !library.running ? '' : 'disabled'}><i class="fa-solid ${library.running ? 'fa-spinner fa-spin' : 'fa-play'}"></i> ${library.running ? 'Running' : 'Launch'}</button>
                    <button id="modal-library-folder-btn" class="btn btn-secondary" ${library.install_path ? '' : 'disabled'}><i class="fa-solid fa-folder-open"></i> Open Folder</button>
                    <button id="modal-library-relink-btn" class="btn btn-secondary"><i class="fa-solid fa-link"></i> Relink Executable</button>
                    <button id="modal-library-artwork-btn" class="btn btn-secondary"><i class="fa-solid fa-image"></i> Change Artwork</button>
                    <button id="modal-library-artwork-refresh-btn" class="btn btn-secondary"><i class="fa-solid fa-wand-magic-sparkles"></i> Refresh Artwork</button>
                    <button id="modal-library-artwork-reset-btn" class="btn btn-secondary"><i class="fa-solid fa-rotate-left"></i> Reset Artwork</button>
                    <button id="modal-library-remove-btn" class="btn btn-danger"><i class="fa-solid fa-trash-can"></i> Remove from Library</button>
                </div>
            </div>
        ` : '';

        return `
            <div class="modal-grid">
                <div>
                    <div class="modal-cover">
                        <img src="${this.escape(coverImg)}" alt="${safeTitle}" onerror="this.src='${this.fallbackCover}'">
                    </div>
                    ${downloadCalculatorHTML}
                </div>
                <div>
                    <h2 class="modal-title">${safeTitle}</h2>
                    <ul class="modal-meta-list">
                        <li class="modal-meta-item"><span class="meta-label">Genres</span><span class="meta-value">${this.escape(game.genres || 'N/A')}</span></li>
                        <li class="modal-meta-item"><span class="meta-label">Companies</span><span class="meta-value">${this.escape(game.companies || 'N/A')}</span></li>
                        <li class="modal-meta-item"><span class="meta-label">Languages</span><span class="meta-value">${this.escape(game.languages || 'N/A')}</span></li>
                        <li class="modal-meta-item"><span class="meta-label">Original Size</span><span class="meta-value">${this.escape(game.original_size || 'N/A')}</span></li>
                        <li class="modal-meta-item"><span class="meta-label">Source Size</span><span class="meta-value meta-value-strong text-green">${this.escape(game.repack_size || 'N/A')}</span></li>
                        <li class="modal-meta-item"><span class="meta-label">Release Date</span><span class="meta-value">${game.date ? new Date(game.date).toLocaleDateString() : 'N/A'}</span></li>
                    </ul>
                    <div class="modal-actions">
                        ${primaryLaunchHTML}
                        <button id="modal-download-btn" class="btn ${downloadBtnClass}" ${downloadBtnDisabled}><i class="fa-solid fa-magnet"></i> ${downloadBtnText}</button>
                        <button id="modal-wishlist-btn" class="btn btn-star-wishlist ${isWishlisted ? 'active' : ''}"><i class="fa-${isWishlisted ? 'solid' : 'regular'} fa-star"></i> ${isWishlisted ? 'Wishlisted' : 'Add to Wishlist'}</button>
                        <button id="modal-save-offline-btn" class="btn btn-secondary"><i class="fa-solid fa-box-archive"></i> Save to Library</button>
                        <button id="modal-check-updates-btn" class="btn btn-secondary"><i class="fa-solid fa-rotate"></i> Check for Updates</button>
                        ${game.url ? `<a href="${this.escape(game.url)}" class="btn btn-secondary" target="_blank"><i class="fa-solid fa-database"></i> Open Source Page</a>` : ''}
                    </div>
                    ${officialLinks ? `<div class="detail-section"><h3>Official Links</h3><div class="mirrors-list">${officialLinks}</div></div>` : ''}
                    ${libraryHTML}
                    ${spaceWarningHTML}
                    ${compatibilityPanelHTML}
                    ${game.description ? `<div class="detail-section"><h3>Game Description</h3><p class="detail-text">${this.escape(game.description)}</p></div>` : ''}
                    ${game.file_list ? `<div class="detail-section"><h3>Selectable Files Listed By Source</h3><div class="file-list-box">${this.escape(game.file_list)}</div></div>` : ''}
                    ${featuresHTML}
                    ${updatesHTML}
                    ${torrentMirrorsHTML}
                    ${directMirrorsHTML}
                    ${screenshotsHTML}
                </div>
            </div>
        `;
    },

    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icon = type === 'success' ? 'fa-check' : 'fa-triangle-exclamation';
        toast.innerHTML = `<i class="fa-solid ${icon} toast-icon"></i><span>${this.escape(message)}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};
