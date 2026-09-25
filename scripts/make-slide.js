// Generates a 16:9 "Teknoloji yığınımız" tech-stack slide as a standalone SVG,
// replicating the reference layout: five staggered grouped columns of cards
// connected by colored arrows. Fixed colors + white background for pasting
// into a pitch deck.
const fs = require('fs');
const path = require('path');

const W = 1280;
const H = 720;
const COL_W = 210;
const CARD_H = 52;
const CARD_GAP = 12;
const TITLE_BAND = 46;
const BOTTOM_PAD = 18;

const FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif";

const stages = [
  {
    title: 'Frontend & UI', accent: '#2563EB', bg: '#EAF1FB', border: '#CFE0F6',
    items: [
      { name: 'React Native', sub: 'Mobil Arayüz', icon: 'react', c: '#2F9BE0' },
      { name: 'Expo (SDK 54)', sub: 'Geliştirme Platformu', icon: 'expo', c: '#0B1220' },
      { name: 'TypeScript', sub: 'Tip Güvenli Kod', icon: 'ts', c: '#3178C6' },
      { name: 'React + Vite', sub: 'Web Yönetim Paneli', icon: 'vite', c: '#8B5CF6' },
    ],
  },
  {
    title: 'Backend Teknolojileri', accent: '#2F6DB0', bg: '#E8F1FB', border: '#CFE2F6',
    items: [
      { name: 'FastAPI', sub: 'Web API Çerçevesi', icon: 'fastapi', c: '#059669' },
      { name: 'Python', sub: 'Sunucu Dili', icon: 'python', c: '#3B6FA8' },
      { name: 'Uvicorn', sub: 'ASGI Sunucusu', icon: 'server', c: '#4B5563' },
      { name: 'Pydantic', sub: 'Veri Doğrulama', icon: 'shield', c: '#E11D48' },
      { name: 'REST API', sub: 'Servis İletişimi', icon: 'braces', c: '#2563EB' },
    ],
  },
  {
    title: 'AI/ML Motoru', accent: '#E23B4E', bg: '#FCECEE', border: '#F6D5D9',
    items: [
      { name: 'YOLO11', sub: 'Yaprak Segmentasyonu', icon: 'scan', c: '#7C3AED' },
      { name: 'PyTorch', sub: 'Derin Öğrenme', icon: 'pytorch', c: '#EE4C2C' },
      { name: 'OpenCV', sub: 'Görüntü İşleme', icon: 'opencv', c: '#22C55E' },
      { name: 'Gemini AI', sub: 'Akıllı Asistan', icon: 'gemini', c: '#4285F4' },
    ],
  },
  {
    title: 'Veritabanı & Bulut', accent: '#3A4757', bg: '#EEF1F5', border: '#DFE5EC',
    items: [
      { name: 'Firebase RTDB', sub: 'Gerçek Zamanlı DB', icon: 'db', c: '#F59E0B' },
      { name: 'Firebase Storage', sub: 'Görsel Depolama', icon: 'image', c: '#F97316' },
      { name: 'Firebase Auth', sub: 'Kimlik Doğrulama', icon: 'lock', c: '#F59E0B' },
    ],
  },
  {
    title: 'DevOps & Dağıtım', accent: '#D98A0B', bg: '#FEF6E7', border: '#FBE8C2',
    items: [
      { name: 'Expo EAS', sub: 'Mobil Dağıtım', icon: 'expo', c: '#0B1220' },
      { name: 'Git & GitHub', sub: 'Versiyon Kontrolü', icon: 'git', c: '#F05133' },
    ],
  },
];

// ---- geometry ----
const colX = [];
{
  const left = 40;
  const gap = (W - 80 - 5 * COL_W) / 4;
  for (let i = 0; i < 5; i++) colX.push(left + i * (COL_W + gap));
}
const groupH = (n) => TITLE_BAND + n * CARD_H + (n - 1) * CARD_GAP + BOTTOM_PAD;
const waveOffset = [12, -30, -4, -24, 22];
const CENTER_Y = 432;
const groupTop = stages.map((s, i) => CENTER_Y + waveOffset[i] - groupH(s.items.length) / 2);

// ---- helpers ----
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const rgba = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

