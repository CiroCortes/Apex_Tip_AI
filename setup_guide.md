# ApexTip AI - Setup Guide para Servicios Externos

Esta guía detalla los pasos para obtener las credenciales necesarias para el backend de ApexTip AI.

## 1. API de Deportes (MVP: Fútbol)
Para alimentar la inteligencia artificial con estadísticas reales (xG, posesión, H2H).

**Recomendación:** [API-Football](https://www.api-football.com/)
1. Crea una cuenta gratuita en su página web o a través de RapidAPI.
2. Navega a tu panel de control/dashboard.
3. Copia tu **API Key**.
4. *(Añadiremos esta variable al archivo `.env` en los próximos pasos).*

## 2. Base de Datos (Supabase)
Usamos Supabase como nuestra base de datos PostgreSQL (y almacenamiento si se requiere).

1. Ve a [Supabase](https://supabase.com/) y crea/inicia sesión en tu cuenta.
2. Haz clic en **"New Project"**.
3. Nombra tu proyecto (ej. `apextip-ai`) y genera una contraseña segura.
4. Cuando el proyecto termine de crearse, ve a **Project Settings -> API** (en el menú lateral izquierdo).
5. Copia la **Project URL** (será tu `SUPABASE_URL`).
6. Copia la **anon public key** o **service_role key** (será tu `SUPABASE_KEY`).
7. Pégalas en tu archivo `.env`.

## 3. Autenticación (Firebase)
Usamos Firebase Auth para gestionar de forma segura el inicio de sesión de los usuarios (Email, Google, etc.).

1. Ve a la [Consola de Firebase](https://console.firebase.google.com/).
2. Haz clic en **Crear un proyecto** y nómbralo `ApexTip`.
3. En el menú izquierdo, selecciona **Authentication** y haz clic en "Comenzar". Habilita los proveedores que desees (ej. Correo electrónico/contraseña).
4. Ve al ícono de **Engranaje (Configuración del proyecto) -> Cuentas de servicio**.
5. Haz clic en el botón **"Generar nueva clave privada"**.
6. Esto descargará un archivo JSON. Guárdalo en la carpeta raíz del proyecto (junto a `main.py`) y renómbralo a algo simple como `firebase-credentials.json`.
7. En tu archivo `.env`, asegúrate de que `FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json` apunte a ese archivo.

## 4. Inteligencia Artificial (Gemini)
El cerebro analítico del proyecto.

1. Ve a [Google AI Studio](https://aistudio.google.com/).
2. Inicia sesión y busca la sección **"Get API key"** o **"API Keys"**.
3. Crea una nueva clave.
4. Copia la clave y pégala en tu `.env` como `GEMINI_API_KEY`.

---
*Nota: Nunca subas el archivo `.env` o tu archivo JSON de Firebase a GitHub. Ya están incluidos en el `.gitignore` proporcionado.*
