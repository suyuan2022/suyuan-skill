#!/usr/bin/env node

/**
 * Get Notes Deduplication Tool
 *
 * Finds summary files that share a `note_id` anywhere under the notes directory,
 * keeps the largest one, and deletes the rest together with their `_原文.md` transcript file.
 * A summary and its own `_原文.md` share a note_id by design, so transcript files are never compared.
 */

const fs = require('fs');
const path = require('path');
const { resolveOutputDir } = require('./paths');

const TRANSCRIPT_SUFFIX = '_原文.md';

function listSummaryFiles(dir) {
    return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) return listSummaryFiles(full);
        return entry.name.endsWith('.md') && !entry.name.endsWith(TRANSCRIPT_SUFFIX) ? [full] : [];
    });
}

function frontmatterField(content, field) {
    const match = content.match(new RegExp(`^${field}:\\s*"?([^"\\n]+)"?`, 'm'));
    return match ? match[1].trim() : null;
}

function main() {
    const notesDir = resolveOutputDir();
    if (!fs.existsSync(notesDir)) {
        throw new Error(`Notes directory not found: ${notesDir}`);
    }
    console.log(`🔍 Scanning ${notesDir}...\n`);

    const byNoteId = new Map();
    for (const file of listSummaryFiles(notesDir)) {
        const content = fs.readFileSync(file, 'utf8');
        const noteId = frontmatterField(content, 'note_id');
        if (!noteId) continue;
        const stats = fs.statSync(file);
        const entry = { file, size: stats.size, mtime: stats.mtimeMs, transcript: frontmatterField(content, 'transcript') };
        byNoteId.set(noteId, [...(byNoteId.get(noteId) || []), entry]);
    }

    const duplicates = [...byNoteId.entries()].filter(([, files]) => files.length > 1);
    if (duplicates.length === 0) {
        console.log('✅ No duplicates found.');
        return;
    }

    let deleted = 0;
    for (const [noteId, files] of duplicates) {
        files.sort((a, b) => b.size - a.size || b.mtime - a.mtime);
        const [keep, ...remove] = files;
        console.log(`📝 note_id ${noteId}\n   Keep:   ${path.relative(notesDir, keep.file)}`);
        for (const f of remove) {
            const paired = f.transcript ? path.join(path.dirname(f.file), f.transcript) : null;
            for (const target of [f.file, paired]) {
                if (target && target !== keep.file && fs.existsSync(target)) {
                    console.log(`   Delete: ${path.relative(notesDir, target)}`);
                    fs.unlinkSync(target);
                    deleted++;
                }
            }
        }
    }
    console.log(`\n📊 Deleted ${deleted} files in ${duplicates.length} duplicate sets.`);
}

try {
    main();
} catch (e) {
    console.error(`❌ ${e.message}`);
    process.exit(1);
}
