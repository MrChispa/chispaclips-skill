---
name: chispaclips
description: "Pipeline diario en español que selecciona un video largo de una carpeta, lo transcribe con Whisper, usa un LLM multimodal (Gemini / Claude / OpenAI) para detectar momentos virales, recorta cada candidato con FFmpeg, le superpone un texto gancho estilo TikTok, presenta los candidatos al usuario para aprobación, y publica los aprobados en TikTok / Instagram Reels / YouTube Shorts mediante la API de Upload-Post. Pensado para creadores de contenido hispanohablantes. Use cuando el usuario quiera crear Shorts/Reels/TikToks a partir de videos largos, mencione chispaclips, clips virales, automatización de contenido en español, o pida el lote diario de clips."
license: MIT
compatibility: "Requiere ffmpeg, Python 3.11+, faster-whisper, google-genai (Gemini) o anthropic (Claude) o openai (OpenAI-compat), Pillow, y acceso a internet para los LLM y la API de Upload-Post. Diseñado para correr dentro de un harness de agente (Hermes / Openclaw / Claude Code) — funciona headless en un VPS."
metadata:
  author: BrainMatic
  version: "1.0.0"
  homepage: "https://github.com/MrChispa/chispaclips-skill"
  llm_providers:
    - gemini
    - claude
    - openai
  primary_language: "es"
---

# ChispaClips — Pipeline Diario de Clips Virales (BrainMatic)

Las herramientas del pipeline viven en `~/Documents/chispaclips-skill/`. Cada día esta skill selecciona UN video largo de `INPUT_FOLDER`, extrae todos los momentos viables para clips cortos (decididos por el LLM configurado), los muestra al usuario para aprobación, y publica los aprobados via Upload-Post.

## Setup (solo si aún no está configurado)

### 1. Entorno Python

```bash
cd ~/Documents/chispaclips-skill && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

Como alternativa moderna, instalar el paquete en modo editable:

```bash
pip install -e .
```

Esto habilita el comando global `chispaclips`.

### 2. FFmpeg

Binario del sistema requerido. Verificar con `ffmpeg -version`. Instalar con `brew install ffmpeg` (macOS) o `apt install ffmpeg` (Linux) si falta.

### 3. Variables de entorno (`.env`)

El archivo vive en `~/Documents/chispaclips-skill/.env`. Copia `.env.example` como punto de partida. Claves obligatorias:

```bash
LLM_PROVIDER=gemini          # gemini | claude | openai
GEMINI_API_KEY=...
UPLOAD_POST_API_KEY=...
UPLOAD_POST_PROFILE=...
INPUT_FOLDER=/ruta/absoluta/a/videos/largos
OUTPUT_FOLDER=/ruta/absoluta/clips
TRANSCRIBER_PROVIDER=whisper  # whisper | groq (ver sección "Transcripción")
WHISPER_MODEL=medium
GROQ_API_KEY=...              # solo si TRANSCRIBER_PROVIDER=groq
TIMEZONE=America/Bogota
```

Para usar Claude u OpenAI en vez de Gemini, rellena los bloques correspondientes en `.env.example` y cambia `LLM_PROVIDER`.

Si falta una clave obligatoria, pregunta al usuario antes de continuar. Si el usuario pega una API key en la conversación, escríbela en `.env` de inmediato, no la devuelvas al chat, y avisa que debe rotarla tras las pruebas.

### 4. Cuenta en Upload-Post

- Regístrate gratis en https://upload-post.com → panel en https://app.upload-post.com.
- Conecta TikTok, Instagram (cuenta Business o Creator enlazada a una Página de Facebook) y YouTube mediante OAuth en el panel.
- En **Manage Users**, crea un "profile" — su nombre es `UPLOAD_POST_PROFILE` (NO tu @handle social).
- Genera una API key en **Settings**.
- Verifica: `curl -H "Authorization: Apikey $UPLOAD_POST_API_KEY" https://api.upload-post.com/api/uploadposts/me`.

## Modelo de orquestación

