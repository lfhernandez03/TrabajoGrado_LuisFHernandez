# 🐳 Guía Docker para movie-graph-rag-backend-fastapi

## Archivos creados

- **Dockerfile** - Imagen de FastAPI con Python 3.11
- **docker-compose.yml** - Orquestación completa: MongoDB + Fuseki + FastAPI
- **docker-compose.local.yml** - Versión para desarrollo (MongoDB Atlas externo)
- **.dockerignore** - Optimización de imagen

---

## 🚀 Quickstart

### Opción A: Ambiente completo local (MongoDB + Fuseki + FastAPI)

```bash
# 1. Levantar todo
docker-compose up -d

# 2. Ver logs
docker-compose logs -f api

# 3. Verificar salud
curl http://localhost:8000/health
curl http://localhost:3030

# 4. Acceso MongoDB
mongodb://root:password@localhost:27017/movie-graph-rag

# 5. Detener
docker-compose down
```

### Opción B: Desarrollo rápido (solo Fuseki local + MongoDB Atlas)

```bash
# Usa la configuración con MongoDB Atlas externo
docker-compose -f docker-compose.local.yml up -d

# Logs
docker-compose -f docker-compose.local.yml logs -f api

# Detener
docker-compose -f docker-compose.local.yml down
```

---

## 📋 Variables de entorno (.env)

```env
# Aplicación
APP_ENV=development              # development | production
APP_PORT=8000

# MongoDB (docker-compose.yml)
MONGO_USER=root
MONGO_PASS=password              # Cambia en producción
MONGO_URI=mongodb://root:password@mongodb:27017/movie-graph-rag?authSource=admin

# Fuseki
FUSEKI_URL=http://fuseki:3030
FUSEKI_DATASET=movies
FUSEKI_USER=admin
FUSEKI_PASSWORD=admin

# APIs externas
JWT_SECRET=tu_jwt_secret_aqui    # Genera: openssl rand -hex 32
GEMINI_API_KEY=tu_clave_aqui
GROQ_API_KEY=tu_clave_aqui

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

---

## 🔧 Comandos útiles

### Ver servicios en ejecución
```bash
docker-compose ps
```

### Ver logs
```bash
# Todos
docker-compose logs -f

# Solo FastAPI
docker-compose logs -f api

# Último 100 líneas
docker-compose logs --tail=100 api
```

### Ejecutar comandos dentro del contenedor
```bash
# Acceso a shell
docker-compose exec api bash

# Ejecutar pytest
docker-compose exec api pytest tests/

# Ejecutar script específico
docker-compose exec api python scripts/compute_network_metrics.py
```

### Reconstruir imagen
```bash
# Rebuild
docker-compose build api

# Rebuild sin cache
docker-compose build --no-cache api
```

### Limpieza
```bash
# Detener y remover contenedores
docker-compose down

# + borrar volúmenes
docker-compose down -v

# Borrar imagen
docker image rm movie-graph-rag-backend-fastapi-api
```

---

## 🧪 Verificar servicios

### FastAPI (http://localhost:8000)
```bash
# Health check
curl http://localhost:8000/health

# Docs interactivos
open http://localhost:8000/docs
```

### Fuseki (http://localhost:3030)
```bash
# Panel de administración
open http://localhost:3030

# Health check
curl -s http://localhost:3030/$/ping
```

### MongoDB
```bash
# Conectar con mongosh
docker-compose exec mongodb mongosh -u root -p password

# O con MongoDB Compass (GUI)
# Connection: mongodb://root:password@localhost:27017
```

---

## 🚨 Troubleshooting

### Contenedor termina inmediatamente
```bash
# Ver error
docker-compose logs api

# Común: puerto ya en uso
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

### MongoDB no conecta
```bash
# Verificar conectividad
docker-compose exec api python -c "import pymongo; print(pymongo.MongoClient('mongodb://root:password@mongodb:27017/'))"

# Ver logs MongoDB
docker-compose logs mongodb
```

### Fuseki lento o no responde
```bash
# Aumentar memoria JVM en docker-compose.yml
# JVM_ARGS: -Xmx4g  (o menos si tienes poca RAM)

# Reiniciar
docker-compose restart fuseki
```

### Cambios en código no se reflejan
```bash
# Si montaste volúmenes en modo read-only (:ro)
# El hot-reload podría no funcionar

# Solución: Reconstruir imagen
docker-compose build api
docker-compose up api
```

---

## 📦 Despliegue en Render/Railway/Fly.io

Estos archivos Docker funcionan directamente con:

### Render
```bash
# Render auto-detecta docker-compose.yml
# 1. Conecta repo a dashboard.render.com
# 2. New Web Service → Deploy from repository
# 3. Render builds & deploys automáticamente
```

### Railway
```bash
# railway.app auto-detecta Dockerfile
# 1. railway Login
# 2. railway link
# 3. railway up
```

### Fly.io
```bash
# fly.io auto-detecta docker-compose.yml
# 1. fly auth login
# 2. fly launch
# 3. fly deploy
```

---

## 🔐 Notas de seguridad

⚠️ **Cambiar en producción:**
- `MONGO_PASS` - NO usar `password` en prod
- `JWT_SECRET` - Generar nuevo con `openssl rand -hex 32`
- `FUSEKI_PASSWORD` - Cambiar `admin`

✅ **En Cloud (Render/Railway/Fly.io):**
- Variables de entorno se configuran en dashboard
- Secretos se almacenan encriptados
- No envíes .env al repo

---

## 📊 Recursos consumidos (local)

| Servicio | CPU | Memoria | Almacenamiento |
|----------|-----|---------|-----------------|
| FastAPI | ~50-100m | ~200-300 MB | - |
| MongoDB | ~50-100m | ~300-500 MB | 1-5 GB (datos) |
| Fuseki | ~100-200m | ~1-2 GB | 500 MB - 5 GB (RDF) |

Para desarrollo local necesitas ~2-3 GB RAM libre.

---

## ✅ Checklist pre-producción

- [ ] `JWT_SECRET` generado y diferente al dev
- [ ] `MONGO_PASS` cambiado (no es `password`)
- [ ] `CORS_ALLOWED_ORIGINS` actualizado al dominio real
- [ ] `FUSEKI_PASSWORD` cambiado
- [ ] Gemini API key activa y con quota
- [ ] Base de datos MongoDB respaldada
- [ ] Fuseki dataset pre-cargado con ontologías
- [ ] Health check funcionando en `/health`
- [ ] Tests pasando: `docker-compose exec api pytest`
