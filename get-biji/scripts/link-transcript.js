#!/usr/bin/env node

/**
 * 链接 / 本地音视频 → 逐字稿：交给 Get 转写，取原文后彻底删除这条笔记。
 *
 * Usage: node scripts/link-transcript.js <url> [--json] [--keep]
 *        node scripts/link-transcript.js --file <本地路径或媒体直链> [--json] [--keep]
 *   --json  输出 JSON（给其他脚本调用）
 *   --keep  不删除笔记（调试用）
 *   --file  上传音视频让 Get 转写（ffmpeg 先抽成 mp3）。按音频时长扣每月转写额度，链接解析不扣
 *
 * 走网页版接口（逆向自 biji.com 网页，鉴权复用 sync 的 JWT），因为官方 OpenAPI 建链接笔记不能带提示词：
 * 建链接笔记（提示词让 AI 输出纠错后的全文）→ 取 /original 原始识别 →
 * 按 note_id 删除 → 按 prime_id 从回收站永久删除。
 * 只按本次创建的 id 删除；绝不调用「清空回收站」。
 * 创建过的 note_id 记进 .link-transcript-ids.json，sync.js 跳过它们。
 *
 * 各平台实测（2026-10）：
 *   抖音      按提示词出纠错稿
 *   小红书    多数能转，原文 = 笔记文案 + 话题行 + 语音；个别视频只回文案；失效链接回登录页
 *   B 站      能转（认 ?p=N 分 P）；早先只出「智能总结」，2026-10-18 实测已按提示词出纠错稿
 *   小宇宙    能转（1 小时 43 分的播客约 2 分钟），同样只出智能总结
 *   YouTube   会抓到错误语言的字幕轨，别用；微博等其他站只回网页文字，不转语音
 *   --file    任何音视频都能转，原文带逐句时间戳和说话人，AI 同样只出智能总结
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const { CONFIG, getToken } = require('./api');
const { STATE_FILES, readState, writeState } = require('./paths');

const NOTES_API = CONFIG.authApiUrl;   // notes-api.biji.com
const LEGACY_API = CONFIG.baseUrl;     // get-notes.luojilab.com
const LEDGER = STATE_FILES.transcriptLedger;

const PROMPT = '请把这条视频的语音逐字稿完整输出：只修正语音识别造成的错别字、同音字和中英文专有名词拼写（如 Claude Code、Figma、CLI），补全标点、按意思分段。不要删减、不要概括、不要改写说法、不要加标题和任何说明。';

// 纠错版短于原始识别的这个比例，视为 AI 删减了内容，改用原始识别
const MIN_CORRECTED_RATIO = 0.85;

async function headers() {
    return {
        'Content-Type': 'application/json;charset=UTF-8',
        'X-Appid': '3',
        'Authorization': `Bearer ${await getToken()}`,
    };
}

async function api(base, p, { method = 'GET', body } = {}) {
    const res = await fetch(`${base}${p}`, {
        method,
        headers: await headers(),
        body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || (data.h && data.h.c !== 0)) {
        throw new Error(`${method} ${p} → ${res.status} ${data.h?.e || ''}`.trim());
    }
    return data.c ?? data;
}

// Get 拒收带分享参数的链接（报「仅支持 HTTP 协议的链接」），统一成干净的规范链接
async function normalizeUrl(input) {
    let url = input.trim();
    if (/xhslink\.com|v\.douyin\.com|b23\.tv/.test(url)) url = (await fetch(url, { redirect: 'follow' })).url;

    const bili = url.match(/bilibili\.com\/video\/(BV\w+)/);
    if (bili) {
        const p = url.match(/[?&]p=(\d+)/);  // Get 认分 P，丢了会转成第一 P
        return `https://www.bilibili.com/video/${bili[1]}${p && p[1] !== '1' ? `?p=${p[1]}` : ''}`;
    }

    const xhs = url.match(/xiaohongshu\.com\/(?:explore|discovery\/item)\/([0-9a-f]{24})/);
    if (xhs) return `https://www.xiaohongshu.com/discovery/item/${xhs[1]}`;

    const dy = url.match(/douyin\.com\/(?:video|note)\/(\d+)/) || url.match(/modal_id=(\d+)/);
    if (dy) return `https://www.douyin.com/video/${dy[1]}`;

    const u = new URL(url);
    return `${u.origin}${u.pathname}`;
}

function remember(noteId) {
    const ids = readState(LEDGER, []);
    ids.push(noteId);
    writeState(LEDGER, ids.slice(-1000));
}

async function streamNote(apiPath, body) {
    const res = await fetch(`${LEGACY_API}${apiPath}`, {
        method: 'POST',
        headers: { ...(await headers()), Accept: 'text/event-stream' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`stream → HTTP ${res.status}`);

    let noteId = '', corrected = '', error = '';
    for (const line of (await res.text()).split('\n')) {
        if (!line.startsWith('data:')) continue;
        let ev;
        try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
        const msg = ev.data?.msg;
        if (ev.msg_type === -1 && ev.data?.note_id) {
            if (!noteId) remember(ev.data.note_id);
            noteId = ev.data.note_id;
        } else if (ev.msg_type === 1 && msg && msg !== 'stop') {
            try { corrected += JSON.parse(msg).content || ''; } catch { corrected += msg; }
        } else if (ev.code && ev.code !== 200) {
            try { error = JSON.parse(msg).err_msg || msg; } catch { error = msg || `code ${ev.code}`; }
        }
    }
    return { noteId, corrected: corrected.trim(), error };
}

function createLinkNote(url) {
    return streamNote('/voicenotes/web/notes/stream', {
        attachments: [{ size: 100, type: 'link', url }],
        content: PROMPT,
        entry_type: 'ai',
        note_type: 'link',
        source: 'web',
        client_note_id: crypto.randomUUID(),
    });
}

const mmss = ms => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
};

// 上传本地音视频（或媒体直链）转写：ffmpeg 抽 mp3 → 要上传凭证 → PUT 到 OSS → 建「本地音频」笔记 → 取逐句原文。
// 网页限制单个文件 3 小时 / 1GB；每次都按时长扣额度，同一个文件重复传也扣。
async function transcribeFile(input, { keep = false } = {}) {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'get-upload-'));
    try {
        const mp3 = path.join(tmp, 'audio.mp3');
        execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-i', input, '-vn', '-ac', '1', '-ar', '16000', '-b:a', '48k', mp3]);
        const durationMs = Math.round(1000 * parseFloat(execFileSync('ffprobe',
            ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3]).toString()));
        if (!(durationMs > 0)) throw new Error('读不出音频时长');
        if (durationMs > 3 * 3600 * 1000) throw new Error('Get 单个文件上限 3 小时');
        const buf = fs.readFileSync(mp3);
        const md5 = crypto.createHash('md5').update(buf).digest('base64');

        const tk = await api(LEGACY_API, '/voicenotes/web/notes/local_audio/token', {
            method: 'POST',
            body: { duration_ms: durationMs, local_name: 'audio.mp3', md5, size_byte: buf.length, type: 'mp3' },
        });
        let url = tk.uploaded_url;  // 同样内容传过的话直接给地址
        if (!url) {
            const ti = tk.token_info;
            const put = await fetch(ti.put_sign_url, {
                method: 'PUT',
                headers: { 'X-Oss-Callback': ti.put_callback, 'Content-Type': ti.put_content_type, 'Content-MD5': md5 },
                body: buf,
            });
            if (put.status !== 200) throw new Error(`上传失败 HTTP ${put.status}`);
            url = ti.get_url;
        }

        const { noteId, corrected, error } = await streamNote('/voicenotes/web/notes/stream_on_local_audio', {
            prompt_template_id: 'custom',
            note_id: '0',
            file_id: tk.file_id,
            attachments: [{ action_time: Date.now(), size: 0, type: 'audio', title: '', url, duration: durationMs }],
            content: '',
            entry_type: 'ai',
            note_type: 'local_audio',
            source: 'web',
            topic_id: '0',
            topic_directory_id: '0',
        });
        if (!noteId) throw new Error(`Get 转写失败：${error || '没有返回 note_id'}`);

        try {
            const original = await api(NOTES_API, `/voicenotes/web/notes/${noteId}/original`);
            const sentences = original.sentences || [];
            if (!sentences.length) throw new Error('Get 没有返回原文');
            const multi = new Set(sentences.map(x => x.speaker_id)).size > 1;
            const raw = sentences.map(x =>
                `[${mmss(x.start_ms)} - ${mmss(x.end_ms)}] ${multi ? `说话人${x.speaker_id + 1}：` : ''}${x.text}`).join('\n\n');
            return {
                title: original.title || '',
                url: input,
                text: raw,
                source: 'get-upload-raw',
                raw,
                corrected,  // 这里是 Get 的智能总结，不是纠错稿
                minutes: Math.max(1, Math.round(durationMs / 60000)),  // 实测按四舍五入到分钟扣
            };
        } finally {
            if (!keep) await purge(noteId);
        }
    } finally {
        fs.rmSync(tmp, { recursive: true, force: true });
    }
}

async function purge(noteId) {
    const note = await api(LEGACY_API, `/voicenotes/web/notes/${noteId}`);
    await api(LEGACY_API, `/voicenotes/web/notes/${noteId}`, { method: 'DELETE' });
    await api(NOTES_API, '/voicenotes/web/notes/recycle/op/batch', {
        method: 'POST',
        body: { ids_str: [note.prime_id], op: 'del' },
    });
}

function stripImages(text) {
    return text.replace(/!\[[^\]]*\]\([^)]*\)\s*/g, '').trim();
}

