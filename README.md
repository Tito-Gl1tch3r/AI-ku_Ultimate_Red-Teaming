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
│   ├── 02_github_verify.py     Fase 2a — puerta dura de licencias upstream (reanudable por chunks)
│   ├── 03_mine_github.py       Fase 2b — clonado + minería + manifiesto de procedencia (incremental)
│   ├── 04_verify.py            Fase 2c — verificación de integridad (sha256, firmas, NOTICE, huérfanos)
│   ├── 05_expand_github.py     Fase 2e — expansión dirigida (stars≥25, keywords, orgs curadas)
│   ├── 06_hf_dataset_search.py Fase 2d — datasets públicos en HF con regla de licencia estricta
│   └── 07_repair_attribution.py Fase 2f — mantenimiento: purga de duplicados + reparación de atribución
├── audit/topics_audit.json     auditoría de estructura del dataset (shards/filas/fuente por tópico)
├── audit/hf_vs_cleanroom.json  comparativa de calidad HF vs corpus limpio (contaminación de licencias)
├── audit/hf_datasets_candidates.json  datasets HF evaluados por licencia declarada (ACEPTADO/REVISAR/RECHAZADO)
├── catalog/{topic}.json        catálogo por tópico (9.576 repos únicos en la unión)
├── catalog/github/             verificación de licencias (verified.jsonl, resumen, checkpoint)
├── results/demo/               tanda de demostración: manifiesto + estadísticas + dedup
├── results/full-1/             tanda completa: 3.553 repos · 228.880 archivos · dedup + reparaciones
├── results/verification/       informes de integridad por tanda (5/5 OK en full-1)
└── corpus/                     código extraído, versionado con atribución (_UPSTREAM_LICENSE/NOTICE por repo; variantes dual-licencia preservadas)
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

# Fase 2e — expansión dirigida (tópicos deficitarios: pwn/exploit/osint)
python3 src/05_expand_github.py --stars 25

# Fase 2d — exploración de datasets públicos en HF (solo licencia declarada; sin contenido)
python3 src/06_hf_dataset_search.py

