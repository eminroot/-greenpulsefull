// Minimal dependency-free static server that renders the generated slide SVG in
// a page, used only to preview/verify the slide. Not part of the app.
const http = require('http');
const fs = require('fs');
const path = require('path');

const svgPath = path.resolve(__dirname, '..', 'slides', 'tech-stack.svg');
const port = Number(process.env.PORT) || 4321;

http
  .createServer((_req, res) => {
    const svg = fs.readFileSync(svgPath, 'utf8');
    const html = `<!doctype html><meta charset="utf8">
<style>html,body{margin:0;background:#586675;min-height:100vh;display:flex;align-items:center;justify-content:center}
svg{width:94vw;height:auto;box-shadow:0 12px 50px rgba(0,0,0,.45);border-radius:6px}</style>
<body>${svg}</body>`;
    res.writeHead(200, { 'content-type': 'text/html' });
    res.end(html);
  })
  .listen(port, () => console.log('slides preview on', port));
