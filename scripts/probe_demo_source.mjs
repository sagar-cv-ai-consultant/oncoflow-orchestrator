import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const file = resolve(root, 'docs/submission/video_v2/oncoflow-source-seekable.webm');
const runtime = '/Users/sagardeyagond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const { chromium } = await import(runtime);
const browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'] });
try {
  const page = await browser.newPage();
  const videoBytes = readFileSync(file);
  await page.route('http://oncoflow-probe.local/**', (route) => {
    if (!route.request().url().endsWith('.webm')) return route.fulfill({ contentType: 'text/html', body: '<!doctype html>' });
    const range = route.request().headers().range?.match(/^bytes=(\d+)-(\d*)$/);
    if (!range) return route.fulfill({ contentType: 'video/webm', body: videoBytes, headers: { 'Accept-Ranges': 'bytes' } });
    const start = Number(range[1]);
    const end = range[2] ? Math.min(Number(range[2]), videoBytes.length - 1) : videoBytes.length - 1;
    return route.fulfill({ status: 206, contentType: 'video/webm', body: videoBytes.subarray(start, end + 1), headers: { 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${videoBytes.length}` } });
  });
  await page.goto('http://oncoflow-probe.local/');
  console.log(await page.evaluate(async () => {
    const video = document.createElement('video');
    video.src = 'http://oncoflow-probe.local/source.webm';
    video.muted = true;
    document.body.append(video);
    await new Promise((resolve, reject) => { video.onloadedmetadata = resolve; video.onerror = reject; });
    const before = { duration: video.duration, seekable: video.seekable.length ? [video.seekable.start(0), video.seekable.end(0)] : [] };
    video.currentTime = 154;
    await new Promise((resolve) => { video.onseeked = resolve; setTimeout(resolve, 5000); });
    const seek = { currentTime: video.currentTime, readyState: video.readyState };
    await video.play();
    await new Promise((resolve) => setTimeout(resolve, 2000));
    return { before, seek, after: { currentTime: video.currentTime, paused: video.paused, readyState: video.readyState } };
  }));
} finally { await browser.close(); }
