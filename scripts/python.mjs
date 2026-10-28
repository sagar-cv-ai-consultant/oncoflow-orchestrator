import { spawn } from 'node:child_process';
import { projectRoot, pythonExecutable } from './runtime.mjs';

try {
  const child = spawn(pythonExecutable(), process.argv.slice(2), {
    cwd: projectRoot,
    stdio: 'inherit',
  });
  child.on('error', (error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
  child.on('exit', (code) => {
    process.exitCode = code ?? 1;
  });
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
