#!/usr/bin/env node

/**
 * Rebuild sync state from API note list.
 * - ALL notes (including pre-2026) are marked as synced to prevent re-download
 * - Only 2026+ notes are checked for disk existence and reported as missing
 */

const fs = require('fs');
const path = require('path');
const { fetchAllNotes, saveSyncState } = require('./api');
const { safeName } = require('./format');

const OUTPUT_DIR = process.env.OUTPUT_DIR || path.join(process.cwd(), 'notes');
const SINCE_DATE = process.env.SINCE_DATE || '2026-01-01';

async function main() {
    console.log('🔄 Rebuilding sync state from API...\n');

    const allNotes = await fetchAllNotes();
    const getDir = OUTPUT_DIR;

    let onDisk = 0;
    let missing = 0;
    let skippedOld = 0;
    const missingNotes = [];

    for (const note of allNotes) {
        const dateStr = (note.created_at || '').split(' ')[0] || 'unknown-date';

        // Pre-2026: skip disk check, just count
        if (dateStr < SINCE_DATE) {
            skippedOld++;
            continue;
        }

        // 2026+: check if file exists on disk
        const rawTime = (note.created_at || '').split(' ')[1] || '00:00:00';
        const timeStr = rawTime.substring(0, 8).replace(/:/g, '');
        const safeTitle = safeName(note.title);
        const baseName = `${timeStr}_${safeTitle}`;
        const filePath = path.join(getDir, dateStr, `${baseName}.md`);

        if (fs.existsSync(filePath)) {
            onDisk++;
        } else {
            missing++;
            missingNotes.push({ note_id: note.note_id, date: dateStr, title: note.title });
        }
    }

    console.log(`\n📊 Results:`);
    console.log(`   Total notes in API: ${allNotes.length}`);
    console.log(`   Pre-${SINCE_DATE} (skipped): ${skippedOld}`);
    console.log(`   ${SINCE_DATE}+ on disk: ${onDisk}`);
    console.log(`   ${SINCE_DATE}+ missing: ${missing}`);

    if (missing > 0) {
        console.log(`\n📋 Missing notes:`);
        for (const n of missingNotes) {
            console.log(`   - ${n.date} ${n.title} (${n.note_id})`);
        }
    }

    // Mark ALL notes as synced (old + on-disk)
    // Missing 2026+ notes are NOT marked, so sync.js will fetch them
    const missingIds = new Set(missingNotes.map(n => n.note_id));
    const syncedIds = allNotes
        .filter(n => !missingIds.has(n.note_id))
        .map(n => n.note_id);

    saveSyncState({
        syncedIds,
        lastSyncTime: new Date().toISOString(),
    });

    console.log(`\n✅ Sync state rebuilt: ${syncedIds.length} marked as synced`);
    if (missing > 0) {
        console.log(`   Run sync.js to fetch the ${missing} missing notes`);
    }
}

main().catch(console.error);
