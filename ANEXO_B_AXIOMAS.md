# Anexo B: Inventario Exhaustivo de Axiomas Ontológicos

Este anexo documenta el conjunto completo de restricciones lógicas implementadas en las tres ontologías del sistema. Su propósito es proporcionar una referencia técnica exhaustiva para la verificación y reproducibilidad del diseño ontológico, sin interrumpir el flujo narrativo del Capítulo 6.

Todas las restricciones documentadas aquí son axiomas TBox verificables mediante razonadores OWL como HermiT o Pellet.

---

## B.1. Restricciones de la Ontología de Dominio Cinematográfico

### B.1.1. Axiomas de Disyunción

Las clases principales de la ontología son mutuamente disjuntas, lo que significa que ningún individuo puede pertenecer simultáneamente a dos de ellas. La ontología implementa dos mecanismos complementarios: axiomas globales mediante `owl:AllDisjointClasses` y pares explícitos mediante `owl:disjointWith`.

| Mecanismo | Clases mutuamente excluyentes |
|---|---|
| *AllDisjointClasses — nivel superior (1 declaración)* | |
| Top-level | Movie, Person, Attribute, Role, ProductionCompany, Certification, Award, AwardParticipation, MovieCluster |
| *AllDisjointClasses — subjerarquías (3 declaraciones)* | |
| Subclases de Person | Director, Actor, Producer, Screenwriter, Cinematographer, Composer, Editor |
| Subclases de Rating | CriticRating, UserRating, AggregateRating |
| Subclases de NarrativeElement | Theme, Tone, PlotStructure |
| *disjointWith — pares explícitos (32 pares)* | |
| Tipos de Movie (6 pares) | FeatureFilm ⊥ Documentary ⊥ ShortFilm ⊥ AnimatedFilm |
| Tipos de Award (1 par) | FilmAward ⊥ PersonAward |
| Subtipos de Tone (10 pares) | DramaticTone ⊥ ComedyTone ⊥ SuspensefulTone ⊥ RomanticTone ⊥ DarkTone |
| Tipos de Role (1 par) | ActingRole ⊥ CreativeRole |
| Tipos de Genre (1 par) | MainGenre ⊥ Subgenre |
| Períodos históricos (3 pares) | Contemporary ⊥ Historical ⊥ Futuristic |
| Clasificación por edad (10 pares) | GeneralAudience ⊥ ParentalGuidance ⊥ Teen ⊥ Mature ⊥ AdultOnly |

*Cuadro B.1: Axiomas de disyunción de la ontología de dominio cinematográfico*

Formalización Turtle del axioma AllDisjointClasses de nivel superior:

```turtle
[] rdf:type owl:AllDisjointClasses ;
   owl:members ( :Movie :Person :Attribute :Role
   :ProductionCompany :Certification :Award
   :AwardParticipation :MovieCluster ) .
```

*Nota de diseño*: Las subclases de Person (Director, Actor, Producer, etc.) son declaradas como disjuntas entre sí. Cuando una persona cumple múltiples roles (e.g., Clint Eastwood como actor y director), se crean dos individuos conectados por sus respectivas relaciones con la película. Esta simplificación aborda mediante el patrón n-ario Role: una persona se asocia a una película a través de instancias separadas de ActingRole o CreativeRole, sin necesidad de que el individuo pertenezca a múltiples subclases de Person.

---

### B.1.2. Restricciones de Cardinalidad

Las restricciones de cardinalidad definen cuántas veces una propiedad puede o debe asociarse a un individuo, organizadas por clase y tipo de cardinalidad.

