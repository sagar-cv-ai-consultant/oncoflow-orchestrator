import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

export const projectRoot = fileURLToPath(new URL('../', import.meta.url));

/** Resolve this checkout's interpreter instead of a machine-specific path. */
export function pythonExecutable() {
  const executable = join(
    projectRoot,
    '.venv',
    process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
  );
  if (!existsSync(executable)) {
    throw new Error(
      'Create .venv using Python 3.10+ and install requirements-dev.txt. See README.md.',
    );
  }
  return executable;
}
