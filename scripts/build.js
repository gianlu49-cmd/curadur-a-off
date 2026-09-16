// Build sin dependencias: copia el sitio a dist/ y genera _headers.
// Por seguridad, el build FALLA si no hay credenciales configuradas,
// para que el sitio (uso interno) nunca quede público por error.
const fs = require('fs');
const path = require('path');

const OUT = 'dist';
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT);
for (const f of ['index.html', 'robots.txt']) fs.copyFileSync(f, path.join(OUT, f));

const cred = process.env.BASIC_AUTH_CREDENTIALS; // formato usuario:clave
const allowPublic = process.env.ALLOW_PUBLIC === 'true';
if (!cred && !allowPublic) {
  console.error('Falta BASIC_AUTH_CREDENTIALS (usuario:clave). Configurala en Netlify o definí ALLOW_PUBLIC=true.');
  process.exit(1);
}
if (cred && !/^[^:\s]+:\S+$/.test(cred)) {
  console.error('BASIC_AUTH_CREDENTIALS debe tener el formato usuario:clave, sin espacios.');
  process.exit(1);
}

let headers = [
  '/*',
  '  X-Robots-Tag: noindex, nofollow',
  '  X-Frame-Options: DENY',
  '  X-Content-Type-Options: nosniff',
  '  Referrer-Policy: no-referrer',
];
if (cred) headers.push(`  Basic-Auth: ${cred}`);
fs.writeFileSync(path.join(OUT, '_headers'), headers.join('\n') + '\n');
console.log(`Build OK. Protección con contraseña: ${cred ? 'activada' : 'DESACTIVADA (ALLOW_PUBLIC=true)'}`);