| Clase | Propiedad | Card. | Significado |
|---|---|---|---|
| *Cardinalidad exacta (owl:cardinality) — 9 restricciones* | | | |
| Movie | hasTitle | = 1 | Toda película tiene exactamente un título |
| Movie | releaseDate | = 1 | Toda película tiene exactamente una fecha de estreno |
| Person | hasName | = 1 | Toda persona tiene exactamente un nombre |
| Genre | genreName | = 1 | Todo género tiene exactamente un nombre |
| ProductionCompany | companyName | = 1 | Toda compañía tiene exactamente un nombre |
| MovieCluster | clusterID | = 1 | Todo cluster tiene exactamente un identificador |
| AwardParticipation | hasAward | = 1 | Cada participación refiere exactamente un premio |
| AwardParticipation | forEntity | = 1 | Cada participación refiere exactamente una entidad |
| AwardParticipation | awardYear | = 1 | Cada participación tiene exactamente un año |
| *Cardinalidad mínima (owl:minCardinality) — 7 restricciones* | | | |
| Movie | hasDirector | ≥ 1 | Toda película tiene al menos un director |
| Movie | hasMainGenre | ≥ 1 | Toda película tiene al menos un género principal |
| Director | isDirectorOf | ≥ 1 | Todo director ha dirigido al menos una película |
| Actor | isActorIn | ≥ 1 | Todo actor ha actuado en al menos una película |
| ProductionCompany | producedMovie | ≥ 1 | Toda compañía ha producido al menos una película |
| Genre | isGenreOf | ≥ 1 | Todo género está asociado a al menos una película |
| MovieCluster | containsMovie | ≥ 1 | Todo cluster contiene al menos una película |
| *Cardinalidad máxima (owl:maxCardinality) — 2 restricciones* | | | |
| Movie | runtime | ≤ 1 | Una película tiene como máximo una duración |
| Movie | hasPlotSummary | ≤ 1 | Una película tiene como máximo un resumen de trama |

*Cuadro B.2: Restricciones de cardinalidad de la ontología de dominio cinematográfico*

*Nota sobre AwardParticipation*: El diseño utiliza el **patrón n-ario** para modelar la relación entre entidades y premios. Una película o persona puede tener múltiples instancias de AwardParticipation, pero cada instancia tiene cardinalidad = 1 para sus propiedades. Por ejemplo, si Oppenheimer ganó tres premios Oscar, existirán tres instancias distintas de AwardParticipation.

---

### B.1.3. Propiedades Funcionales (24 propiedades)

Una propiedad funcional (`owl:FunctionalProperty`) establece que un individuo puede tener **como máximo un valor** para esa propiedad. Son equivalentes a restricciones de cardinalidad máxima de 1, pero declaradas a nivel de propiedad en lugar de a nivel de clase.

| Propiedad | Dominio | Significado |
|---|---|---|
| *Identificación y títulos (6)* | | |
| hasTitle | Movie | Un único título |
| hasOriginalTitle | Movie | Un único título original |
| hasIMDbID | Movie | Un único identificador IMDb |
| hasTMDbID | Movie | Un único identificador TMDb |
| hasName | Person | Un único nombre por persona |
| hasOriginalLanguage | Movie | Un único idioma original |
| *Temporales y técnicas (2)* | | |
| releaseDate | Movie | Una única fecha de estreno |
| runtime | Movie | Una única duración en minutos |
| *Métricas y calificaciones (9)* | | |
| hasPopularity | Movie | Un solo valor de popularidad TMDb |
| hasVoteCount | Movie | Un solo conteo general de votos |
| hasTMDbRating | Movie | Una sola calificación promedio TMDb |
| hasTMDbVoteCount | Movie | Un solo conteo de votos TMDb |
| hasIMDbRating | Movie | Una sola calificación promedio IMDb |
| hasIMDbVoteCount | Movie | Un solo conteo de votos IMDb |
| hasAverageRating | Movie | Una sola calificación promedio MovieLens |
| hasRatingCount | Movie | Un solo conteo de calificaciones MovieLens |
| hasMetascore | Movie | Un solo valor de Metascore |
| *Financieras (2)* | | |
| hasBudget | Movie | Un único presupuesto |
| hasBoxOffice | Movie | Una única recaudación en taquilla |
| *Atributos de entidades (2)* | | |
| genreName | Genre | Un único nombre por género |
| companyName | ProductionCompany | Un único nombre por compañía |
| *Cluster GraphRAG (3)* | | |
| clusterID | MovieCluster | Un único identificador de cluster |
| clusterLabel | MovieCluster | Una única etiqueta descriptiva |
| clusterSize | MovieCluster | Un único valor de tamaño |

