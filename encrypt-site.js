// Encrypt the built portfolio site -> site.enc with AES-256-GCM (PBKDF2-SHA256, 200k).
// Output layout: [salt(16)][iv(12)][ciphertext][gcm tag(16)]  -> matches WebCrypto decrypt.
//
// Usage:  node encrypt-site.js            <- prompts for the password (recommended)
//         node encrypt-site.js "<pw>"     <- also works, but the shell sees the password
//
// Prompting avoids two problems with passing it as an argument: quoting errors
// when the password contains " ' $ ! or spaces, and the password landing in
// your shell history.
const fs = require('fs');
const crypto = require('crypto');
const readline = require('readline');

const ITER = 200000;
const input = process.argv[3] || 'site.html';

// One shared readline interface, consumed via the 'line' event rather than
// rl.question(): on stdin EOF readline closes and silently drops any pending
// question callback, which would hang the script. A queue survives that.
let rl = null, muted = false;
const lines = [], waiters = [];
let closed = false;

function initRl() {
  rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: process.stdin.isTTY === true
  });
  // Suppress echo of typed characters while a hidden prompt is open.
  const write = rl._writeToOutput.bind(rl);
  rl._writeToOutput = function (s) { if (!muted) write(s); };
  rl.on('line', (l) => {
    if (waiters.length) waiters.shift()(l);
    else lines.push(l);
  });
  rl.on('close', () => {
    closed = true;
    while (waiters.length) waiters.shift()(null);
  });
}

function ask(query, hide) {
  if (!rl) initRl();
  process.stdout.write(query);
  muted = !!hide;
  return new Promise((resolve) => {
    const done = (v) => {
      muted = false;
      if (hide) process.stdout.write('\n');
      resolve(v == null ? '' : v);
    };
    if (lines.length) return done(lines.shift());
    if (closed) return done(null);
    waiters.push(done);
  });
}

(async function main() {
  if (!fs.existsSync(input)) {
    console.error('Input not found: ' + input);
    process.exit(1);
  }

  let password = process.argv[2];
  if (!password) {
    password = await ask('Password: ', true);
    const again = await ask('Confirm:  ', true);
    if (password !== again) {
      console.error('Passwords did not match. Nothing written.');
      process.exit(1);
    }
  }
  if (rl) rl.close();

  if (!password) {
    console.error('Empty password. Nothing written.');
    process.exit(1);
  }

  const html = fs.readFileSync(input);
  const salt = crypto.randomBytes(16);
  const iv = crypto.randomBytes(12);
  const key = crypto.pbkdf2Sync(password, salt, ITER, 32, 'sha256');

  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([cipher.update(html), cipher.final()]);
  const tag = cipher.getAuthTag();

  fs.writeFileSync('site.enc', Buffer.concat([salt, iv, ct, tag]));
  const out = fs.statSync('site.enc').size;
  console.log(
    'Wrote site.enc  (' + (out / 1e6).toFixed(2) + ' MB) from ' +
    input + ' (' + (html.length / 1e6).toFixed(2) + ' MB)'
  );
})();
