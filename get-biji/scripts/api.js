#!/usr/bin/env node

/**
 * Get Notes API Client
 * Auth chain: cached JWT → refresh_token (90d) → Playwright browser login
 * Logs go to stderr so that callers' stdout stays clean.
 */

const fs = require('fs');
const { STATE_FILES, readState, writeState } = require('./paths');

const CONFIG = {
    baseUrl: 'https://get-notes.luojilab.com',
    authApiUrl: 'https://notes-api.biji.com',
    loginUrl: 'https://www.biji.com/note',
    refreshEndpoint: '/account/v2/web/user/auth/refresh',
    listEndpoint: '/voicenotes/web/notes',
    detailEndpoint: '/voicenotes/web/notes/',
    originalEndpoint: '/voicenotes/web/notes/',
    pageSize: 20,
    delayMs: 500,

    authStateFile: STATE_FILES.authState,
    tokenCacheFile: STATE_FILES.tokenCache,
    syncStateFile: STATE_FILES.syncState,

    loginTimeoutMs: 10 * 60 * 1000,
};

// In-process JWT and its expiry (unix seconds; 0 = unknown)
let token = null;
let tokenExpireAt = 0;

function useToken(t, expireAt) {
    token = t;
    tokenExpireAt = expireAt ? Number(expireAt) : 0;
    return token;
}

function loadTokenCache() {
    return readState(CONFIG.tokenCacheFile, null);
}

function saveTokenCache(data) {
    writeState(CONFIG.tokenCacheFile, {
        token: data.token,
        tokenExpireAt: data.tokenExpireAt || null,
        refreshToken: data.refreshToken || null,
        refreshTokenExpireAt: data.refreshTokenExpireAt || null,
        savedAt: new Date().toISOString(),
    });
}

/**
 * Try silent refresh using refresh_token (valid ~90 days).
 * Returns new JWT or null on failure.
 */
async function silentRefresh(refreshToken) {
    try {
        const url = `${CONFIG.authApiUrl}${CONFIG.refreshEndpoint}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return null;

        const data = await res.json();
        const t = data?.c?.token;
        if (!t?.token) return null;

        saveTokenCache({
            token: t.token,
            tokenExpireAt: t.token_expire_at,
            refreshToken: t.refresh_token,
            refreshTokenExpireAt: t.refresh_token_expire_at,
        });

        console.error('🔄 Token refreshed silently.');
        return useToken(t.token, t.token_expire_at);
    } catch {
        return null;
    }
}

/**
 * Get refresh_token from cache or from .auth-state.json localStorage.
 */
function getRefreshToken(cache) {
    // Prefer cache file
    if (cache?.refreshToken && cache?.refreshTokenExpireAt) {
        if (Date.now() / 1000 < cache.refreshTokenExpireAt - 300) {
            return cache.refreshToken;
        }
    }
    // Fallback: extract from auth-state localStorage
    if (fs.existsSync(CONFIG.authStateFile)) {
        try {
            const state = JSON.parse(fs.readFileSync(CONFIG.authStateFile, 'utf8'));
            const origin = state.origins?.find(o => o.origin?.includes('biji.com'));
            if (!origin) return null;
            const rtItem = origin.localStorage?.find(i => i.name === 'refresh_token');
            const rtExpItem = origin.localStorage?.find(i => i.name === 'refresh_token_expire_at');
            const rtExp = rtExpItem ? parseInt(rtExpItem.value) : 0;
            if (rtItem?.value && Date.now() / 1000 < rtExp - 300) {
                return rtItem.value;
            }
        } catch { }
    }
    return null;
}

/**
 * Returns a JWT that is valid for at least 5 more minutes.
 * force: skip the in-process and cached JWT (the server rejected it), go straight to refresh.
 */
async function getToken({ force = false } = {}) {
    const fresh = exp => !exp || Date.now() / 1000 < Number(exp) - 300;

    if (!force && token && fresh(tokenExpireAt)) return token;

    const cache = loadTokenCache();

    // 1. Try cached JWT (still valid for >5 min)
    if (!force && cache?.token && cache.tokenExpireAt && fresh(cache.tokenExpireAt)) {
        return useToken(cache.token, cache.tokenExpireAt);
    }

    // 2. Try silent refresh via refresh_token (~90 day validity)
    const refreshTk = getRefreshToken(cache);
    if (refreshTk) {
        const newToken = await silentRefresh(refreshTk);
        if (newToken) return newToken;
    }

    // 3. Last resort: browser login
    return browserLogin();
}

async function browserLogin() {
    console.error('🔐 Login required: opening a browser window, log in to biji.com there (waiting up to 10 min)...');
    let browser;
    try {
        const { chromium } = require('playwright');
        browser = await chromium.launch({ headless: false });
    } catch (e) {
        throw new Error(`Cannot open a browser for login. It needs a desktop session, plus "npm install && npx playwright install chromium" in the skill folder. ${e.message.split('\n')[0]}`);
    }

    try {
        const context = fs.existsSync(CONFIG.authStateFile)
            ? await browser.newContext({ storageState: CONFIG.authStateFile })
            : await browser.newContext();
        const page = await context.newPage();
        await page.goto(CONFIG.loginUrl, { waitUntil: 'networkidle' });

        const loggedIn = () => page.evaluate(() => !!localStorage.getItem('token'));
        const deadline = Date.now() + CONFIG.loginTimeoutMs;
        let isLoggedIn = await loggedIn();
        while (!isLoggedIn) {
            if (Date.now() > deadline) throw new Error('Login not completed within 10 minutes. Run the command again to retry.');
            await delay(2000);
            try {
                isLoggedIn = await loggedIn();
            } catch {
                throw new Error('The login window was closed before login finished. Run the command again to retry.');
            }
        }
        console.error('✅ Login successful');

        const authInfo = await page.evaluate(() => ({
            token: localStorage.getItem('token'),
            tokenExpireAt: localStorage.getItem('token_expire_at'),
            refreshToken: localStorage.getItem('refresh_token'),
            refreshTokenExpireAt: localStorage.getItem('refresh_token_expire_at'),
        }));

        writeState(CONFIG.authStateFile, await context.storageState());
        saveTokenCache({
            token: authInfo.token,
            tokenExpireAt: authInfo.tokenExpireAt ? parseInt(authInfo.tokenExpireAt) : null,
            refreshToken: authInfo.refreshToken || null,
            refreshTokenExpireAt: authInfo.refreshTokenExpireAt ? parseInt(authInfo.refreshTokenExpireAt) : null,
        });
        return useToken(authInfo.token, authInfo.tokenExpireAt);
    } finally {
        await browser.close().catch(() => { });
    }
}

async function fetchWithAuth(url, { retried = false } = {}) {
    const t = await getToken({ force: retried });
    const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${t}`, 'Accept': 'application/json' }
    });

    const data = response.ok ? await response.json() : null;
    const expired = response.status === 401 || data?.message === 'LoginRequired';
    if (expired && !retried) return fetchWithAuth(url, { retried: true });
    if (expired) throw new Error('Token expired and could not be refreshed');
    if (!response.ok) throw new Error(`API Error: ${response.status}`);

    return data;
}