*Cuadro B.3: Propiedades funcionales de la ontología de dominio (24 propiedades)*

---

### B.1.4. Restricciones de Rango de Valores (20 restricciones)

Estas restricciones especifican qué tipos de valores son válidos para las propiedades de datos, usando tipos XSD.

| Propiedad | Restricción de rango | Tipo XSD |
|---|---|---|
| hasTitle | `xsd:string` | String |
| releaseDate | `xsd:date` | Fecha ISO 8601 |
| releaseYear | `xsd:gYear` | Año (YYYY) |
| runtime | `xsd:integer` | Entero positivo |
| budget | `xsd:decimal` | Decimal |
| revenue | `xsd:decimal` | Decimal |
| voteAverage | `xsd:float` | Float [0.0, 10.0] |
| voteCount | `xsd:integer` | Entero no negativo |
| popularity | `xsd:float` | Float no negativo |
| hasIMDbRating | `xsd:float` | Float [0.0, 10.0] |
| hasTMDbRating | `xsd:float` | Float [0.0, 10.0] |
| hasAverageRating | `xsd:float` | Float [0.0, 5.0] |
| hasMetascore | `xsd:integer` | Entero [0, 100] |
| hasBudget | `xsd:decimal` | Decimal no negativo |
| hasBoxOffice | `xsd:decimal` | Decimal no negativo |
| overview | `xsd:string` | String |
| posterPath | `xsd:anyURI` | URI |
| originalLanguage | `xsd:string` | Código ISO 639-1 |
| tmdbId | `xsd:integer` | Entero positivo |
| imdbId | `xsd:string` | String (formato "tt\d+") |

*Cuadro B.4: Restricciones de rango de valores en propiedades de datos (20 restricciones)*

---

### B.1.5. Pares de Propiedades Inversas (8 pares)

| Propiedad | Inversa |
|---|---|
| `mo:hasGenre` | `mo:isGenreOf` |
| `mo:hasDirector` | `mo:directedBy` |
| `mo:hasActor` | `mo:actedIn` |
| `mo:producedBy` | `mo:produced` |
| `mo:belongsToCollection` | `mo:hasMovie` |
| `mo:hasAward` | `mo:awardedTo` |
| `mo:hasRole` | `mo:isRoleOf` |
| `mo:containsMovie` | `mo:belongsToCluster` |

*Cuadro B.5: Pares de propiedades inversas de la ontología de dominio (8 pares)*

---

### B.1.6. Propiedades Simétricas y Subpropiedades

| Propiedad | Tipo | Descripción |
|---|---|---|
| `mo:coStarredWith` | Simétrica | Si A actuó con B, entonces B actuó con A |
| `mo:coDirectedWith` | Simétrica | Si A codirigió con B, entonces B codirigió con A |
| `mo:hasMainGenre` | Subpropiedad de `mo:hasGenre` | El género principal es un tipo de género |

*Cuadro B.6: Propiedades simétricas y subpropiedades de la ontología de dominio*

---

### B.1.7. Equivalencias con Vocabularios Linked Open Data

| Clase/Propiedad (movie-ontology) | Equivalente externo |
|---|---|
| `mo:Movie` | `schema:Movie`, `dbo:Film` |
| `mo:Person` | `schema:Person`, `foaf:Person` |
| `mo:Director` | `schema:director`, `dbo:director` |
| `mo:Actor` | `schema:actor`, `dbo:starring` |
| `mo:Genre` | `schema:genre`, `dbo:genre` |
| `mo:hasTitle` | `schema:name`, `dbo:title` |
| `mo:releaseDate` | `schema:datePublished`, `dbo:releaseDate` |
| `mo:runtime` | `schema:duration`, `dbo:runtime` |

*Cuadro B.7: Equivalencias con vocabularios de Linked Open Data*

---

