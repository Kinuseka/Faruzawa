# JASSUB

**Production watch page** loads `jassub.umd.js` + matching `jassub-worker.js` / `jassub-worker.wasm`
(1.x protocol). ASS fonts come from `static/fonts/ass/manifest.json` via `availableFonts` in
`video.js` (`useLocalFonts: false`).

## Optional: vendoring JASSUB 2.x (not used on watch page yet)

Browser bundles can be built from the npm package with esbuild:

```bash
cd tools/jassub-vendor
npm install jassub@2.5.16 esbuild@0.25.0
npx esbuild node_modules/jassub/dist/jassub.js --bundle --format=esm --outfile=../../static/js/jassub/jassub.js --platform=browser
npx esbuild node_modules/jassub/dist/worker/worker.js --bundle --format=esm --outfile=../../static/js/jassub/jassub-worker.js --platform=browser
cp node_modules/jassub/dist/wasm/jassub-worker.wasm ../../static/js/jassub/
cp node_modules/jassub/dist/wasm/jassub-worker-modern.wasm ../../static/js/jassub/
cp node_modules/jassub/dist/default.woff2 ../../static/js/jassub/
```

JASSUB is loaded on demand via dynamic `import()` from `video.js` when an ASS/SSA track is selected.
