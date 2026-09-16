// Build sin dependencias para Netlify (cualquier plan).
// Cifra index.html con AES-256-GCM (clave derivada con PBKDF2-SHA256) usando SITE_PASSWORD
// y publica una pantalla de acceso que lo descifra en el navegador.
// Sin la contraseña correcta el contenido no es legible, ni siquiera viendo el código fuente.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const OUT = 'dist';
const ITER = 600000;
const pass = process.env.SITE_PASSWORD || '';

if (pass.length < 12) {
  console.error('Falta SITE_PASSWORD o tiene menos de 12 caracteres. Configurala en Netlify (Environment variables) y volvé a deployar.');
  process.exit(1);
}

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT);
fs.copyFileSync('robots.txt', path.join(OUT, 'robots.txt'));

const html = fs.readFileSync('index.html');
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(pass, salt, ITER, 32, 'sha256');
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const payload = Buffer.concat([cipher.update(html), cipher.final(), cipher.getAuthTag()]);

const gate = `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Acceso · Curaduría de Fondos Offshore · Balanz International</title>
<style>
  :root{--navy:#071A3D;--navy2:#0C2A5C;--accent:#1D5BF5;--line:#DAE2EC;--ink:#0D1B33;--muted:#5B6B83;--neg:#B42318;
        --font:Aptos,"IBM Plex Sans","Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:flex;flex-direction:column;background:#F2F5F9;color:var(--ink);font-family:var(--font)}
  header{background:var(--navy);color:#fff;padding:14px 20px;display:flex;align-items:center;gap:16px}
  .brand{display:flex;flex-direction:column;line-height:1}
  .brand b{font-size:19px;letter-spacing:.14em}
  .brand span{font-size:8.5px;letter-spacing:.42em;margin-top:4px;color:#AFC1DE}
  .strip{background:var(--navy2);color:#fff;font-size:12.5px;font-weight:600;letter-spacing:.06em;padding:5px 20px}
  main{flex:1;display:flex;align-items:center;justify-content:center;padding:24px}
  form{background:#fff;border:1px solid var(--line);border-radius:8px;padding:28px;width:100%;max-width:400px}
  h1{font-size:22px;margin:0 0 6px}
  p{margin:0 0 20px;color:var(--muted);font-size:14.5px;line-height:1.5}
  label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}
  input{width:100%;height:42px;padding:0 12px;border:1px solid var(--line);border-radius:6px;font:inherit;font-size:15px}
  input:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
  button{margin-top:14px;width:100%;height:42px;border:0;border-radius:6px;background:var(--accent);color:#fff;font:inherit;font-weight:600;font-size:15px;cursor:pointer}
  button[disabled]{opacity:.6;cursor:wait}
  .err{color:var(--neg);font-size:14px;margin:12px 0 0;min-height:20px}
  @media (prefers-color-scheme: dark){
    body{background:#07101E;color:#E6ECF5} form{background:#0D192C;border-color:#21324E}
    input{background:#112039;border-color:#21324E;color:#E6ECF5} p,label{color:#8FA0B9} .err{color:#FF8F85}
  }
</style>
</head>
<body>
<header><div class="brand"><b>BALANZ</b><span>INTERNATIONAL</span></div><div>Curaduría de Fondos Offshore</div></header>
<div class="strip">USO INTERNO · INDIVIDUOS</div>
<main>
  <form id="f" autocomplete="on">
    <h1>Acceso restringido</h1>
    <p>Ingresá la contraseña provista para asesores del segmento Individuos.</p>
    <label for="pw">Contraseña</label>
    <input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
    <button id="go" type="submit">Ingresar</button>
    <div class="err" id="err" role="alert" aria-live="assertive"></div>
    <noscript><p class="err">Se requiere JavaScript habilitado.</p></noscript>
  </form>
</main>
<script>
(function(){
  var SALT = "${salt.toString('base64')}", IV = "${iv.toString('base64')}", ITER = ${ITER};
  var DATA = "${payload.toString('base64')}";
  var KEY = 'cfo-access';
  function b64(s){ var bin = atob(s), u = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }
  async function unlock(pw){
    var enc = new TextEncoder();
    var base = await crypto.subtle.importKey('raw', enc.encode(pw), 'PBKDF2', false, ['deriveKey']);
    var key = await crypto.subtle.deriveKey({name:'PBKDF2', salt:b64(SALT), iterations:ITER, hash:'SHA-256'}, base, {name:'AES-GCM', length:256}, false, ['decrypt']);
    var plain = await crypto.subtle.decrypt({name:'AES-GCM', iv:b64(IV)}, key, b64(DATA));
    return new TextDecoder().decode(plain);
  }
  function show(html){ document.open(); document.write(html); document.close(); }
  var f = document.getElementById('f'), go = document.getElementById('go'), err = document.getElementById('err'), pw = document.getElementById('pw');
  if (!window.crypto || !crypto.subtle) { err.textContent = 'Este navegador no permite abrir el contenido. Usá una versión actualizada de Chrome, Edge, Safari o Firefox.'; go.disabled = true; return; }
  try { var saved = sessionStorage.getItem(KEY); if (saved) { go.disabled = true; go.textContent = 'Abriendo…'; unlock(saved).then(show).catch(function(){ sessionStorage.removeItem(KEY); go.disabled = false; go.textContent = 'Ingresar'; }); } } catch(e) {}
  f.addEventListener('submit', function(e){
    e.preventDefault(); err.textContent = ''; go.disabled = true; go.textContent = 'Verificando…';
    var value = pw.value;
    unlock(value).then(function(html){ try { sessionStorage.setItem(KEY, value); } catch(e) {} show(html); })
      .catch(function(){ err.textContent = 'Contraseña incorrecta.'; go.disabled = false; go.textContent = 'Ingresar'; pw.select(); });
  });
})();
</script>
</body>
</html>`;

fs.writeFileSync(path.join(OUT, 'index.html'), gate);
fs.writeFileSync(path.join(OUT, '_headers'), [
  '/*',
  '  X-Robots-Tag: noindex, nofollow',
  '  X-Frame-Options: DENY',
  '  X-Content-Type-Options: nosniff',
  '  Referrer-Policy: no-referrer',
  '  Cache-Control: no-store',
].join('\n') + '\n');
console.log('Build OK. Contenido cifrado (AES-256-GCM, PBKDF2 ' + ITER + ' iteraciones).');
