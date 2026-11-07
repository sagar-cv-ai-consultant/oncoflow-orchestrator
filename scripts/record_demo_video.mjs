import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { performance } from 'node:perf_hooks';

const root = resolve(import.meta.dirname, '..');
const output = resolve(root, 'docs/submission/video_draft');
mkdirSync(output, { recursive: true });
const script = readFileSync(resolve(root, 'docs/submission/DEMO_VIDEO_SCRIPT.md'), 'utf8');
const sections = [...script.matchAll(/### ([^\n]+)\n\n\*\*On screen:\*\*[\s\S]*?\n\n\*\*Say:\*\* “([\s\S]*?)”/g)];
if (sections.length !== 8) throw new Error(`Expected 8 scenes, found ${sections.length}`);

const scenes = sections.map((match, index) => {
  const narration = match[2].replace(/\s+/g, ' ').trim();
  const audio = resolve(output, `scene-${index + 1}.aiff`);
  execFileSync('/usr/bin/say', ['-v', 'Rishi', '-r', '170', '-o', audio, narration]);
  const info = execFileSync('/usr/bin/afinfo', [audio], { encoding: 'utf8' });
  const duration = Number(info.match(/estimated duration: ([\d.]+) sec/)?.[1]);
  if (!duration) throw new Error(`Could not read duration of ${audio}`);
  return { title: match[1], narration, audio, duration, sceneSeconds: Math.ceil(duration + 6) };
});
if (process.argv.includes('--voice-only')) {
  console.log('Regenerated eight narration clips.');
  process.exit(0);
}

const runtime = '/Users/sagardeyagond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const { chromium } = await import(runtime);
const browser = await chromium.launch({
  headless: true,
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  args: ['--no-sandbox'],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
  recordVideo: { dir: output, size: { width: 1440, height: 900 } },
});
await context.route('**/api/**', async (route) => {
  const target = route.request().url().replace('127.0.0.1:5173', '127.0.0.1:8001');
  const response = await route.fetch({ url: target });
  await route.fulfill({ response });
});
const page = await context.newPage();
const video = page.video();
const timeline = [];
const start = performance.now();
const titlePage = (title, subtitle, body, footer = 'Team_vaidya · 9GGP74') => `
<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0d2032;color:#f5f8fa;font:26px -apple-system,BlinkMacSystemFont,Arial,sans-serif}
.wrap{height:900px;box-sizing:border-box;padding:100px 120px;display:flex;flex-direction:column;justify-content:center;background:radial-gradient(circle at 85% 15%,#1d6272 0%,#0d2032 46%)}
.eyebrow{color:#88dfd0;font-size:20px;letter-spacing:.18em;font-weight:700;text-transform:uppercase}
h1{font-size:64px;line-height:1.07;margin:20px 0 20px;max-width:1050px}
.subtitle{font-size:32px;color:#cbebeb;max-width:1060px;line-height:1.3}
.body{font-size:25px;line-height:1.5;color:#dce8ec;max-width:1080px;margin-top:25px}
.footer{position:absolute;bottom:54px;color:#90b7bc;font-size:20px}
.bar{height:8px;width:150px;background:#67d2bd;margin-top:40px;border-radius:8px}
</style></head><body><div class="wrap"><div class="eyebrow">OncoFlow Orchestrator</div><h1>${title}</h1><div class="subtitle">${subtitle}</div><div class="body">${body}</div><div class="bar"></div><div class="footer">${footer}</div></div></body></html>`;

async function scene(index, action) {
  const item = scenes[index];
  const at = (performance.now() - start) / 1000;
  timeline.push({ index: index + 1, title: item.title, start: at, audio: item.audio, audioDuration: item.duration, sceneSeconds: item.sceneSeconds });
  console.log(`Scene ${index + 1}: ${item.title} (${item.sceneSeconds}s)`);
  await action();
  const remaining = item.sceneSeconds - (performance.now() - start) / 1000 + at;
  if (remaining > 0) await page.waitForTimeout(remaining * 1000);
}

try {
  await scene(0, async () => {
    await page.setContent(titlePage('Make every usable chair count', 'A coordinator-guided recovery workflow for oncology day care', 'Sagar Deyagond · Technical Lead<br>Sindhura C · Technical Developer<br>Jatin Punera · Doctor Lead'));
    await page.waitForTimeout(9000);
    await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
    await page.getByText('Connected locally').waitFor();
  });
  await scene(1, async () => {
    await page.getByRole('region', { name: 'Clinic overview' }).scrollIntoViewIfNeeded();
    await page.waitForTimeout(4500);
    await page.getByRole('region', { name: 'Ghost chair recovery' }).scrollIntoViewIfNeeded();
  });
  await scene(2, async () => {
    const cards = page.locator('.ghost-card');
    await cards.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(2500);
    await cards.first().locator('summary').click();
    await page.waitForTimeout(8000);
    await cards.nth(1).scrollIntoViewIfNeeded();
    await page.waitForTimeout(4500);
    await cards.first().scrollIntoViewIfNeeded();
  });
  await scene(3, async () => {
    const chair2 = page.locator('.ghost-card').first();
    await chair2.scrollIntoViewIfNeeded();
    await page.waitForTimeout(6500);
    await chair2.getByRole('button', { name: 'Confirm displacement and start' }).click();
    await page.getByText('Displaced bookings needing follow-up').waitFor();
    await page.getByText('Displaced bookings needing follow-up').scrollIntoViewIfNeeded();
  });
  await scene(4, async () => {
    await page.getByRole('button', { name: 'Audit history' }).click();
    await page.getByText('ghost slot filled').first().waitFor();
    await page.waitForTimeout(9000);
    await page.getByRole('button', { name: 'Patient worklist' }).click();
  });
  await scene(5, async () => {
    await page.getByRole('button', { name: 'Add already-tested patient' }).click();
    const newVisit = page.getByRole('button', { name: 'Open OF-013' });
    await newVisit.waitFor();
    await newVisit.scrollIntoViewIfNeeded();
    await newVisit.click();
    await page.waitForTimeout(5000);
  });
  await scene(6, async () => {
    await page.setContent(titlePage('Measured on fictional clinic days', 'One scripted case: 120 of 140 idle chair-minutes recovered', '36 automated tests passed. Across 50 varied synthetic cases, median recovered time was 101 chair-minutes and median possible same-chair delay was 42 minutes.<br><br>Scenario results only; no measured clinic benefit.'));
  });
  await scene(7, async () => {
    await page.setContent(titlePage('Staff stay in control', 'Operational recommendations with an explicit approval and audit trail', 'Doctor review remains pending. This prototype uses fictional data, local storage, and no live hospital integration or production access control.<br><br>Thank you for reviewing Team_vaidya’s Phase II build.'));
  });
} finally {
  await context.close();
  await browser.close();
}
const path = await video.path();
copyFileSync(path, resolve(output, 'oncoflow-silent.webm'));
writeFileSync(resolve(output, 'timeline.json'), JSON.stringify({ totalSeconds: (performance.now() - start) / 1000, scenes: timeline }, null, 2));
console.log(`Saved ${resolve(output, 'oncoflow-silent.webm')}`);
