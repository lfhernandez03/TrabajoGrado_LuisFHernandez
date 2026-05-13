# 6. Diseño de Ontologías

El presente capítulo aborda la materialización del Objetivo Específico 2, centrado en el diseño de una ontología para el dominio cinematográfico utilizando estándares semánticos. Para superar las limitaciones de contextualización y adaptabilidad inherentes a los sistemas de recomendación tradicionales, se requiere una representación del conocimiento explícita, formal y robusta, alcanzada mediante la aplicación de principios de la Web Semántica.

El modelado de un dominio tan complejo como el cinematográfico, acoplado a la dinámica del contexto del usuario, exige una arquitectura que garantice claridad conceptual, extensibilidad y sostenibilidad. Por esta razón, se adoptó una arquitectura de ontologías modulares: una estrategia reconocida en la ingeniería ontológica para la gestión de dominios de conocimiento heterogéneos que evita el acoplamiento conceptual monolítico y facilita la reutilización e integración con la iniciativa de Linked Open Data (LOD).

---

## 6.1. Justificación del Diseño Modular de Ontologías

Este proyecto adopta una arquitectura modular compuesta por tres ontologías interconectadas (Figura 3): `movie-ontology.owl` (dominio cinematográfico), `context-ontology.owl` (contexto del usuario) y `recommendation-bridge.owl` (alineamiento y reglas de recomendación). Esta decisión se fundamenta en principios establecidos de ingeniería ontológica y responde a necesidades específicas del sistema.

### 6.1.1. Fundamentación Teórica

Los principios de diseño ontológico de Gruber (1995) establecen que una ontología bien construida debe satisfacer cinco criterios: claridad, coherencia, extensibilidad, mínimo sesgo de codificación y mínimo compromiso ontológico [21]. La modularización contribuye directamente al cumplimiento de estos principios, particularmente en lo referente a la extensibilidad y la claridad conceptual.

Noy & McGuinness (2001), en su metodología *Ontology Development 101*, destacan la importancia de reutilizar vocabularios existentes y separar conceptos en módulos independientes cuando pertenecen a dominios diferenciados [36]. En este trabajo, el dominio cinematográfico y el dominio contextual representan áreas conceptualmente distintas que se benefician de una separación arquitectónica.

### 6.1.2. Ventajas Técnicas y Estratégicas

La modularización ofrece cuatro beneficios concretos para el sistema:

- **Portabilidad y reutilización del conocimiento**: `context-ontology.owl` puede reutilizarse en otros sistemas de recomendación sin modificación, incrementando el valor de la investigación.
- **Facilidad de integración con Linked Open Data**: `movie-ontology.owl` puede extender libremente `Schema.org/Movie` y la DBpedia Ontology, mientras que `context-ontology.owl` puede importar vocabularios especializados como GUMO o FOAF.
- **Mantenimiento y evolución independiente**: Cambios en el modelado cinematográfico no afectan la ontología de contexto, reduciendo el riesgo de inconsistencias y facilitando el versionado independiente con herramientas como OOPS! y razonadores como HermiT o Pellet [30].
- **Alineamiento centralizado de la lógica**: `recommendation-bridge.owl` concentra las relaciones semánticas puente y las reglas SWRL de recomendación contextualizada, sin contaminar las ontologías de dominio con lógica de aplicación.

Frente a una solución monolítica —que implicaría acoplamiento conceptual, violación del principio de separación de responsabilidades, limitada reutilización y mayor complejidad para el motor de razonamiento— la modularización es arquitectónicamente superior.

---

## 6.2. Ontología de Dominio Cinematográfico

La ontología de dominio cinematográfico (`movie-ontology`) modela las entidades fundamentales del cine y sus interrelaciones. Fue diseñada siguiendo las fases de especificación y conceptualización de la metodología NeOn, tomando como referencia ontologías existentes como la *Movie Ontology* de DBpedia y Schema.org, pero adaptándola a las necesidades específicas del sistema de recomendación.

### 6.2.1. Espacio de Nombres y Prefijos

