#!/usr/bin/env node

/**
 * Rebuild sync state from the notes already on disk.
 * Notes found in the notes directory are marked as synced; the rest are left for the next sync.js run.
 * Use it when the sync state is lost (new machine, deleted ~/.config/get-biji) but the notes directory is intact.
 */

const fs = require('fs');
const path = require('path');
const { fetchAllNotes, saveSyncState } = require('./api');
const { safeName } = require('./format');
const { resolveOutputDir } = require('./paths');

async function main() {
    const outputDir = resolveOutputDir();
    console.log(`🔄 Rebuilding sync state from ${outputDir}...\n`);

    const allNotes = await fetchAllNotes();
    const onDisk = [];
    const missing = [];

    for (const note of allNotes) {
        const dateStr = (note.created_at || '').split(' ')[0] || 'unknown-date';
        const rawTime = (note.created_at || '').split(' ')[1] || '00:00:00';
        const timeStr = rawTime.substring(0, 8).replace(/:/g, '');
        const filePath = path.join(outputDir, dateStr, `${timeStr}_${safeName(note.title)}.md`);
        (fs.existsSync(filePath) ? onDisk : missing).push(note);
    }

    saveSyncState({
        outputDir,
        fullSyncAt: missing.length === 0 ? new Date().toISOString() : undefined,
        syncedIds: onDisk.map(n => n.note_id),
        lastSyncTime: new Date().toISOString(),
    });

    console.log(`📊 Notes in Get: ${allNotes.length}`);
    console.log(`   On disk (marked as synced): ${onDisk.length}`);
    console.log(`   Missing (next sync.js run fetches them): ${missing.length}`);
}

main().catch(e => {
    console.error(`❌ ${e.message}`);
    process.exit(1);
});
