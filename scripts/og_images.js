#!/usr/bin/env node
/*
 * Gives every blog post its own social-share image (og:image).
 *
 * Why this exists
 * ---------------
 * Every post used to point og:image at /assets/og-image.png, the portfolio
 * card. So a blog link shared on Facebook or WhatsApp previewed as
 * "Senior IT Manager @ AKS Khan Diagnostics", not as the article.
 *
 * For each blog/<lang>/<slug>/index.html this script:
 *   1. works out which app the post is about (from its Play / app-page links),
 *   2. renders a 1200x630 PNG with the post's og:title, that app's icon and
 *      name, and the site name, to assets/og/<lang>-<slug>.png,
 *   3. points og:image, og:image:width/height/alt and the JSON-LD "image" at it.
 * Redirect stubs (robots noindex) are skipped. Safe to re-run.
 *
 * Usage
 * -----
 *   node scripts/og_images.js                 # all posts
 *   node scripts/og_images.js some-slug       # only posts whose slug matches
 *   node scripts/og_images.js --font-css /path/fonts.css
 *
 * Needs Playwright (Chromium). Fonts load from Google Fonts by default; pass
 * --font-css with local @font-face rules when the browser has no network.
 * A new post just needs this re-run (and, if it is about a new app, an entry
 * in APPS and DETECT below).
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const SITE = 'https://mohammadrafiqulislam.com';
const OUT_DIR = path.join(ROOT, 'assets', 'og');

const APPS = {
  mhr:          { name: 'Medicine & Health Reminder', icon: 'mhr_icon.png',        color: '#60a5fa' },
  nextcue:      { name: 'NextCue',                    icon: 'nextcue_icon.png',    color: '#2dd4bf' },
  docuary:      { name: 'Docuary',                    icon: 'docuary_icon.png',    color: '#a78bfa' },
  mouzaplot:    { name: 'Mouza Plot & Land Measure BD', icon: 'mouzaplot_icon.png', color: '#4ade80' },
  cloudburst:   { name: 'Cloudburst',                 icon: 'cloudburst_icon.png', color: '#38bdf8' },
  trueinstalls: { name: 'TrueInstalls',               mono: 'T',                   color: '#3DDC84' },
  wafid:        { name: 'Wafid GCC Slip',             mono: 'W',                   color: '#f59e0b' },
};

// Order matters: first match wins. Both reminder apps -> 'both'.
const DETECT = [
  ['both',         h => /id=com\.rafiqctgbd\.medicinehealth/.test(h) && /id=com\.rafiqctgbd\.nextcue/.test(h)],
  ['mhr',          h => /id=com\.rafiqctgbd\.medicinehealth|apps\/medicine-health-reminder\//.test(h)],
  ['nextcue',      h => /id=com\.rafiqctgbd\.nextcue|apps\/nextcue\//.test(h)],
  ['docuary',      h => /apps\/docuary\//.test(h)],
  ['mouzaplot',    h => /apps\/mouza-plot\//.test(h)],
  ['cloudburst',   h => /Cloudburst/.test(h)],
  ['trueinstalls', h => /TrueInstalls/.test(h)],
  ['wafid',        h => /Wafid/i.test(h)],
];

const decode = s => s.replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'")
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function iconHtml(app) {
  if (app.mono) return `<div class="icon mono" style="background:${app.color}">${app.mono}</div>`;
  const b64 = fs.readFileSync(path.join(ROOT, 'assets', app.icon)).toString('base64');
  return `<img class="icon" src="data:image/png;base64,${b64}">`;
}

function pageHtml({ title, lang, appKey, fontCss }) {
  const apps = appKey === 'both' ? [APPS.mhr, APPS.nextcue] : [APPS[appKey]];
  const color = apps[0].color;
  const bn = lang === 'bn';
  const appName = apps.map(a => esc(a.name)).join(' <span class="dot">·</span> ');
  const fonts = fontCss
    ? `<link rel="stylesheet" href="file://${fontCss}">`
    : `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@500;700&family=Noto+Sans+Bengali:wght@600;700&display=block">`;
  return `<!DOCTYPE html><html lang="${lang}"><head><meta charset="utf-8">${fonts}<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#0f172a;font-family:'DM Sans','Noto Sans Bengali',sans-serif;color:#f1f5f9;overflow:hidden;position:relative}
  .glow{position:absolute;right:-180px;top:-220px;width:620px;height:620px;border-radius:50%;background:${color};opacity:.13;filter:blur(40px)}
  .bar{position:absolute;left:0;top:0;bottom:0;width:12px;background:${color}}
  .wrap{position:absolute;left:84px;right:84px;top:64px;bottom:58px;display:flex;flex-direction:column}
  .top{display:flex;align-items:center;gap:22px}
  .icons{display:flex;gap:12px}
  .icon{width:76px;height:76px;border-radius:18px;display:block;box-shadow:0 6px 18px rgba(0,0,0,.35)}
  .mono{display:flex;align-items:center;justify-content:center;font:700 46px 'DM Sans',sans-serif;color:#0f172a}
  .app{font-weight:700;font-size:30px;color:#e2e8f0;line-height:1.2}
  .dot{color:#64748b}
  .title-box{flex:1;display:flex;align-items:center}
  h1{font-family:${bn ? "'Noto Sans Bengali'" : "'Syne'"},sans-serif;font-weight:700;line-height:${bn ? 1.42 : 1.12};letter-spacing:${bn ? '0' : '-0.5px'};color:#f8fafc}
  .bottom{display:flex;align-items:center;justify-content:space-between}
  .brand{font:700 26px 'Syne',sans-serif;color:#f1f5f9}
  .brand span{color:${color};font:500 24px 'DM Sans',sans-serif;margin-left:14px}
  .pill{font:700 22px ${bn ? "'Noto Sans Bengali'" : "'DM Sans'"},sans-serif;color:#0f172a;background:${bn ? '#f59e0b' : color};padding:${bn ? '4px 20px 8px' : '7px 20px'};border-radius:999px}
  </style></head><body><div class="glow"></div><div class="bar"></div>
  <div class="wrap">
    <div class="top"><div class="icons">${apps.map(iconHtml).join('')}</div><div class="app">${appName}</div></div>
    <div class="title-box"><h1 id="t">${esc(title)}</h1></div>
    <div class="bottom"><div class="brand">SixSeasons Labs<span>mohammadrafiqulislam.com</span></div><div class="pill">${bn ? 'ব্লগ · বাংলা' : 'Blog · English'}</div></div>
  </div></body></html>`;
}

function updateMeta(html, imgUrl, alt) {
  let out = html.replace(/<meta property="og:image" content="[^"]*">(\s*<meta property="og:image:(width|height|alt)" content="[^"]*">)*/,
    `<meta property="og:image" content="${imgUrl}">\n  <meta property="og:image:width" content="1200">\n  <meta property="og:image:height" content="630">\n  <meta property="og:image:alt" content="${esc(alt)}">`);
  out = out.replace(/"image": "https:\/\/mohammadrafiqulislam\.com\/assets\/[^"]*"/, `"image": "${imgUrl}"`);
  return out;
}

