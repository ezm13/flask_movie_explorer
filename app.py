from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask import Flask
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from config import Config
from extensions import db
from models import User, FavoriteMovie
from datetime import timedelta
import os, requests

# ==========================================================
# 🔧 CONFIGURACIÓN BASE
# ==========================================================
load_dotenv()  # debe ir ANTES de crear la app
app = Flask(__name__)
app.config.from_object(Config)

# Inicializa las extensiones con app directamente ✅
db.init_app(app)
print("📧 MAIL_USERNAME:", os.environ.get("MAIL_USERNAME"))
print("🔑 MAIL_PASSWORD:", os.environ.get("MAIL_PASSWORD"))
print("📤 MAIL_DEFAULT_SENDER:", os.environ.get("MAIL_DEFAULT_SENDER"))
mail = Mail(app)  # 👈 Esta inicializa correctamente la conexión SMTP

# Config extra
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
app.config['SESSION_PERMANENT'] = True

# Serializador
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# ==========================================================
# 🔑 LOGIN MANAGER
# ==========================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================================================
# 🏠 RUTA PRINCIPAL
# ==========================================================
@app.route('/')
def index():
    return render_template('index.html')


# ==========================================================
# 🎬 DASHBOARD
# ==========================================================
@app.route('/dashboard')
@login_required
def dashboard():
    favorites = FavoriteMovie.query.filter_by(user_id=current_user.id).all()
    api_key = app.config.get('TMDB_API_KEY', '')
    return render_template('dashboard.html', favorites=favorites, tmdb_key=api_key)


@app.route('/delete_favorite/<int:movie_id>', methods=['POST'])
@login_required
def delete_favorite(movie_id):
    movie = FavoriteMovie.query.get_or_404(movie_id)
    if movie.user_id != current_user.id:
        flash("⚠️ No tienes permiso para eliminar esta película.", "danger")
        return redirect(url_for('dashboard'))

    db.session.delete(movie)
    db.session.commit()
    flash("🗑️ Película eliminada de favoritos.", "info")
    return redirect(url_for('dashboard'))


# ==========================================================
# 🔐 REGISTRO DE USUARIO
# ==========================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()

        if not username or not email or not password:
            flash("⚠️ Todos los campos son obligatorios.", "warning")
            return redirect(url_for('register'))

        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("📧 Ingresa un correo electrónico válido.", "warning")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("⚠️ Ya existe una cuenta con ese correo.", "warning")
            return redirect(url_for('register'))

        new_user = User(username=username, email=email,
                        password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Usuario registrado correctamente.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# ==========================================================
# 🔑 LOGIN / LOGOUT
# ==========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('❌ Credenciales incorrectas. Intenta de nuevo.', 'danger')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        flash(f'👋 Bienvenido de nuevo, {user.username}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))


# ==========================================================
# 📬 OLVIDÉ MI CONTRASEÑA
# ==========================================================
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No se encontró una cuenta con ese correo electrónico.", "warning")
            return redirect(url_for("forgot_password"))

        token = serializer.dumps(email, salt="password-reset-salt")
        reset_url = url_for("reset_password", token=token, _external=True)

        msg = Message(
            subject="Restablecimiento de contraseña - Flask Movie Explorer",
            sender=app.config["MAIL_DEFAULT_SENDER"],
            recipients=[email],
            body=(
                f"Hola {user.username},\n\n"
                f"Haz clic en el siguiente enlace para restablecer tu contraseña:\n\n"
                f"{reset_url}\n\n"
                "Si no solicitaste este cambio, ignora este mensaje.\n\n"
                "Atentamente,\nEl equipo de Flask Movie Explorer 🎬"
            ),
        )

        try:
            with app.app_context():  # 👈 garantiza que Mail use la app activa
                mail.send(msg)
            flash("✅ Se ha enviado un correo con instrucciones para restablecer tu contraseña.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            print(f"⚠️ Error al enviar correo: {e}")
            flash("Ocurrió un error al enviar el correo. Verifica tu App Password o configuración SMTP.", "danger")
            return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


# ==========================================================
# 🔄 RESTABLECER CONTRASEÑA
# ==========================================================
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)
    except Exception:
        flash('❌ Enlace inválido o expirado.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        user = User.query.filter_by(email=email).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('✅ Tu contraseña ha sido actualizada correctamente.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

# ==========================================================
# 🔍 BUSCAR PELÍCULAS (conexión real con TMDb)
# ==========================================================
@app.route('/search_movie', methods=['GET'])
@login_required
def search_movie():
    query = request.args.get('query', '').strip()
    if not query:
        flash('⚠️ Ingresa un nombre de película para buscar.', 'warning')
        return redirect(url_for('dashboard'))

    api_key = app.config.get('TMDB_API_KEY')
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&language=es-ES&query={query}"

    response = requests.get(url)
    if response.status_code != 200:
        flash('❌ Error al conectar con TMDb.', 'danger')
        return redirect(url_for('dashboard'))

    data = response.json()
    movies = data.get('results', [])

    if not movies:
        flash('😕 No se encontraron resultados para tu búsqueda.', 'info')
        return redirect(url_for('dashboard'))

    return render_template('search_results.html', movies=movies, query=query)

# ==========================================================
# ⭐ AGREGAR PELÍCULA A FAVORITOS
# ==========================================================
@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    title = request.form.get('title')

    # Buscar detalles en TMDb
    api_key = app.config.get('TMDB_API_KEY')
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&language=es-ES&query={title}"
    response = requests.get(search_url)

    if response.status_code != 200:
        flash('❌ Error al conectar con TMDb.', 'danger')
        return redirect(url_for('dashboard'))

    data = response.json().get('results', [])
    if not data:
        flash('⚠️ No se encontraron datos para esta película.', 'warning')
        return redirect(url_for('dashboard'))

    movie_data = data[0]  # Tomamos el primer resultado

    # Buscar tráiler en TMDb (videos)
    movie_id = movie_data.get('id')
    video_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}&language=es-ES"
    video_response = requests.get(video_url)
    trailer_url = None

    if video_response.status_code == 200:
        videos = video_response.json().get('results', [])
        for v in videos:
            if v['site'] == 'YouTube' and v['type'] == 'Trailer':
                trailer_url = f"https://www.youtube.com/embed/{v['key']}"
                break

    # Crear registro en base de datos
    movie = FavoriteMovie(
        title=movie_data.get('title'),
        poster_url=f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path')}" if movie_data.get('poster_path') else None,
        overview=movie_data.get('overview'),
        rating=movie_data.get('vote_average'),
        release_date=movie_data.get('release_date'),
        trailer_url=trailer_url,
        user_id=current_user.id
    )

    db.session.add(movie)
    db.session.commit()

    flash(f"✅ '{movie.title}' fue agregada a tus favoritos.", "success")
    return redirect(url_for('dashboard'))


# ==========================================================
# ▶️ EJECUCIÓN PRINCIPAL
# ==========================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