Esta skill está pensada para ser invocada diariamente por el harness **openclaw** (o equivalente), que también gestiona el bridge de mensajería (Telegram, WhatsApp u otro canal). La skill NO habla directamente con Telegram/WhatsApp — solo ejecuta el pipeline y entrega los candidatos como texto + rutas absolutas. El harness reenvía tu output al teléfono del usuario, captura la respuesta y la inyecta de vuelta en la conversación.

En concreto: en el Paso 5 imprimes la tabla de candidatos y preguntas qué IDs publicar; el harness entrega esa tabla + los archivos de clip por el canal configurado; el usuario responde desde su móvil (ej. "1, 3, 5"); el harness inyecta esa respuesta; tú continúas con los Pasos 6-8. Mismo patrón para cualquier otro punto de "preguntar al usuario" (revisión de metadata, confirmación de dry-run, etc.).

Si la skill se invoca fuera de openclaw (ej. usuario corre `python -m chispaclips pick` directamente), los mismos prompts funcionan — simplemente aparecen en la terminal en lugar del teléfono.

## Flujo diario

Esta skill corre como un **bucle infinito diario**. Cada ejecución elige UN video y lo recorre por el pipeline. La semántica de elección es **round-robin por ciclo**: cada video se elige como máximo una vez por ciclo. Cuando todos los videos en `INPUT_FOLDER` han sido procesados en el ciclo actual, se inicia un nuevo ciclo y los mismos videos vuelven a estar disponibles — generando clips nuevos de fuentes ya procesadas. El archivo de estado en `.chispaclips/state/processed.json` rastrea `cycle_started_at`, `last_processed_at` por video y `cycles_count` por video. Dentro de un ciclo, el siguiente pick es el más nuevo NO procesado (mtime DESC), por lo que el material recién añadido siempre salta la cola.

### Paso 0 — Preflight (en cada invocación, no saltar)

Antes de cualquier trabajo, comprueba que el entorno está listo y pide al usuario lo que falte:

1. **venv** — ¿existe `~/Documents/chispaclips-skill/venv/bin/python`? Si no, ejecuta el paso 1 del Setup (es mecánico, no necesitas preguntar).
2. **`ffmpeg`** en `PATH` — si falta, pide al usuario que ejecute `brew install ffmpeg` o `apt install ffmpeg` (no instales tú: las instalaciones del sistema merecen confirmación).
3. **`.env`** — comprueba que cada clave obligatoria está configurada y no vacía:
   - `GEMINI_API_KEY` (o `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` según `LLM_PROVIDER`) → si falta, pregunta: *"Falta la API key de {proveedor}. Pégamela."*
   - `UPLOAD_POST_API_KEY` y `UPLOAD_POST_PROFILE` → si falta, pregunta: *"Necesito la API key de Upload-Post y el nombre del profile (Manage Users en https://app.upload-post.com)."*
   - `INPUT_FOLDER` y `OUTPUT_FOLDER` → si falta, usa `~/Documents/chispaclips-skill/.chispaclips/input` y `.../output`.
   - `WHISPER_MODEL` → default `medium`. `TIMEZONE` → default `America/Bogota`.