# Fase 2f — mantenimiento del corpus (purga duplicados + reparación de atribución)
python3 src/07_repair_attribution.py --label full-1 --purge-duplicates --fix-attribution
```

> **Nota de ejecución (entornos con límite de tiempo por llamada):** 02, 03 y 07 aceptan `--max-runtime N` para salir limpiamente tras N segundos; todos son reanudables vía checkpoint (`_checkpoint.json`, `_mined.json`, `_attribution.json`). Patrón recomendado para tandas grandes: bucles de chunks de ~500 s.

## 5. La rúbrica (resumen)

`rubric.json` es la definición formal y automatizable (orden determinista, primer fallo = veredicto). Sin censura temática: exploits, C2, shellcode, evasión o ingeniería inversa **nunca** son motivo de exclusión. Solo se excluye por licencia no permisiva o basura técnica:

| Fase | Criterio | Umbral exacto |
|---|---|---|
| 1 · Licencia | `license.spdx_id` (GitHub API) | ∈ {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause} |
| 2 · Rutas | dirs vendored/IDE/build; lockfiles; binarios; stubs | listas cerradas en `rubric.json` |
| 3 · Contenido | tamaño; binario (byte nulo); minificado; autogenerado; trivial | 80 B–256 KiB · ≥30 chars útiles · avg línea <180 |
| 4 · Calidad | puntuación 0–100 (estructura, volumen, comentarios, profundidad técnica, modularidad) | aceptación ≥ 40 |

## 6. Resultados

### 6.0 Tanda completa `full-1` (base consolidada)

| fase | resultado |
|---|---|
| Catálogo (01) | 30 configs auditados; unión de 9.576 repos; expansión dirigida (05): +2.625 → plan final 11.090 únicos |
| Verificación (02) | **11.090/11.090 verificados** · 4.215 aceptados · 6.623 licencia no permisiva · 251 desaparecidos · 1 DMCA |
| Minería (03) | plan 4.563 → 3.553 repos minados · 0 fallos de clonado · 609.619 rechazos (razones deterministas) |
| Dedup exacto | 6.989 duplicados marcados y purgados del corpus (sha256) |
| Integridad (04) | **5/5 OK**: 228.880 archivos sha256-verificados · 0 huérfanos · 0 rechazados presentes |
| Exclusiones post | 6 repos sin LICENSE en raíz (spdx de la API caducado) → eliminados por directiva estricta |
| Atribución (07) | 679 reparaciones; variantes cubiertas: LICENCE, MIT-LICENSE, LICENSE-MIT/APACHE, dual-licencia (ambos textos preservados) |
| Corpus final | **228.880 archivos · ~232.000 con atribución · 2,7 GB** |

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

### 6.2 Datasets públicos en Hugging Face (exploración con regla de licencia estricta)

Exploración de datasets HF orientados a `pwn`, `binary-exploitation`, `ctf`, `reverse-engineering`, `exploit-code` y `osint` — **sin descargar jamás su contenido**; solo metadata/tarjeta (`audit/hf_datasets_candidates.json`, 214 datasets evaluados):

- **23 ACEPTADO (STRONG)** — licencia declarada permisiva + foco real. Ejemplos: `ethz-spylab/ctf-satml24` (MIT, retos CTF reales), `jason-oneal/mitre-stix-cve-exploitdb-*` (Apache-2.0, señales CVE/exploit), `exploitintel/cve-cwe-consensus` (CC-BY-4.0), `qizwiz/pact-ctf-corpus` (MIT), `invariantlabs/agent-ctf24-public` (MIT), familia `Yemen-JPT/OSINT-*` (CC-BY-4.0).
- **13 MARGINAL** — `jordan-taylor-aisi/*` (Apache-2.0): trazas de evaluación de agentes CTF, no código.
- **7 FALSO POSITIVO** — descartados por curación (minería en francés `site d'exploitation`, usernames con 'pwn', etc.).
- **17 REVISAR** — permisiva declarada pero parecen compilaciones (casi todos espejos de ExploitDB): exigen licencias por registro o síntesis propia; upstream no las provee → no usar sin verificación registro a registro.
- **154 RECHAZADO** — CC-BY-NC, GPL/AGPL, `other`/privativa o sin licencia explícita.

> Regla aplicada (decisión del usuario): MIT · Apache-2.0 · BSD-2/3 · **CC-BY-4.0** (solo para datasets HF; el gate de código GitHub sigue siendo MIT/Apache/BSD). NC y sin licencia explícita → fuera.

## 7. Escalado y costes reales (medidos)

- Verificación completa (11.090 repos): el cuello de botella es el límite REST de GitHub (5.000/h con token clásico) → ~2 h con chunks de 500 s reanudables. No depende de nosotros: planificar en consecuencia.
- Minería completa (3.553 clones): ~1,4 s/repo medio con `--depth 1` → ~1,5 h total; reanudable por `_mined.json`.
- Reproducibilidad exacta: hoy el manifiesto registra el commit minado, pero 03 clona HEAD; para reprodución bit a bit usar clones pineados al commit del manifiesto (ver hoja de ruta).
- Recomendado para el entrenamiento: dedup exacto (incluido) + dedup aproximado (MinHash) en fase posterior.

## 8. Hoja de ruta

- [ ] Fase 3: empaquetado del corpus a formato de entrenamiento (JSONL `content` + metadatos) — en pausa hasta integrar HF (06) + expansión (05), según plan del usuario
- [x] Exploración HF (06) y expansión dirigida (05) — completadas en esta revisión
- [ ] Clones pineados al commit del manifiesto (reproducibilidad bit a bit del corpus)
- [ ] Dedup aproximado (MinHash/LSH) sobre el corpus completo
- [ ] Re-verificación periódica de licencias upstream antes de cada tanda
- [ ] Panel de estadísticas del corpus (lenguajes, tópicos, tamaños)
- [ ] Distribución del corpus >2 GB: valorar GitHub Release assets en lugar de historial git

## 9. Aviso

Este proyecto trabaja exclusivamente con código público de seguridad ofensiva bajo licencias permisivas, con fines de investigación, educación y testing defensivo. El linaje legal del corpus está diseñado para ser auditable (manifiesto + licencia upstream por repo). Esto no constituye asesoramiento legal: antes de publicar AI-ku en producción, conviene una revisión formal por parte de un especialista.