function bolt(cx, cy, s, fill) {
  const p = [
    [-1, -8], [4.5, -1.2], [1, -1.2], [3, 8], [-4.5, 1], [-1, 1],
  ].map(([x, y]) => `${(cx + x * (s / 8)).toFixed(1)},${(cy + y * (s / 8)).toFixed(1)}`).join(' ');
  return `<polygon points="${p}" fill="${fill}"/>`;
}

function icon(name, cx, cy, c) {
  switch (name) {
    case 'react':
      return `<circle cx="${cx}" cy="${cy}" r="2" fill="${c}"/>
        <g fill="none" stroke="${c}" stroke-width="1.3">
          <ellipse cx="${cx}" cy="${cy}" rx="8" ry="3.1"/>
          <ellipse cx="${cx}" cy="${cy}" rx="8" ry="3.1" transform="rotate(60 ${cx} ${cy})"/>
          <ellipse cx="${cx}" cy="${cy}" rx="8" ry="3.1" transform="rotate(120 ${cx} ${cy})"/>
        </g>`;
    case 'expo':
      return `<rect x="${cx - 9}" y="${cy - 9}" width="18" height="18" rx="5" fill="#0B1220"/>
        <path d="M ${cx} ${cy - 5.5} L ${cx + 5.5} ${cy + 5} L ${cx + 2.4} ${cy + 5} L ${cx} ${cy - 0.5} L ${cx - 2.4} ${cy + 5} L ${cx - 5.5} ${cy + 5} Z" fill="#fff"/>`;
    case 'ts':
      return `<rect x="${cx - 9}" y="${cy - 9}" width="18" height="18" rx="4" fill="#3178C6"/>
        <text x="${cx + 0.5}" y="${cy + 4.2}" font-family="${FONT}" font-size="9.5" font-weight="800" fill="#fff" text-anchor="middle">TS</text>`;
    case 'vite':
      return bolt(cx, cy, 9, '#F7C948') +
        `<polygon points="${cx - 1},${cy - 9} ${cx + 5},${cy - 1.5} ${cx + 1},${cy - 1.5}" fill="#8B5CF6" opacity="0.0"/>`;
    case 'fastapi':
      return `<circle cx="${cx}" cy="${cy}" r="9" fill="#059669"/>${bolt(cx + 0.3, cy, 8, '#fff')}`;
    case 'python':
      return `<path d="M ${cx} ${cy - 8.5} h3 a4 4 0 0 1 4 4 v3 a4 4 0 0 1 -4 4 h-6 a3 3 0 0 0 -3 3 v2.5" fill="none" stroke="#3B6FA8" stroke-width="3.4" stroke-linecap="round"/>
        <path d="M ${cx} ${cy + 8.5} h-3 a4 4 0 0 1 -4 -4 v-3 a4 4 0 0 1 4 -4 h6 a3 3 0 0 0 3 -3 v-2.5" fill="none" stroke="#FFD13B" stroke-width="3.4" stroke-linecap="round"/>`;
    case 'server':
      return `<g fill="none" stroke="${c}" stroke-width="1.5">
          <rect x="${cx - 8}" y="${cy - 7.5}" width="16" height="5" rx="1.6"/>
          <rect x="${cx - 8}" y="${cy - 0.5}" width="16" height="5" rx="1.6"/>
        </g>
        <circle cx="${cx - 4.5}" cy="${cy - 5}" r="1.1" fill="${c}"/>
        <circle cx="${cx - 4.5}" cy="${cy + 2}" r="1.1" fill="${c}"/>
        <path d="M ${cx - 3} ${cy + 8.5} h6" stroke="${c}" stroke-width="1.5" stroke-linecap="round"/>`;
    case 'shield':
      return `<path d="M ${cx} ${cy - 8.5} L ${cx + 7} ${cy - 5.5} L ${cx + 7} ${cy + 0.5} C ${cx + 7} ${cy + 5} ${cx + 3.5} ${cy + 7.8} ${cx} ${cy + 8.8} C ${cx - 3.5} ${cy + 7.8} ${cx - 7} ${cy + 5} ${cx - 7} ${cy + 0.5} L ${cx - 7} ${cy - 5.5} Z" fill="${c}"/>
        <path d="M ${cx - 3} ${cy} l 2.2 2.4 l 4 -4.4" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>`;
    case 'braces':
      return `<text x="${cx}" y="${cy + 5.5}" font-family="${FONT}" font-size="15" font-weight="800" fill="${c}" text-anchor="middle">{ }</text>`;
    case 'scan': {
      const b = (dx, dy, sx, sy) =>
        `<path d="M ${cx + dx} ${cy + dy + sy * 4} L ${cx + dx} ${cy + dy} L ${cx + dx + sx * 4} ${cy + dy}" fill="none" stroke="${c}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>`;
      return b(-7.5, -7.5, 1, 1) + b(7.5, -7.5, -1, 1) + b(-7.5, 7.5, 1, -1) + b(7.5, 7.5, -1, -1) +
        `<circle cx="${cx}" cy="${cy}" r="2" fill="${c}"/>`;
    }
    case 'pytorch':
      return `<path d="M ${cx} ${cy - 9} C ${cx + 6} ${cy - 2} ${cx + 5.5} ${cy + 6} ${cx} ${cy + 8.5} C ${cx - 5.5} ${cy + 6} ${cx - 5.5} ${cy - 1} ${cx} ${cy - 4} Z" fill="#EE4C2C"/>
        <circle cx="${cx + 2.6}" cy="${cy - 6}" r="1.5" fill="#EE4C2C"/>`;
    case 'opencv': {
      const ring = (dx, dy, col) =>
        `<circle cx="${cx + dx}" cy="${cy + dy}" r="3.1" fill="none" stroke="${col}" stroke-width="1.9"/>`;
      return ring(0, -4.6, '#EF4444') + ring(-5, 4, '#22C55E') + ring(5, 4, '#3B82F6');
    }
    case 'gemini':
      return `<path d="M ${cx} ${cy - 9} C ${cx + 1.2} ${cy - 2.2} ${cx + 2.2} ${cy - 1.2} ${cx + 9} ${cy} C ${cx + 2.2} ${cy + 1.2} ${cx + 1.2} ${cy + 2.2} ${cx} ${cy + 9} C ${cx - 1.2} ${cy + 2.2} ${cx - 2.2} ${cy + 1.2} ${cx - 9} ${cy} C ${cx - 2.2} ${cy - 1.2} ${cx - 1.2} ${cy - 2.2} ${cx} ${cy - 9} Z" fill="#4285F4"/>`;
    case 'db':
      return `<path d="M ${cx - 7} ${cy - 5} v 10 a 7 3 0 0 0 14 0 v -10" fill="${c}"/>
        <ellipse cx="${cx}" cy="${cy - 5}" rx="7" ry="3" fill="${c}"/>
        <ellipse cx="${cx}" cy="${cy - 5}" rx="7" ry="3" fill="none" stroke="#fff" stroke-width="1.1" opacity="0.55"/>
        <ellipse cx="${cx}" cy="${cy}" rx="7" ry="3" fill="none" stroke="#fff" stroke-width="1.1" opacity="0.35"/>`;
    case 'image':
      return `<rect x="${cx - 8}" y="${cy - 7}" width="16" height="14" rx="3" fill="${c}"/>
        <circle cx="${cx - 3}" cy="${cy - 2.5}" r="2" fill="#fff"/>
        <path d="M ${cx - 8} ${cy + 6} L ${cx - 2} ${cy} L ${cx + 2} ${cy + 4} L ${cx + 5} ${cy + 1} L ${cx + 8} ${cy + 5} V ${cy + 7} H ${cx - 8} Z" fill="#fff" opacity="0.9"/>`;
    case 'lock':
      return `<rect x="${cx - 6.5}" y="${cy - 1}" width="13" height="10" rx="2.4" fill="${c}"/>
        <path d="M ${cx - 4} ${cy - 1} v -2.5 a 4 4 0 0 1 8 0 v 2.5" fill="none" stroke="${c}" stroke-width="1.8"/>
        <circle cx="${cx}" cy="${cy + 3.5}" r="1.5" fill="#fff"/>`;
    case 'git':
      return `<g stroke="${c}" stroke-width="1.7" fill="none">
          <path d="M ${cx - 4} ${cy - 5} V ${cy + 5}"/>
          <path d="M ${cx - 4} ${cy} H ${cx + 1} a 3 3 0 0 0 3 -3 V ${cy - 3.5}"/>
        </g>
        <circle cx="${cx - 4}" cy="${cy - 5.5}" r="2.4" fill="${c}"/>
        <circle cx="${cx - 4}" cy="${cy + 5.5}" r="2.4" fill="${c}"/>
        <circle cx="${cx + 4}" cy="${cy - 5}" r="2.4" fill="${c}"/>`;
    default:
      return '';
  }
}

