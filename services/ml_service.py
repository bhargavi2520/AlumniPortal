import numpy as np

# Lazy loaded module-level variable
_model = None

def _get_model():
    """
    Lazy initialize the SentenceTransformer model only when first needed.
    This prevents memory/startup overhead if ML features aren't used.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("[ml_service] Initializing all-MiniLM-L6-v2 model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def chunk_text(text: str, max_words=300):
    """
    Splits text into smaller chunks based on word count. 
    A more robust chunker might use NLTK or spacy.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i+max_words])
        chunks.append(chunk)
    return chunks

def generate_embedding(text: str) -> np.ndarray:
    """
    Given an arbitrarily long text document, generates a single robust
    vector embedding representing its semantic meaning.
    Returns None if text is empty.
    """
    if not text.strip():
        return None
        
    model = _get_model()
    chunks = chunk_text(text)
    
    if not chunks:
        return None
        
    # Generate embeddings for all chunks natively
    chunk_embeddings = model.encode(chunks)
    
    # If only one chunk, return it
    if len(chunk_embeddings) == 1:
        return chunk_embeddings[0]
        
    # Mean pooling across chunks to get a single doc vector
    document_embedding = np.mean(chunk_embeddings, axis=0)
    
    # Normalize for cosine similarity
    norm = np.linalg.norm(document_embedding)
    if norm > 0:
        document_embedding = document_embedding / norm
        
    return document_embedding

def compute_similarities(query_vector: np.ndarray, target_vectors_dict: dict) -> dict:
    """
    Given a single query vector (e.g. Resume) and a dict mapping job_ids 
    to their target vectors, compute cosine similarity efficiently using numpy.
    
    Returns: a dict of {job_id: similarity_score (0.0 to 1.0)}
    """
    if query_vector is None or not target_vectors_dict:
        return {}

    job_ids = list(target_vectors_dict.keys())
    target_matrix = np.array(list(target_vectors_dict.values()))
    
    # Compute dot products between query and all targets
    dot_products = np.dot(target_matrix, query_vector)
    
    # Compute norms
    query_norm = np.linalg.norm(query_vector)
    target_norms = np.linalg.norm(target_matrix, axis=1)
    
    scores = {}
    for i, job_id in enumerate(job_ids):
        target_norm = target_norms[i]
        
        # Avoid division by zero
        if query_norm > 0 and target_norm > 0:
            sim = dot_products[i] / (query_norm * target_norm)
            # Clip between 0 and 1 theoretically
            sim = max(0.0, min(1.0, float(sim)))
        else:
            sim = 0.0
            
        scores[job_id] = sim
        
    return scores