function delay(ms) {
    return new Promise(r => setTimeout(r, ms));
}

/**
 * Fetch all notes from the API using cursor pagination.
 * Returns an array of unique note objects (list-level data, no detail).
 */
async function fetchAllNotes() {
    let allNotes = [];
    let sinceId = null;
    let hasMore = true;

    console.error('📋 Fetching notes list...');

    while (hasMore) {
        let url = `${CONFIG.baseUrl}${CONFIG.listEndpoint}?limit=${CONFIG.pageSize}&sort=create_desc`;
        if (sinceId) url += `&since_id=${sinceId}`;

        const data = await fetchWithAuth(url);
        const notes = data.c.list || [];

        if (notes.length === 0) {
            hasMore = false;
        } else {
            process.stderr.write('.');
            allNotes = allNotes.concat(notes);
            sinceId = notes[notes.length - 1].note_id;
            await delay(CONFIG.delayMs);
        }
    }

    // Deduplicate by note_id
    const seenIds = new Set();
    const uniqueById = allNotes.filter(n => {
        if (seenIds.has(n.note_id)) return false;
        seenIds.add(n.note_id);
        return true;
    });

    // Deduplicate by created_at + title (API returns same content under different note_ids)
    const seenContent = new Set();
    const unique = uniqueById.filter(n => {
        const key = `${n.created_at || ''}|${n.title || ''}`;
        if (seenContent.has(key)) return false;
        seenContent.add(key);
        return true;
    });

    const dupeCount = uniqueById.length - unique.length;
    console.error(`\n📁 Found ${uniqueById.length} notes (${dupeCount} content duplicates removed) → ${unique.length} unique.\n`);
    return unique;
}

/**
 * Fetch note detail + original transcript for a single note.
 */
async function fetchNoteDetail(noteId) {
    const detailUrl = `${CONFIG.baseUrl}${CONFIG.detailEndpoint}${noteId}`;
    const detail = (await fetchWithAuth(detailUrl)).c;

    let originalData = null;
    try {
        const origUrl = `${CONFIG.baseUrl}${CONFIG.originalEndpoint}${noteId}/original`;
        originalData = (await fetchWithAuth(origUrl)).c;
    } catch (e) { }

    await delay(CONFIG.delayMs);
    return { detail, originalData };
}

// Sync state helpers
function loadSyncState() {
    return readState(CONFIG.syncStateFile, { syncedIds: [] });
}

function saveSyncState(state) {
    writeState(CONFIG.syncStateFile, state);
}

module.exports = {
    CONFIG,
    getToken,
    fetchAllNotes,
    fetchNoteDetail,
    loadSyncState,
    saveSyncState,
    delay,
};