La ontología utiliza el espacio de nombres base `http://example.org/movie-ontology#` con el prefijo `mo:`.

| Prefijo | URI |
|---|---|
| `mo:` | `http://example.org/movie-ontology#` |
| `owl:` | `http://www.w3.org/2002/07/owl#` |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` |

*Tabla 4: Prefijos y espacios de nombres de la ontología de dominio*

### 6.2.2. Jerarquía de Clases

La ontología define las siguientes clases principales, organizadas en una jerarquía que refleja las entidades del dominio cinematográfico:

- **`mo:Movie`**: Clase central que representa una obra cinematográfica. Constituye el eje del grafo de conocimiento y concentra la mayor parte de las propiedades de datos y relaciones. Cuenta con cuatro subclases disjuntas: `FeatureFilm`, `Documentary`, `ShortFilm` y `AnimatedFilm`.
- **`mo:Person`**: Superclase abstracta que representa a cualquier individuo participante en la producción cinematográfica, con subclases `mo:Director` y `mo:Actor`, entre otras.
- **`mo:Genre`**: Representa las categorías temáticas de clasificación. Los géneros se modelan como *instancias* de esta clase —no como subclases— lo que permite la multi-clasificación natural de películas y la adición dinámica de nuevos géneros sin modificar la TBox.
- **`mo:ProductionCompany`**: Compañía productora involucrada en la financiación de la película.
- **`mo:Collection`**: Agrupa películas que pertenecen a una misma saga o franquicia (e.g., *Harry Potter*, *The Lord of the Rings*).

La Figura 4 presenta el diagrama completo de la ontología con sus clases, propiedades de objeto y propiedades de datos.

### 6.2.3. Propiedades de Objeto

Las propiedades de objeto (`owl:ObjectProperty`) definen las relaciones semánticas entre las clases. La Tabla 5 presenta las propiedades implementadas.

| Propiedad | Dominio | Rango | Inversa |
|---|---|---|---|
| `mo:hasGenre` | `mo:Movie` | `mo:Genre` | `mo:isGenreOf` |
| `mo:hasDirector` | `mo:Movie` | `mo:Director` | `mo:directedBy` |
| `mo:hasActor` | `mo:Movie` | `mo:Actor` | `mo:actedIn` |
| `mo:producedBy` | `mo:Movie` | `mo:ProductionCompany` | `mo:produced` |
| `mo:belongsToCollection` | `mo:Movie` | `mo:Collection` | `mo:hasMovie` |

*Tabla 5: Propiedades de objeto de la ontología de dominio cinematográfico*

La definición de propiedades inversas permite la navegación bidireccional del grafo: a partir de un director es posible recuperar todas sus películas mediante `mo:directedBy`, y a partir de una película se puede acceder a su director mediante `mo:hasDirector`. Esta bidireccionalidad es fundamental para el explorador de conexiones del sistema.

### 6.2.4. Propiedades de Datos

Las propiedades de datos (`owl:DatatypeProperty`) capturan los atributos escalares de cada entidad. La Tabla 6 resume las propiedades de la clase `mo:Movie`, que constituye la clase con mayor número de atributos.

| Propiedad | Rango | Descripción |
|---|---|---|
| `mo:title` | `xsd:string` | Título de la película en español |
| `mo:originalTitle` | `xsd:string` | Título en idioma original |
| `mo:releaseDate` | `xsd:date` | Fecha de estreno |
| `mo:releaseYear` | `xsd:gYear` | Año de estreno |
| `mo:runtime` | `xsd:integer` | Duración en minutos |
| `mo:budget` | `xsd:decimal` | Presupuesto de producción (USD) |
| `mo:revenue` | `xsd:decimal` | Recaudación en taquilla (USD) |
| `mo:voteAverage` | `xsd:float` | Puntuación promedio (0–10) |
| `mo:voteCount` | `xsd:integer` | Número de votos |
| `mo:popularity` | `xsd:float` | Índice de popularidad TMDb |
| `mo:overview` | `xsd:string` | Sinopsis en español |
| `mo:posterPath` | `xsd:anyURI` | URL del póster |
| `mo:originalLanguage` | `xsd:string` | Código ISO 639-1 del idioma |
| `mo:tmdbId` | `xsd:integer` | Identificador en TMDb |
| `mo:imdbId` | `xsd:string` | Identificador en IMDb |

*Tabla 6: Propiedades de datos de la clase `mo:Movie`*

Para las clases auxiliares, la Tabla 7 resume sus propiedades identificadoras.

| Clase | Propiedad | Rango | Descripción |
|---|---|---|---|
| `mo:Person` | `mo:name` | `xsd:string` | Nombre completo |
| `mo:Person` | `mo:personId` | `xsd:integer` | Identificador numérico |
| `mo:Genre` | `mo:genreName` | `xsd:string` | Nombre del género |
| `mo:Genre` | `mo:genreId` | `xsd:integer` | Identificador numérico |
| `mo:ProductionCompany` | `mo:companyName` | `xsd:string` | Nombre de la compañía |
| `mo:Collection` | `mo:collectionName` | `xsd:string` | Nombre de la saga |

*Tabla 7: Propiedades de datos de las clases auxiliares*

### 6.2.5. Decisiones de Diseño Relevantes

Durante la implementación surgieron cuatro decisiones de diseño que difieren o complementan el diseño teórico inicial:

1. **Géneros como instancias, no como subclases**: Los géneros cinematográficos se modelaron como individuos de la clase `mo:Genre` en lugar de subclases de `mo:Movie`. Esta decisión permite la multi-clasificación natural y facilita la adición dinámica de nuevos géneros sin modificar la TBox.
2. **Separación Actor/Director como subclases disjuntas de Person**: Cuando una misma persona cumple ambos roles, se crean dos individuos conectados con la película. Esta simplificación evita la complejidad de roles contextuales y facilita las consultas SPARQL.
3. **Identificadores externos (TMDb, IMDb)**: Se incluyeron propiedades para los identificadores externos (`mo:tmdbId`, `mo:imdbId`), habilitando la integración futura con Linked Open Data y servicios de terceros como APIs de streaming.
4. **Contenido bilingüe**: Los títulos y sinopsis se almacenan en español (obtenidos de la API de TMDb con el parámetro `language=es-ES`), mientras que el título original se preserva en `mo:originalTitle`, respondiendo al público objetivo hispanohablante.

---

## 6.3. Ontología de Contexto de Usuario

La ontología de contexto de usuario (`context-ontology`) modela las condiciones situacionales bajo las cuales un usuario solicita una recomendación. A diferencia de enfoques tradicionales que capturan únicamente preferencias explícitas (géneros favoritos, películas vistas), esta ontología formaliza el *contexto de visualización*: las circunstancias sociales, emocionales, temporales y ambientales que condicionan qué tipo de película resulta apropiada en un momento dado.

### 6.3.1. Dimensiones Contextuales

El modelo contextual se estructura en seis dimensiones independientes, cada una representada por una clase o conjunto de propiedades dentro de la ontología:

1. **Dimensión Social** (`co:CompanionType`): Captura con quién va a ver la película el usuario. Valores válidos: `co:family`, `co:couple`, `co:friends`, `co:alone`.
2. **Dimensión Emocional** (`co:EmotionalState`): Representa el estado emocional actual o el estado deseado tras la visualización. Valores: `co:happy`, `co:sad`, `co:anxious`, `co:nostalgic`, `co:excited`, `co:neutral`.
3. **Dimensión Energética** (`co:EnergyLevel`): Indica el nivel de estimulación deseado. Valores: `co:relaxed`, `co:moderate`, `co:energetic`. Esta dimensión se separó de la emocional durante la implementación al verificar que un usuario puede estar triste pero desear contenido energético.
4. **Dimensión Temporal** (`co:TemporalContext`): Captura el momento de la solicitud dividido en dos propiedades independientes: `co:timeOfDay` (morning, afternoon, evening, night) y `co:dayOfWeek` (monday a sunday), lo que permite reglas de inferencia más granulares.
5. **Dimensión de Requisitos** (`co:ContentRequirements`): Restricciones explícitas sobre el contenido: duración máxima (`co:maxDuration`), idioma preferido (`co:languagePreference`) y aptitud para menores (`co:ageAppropriate`). Esta dimensión no estaba contemplada en el diseño inicial; surgió durante las pruebas cuando se identificó que restricciones como la duración máxima son cruciales para la satisfacción del usuario.
6. **Dimensión de Preferencias** (`co:UserPreferences`): Preferencias temáticas expresadas directa o indirectamente: géneros deseados (`co:preferredGenres`), géneros a evitar (`co:excludedGenres`) y época preferida (`co:preferredEra`).

Las cinco clases principales están declaradas como `owl:AllDisjointClasses` y todas las relaciones tienen `owl:inverseOf`, garantizando la consistencia del grafo de contexto. La Figura 5 presenta el diagrama completo de la ontología.

### 6.3.2. Vocabulario Controlado

Una decisión de diseño fundamental fue la adopción de vocabularios controlados (enumeraciones cerradas) para las dimensiones cualitativas del contexto. La Tabla 8 resume los valores válidos por dimensión.

| Dimensión | Valores permitidos |
|---|---|
| Compañía | `family`, `couple`, `friends`, `alone` |
| Estado emocional | `happy`, `sad`, `anxious`, `nostalgic`, `excited`, `neutral` |
| Nivel de energía | `relaxed`, `moderate`, `energetic` |
| Momento del día | `morning`, `afternoon`, `evening`, `night` |
| Día de la semana | `monday` a `sunday` |

*Tabla 8: Vocabulario controlado de la ontología de contexto*

El uso de vocabularios controlados, en lugar de texto libre, ofrece tres beneficios concretos: (1) **Consistencia en el LLM**, ya que el modelo recibe instrucciones explícitas de mapear la entrada del usuario a estos valores, eliminando ambigüedades (e.g., "estoy con mis hijos" → `co:family`); (2) **Eficiencia en SPARQL**, al usar comparaciones exactas de strings en lugar de operaciones de similitud textual; (3) **Extensibilidad controlada**, donde nuevos valores se añaden actualizando únicamente las instrucciones del prompt del LLM y las instancias en el triplestore.

---

## 6.4. Ontología de Interconexión

La ontología de interconexión (`bridge-ontology`) constituye el componente arquitectónico que habilita la comunicación semántica entre la ontología de dominio cinematográfico y la ontología de contexto de usuario. Su función es establecer los mapeos formales que permiten al motor de recomendación generar consultas SPARQL que involucren simultáneamente entidades de ambos dominios.

La ontología utiliza el espacio de nombres `http://example.org/bridge-ontology#` con el prefijo `bo:` e importa explícitamente las dos ontologías anteriores mediante declaraciones `owl:imports`.