function arrow(ax, ay, color) {
  const pts = [
    [-16, -3.2], [3, -3.2], [3, -7.5], [16, 0], [3, 7.5], [3, 3.2], [-16, 3.2],
  ].map(([x, y]) => `${(ax + x).toFixed(1)},${(ay + y).toFixed(1)}`).join(' ');
  return `<polygon points="${pts}" fill="${color}"/>`;
}

// ---- build ----
let out = '';

// decorative dots
const dots = [
  [240, 196, 4, '#CBE0F7'], [470, 150, 5, '#D9E2EC'], [690, 196, 4, '#F6D2D6'],
  [965, 168, 5, '#FBE7BF'], [1120, 230, 4, '#D9E2EC'], [150, 470, 4, '#CFE0F6'],
  [770, 560, 5, '#F6D5D9'], [1015, 540, 4, '#FBE8C2'], [300, 610, 4, '#D9E2EC'],
  [560, 175, 3, '#E5C9F0'], [1180, 470, 4, '#DFE5EC'], [60, 250, 3, '#D9E2EC'],
];
for (const [x, y, r, c] of dots) out += `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`;

// arrows
const arrowColors = ['#2563EB', '#E23B4E', '#334155', '#E8A33D'];
for (let i = 0; i < 4; i++) {
  const ax = (colX[i] + COL_W + colX[i + 1]) / 2;
  out += arrow(ax, CENTER_Y - 6, arrowColors[i]);
}