(async () => {
  const args = process.argv.slice(2);
  let fontCss = null, filter = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--font-css') fontCss = path.resolve(args[++i]);
    else filter = args[i];
  }
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  for (const lang of ['en', 'bn']) {
    const dir = path.join(ROOT, 'blog', lang);
    for (const slug of fs.readdirSync(dir).sort()) {
      const file = path.join(dir, slug, 'index.html');
      if (!fs.existsSync(file) || (filter && !slug.includes(filter))) continue;
      const html = fs.readFileSync(file, 'utf8');
      if (/<meta name="robots" content="noindex/.test(html)) continue;   // redirect stub
      const m = html.match(/<meta property="og:title" content="([^"]*)">/);
      if (!m) { console.warn('no og:title:', file); continue; }
      const title = decode(m[1]);
      const hit = DETECT.find(([, test]) => test(html));
      if (!hit) { console.warn('no app detected, skipped:', file); continue; }
      const appKey = hit[0];

      const tmp = path.join(OUT_DIR, '.render.html');
      fs.writeFileSync(tmp, pageHtml({ title, lang, appKey, fontCss }));
      await page.goto('file://' + tmp);
      await page.evaluate(() => document.fonts.ready);
      // Largest size at which the title fits the box in at most 3 lines.
      await page.evaluate(lang => {
        const h = document.getElementById('t'), box = h.parentElement;
        for (let s = lang === 'bn' ? 66 : 70; s >= 36; s -= 2) {
          h.style.fontSize = s + 'px';
          const lines = Math.round(h.scrollHeight / (s * (lang === 'bn' ? 1.42 : 1.12)));
          if (lines <= 3 && h.scrollHeight <= box.clientHeight) break;
        }
      }, lang);
      const name = `${lang}-${slug}.png`;
      await page.screenshot({ path: path.join(OUT_DIR, name) });
      fs.unlinkSync(tmp);

      const updated = updateMeta(html, `${SITE}/assets/og/${name}`, title);
      if (updated !== html) fs.writeFileSync(file, updated);
      console.log(`${name}  [${appKey}]`);
    }
  }
  await browser.close();
})();