### 6.4.1. Propiedades de Alineación

Las propiedades de la ontología de interconexión se clasifican en dos categorías:

**Propiedades de alineación directa**: Conectan entidades del dominio cinematográfico con condiciones contextuales específicas.

| Propiedad | Dominio | Rango |
|---|---|---|
| `bo:suitableForCompanion` | `mo:Movie` | `co:CompanionType` |
| `bo:suitableForMood` | `mo:Movie` | `co:EmotionalState` |
| `bo:suitableForEnergy` | `mo:Movie` | `co:EnergyLevel` |
| `bo:suitableForTimeOfDay` | `mo:Movie` | `co:TemporalContext` |

*Tabla 9: Propiedades de alineación directa de la ontología de interconexión*

**Propiedades de inferencia contextual**: Permiten derivar relaciones entre contexto y contenido a través del grafo.

| Propiedad | Dominio | Rango | Semántica |
|---|---|---|---|
| `bo:moodToGenre` | `co:EmotionalState` | `mo:Genre` | Mapea un estado emocional a géneros apropiados |
| `bo:companionToGenre` | `co:CompanionType` | `mo:Genre` | Mapea un tipo de compañía a géneros adecuados |
| `bo:energyToGenre` | `co:EnergyLevel` | `mo:Genre` | Mapea un nivel de energía a géneros correspondientes |

