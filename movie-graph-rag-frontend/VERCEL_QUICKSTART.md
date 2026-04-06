# 🎬 Frontend Deployment - Vercel Quickstart

## 📋 Archivos creados

- **vercel.json** - Configuración específica de Vercel
- **VERCEL_GUIDE.md** - Guía completa y detallada
- **.vercelignore** - Archivos a ignorar en build
- **vercel-deploy.sh** - Script automático (Linux/macOS)
- **vercel-deploy.ps1** - Script automático (Windows)
- **.env.example** - Variables comentadas

---

## 🚀 Deploy en 3 pasos

### Paso 1: Conectar repositorio a Vercel

**Opción A: Online (Recomendado)**
```
1. https://vercel.com/dashboard
2. Sign in con GitHub
3. Add New → Project
4. Selecciona: movie-graph-rag-frontend
5. Click "Deploy"
```

**Opción B: CLI**
```bash
npm install -g vercel
vercel login
cd movie-graph-rag-frontend
vercel
```

### Paso 2: Configurar variables de entorno

En **Vercel Dashboard** → Project Settings → Environment Variables:

Agrega (IMPORTANTE):
```
NEXT_PUBLIC_API_URL = [URL de tu backend]
```

Donde `[URL de tu backend]` es:
- **Local dev**: `http://localhost:8000`
- **Render**: `https://tu-api-name.onrender.com`
- **Railway**: `https://tu-api-railway.up.railway.app`

### Paso 3: Deploy

**Automático:**
```bash
git push origin main
# Vercel auto-deploya en 1-2 minutos
```

**Manual:**
```bash
vercel deploy --prod
```

---

## 🔧 Setup local

```bash
# 1. Instalar dependencias
npm install

# 2. Crear .env.local
cp .env.example .env.local

# 3. Editar .env.local (si es local)
# NEXT_PUBLIC_API_URL=http://localhost:8000

# 4. Dev server
npm run dev
# Abre: http://localhost:3000

# 5. Build simulation
npm run build
npm start
```

---

## 📊 URLs después de deploy

| Componente | URL |
|-----------|-----|
| Frontend (Vercel) | https://movie-graph-rag-frontend.vercel.app |
| Backend (Render) | https://movie-rag-api.onrender.com |
| Docs API | https://movie-rag-api.onrender.com/docs |

---

## ✅ Verificar que todo funciona

1. **Abre el frontend**: https://movie-graph-rag-frontend.vercel.app
2. **Abre DevTools** (F12) → Console
3. **Ejecuta**: 
```javascript
fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`).then(r => r.json()).then(console.log)
```
4. Debería mostrar: `{ status: 'ok' }`

---

## 🚨 Problemas comunes

### Backend no conecta
```
Error: Failed to fetch from http://localhost:8000
```
**Solución**: 
- Verifica NEXT_PUBLIC_API_URL en Vercel env vars
- Asegúrate que apunta a la URL correcta del backend
- Redeploy es NECESARIO después de cambiar variables

### CORS error
```
Access-Control-Allow-Origin error
```
**Solución**: 
- En backend FastAPI, actualiza CORS_ALLOWED_ORIGINS:
```env
CORS_ALLOWED_ORIGINS=https://tu-app.vercel.app,https://www.tu-app.vercel.app
```
- Redeploy backend

### Build fallido
```bash
# Ver error completo
npm run build

# Soluciones:
# 1. npm install
# 2. npm run lint
# 3. vercel logs
```

---

## 📦 Estructura de deployment

```
Tu Laptop (local)
        ↓
GitHub (main branch)
        ↓
Vercel (auto-build & deploy)
        ↓
🌐 https://movie-graph-rag-frontend.vercel.app ✅
        ↓
Fetch/API calls
        ↓
Backend (Render/Railway)
        ↓
Database + Fuseki
```

---

## 🔐 Seguridad

✅ **Seguro**:
- Usar `NEXT_PUBLIC_*` para URLs de backend
- Guardar env vars en Vercel dashboard
- No enviar `.env` al repo

⚠️ **NUNCA**:
- Poner API keys en código
- Enviar `.env` a GitHub
- Exponer secretos en `NEXT_PUBLIC_`

---

## 📖 Documentación completa

Lee **VERCEL_GUIDE.md** para:
- Troubleshooting detallado
- Configuración avanzada
- Custom domains
- Environment variables por rama
- Rollbacks
- Analytics

---

## 🎯 Checklist rápido

- [ ] Frontend desplegado en Vercel
- [ ] `NEXT_PUBLIC_API_URL` configurada
- [ ] Backend activo y accesible
- [ ] CORS habilitado en backend
- [ ] `/health` funciona
- [ ] Frontend conecta correctamente
- [ ] No hay errores en DevTools Console

---

## 📞 Siguiente paso

1. **Verifica que el backend también esté desplegado** (ver `../movie-graph-rag-backend-fastapi/DOCKER_GUIDE.md`)
2. **Obtén la URL del backend desplegado**
3. **Configura `NEXT_PUBLIC_API_URL` en Vercel**
4. **Haz git push para redeployar** (si ya estaba desplegado)
