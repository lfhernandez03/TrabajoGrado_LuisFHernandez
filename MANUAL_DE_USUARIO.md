# Manual de Usuario — CineSemantico

**Sistema de Recomendación Semántica de Películas basado en Grafos de Conocimiento y GraphRAG**

> Trabajo de Grado · Universidad del Valle · Escuela de Ingeniería de Sistemas y Computación
> Autor: Luis F. Hernández · 2026

---

## Tabla de Contenidos

1. [Descripción General del Sistema](#1-descripción-general-del-sistema)
2. [Guía de Uso de la Aplicación](#2-guía-de-uso-de-la-aplicación)
   - 2.1 [Acceso al Sistema](#21-acceso-al-sistema)
   - 2.2 [Registro e Inicio de Sesión](#22-registro-e-inicio-de-sesión)
   - 2.3 [Página Principal (Home)](#23-página-principal-home)
   - 2.4 [Chat de Recomendación](#24-chat-de-recomendación)
   - 2.5 [Búsqueda Avanzada de Películas](#25-búsqueda-avanzada-de-películas)
   - 2.6 [Explorador de Conexiones](#26-explorador-de-conexiones)
   - 2.7 [Favoritos](#27-favoritos)
   - 2.8 [Perfil de Usuario](#28-perfil-de-usuario)
   - 2.9 [Topología del Grafo](#29-topología-del-grafo)
3. [Glosario de Términos](#3-glosario-de-términos)
4. [Solución de Problemas Frecuentes](#4-solución-de-problemas-frecuentes)

---

## 1. Descripción General del Sistema

**CineSemantico** es una aplicación web de recomendación inteligente de películas que combina tres tecnologías de vanguardia:

- **Ontologías OWL 2 DL y grafos RDF** para representar el dominio cinematográfico de manera semántica.
- **GraphRAG** (*Graph Retrieval-Augmented Generation*) para generar consultas SPARQL dinámicas a partir del lenguaje natural del usuario.
- **Modelos de Lenguaje de Gran Escala (LLMs)** para extraer el contexto de la solicitud del usuario y generar explicaciones narrativas de las recomendaciones.

### Flujo General del Sistema

```
Usuario escribe: "Quiero algo relajado para ver en familia esta noche"
        ↓
① Extracción de contexto (LLM)
   mood: relajado | compañía: familia | horario: noche
        ↓
② Generación de consulta SPARQL cruzando tres ontologías
        ↓
③ Ejecución en Apache Jena Fuseki (triple store RDF)
        ↓
④ Puntuación de compatibilidad multi-criterio
        ↓
⑤ Generación de explicación narrativa (LLM)
        ↓
Respuesta: 5 películas recomendadas con justificación personalizada
```

### Componentes del Sistema

| Componente | Tecnología | Propósito |
|---|---|---|
| Interfaz Web | Next.js 16 + React 19 | Frontend de usuario |
| API REST | FastAPI (Python 3.11+) | Backend y lógica de negocio |
| Triple Store | Apache Jena Fuseki | Almacenamiento y consulta RDF/SPARQL |
| Base de Datos | MongoDB | Usuarios, sesiones, historial, favoritos |
| LLM Principal | Gemini Flash 2.5 (Google) | Extracción de contexto y explicaciones |
| LLM Auxiliar | Llama 3.3 70B (Groq) | Etiquetado de comunidades de la red |

---

## 2. Guía de Uso de la Aplicación

### 2.1 Acceso al Sistema

Abra su navegador web y diríjase a la dirección de la aplicación proporcionada por el administrador del sistema.

La aplicación es compatible con los navegadores modernos:
- Google Chrome 110+
- Mozilla Firefox 110+
- Microsoft Edge 110+
- Safari 16+

### 2.2 Registro e Inicio de Sesión

#### Crear una cuenta nueva

1. En la pantalla de inicio, haga clic en **"Crear cuenta"** o navegue a `/register`.
2. Complete el formulario con:
   - **Nombre de usuario**: nombre para mostrar en la aplicación.
   - **Correo electrónico**: dirección de email válida.
   - **Contraseña**: mínimo 8 caracteres.
3. Haga clic en **"Registrarse"**.
4. Será redirigido automáticamente a la página principal.

#### Iniciar sesión con cuenta existente

1. Navegue a `/login`.
2. Ingrese su correo electrónico y contraseña.
3. Haga clic en **"Iniciar sesión"**.

#### Cerrar sesión

Haga clic en el icono de usuario en la esquina superior derecha del menú de navegación y seleccione **"Cerrar sesión"**.

---

### 2.3 Página Principal (Home)

La página principal (`/`) es el punto de entrada al sistema. Presenta:

**Sección Hero**
: Muestra una película destacada con su puntuación de compatibilidad y un botón de acceso rápido al chat de recomendación.

**Carruseles de Recomendación**
: Tres carruseles de películas personalizados según el perfil del usuario:
- *Para ti hoy*: basado en la hora del día y su historial.
- *Según tus favoritos*: películas similares a las que ha guardado.
- *Explora algo nuevo*: películas de comunidades que no ha explorado.

**Grid de Películas Destacadas**
: Galería de películas populares del catálogo, con información básica de género, año y puntuación.

> **Primera visita**: Si aún no tiene historial ni favoritos, los carruseles mostrarán recomendaciones basadas en géneros populares del día. Esto se denomina *cold start* y mejora progresivamente conforme use el sistema.

---

### 2.4 Chat de Recomendación

El chat (`/chat`) es la funcionalidad central del sistema. Permite solicitar recomendaciones en **lenguaje natural**, como si conversara con un experto cinematográfico.

#### Cómo escribir una consulta efectiva

El sistema extrae automáticamente el contexto de su mensaje. Puede incluir:

| Elemento de contexto | Ejemplo en la consulta |
|---|---|
| Estado de ánimo | *"algo emocionante"*, *"película relajante"*, *"quiero reír"* |
| Compañía | *"para ver solo"*, *"con mi familia"*, *"con amigos"* |
| Tiempo disponible | *"menos de 2 horas"*, *"tengo toda la tarde"* |
| Género preferido | *"acción"*, *"drama"*, *"ciencia ficción"* |
| Restricciones | *"sin violencia"*, *"apta para niños"* |

**Ejemplos de consultas:**

```
"Quiero algo ligero y divertido para ver con mi pareja esta noche"

"Recomiéndame una película de suspenso que no sea muy larga"

"Busco algo inspirador para ver solo, tengo unas 3 horas"

"Película de acción intensa, no importa la duración"
```

#### Proceso paso a paso

1. Escriba su consulta en el campo de texto inferior y presione **Enter** o haga clic en el botón de enviar.
2. El sistema procesará su solicitud (5–15 segundos según la complejidad).
3. Recibirá una respuesta con:
   - **Tarjeta de película recomendada**: título, poster, año, duración, género y puntuación de compatibilidad.
   - **Explicación narrativa**: texto que justifica por qué esa película es adecuada para su contexto.
   - **Lista de películas adicionales** (hasta 5 en total): puede explorar las alternativas deslizando horizontalmente.

#### Conversación multi-turno

El chat mantiene el contexto de la conversación. Puede refinar sus preferencias con mensajes de seguimiento:

```
Usuario: "Algo para ver en familia"
Sistema: [Muestra "El Rey León" con compatibilidad 0.94]
Usuario: "Me gustó, pero prefiero algo de acción, no animación"
Sistema: [Ajusta la recomendación con el nuevo contexto]
```

#### Accesos rápidos (*Quick Prompts*)

En la parte superior del chat se muestran sugerencias de consulta predefinidas que puede usar como punto de partida:
- *"Action movie with friends tonight"*
- *"Something relaxing to watch alone"*
- *"Family-friendly comedy"*

#### Historial de sesiones

Las conversaciones anteriores se guardan localmente en su navegador (hasta 20 sesiones). Puede acceder a ellas haciendo clic en el ícono de historial en la esquina superior izquierda del chat.

---

### 2.5 Búsqueda Avanzada de Películas

La pantalla de búsqueda (`/search`) permite explorar el catálogo con filtros precisos.

#### Modos de búsqueda

| Modo | Descripción | Ejemplo |
|---|---|---|
| **Por título** | Búsqueda por nombre de la película (parcial o completo) | `"Inception"`, `"Star"` |
| **Por director** | Películas de un director específico | `"Nolan"`, `"Spielberg"` |
| **Por género** | Filtrar por categoría cinematográfica | `"Sci-Fi"`, `"Drama"` |

#### Filtros adicionales

- **Año desde / hasta**: rango de años de lanzamiento.
- **Consulta SPARQL visible**: active esta opción para ver la consulta semántica generada y ejecutada sobre el grafo.

#### Resultados

Cada tarjeta de resultado muestra:
- Poster, título, año, director.
- Duración, certificación (G, PG, PG-13, R).
- Puntuación promedio y géneros.
- Sinopsis resumida.
- Botón para agregar a favoritos (icono de corazón).

---

### 2.6 Explorador de Conexiones

El explorador de conexiones (`/connections`) permite descubrir cómo dos películas están relacionadas dentro del grafo de conocimiento.

#### Cómo usarlo

1. En el campo **"Película origen"**, escriba el nombre de la primera película. Un menú desplegable de autocompletado le mostrará sugerencias.
2. En el campo **"Película destino"**, seleccione la segunda película del mismo modo.
3. Haga clic en **"Explorar conexión"**.

#### Interpretación de resultados

El sistema calcula el **camino más corto** entre las dos películas en el grafo, mostrando:

- **Visualización de grafo**: nodos (películas, directores, actores, géneros, temas) conectados por aristas etiquetadas con el tipo de relación.
- **Lista de conexiones**: secuencia de nodos y relaciones que une las dos películas.
- **Consulta SPARQL ejecutada** (opcional, para usuarios con conocimiento técnico).

**Ejemplo:** Conexión entre *"The Dark Knight"* y *"Memento"*:

```
The Dark Knight → [dirigida por] → Christopher Nolan → [también dirigió] → Memento
```

#### Tipos de relaciones disponibles

| Relación | Descripción |
|---|---|
| `dirigida por` | Comparten director |
| `actuada por` | Comparten actor/actriz |
| `género` | Pertenecen al mismo género |
| `tema` | Comparten un tema narrativo (ej: redención, identidad) |
| `tono` | Comparten tono (ej: oscuro, cómico, épico) |

---

### 2.7 Favoritos

La sección de favoritos (`/favorites`) almacena las películas que el usuario guarda para ver más tarde o como referencia para mejorar las recomendaciones.

#### Agregar una película a favoritos

Desde cualquier tarjeta de película en el sistema (búsqueda, chat, home), haga clic en el **ícono de corazón**. La película se añadirá a su colección personal y el ícono cambiará a color para indicar que ya está guardada.

#### Ver y gestionar favoritos

1. Navegue a `/favorites` desde el menú principal.
2. Visualice la galería completa de películas guardadas.
3. Para **eliminar un favorito**, haga clic en el ícono de corazón nuevamente (o en el botón de eliminar que aparece al pasar el cursor sobre la tarjeta).

> **Impacto en recomendaciones**: Sus favoritos alimentan directamente el motor de recomendación. Cuantas más películas guarde, más personalizadas serán las sugerencias del sistema, especialmente en el carrusel *"Según tus favoritos"* de la página principal.

---

### 2.8 Perfil de Usuario

El perfil (`/profile`) muestra su identidad dentro del sistema y su **perfil topológico de gustos cinematográficos**.

#### Información personal

- Avatar con iniciales del nombre de usuario.
- Nombre de usuario y correo electrónico.
- Fecha de registro.

#### Perfil Topológico

Esta sección es exclusiva de CineSemantico y analiza sus favoritos en el contexto del grafo de conocimiento:

**Índice de Exploración** *(Exploration Index)*
: Valor entre 0 % y 100 % que mide qué tan diverso es su gusto cinematográfico.
- **Cercano a 0 %**: es un espectador *especialista*, con preferencias muy definidas en un tipo de cine.
- **Cercano a 100 %**: es un espectador *explorador*, con gustos amplios y variados.

**Comunidades Dominantes** *(Dominant Clusters)*
: Las 3 a 5 comunidades del grafo que concentran la mayoría de sus favoritos. Cada comunidad tiene un nombre descriptivo generado automáticamente (ej: *"Thriller Psicológico Europeo"*, *"Ciencia Ficción Especulativa"*).

**Comunidades Adyacentes** *(Unexplored Adjacent Clusters)*
: Comunidades temáticamente cercanas a sus favoritas que aún no ha explorado. Son candidatas ideales para ampliar sus gustos.

**Tendencia Temporal**
: Indica si, con el paso del tiempo, sus gustos se están **especializando** (eligiendo dentro de las mismas comunidades) o **diversificando** (explorando nuevas áreas del grafo).

#### Estadísticas de Géneros

Gráfico de distribución de los géneros de sus películas favoritas, para visualizar sus preferencias de forma intuitiva.

---

### 2.9 Topología del Grafo

La vista de topología (`/topology`) es una herramienta de **exploración avanzada** del grafo de conocimiento cinematográfico. Está disponible para todos los usuarios autenticados.

#### Estadísticas Globales del Grafo

| Métrica | Descripción |
|---|---|
| **Total de películas** | Número de nodos de tipo Película en el grafo |
| **Total de conexiones** | Número total de aristas (relaciones entre entidades) |
| **Grado promedio** | Promedio de conexiones por nodo |
| **Coeficiente de clustering** | Medida de cuán interconectados están los vecinos de un nodo |
| **Número de comunidades** | Cantidad de grupos temáticos detectados (algoritmo Louvain) |
| **Modularidad** | Calidad de la estructura de comunidades (0–1, mayor es mejor) |

#### Centralidades

Las centralidades identifican las películas más importantes dentro de la red:

- **Degree Centrality** *(Top 10)*: películas con más conexiones directas. Son "hubs" del grafo cinematográfico.
- **Betweenness Centrality** *(Top 10)*: películas que sirven de puente entre diferentes partes de la red. Son claves para la exploración.
- **PageRank** *(Top 10)*: películas más influyentes de la red, considerando el peso y la calidad de sus conexiones.

#### Comunidades del Grafo *(Clusters)*

Listado de todas las comunidades detectadas, con:
- Nombre descriptivo generado por LLM.
- Número de películas en la comunidad.
- Las 10 películas más representativas.
- Comunidades adyacentes (temáticamente relacionadas).

> Esta vista es especialmente útil para **descubrir géneros y temáticas** que quizás no conocía pero que podrían interesarle, y para navegar hacia cualquier comunidad y explorar sus películas representativas.

---

## 3. Glosario de Términos

| Término | Definición |
|---|---|
| **Ontología** | Representación formal del conocimiento de un dominio. En CineSemantico, modela películas, personas, géneros, contextos y relaciones entre ellos. |
| **RDF** (*Resource Description Framework*) | Estándar W3C para representar información en forma de tripletas `(sujeto, predicado, objeto)` en un grafo. |
| **SPARQL** | Lenguaje de consulta para bases de datos RDF. Equivalente a SQL para grafos semánticos. |
| **Triple Store** | Base de datos especializada en almacenar y consultar datos RDF. CineSemantico usa Apache Jena Fuseki. |
| **GraphRAG** | Técnica que combina grafos de conocimiento con generación de texto mediante LLMs para producir respuestas contextualizadas. |
| **LLM** (*Large Language Model*) | Modelo de inteligencia artificial entrenado sobre grandes volúmenes de texto, capaz de comprender y generar lenguaje natural. |
| **Puntuación de Compatibilidad** | Valor entre 0 y 1 que indica qué tan bien una película se ajusta al contexto y preferencias del usuario en una consulta específica. |
| **Comunidad / Cluster** | Grupo de películas densamente conectadas en el grafo, que comparten características temáticas, estilísticas o autorales. |
| **Índice de Exploración** | Métrica derivada de la entropía de Shannon que cuantifica la diversidad cinematográfica del usuario en el grafo. |
| **Centralidad** | Conjunto de métricas que miden la importancia de un nodo dentro de una red (degree, betweenness, pagerank). |
| **Cold Start** | Situación en la que un usuario nuevo no tiene historial ni favoritos. El sistema usa estrategias alternativas para generar recomendaciones relevantes. |
| **Contexto Snapshot** | Captura temporal del contexto de una consulta: estado de ánimo del usuario, compañía, hora, preferencias declaradas en ese momento. |

---

## 4. Solución de Problemas Frecuentes

### El sistema tarda demasiado en responder (más de 30 segundos)

**Causa probable**: La API del LLM está saturada o la conexión a internet es lenta.

**Solución**: Espere unos segundos y reintente la consulta. Si el problema persiste, contacte al administrador del sistema.

---

### El chat muestra un error "No se pudo generar la recomendación"

**Causa probable**: La API del LLM alcanzó su límite de uso o el grafo de conocimiento no tiene datos suficientes para su consulta.

**Solución**:
1. Reformule su consulta con términos más generales (ej: en lugar de *"película francesa de los 70 sobre existencialismo"*, pruebe *"drama europeo reflexivo"*).
2. Si el error persiste, contacte al administrador del sistema.

---

### No puedo iniciar sesión con mis credenciales correctas

**Causa probable**: La sesión expiró o las credenciales son incorrectas.

**Solución**:
1. Verifique que está usando el correo electrónico y contraseña correctos.
2. Limpie las cookies del navegador para el sitio e intente nuevamente.
3. Si olvidó su contraseña, contacte al administrador para restablecer su cuenta.

---

### El Explorador de Conexiones no encuentra caminos entre dos películas

**Causa probable**: Las películas seleccionadas no están conectadas dentro del grafo en el número de saltos configurado (máximo 3 por defecto).

**Solución**: Pruebe con películas más populares o mainstream, ya que estas tienen más conexiones en el grafo. Las películas muy nicho pueden tener pocos vínculos directos.

---

*Versión del manual: 1.0 · Mayo 2026*
*Sistema: MOVIQ v1.0 · Trabajo de Grado · Universidad del Valle*
