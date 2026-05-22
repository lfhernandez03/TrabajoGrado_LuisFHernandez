# Manual de Usuario — CineSemantico

**Sistema de Recomendación Semántica de Películas basado en Grafos de Conocimiento y GraphRAG**

> Trabajo de Grado · Universidad del Valle · Escuela de Ingeniería de Sistemas y Computación
> Autor: Luis F. Hernández · 2026

---

## Tabla de Contenidos

1. [Descripción General del Sistema](#1-descripción-general-del-sistema)
2. [Guía de Despliegue](#2-guía-de-despliegue) *(Para evaluadores técnicos)*
   - 2.1 [Prerrequisitos](#21-prerrequisitos)
   - 2.2 [Configuración de Variables de Entorno](#22-configuración-de-variables-de-entorno)
   - 2.3 [Despliegue con Docker Compose](#23-despliegue-con-docker-compose)
   - 2.4 [Despliegue Local para Desarrollo](#24-despliegue-local-para-desarrollo)
   - 2.5 [Verificación del Despliegue](#25-verificación-del-despliegue)
3. [Guía de Uso de la Aplicación](#3-guía-de-uso-de-la-aplicación) *(Para usuarios finales)*
   - 3.1 [Acceso al Sistema](#31-acceso-al-sistema)
   - 3.2 [Registro e Inicio de Sesión](#32-registro-e-inicio-de-sesión)
   - 3.3 [Página Principal (Home)](#33-página-principal-home)
   - 3.4 [Chat de Recomendación](#34-chat-de-recomendación)
   - 3.5 [Búsqueda Avanzada de Películas](#35-búsqueda-avanzada-de-películas)
   - 3.6 [Explorador de Conexiones](#36-explorador-de-conexiones)
   - 3.7 [Favoritos](#37-favoritos)
   - 3.8 [Perfil de Usuario](#38-perfil-de-usuario)
   - 3.9 [Topología del Grafo](#39-topología-del-grafo)
4. [Glosario de Términos](#4-glosario-de-términos)
5. [Solución de Problemas Frecuentes](#5-solución-de-problemas-frecuentes)

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

## 2. Guía de Despliegue

> Esta sección está dirigida a **evaluadores técnicos, docentes o jurados** que necesiten instalar y ejecutar el sistema en un entorno local o de pruebas.

### 2.1 Prerrequisitos

Antes de desplegar el sistema, asegúrese de tener instalados los siguientes programas:

| Herramienta | Versión mínima | Uso |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 24.x | Contenedores del sistema |
| [Docker Compose](https://docs.docker.com/compose/) | 2.x | Orquestación de servicios |
| [Node.js](https://nodejs.org/) | 18.x | Ejecución del frontend (solo modo local) |
| [Python](https://www.python.org/) | 3.11+ | Ejecución del backend (solo modo local) |
| Git | — | Clonación del repositorio |

Adicionalmente, se requieren **claves API** de los siguientes servicios gratuitos:

- **Google AI Studio** ([aistudio.google.com](https://aistudio.google.com)) → API Key para Gemini Flash 2.5.
- **Groq Cloud** ([console.groq.com](https://console.groq.com)) → API Key para Llama 3.3 70B.

### 2.2 Configuración de Variables de Entorno

1. Navegue al directorio del backend:

```bash
cd movie-graph-rag-backend-fastapi
```

2. Copie el archivo de configuración de ejemplo:

```bash
# Linux / macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

3. Abra el archivo `.env` en un editor de texto y complete los valores requeridos:

```ini
# ── LLMs (REQUERIDO) ──────────────────────────────────────────────
GEMINI_API_KEY=<su_clave_de_google_ai_studio>
GROQ_API_KEY=<su_clave_de_groq_cloud>

# ── Seguridad (CAMBIAR EN PRODUCCIÓN) ─────────────────────────────
JWT_SECRET=una_clave_secreta_larga_y_aleatoria

# ── Administrador ─────────────────────────────────────────────────
# El primer usuario que se registre con este email recibirá rol admin
ADMIN_EMAILS=su_email@ejemplo.com

# ── Los demás valores pueden dejarse con sus valores por defecto ──
```

> **Nota**: Los valores de MongoDB, Fuseki y otros servicios de infraestructura están preconfigurados para el entorno Docker y no requieren modificación para un despliegue estándar.

### 2.3 Despliegue con Docker Compose

Este es el método **recomendado**. Levanta todos los servicios (API, MongoDB, Fuseki) con un único comando.

```bash
# Desde el directorio: movie-graph-rag-backend-fastapi/
docker-compose up -d
```

El proceso descargará las imágenes necesarias (solo la primera vez) e iniciará los contenedores. Espere entre 1 y 2 minutos hasta que todos los servicios estén activos.

Para iniciar el **frontend**, abra una segunda terminal:

```bash
cd movie-graph-rag-frontend

# Cree el archivo de configuración local
# Windows PowerShell:
Set-Content .env.local "NEXT_PUBLIC_API_URL=http://localhost:8000`nNEXT_PUBLIC_API_PREFIX=/api/v1"

npm install
npm run dev
```

La aplicación estará disponible en: **http://localhost:3000**

Para detener todos los servicios:

```bash
# Desde movie-graph-rag-backend-fastapi/
docker-compose down
```

### 2.4 Despliegue Local para Desarrollo

Use esta opción si prefiere ejecutar los servicios sin Docker o si desea modificar el código.

**Backend:**

```bash
cd movie-graph-rag-backend-fastapi

# Crear y activar entorno virtual
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"

# Iniciar el servidor (con recarga automática)
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd movie-graph-rag-frontend
npm install
npm run dev
```

> **Importante**: En modo local, MongoDB y Fuseki deben estar corriendo independientemente. Se recomienda usar Docker solo para esos dos servicios:
> ```bash
> docker-compose up -d mongodb fuseki
> ```

### 2.5 Verificación del Despliegue

Una vez iniciados los servicios, verifique que cada componente responde correctamente:

| Componente | URL | Respuesta esperada |
|---|---|---|
| Frontend | http://localhost:3000 | Página de inicio de CineSemantico |
| API REST (health) | http://localhost:8000/health | `{"status": "ok"}` |
| Documentación API | http://localhost:8000/docs | Interfaz Swagger interactiva |
| Apache Fuseki | http://localhost:3030 | Panel de administración Fuseki |

---

## 3. Guía de Uso de la Aplicación

> Esta sección está dirigida al **usuario final** de la aplicación. No se requieren conocimientos técnicos.

### 3.1 Acceso al Sistema

Abra su navegador web y diríjase a la dirección de la aplicación (por ejemplo, `http://localhost:3000` si ejecuta en modo local).

La aplicación es compatible con los navegadores modernos:
- Google Chrome 110+
- Mozilla Firefox 110+
- Microsoft Edge 110+
- Safari 16+

### 3.2 Registro e Inicio de Sesión

#### Crear una cuenta nueva

1. En la pantalla de inicio, haga clic en **"Crear cuenta"** o navegue a `/register`.
2. Complete el formulario con:
   - **Nombre de usuario**: nombre para mostrar en la aplicación.
   - **Correo electrónico**: dirección de email válida.
   - **Contraseña**: mínimo 8 caracteres.
3. Haga clic en **"Registrarse"**.
4. Será redirigido automáticamente a la página principal.

> **Nota**: Si su correo electrónico coincide con el configurado como administrador (variable `ADMIN_EMAILS`), su cuenta recibirá automáticamente el rol de administrador, dando acceso a métricas del sistema.

#### Iniciar sesión con cuenta existente

1. Navegue a `/login`.
2. Ingrese su correo electrónico y contraseña.
3. Haga clic en **"Iniciar sesión"**.

#### Cerrar sesión

Haga clic en el icono de usuario en la esquina superior derecha del menú de navegación y seleccione **"Cerrar sesión"**.

---

### 3.3 Página Principal (Home)

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

### 3.4 Chat de Recomendación

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

### 3.5 Búsqueda Avanzada de Películas

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

### 3.6 Explorador de Conexiones

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

### 3.7 Favoritos

La sección de favoritos (`/favorites`) almacena las películas que el usuario guarda para ver más tarde o como referencia para mejorar las recomendaciones.

#### Agregar una película a favoritos

Desde cualquier tarjeta de película en el sistema (búsqueda, chat, home), haga clic en el **ícono de corazón**. La película se añadirá a su colección personal y el ícono cambiará a color para indicar que ya está guardada.

#### Ver y gestionar favoritos

1. Navegue a `/favorites` desde el menú principal.
2. Visualice la galería completa de películas guardadas.
3. Para **eliminar un favorito**, haga clic en el ícono de corazón nuevamente (o en el botón de eliminar que aparece al pasar el cursor sobre la tarjeta).

> **Impacto en recomendaciones**: Sus favoritos alimentan directamente el motor de recomendación. Cuantas más películas guarde, más personalizadas serán las sugerencias del sistema, especialmente en el carrusel *"Según tus favoritos"* de la página principal.

---

### 3.8 Perfil de Usuario

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

### 3.9 Topología del Grafo

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

> Esta vista es especialmente útil para **descubrir géneros y temáticas** que quizás no conocía pero que podrían interesarle, navegar hacia cualquier comunidad y explorar sus películas representativas.

---

## 4. Glosario de Términos

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

## 5. Solución de Problemas Frecuentes

### El sistema tarda demasiado en responder (>30 segundos)

**Causa probable**: Fuseki está inicializando o la clave de la API del LLM es inválida.

**Solución**:
1. Verifique que todos los contenedores Docker están corriendo: `docker-compose ps`.
2. Revise los logs del backend: `docker-compose logs api --tail=50`.
3. Confirme que las variables `GEMINI_API_KEY` y `GROQ_API_KEY` son válidas en el archivo `.env`.

---

### El chat muestra un error "No se pudo generar la recomendación"

**Causa probable**: Fuseki no tiene datos cargados o la API del LLM alcanzó su límite de uso.

**Solución**:
1. Acceda a la interfaz de Fuseki en `http://localhost:3030` y verifique que el dataset `movies` contiene tripletas.
2. Revise el panel de uso en Google AI Studio o Groq Cloud para verificar cuotas.

---

### La aplicación frontend no carga (pantalla en blanco)

**Causa probable**: El archivo `.env.local` no está configurado o el backend no está accesible.

**Solución**:
1. Verifique que existe el archivo `.env.local` en `movie-graph-rag-frontend/`.
2. Confirme que contiene: `NEXT_PUBLIC_API_URL=http://localhost:8000`.
3. Compruebe que la API responde en `http://localhost:8000/health`.

---

### No puedo iniciar sesión con mis credenciales correctas

**Causa probable**: La sesión JWT expiró o la base de datos de usuarios fue reiniciada.

**Solución**:
1. Limpie las cookies del navegador para el sitio.
2. Intente registrar una nueva cuenta.
3. Si el problema persiste, verifique que el volumen de MongoDB no fue eliminado al detener Docker.

---

### El Explorador de Conexiones no encuentra caminos entre dos películas

**Causa probable**: Las películas seleccionadas no están conectadas dentro del grafo en el número de saltos configurado (máximo 3 por defecto).

**Solución**: Pruebe con películas más populares o mainstream, ya que estas tienen más conexiones en el grafo. Las películas muy nicho pueden tener pocos vínculos directos.

---

*Versión del manual: 1.0 · Mayo 2026*
*Sistema: CineSemantico v1.0 · Trabajo de Grado · Universidad del Valle*
