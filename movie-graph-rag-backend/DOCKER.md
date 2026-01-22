# 🐳 Docker & GraphDB - Guía Completa

## Requisitos Previos

- **Docker** 20.10+
- **Docker Compose** 1.29+
- **bash** (para los scripts)

Verifica tu instalación:
```bash
docker --version
docker-compose --version
```

---

## 🚀 Inicio Rápido

### 1. Iniciar GraphDB
```bash
./scripts/manage-graphdb.sh start
```

Esto hará:
- ✅ Levanta el contenedor de GraphDB
- ✅ Espera a que esté listo
- ✅ Crea el repositorio `Cine`
- ✅ Carga todas las ontologías automáticamente

### 2. Verificar Estado
```bash
./scripts/manage-graphdb.sh status
```

### 3. Acceder a GraphDB
- **URL**: http://localhost:7200
- **Repositorio**: Cine
- **Usuario/Pass**: (sin autenticación por defecto)

---

## 📦 Estructura de Archivos

```
movie-graph-rag-backend/
├── docker-compose.yml              # Configuración de Docker
├── scripts/
│   ├── manage-graphdb.sh           # Script principal de gestión
│   ├── load-ontologies.sh          # Carga ontologías
│   └── watch-ontologies.sh         # Monitorea cambios
├── .env.example                     # Template de variables
└── ../movie-graph-rag-ontologies/
    └── data/ontologies/            # Fuente de datos
        ├── base/
        │   ├── movie-ontology.ttl
        │   └── context-ontology.ttl
        ├── bridge/
        │   └── bridge-ontology.ttl
        └── instances/
            ├── movies_data.ttl
            ├── contexts_data.ttl
            └── bridge_data.ttl
```

---

## 🔧 docker-compose.yml

```yaml
version: '3.8'

services:
  graphdb:
    image: ontotext/graphdb:10.6-se
    container_name: movie-graph-rag-graphdb
    ports:
      - "7200:7200"                  # Puerto GraphDB
    environment:
      - GDB_JAVA_OPTS=-Xmx4g         # Memory: 4GB
      - GDB_HEAP_INIT=2g             # Initial heap: 2GB
    volumes:
      - graphdb-data:/var/lib/graphdb  # Datos persistentes
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7200/graphdb/rest/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - movie-rag-network
```

**Características:**
- GraphDB 10.6 Standard Edition
- 4GB memoria máxima
- Health check automático
- Volumen persistente
- Red Docker personalizada

---

## 📋 Comandos Disponibles

### Gestión Principal
```bash
# Iniciar + cargar ontologías
./scripts/manage-graphdb.sh start

# Detener (datos persistentes)
./scripts/manage-graphdb.sh stop

# Reiniciar + recargar
./scripts/manage-graphdb.sh restart

# Eliminar TODO (¡cuidado!)
./scripts/manage-graphdb.sh clean

# Ver logs en tiempo real
./scripts/manage-graphdb.sh logs

# Abrir shell en el contenedor
./scripts/manage-graphdb.sh shell

# Ver estado
./scripts/manage-graphdb.sh status
```

### Carga de Ontologías
```bash
# Carga normal (respeta datos existentes)
./scripts/load-ontologies.sh

# Fuerza recarga (elimina repo y carga de cero)
./scripts/load-ontologies.sh --force

# Solo verifica conectividad
./scripts/load-ontologies.sh --check
```

### Monitoreo Automático
```bash
# Monitorea cambios continuamente (requiere fswatch)
./scripts/watch-ontologies.sh

# Ejecuta una sola vez
./scripts/watch-ontologies.sh --once
```

---

## 🔄 Flujo de Carga de Ontologías

```
1. Esperar a GraphDB (10s máximo)
   ↓
2. Crear repositorio "movies" (si no existe)
   ↓
3. Cargar en orden:
   ├─ base/movie-ontology.ttl
   ├─ base/context-ontology.ttl
   ├─ bridge/bridge-ontology.ttl
   ├─ instances/movies_data.ttl
   ├─ instances/contexts_data.ttl
   └─ instances/bridge_data.ttl
   ↓
4. Mostrar estadísticas (número de tripletas)
```

---

## 📊 Verificación de Carga

### Via Script
```bash
./scripts/load-ontologies.sh --check
# Output:
# ✅ GraphDB está disponible
```

### Via CLI
```bash
# Verificar salud
curl -f http://localhost:7200/graphdb/rest/health

# Obtener tamaño del repositorio
curl http://localhost:7200/graphdb/rest/repositories/movies/size

# Ejecutar query SPARQL
curl -X POST http://localhost:7200/graphdb/repositories/movies \
  -H "Content-Type: application/x-sparql-query" \
  -d "SELECT COUNT(?s) WHERE { ?s ?p ?o }"
```

### Via UI
1. Accede a http://localhost:7200
2. Left menu → SPARQL → Query Editor
3. Ejecuta una query de prueba

---

## 🔄 Actualizar Ontologías

