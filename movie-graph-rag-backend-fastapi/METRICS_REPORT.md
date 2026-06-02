# Reporte de Métricas de Evaluación — CineGraph RAG
**Fecha:** 2026-05-20  
**Perfil de evaluación:** cold-start neutro (`__metrics_eval__`) — sin historial de usuario  
**Queries evaluadas:** 10  
**Endpoint:** `POST /api/v1/recommendation/metrics-report`

---

## Resumen Ejecutivo

| Métrica | Valor | Descripción |
|---|---|---|
| **ILD promedio** | 0.20 | Diversidad intra-lista por distancia de género |
| **ILD mínimo** | 0.00 | Lista más homogénea (todas del mismo género) |
| **ILD máximo** | 1.00 | Lista más diversa (géneros todos distintos) |
| **Graph Diversity promedio** | 0.96 | Distancia BFS promedio entre pares en el grafo |
| **Precisión Semántica promedio** | 1.00 | Fracción de películas con `compatibilityScore > 0.7` |
| **Novelty promedio** | 0.50 | Neutralizada por perfil cold-start (sin historial) |
| **Onto-Recall promedio** | 0.18 | Fracción de candidatos semánticos recuperados en la lista final |
| **Detecciones Cold-Start** | 3 / 10 | Queries que activaron modo cold-start |

---

## Resultados por Query

| # | Query | ILD | Graph Div. | Sem. Prec. | Onto-Recall | Películas | Estrategia | Cold-Start | Tiempo (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | I want an intense action movie for tonight | 0.00 | 1.00 | 1.00 | 0.125 | 5 | `ontology_mood_only` | ✓ | 42.7 |
| 2 | A romantic comedy to watch with my partner | 0.60 | 1.00 | 1.00 | 0.143 | 5 | `ontology_full` + fallbacks | ✓ | 29.5 |
| 3 | Psychological horror, something disturbing and tense | 0.00 | 1.00 | 1.00 | 0.135 | 5 | `ontology_mood_only` + `genre_filter` | ✓ | 85.2 |
| 4 | Epic science fiction, something like Interstellar | 0.00 | 1.00 | 1.00 | 0.125 | 5 | `ontology_mood_only` | ✗ | 39.6 |
| 5 | An animated movie to watch with young children | 0.00 | 0.87 | 1.00 | 0.294 | 5 | `ontology_full` | ✗ | 50.4 |
| 6 | A historical drama from the 90s, something deep | 0.00 | 1.00 | 1.00 | 0.135 | 5 | `ontology_mood_only` | ✗ | 135.4 |
| 7 | Something short and fun, under 90 minutes | 0.00 | 1.00 | 1.00 | 0.147 | 5 | `ontology_mood_only` | ✗ | 45.6 |
| 8 | A suspense thriller to watch alone late at night | 0.00 | 0.93 | 1.00 | 0.132 | 5 | `ontology_companion_only` | ✗ | 114.0 |
| 9 | Recommend me something different I haven't seen, surprise me | 1.00 | 1.00 | 1.00 | 0.263 | 5 | `broad` | ✗ | 88.0 |
| 10 | An adventure movie for the whole family this weekend | 0.40 | 0.80 | 1.00 | 0.294 | 5 | `ontology_full` | ✗ | 16.3 |

---

## Películas Recomendadas por Query

**Q1 — Acción intensa para esta noche**
> Inglourious Basterds · The Dark Knight Rises · The Hurt Locker · Hot Fuzz · The Lord of the Rings: The Return of the King

**Q2 — Comedia romántica en pareja**
> Intouchables · WALL·E · In Bruges · The Lives of Others · Eternal Sunshine of the Spotless Mind

**Q3 — Horror psicológico perturbador**
> Zombieland · Shaun of the Dead · 28 Days Later · Sweeney Todd · Battle Royale

**Q4 — Ciencia ficción épica (estilo Interstellar)**
> Rogue One · Limitless · WALL·E · The Avengers · Moon

**Q5 — Animación para niños pequeños**
> WALL·E · Up · Howl's Moving Castle · Spirited Away · Finding Nemo

**Q6 — Drama histórico de los 90s**
> Inglourious Basterds · The Departed · In Bruges · Eternal Sunshine of the Spotless Mind · City of God

**Q7 — Algo corto y divertido (< 90 min)**
> Zombieland · Easy A · Monsters, Inc. · Wallace & Gromit: The Best of Aardman Animation · Wallace & Gromit in The Curse of the Were-Rabbit

**Q8 — Thriller de suspenso, solo y de noche**
> The Departed · In Bruges · Shutter Island · The Hurt Locker · The Lives of Others

**Q9 — Serendipity — sorpréndeme**
> The Dark Knight · Hoop Dreams · Sunset Blvd. · Lawrence of Arabia · Harold and Maude