*Tabla 10: Propiedades de inferencia contextual*

### 6.4.2. Reglas de Mapeo Contexto-Género

El mecanismo central de la ontología de interconexión es el conjunto de reglas que asocian condiciones contextuales con géneros cinematográficos apropiados. Estas reglas se implementaron como instancias de las propiedades de inferencia, formando un grafo de conocimiento que el motor de recomendación consulta dinámicamente.

La Tabla 11 presenta los mapeos representativos entre estado emocional y géneros, mientras que la Tabla 12 detalla las restricciones de género según el contexto social.

| Estado Emocional | Géneros Asociados |
|---|---|
| `co:happy` | Comedia, Aventura, Animación, Musical |
| `co:sad` | Drama, Romance, Animación (reconfortante) |
| `co:anxious` | Comedia (ligera), Animación, Familia |
| `co:nostalgic` | Drama, Romance, Clásicos |
| `co:excited` | Acción, Ciencia Ficción, Aventura, Thriller |
| `co:neutral` | Sin restricción de género |

*Tabla 11: Mapeos representativos entre estado emocional y géneros*

| Tipo de Compañía | Restricciones de Género |
|---|---|
| `co:family` | Animación, Familia, Aventura, Comedia. Se excluyen Terror, Thriller violento y contenido adulto |
| `co:couple` | Romance, Drama, Comedia Romántica, Thriller (ligero) |
| `co:friends` | Acción, Comedia, Ciencia Ficción, Terror |
| `co:alone` | Sin restricción significativa; favorece Drama, Thriller, Ciencia Ficción, Documentales |

