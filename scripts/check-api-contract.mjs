/**
 * Checks that the phone app and the web panel still agree with the server.
 *
 * Both clients declare the server's shapes by hand, in src/api/types.ts and
 * web/src/api/types.ts. This reads the server's own OpenAPI schema and compares
 * all three field by field, so a field renamed in one place cannot quietly ship.
 *
 *   node scripts/check-api-contract.mjs [http://127.0.0.1:8000]
 */

import fs from 'node:fs';
import path from 'node:path';

const BASE = process.argv[2] ?? 'http://127.0.0.1:8000';

// Both clients read the same data, so both are checked against the same schema.
const CLIENTS = [
  { name: 'phone app', file: path.join(process.cwd(), 'src/api/types.ts') },
  { name: 'web panel', file: path.join(process.cwd(), 'web/src/api/types.ts') },
];

// Which TS interface should match which server schema.
const PAIRS = [
  ['User', 'UserOut'],
  ['TokenPair', 'TokenPair'],
  ['Site', 'SiteOut'],
  ['Device', 'DeviceOut'],
  ['Reading', 'ReadingOut'],
  ['Capture', 'CaptureOut'],
  ['Diagnosis', 'DiagnosisOut'],
  ['DiagnosisAlternative', 'DiagnosisAlternativeOut'],
  ['DeviceStatus', 'DeviceStatusOut'],
  ['Live', 'LiveOut'],
  ['Series', 'SeriesOut'],
  ['Sustainability', 'SustainabilityOut'],
  ['ScanSubmitted', 'ScanSubmitOut'],
  ['ScanStatus', 'ScanStatusOut'],
  ['ScorePreview', 'ScorePreviewOut'],
];

// A type only one client needs is skipped for the other rather than failing it.
// The phone pairs devices; the panel runs the what-if twin and builds its
// trend from the captures it already holds. Both follow scan jobs, since both
// can ask the greenhouse camera for a photo.
const OPTIONAL_FOR = {
  'phone app': ['ScorePreview'],
  'web panel': ['Device', 'Series'],
};

function parseTsInterfaces(source) {
  const out = {};
  const re = /export interface (\w+)(?: extends (\w+))? \{([\s\S]*?)\n\}/g;
  let m;
  while ((m = re.exec(source))) {
    const [, name, parent, body] = m;
    const fields = [...body.matchAll(/^\s{2}(\w+)(\??):/gm)].map((f) => f[1]);
    out[name] = { fields, parent };
  }
  // Flatten inheritance so an extended interface reports every field it has.
  for (const name of Object.keys(out)) {
    let node = out[name];
    const seen = new Set(node.fields);
    while (node.parent && out[node.parent]) {
      node = out[node.parent];
      node.fields.forEach((f) => seen.add(f));
    }
    out[name].fields = [...seen];
  }
  return out;
}

const problems = [];

const schema = await fetch(`${BASE}/openapi.json`).then((r) => {
  if (!r.ok) throw new Error(`Could not read the schema: HTTP ${r.status}`);
  return r.json();
});

const serverSchemas = schema.components?.schemas ?? {};

for (const client of CLIENTS) {
  console.log('');
  console.log(client.name);
  const tsTypes = parseTsInterfaces(fs.readFileSync(client.file, 'utf8'));

  for (const [tsName, serverName] of PAIRS) {
    const ts = tsTypes[tsName];
    const server = serverSchemas[serverName];

    if (!ts) {
      if (OPTIONAL_FOR[client.name]?.includes(tsName)) continue;
      problems.push(`${client.name} is missing the interface ${tsName}`);
      continue;
    }
    if (!server) {
      problems.push(`server is missing the schema ${serverName}`);
      continue;
    }

    const serverFields = Object.keys(server.properties ?? {});
    const missingInClient = serverFields.filter((f) => !ts.fields.includes(f));
    const notOnServer = ts.fields.filter((f) => !serverFields.includes(f));

    if (missingInClient.length) {
      problems.push(`${client.name} ${tsName}: server sends fields it does not declare: ${missingInClient.join(', ')}`);
    }
    if (notOnServer.length) {
      problems.push(`${client.name} ${tsName}: expects fields the server does not send: ${notOnServer.join(', ')}`);
    }
    if (!missingInClient.length && !notOnServer.length) {
      console.log(`  ok    ${tsName} matches ${serverName} (${serverFields.length} fields)`);
    }
  }
}

console.log();
// Every route either client calls must exist on the server.
const CALLED_PATHS = [
  ['post', '/api/v1/score/preview'],
  ['post', '/api/v1/auth/register'],
  ['post', '/api/v1/auth/login'],
  ['post', '/api/v1/auth/google'],
  ['post', '/api/v1/auth/refresh'],
  ['post', '/api/v1/auth/logout'],
  ['get', '/api/v1/auth/me'],
  ['patch', '/api/v1/auth/me'],
  ['delete', '/api/v1/auth/me'],
  ['post', '/api/v1/auth/me/password'],
  ['get', '/api/v1/sites'],
  ['get', '/api/v1/sites/{site_id}/devices'],
  ['post', '/api/v1/sites/{site_id}/devices'],
  ['delete', '/api/v1/devices/{device_id}'],
  ['get', '/api/v1/sites/{site_id}/live'],
  ['get', '/api/v1/sites/{site_id}/captures'],
  ['delete', '/api/v1/sites/{site_id}/captures'],
  ['get', '/api/v1/sites/{site_id}/sustainability'],
  ['post', '/api/v1/sites/{site_id}/scans'],
  ['get', '/api/v1/scans/{job_id}'],
  ['get', '/api/v1/captures/{capture_id}'],
  ['delete', '/api/v1/captures/{capture_id}'],
];

for (const [method, route] of CALLED_PATHS) {
  if (!schema.paths?.[route]?.[method]) {
    problems.push(`a client calls ${method.toUpperCase()} ${route}, which the server does not serve`);
  }
}
if (!problems.length) {
  console.log(`  ok    all ${CALLED_PATHS.length} routes the clients call exist`);
}

console.log();
if (problems.length) {
  for (const p of problems) console.log(`  FAIL  ${p}`);
  process.exit(1);
}
console.log('both clients and the server agree');
