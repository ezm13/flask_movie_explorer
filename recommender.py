import os
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
import hashlib
import time

# Ruta absoluta del CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), "data/movies.csv")
CACHE_FILE = os.path.join(os.path.dirname(__file__), "data/embeddings_cache.pt")

# Cargar modelo
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def file_hash(filepath):
    """Genera un hash único del archivo CSV para detectar cambios."""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# Verifica que el CSV exista
if not os.path.exists(CSV_PATH):
    print(f"❌ No se encontró el archivo: {CSV_PATH}")
    movies = pd.DataFrame(columns=["title", "description"])
else:
    movies = pd.read_csv(CSV_PATH)

# Cargar o regenerar embeddings
if os.path.exists(CACHE_FILE):
    cache = torch.load(CACHE_FILE)
    if cache.get("hash") == file_hash(CSV_PATH):
        print("Cargando embeddings desde archivo existente ✅")
        embeddings = cache["embeddings"]
    else:
        print("⚙️ Cambios detectados en movies.csv — regenerando embeddings...")
        sentences = movies["title"] + ". " + movies["description"]
        embeddings = model.encode(sentences.tolist(), convert_to_tensor=True)
        torch.save({"embeddings": embeddings, "hash": file_hash(CSV_PATH)}, CACHE_FILE)
else:
    print("Creando embeddings por primera vez... 🧩")
    sentences = movies["title"] + ". " + movies["description"]
    embeddings = model.encode(sentences.tolist(), convert_to_tensor=True)
    torch.save({"embeddings": embeddings, "hash": file_hash(CSV_PATH)}, CACHE_FILE)

# Sistema de recomendaciones
def get_recommendations(movie_title, num_results=5):
    """Obtiene recomendaciones similares usando similitud semántica."""
    if movie_title not in movies["title"].values:
        # Buscar coincidencia parcial (por ejemplo, "Incept" → "Inception")
        matches = movies[movies["title"].str.contains(movie_title, case=False, na=False)]
        if matches.empty:
            print(f"⚠️ No se encontró coincidencia para '{movie_title}'")
            return []
        idx = matches.index[0]
    else:
        idx = movies[movies["title"] == movie_title].index[0]

    query_vec = embeddings[idx]
    scores = util.pytorch_cos_sim(query_vec, embeddings)[0]

    # Evitar errores si hay menos de num_results
    num_results = min(num_results + 1, len(movies))

    top_results = torch.topk(scores, k=num_results)
    recommendations = []
    for i in top_results[1]:
        title = movies.iloc[i.item()]["title"]
        if title != movie_title:
            recommendations.append(title)

    return recommendations