*Tabla 12: Mapeos representativos entre tipo de compañía y géneros*

El listado completo de instancias de mapeo (53 individuos predefinidos en el ABox) se documenta en el **Anexo A**.

---

## 6.5. Formalización Ontológica: Axiomas y Restricciones

Más allá de la taxonomía de clases y la definición de propiedades, OWL 2 permite formalizar restricciones lógicas que garantizan la consistencia del conocimiento representado. Esta sección presenta las garantías formales del sistema ontológico, describiendo los tipos de restricciones implementadas y su impacto funcional. El inventario exhaustivo de cada restricción se encuentra en el **Anexo B**.

### 6.5.1. Fundamentos: TBox vs. ABox

En lógica descriptiva, el conocimiento ontológico se divide en dos niveles:

- **TBox (Terminological Box)**: Define la estructura conceptual: clases, jerarquías, propiedades, restricciones y axiomas. Es el *esquema* del conocimiento. Ejemplo: *"Toda película tiene exactamente un título"*.
- **ABox (Assertional Box)**: Contiene las instancias concretas y sus relaciones. Es la *población* del conocimiento. Ejemplo: *"Cinema Paradiso es una película con título 'Cinema Paradiso'"*.

Las restricciones documentadas en esta sección pertenecen exclusivamente a la TBox y son verificables mediante razonadores OWL como HermiT o Pellet.

### 6.5.2. Tipos de Restricciones Implementadas

El sistema ontológico implementa cinco categorías principales de restricciones OWL 2:

**Disyunción de clases** (`owl:AllDisjointClasses`, `owl:disjointWith`): Garantiza que ningún individuo pueda pertenecer simultáneamente a dos clases incompatibles. Por ejemplo, una instancia de `mo:Genre` no puede ser clasificada como `mo:Movie`. La ontología de dominio implementa 4 axiomas globales de disyunción y 32 pares explícitos, cubriendo subtipos de película, subtipos de tono narrativo, clasificaciones por edad y períodos históricos.

**Restricciones de cardinalidad**: Definen cuántas veces una propiedad puede o debe asociarse a un individuo. Se implementaron tres variantes: cardinalidad exacta (`owl:cardinality`), mínima (`owl:minCardinality`) y máxima (`owl:maxCardinality`). Un ejemplo representativo en notación Turtle:

