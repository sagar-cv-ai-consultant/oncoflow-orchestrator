import { execFileSync } from 'node:child_process';
import { createWriteStream, readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const output = resolve(root, 'docs/submission/video_draft');
const timeline = JSON.parse(readFileSync(resolve(output, 'timeline.json'), 'utf8'));
const audioFiles = timeline.scenes.map((scene) => {
  const wave = scene.audio.replace(/\.aiff$/, '.wav');
  execFileSync('/usr/bin/afconvert', ['-f', 'WAVE', '-d', 'LEI16', scene.audio, wave]);
  return wave;
});
const runtime = '/Users/sagardeyagond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const { chromium } = await import(runtime);
const browser = await chromium.launch({
  headless: true,
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage();
const out = resolve(output, 'OncoFlow_Phase_II_Demo_Video_DRAFT.webm');
const stream = createWriteStream(out);
let bytes = 0;
await page.exposeFunction('saveVideoChunk', async (base64) => {
  const chunk = Buffer.from(base64, 'base64');
  bytes += chunk.length;
  if (!stream.write(chunk)) await new Promise((done) => stream.once('drain', done));
});
await page.route('http://oncoflow-video.local/**', async (route) => {
  const url = new URL(route.request().url());
  const name = url.pathname.slice(1);
  if (name === '') return route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>OncoFlow demo video</title>' });
  const file = name === 'silent.webm' ? resolve(output, 'oncoflow-silent.webm') : resolve(output, name);
  return route.fulfill({
    body: readFileSync(file),
    contentType: name.endsWith('.webm') ? 'video/webm' : 'audio/wav',
  });
});
await page.goto('http://oncoflow-video.local/');
const result = await page.evaluate(async ({ starts, files, limit }) => {
  const audioContext = new AudioContext();
  const destination = audioContext.createMediaStreamDestination();
  const buffers = await Promise.all(files.map(async (name) => {
    const response = await fetch(`http://oncoflow-video.local/${name}`);
    return audioContext.decodeAudioData(await response.arrayBuffer());
  }));
  const video = document.createElement('video');
  video.src = 'http://oncoflow-video.local/silent.webm';
  video.preload = 'auto';
  video.muted = true;
  video.style.cssText = 'width:100vw;height:100vh';
  document.body.append(video);
  await new Promise((resolve, reject) => {
    video.onloadedmetadata = resolve;
    video.onerror = reject;
  });
  await audioContext.resume();
  const videoStream = video.captureStream();
  const combined = new MediaStream([
    ...videoStream.getVideoTracks(),
    ...destination.stream.getAudioTracks(),
  ]);
  if (!combined.getVideoTracks().length) throw new Error('No video track');
  const mime = 'video/webm;codecs=vp8,opus';
  if (!MediaRecorder.isTypeSupported(mime)) throw new Error(`Unsupported ${mime}`);
  const recorder = new MediaRecorder(combined, { mimeType: mime, videoBitsPerSecond: 2600000 });
  const pending = [];
  recorder.ondataavailable = (event) => {
    if (!event.data.size) return;
    pending.push((async () => {
      const bytes = new Uint8Array(await event.data.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) {
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      await window.saveVideoChunk(btoa(binary));
    })());
  };
  const finished = new Promise((resolve, reject) => {
    recorder.onerror = (event) => reject(event.error);
    recorder.onstop = async () => {
      try { await Promise.all(pending); resolve(); } catch (error) { reject(error); }
    };
  });
  const base = audioContext.currentTime + 0.25;
  for (let i = 0; i < buffers.length; i++) {
    const source = audioContext.createBufferSource();
    source.buffer = buffers[i];
    source.connect(destination);
    source.start(base + starts[i]);
  }
  recorder.start(2000);
  await video.play();
  await new Promise((resolve, reject) => {
    video.ontimeupdate = () => {
      if (video.currentTime >= limit) resolve();
    };
    video.onended = resolve;
    video.onerror = reject;
  });
  video.pause();
  recorder.stop();
  await finished;
  return { duration: video.currentTime, scenes: buffers.length };
}, {
  starts: timeline.scenes.map((scene) => scene.start),
  files: audioFiles.map((file) => file.split('/').at(-1)),
  limit: timeline.scenes.at(-1).start + timeline.scenes.at(-1).sceneSeconds + 1,
});
await new Promise((done) => stream.end(done));
await browser.close();
console.log(`Narrated draft: ${out}`);
console.log(`Duration: ${result.duration.toFixed(1)} seconds; size: ${(bytes / 1024 / 1024).toFixed(1)} MiB`);
