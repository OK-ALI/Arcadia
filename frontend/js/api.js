/**
 * api.js - API client for Arcadia Core.
 */

const API = {
    async _request(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, options);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || `HTTP error! Status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    },

    async search(query, page = 1) {
        return this._request(`/api/search?q=${encodeURIComponent(query)}&page=${page}`);
    },

    async getLatest(page = 1) {
        return this._request(`/api/latest?page=${page}`);
    },

    async getLibrary(letter = 'all', page = 1, pageSize = 48) {
        return this._request(`/api/library?letter=${encodeURIComponent(letter)}&page=${page}&page_size=${pageSize}`);
    },

    async getLibraryIndexStatus() {
        return this._request('/api/library/index');
    },

    async getLibraryArtworkStatus() {
        return this._request('/api/library/artwork');
    },

    async startLibraryArtwork(limit = 36, slugs = []) {
        return this._request('/api/library/artwork', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ limit, slugs })
        });
    },

    async hydrateLibraryRequirements(slugs = [], limit = 24) {
        return this._request('/api/library/requirements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slugs, limit })
        });
    },

    async startLibraryIndex(force = false) {
        return this._request('/api/library/index', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force })
        });
    },

    async getGameDetails(slug) {
        return this._request(`/api/game/${slug}`);
    },

    async triggerDownload(slug) {
        return this._request(`/api/download/${slug}`, { method: 'POST' });
    },

    async prepareDownload(slug, savePath = '') {
        return this._request(`/api/download/prepare/${slug}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ save_path: savePath })
        });
    },

    async getPrepareStatus(preparedId) {
        return this._request(`/api/download/prepare-status/${encodeURIComponent(preparedId)}`);
    },

    async confirmDownload(payload) {
        return this._request('/api/torrent/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    },

    async getTorrentStatus() {
        return this._request('/api/torrent/status');
    },

    async controlTorrent(infoHash, action) {
        return this._request('/api/torrent/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ info_hash: infoHash, action })
        });
    },

    async setTorrentPriority(infoHash, priority) {
        return this._request('/api/torrent/priority', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ info_hash: infoHash, priority })
        });
    },

    async reorderTorrent(infoHash, direction) {
        return this._request('/api/torrent/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ info_hash: infoHash, direction })
        });
    },

    async getTorrentSettings() {
        return this._request('/api/torrent/settings');
    },

    async updateTorrentSettings(settings) {
        return this._request('/api/torrent/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
    },

    async getPopular() {
        return this._request('/api/popular');
    },

    async getUpcoming() {
        return this._request('/api/upcoming');
    },

    async getNews(forceRefresh = false) {
        return this._request(`/api/news${forceRefresh ? '?refresh=1' : ''}`);
    },

    async clearCache() {
        return this._request('/api/cache/clear', { method: 'POST' });
    },

    async getSystemSpecs() {
        return this._request('/api/system/specs');
    },

    async getDrivesInfo() {
        return this._request('/api/system/drives');
    },

    async getPingStatus() {
        return this._request('/api/system/ping');
    },

    async getOfflineCatalog() {
        return this._request('/api/offline/library');
    },

    async saveGameOffline(slug) {
        return this._request(`/api/offline/save/${slug}`, { method: 'POST' });
    },

    async getOfflineStats() {
        return this._request('/api/offline/stats');
    },

    async updateOfflineUser(slug, payload) {
        return this._request(`/api/offline/user/${slug}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    },

    async exportOfflineData() {
        return this._request('/api/offline/export');
    },

    async importOfflineData(payload) {
        return this._request('/api/offline/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    },

    async pruneOfflineMedia() {
        return this._request('/api/offline/prune-media', { method: 'POST' });
    }
};