```turtle
# Toda película tiene exactamente un título
:Movie rdfs:subClassOf [
  rdf:type owl:Restriction ;
  owl:onProperty :hasTitle ;
  owl:cardinality "1"^^xsd:nonNegativeInteger ] .

# Toda película tiene al menos un género principal
:Movie rdfs:subClassOf [
  rdf:type owl:Restriction ;
  owl:onProperty :hasMainGenre ;
  owl:minCardinality "1"^^xsd:nonNegativeInteger ] .
```

**Propiedades funcionales** (`owl:FunctionalProperty`): Establecen que un individuo puede tener **como máximo un valor** para esa propiedad. Son especialmente importantes para los identificadores externos (`hasIMDbID`, `hasTMDbID`), garantizando que no existan valores duplicados. El razonador, al encontrar dos valores distintos para una propiedad funcional, infiere que son el mismo individuo (`owl:sameAs`) o detecta una inconsistencia.

**Restricciones de rango de valores** (`owl:allValuesFrom`, `owl:someValuesFrom`): Restringen el tipo de individuos que pueden relacionarse con una clase. Por ejemplo, `bo:suitableForCompanion` solo puede apuntar a instancias de `co:CompanionType`, lo que garantiza la coherencia de los mapeos contextuales.

**Propiedades inversas y simétricas**: Las propiedades inversas (e.g., `mo:hasDirector` / `mo:directedBy`) permiten la navegación bidireccional del grafo. Las propiedades simétricas garantizan que si A se relaciona con B, entonces B se relaciona con A, lo que es fundamental para el explorador de conexiones.

### 6.5.3. Resumen Cuantitativo del Sistema Ontológico

La Tabla 13 consolida el inventario de axiomas TBox por ontología, permitiendo comparar la riqueza formal de cada componente.

| Categoría de Axioma | movie-ontology | context-ontology | bridge-ontology | **Total** |
|---|---|---|---|---|
| Axiomas de disyunción | 36 | 8 | 4 | **48** |
| Restricciones de cardinalidad | 18 | 15 | 12 | **45** |
| Propiedades funcionales | 24 | 7 | 6 | **37** |
| Restricciones de rango de valores | 20 | 5 | 8 | **33** |
| Pares de propiedades inversas | 8 | 4 | 6 | **18** |
| Propiedades simétricas | 2 | 0 | 1 | **3** |
| Reglas SWRL | 0 | 0 | 3 | **3** |
| **Total axiomas TBox** | **108** | **39** | **40** | **187** |

*Tabla 13: Resumen cuantitativo de axiomas TBox por ontología*

La ontología de dominio concentra la mayor densidad formal (108 axiomas), lo cual es consistente con su rol de modelar el dominio más complejo. La ontología de interconexión, a pesar de su menor tamaño en clases, alcanza una densidad alta debido a las restricciones cross-ontología que garantizan la coherencia de los mapeos contexto-contenido.

### 6.5.4. Impacto de las Restricciones en el Sistema

Las restricciones ontológicas no son meramente documentales: actúan como mecanismo de validación activo en tres fases críticas del sistema (ver Figura 7):

1. **Fase de poblamiento de datos**: El pipeline ETL (Python + rdflib) verifica que cada tripleta generada cumple con las restricciones de cardinalidad y rango antes de insertarla en el triplestore. Cualquier película sin título o sin al menos un género es rechazada.

2. **Fase de extracción de contexto por el LLM**: El prompt del LLM incluye el vocabulario controlado de la ontología de contexto, forzando que los valores extraídos de la consulta del usuario correspondan exactamente a individuos del ABox. Esto elimina la ambigüedad semántica antes de que el contexto llegue a la consulta SPARQL.

3. **Fase de ejecución de consultas SPARQL**: Los FILTERs en las consultas generadas por el LLM explotan las restricciones de vocabulario para hacer comparaciones exactas de strings, en lugar de similitud aproximada, lo que mejora la precisión y el tiempo de ejecución de las consultas.

---

## 6.6. Mecanismo de Integración: Alineación Semántica Dinámica

