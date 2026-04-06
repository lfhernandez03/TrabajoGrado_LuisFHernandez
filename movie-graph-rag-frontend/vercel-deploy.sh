#!/bin/bash

# 🚀 Script para deployar frontend a Vercel
# Uso: bash vercel-deploy.sh

set -e

echo "🚀 Desplegando Next.js a Vercel..."
echo ""

# 1. Verificar si Vercel CLI está instalado
echo "✅ Verificando Vercel CLI..."
if ! command -v vercel &> /dev/null; then
    echo "❌ vercel no está instalado"
    echo "   Instalando: npm install -g vercel"
    npm install -g vercel
fi

# 2. Verificar si estamos autenticados
echo "🔐 Verificando autenticación..."
if [ ! -d ~/.vercel ]; then
    echo "   Requiere login:"
    vercel login
fi

# 3. Crear .env.local si no existe
echo "📝 Verificando .env.local..."
if [ ! -f ".env.local" ]; then
    echo "   Creando .env.local desde .env.example..."
    cp .env.example .env.local
    echo "   ⚠️  IMPORTANTE: Edita .env.local con tu URL de backend"
    echo "   Abre .env.local y actualiza NEXT_PUBLIC_API_URL"
    exit 1
fi

# 4. Build local
echo ""
echo "🏗️  Compilando Next.js localmente..."
npm run build

# 5. Seleccionar environment
echo ""
echo "📌 Selecciona el ambiente de deployment:"
echo "   1) Preview (staging)"
echo "   2) Production"
read -p "Selecciona (1 o 2): " env_choice

if [ "$env_choice" = "2" ]; then
    echo ""
    echo "🚨 CONFIRMACIÓN: Desplegando a PRODUCCIÓN"
    read -p "¿Estás seguro? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Cancelado."
        exit 0
    fi
    echo "🚀 Desplegando a producción..."
    vercel deploy --prod
else
    echo "🚀 Desplegando a preview..."
    vercel deploy
fi

echo ""
echo "✅ Deployment completado!"
echo ""
echo "📊 Próximos pasos:"
echo "   1. Verifica los logs: vercel logs"
echo "   2. Abre: vercel inspect [URL]"
echo "   3. En Vercel dashboard, configura variables si es necesario"
echo ""
