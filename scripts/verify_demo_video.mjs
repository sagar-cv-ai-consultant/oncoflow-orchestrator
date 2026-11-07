import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const file = process.argv[2]
  ? resolve(process.argv[2])
  : resolve(import.meta.dirname, '../docs/submission/video_draft/OncoFlow_Phase_II_Demo_Video_SUBMIT.webm');
const extension = file.endsWith('.mp4') ? 'mp4' : 'webm';
const runtime = '/Users/sagardeyagond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const { chromium } = await import(runtime);
const browser = await chromium.launch({
  headless: true,
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'],
});
try {
  const page = await browser.newPage();
  const videoBytes = readFileSync(file);
  await page.route('http://oncoflow-video.local/**', (route) => {
    if (route.request().url().endsWith(`.${extension}`)) {
      const range = route.request().headers().range?.match(/^bytes=(\d+)-(\d*)$/);
      if (!range) return route.fulfill({ contentType: `video/${extension}`, body: videoBytes, headers: { 'Accept-Ranges': 'bytes' } });
      const start = Number(range[1]);
      const end = range[2] ? Math.min(Number(range[2]), videoBytes.length - 1) : videoBytes.length - 1;
      return route.fulfill({ status: 206, contentType: `video/${extension}`, body: videoBytes.subarray(start, end + 1), headers: { 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${videoBytes.length}` } });
    }
    return route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Verify video</title>' });
  });
  await page.goto('http://oncoflow-video.local/');
  const result = await page.evaluate(async (extension) => {
    const video = document.createElement('video');
    video.src = `http://oncoflow-video.local/demo.${extension}`;
    document.body.append(video);
    await new Promise((resolve, reject) => {
      video.onloadedmetadata = resolve;
      video.onerror = reject;
    });
    const context = new AudioContext();
    const source = context.createMediaElementSource(video);
    const analyser = context.createAnalyser();
    const silent = context.createGain();
    silent.gain.value = 0;
    source.connect(analyser);
    analyser.connect(silent);
    silent.connect(context.destination);
    await context.resume();
    await video.play();
    const samples = new Float32Array(analyser.fftSize);
    let peak = 0;
    for (let i = 0; i < 25; i++) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      analyser.getFloatTimeDomainData(samples);
      for (const sample of samples) peak = Math.max(peak, Math.abs(sample));
    }
    video.pause();
    return { duration: video.duration, audioPeak: peak, width: video.videoWidth, height: video.videoHeight };
  }, extension);
  console.log(JSON.stringify(result));
  if (result.duration > 420 || result.duration < 200 || result.audioPeak < 0.001) {
    throw new Error('Video duration or narration signal failed verification.');
  }
} finally {
  await browser.close();
}
