#!/usr/bin/env node

/**
 * Get Notes Auto Sync v3
 *
 * Orchestrator: imports api.js (auth + fetch) and format.js (formatting + chapter injection).
 *
 * Output structure:
 *   <OUTPUT_DIR>/YYYY-MM-DD/HHMMSS_title.md         ← Summary (short transcripts inlined)
 *   <OUTPUT_DIR>/YYYY-MM-DD/HHMMSS_title_原文.md     ← Structured transcript with chapter headings (long only)
 */

const fs = require('fs');
const path = require('path');

const {
    fetchAllNotes,
    fetchNoteDetail,
    loadSyncState,
    saveSyncState,
    delay,
} = require('./api');

const {
    safeName,
    parseStartTimeMs,
    parseChapters,
    buildTranscript,
    needsSeparateTranscript,
    buildSummaryMarkdown,
    buildTranscriptMarkdown,
} = require('./format');

const { STATE_FILES, readState, resolveOutputDir } = require('./paths');

// ============================================================
// Config
// ============================================================

const TEST_LIMIT = process.env.TEST_LIMIT ? parseInt(process.env.TEST_LIMIT) : 0; // 0 = sync all
const SINCE_DATE = process.env.SINCE_DATE || ''; // Only sync notes from this date onwards ('' = all)

// ============================================================
// Save a single note
// ============================================================

function saveNote(note, originalData, outputDir) {
    const createdDate = note.created_at || '';
    const dateStr = createdDate.split(' ')[0] || 'unknown-date';
    // Use HHMMSS (6 digits) for better uniqueness
    const rawTime = createdDate.split(' ')[1] || '00:00:00';
    const timeStr = rawTime.substring(0, 8).replace(/:/g, '');
    const safeTitle = safeName(note.title);
    let baseName = `${timeStr}_${safeTitle}`;

    // Create date directory
    const dateDir = path.join(outputDir, dateStr);
    if (!fs.existsSync(dateDir)) {
        fs.mkdirSync(dateDir, { recursive: true });
    }

    // Collision detection: if file exists, append counter
    if (fs.existsSync(path.join(dateDir, `${baseName}.md`))) {
        let counter = 2;
        while (fs.existsSync(path.join(dateDir, `${baseName}_${counter}.md`))) {
            counter++;
        }
        baseName = `${baseName}_${counter}`;
    }

    // Parse chapters from note content
    const chapters = parseChapters(note.content);

    // Compute recording start time for absolute timestamps
    const startTimeMs = parseStartTimeMs(note.created_at);

    // Build transcript with chapter injection + absolute timestamps
    const transcript = buildTranscript(originalData, chapters, startTimeMs);

    // Determine inline vs separate
    const separate = needsSeparateTranscript(transcript);
    const transcriptFilename = separate ? `${baseName}_原文.md` : null;

    // Write summary file
    const summaryMd = buildSummaryMarkdown(note, transcript, transcriptFilename, startTimeMs);
    const summaryPath = path.join(dateDir, `${baseName}.md`);
    fs.writeFileSync(summaryPath, summaryMd, 'utf8');

    // Write transcript file (if separate)
    if (separate && transcript) {
        const summaryFilename = `${baseName}.md`;
        const transcriptMd = buildTranscriptMarkdown(note, transcript, summaryFilename);
        fs.writeFileSync(path.join(dateDir, transcriptFilename), transcriptMd, 'utf8');
    }

    return {
        dateStr,
        summaryFilename: `${baseName}.md`,
        hasTranscript: !!transcript,
        separateTranscript: separate,
    };
}

// ============================================================
// Main sync loop
// ============================================================

