from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from datetime import timedelta
from config import Config
from extensions import db
from models import User, FavoriteMovie
import os, requests, logging
import recommender

# Configuración base
load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)

# Inicialización de extensiones
db.init_app(app)
mail = Mail(app)

# Configuración adicional
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=31)
app.config['SESSION_PERMANENT'] = True
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Página principal y login
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Credenciales incorrectas. Intenta de nuevo.', 'danger')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        flash(f'Bienvenido de nuevo, {user.username}!', 'success')
        return redirect(url_for('dashboard'))

    logger.info("Página de inicio y login cargada")
    return render_template('index.html')

# Cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))

# Dashboard del usuario
@app.route('/dashboard')
@login_required
def dashboard():
    favorites = FavoriteMovie.query.filter_by(user_id=current_user.id).all()
    api_key = app.config.get('TMDB_API_KEY', '')
    logger.info(f"Usuario {current_user.username} accedió al dashboard con {len(favorites)} favoritos")
    return render_template('dashboard.html', favorites=favorites, tmdb_key=api_key)

# Eliminar película de favoritos
@app.route('/delete_favorite/<int:movie_id>', methods=['POST'])
@login_required
def delete_favorite(movie_id):
    movie = FavoriteMovie.query.get_or_404(movie_id)
    if movie.user_id != current_user.id:
        flash("No tienes permiso para eliminar esta película.", "danger")
        return redirect(url_for('dashboard'))

    db.session.delete(movie)
    db.session.commit()
    logger.info(f"Película '{movie.title}' eliminada por {current_user.username}")
    flash("Película eliminada de favoritos.", "info")
    return redirect(url_for('dashboard'))

# Registro de usuario
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()

        if not username or not email or not password:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for('register'))

        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("Ingresa un correo electrónico válido.", "warning")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Ya existe una cuenta con ese correo.", "warning")
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"Nuevo usuario registrado: {username}")
        flash("Usuario registrado correctamente.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Recuperar contraseña
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
                "Si no solicitaste este cambio, ignora este mensaje."
            ),
        )

        try:
            mail.send(msg)
            logger.info(f"Correo de restablecimiento enviado a: {email}")
            flash("Se ha enviado un correo con instrucciones para restablecer tu contraseña.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            logger.error(f"Error al enviar correo de restablecimiento: {e}")
            flash("Error al enviar el correo. Verifica tu configuración SMTP.", "danger")
            return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")

# Restablecer contraseña
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)
    except Exception:
        flash('Enlace inválido o expirado.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        user = User.query.filter_by(email=email).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()
        logger.info(f"Contraseña restablecida para: {email}")
        flash('Tu contraseña ha sido actualizada.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

# Buscar películas en TMDb
@app.route('/search_movie', methods=['GET'])
@login_required
def search_movie():
    query = request.args.get('query', '').strip()
    if not query:
        flash('Ingresa un nombre de película para buscar.', 'warning')
        return redirect(url_for('dashboard'))

    api_key = app.config.get('TMDB_API_KEY')
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&language=es-ES&query={query}"

    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Error al conectar con TMDb: código {response.status_code}")
        flash('Error al conectar con TMDb.', 'danger')
        return redirect(url_for('dashboard'))

    data = response.json()
    movies = data.get('results', [])

    if not movies:
        flash('No se encontraron resultados para tu búsqueda.', 'info')
        return redirect(url_for('dashboard'))

    logger.info(f"Usuario {current_user.username} buscó: {query}")
    return render_template('search_results.html', movies=movies, query=query)

# Agregar película a favoritos
@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    title = request.form.get('title')
    api_key = app.config.get('TMDB_API_KEY')
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&language=es-ES&query={title}"
    response = requests.get(search_url)

    if response.status_code != 200:
        flash('Error al conectar con TMDb.', 'danger')
        return redirect(url_for('dashboard'))

    data = response.json().get('results', [])
    if not data:
        flash('No se encontraron datos para esta película.', 'warning')
        return redirect(url_for('dashboard'))

    movie_data = data[0]

    # Buscar tráiler
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
    logger.info(f"Película agregada a favoritos: {movie.title} por {current_user.username}")
    flash(f"'{movie.title}' fue agregada a tus favoritos.", "success")
    return redirect(url_for('dashboard'))

# Recomendaciones IA + respaldo TMDb
@app.route('/recommend', methods=['POST'])
@login_required
def recommend():
    movie_name = request.form['movie']
    api_key = app.config.get('TMDB_API_KEY')

    recommendations = recommender.get_recommendations(movie_name)
    detailed_recommendations = []

    # Si la IA no devuelve nada, usar TMDb como respaldo
    if not recommendations:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&language=es-ES&query={movie_name}"
        search_response = requests.get(search_url)
        if search_response.status_code == 200:
            data = search_response.json().get('results', [])
            if data:
                movie_id = data[0].get('id')
                similar_url = f"https://api.themoviedb.org/3/movie/{movie_id}/similar?api_key={api_key}&language=es-ES"
                similar_response = requests.get(similar_url)
                if similar_response.status_code == 200:
                    similar_movies = similar_response.json().get('results', [])
                    recommendations = [m['title'] for m in similar_movies[:5]]

    # Detalles de las películas recomendadas
    for title in recommendations:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&language=es-ES&query={title}"
        response = requests.get(search_url)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                movie = results[0]
                detailed_recommendations.append({
                    'title': movie.get('title'),
                    'overview': movie.get('overview', 'Sin descripción disponible.'),
                    'poster': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                    'id': movie.get('id')
                })

    if not detailed_recommendations:
        flash(f'No se encontraron recomendaciones para "{movie_name}".', 'warning')

    logger.info(f"Recomendaciones generadas para '{movie_name}' por {current_user.username}")
    return render_template('recommend.html', movie=movie_name, recommendations=detailed_recommendations)

# Ejecución principal
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    logger.info("Aplicación iniciada correctamente")
    app.run(debug=True)
