/**
 * 登录态、同步记录和笔记目录的设置都存在 skill 目录之外：重装或更新 skill 时，skill 目录会被整个换掉。
 * 位置：$GET_BIJI_HOME，默认 ~/.config/get-biji/
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

const STATE_DIR = process.env.GET_BIJI_HOME || path.join(os.homedir(), '.config', 'get-biji');
const CONFIG_FILE = path.join(STATE_DIR, 'config.json');

const STATE_FILES = {
    authState: path.join(STATE_DIR, 'auth-state.json'),
    tokenCache: path.join(STATE_DIR, 'token-cache.json'),
    syncState: path.join(STATE_DIR, 'sync-state.json'),
    transcriptLedger: path.join(STATE_DIR, 'link-transcript-ids.json'),
};

function readState(file, fallback) {
    try {
        return JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
        return fallback;
    }
}

function writeState(file, data) {
    fs.mkdirSync(STATE_DIR, { recursive: true, mode: 0o700 });
    fs.writeFileSync(file, JSON.stringify(data, null, 2), { encoding: 'utf8', mode: 0o600 });
}

/**
 * 笔记目录：带了 OUTPUT_DIR 就用它并记下来；没带就用上次记下的；都没有就报错，由 agent 去问用户。
 */
function resolveOutputDir() {
    const config = readState(CONFIG_FILE, {});
    let dir = process.env.OUTPUT_DIR;
    if (!dir) {
        if (config.outputDir) return config.outputDir;
        throw new Error(`No notes directory yet. Run once with OUTPUT_DIR="<absolute path>"; it is then remembered in ${CONFIG_FILE}`);
    }
    if (dir.startsWith('~/')) dir = path.join(os.homedir(), dir.slice(2));
    if (!path.isAbsolute(dir)) throw new Error(`OUTPUT_DIR must be an absolute path, got: ${dir}`);
    if (config.outputDir !== dir) writeState(CONFIG_FILE, { ...config, outputDir: dir });
    return dir;
}

module.exports = { STATE_DIR, CONFIG_FILE, STATE_FILES, readState, writeState, resolveOutputDir };
