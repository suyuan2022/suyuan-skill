#!/usr/bin/env node

/**
 * Get Notes API Client
 * Auth chain: cached JWT → refresh_token (90d) → Playwright browser login
 */

const fs = require('fs');
const path = require('path');

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

    authStateFile: path.join(__dirname, '../.auth-state.json'),
    tokenCacheFile: path.join(__dirname, '../.token-cache.json'),
    syncStateFile: path.join(__dirname, '../.sync-state.json'),
};

let token = null;

function loadTokenCache() {
    if (!fs.existsSync(CONFIG.tokenCacheFile)) return null;
    try {
        return JSON.parse(fs.readFileSync(CONFIG.tokenCacheFile, 'utf8'));
    } catch { return null; }
}

function saveTokenCache(data) {
    fs.writeFileSync(CONFIG.tokenCacheFile, JSON.stringify({
        token: data.token,
        tokenExpireAt: data.tokenExpireAt || null,
        refreshToken: data.refreshToken || null,
        refreshTokenExpireAt: data.refreshTokenExpireAt || null,
        savedAt: new Date().toISOString(),
    }, null, 2), 'utf8');
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

        console.log('🔄 Token refreshed silently.');
        return t.token;
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

async function getToken() {
    if (token) return token;

    const cache = loadTokenCache();

    // 1. Try cached JWT (still valid for >5 min)
    if (cache?.tokenExpireAt && Date.now() / 1000 < cache.tokenExpireAt - 300) {
        token = cache.token;
        return token;
    }

    // 2. Try silent refresh via refresh_token (~90 day validity)
    const refreshTk = getRefreshToken(cache);
    if (refreshTk) {
        const newToken = await silentRefresh(refreshTk);
        if (newToken) {
            token = newToken;
            return token;
        }
    }

    // 3. Last resort: open browser
    console.log('🔐 Token and refresh_token both expired. Launching browser...');
    const { chromium } = require('playwright');

    const browser = await chromium.launch({ headless: false });
    const context = fs.existsSync(CONFIG.authStateFile)
        ? await browser.newContext({ storageState: CONFIG.authStateFile })
        : await browser.newContext();

    const page = await context.newPage();
    await page.goto(CONFIG.loginUrl, { waitUntil: 'networkidle' });

    let isLoggedIn = await page.evaluate(() => !!localStorage.getItem('token'));

    if (!isLoggedIn) {
        console.log('\n  ⏳ Please log in via the browser window...\n');
        while (!isLoggedIn) {
            await new Promise(r => setTimeout(r, 2000));
            isLoggedIn = await page.evaluate(() => !!localStorage.getItem('token'));
        }
        console.log('  ✅ Login successful!');
    }

    const authInfo = await page.evaluate(() => ({
        token: localStorage.getItem('token'),
        tokenExpireAt: localStorage.getItem('token_expire_at'),
        refreshToken: localStorage.getItem('refresh_token'),
        refreshTokenExpireAt: localStorage.getItem('refresh_token_expire_at'),
    }));

    token = authInfo.token;

    await context.storageState({ path: CONFIG.authStateFile });
    saveTokenCache({
        token: authInfo.token,
        tokenExpireAt: authInfo.tokenExpireAt ? parseInt(authInfo.tokenExpireAt) : null,
        refreshToken: authInfo.refreshToken || null,
        refreshTokenExpireAt: authInfo.refreshTokenExpireAt ? parseInt(authInfo.refreshTokenExpireAt) : null,
    });

    await browser.close();
    return token;
}

async function fetchWithAuth(url) {
    const t = await getToken();
    const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${t}`, 'Accept': 'application/json' }
    });

    if (!response.ok) throw new Error(`API Error: ${response.status}`);

    const data = await response.json();
    if (data.message === 'LoginRequired') throw new Error('Token expired');

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

    console.log('📋 Fetching notes list...');

    while (hasMore) {
        let url = `${CONFIG.baseUrl}${CONFIG.listEndpoint}?limit=${CONFIG.pageSize}&sort=create_desc`;
        if (sinceId) url += `&since_id=${sinceId}`;

        const data = await fetchWithAuth(url);
        const notes = data.c.list || [];

        if (notes.length === 0) {
            hasMore = false;
        } else {
            process.stdout.write('.');
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
    console.log(`\n📁 Found ${uniqueById.length} notes (${dupeCount} content duplicates removed) → ${unique.length} unique.\n`);
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
    if (fs.existsSync(CONFIG.syncStateFile)) {
        return JSON.parse(fs.readFileSync(CONFIG.syncStateFile, 'utf8'));
    }
    return { syncedIds: [] };
}

function saveSyncState(state) {
    fs.writeFileSync(CONFIG.syncStateFile, JSON.stringify(state, null, 2), 'utf8');
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
