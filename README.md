# AI-ku · Ultimate Red-Teaming

**Pipeline clean-room de datos para el entrenamiento de AI-ku** — modelo especializado en ciberseguridad, ingeniería de sistemas, offensive security y red teaming.

> Estrategia: **Hugging Face solo como catálogo. El corpus de entrenamiento se mina 100% desde GitHub upstream, con licencia permisiva formalmente verificada.**

---

## 1. Por qué una arquitectura clean-room

El dataset [`tandevllc/offsec_redteam_codes`](https://huggingface.co/datasets/tandevllc/offsec_redteam_codes) es una *compilación* publicada bajo **"TanDev Proprietary License — All Rights Reserved"**. Aunque el código original pertenece a sus autores, la base de datos compilada les pertenece a ellos. Entrenar AI-ku con esos shards:

1. Contaminaría el linaje legal del modelo con una licencia privativa ajena.
2. Invalidaría la publicación de AI-ku bajo su propia licencia abierta.
3. Expondría el modelo a retirada por vulneración de términos.

La propia documentación de TanDev reconoce: *"Rights in the original repositories remain with their owners. This compilation license does not limit rights you already have in the upstream sources."* Por tanto, el pipeline usa Hugging Face **exclusivamente como índice** (metadatos: `repo_name`, `license`, `topic`, estadísticas) y obtiene todo el código clonando directamente los repositorios originales de GitHub, aceptando solo los que tienen **LICENSE formal en la raíz bajo MIT, Apache-2.0, BSD-2-Clause o BSD-3-Clause**.

**Prohibido por diseño:** descargar shards de HF, leer la columna `content`, o usar cualquier contenido de la compilación como dato de entrenamiento.

## 2. Arquitectura

```
┌───────────────────────────── FASE 1 · CATÁLOGO (solo metadatos) ────────────────────────────┐
│  Hugging Face (tandevllc/offsec_redteam_codes, 30 configs, ~3.1M filas, 186 shards)         │
│    ├─ /api/datasets ............ estructura, shards por tópico         (auditoría)          │
│    ├─ /statistics ............. frecuencias server-side de repo_name   (17 configs)         │
│    └─ (fallback) GitHub Search API `topic:{t}` ........................ (13 configs)         │
│  SALIDA: catalog/{topic}.json · catalog/_union.json (9.576 repos únicos)                    │
│  NUNCA: descarga de parquet, streaming de content, persistencia de contenido HF             │
└────────────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────── FASE 2a · VERIFICACIÓN DE LICENCIA (GitHub) ──────────────────────┐
│  GET /repos/{owner}/{repo} → license.spdx_id (detector licensee sobre el LICENSE raíz)      │
│  ACEPTADO: MIT · Apache-2.0 · BSD-2-Clause · BSD-3-Clause                                   │
│  RECHAZADO: GPL/AGPL/LGPL/CC/NOASSERTION/null · REPO_MISSING (404) · DMCA_BLOCKED (451)     │
│  SALIDA: catalog/github/verified.jsonl (+ _summary.json, _checkpoint.json reanudable)        │
└────────────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────── FASE 2b · MINERÍA CON RÚBRICA (rubric.json) ──────────────────────┐
│  git clone --depth 1 → walk con poda de dirs → judge_file() determinista por archivo        │
│  ACCEPT → corpus/{owner}__{repo}/{ruta} + _UPSTREAM_LICENSE (atribución)                    │
│  REJECT → razón determinista (PATH_*, EXT_*, TOO_*, BINARY, MINIFIED, AUTOGEN, LOW_SCORE)   │
│  SALIDA: results/{label}/manifest.jsonl (repo, commit, sha256, score, spdx) · stats.md      │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Estructura del repositorio

```
├── rubric.json                 rúbrica formal de aceptación/rechazo (determinista, sin LLM)
├── src/
│   ├── 01_hf_catalog.py        Fase 1 — catálogo híbrido (hf-statistics | github-topics)
│   ├── 02_github_verify.py     Fase 2a — puerta dura de licencias upstream
│   ├── 03_mine_github.py       Fase 2b — clonado + minería + manifiesto de procedencia
│   └── 04_verify.py            Fase 2c — verificación de integridad (sha256, firmas, NOTICE)
├── audit/topics_audit.json     auditoría de estructura del dataset (shards/filas/fuente por tópico)
├── audit/hf_vs_cleanroom.json  comparativa de calidad HF vs corpus limpio (contaminación de licencias)
├── catalog/{topic}.json        catálogo por tópico (9.576 repos únicos en la unión)
├── catalog/github/             verificación de licencias (verified.jsonl, resumen, checkpoint)
├── results/demo/               tanda de demostración: manifiesto + estadísticas + dedup
├── results/verification/       informes de integridad por tanda
└── corpus/                     código extraído, versionado con atribución (_UPSTREAM_LICENSE/NOTICE por repo)
```

## 4. Uso

Requisitos: Python ≥ 3.9 (solo stdlib) · git ≥ 2.25. Variables de entorno (nunca se versionan):

```bash
export HF_TOKEN=...       # token de lectura HF (gate del dataset aceptado)
export GITHUB_TOKEN=...   # token de lectura GitHub (repos + search)
```

Ejecución en orden (los tres son reanudables/idempotentes sobre sus salidas):

```bash
# Fase 1 — catálogo completo por tópicos (30 configs; 'raw' no existe en la revisión actual)
python3 src/01_hf_catalog.py --fallback-pages 5

# Fase 2a — verificación de licencias
#   demo acotada (top-30 por tópico, ~3 min):
python3 src/02_github_verify.py --per-topic 30
#   escala completa (9.576 repos, ~40 min con delay 0.22s; checkpoint reanudable):
python3 src/02_github_verify.py

# Fase 2b — minería con la rúbrica
python3 src/03_mine_github.py --topics ctf,pwn,osint --repos-per-topic 5 --label tanda1

# Fase 2c — verificación de integridad (sha256, firmas de licencia, NOTICE, huérfanos)
python3 src/04_verify.py --label tanda1
```

## 5. La rúbrica (resumen)

`rubric.json` es la definición formal y automatizable (orden determinista, primer fallo = veredicto). Sin censura temática: exploits, C2, shellcode, evasión o ingeniería inversa **nunca** son motivo de exclusión. Solo se excluye por licencia no permisiva o basura técnica:

| Fase | Criterio | Umbral exacto |
|---|---|---|
| 1 · Licencia | `license.spdx_id` (GitHub API) | ∈ {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause} |
| 2 · Rutas | dirs vendored/IDE/build; lockfiles; binarios; stubs | listas cerradas en `rubric.json` |
| 3 · Contenido | tamaño; binario (byte nulo); minificado; autogenerado; trivial | 80 B–256 KiB · ≥30 chars útiles · avg línea <180 |
| 4 · Calidad | puntuación 0–100 (estructura, volumen, comentarios, profundidad técnica, modularidad) | aceptación ≥ 40 |

## 6. Resultados de la tanda de demostración

- **Fase 1:** 9.576 repos únicos (17 configs vía `/statistics`, 13 vía GitHub topics — los de cardinalidad alta).
- **Fase 2a** (top-30/tópico, 759 repos): **301 aceptados** · 436 licencia no permisiva · 21 repos desaparecidos · 1 DMCA bloqueado (`BloodHound`, HTTP 451 — excluido correctamente por el pipeline).
- **Fase 2b** (3 repos: `CobaltStrike_OpenBeacon` MIT, `ysoserial` MIT, `SteppingStones` Apache-2.0): **144 archivos aceptados / 382 rechazados** — razones principales: AUTOGEN 126, EXT_NOT_ALLOWED 117, LOW_SCORE 76, TOO_SMALL 49. 0 duplicados (sha256).
- Cada archivo aceptado queda en `results/demo/manifest.jsonl` con repo, commit, sha256, score, SPDX y fecha: **trazabilidad total del linaje**.
- **Verificación de integridad (04): 5/5 OK** — 144/144 sha256 válidos, LICENSE firmado según SPDX en los 3 repos, cumplimiento NOTICE (Apache-2.0), 0 huérfanos, 0 rechazados presentes. Informe: `results/verification/demo.json`.

### 6.1 ¿Es la misma calidad que el dataset de Hugging Face?

**No es el mismo corpus: es el subconjunto legal y técnicamente limpio del mismo upstream.** Comparativa medida (metadatos server-side, método en `audit/hf_vs_cleanroom.json`):

| | filas HF | % con licencia permisiva | tras rúbrica (est.) |
|---|---:|---:|---:|
| TOTAL (30 configs) | 3.813.682 | **22,5%** | **~235.080 (6,2%)** |

- **Calidad legal:** el 77,5% de las filas de HF son de repos con licencia no permisiva (GPL, CC, sin licencia…) o sin etiqueta — jamás entrarían en AI-ku. Casos extremos: `exploit` 1,9% permisivo, `osint` 7,3%, `pwn` 4,7%; frente a `exploitation` 68,3% o `persistence` 65,4%.
- **Calidad técnica:** de lo que sí pasa la puerta de licencia, la rúbrica elimina otro 72,6% de basura (minificados, autogenerados, triviales) — medido en la tanda demo.
- **Trazabilidad:** HF no da commit ni hash; nuestro manifiesto da commit + sha256 + SPDX por archivo, y las licencias se verifican contra GitHub **hoy** (las etiquetas de HF pueden estar caducadas: los repos cambian de licencia).
- **Cobertura:** para 17/30 tópicos el catálogo reproduce exactamente los repos de HF (derivado de sus metadatos); para 13/30 (cardinalidad alta) usamos descubrimiento independiente en GitHub top-500 por estrellas — difiere por diseño.
- Conclusión: **menos volumen (~6% de las filas), mucha más señal**: lo que HF habría publicado si filtrara por licencia y calidad.

## 7. Escalado

- Verificación completa: 9.576 repos ≈ 40 min (delay 0.22 s; límite API 5.000/h con token clásico; el checkpoint reanuda donde lo dejaste).
- Minería completa: proporcional al nº de repos; el walk poda directorios excluidos sin leerlos.
- Recomendado para el entrenamiento: dedup exacto (ya incluido) + dedup aproximado (MinHash) en una fase posterior.

## 8. Hoja de ruta

- [ ] Fase 3: empaquetado del corpus a formato de entrenamiento (JSONL con `content` + metadatos)
- [ ] Dedup aproximado (MinHash/LSH) sobre el corpus completo
- [ ] Verificación periódica de licencias upstream (los repos pueden cambiar de licencia; re-verificar antes de cada tanda)
- [ ] Panel de estadísticas del corpus (lenguajes, tópicos, distribución de tamaños)

## 9. Aviso

Este proyecto trabaja exclusivamente con código público de seguridad ofensiva bajo licencias permisivas, con fines de investigación, educación y testing defensivo. El linaje legal del corpus está diseñado para ser auditable (manifiesto + licencia upstream por repo). Esto no constituye asesoramiento legal: antes de publicar AI-ku en producción, conviene una revisión formal por parte de un especialista.
