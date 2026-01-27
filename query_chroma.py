#!/usr/bin/env python3
from flask import Flask, request, jsonify
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Query, SparseVector
from sentence_transformers import SentenceTransformer
from collections import Counter
import torch

app = Flask(__name__)

# Initialize model and client
_model = 'IEITYuan/Yuan-embedding-2.0-en'
device = "cuda"
model = SentenceTransformer(
    _model, 
    trust_remote_code=True, 
    device=device, 
    model_kwargs={
        "attn_implementation": "sdpa", 
        'dtype': torch.bfloat16
    }
)

client = QdrantClient(path="./qdrant_db")
collection_name = "documents"

def create_sparse_vector(text):
    """Create a simple BM25-style sparse vector from text"""
    words = text.lower().split()
    word_counts = Counter(words)
    
    indices = []
    values = []
    for word, count in word_counts.items():
        idx = hash(word) % (2**31)
        indices.append(idx)
        values.append(float(count))
    
    return SparseVector(indices=indices, values=values)

@app.route('/search', methods=['GET'])
def search():
    # Get query parameter
    query_text = request.args.get('q', '').strip()
    
    if not query_text:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    
    # Optional parameters
    limit = request.args.get('limit', 10, type=int)
    limit = min(max(1, limit), 100)  # Clamp between 1 and 100
    
    try:
        # Encode query
        with torch.no_grad():
            query_embedding = model.encode(
                query_text, 
                convert_to_numpy=True,
                show_progress_bar=False
            ).tolist()
        
        query_sparse = create_sparse_vector(query_text)
        
        # Hybrid search with RRF
        results = client.query_points(
            collection_name=collection_name,
            prefetch=[
                Prefetch(query=query_embedding, using="dense", limit=limit*2),
                Prefetch(query=query_sparse, using="sparse", limit=limit*2)
            ],
            query=Query(fusion="rrf"),
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for point in results.points:
            formatted_results.append({
                "id": point.id,
                "score": point.score,
                "file_path": point.payload.get("file_path"),
                "text_preview": point.payload.get("text", "")[:500]  # First 500 chars
            })
        
        return jsonify({
            "query": query_text,
            "results": formatted_results,
            "count": len(formatted_results)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "collection": collection_name})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