// 小红书的原文是「笔记文案 + 话题行 + 语音识别」，最后一个「[话题]#」之后才是语音
function xhsSpeech(raw) {
    const i = raw.lastIndexOf('[话题]#');
    return i >= 0 ? raw.slice(i + '[话题]#'.length).trim() : raw;
}

async function transcribe(input, { keep = false } = {}) {
    const url = await normalizeUrl(input);
    const { noteId, corrected, error } = await createLinkNote(url);
    if (!noteId) throw new Error(`Get 解析失败：${error || '没有返回 note_id'}`);

    try {
        const original = await api(NOTES_API, `/voicenotes/web/notes/${noteId}/original`);
        const raw = stripImages(original.content || '');
        if (!raw && !corrected) throw new Error('Get 没有返回原文');

        // 纠错稿只有语音，小红书要先切掉文案再比长度，否则会误判成删减
        const isXhs = /xiaohongshu\.com|xhslink\.com/.test(url);
        if (isXhs && /手机号登录|我已阅读并同意/.test(raw)) {
            throw new Error('小红书返回的是登录页，链接可能失效了，换一个完整的笔记链接再试');
        }
        const speech = isXhs ? xhsSpeech(raw) : raw;
        if (isXhs && speech.length < 30) {
            throw new Error('Get 只抓到了小红书的笔记文案，没有转语音；可以下载视频后用 --file 上传转写');
        }

        // B 站、小宇宙 Get 不理会提示词，回的是「智能总结」，长度也够，得单独挡掉
        const isSummary = /^\s*#+\s*\S*\s*智能总结/.test(corrected);
        const useCorrected = corrected && !isSummary && corrected.length >= speech.length * MIN_CORRECTED_RATIO;
        return {
            title: original.title || '',
            url,
            text: useCorrected ? corrected : speech,
            source: useCorrected ? 'get-corrected' : 'get-raw',
            raw,
            corrected,
        };
    } finally {
        if (!keep) await purge(noteId);
    }
}

module.exports = { transcribe, transcribeFile, normalizeUrl };

if (require.main === module) {
    const args = process.argv.slice(2);
    const isFile = args.includes('--file');
    const url = args.find(a => !a.startsWith('--'));
    if (!url) {
        console.error('Usage: node scripts/link-transcript.js <url> [--json] [--keep]\n       node scripts/link-transcript.js --file <本地路径或媒体直链> [--json] [--keep]');
        process.exit(2);
    }
    (isFile ? transcribeFile : transcribe)(url, { keep: args.includes('--keep') })
        .then(r => {
            if (args.includes('--json')) {
                console.log(JSON.stringify(r));
            } else {
                console.log(`# ${r.title}\n来源：${r.url}（${r.source}）\n\n${r.text}`);
            }
        })
        .catch(e => { console.error(e.message); process.exit(1); });
}