### Escenario 1: Cambios Menores (agregar datos)
```bash
# Los datos nuevos se cargan sin eliminar lo existente
./scripts/load-ontologies.sh

# ✅ Datos adicionales cargados
```

### Escenario 2: Cambios Estructurales (modificar ontología)
```bash
# Elimina todo y recarga desde cero
./scripts/load-ontologies.sh --force

# ⚠️  Todos los datos anteriores se pierden
```

### Escenario 3: Desarrollo Iterativo (cambios frecuentes)
```bash
# Terminal 1: Monitorea cambios automáticamente
./scripts/watch-ontologies.sh

# Terminal 2: Edita archivos TTL
# editor movie-ontology.ttl
# (Los cambios se cargan automáticamente)
```

---

## 📈 Rendimiento & Memoria

### Configuración Actual
```env
GDB_JAVA_OPTS=-Xmx4g        # Max heap: 4GB
GDB_HEAP_INIT=2g            # Initial: 2GB
```

### Ajustar Memoria
Edita `docker-compose.yml`:
```yaml
environment:
  - GDB_JAVA_OPTS=-Xmx8g    # Aumentar a 8GB si tienes mucho datos
```

Reinicia:
```bash
./scripts/manage-graphdb.sh restart
```

---

## 🐛 Troubleshooting

### Problema: "Connection refused" al cargar ontologías
```bash
# Solución: Esperar a que GraphDB esté listo
./scripts/load-ontologies.sh

# Si falla, iniciar desde cero
./scripts/manage-graphdb.sh start
```

### Problema: Puerto 7200 en uso
```bash
# Ver qué lo usa
lsof -i :7200

# O cambiar puerto en docker-compose.yml
ports:
  - "7201:7200"  # Usar 7201 en lugar de 7200
```

### Problema: Datos no persisten después de reiniciar
```bash
# Verificar volumen
docker volume ls | grep graphdb

# Recrear volumen
docker-compose down -v
./scripts/manage-graphdb.sh start
```

### Problema: "fswatch: command not found"
```bash
# Instalar fswatch
# Linux (Ubuntu/Debian)
sudo apt-get install fswatch

# macOS
brew install fswatch

# O usar alternativa (si fswatch no disponible)
# Recargar manualmente cuando hagas cambios
```

### Problema: Ontologías no se cargan
```bash
# Verificar archivos existen
ls -la ../movie-graph-rag-ontologies/data/ontologies/

# Revisar logs
./scripts/manage-graphdb.sh logs

# Intentar recarga forzada
./scripts/load-ontologies.sh --force
```

---

## 🔗 URLs Importantes

| Recurso | URL | Usuario | Pass |
|---------|-----|---------|------|
| GraphDB UI | http://localhost:7200 | (ninguno) | (ninguno) |
| SPARQL Endpoint | http://localhost:7200/graphdb/repositories/movies | - | - |
| Health Check | http://localhost:7200/graphdb/rest/health | - | - |
| API REST | http://localhost:7200/graphdb/rest/repositories | - | - |

---

## 🧪 Ejemplos de Testing

### Ejecutar Query SPARQL
```bash
curl -X POST http://localhost:7200/graphdb/repositories/movies \
  -H "Content-Type: application/x-sparql-query" \
  -d 'SELECT ?title WHERE { ?m <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#hasTitle> ?title } LIMIT 10'
```

### Obtener Todas las Tripletas
```bash
curl -H "Accept: application/n-triples" \
  http://localhost:7200/graphdb/repositories/movies/statements
```

### Agregar Datos Manualmente
```bash
curl -X POST \
  -H "Content-Type: application/x-turtle" \
  --data-binary "@archivo.ttl" \
  http://localhost:7200/graphdb/repositories/movies/statements
```

---

## 📦 Limpiar y Reiniciar

### Eliminar TODO
```bash
# Detiene + elimina volúmenes
./scripts/manage-graphdb.sh clean

# O manual
docker-compose down -v
```

### Reiniciar Limpio
```bash
# Elimina y recrea
./scripts/manage-graphdb.sh clean
./scripts/manage-graphdb.sh start
```

---

## 💡 Tips & Mejores Prácticas

1. **Mantén ontologías versionadas** en git
2. **Usa --force solo cuando sea necesario** (recarga completa es lenta)
3. **Monitorea cambios en desarrollo** con `watch-ontologies.sh`
4. **Backupea datos importantes** antes de `clean`
5. **Revisa logs regularmente** `docker-compose logs -f`

---

## 🚀 Próximos Pasos

- [ ] Implementar backup automático
- [ ] Agregar autenticación a GraphDB
- [ ] Integrar con CI/CD (GitHub Actions)
- [ ] Crear dump de datos periódicos
- [ ] Monitoreo con Prometheus/Grafana

---

## 📚 Recursos Adicionales

- [GraphDB Documentation](https://graphdb.ontotext.com/documentation/)
- [Docker Documentation](https://docs.docker.com/)
- [SPARQL Query Language](https://www.w3.org/TR/sparql11-query/)