## B.2. Restricciones de la Ontología de Contexto de Usuario

### B.2.1. Axiomas de Disyunción

| Mecanismo | Clases mutuamente excluyentes |
|---|---|
| AllDisjointClasses (1 declaración) | ContextSnapshot, SocialContext, EmotionalContext, RequirementContext, TemporalContext, UserPreferences |
| disjointWith — CompanionType (6 pares) | family ⊥ couple ⊥ friends ⊥ alone |
| disjointWith — EmotionalState (15 pares) | happy ⊥ sad ⊥ anxious ⊥ nostalgic ⊥ excited ⊥ neutral |
| disjointWith — EnergyLevel (3 pares) | relaxed ⊥ moderate ⊥ energetic |

*Cuadro B.8: Axiomas de disyunción de la ontología de contexto de usuario*

### B.2.2. Enumeraciones Cerradas (owl:oneOf)

Las dimensiones cualitativas del contexto se formalizan como enumeraciones cerradas, lo que garantiza que solo los valores del vocabulario controlado sean válidos en el ABox.

| Clase | Individuos permitidos (owl:oneOf) |
|---|---|
| `co:CompanionType` | `co:family`, `co:couple`, `co:friends`, `co:alone` |
| `co:EmotionalState` | `co:happy`, `co:sad`, `co:anxious`, `co:nostalgic`, `co:excited`, `co:neutral` |
| `co:EnergyLevel` | `co:relaxed`, `co:moderate`, `co:energetic` |
| `co:TimeOfDay` | `co:morning`, `co:afternoon`, `co:evening`, `co:night` |
| `co:DayOfWeek` | `co:monday`, `co:tuesday`, `co:wednesday`, `co:thursday`, `co:friday`, `co:saturday`, `co:sunday` |

*Cuadro B.9: Enumeraciones cerradas de la ontología de contexto*

### B.2.3. Restricciones de Cardinalidad (15 restricciones)

| Clase | Propiedad | Card. | Significado |
|---|---|---|---|
| ContextSnapshot | snapshotID | = 1 | Cada snapshot tiene un ID único |
| ContextSnapshot | requestTimestamp | = 1 | Cada snapshot tiene un timestamp único |
| ContextSnapshot | hasSocialContext | = 1 | Exactamente un contexto social por snapshot |
| ContextSnapshot | hasEmotionalContext | = 1 | Exactamente un estado emocional por snapshot |
| ContextSnapshot | hasRequirementContext | ≤ 1 | Máximo un contexto de requisitos |
| ContextSnapshot | hasTemporalContext | = 1 | Exactamente un contexto temporal |
| SocialContext | companionType | = 1 | Un solo tipo de compañía por contexto social |
| SocialContext | groupSize | ≤ 1 | Máximo un valor de tamaño de grupo |
| EmotionalContext | emotionalState | = 1 | Un solo estado emocional por contexto |
| EmotionalContext | energyLevel | = 1 | Un solo nivel de energía por contexto |
| RequirementContext | maxDuration | ≤ 1 | Máximo una duración máxima |
| RequirementContext | languagePreference | ≤ 1 | Máximo un idioma preferido |
| RequirementContext | ageAppropriate | ≤ 1 | Máximo una restricción de edad |
| TemporalContext | timeOfDay | = 1 | Exactamente un momento del día |
| TemporalContext | dayOfWeek | = 1 | Exactamente un día de la semana |

*Cuadro B.10: Restricciones de cardinalidad de la ontología de contexto de usuario (15 restricciones)*

### B.2.4. Propiedades Funcionales de la Ontología de Contexto (7 propiedades)

| Propiedad | Dominio | Significado |
|---|---|---|
| `co:snapshotID` | ContextSnapshot | Un único ID por snapshot |
| `co:requestTimestamp` | ContextSnapshot | Un único timestamp |
| `co:userIntent` | ContextSnapshot | Una única intención de usuario |
| `co:companionType` | SocialContext | Un único tipo de compañía |
| `co:emotionalState` | EmotionalContext | Un único estado emocional |
| `co:energyLevel` | EmotionalContext | Un único nivel de energía |
| `co:maxDuration` | RequirementContext | Una única duración máxima |