// groups
stages.forEach((stage, i) => {
  const gx = colX[i];
  const gy = groupTop[i];
  const gh = groupH(stage.items.length);

  out += `<rect x="${gx}" y="${gy}" width="${COL_W}" height="${gh}" rx="18" fill="${stage.bg}" stroke="${stage.border}" stroke-width="1.5"/>`;
  out += `<text x="${gx + COL_W / 2}" y="${gy + 30}" font-family="${FONT}" font-size="16.5" font-weight="800" fill="${stage.accent}" text-anchor="middle">${esc(stage.title)}</text>`;

  stage.items.forEach((it, j) => {
    const cx = gx + 12;
    const cy = gy + TITLE_BAND + j * (CARD_H + CARD_GAP);
    const cw = COL_W - 24;
    out += `<rect x="${cx}" y="${cy}" width="${cw}" height="${CARD_H}" rx="12" fill="#FFFFFF" stroke="#ECF0F4" stroke-width="1" filter="url(#cardShadow)"/>`;
    // icon chip
    const chipX = cx + 12;
    const chipY = cy + (CARD_H - 34) / 2;
    out += `<rect x="${chipX}" y="${chipY}" width="34" height="34" rx="10" fill="${rgba(it.c, 0.12)}"/>`;
    out += icon(it.icon, chipX + 17, chipY + 17, it.c);
    // texts
    const tx = chipX + 34 + 12;
    out += `<text x="${tx}" y="${cy + 23}" font-family="${FONT}" font-size="13.5" font-weight="700" fill="#1E2A36">${esc(it.name)}</text>`;
    out += `<text x="${tx}" y="${cy + 39}" font-family="${FONT}" font-size="10.5" font-weight="500" fill="#8A98A6">${esc(it.sub)}</text>`;
  });
});

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" font-family="${FONT}">
  <title>GreenPulse teknoloji yığını</title>
  <defs>
    <filter id="cardShadow" x="-20%" y="-20%" width="140%" height="160%">
      <feDropShadow dx="0" dy="2.5" stdDeviation="4" flood-color="#1E2A36" flood-opacity="0.10"/>
    </filter>
  </defs>
  <rect x="0" y="0" width="${W}" height="${H}" fill="#FFFFFF"/>
  <text x="60" y="78" font-family="${FONT}" font-size="46" font-weight="800" fill="#16365C" letter-spacing="0.3">Teknoloji yığınımız</text>
  ${out}
</svg>`;

const outPath = path.resolve(__dirname, '..', 'slides', 'tech-stack.svg');
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, svg);
console.log('Wrote', outPath, `(${svg.length} bytes)`);