4. **Salud de las plataformas Upload-Post** — llama a `GET /api/uploadposts/users` y lee `reauth_required` para cada plataforma del profile configurado. Si alguna requiere reauth, avisa al usuario para que la reautentique (https://app.upload-post.com) o la descarte de `--platforms` después.

**Formato del video de entrada**: los videos en `INPUT_FOLDER` deben estar ya en 9:16 vertical y listos para publicar (1080×1920 típico). Si el usuario tiene subtítulos grabados, deben estar ya en el video fuente. La skill NO reformatea, recorta, escala ni graba subtítulos — solo corta el segmento elegido y superpone un gancho encima. Si llega un video en landscape o en otra proporción, avisa al usuario y pregunta antes de procesar.

**Cómo llegan los videos a `INPUT_FOLDER`** es trabajo del harness, no de la skill. El flujo canónico: el usuario reenvía un video a openclaw / Hermes / su agente en el chat (Telegram / WhatsApp / etc.), el harness lo descarga y lo guarda en `INPUT_FOLDER`. La skill solo opera sobre archivos que ya están ahí. Si el usuario pasa una ruta de video que NO está dentro de `INPUT_FOLDER` (ej. `/chispaclips /Users/foo/Descargas/podcast.mp4`), cópiala primero con `cp` (no la muevas — el original se queda en su sitio). Si no, `pick` no la encontrará.

### Paso 1 — Elegir el video

```bash
python -m chispaclips pick
```

Devuelve JSON con el siguiente video a procesar. Campos:
- `path`, `name`, `size_mb`, `mtime`, `duration_s` — metadatos del archivo.
- `previous_cycles_completed` — cuántos ciclos ha recorrido ya este video (0 significa primera vez).
- `remaining_in_cycle` — cuántos videos quedan sin tocar en el ciclo actual.
- `cycle_started_at` — timestamp de inicio del ciclo actual.
- `new_cycle_started` — `true` si ESTE pick abrió un ciclo nuevo (todos los videos se procesaron en el ciclo anterior, el bucle ha dado la vuelta).

Si `new_cycle_started` es `true`, coméntalo brevemente al usuario: *"Iniciando un nuevo ciclo: este video ya se procesó N veces. Buscaré momentos nuevos."* No es un error — es el wrap-around esperado. Gemini (o el LLM configurado) probablemente elegirá momentos distintos porque el prompt no es determinista y los priors de HOT.md evolucionan.

El pipeline NO se detiene cuando se quedan sin videos frescos. El único caso de parada dura es `INPUT_FOLDER` vacío — avisa al usuario y pídele que suelte algo ahí.

Si el usuario dice "reprocesa el video X ahora mismo" fuera del orden del ciclo, elimina su entrada de `.chispaclips/state/processed.json` primero y luego ejecuta `pick`. NO bypasees la lógica de ciclo por otros medios.

### Paso 2 — Transcribir

```bash
python -m chispaclips transcribe "<VIDEO_PATH>"
```

Escribe `.chispaclips/output/<video_slug>/transcript.json` con segmentos a nivel de oración y marcas por palabra. Whisper autodetecta el idioma. Modelo por defecto: `medium`.

**Proveedor de transcripción** (configurable vía `TRANSCRIBER_PROVIDER` en `.env`):
- `whisper` (default) — corre `faster-whisper` en CPU local. Privado, gratis, primera ejecución descarga el modelo (~1.5 GB).
- `groq` — usa la API de Groq (Whisper large-v3 en la nube). **~30× más rápido**: un video de 10 min se transcribe en ~10s en vez de ~5min. Requiere `GROQ_API_KEY`. Si el video es >25 MB, ChispaClips extrae el audio a MP3 mono 64 kbps antes de enviarlo.

Override puntual por llamada: `python -m chispaclips transcribe video.mp4 --provider groq`

### Paso 3 — Analizar con el LLM configurado

```bash
python -m chispaclips analyze "<VIDEO_PATH>"
```

Sube el video al proveedor LLM configurado (`GEMINI_API_KEY` → `google-genai` con Files API; `ANTHROPIC_API_KEY` → `anthropic` con frames extraídos; `OPENAI_API_KEY` → `openai` con multimodal) y pide que devuelva TODOS los momentos viables para clips cortos (20-60s cada uno), con marcas temporales ancladas a palabras de la transcripción. Salida: `.chispaclips/output/<video_slug>/clips.json`. Lee este archivo para obtener la lista de candidatos.

**Detección automática de dialecto**: el prompt se construye inyectando el dialecto detectado por Whisper (ej. `es-MX`, `es-CO`, `es-AR`, `es-ES`) y una instrucción de registro para que el LLM adapte los ganchos al dialecto concreto del creador.

### Paso 4 — Cortar cada candidato y añadir el gancho

Para cada clip en `clips.json`, ejecuta dos comandos:

```bash
python -m chispaclips extract "<VIDEO_PATH>" \
    --start <START> --end <END> \
    --output ".chispaclips/output/<slug>/clip_<ID>.mp4"

python -m chispaclips hook ".chispaclips/output/<slug>/clip_<ID>.mp4" \
    --text "<HOOK_TEXT>" --duration 3 \
    --output ".chispaclips/output/<slug>/clip_<ID>_final.mp4"
```

El gancho se renderiza estilo TikTok/Instagram: cada línea de texto lleva su propia pildora negra (78% opacidad, esquinas redondeadas) detrás, con texto blanco Impact + trazo negro encima. La pildora mantiene el gancho legible sobre cualquier fondo (blanco puro, negro puro, capturas de pantalla con mucho detalle) sin necesidad de inspeccionar el frame subyacente. Posicionado en la parte superior de la pantalla durante los primeros 3 segundos. El texto del gancho viene de `clips.json` (lo escribió el LLM en el idioma del video).

Corta y superpone el gancho de TODOS los candidatos por adelantado — el usuario revisará los archivos finales visualmente, no los metadatos.

### Paso 4.5 — QA visual del gancho (lo haces tú mismo, sin llamar al LLM)

Eres multimodal. **Usa eso.** Antes de mostrar los candidatos al usuario, verifica que el gancho se renderiza limpiamente sobre cada clip.

Para cada `clip_<ID>_final.mp4`:

```bash
python -m chispaclips preview .chispaclips/output/<slug>/clip_<ID>_final.mp4
```

Esto extrae un solo frame en t=1.0s (medio del gancho) a `preview_clip_<ID>_final.png` junto al clip. Ábrelo con tu herramienta de **Read** multimodal — tanto Claude como openclaw leen PNGs directamente. No necesitas llamar al LLM; el agente que corre la skill ES el revisor multimodal.

Para cada preview, evalúa:

1. ¿El texto del gancho se ve completo? ¿Alguna letra recortada en los bordes?
2. ¿La pildora se sale del área segura (más de ~5% desde cualquier borde)?
3. ¿El gancho tapa la cara del hablante u otro contenido crítico?
4. ¿Se renderizan correctamente los acentos y caracteres especiales (`á é í ó ú ñ ¿ ¡`)?
5. ¿El gancho se solapa con subtítulos grabados? (Los subtítulos abajo son esperados — solo marca si colisionan con el gancho, que vive arriba).
6. ¿Algún glitch de renderizado: texto corrupto, pildora faltante, transparencia rota?

**Añade una columna "QA" a la tabla del Paso 5** con uno de:
- `✅` — limpio
- `⚠️ <problema>` — marca el problema concreto (ej. `⚠️ último carácter recortado`, `⚠️ pildora desbordada a la derecha`)

**NO descartes clips marcados en silencio** — enséñalos al usuario con la advertencia para que decida. El QA es asesor: un "⚠️" es una pista, no un veto. Si varios clips fallan del mismo modo (ej. el gancho se desborda siempre), es una señal para sugerir al usuario acortar el estilo de gancho en el futuro.

### Paso 5 — Presentar al usuario

Muestra una tabla markdown:

| ID | Duración | Gancho | Score | QA | Razón | Archivo |
|----|----------|--------|-------|----|-------|---------|
| 1  | 38s      | "..."  | 9     | ✅ | ...   | .chispaclips/output/<slug>/clip_1_final.mp4 |
| 2  | 27s      | "..."  | 7     | ⚠️ acento "ó" recortado | ... | .chispaclips/output/<slug>/clip_2_final.mp4 |
| …  | …        | …      | …     | …  | …     | … |

**Incluye siempre las rutas absolutas en la tabla** — el harness openclaw las usa para adjuntar los clips reales al reenviar el mensaje al messenger del usuario (Telegram / WhatsApp / etc.). Sin rutas absolutas el usuario solo ve metadatos y no puede revisar los clips visualmente. Después pregunta:

> **¿Qué IDs de clips quieres publicar? (ej. `1, 3, 5`, o `ninguno`.)**

Espera la respuesta del usuario (llegará via openclaw desde su móvil).

**Si el usuario responde `ninguno`** (rechaza todos los candidatos), salta directo al Paso 8 y ejecuta `mark-processed` con `--clips-published 0`. Esto consume el video para que la próxima ejecución elija el siguiente — si no, los mismos candidatos rechazados volverían a aparecer. Si el usuario quiere reintentar el mismo video más tarde, puede eliminar manualmente su entrada de `.chispaclips/state/processed.json`.

### Paso 6 — Generar metadata por plataforma para los clips aprobados

Para cada ID aprobado, genera copy específico por plataforma. **Esto es TU trabajo como agente** — escríbelo directamente, no uses una herramienta. Hazlo en el mismo idioma del video.

- **TikTok** (`tiktok_title`, máx 90 chars): gancho contundente, 1-2 emojis, mix de hashtags al final. Punto dulce ~70-85 chars.
- **Instagram Reels** (`instagram_title`, hasta 2200 chars): storytelling largo — primera línea es el gancho, luego 2-4 párrafos cortos (usa `\n\n`), CTA ("Guarda esto", "Etiqueta a alguien…", "Comenta X para…"), después 20-30 hashtags mezclando tamaños (grande/mediano/nicho). Punto dulce 500-800 chars en total.
- **YouTube Shorts** (`youtube_title`, máx 100 chars pero **mantén ~40-60 chars** para que no se trunque en móvil): SEO-friendly con keywords. Descripción enfocada en búsqueda, 3-5 hashtags máx.
- Un `title` y `description` general para cualquier plataforma que no tenga su propio override.

**Contrato de longitud (verifica antes de publicar)**: el título de YouTube es el más restringido — escríbelo más corto y directo. TikTok e Instagram pueden respirar — TikTok hasta ~85 chars en `tiktok_title`, los captions de Instagram son long-form por diseño.

Muestra el copy generado al usuario y confirma antes de publicar.

### Paso 7 — Programar la publicación

Programa un clip aprobado por día empezando mañana a las **10:00** en `TIMEZONE` (default `America/Bogota`). Cada clip siguiente += 1 día.

**Antes de publicar**, verifica las plataformas conectadas y el estado de reauth:

```bash
curl -s -H "Authorization: Apikey $UPLOAD_POST_API_KEY" \
    https://api.upload-post.com/api/uploadposts/users | python -m json.tool
```

Si alguna plataforma muestra `"reauth_required": true`, avisa al usuario — esa subida fallará. O bien quita esa plataforma de `--platforms` o pausa y deja que el usuario reautorice en https://app.upload-post.com.

Para cada clip aprobado:

```bash
python -m chispaclips publish ".chispaclips/output/<slug>/clip_<ID>_final.mp4" \
    --platforms tiktok,instagram,youtube \
    --title "<GENERAL>" \
    --description "<DESCRIPCION>" \
    --tiktok-title "<TIKTOK_TITLE>" \
    --instagram-title "<INSTAGRAM_CAPTION>" \
    --youtube-title "<YOUTUBE_TITLE>" \
    --schedule "<ISO_DATE>" \
    --timezone "America/Bogota" \
    --tiktok-mode draft \
    --clip-id <ID> \
    --hook-text "<HOOK_TEXT>" \
    --viral-score <LLM_SCORE> \
    --reason "<LLM_REASON>" \
    --video-source "<SOURCE_VIDEO_FILENAME>"
```

**Los flags `--clip-id`, `--hook-text`, `--viral-score`, `--reason`, `--video-source` no son opcionales en la práctica** — alimentan el loop de aprendizaje. Sin ellos, `learn` no puede correlacionar las métricas de engagement con qué patrones de gancho funcionaron. Los valores vienen directamente de `clips.json` (la salida del LLM) y del nombre del archivo de video fuente.

**Modo TikTok**: `--tiktok-mode draft` (default) envía al inbox de TikTok via `post_mode=MEDIA_UPLOAD` para que el usuario termine de editar en la app antes de publicar. Usa `--tiktok-mode direct` (`DIRECT_POST`) solo cuando el usuario quiera publicación inmediata.

**Ejecuta siempre primero con `--dry-run`** y muestra al usuario los payloads exactos. Solo ejecuta la publicación real tras un "dale" explícito.

### Paso 8 — Marcar el video como procesado

```bash
python -m chispaclips mark-processed "<VIDEO_PATH>" \
    --clips-generated <N_CANDIDATOS> \
    --clips-published <N_APROBADOS>
```

Esto añade el hash del video a `.chispaclips/state/processed.json` para que el próximo `pick` lo salte. **Ejecútalo aunque `--clips-published 0`** — un video rechazado también se consume. La única vez que NO marcas como procesado es si el pipeline se cayó a mitad (ej. el LLM falló antes de producir clips); en ese caso deja que el usuario reintente el mismo video mañana.

### Paso 8.5 — Reflect (opcional, rápido, cualitativo)

Tras publicar, puedes ejecutar un `reflect` rápido para capturar POR QUÉ aprobaste los clips que aprobaste (sin métricas de engagement — solo la señal aprobado-vs-rechazado):

```bash
python -m chispaclips reflect --window-days 30
```

Compara los candidatos recientes (`.chispaclips/learnings/candidate-history.jsonl`) con los aprobados (`.chispaclips/learnings/post-history.jsonl`) y pide al LLM extraer patrones cualitativos ("aprueba ganchos con números concretos, rechaza ganchos en forma de pregunta"). Salida en `.chispaclips/learnings/runs/reflect-YYYY-MM-DD-HHMM.md`.

Estas observaciones NO se promueven automáticamente a HOT.md. Son notas para que el usuario las revise y cure. Ejecuta reflect de vez en cuando — diario es excesivo, semanal está bien.

### Paso 9 — Resumen final

Imprime:

| # | Archivo | Duración | Gancho | Programación | Plataformas |
|---|---------|----------|--------|--------------|-------------|
| … | …       | …        | …      | …            | …           |

…y el nombre del video fuente con cuántos candidatos se generaron vs. publicaron.

## Bucle semanal de aprendizaje (`learn`)

Esta skill **se vuelve más inteligente con el tiempo**. Los datos de engagement de clips pasados (vistas, likes, comentarios, compartidos, guardados — obtenidos de las analíticas de Upload-Post) se realimentan al prompt de selección de clips para ejecuciones futuras.

### Cadencia

Ejecuta `learn` **semanalmente**, no diario. Las métricas de engagement necesitan tiempo para madurar; un `learn` diario perseguiría ruido.

```bash
python -m chispaclips learn
```

Defaults: 7 días de maduración (clips más jóvenes se excluyen), 90 días de edad máxima (más viejos son obsoletos), score compuesto = 0.6·vistas + 0.4·tasa_engagement, top/bottom 20% como ganadores/perdedores.

### Qué hace

1. Lee `.chispaclips/learnings/post-history.jsonl` (cada clip publicado, con su gancho + score del LLM + razón + video fuente).
2. Para cada clip en la ventana de maduración, llama a `GET /api/uploadposts/post-analytics/{request_id}` — el mismo `request_id` que obtuvimos al publicar.
3. Calcula un score compuesto por clip y elige el top 20% (ganadores) y el bottom 20% (perdedores).
4. Envía ganadores + perdedores + el `HOT.md` existente al LLM Flash con un meta-prompt pidiéndole un `HOT.md` actualizado (≤80 líneas) con patrones respaldados por la nueva evidencia.
5. Escribe el nuevo `HOT.md` (respaldando el anterior como `HOT.YYYYMMDD-HHMMSS.md.bak`).
6. Escribe una auditoría completa en `.chispaclips/learnings/runs/learn-YYYY-MM-DD.md` para que el usuario pueda ver exactamente qué clips se llamaron ganadores/perdedores y cómo cambiaron los aprendizajes.

### Cómo HOT.md se realimenta

`analyze` lee automáticamente `.chispaclips/learnings/HOT.md` (si existe y no está vacío) y **lo prepende al prompt del LLM** como "APRENDIZAJES PREVIOS — aplica al seleccionar clips y escribir ganchos". El LLM entonces sopesa esos patrones al proponer clips y escribir ganchos para el video de mañana. **No tienes que hacer nada para que esto funcione** — pasa en cada llamada a `analyze`.

### Cuándo ejecutar `learn`

- **Manualmente**, bajo demanda: `python -m chispaclips learn`
- **Programado**, semanalmente via cron / openclaw: `0 9 * * 1 cd ~/Documents/chispaclips-skill && ./venv/bin/python -m chispaclips learn`
- **Saltar** si `post-history.jsonl` tiene menos de ~10 entradas — la regla de "5 ganadores + 5 perdedores mínimo" cortocircuitará la ejecución con una nota de "datos insuficientes".

### Qué NO hacer

- No edites `HOT.md` a mano Y sigas ejecutando `learn` — `learn` sobrescribirá tus ediciones. Si quieres reglas manuales, ponlas en `.chispaclips/learnings/insights/` (notas manuales, no usadas por el pipeline).
- No borres `post-history.jsonl` ni `metrics.jsonl` — son memoria append-only. Sin ellos cada `learn` empieza desde cero.
- No ejecutes `learn` más de ~1 vez por semana — el LLM solo removerá los mismos patrones.

## Cambio de proveedor LLM

ChispaClips es agnóstico del proveedor. Para cambiar:

```bash
# Editar .env
LLM_PROVIDER=claude            # gemini | claude | openai
ANTHROPIC_API_KEY=sk-ant-...   # rellenar la clave del proveedor elegido
CLAUDE_MODEL=claude-3-5-sonnet-latest
```

El resto de la skill no cambia. Si usas OpenAI-compat (OpenRouter, OpenCode, etc.), ajusta `OPENAI_BASE_URL` y `OPENAI_MODEL`:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=anthropic/claude-3.5-sonnet
```

## Cambio de proveedor de transcripción

ChispaClips también es agnóstico del proveedor de transcripción. Para usar Groq en vez de Whisper local (mucho más rápido, pero envía audio a la nube):

```bash
# 1. Consigue una API key gratis en https://console.groq.com/
# 2. Edita .env:
TRANSCRIBER_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_WHISPER_MODEL=whisper-large-v3   # o whisper-large-v3-turbo

# 3. Listo, la próxima vez que ejecutes `transcribe` usará Groq
python -m chispaclips transcribe "<VIDEO_PATH>"
```

| Aspecto | `whisper` (local) | `groq` (API) |
|---|---|---|
| Velocidad (video de 10 min) | ~5 min en CPU | ~10 segundos |
| Privacidad | 100% local (no sale del equipo) | audio viaja a Groq |
| Costo | Gratis | Tier gratuito generoso + planes de pago |
| Privacidad del modelo | Privado | Compartido |
| Requisito de disco | ~1.5 GB para `medium` | Ninguno |
| Requisito de internet | No (excepto 1ª descarga) | Sí (cada transcripción) |
| Calidad (es-MX, es-CO, es-AR) | Muy buena | Excelente (Whisper large-v3) |
| Límite de tamaño | Sin límite | 25 MB (ChispaClips extrae audio a MP3 si excede) |

## Notas operativas

- **Confirma siempre** antes del Paso 4 (trabajo pesado de ffmpeg — no lo saltes, pero confirma si el LLM devolvió > 15 candidatos — podría perder tiempo), antes del Paso 7 (publicar es irreversible una vez programado), y después del Paso 6 (copy de metadata).
- Si el LLM devuelve JSON malformado, la respuesta cruda se vuelca a `output/<slug>/clips.raw.txt` — léelo y vuelve a promptar manualmente.
- El texto del gancho viene del LLM en el idioma del video. No lo traduzcas.
- El plan gratuito de Upload-Post es **10 subidas/mes** — una publicación a 3 plataformas cuenta como 3. Avisa al usuario si la programación excede la cuota.
- Todos los archivos de clip son rutas absolutas bajo `.chispaclips/output/<video_slug>/`. Surfázcalas claramente para que el harness openclaw pueda adjuntarlas al reenviar a Telegram / WhatsApp / el canal que sea.
- Si `pick` dice "todos los videos ya procesados", avisa al usuario y para — no reproceses. Necesita soltar un video nuevo en `INPUT_FOLDER`.
- El archivo de estado en `.chispaclips/state/processed.json` es la **única** memoria entre ejecuciones. Nunca lo edites programáticamente excepto via `mark-processed`. Si el usuario pide "reprocesar el video X", lo correcto es pedirle confirmación y luego eliminar manualmente la entrada correspondiente de `state/processed.json`.
- El modelo Whisper `medium` (~1.5 GB) se descarga en la primera llamada a `transcribe` — **solo si `TRANSCRIBER_PROVIDER=whisper`**. Avisa al usuario de que la primera ejecución tardará más — las siguientes reutilizan el modelo cacheado. Si `TRANSCRIBER_PROVIDER=groq` no hay descarga inicial.