*Cuadro B.11: Propiedades funcionales de la ontología de contexto (7 propiedades)*

### B.2.5. Restricciones de Dominio y Rango en Propiedades de Objeto

| Propiedad | Dominio | Rango |
|---|---|---|
| `co:hasSocialContext` | ContextSnapshot | SocialContext |
| `co:hasEmotionalContext` | ContextSnapshot | EmotionalContext |
| `co:hasRequirementContext` | ContextSnapshot | RequirementContext |
| `co:hasTemporalContext` | ContextSnapshot | TemporalContext |
| `co:hasCompanionType` | SocialContext | CompanionType |
| `co:hasEmotionalState` | EmotionalContext | EmotionalState |
| `co:hasEnergyLevel` | EmotionalContext | EnergyLevel |
| `co:hasTimeOfDay` | TemporalContext | TimeOfDay |
| `co:hasDayOfWeek` | TemporalContext | DayOfWeek |

*Cuadro B.12: Restricciones de dominio y rango en propiedades de objeto (ontología de contexto)*

### B.2.6. Restricciones allValuesFrom (5 restricciones)

| Clase | Propiedad | allValuesFrom |
|---|---|---|
| ContextSnapshot | hasSocialContext | SocialContext |
| ContextSnapshot | hasEmotionalContext | EmotionalContext |
| SocialContext | companionType | CompanionType |
| EmotionalContext | emotionalState | EmotionalState |
| EmotionalContext | energyLevel | EnergyLevel |

*Cuadro B.13: Restricciones allValuesFrom de la ontología de contexto (5 restricciones)*

### B.2.7. Propiedades de Datos con Tipos XSD

| Propiedad | Clase | Tipo XSD |
|---|---|---|
| `co:snapshotID` | ContextSnapshot | `xsd:string` |
| `co:requestTimestamp` | ContextSnapshot | `xsd:dateTime` |
| `co:userIntent` | ContextSnapshot | `xsd:string` |
| `co:hourOfDay` | ContextSnapshot | `xsd:integer` (0-23) |
| `co:dayOfWeek` | ContextSnapshot | `xsd:string` |
| `co:groupSize` | SocialContext | `xsd:integer` |
| `co:hasChildren` | SocialContext | `xsd:boolean` |
| `co:maxDuration` | RequirementContext | `xsd:integer` (minutos) |
| `co:languagePreference` | RequirementContext | `xsd:string` |
| `co:ageAppropriate` | RequirementContext | `xsd:boolean` |

*Cuadro B.14: Propiedades de datos de la ontología de contexto con tipos XSD*

---

## B.3. Restricciones de la Ontología de Interconexión

### B.3.1. Clases Definidas en la Bridge Ontology

| Clase | Superclase | Descripción |
|---|---|---|
| `bo:CompatibilityMapping` | `owl:Thing` | Mapeo de compatibilidad película-contexto |
| `bo:MoodGenreMapping` | `bo:CompatibilityMapping` | Mapeo estado emocional → género |
| `bo:CompanionGenreMapping` | `bo:CompatibilityMapping` | Mapeo compañía → género |
| `bo:EnergyGenreMapping` | `bo:CompatibilityMapping` | Mapeo nivel de energía → género |

*Cuadro B.15: Clases definidas en la ontología de interconexión*

### B.3.2. Restricciones de Dominio y Rango Cross-Ontology

