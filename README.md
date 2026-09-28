# El Buen Viaje · Biblioteca

Aplicación web con React/Vite y API Django REST Framework. Incluye catálogo, usuarios con CI y teléfono, préstamos físicos, solicitudes de edición digital, gestión de inventario y roles `admin`, `librarian` y `member`.

## Backend

Desde `backend/`, instala dependencias y prepara la base de datos:

```powershell
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Las dependencias se instalan en el Python global seleccionado por Windows. Si el comando `python` apunta a otra instalación, usa la ruta del intérprete deseado delante de `-m pip` y `manage.py`.

Para desarrollo local, si lo deseas, define una clave propia en PowerShell antes de iniciar Django: `$env:DJANGO_SECRET_KEY = "tu-clave-local"`. Nunca subas una clave real al repositorio.

El superusuario tiene rol administrador. Se pueden crear cuentas de bibliotecario y administrar títulos desde `/admin/`; la API queda en `http://127.0.0.1:8000/api/`.

## Frontend

Desde `frontend/`:

```powershell
npm install
npm run dev
```

Abre la URL que indique Vite (normalmente `http://localhost:5173`). Si el backend no está iniciado, se muestra el catálogo de demostración; para registrar cuentas y usar operaciones reales se requiere la API.

## Roles

- **Admin:** control de usuarios y roles, catálogo, inventario y operaciones.
- **Bibliotecario:** gestión de libros, compras/ventas, devoluciones, solicitudes digitales y suspensiones.
- **Usuario:** consulta el catálogo, alquila ejemplares disponibles y solicita ediciones digitales.

Los permisos se validan en Django, no dependen de los controles visibles del frontend.

## Desplegar en Render

El archivo `render.yaml` define la API Django, el sitio estático Vite y PostgreSQL. Fija Python 3.13.4 y Node 22.22.0; instala dependencias, recoge los estáticos y aplica migraciones durante el build, porque Render Free no dispone de comando pre-deploy. Primero publica los cambios de `main` en GitHub; Render desplegará el nuevo commit automáticamente.

El servicio de API ejecuta `bootstrap_admin` al iniciar. Define `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` y `DJANGO_SUPERUSER_PASSWORD` en **Environment** del servicio `el-buen-viaje-api`; el comando crea el superusuario o repara su contraseña y perfil admin. Se puede volver a ejecutar para recuperar el acceso. Si el nombre ya pertenece a una cuenta lectora, el despliegue falla por seguridad: elige otro nombre de usuario para el superadmin. Inicia sesión con el **nombre de usuario** (no el email) en `https://el-buen-viaje-api.onrender.com/admin/`. Después de confirmar el acceso, elimina `DJANGO_SUPERUSER_PASSWORD` de Environment y vuelve a desplegar; la cuenta seguirá funcionando.

El frontend se compila como Static Site y apunta a `https://el-buen-viaje-api.onrender.com/api`. Si Render asigna un hostname diferente, actualiza `VITE_API_BASE_URL` en el sitio estático y los valores CORS/hosts del servicio API, y vuelve a desplegar el frontend.

**El plan gratuito sirve para una demo, no para guardar datos reales:** Render duerme las Web Services tras 15 minutos sin tráfico y el primer acceso puede tardar alrededor de un minuto. El disco del servicio es temporal. Además, PostgreSQL Free tiene 1 GB, no incluye copias de seguridad y **vence a los 30 días**, tras lo cual Render termina borrando la base de datos si no se actualiza. Usa datos de prueba; para conservar préstamos y cuentas, migra a una base con persistencia y copias de seguridad antes de cargar información real.

## Configuración antes de publicar

En producción, configura estas variables en el panel de tu proveedor de hosting o en el servicio que inicia Django. Los nombres de dominio de abajo son ejemplos: reemplaza `biblioteca.example.com` y `api.example.com` por tus dominios reales.

```powershell
cd backend
$env:DJANGO_SECRET_KEY = (python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "False"
$env:DJANGO_ALLOWED_HOSTS = "biblioteca.example.com,api.example.com"
$env:DJANGO_CORS_ALLOWED_ORIGINS = "https://biblioteca.example.com"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://biblioteca.example.com,https://api.example.com"
$env:DJANGO_SECURE_SSL_REDIRECT = "True"
$env:DJANGO_SESSION_COOKIE_SECURE = "True"
$env:DJANGO_CSRF_COOKIE_SECURE = "True"
$env:DJANGO_SECURE_HSTS_SECONDS = "31536000"
```

- `DJANGO_SECRET_KEY`: clave privada aleatoria de Django. Genérala una vez y guárdala como secreto en el hosting; no generes una nueva en cada arranque.
- `DJANGO_DEBUG=False`: desactiva páginas de error detalladas y activa los valores seguros por defecto. La aplicación no inicia en este modo si falta `DJANGO_SECRET_KEY`.
- `DJANGO_ALLOWED_HOSTS`: nombres de host que atiende el backend, separados por comas, sin `https://`, rutas ni puertos. No uses `*` en producción.
- `DJANGO_CORS_ALLOWED_ORIGINS`: orígenes exactos del frontend autorizados para llamar a la API. Incluyen protocolo (`https://`) y no llevan rutas.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: orígenes HTTPS autorizados para formularios protegidos por CSRF; suele incluir el frontend y el dominio del backend.
- HTTPS debe terminarse con un certificado TLS válido en el hosting o proxy inverso. Las opciones de cookies seguras y redirección HTTPS quedan activadas por defecto cuando `DJANGO_DEBUG=False`.

Si Django está detrás de un proxy TLS que reenvía `X-Forwarded-Proto: https`, añade `DJANGO_TRUST_PROXY_SSL=True`. Actívalo solo cuando ese encabezado lo controla tu proxy confiable. HSTS usa un año por defecto en producción; activa `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` o `DJANGO_SECURE_HSTS_PRELOAD` solo si todos los subdominios soportan HTTPS de forma permanente.

Antes del despliegue, ejecuta `python manage.py check --deploy`. Configura además `DJANGO_SECRET_KEY` y el resto de variables en el entorno persistente del hosting, no solo en una terminal temporal.

El frontend también necesita saber dónde está la API. Configura `VITE_API_BASE_URL` antes de compilarlo, usando la URL completa del API y terminando en `/api`, por ejemplo `https://api.example.com/api`. En PowerShell: `$env:VITE_API_BASE_URL = "https://api.example.com/api"`; después ejecuta `npm run build` desde `frontend/` y publica el contenido de `dist/`.