async function main() {
    console.log('========================================');
    console.log('   Get Notes Auto Sync v3');
    console.log('========================================\n');

    const outputDir = resolveOutputDir();
    console.log(`📁 Notes directory: ${outputDir}\n`);

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    // Load sync state; it belongs to one notes directory, so a new directory starts from scratch
    const state = loadSyncState();
    const sameDir = !state.outputDir || state.outputDir === outputDir;
    if (!sameDir) {
        console.log(`📂 Notes directory changed (was ${state.outputDir}): syncing everything into the new one\n`);
    }
    const syncedIds = new Set(sameDir ? state.syncedIds || [] : []);
    console.log(`📊 Previously synced: ${syncedIds.size} notes\n`);

    // fullSyncAt: when a sync without SINCE_DATE last finished with every note in the account on disk.
    // Notes that reach Get later (recorder uploads can lag by days) are only picked up by the next such sync.
    let fullSyncAt = sameDir ? state.fullSyncAt : undefined;
    const save = () => saveSyncState({
        outputDir,
        fullSyncAt,
        syncedIds: Array.from(syncedIds),
        lastSyncTime: new Date().toISOString(),
    });

    // Fetch all notes list
    const allNotes = await fetchAllNotes();

    // Filter by date (only notes from SINCE_DATE onwards)
    const dateFiltered = allNotes.filter(n => {
        const dateStr = (n.created_at || '').split(' ')[0] || '';
        return dateStr >= SINCE_DATE;
    });
    console.log(`📅 Notes from ${SINCE_DATE || 'the beginning'}: ${dateFiltered.length} (skipped ${allNotes.length - dateFiltered.length} older)`);

    // Filter new notes (not yet synced), skipping temporary notes made by link-transcript.js
    const skipIds = new Set(readState(STATE_FILES.transcriptLedger, []));
    const newNotes = dateFiltered.filter(n => !syncedIds.has(n.note_id) && !skipIds.has(n.note_id));
    console.log(`🆕 New notes to sync: ${newNotes.length}\n`);

    if (newNotes.length === 0) {
        if (!SINCE_DATE) {
            fullSyncAt = new Date().toISOString();
            save();
        }
        console.log('✅ All up to date.');
        return;
    }

    // Apply test limit
    const toSync = TEST_LIMIT > 0 ? newNotes.slice(0, TEST_LIMIT) : newNotes;
    if (TEST_LIMIT > 0) {
        console.log(`🧪 Test mode: syncing ${toSync.length} of ${newNotes.length} notes\n`);
    }

    // Sync loop
    console.log('📥 Starting sync...\n');
    let savedCount = 0;
    let transcriptCount = 0;
    let separateCount = 0;
    const failed = [];

    for (let i = 0; i < toSync.length; i++) {
        const note = toSync[i];
        const dateStr = note.created_at?.split(' ')[0] || '';
        console.log(`[${i + 1}/${toSync.length}] ${dateStr} ${note.title || 'Untitled'}`);

        try {
            // Fetch detail + original transcript
            const { detail, originalData } = await fetchNoteDetail(note.note_id);

            // Save with chapter injection
            const result = saveNote(detail, originalData, outputDir);

            const status = [];
            if (result.hasTranscript) {
                transcriptCount++;
                status.push(result.separateTranscript ? '原文(separate)' : '原文(inline)');
                if (result.separateTranscript) separateCount++;
            }
            console.log(`  ✅ ${path.join(outputDir, result.dateStr, result.summaryFilename)} ${status.join(' ')}`);

            // Track synced
            syncedIds.add(note.note_id);
            savedCount++;

            // Incremental state save: an interrupted run resumes where it stopped
            save();

        } catch (e) {
            console.log(`  ⚠️ Failed: ${e.message}`);
            failed.push(`${dateStr} ${note.title || 'Untitled'}: ${e.message}`);
        }

        if (i < toSync.length - 1) await delay(500);
    }

    if (!SINCE_DATE && toSync.length === newNotes.length && failed.length === 0) {
        fullSyncAt = new Date().toISOString();
        save();
    }

    console.log('\n========================================');
    console.log(failed.length ? `📊 Sync finished with ${failed.length} failed` : `📊 Sync Completed`);
    console.log(`   ✅ Saved: ${savedCount}`);
    console.log(`   📝 With Transcripts: ${transcriptCount} (${separateCount} separate, ${transcriptCount - separateCount} inline)`);
    if (failed.length) {
        console.log(`   ⚠️ Failed: ${failed.length} (run again to retry only these)`);
        failed.forEach(f => console.log(`      - ${f}`));
        process.exitCode = 1;
    }
    console.log('========================================\n');
}

main().catch(e => {
    console.error(`❌ ${e.message}`);
    process.exit(1);
});