| Propiedad | Dominio | Rango | Tipo |
|---|---|---|---|
| `bo:suitableForCompanion` | `mo:Movie` | `co:CompanionType` | ObjectProperty |
| `bo:suitableForMood` | `mo:Movie` | `co:EmotionalState` | ObjectProperty |
| `bo:suitableForEnergy` | `mo:Movie` | `co:EnergyLevel` | ObjectProperty |
| `bo:suitableForTimeOfDay` | `mo:Movie` | `co:TemporalContext` | ObjectProperty |
| `bo:moodToGenre` | `co:EmotionalState` | `mo:Genre` | ObjectProperty |
| `bo:companionToGenre` | `co:CompanionType` | `mo:Genre` | ObjectProperty |
| `bo:energyToGenre` | `co:EnergyLevel` | `mo:Genre` | ObjectProperty |
| `bo:isRecommendedIn` | `mo:Movie` | `co:ContextSnapshot` | ObjectProperty |
| `bo:compatibilityScore` | `mo:Movie` | `xsd:float` | DatatypeProperty |
| `bo:isKidFriendly` | `mo:Movie` | `xsd:boolean` | DatatypeProperty |

*Cuadro B.16: Restricciones de dominio y rango cross-ontology (bridge-ontology)*

### B.3.3. Restricciones de Cardinalidad de la Ontología de Interconexión

| Clase | Propiedad | Card. | Significado |
|---|---|---|---|
| CompatibilityMapping | moodToGenre | ≥ 1 | Todo mapeo de mood tiene al menos un género |
| CompatibilityMapping | companionToGenre | ≥ 1 | Todo mapeo de compañía tiene al menos un género |
| Movie | compatibilityScore | ≤ 1 | Máximo un score de compatibilidad por película |
| Movie | isKidFriendly | ≤ 1 | Máximo un valor de aptitud para menores |
| Movie | moodMatchScore | ≤ 1 | Máximo un score de alineación emocional |
| Movie | socialMatchScore | ≤ 1 | Máximo un score de adecuación social |
| Movie | energyMatchScore | ≤ 1 | Máximo un score de nivel de energía |
| Movie | temporalMatchScore | ≤ 1 | Máximo un score de relevancia temporal |

*Cuadro B.17: Restricciones de cardinalidad de la ontología de interconexión*

### B.3.4. Propiedades Funcionales de la Ontología de Interconexión (6 propiedades)

| Propiedad | Dominio | Significado |
|---|---|---|
| `bo:compatibilityScore` | Movie | Un único score general (0.0-1.0) |
| `bo:isKidFriendly` | Movie | Un único valor booleano |
| `bo:moodMatchScore` | Movie | Un único score de alineación emocional |
| `bo:socialMatchScore` | Movie | Un único score de adecuación social |
| `bo:energyMatchScore` | Movie | Un único score de energía |
| `bo:temporalMatchScore` | Movie | Un único score temporal |

*Cuadro B.18: Propiedades funcionales de la ontología de interconexión (6 propiedades)*

### B.3.5. Restricciones de Rango de Valores en la Bridge Ontology

| Propiedad | Tipo XSD | Rango válido |
|---|---|---|
| `bo:compatibilityScore` | `xsd:float` | [0.0, 1.0] |
| `bo:moodMatchScore` | `xsd:float` | [0.0, 1.0] |
| `bo:socialMatchScore` | `xsd:float` | [0.0, 1.0] |
| `bo:energyMatchScore` | `xsd:float` | [0.0, 1.0] |
| `bo:temporalMatchScore` | `xsd:float` | [0.0, 1.0] |
| `bo:requirementMatchScore` | `xsd:float` | [0.0, 1.0] |

*Cuadro B.19: Restricciones de rango de valores en la ontología de interconexión*

### B.3.6. Reglas SWRL Documentadas en la Bridge Ontology

Las reglas SWRL implementan lógica de inferencia que va más allá de las restricciones OWL 2 estándar. Se documentan tres reglas fundamentales:

