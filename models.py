from extensions import db
from flask_login import UserMixin

# ==========================================================
# 👤 Modelo de Usuario
# ==========================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

# ==========================================================
# 🎬 Modelo de Películas Favoritas (actualizado)
# ==========================================================
class FavoriteMovie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    poster_url = db.Column(db.String(300))
    overview = db.Column(db.Text)
    rating = db.Column(db.Float)
    release_date = db.Column(db.String(20))
    trailer_url = db.Column(db.String(300))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('favorites', lazy=True))

    def __repr__(self):
        return f"<FavoriteMovie {self.title}>"
