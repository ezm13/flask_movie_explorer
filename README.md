# 🎬 Flask Movie Explorer

Una aplicación web desarrollada con **Flask** que permite a los usuarios buscar películas, agregarlas a favoritos y recibir **recomendaciones inteligentes** generadas con IA utilizando *Sentence Transformers*.  
Incluye autenticación de usuarios, recuperación de contraseña vía correo, y conexión directa con la API de **TMDb**.

---

## 🚀 Características principales

- 🔐 Sistema de **registro e inicio de sesión seguro** con Flask-Login.
- 🎥 **Búsqueda de películas** en tiempo real mediante la API de TMDb.
- ⭐ **Favoritos personales** guardados por usuario.
- 🧠 **Motor de recomendaciones IA** con `sentence-transformers` y embeddings cacheados.
- ✉️ **Recuperación de contraseña por correo** con Flask-Mail.
- 🎨 Interfaz moderna y oscura, con diseño responsivo basado en Bootstrap 5.
- 🗃️ Base de datos SQLite para facilidad de desarrollo.

---

## 🧩 Requisitos previos

Asegúrate de tener instalado:

- Python 3.10 o superior
- pip y venv
- Una cuenta de Gmail (para enviar correos)
- Clave de API de [The Movie Database (TMDb)](https://www.themoviedb.org/)

---

## ⚙️ Instalación

```bash
# Clonar el repositorio
git clone https://github.com/ezm13/flask_movie_explorer.git
cd flask_movie_explorer

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En macOS o Linux
venv\Scripts\activate     # En Windows

# Instalar dependencias
pip install -r requirements.txt

🔐 Variables de entorno (.env)

Crea un archivo .env en la raíz del proyecto con:

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_app_password
MAIL_DEFAULT_SENDER=tu_correo@gmail.com
TMDB_API_KEY=tu_api_key_tmdb

🧠 Recomendaciones IA

El sistema genera recomendaciones similares mediante embeddings semánticos.
Utiliza el modelo all-MiniLM-L6-v2 de sentence-transformers.

Los embeddings se almacenan en caché (data/embeddings_cache.pt)
y se regeneran automáticamente cuando cambia el archivo movies.csv. 

▶️ Ejecutar la aplicación
flask run
# o directamente:
python app.py


Luego abre:
👉 http://127.0.0.1:5000

🧰 Estructura del proyecto
flask_movie_explorer/
│
├── app.py                     # Archivo principal Flask
├── recommender.py              # Motor de recomendaciones IA
├── models.py                   # Definición de modelos (User, FavoriteMovie)
├── extensions.py               # Inicialización de SQLAlchemy y Mail
├── config.py                   # Configuración global
│
├── data/
│   └── movies.csv              # Dataset base de películas
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── recommend.html
│   └── ... (otras vistas)
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── img/
│
├── .env                        # Variables privadas (ignorado por git)
├── .gitignore
└── README.md

📦 Dependencias principales
Flask
Flask-Login
Flask-Mail
Flask-SQLAlchemy
Werkzeug
itsdangerous
python-dotenv
requests
pandas
torch
sentence-transformers

🧑‍💻 Autor

Eroz Meléndez
Desarrollador en formación — Ingeniería en Sistemas
💻 Enfocado en Python, Flask y desarrollo web full stack.
📫 Contacto: erozmelendez0@gmail.com

📜 Licencia

Este proyecto es de uso educativo y libre bajo la licencia MIT.


---

¿Quieres que le agregue también una **sección con capturas (screenshots)** de tu dashboard, login y sistema de recomendaciones (en formato Markdown listo para GitHub)?  
Así tu repositorio se ve más profesional y atractivo.