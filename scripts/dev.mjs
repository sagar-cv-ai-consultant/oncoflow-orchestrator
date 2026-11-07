import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { projectRoot, pythonExecutable } from './runtime.mjs';

const children = [];
let closing = false;

function stop(code = 0) {
  if (closing) return;
  closing = true;
  for (const child of children) child.kill('SIGTERM');
  process.exitCode = code;
}

function launch(executable, arguments_, env = process.env) {
  const child = spawn(executable, arguments_, {
    cwd: projectRoot,
    stdio: 'inherit',
    env,
  });
  children.push(child);
  child.on('error', (error) => {
    console.error(error.message);
    stop(1);
  });
  child.on('exit', (code) => stop(code ?? 1));
}

try {
  const python = pythonExecutable();
  const vite = join(projectRoot, 'node_modules/vite/bin/vite.js');
  if (!existsSync(vite)) throw new Error('Run npm ci before npm run dev.');
  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => stop());
  }
  launch(
    python,
    [
      '-m',
      'uvicorn',
      'oncoflow.api:create_app',
      '--factory',
      '--app-dir',
      'backend/src',
      '--host',
      '127.0.0.1',
      '--port',
      '8000',
    ],
    { ...process.env, ONCOFLOW_LOCAL_DEMO: '1' },
  );
  launch(process.execPath, [vite, '--config', 'frontend/vite.config.ts']);
} catch (error) {
  console.error(error.message);
  stop(1);
}