| # | Regla | Descripción |
|---|---|---|
| SWRL-1 | `Movie(?m) ∧ runtime(?m, ?r) ∧ RequirementContext(?rc) ∧ maxDuration(?rc, ?d) ∧ swrlb:lessThanOrEqual(?r, ?d) → satisfiesRequirement(?m, ?rc)` | Si la duración de la película es ≤ al tiempo disponible del usuario, la película satisface el requisito temporal |
| SWRL-2 | `SocialContext(?sc) ∧ hasChildren(?sc, true) ∧ Movie(?m) ∧ hasCertification(?m, ?cert) ∧ swrlb:notEqual(?cert, "G") ∧ swrlb:notEqual(?cert, "PG") → excludedFor(?m, ?sc)` | Si el usuario tiene niños y la película no es G o PG, se excluye automáticamente |
| SWRL-3 | `UserPreferences(?up) ∧ excludedGenre(?up, ?g) ∧ Movie(?m) ∧ hasGenre(?m, ?g) → isExcludedFor(?m, ?up)` | Si el usuario ha excluido un género explícitamente y la película lo tiene, se marca como excluida |

*Cuadro B.20: Reglas SWRL documentadas en la bridge-ontology*

### B.3.7. Instancias de Mapeo Mood→Género Predefinidas en el ABox (Muestra Representativa)

El ABox de la bridge-ontology contiene 53 individuos predefinidos que implementan los mapeos contexto-género. La siguiente tabla muestra una muestra representativa; el archivo `bridge_data.ttl` contiene el inventario completo.

| Individuo | Propiedad | Valor |
|---|---|---|
| `bo:mapping_happy_comedy` | `bo:moodToGenre` | `genre:Comedy` |
| `bo:mapping_happy_adventure` | `bo:moodToGenre` | `genre:Adventure` |
| `bo:mapping_happy_animation` | `bo:moodToGenre` | `genre:Animation` |
| `bo:mapping_sad_drama` | `bo:moodToGenre` | `genre:Drama` |
| `bo:mapping_sad_romance` | `bo:moodToGenre` | `genre:Romance` |
| `bo:mapping_anxious_comedy` | `bo:moodToGenre` | `genre:Comedy` |
| `bo:mapping_nostalgic_classics` | `bo:moodToGenre` | `genre:Drama` |
| `bo:mapping_excited_action` | `bo:moodToGenre` | `genre:Action` |
| `bo:mapping_family_animation` | `bo:companionToGenre` | `genre:Animation` |
| `bo:mapping_family_family` | `bo:companionToGenre` | `genre:Family` |
| `bo:mapping_couple_romance` | `bo:companionToGenre` | `genre:Romance` |
| `bo:mapping_friends_action` | `bo:companionToGenre` | `genre:Action` |
| `bo:mapping_alone_drama` | `bo:companionToGenre` | `genre:Drama` |
| `bo:mapping_energetic_action` | `bo:energyToGenre` | `genre:Action` |
| `bo:mapping_relaxed_drama` | `bo:energyToGenre` | `genre:Drama` |

*Cuadro B.21: Muestra de instancias de mapeo predefinidas en el ABox de bridge-ontology*

---

## B.4. Resumen Consolidado del Sistema Ontológico Completo

| Categoría | movie-ontology | context-ontology | bridge-ontology | Total |
|---|---|---|---|---|
| Clases definidas | 54 | 12 | 4 | **70** |
| Propiedades de objeto | 15 | 9 | 10 | **34** |
| Propiedades de datos | 24 | 10 | 6 | **40** |
| Axiomas de disyunción | 36 | 24 | 4 | **64** |
| Restricciones de cardinalidad | 18 | 15 | 8 | **41** |
| Propiedades funcionales | 24 | 7 | 6 | **37** |
| Restricciones de rango | 20 | 10 | 6 | **36** |
| Pares propiedades inversas | 8 | 4 | 4 | **16** |
| Reglas SWRL | 0 | 0 | 3 | **3** |
| **Total axiomas TBox** | **125** | **59** | **41** | **225** |
| **Individuos ABox** | ~9,400 películas | ~50 contextos | 53 mapeos | **~9,503** |

*Cuadro B.22: Resumen cuantitativo consolidado del sistema ontológico completo*

---

> Los archivos fuente de las ontologías se encuentran en el directorio `movie-graph-rag-ontologies/` del repositorio del proyecto. El triplestore con los datos instanciados es accesible mediante Apache Jena Fuseki en los grafos nombrados `/movie-ontology`, `/context-ontology` y `/bridge-ontology`.
