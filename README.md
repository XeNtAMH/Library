# Atenea · Biblioteca

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

Para definir una clave propia de Django en PowerShell antes de iniciar el servidor, ejecuta `$env:DJANGO_SECRET_KEY = "tu-clave-local"`. No subas claves reales al repositorio; en producción define esta variable en la configuración segura del servidor.

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

Los permisos se validan en Django, no dependen de los controles visibles del frontend. Configura `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, CORS y HTTPS antes de publicar la aplicación.