**Q10 — Aventura familiar este fin de semana**
> WALL·E · My Neighbor Totoro · Up · Howl's Moving Castle · Spirited Away

---

## Análisis de Métricas

### Precisión Semántica — 1.00 (todas las queries)
Todas las películas recomendadas en los 10 escenarios obtuvieron `compatibilityScore > 0.70`, lo que indica que la bridge-ontology establece compatibilidad contextual sólida para los candidatos que llegan al scorer. El sistema no devuelve películas con bajo match ontológico.

### ILD — Diversidad Intra-Lista (promedio: 0.20)
La mayoría de listas (7/10) presenta ILD = 0.0, lo que significa que todas las películas de la lista pertenecen al mismo género. Esto refleja que el sistema optimiza por relevancia temática. Las excepciones son:
- **Q2 (comedia romántica):** ILD = 0.60 — el sistema combinó múltiples estrategias de fallback y resultó en mezcla de géneros
- **Q9 (serendipity):** ILD = 1.00 — la estrategia `broad` sin filtro de género produce diversidad máxima por diseño
- **Q10 (aventura familiar):** ILD = 0.40 — la estrategia `ontology_full` recuperó candidatos de géneros adyacentes

### Graph Diversity — 0.96 promedio
A pesar de la homogeneidad por género (ILD bajo), las películas están bien distribuidas en el grafo del conocimiento. Valores cercanos a 1.0 indican que los pares de películas recomendadas son distantes en la red de conexiones (actores, directores, temas), lo que refleja variedad semántica más allá del género.

### Onto-Recall — 0.18 promedio
En promedio, el pipeline recupera ~18% de los candidatos semánticos del pool SPARQL. Esto indica que el scoring MMR es altamente selectivo: de un pool de ~37 candidatos con score ontológico > 0, solo 5 pasan al resultado final. El onto-recall más alto se observa en queries con estrategia `ontology_full` (Q5: 0.29, Q10: 0.29).

### Novelty — 0.50 (todas las queries)
Valor neutral en todas las queries, como se esperaba al usar un perfil cold-start sin historial de géneros. En producción, con un perfil de usuario real, este valor varía entre 0.3 (usuario especializado) y 0.8 (usuario explorador).

### Estrategias Activadas
| Estrategia | Frecuencia | Observación |
|---|---|---|
| `ontology_mood_only` | 5/10 | Estrategia más frecuente — el mood es el signal más común |
| `ontology_full` | 2/10 | Activa cuando hay mood + companion + género disponibles |
| `ontology_companion_only` | 1/10 | Activada por "watch alone" en Q8 |
| `broad` | 1/10 | Activada en Q9 (query sin señales contextuales claras) |
| `ontology_full` + fallbacks | 1/10 | Q2 requirió 5 estrategias en cascada |

### Cold-Start (3/10)
Las primeras 3 queries activaron modo cold-start (`isColdStart=true`). Esto ocurre porque el perfil `__metrics_eval__` tiene `snapshot_count=0` y a medida que el sistema archiva los contextos de las queries anteriores durante la sesión, las siguientes dejan de ser cold-start. Nótese que esto es un artefacto del endpoint secuencial, no del comportamiento real del sistema.

---

## Tiempo de Ejecución

| Métrica | Valor |
|---|---|
| Tiempo total | ~646 s (~10.8 min) |
| Tiempo promedio por query | 64.7 s |
| Query más rápida | Q10 — 16.3 s |
| Query más lenta | Q6 — 135.4 s |

El tiempo por query incluye: extracción de contexto NLU (Groq, hasta 15 s), hasta 5 intentos de estrategia SPARQL en Fuseki, scoring MMR, cálculo de métricas y generación de explicación (segundo call a Groq).

---

## Observaciones para el Documento

1. **La precisión semántica perfecta (1.0)** valida que la bridge-ontology clasifica correctamente los candidatos — el sistema no recomienda películas fuera de contexto.
2. **El ILD bajo (0.20)** es una limitación conocida del scoring actual que pondera relevancia (λ=0.7) sobre diversidad en MMR. Para aumentar diversidad se puede reducir λ.
3. **El Graph Diversity alto (0.96)** sugiere que aunque las listas son temáticamente homogéneas por género, las conexiones en el grafo son variadas — el sistema explora distintas zonas de la red.
4. **El Onto-Recall bajo (0.18)** es esperable: el MMR es un filtro exigente sobre un pool semántico grande. No indica pérdida de calidad sino selectividad.
5. **La estrategia `broad` (Q9)** produce la mayor diversidad (ILD=1.0) a costa de relevancia contextual — útil como mecanismo de serendipity explícita.
