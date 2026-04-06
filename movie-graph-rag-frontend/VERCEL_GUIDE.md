# 🚀 Guía de deployment del Frontend en Vercel

## Inicio rápido (3 pasos)

### 1. Conectar GitHub a Vercel
```bash
# Opción A: CLI (recomendado)
npm install -g vercel
vercel login
vercel

# Opción B: Dashboard
# https://vercel.com → Sign up → Import Git Repository
# Selecciona: movie-graph-rag-frontend
```

### 2. Configurar variables de entorno
En Vercel Dashboard → Project Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL = https://tu-api-backend.onrender.com
NEXT_PUBLIC_API_PREFIX = /api/v1
```

### 3. Deploy
```bash
vercel deploy --prod

# O simplemente hace git push a main
# Vercel auto-deploya
```

---

## 🔧 Configuración por entorno

### Desarrollo Local
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
```

Corre con:
```bash
npm run dev
# http://localhost:3000
```

### Preview (Staging)
```
En Vercel: conecta rama 'develop' o 'staging'
Usado para testing antes de producción
```

### Producción
```env
NEXT_PUBLIC_API_URL=https://tu-api-backend.onrender.com
NEXT_PUBLIC_API_PREFIX=/api/v1
```

---

## 📋 Pasos detallados para Vercel

### Paso 1: Preparar repositorio local

```bash
cd movie-graph-rag-frontend

# Ver .env.example
cat .env.example

# Crear .env local (NO enviar a git)
cp .env.example .env.local

# Editar con tu URL local
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Paso 2: Crear cuenta Vercel

1. https://vercel.com/signup
2. Sign up con GitHub
3. Autorizar acceso al repositorio

### Paso 3: Importar proyecto

**Opción A: Dashboard**
```
1. https://vercel.com/dashboard → Add New → Project
2. Select Repository → movie-graph-rag-frontend
3. Framework: Next.js (auto-detectado)
4. Click "Deploy"
```

**Opción B: CLI**
```bash
vercel login
cd movie-graph-rag-frontend
vercel
# Seguir el wizard
```

### Paso 4: Configurar variables en Vercel

Dashboard → Settings → Environment Variables:

| Variable | Valor | Scope |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | https://api-prod.onrender.com | Production |
| `NEXT_PUBLIC_API_URL` | https://api-staging.onrender.com | Preview |
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | Development |

O vía CLI:
```bash
vercel env add NEXT_PUBLIC_API_URL
# Paste: https://tu-backend.com
```

### Paso 5: Deploy a producción

```bash
# Deploy a producción
vercel deploy --prod

# O simplemente git push a main
git push origin main
# Vercel auto-deploya
```

---

## 🌐 URL de tu aplicación

Una vez desplegada:

```
Default: https://movie-graph-rag-frontend.vercel.app
Custom domain: https://tudominio.com (agrega en Vercel dashboard)
```

---

## 🔄 Continuous Deployment (CD)

Vercel auto-deploya cuando haces **git push**:

| Rama | Comportamiento |
|------|-----------------|
| `main` | Deploy a producción |
| `develop` | Deploy a preview (si la configuras) |
| Pull Request | Preview automático |
| Otros commits | Preview temporal |

---

## ✅ Verificación de ambiente

### Verificar que las variables se aplicaron

```bash
# Ver output en vercel.json
vercel env ls

# Verificar en el navegador
# DevTools → Network → ver headers X-Vercel-*
curl https://tu-app.vercel.app
```

### Probar la conexión con el backend

```bash
# Abre la consola del navegador y ejecuta:
fetch('https://tu-backend.com/health').then(r => r.json()).then(console.log)
```

Deberías ver: `{ status: 'ok' }`

---

## 🚨 Troubleshooting

### Build fallido

```bash
# Ver logs completos
vercel logs

# Soluciones comunes:
# 1. Falta node_modules: npm install
# 2. Type errors: npm run build local para ver el error
# 3. Env vars no definidas: vercel env ls
```

### Errores de CORS

```
Access-Control-Allow-Origin error
```

**Solución:** Verifica en tu FastAPI backend:

```python
# app/main.py
CORS_ALLOWED_ORIGINS=https://tu-app.vercel.app
```

### API no responde

```bash
# 1. Verifica que NEXT_PUBLIC_API_URL es correcto
# 2. Abre: https://tu-backend.com/health en navegador
# 3. Si da error, el backend no está activo

# Si está en Render:
# - Puede estar durmido (free tier)
# - Espera 30s para que despierte
```

### Variables de entorno no se aplican

```bash
# 1. Redeploy es NECESARIO después de cambiar env vars
vercel deploy --prod

# 2. Clear cache del navegador (Ctrl+Shift+R)

# 3. Verifica que están en el scope correcto
vercel env ls
```

---

## 📊 Monitoreo y Analytics

Vercel dashboard proporciona:

- **Analytics**: Visitas, tiempo de carga
- **Logs**: Errores, eventos de build
- **Performance**: Core Web Vitals
- **Deployments**: Historial de diferentes versiones

https://vercel.com/dashboard/[project]/analytics

---

## 🔐 Seguridad

1. **Nunca** envíes `.env` al repo (está en `.gitignore`)
2. **Usa** `.env.example` para mostrar variables necesarias
3. **Secretos** (API keys) solo en Vercel dashboard
4. **NEXT_PUBLIC_*** variables son visibles al navegador - no pongas secretos aquí

---

## 💡 Tips avanzados

### Deploy a rama específica
```bash
vercel deploy --prod --target production
```

### Rollback a versión anterior
```bash
vercel rollback
# O desde dashboard: Deployments → Select → Promote to Production
```

### Environment variables por rama
```
En Dashboard → Settings → Environment Variables
Selecciona scope: Production / Preview / Development
```

### Conectar dominio personalizado
```
Dashboard → Settings → Domains
Agrega: tudominio.com
Configura DNS records según indicaciones
```

---

## 🎯 Checklist antes de ir a producción

- [ ] `NEXT_PUBLIC_API_URL` apunta a backend correcto
- [ ] Backend (Render/Railway) está activo
- [ ] CORS permitido en backend
- [ ] Variables en todos los scopes correctos
- [ ] Build local: `npm run build` sin errores
- [ ] Tests pasan: `npm run lint`
- [ ] `.env` NO está en git (verifica .gitignore)
- [ ] NEXT_PUBLIC_* variables no contienen secretos
- [ ] Health check funciona: `curl https://tu-backend.com/health`

---

## 📞 Soporte

- **Documentación**: https://vercel.com/docs/
- **Status**: https://status.vercel.com/
- **Comunidad**: https://github.com/vercel/next.js/discussions
