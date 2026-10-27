// Only the local file-selection function used by exact vercel@62.1.0 --dry.
import { createHash } from 'node:crypto';
import { lstat, readFile, readlink, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const SELECTOR_SHA256 = '813e0e6740cbf5f4f0781b6320f8470a1e5d9a52b5b4fa58b79bd3e83fb46c47';

export async function validateSelectedFiles(root, manifest) {
  root = await realpath(root);
  if (manifest.basePath !== root || !Array.isArray(manifest.files) || !manifest.files.length) {
    throw new Error('Wrong or empty selector root');
  }
  const seen = new Set();
  for (const entry of manifest.files) {
    const file = path.resolve(root, entry.path);
    const resolved = await realpath(file);
    const relative = path.relative(root, resolved);
    if (path.isAbsolute(entry.path) || !relative || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
      throw new Error('External selected file');
    }
    if (seen.has(entry.path)) throw new Error('Duplicate selected file');
    seen.add(entry.path);
    if (path.basename(file).startsWith('.env') && path.basename(file) !== '.env.example') {
      throw new Error('Environment file selected');
    }
    if ((path.basename(resolved).startsWith('.env') && path.basename(resolved) !== '.env.example') ||
        relative.split(path.sep).some(part => ['.git', '.secrets', '.vercel'].includes(part))) {
      throw new Error('Private selected target');
    }
    const info = await stat(file);
    const link = await lstat(file);
    if (link.isSymbolicLink()) {
      if ((entry.mode & 0o170000) !== 0o120000 || !info.isFile()) {
        throw new Error('Invalid selected symbolic link');
      }
      // The pinned SDK hashes the UTF-8 link text, not the resolved bytes.
      // Require the resolved regular file to be selected separately, where its
      // real bytes are independently checked by this same verifier.
      if (!manifest.files.some(target => path.resolve(root, target.path) === resolved &&
          (target.mode & 0o170000) === 0o100000)) {
        throw new Error('Selected symbolic link target missing');
      }
      const bytes = Buffer.from(await readlink(file), 'utf8');
      if (entry.size !== bytes.length || entry.sha !== createHash('sha1').update(bytes).digest('hex')) {
        throw new Error(`Selected link bytes changed: ${JSON.stringify(entry.path)}`);
      }
      continue;
    }
    // The exact SDK also represents directory placeholders, with directory mode,
    // zero size and no digest. Preserve that manifest shape without treating
    // a directory as a hashed source file.
    if (info.isDirectory() && (entry.mode & 0o170000) === 0o040000 &&
        entry.size === 0 && entry.sha === undefined) continue;
    if (!info.isFile() || (entry.mode & 0o170000) !== 0o100000) throw new Error('Invalid selected directory or file');
    const bytes = await readFile(file);
    if (entry.size !== bytes.length || entry.sha !== createHash('sha1').update(bytes).digest('hex')) {
      throw new Error(`Selected file bytes changed: ${JSON.stringify(entry.path)} (selected size ${entry.size}, actual size ${bytes.length})`);
    }
  }
  return manifest;
}

export async function selectSourceFiles(root, packageRoot) {
  root = await realpath(root);
  const config = JSON.parse(await readFile(path.join(root, 'frontend/vercel.json'), 'utf8'));
  if (config.framework !== 'create-react-app' || config.bulkRedirectsPath !== undefined) {
    throw new Error('Unreviewed source packaging configuration');
  }
  if (!(await stat(path.join(root, 'frontend/api'))).isDirectory()) {
    throw new Error('Wrong source root: frontend/api directory missing');
  }
  const pkg = JSON.parse(await readFile(path.join(packageRoot, 'package.json'), 'utf8'));
  const selector = path.join(packageRoot, 'dist/chunks/chunk-Z6TGFLIO.js');
  if (pkg.name !== 'vercel' || pkg.version !== '62.1.0' ||
      createHash('sha256').update(await readFile(selector)).digest('hex') !== SELECTOR_SHA256) {
    throw new Error('Exact package/selector identity mismatch');
  }
  const { require_dist } = await import(pathToFileURL(selector).href);
  // Same options as the existing source --dry path for the reviewed settings.
  // Static settings verify packaging only; they do not attest live provider config.
  const manifest = await require_dist().inspectDeploymentFiles({
    path: root, prebuilt: false, projectName: 'earnalism', rootDirectory: 'frontend',
  });
  return validateSelectedFiles(root, manifest);
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const args = process.argv.slice(2);
  if (args.length !== 4 || args[0] !== '--root' || args[2] !== '--vercel-package' || !path.isAbsolute(args[1]) || !path.isAbsolute(args[3])) {
    throw new Error('Require absolute --root and --vercel-package');
  }
  console.log(JSON.stringify(await selectSourceFiles(args[1], args[3]), null, 2));
}
