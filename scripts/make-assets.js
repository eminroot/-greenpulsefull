// Generates branded PNG assets (icon + splash) for GreenPulse with no external
// deps — raw RGBA rasterized to PNG via Node's built-in zlib. The mark is a
// vesica-piscis leaf with a glowing midrib over a dark radial-glow field,
// echoing the in-app SVG logo.
const zlib = require('zlib');
const fs = require('fs');
const path = require('path');

const SIZE = 1024;

// ---- palette ----
const bgTop = [0x0b, 0x1a, 0x12];
const bgBottom = [0x06, 0x10, 0x0b];
const glow = [0x10, 0xb9, 0x81]; // emerald
const leafA = [0xa3, 0xe6, 0x35]; // lime
const leafB = [0x16, 0xa3, 0x4a]; // green
const rib = [0x06, 0x2a, 0x1c];

const lerp = (a, b, t) => a + (b - a) * t;
const mix = (c1, c2, t) => [lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t)];
const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)));

function render(size) {
  const buf = Buffer.alloc(size * size * 4);
  const cx = size / 2;
  const cy = size / 2;

  // Leaf geometry: vesica piscis rotated 45deg. Two circle centers offset
  // along the leaf's short axis; a point is "leaf" if inside both circles.
  const ang = -Math.PI / 4;
  const cos = Math.cos(ang);
  const sin = Math.sin(ang);
  const R = size * 0.42; // circle radius
  const off = size * 0.205; // half-distance between the two centers

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;

      // background vertical gradient
      let col = mix(bgTop, bgBottom, y / size);

      // radial emerald glow
      const dxg = x - cx;
      const dyg = y - cy;
      const dist = Math.sqrt(dxg * dxg + dyg * dyg) / (size * 0.62);
      const g = Math.max(0, 1 - dist);
      const gi = Math.pow(g, 2.2) * 0.55;
      col = mix(col, glow, gi);

      // rotate into leaf space
      const rx = (x - cx) * cos - (y - cy) * sin;
      const ry = (x - cx) * sin + (y - cy) * cos;
      const d1 = Math.sqrt((rx - off) * (rx - off) + ry * ry);
      const d2 = Math.sqrt((rx + off) * (rx + off) + ry * ry);
      const edge = 6;
      const inside = Math.min(R - d1, R - d2); // >0 inside leaf
      const leafMask = Math.max(0, Math.min(1, (inside + edge) / (2 * edge)));

      if (leafMask > 0) {
        // leaf fill gradient along long axis (rx)
        const t = Math.max(0, Math.min(1, (rx + R) / (2 * R)));
        let lc = mix(leafA, leafB, t);
        // midrib: darker band where |ry| small
        const ribMask = Math.max(0, 1 - Math.abs(ry) / (size * 0.012));
        lc = mix(lc, rib, ribMask * 0.85);
        col = mix(col, lc, leafMask);
      }

      buf[i] = clamp(col[0]);
      buf[i + 1] = clamp(col[1]);
      buf[i + 2] = clamp(col[2]);
      buf[i + 3] = 255;
    }
  }
  return buf;
}

function toPng(rgba, size) {
  const bytesPerPixel = 4;
  const stride = size * bytesPerPixel;
  const raw = Buffer.alloc((stride + 1) * size);
  for (let y = 0; y < size; y++) {
    raw[y * (stride + 1)] = 0; // no filter
    rgba.copy(raw, y * (stride + 1) + 1, y * stride, y * stride + stride);
  }
  const idat = zlib.deflateSync(raw, { level: 9 });

  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length, 0);
    const typeBuf = Buffer.from(type, 'ascii');
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])) >>> 0, 0);
    return Buffer.concat([len, typeBuf, data, crc]);
  };

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  return Buffer.concat([sig, chunk('IHDR', ihdr), chunk('IDAT', idat), chunk('IEND', Buffer.alloc(0))]);
}

const crcTable = (() => {
  const t = new Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const outDir = path.resolve(__dirname, '..', 'assets');
fs.mkdirSync(outDir, { recursive: true });
const png = toPng(render(SIZE), SIZE);
fs.writeFileSync(path.join(outDir, 'icon.png'), png);
fs.writeFileSync(path.join(outDir, 'splash.png'), png);
fs.writeFileSync(path.join(outDir, 'adaptive-icon.png'), png);
fs.writeFileSync(path.join(outDir, 'favicon.png'), png);
console.log('Wrote icon.png, splash.png, adaptive-icon.png, favicon.png to', outDir);
