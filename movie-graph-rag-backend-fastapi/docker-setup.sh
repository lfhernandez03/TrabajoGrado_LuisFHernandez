#!/bin/bash

# 🐳 Script rápido para levantar backend completo
# Uso: bash docker-setup.sh
# O en Windows PowerShell: & 'docker-setup.ps1'

set -e

echo "🐳 Configurando movie-graph-rag-backend con Docker..."
echo ""

# 1. Verificar Docker
echo "✅ Verificando Docker..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose no está instalado"
    echo "   👉 Descarga: https://docs.docker.com/compose/install/"
    exit 1
fi

# 2. Crear .env si no existe
echo "📝 Verificando archivo .env..."
if [ ! -f ".env" ]; then
    echo "   Creando .env desde .env.example..."
    cp .env.example .env
    echo "   ✅ Archivo .env creado"
    echo "   ⚠️  IMPORTANTE: Actualiza las credenciales en .env"
else
    echo "   ✅ .env ya existe"
fi

# 3. Build de imagen Docker
echo ""
echo "🏗️  Construyendo imagen Docker..."
docker-compose build api

# 4. Levantar servicios
echo ""
echo "🚀 Levantando servicios (MongoDB + Fuseki + FastAPI)..."
docker-compose up -d

# 5. Esperar a que estén sanos
echo ""
echo "⏳ Esperando a que los servicios se inicialicen..."
sleep 10

# 6. Verificar salud
echo ""
echo "🏥 Verificando salud de servicios..."

# FastAPI
echo -n "   FastAPI: "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "⏳ Iniciando..."
fi

# Fuseki
echo -n "   Fuseki: "
if curl -s http://localhost:3030/$/ping > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "⏳ Iniciando..."
fi

# MongoDB
echo -n "   MongoDB: "
if docker-compose exec -T mongodb mongosh -u root -p password --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "⏳ Iniciando..."
fi

# 7. Output
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Backend configurado correctamente!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📍 Endpoints disponibles:"
echo "   • API:     http://localhost:8000"
echo "   • Docs:    http://localhost:8000/docs"
echo "   • Fuseki:  http://localhost:3030"
echo "   • MongoDB: mongodb://root:password@localhost:27017"
echo ""
echo "📊 Comandos útiles:"
echo "   • Ver logs:        docker-compose logs -f api"
echo "   • Ejecutar tests:  docker-compose exec api pytest"
echo "   • Shell Python:    docker-compose exec api bash"
echo "   • Detener:         docker-compose down"
echo ""
echo "🔧 Próximos pasos:"
echo "   1. Carga ontologías en Fuseki:"
echo "      docker-compose exec api python scripts/compute_network_metrics.py"
echo ""
echo "   2. Prueba la API:"
echo "      curl http://localhost:8000/health"
echo ""
echo "   3. Abre la documentación:"
echo "      open http://localhost:8000/docs"
echo ""
