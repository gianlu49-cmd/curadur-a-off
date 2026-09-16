# Curaduría de Fondos Offshore · Balanz International

Aplicación estática (un solo `index.html`, sin dependencias) para asesores del segmento Individuos.
USO INTERNO · INDIVIDUOS.

## Estructura
- `index.html`: la aplicación completa, con los datos embebidos.
- `data/funds.json`: copia de referencia de los datos (fuente: PPT Curaduría Offshore v14). No se publica.
- `scripts/build.js`: genera `dist/` y el archivo `_headers` con la contraseña de acceso.
- `netlify.toml`: le indica a Netlify cómo construir y qué carpeta publicar.

## Variables de entorno en Netlify
- `BASIC_AUTH_CREDENTIALS` = `usuario:clave` (obligatoria; sin ella el deploy falla a propósito).
- `ALLOW_PUBLIC` = `true` solo si se decide publicar sin contraseña.

## Actualizar
Reemplazar `index.html` (y `data/funds.json`) y hacer commit. Netlify vuelve a publicar solo.
