# Vocabulario Controlado - Referencia Rápida para LLM

## 📋 Valores Normalizados Obligatorios

Este documento define los valores EXACTOS que el LLM debe usar al extraer contextos del lenguaje natural.

---

## 1. Nivel de Energía Deseado (`desiredEnergyLevel`)

**Campo:** `EmotionalContext.desiredEnergyLevel`  
**Tipo:** `xsd:string`  
**Valores permitidos:** 3 opciones

| Valor | Significado | Ejemplos de uso |
|-------|-------------|-----------------|
| `"bajo"` | Contenido tranquilo, relajante, contemplativo | "algo relajante", "quiero desconectar", "necesito calma" |
| `"medio"` | Contenido moderado, equilibrado | "algo ligero pero entretenido", "equilibrado" |
| `"alto"` | Contenido intenso, dinámico, emocionante | "algo épico", "emocionante", "lleno de acción" |

**Importante:** No usar variantes como "muy bajo", "un poco alto", "bastante medio", etc.

---

## 2. Tipo de Compañía (`companionType`)

**Campo:** `SocialContext.companionType`  
**Tipo:** `xsd:string`  
**Valores permitidos:**

| Valor | Uso | Ejemplos del usuario |
|-------|-----|---------------------|
| `"solo"` | Viendo solo | "estoy solo", "voy a ver solo" |
| `"pareja"` | Con pareja romántica | "con mi pareja", "date night" |
| `"familia"` | Con familia (sin niños pequeños) | "con mi familia", "reunión familiar" |
| `"familia con niños"` | Con niños presentes ⚠️ CRÍTICO | "con los niños", "con mis hijos", "mis pequeños" |
| `"amigos"` | Con amigos | "con amigos", "mis amigos vienen" |
| `"compañeros de trabajo"` | Con colegas | "con compañeros del trabajo", "team building" |
| `"grupo grande"` | Grupo de 7+ personas | "somos muchos", "fiesta", "grupo grande" |

**⚠️ Importante:** `"familia con niños"` activa filtros de contenido infantil. Usar SIEMPRE que haya menores presentes.

---

## 3. Estados de Ánimo (`moodDescription`)

**Campo:** `EmotionalContext.moodDescription`  
**Tipo:** `xsd:string`  
**Valores preferidos (puede ser flexible pero usar estos como base):**

### Positivos
- `"feliz"` - alegría, satisfacción
- `"alegre"` - energía positiva, entusiasmo
- `"relajado"` - tranquilo, en paz
- `"romántico"` - amor, ternura
- `"aventurero"` - búsqueda de emociones
- `"curioso"` - interés, ganas de aprender

### Negativos
- `"estresado"` - presión, ansiedad
- `"triste"` - melancolía, bajón emocional
- `"aburrido"` - falta de estímulo
- `"nostálgico"` - añoranza del pasado

### Neutros/Complejos
- `"reflexivo"` - contemplativo, pensativo
- `"social"` - ganas de compartir, conectar
- `"contemplativo"` - introspectivo

**Nota:** Si el usuario usa sinónimos, mapear al valor estándar más cercano.

---

## 4. Días de la Semana (`dayOfWeek`)

**Campo:** `ContextSnapshot.dayOfWeek`  
**Tipo:** `xsd:string`  
**Formato ESTRICTO:** Primera letra mayúscula, resto minúsculas CON tildes

| Valor CORRECTO | ❌ INCORRECTO |
|----------------|---------------|
| `"Lunes"` | lunes, LUNES, Lúnes |
| `"Martes"` | martes, MARTES |
| `"Miércoles"` | miercoles, Miercoles, MIÉRCOLES |
| `"Jueves"` | jueves, JUEVES |
| `"Viernes"` | viernes, VIERNES |
| `"Sábado"` | sabado, Sabado, SÁBADO |
| `"Domingo"` | domingo, DOMINGO |

---

## 5. Hora del Día (`hourOfDay`)

**Campo:** `ContextSnapshot.hourOfDay`  
**Tipo:** `xsd:integer`  
**Rango válido:** 0-23 (formato 24 horas)

| Rango | Interpretación |
|-------|----------------|
| 0-5 | Madrugada |
| 6-11 | Mañana |
| 12-17 | Tarde |
| 18-21 | Noche temprana |
| 22-23 | Noche tardía |

**Ejemplos:**
- "por la mañana" → `8` (hora típica)
- "al mediodía" → `12`
- "por la tarde" → `15`
- "por la noche" → `21`
- "de madrugada" → `3`

---

## 📝 Ejemplos de Mapeo Completo

### Ejemplo 1: Usuario relajado, solo
```
Usuario: "Estoy relajado, quiero ver algo tranquilo, estoy solo"

LLM extrae:
- moodDescription: "relajado"
- desiredEnergyLevel: "bajo"
- companionType: "solo"
- hasChildren: false
```

### Ejemplo 2: Familia con niños el sábado
```
Usuario: "El sábado vamos a ver algo con los niños a las 6 de la tarde"

LLM extrae:
- dayOfWeek: "Sábado"
- hourOfDay: 18
- companionType: "familia con niños"
- hasChildren: true
- groupSize: 4 (si se menciona)
- contentRestrictions: "apto para niños"
- excludedGenre: "terror, horror"
```

### Ejemplo 3: Amigos el viernes, energía alta
```
Usuario: "Somos 6 amigos el viernes por la noche, queremos algo emocionante"

LLM extrae:
- dayOfWeek: "Viernes"
- hourOfDay: 21
- companionType: "amigos"
- groupSize: 6
- desiredEnergyLevel: "alto"
- emotionalNeed: "entretenimiento compartido"
```

### Ejemplo 4: Estresado pero quiere acción
```
Usuario: "Estoy muy estresado pero quiero algo épico que me saque de esto"

LLM extrae:
- moodDescription: "estresado"
- desiredEnergyLevel: "alto" (paradoja emocional)
- emotionalNeed: "escapar del estrés"
```

---

## ✅ Validación

El sistema incluye métodos de validación:
```python
# En Python
RDFContextGenerator.validate_energy_level("bajo")      # ✓ OK
RDFContextGenerator.validate_energy_level("muy bajo")  # ✗ Error

RDFContextGenerator.validate_companion_type("amigos")  # ✓ OK
RDFContextGenerator.validate_companion_type("Amigos")  # ✗ Error

RDFContextGenerator.validate_day_of_week("Sábado")     # ✓ OK
RDFContextGenerator.validate_day_of_week("sabado")     # ✗ Error
```

---

## 🎯 Beneficios

1. **Matching exacto en SPARQL** - Las consultas encuentran resultados de forma predecible
2. **Sin ambigüedad** - El LLM sabe exactamente qué valores producir
3. **Debugging simple** - Errores fáciles de identificar
4. **Integración confiable** - GraphRAG funciona consistentemente
5. **Mejor UX** - Recomendaciones más precisas

---

## 📚 Referencias

- Ontología: `context-ontology-v3.ttl`
- Generador: `rdf_context_generator.py`
- Pruebas: `test_context_queries.py`
- Demo: `demo_normalized_values.py`

---

**Versión:** 1.0  
**Fecha:** Enero 11, 2026  
**Autor:** Luis Fernando Hernández Solís
