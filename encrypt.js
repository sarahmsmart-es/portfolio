// Encrypt portfolio.pdf -> portfolio.enc with AES-256-GCM (PBKDF2-SHA256, 200k).
// Output layout: [salt(16)][iv(12)][ciphertext][gcm tag(16)]  -> matches WebCrypto decrypt.
// Usage: node encrypt.js "<password>"
const fs = require('fs');
const crypto = require('crypto');

const password = process.argv[2];
if (!password) { console.error('Usage: node encrypt.js "<password>"'); process.exit(1); }

const ITER = 200000;
const pdf = fs.readFileSync('portfolio.pdf');
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(password, salt, ITER, 32, 'sha256');

const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const ct = Buffer.concat([cipher.update(pdf), cipher.final()]);
const tag = cipher.getAuthTag();

const out = Buffer.concat([salt, iv, ct, tag]);
fs.writeFileSync('portfolio.enc', out);
console.log('Wrote portfolio.enc  (' + out.length + ' bytes) from portfolio.pdf (' + pdf.length + ' bytes)');
