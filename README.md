# 🚀 Metricool Personal

Una plataforma web completa, ligera y moderna para centralizar la subida única de videos, personalización de copys y programación automática desatendida en **YouTube**, **Instagram (Reels)** y **TikTok** para múltiples cuentas (~10 perfiles simultáneos).

Diseñada para ser ejecutada localmente o alojada de forma **100% gratuita** en servicios como **Render** junto a **cron-job.org**.

---

## 🌟 Características Principales

1. **Subida Única de Video Maestro:** Carga videos en MP4, MOV o WebM con reproductor de vista previa en el navegador antes de programar.
2. **Capacidad Multi-Cuenta:** Administra simultáneamente canales de YouTube, cuentas de Instagram y perfiles de TikTok.
3. **Matriz de Copys y Horarios:** Redacta un título, descripción, hashtags y fecha/hora global, con la posibilidad de sobreescribir y personalizar el copy de forma independiente para cada cuenta.
4. **Programación Desatendida:**
   - **En local/servidor:** Motor APScheduler en segundo plano que revisa la cola cada 60 segundos.
   - **En la nube gratuita (Render):** Endpoint webhook `GET /api/cron/trigger?secret=...` para despertar y procesar la cola puntualmente usando cron-job.org sin costo.
5. **Monitor en Tiempo Real:** Dashboard con métricas, filtros por estado (*Pendientes, Publicando, Publicados, Fallidos*), enlaces directos al video en vivo y botón de reintento manual en 1 clic.
6. **Frontend Ultraligero:** Single Page Application (SPA) construida en HTML5, Tailwind CSS y JavaScript Vanilla sin dependencias pesadas de Node.js o Webpack.

---

## 🛠️ Stack Tecnológico

- **Backend:** Python 3 + FastAPI.
- **Base de Datos:** SQLite local (archivo `data/metricool.db`).
- **Motor de Tareas:** APScheduler con candados de concurrencia multihilo.
- **Conectores Oficiales:**
  - YouTube Data API v3 (Resumable Upload para videos largos).
  - Meta Graph API (Reels Containers `media_type=REELS` y subida binaria directa).
  - TikTok Content Posting API v2 (Chunked Transfer y Polling).
- **Despliegue:** Dockerfile optimizado (`python:3.11-slim`) y `render.yaml`.

---

## 🚀 Inicio Rápido en Local

### 1. Clonar y configurar entorno
```bash
cd /Users/henry/.gemini/antigravity/scratch/metricool-personal

# Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
Copia la plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```
*(Puedes dejar las credenciales de API vacías mientras pruebas la interfaz y el flujo)*.

### 3. Arrancar la aplicación
```bash
./run.sh
```
O directamente con Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Abre tu navegador en: **`http://localhost:8000`**  
La documentación interactiva de la API está en: **`http://localhost:8000/docs`**

---

## 🐳 Ejecución con Docker

Si tienes Docker instalado:
```bash
# Construir y levantar
docker-compose up -d --build

# Ver logs
docker-compose logs -f
```

---

## ☁️ Despliegue 100% Gratuito en la Nube (Render + cron-job.org)

Render ofrece un plan gratuito (*Free Web Service*) que apaga las aplicaciones inactivas tras 15 minutos sin peticiones. Combinándolo con **cron-job.org**, la app se mantiene activa y publica a la hora exacta sin pagar un solo dólar.

### Paso 1: Desplegar en Render
1. Sube este repositorio a tu cuenta de **GitHub**.
2. Entra a [Render.com](https://render.com/) y crea un nuevo **Web Service**.
3. Conecta tu repositorio de GitHub.
4. Render detectará automáticamente el archivo `Dockerfile` o la configuración de `render.yaml`.
5. En las variables de entorno (*Environment Variables*), define:
   - `CRON_SECRET`: Una clave secreta (ej. `mi_clave_super_segura_123`).
   - `BASE_URL`: La URL pública que te dé Render (ej. `https://mi-metricool.onrender.com`).
   - Las llaves de API de Google, Meta y TikTok que vayas a usar.
6. Haz clic en **Deploy Web Service**.

### Paso 2: Configurar cron-job.org
1. Entra a [cron-job.org](https://cron-job.org/) y crea una cuenta gratuita.
2. Haz clic en **Create Cronjob**.
3. Configura:
   - **Title:** `Metricool Auto Publisher`
   - **URL:** `https://tu-app-de-render.onrender.com/api/cron/trigger?secret=mi_clave_super_segura_123`
   - **Schedule:** Cada 1 minuto (`* * * * *`).
4. Guarda el cron job.

¡Listo! Cada 60 segundos cron-job.org llamará a tu aplicación, despertando el backend en Render y ejecutando cualquier publicación pendiente al instante.

---

## 🔑 Cómo Obtener tus Credenciales de API

- **YouTube Data API v3:** [Google Cloud Console](https://console.cloud.google.com/) > APIs & Services > Habilitar YouTube Data API v3 > Crear OAuth Client ID.
- **Instagram Reels:** [Meta for Developers](https://developers.facebook.com/) > Crear App de Negocios > Añadir producto Instagram Graph API.
- **TikTok API v2:** [TikTok for Developers](https://developers.tiktok.com/) > Crear App > Solicitar Content Posting API.
