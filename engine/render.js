// node render.js page.html outDir N worker workers
let pw; try { pw = require('playwright') } catch (e) { pw = require('/opt/npm-tools/node_modules/playwright') }
const fs = require('fs'), path = require('path');
const [, , page, out, N, k, K] = process.argv; const FPS = 30;
(async () => {
  const b = await pw.chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.log('E:', e.message));
  await p.goto('file://' + path.resolve(page)); await p.evaluate(() => document.fonts.ready); await p.waitForFunction('window.ready===true',null,{timeout:120000}); await p.waitForTimeout(400);
  const t0 = Date.now(); let n = 0;
  for (let i = +k; i < +N; i += +K) {
    await p.evaluate(t => render(t), i / FPS);
    await p.screenshot({ path: `${out}/${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 90 }); n++;
  }
  console.log(`worker ${k}: ${n} frames ${((Date.now() - t0) / 1000).toFixed(0)}s`); await b.close();
})();
