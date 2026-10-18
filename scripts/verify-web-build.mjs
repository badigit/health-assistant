import { readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

const dist = resolve('dist');
for (const file of ['index.html', 'sw.js']) {
  if (statSync(resolve(dist, file)).size < 1000) throw new Error(`Incomplete web build: ${file}`);
}
const html = readFileSync(resolve(dist, 'index.html'), 'utf8');
const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"?]+\.(?:js|css))"/g)];
if (!assets.some(([, name]) => name.endsWith('.js')) || !assets.some(([, name]) => name.endsWith('.css'))) {
  throw new Error('Web build is missing entry script or stylesheet');
}
for (const [, asset] of assets) {
  if (statSync(resolve(dist, asset.slice(1))).size < 100) throw new Error(`Empty web asset: ${asset}`);
}
console.log(`Verified web shell, service worker and ${assets.length} entry assets`);
