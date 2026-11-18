# Guía para principiantes: Sistema de Nómina RD con Docker, Firebase y Jenkins

Esta guía está adaptada a tu **Sistema de Nómina RD** (Flask, Flask-SQLAlchemy, SQLite y Bootstrap). Para que funcione en la nube modifiqué el proyecto: usa el archivo **SistemaNomina\_Cloud.zip** que te dejé en el chat como base. Cada paso explica **qué haces** y **por qué**.

**Cómo encajan las tres herramientas:** Docker es una caja de mudanza que guarda tu app con todo lo que necesita. Cloud Run (de Google) ejecuta esa caja. Firebase Hosting es la puerta de entrada pública (`https://tu-proyecto.web.app`). Jenkins es un robot que, al subir cambios a GitHub, prueba la app, arma la caja y la publica solo. Firebase Hosting no puede ejecutar Flask por sí mismo; por eso se usa Cloud Run detrás.

> **Importante:** pude probar desde aquí las pruebas automáticas (10 pasaron) y el arranque con gunicorn en modo producción. No pude probar Docker, Cloud Run, Firebase ni Jenkins reales, así que haz primero la prueba local de Docker (sección 3) y el despliegue manual (sección 6) antes de automatizar.

## 0. Qué cambié en tu proyecto y por qué

| Cambio | Por qué era necesario |
| --- | --- |
| `SECRET_KEY` estaba escrita dentro de `app.py`; ahora viene de una variable de entorno y en producción la app no arranca sin una clave real | Quien viera el código podría falsificar sesiones de usuario |
| Base de datos SQLite fija; ahora se lee `DATABASE_URL` (PostgreSQL en la nube). Sin esa variable sigue usando `nominard.db` en tu PC | Cloud Run borra los archivos cuando reinicia: con SQLite perderías la nómina |
| La cookie de sesión ahora se llama `__session` | Firebase Hosting solo reenvía esa cookie a Cloud Run; con el nombre anterior el login no funcionaría en la web publicada |
| Las respuestas de `/` y `/api/*` llevan `Cache-Control: no-store` | Firebase tiene CDN y no debe guardar datos de nómina |
| En producción, "Olvidé mi contraseña" ya no muestra el token en pantalla | Con el token visible cualquiera podría tomar cualquier cuenta. Para restablecer: `flask reset-password correo clave` |
| El registro público de usuarios queda cerrado en producción (`ALLOW_REGISTRATION`) | Si no, cualquiera podría crearse una cuenta y ver sueldos y cédulas |
| El primer administrador se crea con `ADMIN_EMAIL` y `ADMIN_PASSWORD`; `seed.py` queda bloqueado en producción | `seed.py` borra todos los datos y crea usuarios con claves públicas (`admin123`) |
| `CORS` abierto y `debug=True` solo en desarrollo | En producción frontend y API salen del mismo dominio |
| Nueva ruta `/healthz` y carpeta `tests/` con 10 pruebas | Jenkins necesita pruebas y Cloud Run una forma de saber que la app vive |

**Archivos nuevos:** `config.py`, `Dockerfile`, `.dockerignore`, `.gitignore`, `.env.example`, `firebase.json`, `.firebaserc`, `public/`, `Jenkinsfile`, `jenkins/` (Dockerfile y docker-compose.yml), `requirements-dev.txt` y `tests/`. En `requirements.txt` se agregaron `gunicorn` y `psycopg2-binary`.

**Tu base de datos actual:** el zip no incluye tu `nominard.db`. Si quieres conservar tus datos locales, copia tu archivo a la carpeta del proyecto. Nunca se sube a GitHub ni a Docker (`.gitignore` y `.dockerignore` lo excluyen).

## 1. Programas que debes instalar