La integración operativa de las tres ontologías en el sistema de recomendación se realiza mediante un mecanismo de alineación semántica dinámica. En lugar de combinar las ontologías en un único artefacto OWL, el sistema las mantiene como grafos nombrados (*named graphs*) independientes dentro del triplestore Apache Jena Fuseki, consultables de forma conjunta mediante SPARQL 1.1.

### 6.6.1. Estrategia de Carga en el Triplestore

Cada ontología ocupa un grafo nombrado dedicado en Fuseki:

| Grafo nombrado | Contenido | Tamaño aproximado |
|---|---|---|
| `/movie-ontology` | TBox + ABox de películas (`movies_data.ttl`) | 159,568 líneas RDF |
| `/context-ontology` | TBox + ABox de contextos (`contexts_data.ttl`) | ~200 tripletas |
| `/bridge-ontology` | TBox + ABox de scores y mapeos (`bridge_data.ttl`) | 18,920 líneas RDF |

Esta separación física permite: actualizar el grafo de películas sin afectar el grafo de contexto, aplicar permisos de acceso por grafo, y ejecutar consultas sobre subconjuntos del triplestore para optimizar el rendimiento.

---

## 6.7. Mecanismo de Consulta Multi-Ontología (Cross-Ontology)

La capacidad de consultar simultáneamente las tres ontologías desde una sola consulta SPARQL es el mecanismo que materializa la recomendación contextualizada. Esto se logra mediante consultas `SELECT` que combinan patrones de triples provenientes de los tres grafos nombrados, navegando las propiedades de alineación definidas en `bridge-ontology`.

El ejemplo siguiente ilustra una consulta cross-ontología representativa para el escenario "familia con niños, estado feliz, máximo 90 minutos":

```sparql
PREFIX mo: <http://example.org/movie-ontology#>
PREFIX co: <http://example.org/context-ontology#>
PREFIX bo: <http://example.org/bridge-ontology#>
PREFIX genre: <http://example.org/data/genre/>

SELECT DISTINCT ?title ?runtime ?genreName ?averageRating WHERE {
  # Patrón de dominio cinematográfico
  { ?m a mo:FeatureFilm } UNION { ?m a mo:AnimatedFilm }
  ?m mo:hasTitle ?title ;
     mo:runtime ?runtime ;
     mo:hasMainGenre ?g .
  ?g mo:genreName ?genreName .
  OPTIONAL { ?m mo:hasAverageRating ?averageRating }

  # Patrón de interconexión (bridge)
  ?companionMapping bo:companionToGenre ?g ;
                    co:companionType "family" .
  ?moodMapping bo:moodToGenre ?g ;
               co:emotionalState "happy" .

  # Restricciones de requisitos
  FILTER(?runtime <= 90)
  FILTER(!CONTAINS(?genreName, "Horror") &&
         !CONTAINS(?genreName, "Thriller"))
}
ORDER BY DESC(?averageRating)
LIMIT 20
```

Esta consulta demuestra tres propiedades arquitectónicas clave del sistema:

- **Multi-hop semántico**: La consulta navega de `mo:Movie` → `mo:Genre` → `bo:CompanionType` → `co:CompanionType`, cruzando tres ontologías en una sola ejecución.
- **Restricciones contextuales nativas**: Los filtros de compañía y estado emocional son ciudadanos de primera clase de la consulta, no post-procesamiento.
- **Vocabulario controlado como clave de unión**: Los valores de string `"family"` y `"happy"` son exactamente los individuos del vocabulario controlado, garantizando que la consulta del LLM sea siempre válida frente al grafo.

El resultado de la consulta (hasta 20 películas candidatas) es el insumo para las fases 4 y 5 del pipeline de recomendación: cálculo de *compatibility scores* por LLM y generación de respuesta narrativa contextualizada.

---

> **Nota**: Las tablas detalladas de axiomas, restricciones de cardinalidad, propiedades funcionales, restricciones de rango, pares de propiedades inversas e instancias de mapeo completas se encuentran en el **Anexo B: Inventario Exhaustivo de Axiomas Ontológicos**.
