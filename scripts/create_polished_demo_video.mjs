import { createWriteStream, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const output = resolve(root, 'docs/submission/video_v2');
const sourceVideo = resolve(root, 'docs/submission/video_v2/oncoflow-source-seekable.webm');
const manifest = JSON.parse(readFileSync(resolve(output, 'voice_manifest.json'), 'utf8'));
const previewMode = process.argv.includes('--preview');
const previewScene = process.argv.find((argument) => argument.startsWith('--preview-scene='))?.split('=')[1] ?? 'problem';
if (manifest.length !== 8 || manifest.some((scene) => !scene.words.length)) {
  throw new Error('Generate all eight neural voice clips with word timings first.');
}

const runtime = '/Users/sagardeyagond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const { chromium } = await import(runtime);
const browser = await chromium.launch({
  headless: true,
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling'],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const target = resolve(output, previewMode ? `OncoFlow_Demo_Explainer_PREVIEW_${previewScene}.mp4` : 'OncoFlow_Demo_Explainer_REVIEW.mp4');
const writer = createWriteStream(target);
let totalBytes = 0;
await page.exposeFunction('saveVideoChunk', async (base64) => {
  const chunk = Buffer.from(base64, 'base64');
  totalBytes += chunk.length;
  if (!writer.write(chunk)) await new Promise((done) => writer.once('drain', done));
});
const sourceBytes = readFileSync(sourceVideo);
await page.route('http://oncoflow-render.local/**', (route) => {
  const name = new URL(route.request().url()).pathname.slice(1);
  if (!name) return route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>OncoFlow demo</title>' });
  if (name === 'source.webm') {
    const range = route.request().headers().range?.match(/^bytes=(\d+)-(\d*)$/);
    if (!range) return route.fulfill({ contentType: 'video/webm', body: sourceBytes, headers: { 'Accept-Ranges': 'bytes' } });
    const start = Number(range[1]);
    const end = range[2] ? Math.min(Number(range[2]), sourceBytes.length - 1) : sourceBytes.length - 1;
    return route.fulfill({ status: 206, contentType: 'video/webm', body: sourceBytes.subarray(start, end + 1), headers: { 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${sourceBytes.length}` } });
  }
  const file = resolve(output, name);
  return route.fulfill({
    contentType: 'audio/mpeg',
    body: readFileSync(file),
  });
});
await page.goto('http://oncoflow-render.local/');

const result = await page.evaluate(async ({ manifest, previewMode, previewScene }) => {
  const W = 1920, H = 1080;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  document.body.style.margin = '0';
  document.body.append(canvas);
  const ctx = canvas.getContext('2d', { alpha: false });
  const sourceVideo = document.createElement('video');
  sourceVideo.src = 'http://oncoflow-render.local/source.webm';
  sourceVideo.muted = true;
  sourceVideo.preload = 'auto';
  sourceVideo.style.cssText = 'position:absolute;opacity:0;width:1px;height:1px;pointer-events:none';
  document.body.append(sourceVideo);
  await new Promise((resolve, reject) => {
    sourceVideo.onloadedmetadata = resolve;
    sourceVideo.onerror = reject;
  });
  const audioContext = new AudioContext();
  const destination = audioContext.createMediaStreamDestination();
  const audioBuffers = await Promise.all(manifest.map(async (scene) => {
    const response = await fetch(`http://oncoflow-render.local/${scene.audio}`);
    if (!response.ok) throw new Error(`Audio unavailable: ${scene.audio}`);
    return audioContext.decodeAudioData(await response.arrayBuffer());
  }));
  const scenes = manifest.map((scene, index) => ({
    ...scene,
    audioDuration: audioBuffers[index].duration,
    duration: Math.max(scene.min_seconds, Math.ceil(audioBuffers[index].duration + 3)),
  }));
  let position = 0;
  scenes.forEach((scene) => { scene.start = position; position += scene.duration; });
  const previewStart = previewMode ? (scenes.find((scene) => scene.id === previewScene)?.start ?? 0) : 0;
  const totalDuration = previewMode ? Math.min(position - previewStart, 8) : position;
  if (totalDuration > 420) throw new Error(`Video exceeds 7 minutes: ${totalDuration}s`);

  const ink = '#102638', teal = '#087b75', aqua = '#17b9a7', muted = '#536c78';
  const ease = (t) => 1 - Math.pow(1 - Math.max(0, Math.min(1, t)), 3);
  const fade = (t, at, length = 0.7) => Math.max(0, Math.min(1, (t - at) / length));
  function rr(x, y, w, h, r, fill, stroke, width = 1) {
    ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
  }
  function type(text, x, y, font, color = ink, align = 'left') {
    ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align;
    ctx.textBaseline = 'alphabetic'; ctx.fillText(text, x, y);
    ctx.textAlign = 'left';
  }
  function wrap(text, x, y, maxWidth, lineHeight, font, color = ink, maxLines = 3) {
    ctx.font = font; ctx.fillStyle = color; ctx.textBaseline = 'alphabetic';
    const words = text.split(/\s+/); let line = '', lines = 0;
    for (const word of words) {
      const candidate = line ? `${line} ${word}` : word;
      if (ctx.measureText(candidate).width > maxWidth && line) {
        ctx.fillText(line, x, y + lines * lineHeight); lines++; line = word;
        if (lines >= maxLines - 1) break;
      } else line = candidate;
    }
    if (line && lines < maxLines) ctx.fillText(line, x, y + lines * lineHeight);
  }
  function background() {
    const gradient = ctx.createLinearGradient(0, 0, W, H);
    gradient.addColorStop(0, '#edf4f5'); gradient.addColorStop(0.55, '#f7f8f3'); gradient.addColorStop(1, '#eef5ed');
    ctx.fillStyle = gradient; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(18,139,127,0.045)'; ctx.beginPath(); ctx.arc(1630, 170, 430, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'rgba(47,119,165,0.035)'; ctx.beginPath(); ctx.arc(140, 950, 380, 0, Math.PI * 2); ctx.fill();
  }
  function header(scene, index) {
    rr(78, 46, 46, 46, 13, ink);
    type('o+', 88, 78, '700 26px system-ui', '#f7fffb');
    type('ONCOFLOW', 140, 78, '700 27px system-ui', ink);
    type('FICTIONAL CLINIC DEMO', 1830, 76, '700 18px system-ui', teal, 'right');
    type(scene.label, 140, 145, '700 18px system-ui', teal);
    type(scene.title, 140, 220, '800 63px system-ui', ink);
    ctx.fillStyle = '#d2dfdc'; ctx.fillRect(140, 245, 1640, 3);
    ctx.fillStyle = aqua; ctx.fillRect(140, 245, Math.max(72, (index + 1) / scenes.length * 1640), 3);
  }
  function numberCard(x, y, w, h, number, label, accent, enter) {
    ctx.save(); ctx.globalAlpha = enter; ctx.translate(0, 25 * (1 - ease(enter)));
    ctx.shadowColor = 'rgba(19,47,55,0.13)'; ctx.shadowBlur = 22; ctx.shadowOffsetY = 12;
    rr(x, y, w, h, 28, '#fff'); ctx.shadowColor = 'transparent';
    rr(x, y, w, 8, 5, accent);
    type(number, x + 35, y + 125, '800 92px system-ui', accent);
    wrap(label, x + 39, y + 175, w - 70, 39, '650 29px system-ui', ink, 2);
    ctx.restore();
  }
  function chair(x, y, color, pulse = 0) {
    const lift = Math.sin(pulse) * 5;
    rr(x + 13, y + lift, 75, 72, 17, color);
    rr(x, y + 63 + lift, 100, 28, 13, color);
    ctx.strokeStyle = color; ctx.lineWidth = 10;
    ctx.beginPath(); ctx.moveTo(x + 22, y + 86 + lift); ctx.lineTo(x + 15, y + 114 + lift);
    ctx.moveTo(x + 78, y + 86 + lift); ctx.lineTo(x + 85, y + 114 + lift); ctx.stroke();
  }
  function drawProblem(t) {
    const enter = fade(t, 0.4);
    ctx.save(); ctx.globalAlpha = enter;
    type('10:30', 145, 365, '800 105px system-ui', ink);
    type('A booked chair cannot start treatment yet.', 145, 424, '500 34px system-ui', muted);
    type('Who can use the gap next?', 145, 470, '700 38px system-ui', teal);
    rr(125, 540, 1670, 355, 33, '#ffffff', '#dce8e5', 2);
    for (let i = 0; i < 6; i++) {
      const on = i < 4;
      chair(190 + i * 260, 615, on ? '#178e7d' : '#d49a33', t * 4 + i);
      type(on ? 'OCCUPIED' : 'BOOKED GAP', 190 + i * 260, 782, '700 17px system-ui', on ? teal : '#a97519');
    }
    type('Six patients waiting. Readiness decides who is eligible.', 190, 850, '600 29px system-ui', ink);
    ctx.restore();
  }
  function drawApp(scene, t) {
    let crop;
    if (scene.id === 'overview') crop = [0, 0, 1440, 720];
    else if (scene.id === 'recommend') crop = [250, 360, 1160, 480];
    else if (scene.id === 'approval') crop = [250, 360, 1160, 480];
    else if (scene.id === 'audit') crop = [250, 300, 1160, 550];
    else crop = [250, 330, 1160, 520];
    const ratio = crop[2] / crop[3];
    const boxW = scene.id === 'overview' ? 1490 : 1580;
    const boxH = boxW / ratio;
    const x = (W - boxW) / 2, y = 280;
    ctx.save();
    ctx.shadowColor = 'rgba(16,41,56,0.22)'; ctx.shadowBlur = 35; ctx.shadowOffsetY = 18;
    rr(x - 8, y - 8, boxW + 16, boxH + 16, 30, '#fff');
    ctx.shadowColor = 'transparent';
    ctx.beginPath(); ctx.roundRect(x, y, boxW, boxH, 21); ctx.clip();
    if (sourceVideo.readyState >= 2) ctx.drawImage(sourceVideo, ...crop, x, y, boxW, boxH);
    ctx.restore();
    const cue = {
      overview: '4 occupied · 2 booked gaps · 6 waiting',
      recommend: 'Staff priority + timing + prerequisites',
      approval: 'Coordinator confirms; original patient remains visible',
      audit: 'Action recorded in audit history',
      intake: 'CBC status final → consultation next',
    }[scene.id];
    rr(1210, 273, 565, 56, 28, '#ffffff', '#badad3', 2);
    type(cue, 1492, 311, '700 22px system-ui', teal, 'center');
  }
  function drawEvidence(t) {
    type('One scripted comparison', 145, 325, '700 32px system-ui', muted);
    numberCard(145, 380, 475, 300, '140', 'chair-minutes idle if held', '#667e8a', fade(t, 0.2));
    numberCard(720, 380, 475, 300, '120', 'chair-minutes filled', teal, fade(t, 0.9));
    numberCard(1295, 380, 475, 300, '10', 'minutes possible extra same-chair wait', '#b78026', fade(t, 1.6));
    rr(145, 745, 1625, 120, 27, '#e5f3ef');
    type('50 varied fictional cases', 185, 795, '700 27px system-ui', teal);
    type('Median: 101 minutes recovered · 42 minutes possible delay', 185, 841, '600 33px system-ui', ink);
    type('Scenario results only. No measured hospital benefit.', 145, 915, '600 26px system-ui', muted);
  }
  function drawClose(t) {
    const steps = [
      ['1', 'Recorded readiness'], ['2', 'CP-SAT proposal'],
      ['3', 'Staff confirmation'], ['4', 'Audit and follow-up'],
    ];
    steps.forEach(([number, label], i) => {
      const x = 145 + i * 425;
      const a = fade(t, 0.3 + i * 0.35);
      ctx.save(); ctx.globalAlpha = a;
      rr(x, 370, 350, 245, 26, '#ffffff', '#d9e6e1', 2);
      rr(x + 24, 395, 62, 62, 18, i === 2 ? teal : ink);
      type(number, x + 55, 439, '800 32px system-ui', '#fff', 'center');
      wrap(label, x + 26, 530, 300, 43, '700 33px system-ui', ink, 2);
      if (i < 3) { type('→', x + 374, 518, '700 58px system-ui', teal); }
      ctx.restore();
    });
    rr(145, 690, 1625, 150, 27, '#e4f2ef');
    type('Operational support. Human oversight.', 190, 754, '800 37px system-ui', teal);
    type('Fictional data · Local prototype · Doctor review pending', 190, 807, '500 27px system-ui', ink);
  }
  function captionGroups(scene) {
    const groups = [], maxChars = 76;
    let current = [], first = 0;
    const tokens = scene.narration.trim().split(/\s+/);
    for (let i = 0; i < tokens.length; i++) {
      current.push(tokens[i]);
      const text = current.join(' ');
      if (/[.!?]$/.test(tokens[i]) || text.length >= maxChars) {
        groups.push({ first, tokens: current }); current = []; first = i + 1;
      }
    }
    if (current.length) groups.push({ first, tokens: current });
    return groups.map((group, index) => ({
      start: scene.words[group.first].start,
      end: groups[index + 1]
        ? scene.words[groups[index + 1].first].start
        : (scene.words.at(-1).start + scene.words.at(-1).duration + 0.55),
      text: group.tokens.join(' '),
    }));
  }
  scenes.forEach((scene) => { scene.captions = captionGroups(scene); });
  function drawCaption(scene, local) {
    const speechTime = local - 0.45;
    const item = scene.captions.find((caption) => speechTime >= caption.start && speechTime < caption.end);
    if (!item) return;
    rr(170, 944, 1580, 106, 27, 'rgba(13,40,58,0.97)');
    wrap(item.text, 222, 1007, 1470, 38, '600 30px system-ui', '#ffffff', 2);
  }
  function sceneAt(seconds) {
    for (let i = 0; i < scenes.length; i++) {
      if (seconds < scenes[i].start + scenes[i].duration) return i;
    }
    return scenes.length - 1;
  }
  let active = -1;
  async function activate(index) {
    const scene = scenes[index];
    sourceVideo.pause();
    if (scene.source_start == null) return;
    sourceVideo.currentTime = scene.source_start;
    await new Promise((resolve) => {
      if (sourceVideo.readyState >= 2 && Math.abs(sourceVideo.currentTime - scene.source_start) < 0.2) return resolve();
      sourceVideo.addEventListener('seeked', resolve, { once: true });
    });
    sourceVideo.playbackRate = (scene.source_end - scene.source_start) / scene.duration;
    await sourceVideo.play();
  }
  function render(seconds) {
    const index = sceneAt(seconds), scene = scenes[index], local = seconds - scene.start;
    if (index !== active) { active = index; void activate(index); }
    background(); header(scene, index);
    if (scene.id === 'problem') drawProblem(local);
    else if (scene.source_start != null) drawApp(scene, local);
    else if (scene.id === 'evidence') drawEvidence(local);
    else drawClose(local);
    drawCaption(scene, local);
  }
  render(previewStart);
  const combined = new MediaStream([
    ...canvas.captureStream(30).getVideoTracks(),
    ...destination.stream.getAudioTracks(),
  ]);
  const mime = 'video/mp4;codecs=avc1.42E01E,mp4a.40.2';
  if (!MediaRecorder.isTypeSupported(mime)) throw new Error(`Unsupported MP4 codec: ${mime}`);
  const recorder = new MediaRecorder(combined, { mimeType: mime, videoBitsPerSecond: 3000000, audioBitsPerSecond: 128000 });
  let chunks = Promise.resolve();
  recorder.ondataavailable = (event) => {
    chunks = chunks.then(async () => {
      if (!event.data.size) return;
      const bytes = new Uint8Array(await event.data.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      await window.saveVideoChunk(btoa(binary));
    });
  };
  const stopped = new Promise((resolve, reject) => {
    recorder.onerror = (event) => reject(event.error);
    recorder.onstop = async () => { try { await chunks; resolve(); } catch (error) { reject(error); } };
  });
  await audioContext.resume();
  const audioStart = audioContext.currentTime + 0.45;
  audioBuffers.forEach((buffer, index) => {
    const relativeStart = scenes[index].start - previewStart;
    if (relativeStart < 0 || relativeStart >= totalDuration) return;
    const source = audioContext.createBufferSource();
    source.buffer = buffer; source.connect(destination);
    source.start(audioStart + relativeStart);
  });
  recorder.start(2000);
  const started = performance.now();
  await new Promise((resolve) => {
    function frame() {
      const seconds = (performance.now() - started) / 1000;
      render(previewStart + Math.min(seconds, totalDuration - 0.001));
      if (seconds < totalDuration) requestAnimationFrame(frame); else resolve();
    }
    requestAnimationFrame(frame);
  });
  recorder.stop();
  await stopped;
  sourceVideo.pause();
  return {
    seconds: totalDuration,
    width: W,
    height: H,
    scenes: scenes.map(({ id, start, duration, audioDuration }) => ({ id, start, duration, audioDuration })),
  };
}, { manifest, previewMode, previewScene });

await new Promise((done) => writer.end(done));
writeFileSync(resolve(output, 'timeline.json'), JSON.stringify(result, null, 2));
await browser.close();
console.log(`Created ${target}`);
console.log(`Duration ${result.seconds}s; size ${(totalBytes / 1024 / 1024).toFixed(1)} MiB`);
