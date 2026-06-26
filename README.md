# ChispaClips-Skill

> **Pipeline diario de clips virales para creadores hispanohablantes.**  
> Convierte videos largos en Shorts / Reels / TikToks automáticamente, con
> aprobación desde el móvil y aprendizaje continuo a partir del engagement
> real de cada clip publicado.
>
> Hecho con cariño por **BrainMatic** · [github.com/brainmatic/chispaclips-skill](https://github.com/brainmatic/chispaclips-skill)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Multi-LLM](https://img.shields.io/badge/LLM-Gemini%20%7C%20Claude%20%7C%20OpenAI-purple.svg)](#proveedor-llm)
[![Idioma](https://img.shields.io/badge/idioma-espa%C3%B1ol-red.svg)](#)

---

## 📑 Tabla de contenidos

Este README tiene **dos partes** claramente diferenciadas. Escoge la que necesitas:

| Si eres… | Ve a… |
|---|---|
| 🤖 **Un agente de IA** (Claude Code, Codex, Hermes, Openclaw, GPT, etc.) | [**Sección 1 — Documentación Técnica**](#-secci%C3%B3n-1--documentaci%C3%B3n-t%C3%A9cnica-para-agentes-de-ia) |
| 👤 **Una persona no técnica** que solo quiere hacer clips virales | [**Sección 2 — Guía para Usuarios No Técnicos**](#-secci%C3%B3n-2--gu%C3%ADa-para-usuarios-no-t%C3%A9cnicos) |
| 📦 **Quieres ver la arquitectura y el código** | [**Sección 3 — Arquitectura del Proyecto**](#-secci%C3%B3n-3--arquitectura-del-proyecto) |

---

# 🤖 Sección 1 — Documentación Técnica (para Agentes de IA)

> Esta sección está escrita con Markdown limpio y semántico. Si le das esta URL
> a un agente de IA con acceso a shell, debería poder instalar, configurar y
> ejecutar ChispaClips sin ayuda humana.

## Descripción

`ChispaClips` es una skill (paquete Python) que automatiza el ciclo completo
de creación de clips cortos a partir de videos largos:

1. Elige un video de una carpeta (`INPUT_FOLDER`).
2. Lo transcribe con Whisper local (CPU, modelo `medium` por defecto).
3. Detecta el dialecto del hablante (ej. `es-MX`, `es-CO`).
4. Envía la transcripción + video a un LLM multimodal (Gemini, Claude o
   cualquier API OpenAI-compatible) y le pide una lista de momentos
   virales con marcas temporales ancladas a palabras de la transcripción.
5. Recorta cada candidato con ffmpeg (frame-accurate).
6. Le superpone un texto gancho estilo TikTok con Pillow.
7. Muestra los candidatos al usuario en su chat (Telegram/WhatsApp).
8. Publica los aprobados en TikTok / Instagram / YouTube via Upload-Post.
9. Aprende de la interacción: cada semana refresca `learnings/HOT.md` con
   los patrones que mejor rindieron en métricas reales.

## Requisitos del sistema

- **Python 3.11 o superior** (probado en 3.11, 3.12, 3.14).
- **ffmpeg** y **ffprobe** en `PATH`. Verificar con `ffmpeg -version`.
- **~2 GB de disco** para el modelo Whisper `medium` (cache local).
- **Acceso a internet** para subir videos al LLM y publicar via Upload-Post.
- **Al menos 1 API key** de los proveedores soportados:
  - `GEMINI_API_KEY` (https://aistudio.google.com/apikey — tier gratuito disponible)
  - `ANTHROPIC_API_KEY` (https://console.anthropic.com/)
  - `OPENAI_API_KEY` (https://platform.openai.com/) — también sirve para
    **OpenRouter** y **OpenCode** cambiando `OPENAI_BASE_URL`.
- **Credenciales de Upload-Post**: `UPLOAD_POST_API_KEY` +
  `UPLOAD_POST_PROFILE` (https://app.upload-post.com).

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/brainmatic/chispaclips-skill.git ~/Documents/chispaclips-skill
cd ~/Documents/chispaclips-skill

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
# Alternativa moderna (modo editable, habilita `chispaclips` global):
pip install -e .

# 4. Verificar instalación
python -m chispaclips --version
python -m chispaclips --help
```

## Configuración de Variables de Entorno

Copia `.env.example` a `.env` y rellena los valores:

```bash
cp .env.example .env
nano .env  # o tu editor favorito
```

| Variable | Obligatorio | Default | Descripción |
|---|---|---|---|
| `LLM_PROVIDER` | sí | `gemini` | `gemini` \| `claude` \| `openai` |
| `GEMINI_API_KEY` | condicional | — | API key de Google Gemini (si `LLM_PROVIDER=gemini`) |
| `GEMINI_MODEL` | no | `gemini-3-flash-preview` | Modelo Gemini a usar |
| `ANTHROPIC_API_KEY` | condicional | — | API key de Anthropic (si `LLM_PROVIDER=claude`) |
| `CLAUDE_MODEL` | no | `claude-3-5-sonnet-latest` | Modelo Claude a usar |
| `OPENAI_API_KEY` | condicional | — | API key de OpenAI / OpenRouter / OpenCode |
| `OPENAI_BASE_URL` | no | `https://api.openai.com/v1` | Endpoint compatible |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Modelo a invocar |
| `UPLOAD_POST_API_KEY` | sí (para publicar) | — | API key de Upload-Post |
| `UPLOAD_POST_PROFILE` | sí (para publicar) | — | Nombre del profile en Manage Users |
| `INPUT_FOLDER` | no | `<repo>/.chispaclips/input` | Carpeta con videos largos |
| `OUTPUT_FOLDER` | no | `<repo>/.chispaclips/output` | Carpeta de salida de clips |
| `WHISPER_MODEL` | no | `medium` | `tiny` \| `base` \| `small` \| `medium` \| `large-v3` |
| `WHISPER_LANGUAGE` | no | autodetect | Forzar idioma (ej. `es`, `en`, `pt`) |
| `TIMEZONE` | no | `America/Bogota` | Zona horaria IANA para programaciones |
| `CLAUDE_VIDEO_FRAMES` | no | `12` | Frames a extraer para análisis con Claude |

> **Tip para agentes**: si el usuario te da una API key en el chat, escríbela
> en `.env` de inmediato. **No la devuelvas al chat** y avisa al usuario de
> que debe rotarla después de las pruebas, porque quedó en el historial.

## Estructura del Proyecto

```
chispaclips-skill/
├── SKILL.md                    # Manifiesto YAML para Hermes / Odysseus / Claude Code
├── README.md                   # Este archivo
├── pyproject.toml              # Metadata del paquete + entry point `chispaclips`
├── requirements.txt            # Dependencias (retrocompat)
├── .env.example                # Plantilla de variables de entorno (en español)
├── .gitignore
├── LICENSE                     # MIT
├── chispaclips.py              # Shim retrocompatible (delega al paquete)
└── chispaclips/                # Paquete Python
    ├── __init__.py
    ├── __main__.py             # Permite `python -m chispaclips`
    ├── cli.py                  # argparse + dispatch de subcomandos
    ├── config.py               # Carga de .env + dataclass de configuración
    ├── dialectos.py            # Mapeo Whisper → instrucción de dialecto
    ├── llm/
    │   ├── base.py             # Clase abstracta LLMProvider
    │   ├── factory.py          # Selección por LLM_PROVIDER
    │   ├── gemini.py           # Google Gemini (multimodal nativo, Files API)
    │   ├── claude.py           # Anthropic Claude (extrae frames con ffmpeg)
    │   └── openai_compat.py    # OpenAI / OpenRouter / OpenCode (cualquier API OpenAI-spec)
    ├── prompts/
    │   ├── analisis_es.py      # PROMPT_ANALISIS (con inyección de dialecto)
    │   ├── aprendizaje_es.py   # META_PROMPT_APRENDIZAJE (HOT.md)
    │   └── reflexion_es.py     # META_PROMPT_REFLEXION
    ├── pipeline/
    │   ├── state.py            # cargar_estado, sha256, append_jsonl, gzip
    │   ├── pick.py             # Selección de video + lógica de ciclo
    │   ├── transcribe.py       # Whisper
    │   ├── analyze.py          # LLM multimodal
    │   ├── extract.py          # ffmpeg cut (frame-accurate)
    │   ├── hook.py             # Pillow + ffmpeg overlay (pildora TikTok)
    │   ├── preview.py          # Extracción de frame para QA
    │   ├── publish.py          # Upload-Post API
    │   ├── mark_processed.py   # Estado: hash + ciclo
    │   ├── list_processed.py   # Estado: lectura
    │   ├── learn.py            # Semanal: refresca HOT.md con métricas
    │   └── reflect.py          # Opcional: patrones cualitativos
    └── utils/
        ├── logging.py          # Logger en español (stderr)
        ├── http.py             # requests.Session con reintentos + backoff
        └── ffmpeg.py           # Helpers ffmpeg / ffprobe
```

## Subcomandos

Cada subcomando escribe JSON limpio a stdout (paths/resultados) y logs en
español a stderr. Así un agente puede parsear stdout sin ambigüedad.

| Comando | Propósito |
|---|---|
| `pick` | Selecciona el siguiente video a procesar (ciclo más reciente) |
| `transcribe <video>` | Transcribe con Whisper, escribe `transcript.json` |
| `analyze <video>` | Analiza con el LLM configurado, escribe `clips.json` |
| `extract <video> --start --end --output` | Corta un clip con ffmpeg |
| `hook <video> --text --duration --output` | Superpone el gancho (Pillow) |
| `preview <video>` | Extrae un frame para QA visual |
| `publish <video> --platforms --title --description ...` | Publica via Upload-Post |
| `mark-processed <video> --clips-generated --clips-published` | Marca como consumido |
| `list-processed` | Lista el estado de videos procesados |
| `learn` | Semanal: refresca `HOT.md` con analíticas |
| `reflect` | Opcional: patrones cualitativos de aprobación |

## Uso Programático (CLI)

```bash
# 1. Elegir el siguiente video
python -m chispaclips pick

# 2. Transcribir
python -m chispaclips transcribe .chispaclips/input/mi-video.mp4

# 3. Analizar con el LLM configurado
python -m chispaclips analyze .chispaclips/input/mi-video.mp4

# 4. Para cada clip en clips.json:
python -m chispaclips extract .chispaclips/input/mi-video.mp4 \
    --start 12.34 --end 45.67 \
    --output .chispaclips/output/mi-video/clip_1.mp4

python -m chispaclips hook .chispaclips/output/mi-video/clip_1.mp4 \
    --text "El truco que nadie te cuenta" --duration 3 \
    --output .chispaclips/output/mi-video/clip_1_final.mp4

# 5. Publicar (TikTok por defecto va a draft / MEDIA_UPLOAD)
python -m chispaclips publish .chispaclips/output/mi-video/clip_1_final.mp4 \
    --platforms tiktok,instagram,youtube \
    --title "Título general" \
    --description "Descripción general" \
    --tiktok-title "Truco viral (90 chars máx)" \
    --instagram-title "Caption largo de Instagram (500-800 chars + 20-30 hashtags)" \
    --youtube-title "YouTube SEO title (40-60 chars)" \
    --schedule "2026-06-26T10:00:00" \
    --timezone "America/Bogota" \
    --tiktok-mode draft \
    --clip-id 1 \
    --hook-text "El truco que nadie te cuenta" \
    --viral-score 9 \
    --reason "Gancho con número + sorpresa" \
    --video-source "mi-video.mp4"

# 6. Marcar como procesado
python -m chispaclips mark-processed .chispaclips/input/mi-video.mp4 \
    --clips-generated 5 --clips-published 3
```

## Flujo Diario Automatizado

```bash
# Cron recomendado: cada día a las 9 AM
0 9 * * * cd ~/Documents/chispaclips-skill && ./venv/bin/python -m chispaclips pick
```

El orquestador (openclaw, Hermes, etc.) se encarga de:
- Reenviar el resultado de `pick` al usuario por chat.
- Capturar la respuesta del usuario (qué clips quiere).
- Inyectar la respuesta de vuelta al agente para continuar el flujo.

Para un walkthrough paso a paso del flujo completo, lee [`SKILL.md`](./SKILL.md).

## Proveedor LLM

ChispaClips es agnóstico del proveedor. Para cambiar:

```bash
# Editar .env
LLM_PROVIDER=claude            # gemini | claude | openai
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-latest
```

El resto del código no cambia. Si usas OpenAI-compatible (OpenRouter, OpenCode, etc.):

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=anthropic/claude-3.5-sonnet
```

## Aprendizaje Continuo

Cada clip publicado se registra en `learnings/post-history.jsonl` con su
contexto completo (gancho, score, razón, video fuente). El comando `learn`
se ejecuta semanalmente para refrescar `learnings/HOT.md` con patrones
validados por datos reales de engagement:

```bash
python -m chispaclips learn
# Defaults: --soak-days 7, --max-age-days 90, top/bottom 20%, peso 0.6 vistas + 0.4 engagement
```

El nuevo `HOT.md` se inyecta automáticamente en cada llamada a `analyze`,
haciendo que el LLM priorice los patrones que mejor rindieron.

## Endpoints Externos

| Servicio | URL base | Auth |
|---|---|---|
| Upload-Post (REST) | `https://api.upload-post.com/api` | `Authorization: Apikey <key>` |
| Gemini Files API | `https://generativelanguage.googleapis.com` | `x-goog-api-key: <key>` |
| Anthropic Messages | `https://api.anthropic.com/v1` | `x-api-key: <key>` |
| OpenAI Chat | configurable via `OPENAI_BASE_URL` | `Authorization: Bearer <key>` |

## Limitaciones Conocidas

- **Cuota Upload-Post gratis**: 10 subidas/mes (1 publicación a 3 plataformas = 3).
- **Whisper primer uso**: ~1.5 GB de descarga, cache local después.
- **Gemini Files API**: procesa videos en 30-60s antes de ser consultables.
- **Rate limiting**: el diseño diario evita flags de TikTok/Instagram por
  publicación masiva.
- **Videos de entrada**: deben ser 9:16 vertical (1080×1920). La skill NO
  recorta ni reformatea.

---

# 👤 Sección 2 — Guía para Usuarios No Técnicos

> Si nunca has programado o no quieres saber qué es Python, esta sección
> es para ti. Léela en orden, sigue los pasos, y tendrás ChispaClips
> funcionando en menos de 30 minutos.

## ¿Qué es ChispaClips? (explicación sencilla)

Imagina que tienes un video de 30 minutos en YouTube. Dentro hay 4 o 5
momentos que podrían volverse virales como TikToks o Reels. ChispaClips
los encuentra automáticamente, los recorta, les pone un texto llamativo
encima, y te los manda al móvil para que tú elijas cuáles quieres
publicar.

Tú solo tienes que:
1. **Arrastrar** el video a una carpeta.
2. **Responder** "1, 3, 5" por WhatsApp o Telegram.
3. **Listo.** El bot publica los clips que elegiste.

Lo demás lo hace una inteligencia artificial.

## ¿Qué necesito para empezar?

- **Una computadora** (Mac, Linux o Windows con WSL).
- **Una cuenta gratuita en Google** (para la IA de Gemini).
- **Una cuenta gratuita en Upload-Post** (para publicar en TikTok, etc.).
- **Las llaves de acceso** que se generan en esas páginas (son como contraseñas especiales para que la IA trabaje por ti).

No necesitas saber programar. Solo seguir los pasos.

## Cómo empezar en 5 minutos

### Paso 1 — Pídele a tu asistente de IA que lo instale

Abre tu agente favorito (Claude Code, GPT, Cursor, etc.) y dile:

> *"Configura https://github.com/brainmatic/chispaclips-skill para mí. Lee el README.md."*

El agente se encargará de:
- Descargar el código.
- Instalar las dependencias.
- Pedirte las dos claves que necesita (Gemini y Upload-Post).

### Paso 2 — Consigue las dos claves gratuitas

#### Clave 1: Google Gemini (la IA que analiza tus videos)
1. Ve a https://aistudio.google.com/apikey
2. Inicia sesión con tu cuenta de Google.
3. Haz clic en "Create API key".
4. Copia la clave (empieza con `AIza...`).

#### Clave 2: Upload-Post (para publicar en TikTok / Instagram / YouTube)
1. Ve a https://app.upload-post.com
2. Crea una cuenta gratis.
3. Conecta tus redes sociales (TikTok, Instagram, YouTube) desde el panel.
4. Crea un "profile" en **Manage Users** (ponle el nombre que quieras, ej. "mi-cuenta").
5. En **Settings**, genera una API key.
6. Anota: la API key + el nombre de tu profile.

### Paso 3 — Pega las claves en el archivo `.env`

Tu agente de IA te dirá exactamente dónde pegar las claves. Solo cópialas y
pégalas. **No las compartas con nadie.**

## Cómo subir tu primer video

Tienes dos opciones:

### Opción A — Por chat (más fácil)

Manda el video por WhatsApp o Telegram a tu agente. Él lo guarda
automáticamente en la carpeta correcta.

### Opción B — Arrastrando el archivo

Si no usas un agente conversacional, abre la carpeta del proyecto y arrastra
el archivo de video a la carpeta que se llama `input/` (o `.chispaclips/input/`
si la viste con archivos ocultos visibles).

**Importante**: el video debe estar en formato **vertical 9:16** (1080×1920
pixeles), como un TikTok. Si grabas en horizontal, primero recórtalo con
algún editor (CapCut, iMovie, etc.).

## Cómo aprobar clips desde el móvil

Cada día, o cuando tú quieras, tu agente te manda un mensaje como este:

```
📱 ChispaClips — 3 clips listos para revisar

| # | Duración | Gancho                          | Tu nota                    |
|---|----------|---------------------------------|----------------------------|
| 1 | 38s      | "El truco que nadie te cuenta"  | ✅ se ve bien              |
| 2 | 27s      | "Por qué tu café está mal"     | ⚠️ acento cortado          |
| 3 | 41s      | "3 errores al empezar"          | ✅ publicable               |

¿Qué IDs quieres publicar? (ej. 1, 3, o ninguno)
```

Tú respondes, desde el móvil, lo que quieras:
- `1, 3` → publicas los clips 1 y 3.
- `ninguno` → no publicas ninguno (el video se marca como visto).
- `1 y 3` → también funciona.

El bot publica los clips que elegiste con el título, descripción y hashtags
adecuados para cada plataforma (TikTok, Instagram, YouTube).

## Cómo leer los resultados

Después de publicar, puedes ver los archivos generados:

- **`.chispaclips/output/mi-video/clip_1_final.mp4`** → El video final
  con el texto gancho encima.
- **`.chispaclips/output/mi-video/clips.json`** → La lista de momentos
  que la IA detectó como virales.
- **`.chispaclips/output/mi-video/transcript.json`** → Lo que la IA
  entendió del audio.
- **`.chispaclips/learnings/HOT.md`** → Lo que el sistema aprendió sobre
  tus hooks con el tiempo. Se actualiza solo cada semana.

## ¿Y si algo falla?

- **"No hay videos en la carpeta"** → Arrastra un video a la carpeta `input/`.
- **"Falta la API key"** → Pega las claves en el archivo `.env`.
- **"El video se ve raro"** → Probablemente está en horizontal. Conviértelo
  a 9:16 vertical con CapCut o iMovie.
- **"No tengo TikTok / Instagram / YouTube conectado"** → Ve a
  https://app.upload-post.com y conéctalos desde el panel.

## Glosario rápido (palabras que escucharás)

| Término | Qué significa |
|---|---|
| **Clip** | Un pedacito corto de video (20-60 segundos). |
| **Gancho (hook)** | El texto que aparece al inicio del clip para llamar la atención. |
| **Ciclo** | Una vuelta completa de todos tus videos. Cuando termina, empieza otra. |
| **HOT.md** | La "memoria" del sistema: lo que aprendió sobre tus clips favoritos. |
| **Transcripción** | El texto escrito de lo que se dice en el video. |

---

# 📦 Sección 3 — Arquitectura del Proyecto

## Diagrama del pipeline

```
┌─────────────────┐
│  video largo    │
└────────┬────────┘
         │
         ├──────────► Whisper (local, faster-whisper)
         │             └─► transcript.json (palabra por palabra)
         │             └─► detección de dialecto (es-MX, es-CO, …)
         │
         └──────────► LLMProvider (Gemini / Claude / OpenAI-compat)
                       ├─► Gemini:    sube video vía Files API
                       ├─► Claude:    extrae 12 frames con ffmpeg
                       └─► OpenAI:    sube video o frames según tamaño
                                  │
                                  ▼
                          clips.json (5-20 candidatos)
                                  │
                                  ▼
                          ffmpeg cut (extract)
                                  │
                                  ▼
                          Pillow hook (pildora TikTok)
                                  │
                                  ▼
                          Upload-Post API
                                  ├─► TikTok (draft o directo)
                                  ├─► Instagram Reels
                                  └─► YouTube Shorts
```

## Por qué Whisper + LLM multimodal

- **Whisper** = el reloj. Marcas a nivel de palabra significan que cada
  corte empieza y termina en una palabra limpia. Nunca corta a media sílaba.
- **LLM multimodal** = el editor. Ve el video, escucha el audio, ve los
  subtítulos quemados, detecta risas y gestos, identifica cambios de escena.
  El prompt le obliga a usar las marcas de la transcripción, así que no
  alucina marcas temporales.
- **Pipeline humano-en-el-bucle** = la calidad. La IA propone; tú decides.
  Cada candidato se recorta y renderiza antes de que lo veas, así revisas
  el video real, no una descripción.

## Estructura del estado en disco

```
chispaclips-skill/
├── .chispaclips/                # runtime (gitignored)
│   ├── input/                   # videos largos 9:16
│   ├── output/
│   │   └── <video_slug>/
│   │       ├── transcript.json
│   │       ├── clips.json
│   │       ├── clip_<ID>.mp4
│   │       ├── clip_<ID>_final.mp4
│   │       └── preview_*.png
│   ├── state/
│   │   └── processed.json       # sha256-keyed, con cycles_count
│   └── learnings/
│       ├── HOT.md               # auto-managed por `learn`
│       ├── post-history.jsonl   # cada clip publicado (request_id, hook, …)
│       ├── candidate-history.jsonl
│       ├── metrics.jsonl[.gz]   # se comprime con gzip tras 10 MB
│       ├── insights/            # notas manuales (no usadas por el pipeline)
│       └── runs/
│           ├── learn-YYYY-MM-DD.md
│           └── reflect-YYYY-MM-DD-HHMM.md
```

## Por qué `.chispaclips/` y no `state/`, `learnings/`, etc.

Decisión de diseño: en lugar de llenar la raíz del proyecto con 4 carpetas
técnicas (`state/`, `learnings/`, `output/`, `input/`), las unificamos bajo
un único directorio oculto `.chispaclips/`. Beneficios:

- La raíz del repo queda limpia (un agente IA que abre el proyecto ve
  claramente `README.md`, `SKILL.md`, `chispaclips/` y `.chispaclips/`).
- `.gitignore` es trivial (una línea: `.chispaclips/`).
- Compatible con File System Access API en navegadores (carpeta única).
- La ruta de runtime se configura via `INPUT_FOLDER` / `OUTPUT_FOLDER` en
  `.env` (default: `.chispaclips/{input,output}/`).

## Atribuciones

- **Autor original**: [mutonby](https://github.com/mutonby) — repositorio
  [Upload-Post/skill-autoshorts](https://github.com/Upload-Post/skill-autoshorts)
  v2.0.0 (MIT). La arquitectura del pipeline es suya.
- **Fork y mantenimiento**: [BrainMatic](https://github.com/brainmatic).
  Refactor modular, localización al español, abstracción multi-LLM,
  detección automática de dialecto y optimizaciones.
- **APIs externas**:
  - [Upload-Post](https://upload-post.com) — publicación multi-plataforma.
  - [Google Gemini](https://aistudio.google.com/) — IA multimodal.
  - [Anthropic Claude](https://www.anthropic.com/) — IA multimodal.
  - [OpenAI](https://openai.com/) / [OpenRouter](https://openrouter.ai/) /
    [OpenCode](https://opencode.ai/) — IA multimodal OpenAI-compatible.
  - [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — transcripción local.

## Licencia

MIT. Ver [`LICENSE`](./LICENSE).

---

¿Encontraste un bug? ¿Quieres pedir una función? Abre un issue en
[github.com/brainmatic/chispaclips-skill/issues](https://github.com/brainmatic/chispaclips-skill/issues).