1. **Git** (https://git-scm.com/downloads): guarda el historial de tu código.
2. **Python 3.12** (https://www.python.org/downloads/): en Windows marca *Add Python to PATH*.
3. **Visual Studio Code** (https://code.visualstudio.com/): editor de código.
4. **Docker Desktop** (https://www.docker.com/products/docker-desktop/): en Windows pedirá activar WSL 2; acepta y reinicia.
5. **Node.js LTS** (https://nodejs.org/): lo necesita la herramienta de Firebase.
6. **Google Cloud CLI** (https://cloud.google.com/sdk/docs/install).
7. Cuentas gratuitas en **GitHub** y **Google**.

Comprueba cada instalación en una terminal (PowerShell en Windows, Terminal en Mac). Cada línea debe mostrar una versión, no un error:

```bash
git --version
python --version
docker --version
node --version
gcloud --version
```

## 2. Probar el proyecto en tu computadora

1. Descomprime `SistemaNomina_Cloud.zip`; se crea la carpeta `SistemaNomina`. Ábrela en VS Code y abre una terminal dentro de ella.
2. Crea y activa el entorno virtual (una carpeta aislada con las librerías del proyecto):

```bash
python -m venv venv
venv\Scripts\activate
```

En Mac o Linux la segunda línea es `source venv/bin/activate`.

3. Instala las librerías y corre las pruebas:

```bash
pip install -r requirements-dev.txt
pytest
```

Debe terminar con `10 passed`. Si alguna falla, lee el mensaje antes de seguir: Jenkins ejecutará exactamente estas pruebas.

4. Crea datos de ejemplo y arranca la app:

```bash
python seed.py
python app.py
```

5. Abre http://localhost:5000 e inicia sesión con `admin@nomina.local` y `admin123` (usuarios demo del seed).

### Subirlo a GitHub

Crea un repositorio vacío en GitHub (botón **New**, sin README) y, en la carpeta del proyecto:

```bash
git init
git add .
git commit -m "Nómina RD lista para la nube"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/nomina-rd.git
git push -u origin main
```

Antes del `git add`, revisa con `git status` que **no** aparezcan `venv/`, `.env` ni archivos `.db`.

## 3. Docker: empaquetar la app

El `Dockerfile` ya está listo. Esto hace cada parte:

- `FROM python:3.12-slim`: parte de una caja que ya trae Python.
- `ENV APP_ENV=production`: la app arranca en modo producción (cookie segura, sin token visible, registro cerrado).
- `COPY requirements.txt .` y `RUN pip install ...`: instala las librerías primero para que Docker reutilice este paso y los cambios sean más rápidos.
- `COPY . .`: copia tu proyecto (el `.dockerignore` deja fuera `venv`, `.git`, `*.db`, `tests`, etc.).
- `USER appuser`: la app corre sin permisos de administrador dentro de la caja.
- `CMD ... gunicorn ... --preload app:app`: arranca la app con un servidor de producción. `--preload` carga la app una sola vez, así las tablas se crean sin choques entre procesos.

### Probarlo localmente

1. Abre **Docker Desktop** y espera a que diga que está corriendo.
2. Copia `.env.example` como `.env` y cambia `SECRET_KEY`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`. **Deja** `APP_ENV=development` en este archivo: así el navegador acepta la cookie por http.
3. Construye y ejecuta:

```bash
docker build -t nomina-rd .
docker run -p 8080:8080 --env-file .env nomina-rd
```

4. Abre http://localhost:8080 e inicia sesión con el `ADMIN_EMAIL` y `ADMIN_PASSWORD` que pusiste en `.env`. También prueba http://localhost:8080/healthz: debe mostrar `{"status":"ok"}`.
5. Detén con `Ctrl + C`. Los datos de este contenedor se pierden al detenerlo; es normal, es solo una prueba.

| Error | Causa y solución |
| --- | --- |
| Cannot connect to the Docker daemon | Docker Desktop no está abierto |
| `RuntimeError: En producción debes definir SECRET_KEY` | Falta `SECRET_KEY` (mínimo 24 caracteres) en `.env` |
| El login no se queda guardado | `.env` tiene `APP_ENV=production` y estás en http; usa `development` solo para esta prueba |
| No existe ningún usuario para entrar | Faltó `ADMIN_EMAIL` o `ADMIN_PASSWORD` en `.env` |

## 4. Google Cloud y Firebase

### 4.1 Crear el proyecto

1. Entra a https://console.firebase.google.com con tu cuenta de Google y pulsa **Agregar proyecto**. Ponle un nombre (por ejemplo `nomina-rd`); puedes desactivar Google Analytics.
2. Anota el **ID del proyecto** (en *Configuración del proyecto*, algo como `nomina-rd-1a2b3`). Lo usarás en varios archivos.
3. En la esquina inferior izquierda cambia el plan **Spark** a **Blaze**. Cloud Run lo exige y pide tarjeta, pero solo pagas lo que exceda el nivel gratuito. En la consola de Google Cloud crea una **alerta de presupuesto** para tener tranquilidad.

### 4.2 Iniciar sesión desde la terminal

```bash
gcloud auth login
gcloud config set project TU_ID_DE_PROYECTO
```

### 4.3 Encender los servicios necesarios

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com firebasehosting.googleapis.com
```

Si vas a usar Cloud SQL (opción B del paso 4.5), agrega también `sqladmin.googleapis.com`.

### 4.4 Crear el almacén de imágenes Docker

Aquí guardará Jenkins cada versión de tu app:

```bash
gcloud artifacts repositories create nomina-rd --repository-format=docker --location=us-central1
```

### 4.5 Crear la base de datos PostgreSQL

Tu nómina necesita una base que no se borre. Elige una opción:

- **Opción A, la más sencilla y económica para empezar:** crea una base PostgreSQL gratuita en Neon (https://neon.tech) o Supabase (https://supabase.com), con nombre `nominard`. Copia la URL de conexión que te dan; la app acepta el formato `postgres://...` o `postgresql://...` y lo convierte sola. Si tu contraseña tiene caracteres especiales, codifícalos en la URL (por ejemplo `@` se escribe `%40`).
- **Opción B, todo dentro de Google (tiene costo mensual):** en la consola de Google Cloud abre **Cloud SQL**, crea una instancia **PostgreSQL** pequeña en `us-central1` y una base llamada `nominard`. Anota el *nombre de conexión* (`proyecto:us-central1:instancia`). Tu `DATABASE_URL` será `postgresql+psycopg2://postgres:CLAVE@/nominard?host=/cloudsql/NOMBRE_DE_CONEXION` y al desplegar necesitarás la opción `--add-cloudsql-instances NOMBRE_DE_CONEXION`.

No tienes que crear las tablas: tu app las crea sola la primera vez que arranca. El archivo `nominard.db.sql` solo sirve para SQLite.

### 4.6 Crear la cuenta de servicio para Jenkins

Es un usuario robot con permisos limitados, para que Jenkins no use tu cuenta personal:

1. En https://console.cloud.google.com ve a **IAM y administración**, luego **Cuentas de servicio**, y pulsa **Crear cuenta de servicio**. Llámala `jenkins-deployer`.
2. Asígnale estos roles: **Administrador de Cloud Run**, **Escritor de Artifact Registry**, **Usuario de cuenta de servicio**, **Administrador de Firebase Hosting** y **Consumidor de Service Usage**.
3. Entra a la cuenta creada, pestaña **Claves**, **Agregar clave**, **Crear clave nueva**, tipo **JSON**. Se descarga un archivo.
4. Guárdalo fuera de tu proyecto. Es la llave maestra: nunca lo subas a GitHub.

## 5. Firebase Hosting: la puerta de entrada

1. Instala la herramienta e inicia sesión:

```bash
npm install -g firebase-tools
firebase login
```

2. Abre `.firebaserc` y reemplaza `TU_ID_DE_PROYECTO` por tu ID real.
3. `firebase.json` ya está listo. Dice que cualquier dirección que alguien visite se envía al servicio de Cloud Run llamado `nomina-rd`. La carpeta `public/` existe solo porque Firebase la exige; todo el tráfico va a Flask.

Por eso se hicieron dos ajustes en el código: Firebase solo reenvía la cookie `__session`, y su CDN no debe guardar tus respuestas privadas.

## 6. Primer despliegue a mano

Hazlo una vez antes de automatizar: así sabrás que cada pieza funciona. Sustituye `TU_ID` por tu ID de proyecto. Cada comando va en **una sola línea**.

1. Genera una clave secreta larga y guárdala:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

2. Construye y sube la imagen:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
docker build -t us-central1-docker.pkg.dev/TU_ID/nomina-rd/nomina-rd:manual-1 .
docker push us-central1-docker.pkg.dev/TU_ID/nomina-rd/nomina-rd:manual-1
```

3. Despliega en Cloud Run (el prefijo `^##^` permite que las claves contengan comas):

```bash
gcloud run deploy nomina-rd --image us-central1-docker.pkg.dev/TU_ID/nomina-rd/nomina-rd:manual-1 --region us-central1 --allow-unauthenticated --max-instances 2 --set-env-vars "^##^APP_ENV=production##SECRET_KEY=TU_CLAVE_SECRETA##DATABASE_URL=TU_URL_DE_BASE_DE_DATOS##ADMIN_EMAIL=tu@correo.com##ADMIN_PASSWORD=TU_CLAVE_DE_ADMIN"
```

4. Publica la puerta de entrada:

```bash
firebase deploy --only hosting
```

5. Abre `https://TU_ID.web.app`. Debes ver el login de tu sistema. Entra con el `ADMIN_EMAIL` y `ADMIN_PASSWORD` que pusiste. Prueba también `https://TU_ID.web.app/healthz`. La primera carga puede tardar unos segundos porque Cloud Run arranca la app al recibir la primera visita.

> Con Cloud SQL, añade `--add-cloudsql-instances NOMBRE_DE_CONEXION` al comando del paso 3.

**Usuarios nuevos:** el registro público está cerrado. Para crear un usuario, abre el registro un momento con `gcloud run services update nomina-rd --region us-central1 --update-env-vars ALLOW_REGISTRATION=1`, crea el usuario desde la pantalla de registro y ciérralo con `--remove-env-vars ALLOW_REGISTRATION`.

## 7. Instalar Jenkins

Jenkins correrá también dentro de Docker. La carpeta `jenkins/` del proyecto ya trae una imagen personalizada con Docker, Python, gcloud y Firebase instalados, y un `docker-compose.yml`.

1. En una terminal entra a la carpeta `jenkins` y arranca:

```bash
cd jenkins
docker compose up -d --build
```

La primera vez tarda varios minutos porque descarga e instala todo.

2. Obtén la contraseña inicial:

```bash
docker compose logs jenkins
```

Busca el bloque con una clave larga de letras y números entre asteriscos.

3. Abre http://localhost:8081, pega la clave y elige **Install suggested plugins**. Cuando termine, crea tu usuario administrador y pulsa **Save and Finish**.
4. Ve a **Manage Jenkins**, **Plugins**, **Available plugins** e instala **Docker Pipeline** si no aparece ya instalado.

El compose usa `user: root` y comparte el Docker de tu PC. Es aceptable para aprender en tu computadora; **no lo repitas igual en un servidor público**.

## 8. Guardar los secretos en Jenkins

Ve a **Manage Jenkins**, **Credentials**, **System**, **Global credentials**, **Add Credentials** y crea cinco. El **ID** debe escribirse exactamente igual, porque el `Jenkinsfile` los busca por ese nombre:

| ID | Tipo | Contenido |
| --- | --- | --- |
| `gcp-key` | Secret file | El archivo JSON de la cuenta de servicio (paso 4.6) |
| `flask-secret-key` | Secret text | Tu `SECRET_KEY` de producción |
| `database-url` | Secret text | Tu `DATABASE_URL` de PostgreSQL |
| `admin-email` | Secret text | Correo del administrador inicial |
| `admin-password` | Secret text | Contraseña del administrador inicial |

Así los secretos viven cifrados dentro de Jenkins y nunca en tu código.

## 9. El Jenkinsfile

Ya está en la raíz del proyecto. Antes de subirlo, ábrelo y cambia estos valores:

- `PROJECT`: tu ID de proyecto.
- `IMAGE`: reemplaza el otro `TU_ID_DE_PROYECTO` que aparece dentro de la dirección.
- `CLOUDSQL_INSTANCE`: déjalo vacío si usas Neon o Supabase; con Cloud SQL escribe el nombre de conexión.

Cada etapa (`stage`) se ejecuta en orden y, si una falla, Jenkins se detiene: **no se publica nada roto**.

| Etapa | Qué hace |
| --- | --- |
| Pruebas | Crea un entorno virtual, instala `requirements-dev.txt` y ejecuta `pytest` |
| Construir imagen | Ejecuta `docker build` con el número de build como etiqueta (1, 2, 3...), para poder volver a una versión anterior |
| Subir imagen | Inicia sesión en Google con la cuenta de servicio y hace `docker push` a Artifact Registry |
| Desplegar | Actualiza el servicio `nomina-rd` en Cloud Run con las variables secretas y luego publica Firebase Hosting |
| Verificar | Consulta `https://TU_ID.web.app/healthz` hasta cinco veces; si no responde, el build falla |

Cada vez que Jenkins despliega reemplaza **todas** las variables de entorno del servicio con las de sus credenciales; por eso `ALLOW_REGISTRATION` vuelve a quedar cerrado en cada despliegue.

Sube los cambios:

```bash
git add .
git commit -m "Configuro Jenkins y Firebase"
git push
```

## 10. Crear el trabajo en Jenkins

1. En Jenkins pulsa **New Item**, nómbralo `nomina-rd`, elige **Pipeline** y pulsa OK.
2. Baja a la sección **Pipeline**. En *Definition* elige **Pipeline script from SCM**.
3. En *SCM* elige **Git** y pega la URL de tu repositorio. Si es privado, agrega credenciales con tu usuario de GitHub y un *Personal Access Token*.
4. En *Branch Specifier* escribe `*/main` y pulsa **Save**.
5. Pulsa **Build Now**. Haz clic en el número del build y luego en **Console Output** para ver lo que ocurre.

Si todas las etapas quedan verdes, tu nómina quedó publicada.

## 11. Que Jenkins despierte solo

- **Para empezar:** en el trabajo, sección **Build Triggers**, marca **Poll SCM** y escribe `H/5 * * * *`. Jenkins revisará GitHub cada 5 minutos.
- **Instantáneo (webhook):** GitHub necesita poder llamar a tu Jenkins, que está en tu PC. Usa una herramienta como ngrok (`ngrok http 8081`) para obtener una dirección pública temporal, y en GitHub crea el webhook en *Settings*, *Webhooks* con la URL `https://TU-DIRECCION/github-webhook/`. En el trabajo marca **GitHub hook trigger for GITScm polling** (requiere el plugin GitHub). Si Jenkins corre en un servidor con IP pública no necesitas ngrok.

## 12. Problemas frecuentes

| Síntoma | Causa probable y solución |
| --- | --- |
| `docker: command not found` en Jenkins | La imagen no se reconstruyó: `docker compose up -d --build` en la carpeta `jenkins` |
| `permission denied` sobre `docker.sock` | Verifica `user: root` en `jenkins/docker-compose.yml` |
| La etapa Pruebas falla | Corre `pytest` en tu PC y corrige primero; Jenkins ejecuta lo mismo |
| `Permission denied` al subir la imagen | Faltan roles en la cuenta de servicio (paso 4.6) |
| El sitio da 503 | La app no arrancó: revisa los *Logs* del servicio en Cloud Run. Casi siempre falta `SECRET_KEY` o la `DATABASE_URL` es incorrecta |
| Entras al login pero no se queda la sesión | La cookie no es `__session` o falta `APP_ENV=production` con HTTPS; confirma que usas `https://TU_ID.web.app` |
| Los datos desaparecen | `DATABASE_URL` vacía: está usando SQLite dentro del contenedor |
| Firebase dice que se requiere facturación | El proyecto sigue en plan Spark; cámbialo a Blaze (paso 4.1) |
| Olvidaste la clave del administrador | Ejecuta en tu PC con `DATABASE_URL` apuntando a la base en la nube: `flask --app app reset-password correo NuevaClave` (con Cloud SQL necesitas el proxy de Cloud SQL) |

## 13. Lista de comprobación

- [ ] Git, Python, Docker, Node y gcloud instalados.
- [ ] `pytest` muestra `10 passed` en tu PC.
- [ ] `docker run` local abre el login en http://localhost:8080.
- [ ] Proyecto de Firebase en plan Blaze y servicios activados.
- [ ] Artifact Registry `nomina-rd` creado.
- [ ] Base PostgreSQL creada y `DATABASE_URL` anotada.
- [ ] Cuenta de servicio con sus cinco roles y clave JSON guardada fuera del proyecto.
- [ ] `.firebaserc` y `Jenkinsfile` con tu ID de proyecto.
- [ ] Despliegue manual exitoso en `https://TU_ID.web.app`.
- [ ] Jenkins con sus cinco credenciales y el trabajo `nomina-rd`.
- [ ] Un build completo en verde.

## 14. Antes de usarlo con nómina real

1. **Copias de seguridad:** activa los respaldos automáticos de tu base PostgreSQL. Son datos de sueldos y cédulas.
2. **Cambios en las tablas:** `db.create_all()` crea tablas que faltan, pero **no modifica** las que ya existen. Si luego agregas una columna, necesitarás Flask-Migrate; hazlo antes de tener datos reales.
3. **Seguridad:** rota la clave JSON de la cuenta de servicio de vez en cuando y no expongas tu Jenkins a internet sin protección.
4. **Dominio propio:** en Firebase Hosting, sección *Dominios personalizados*.
5. **Recuperación de contraseña:** hoy se resuelve con el comando `reset-password`; más adelante conviene enviar correos reales.
