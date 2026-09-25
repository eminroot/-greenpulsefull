// Metro config — excludes the Python ML source (greenpulse/) and the local
// skills/reference library from the bundler so they are never watched or
// crawled (greenpulse/greenpulse/venv alone is tens of thousands of files).
const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const config = getDefaultConfig(projectRoot);

const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const blocked = [
  path.resolve(projectRoot, 'greenpulse'),
  path.resolve(projectRoot, 'skills'),
  path.resolve(projectRoot, 'web'),
];

config.resolver.blockList = blocked.map(
  (dir) => new RegExp(`^${escape(dir)}[\\\\/].*`)
);

module.exports = config;
