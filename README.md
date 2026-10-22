# Curaduría de Fondos Offshore · Balanz International

Aplicación estática (un solo `index.html`, sin dependencias) para asesores del segmento Individuos.
USO INTERNO · INDIVIDUOS.

## Estructura
- `index.html`: la aplicación completa, con los datos embebidos. Es lo único que se publica.
- `data/funds.json`: datos extraídos del documento del mes (referencia y control de cambios).
- `data/institucional.json`: textos institucionales estables (qué es la curaduría, proceso, perfiles).
- `tools/`: extracción y validación. No se publica.
- `scripts/build.js` + `netlify.toml`: cifran el sitio con `SITE_PASSWORD` y lo publican en Netlify.

## Actualización mensual
1. Dejar el documento nuevo en `fuente/` y correr:
   `python tools/actualizar.py fuente/<archivo>.docx`
   Extrae, reconstruye `index.html`, valida cada dato contra el documento y lista altas y bajas.
   Si algo no coincide, se detiene y no publica.
2. Subir a GitHub: `index.html`, `data/funds.json` y el archivo de `fuente/`.
3. Netlify publica solo. Verificar en una ventana de incógnito.

Formatos aceptados: Word (`.docx`, formato vigente) y el texto plano de la PPT (`.txt`, formato anterior).

## Variables de entorno en Netlify
- `SITE_PASSWORD`: contraseña de acceso, mínimo 12 caracteres. Sin ella el deploy falla a propósito.
