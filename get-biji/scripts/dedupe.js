#!/usr/bin/env node

/**
 * Get Notes Deduplication Tool
 *
 * Scans the notes directory and removes duplicate files based on `note_id`.
 * Keeps the largest file (assuming it's the most complete one).
 */

const fs = require('fs');
const path = require('path');

// Configuration
// Default to ./notes in the current directory if not specified
const NOTES_DIR = process.env.OUTPUT_DIR || path.join(process.cwd(), 'notes');

function extractNoteId(filepath) {
    try {
        const content = fs.readFileSync(filepath, 'utf8');
        const match = content.match(/note_id:\s*(\d+)/);
        return match ? match[1] : null;
    } catch (e) {
        return null;
    }
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    return (bytes / 1024).toFixed(1) + ' KB';
}

function main() {
    console.log('========================================');
    console.log('   Get Notes Deduplication');
    console.log('========================================\n');

    if (!fs.existsSync(NOTES_DIR)) {
        console.error(`❌ Notes directory not found: ${NOTES_DIR}`);
        console.log('   Please run this script from the parent of your notes folder or set OUTPUT_DIR.');
        return;
    }

    console.log(`🔍 Scanning directory: ${NOTES_DIR}...\n`);

    const files = fs.readdirSync(NOTES_DIR).filter(f => f.endsWith('.md'));
    const noteMap = new Map();
    let validFiles = 0;

    files.forEach(file => {
        const filepath = path.join(NOTES_DIR, file);
        const noteId = extractNoteId(filepath);

        if (noteId) {
            if (!noteMap.has(noteId)) {
                noteMap.set(noteId, []);
            }
            const stats = fs.statSync(filepath);
            noteMap.get(noteId).push({
                file,
                filepath,
                size: stats.size,
                mtime: stats.mtimeMs
            });
            validFiles++;
        }
    });

    console.log(`📁 Found ${validFiles} valid note files\n`);

    // Find duplicates
    const duplicates = Array.from(noteMap.entries()).filter(([_, files]) => files.length > 1);

    if (duplicates.length === 0) {
        console.log('✅ No duplicates found. Clean!');
        return;
    }

    console.log(`⚠️ Found ${duplicates.length} sets of duplicates\n`);
    let deletedCount = 0;

    duplicates.forEach(([noteId, files]) => {
        // Sort by size (descending), then by mtime (newest first)
        files.sort((a, b) => {
            if (b.size !== a.size) return b.size - a.size; // Keep larger file
            return b.mtime - a.mtime; // Keep newer file
        });

        const keep = files[0];
        const remove = files.slice(1);

        console.log(`📝 Note ID: ${noteId}`);
        console.log(`   Keep:   ${keep.file} (${formatSize(keep.size)})`);

        remove.forEach(f => {
            console.log(`   Delete: ${f.file} (${formatSize(f.size)})`);
            fs.unlinkSync(f.filepath);
            deletedCount++;
        });
        console.log('');
    });

    console.log('========================================');
    console.log(`📊 Deduplication Complete!`);
    console.log(`   🗑️ Deleted: ${deletedCount} files`);
    console.log('========================================\n');
}

main();
