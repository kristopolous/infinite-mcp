#!/usr/bin/env python3
from flask import Flask, request, jsonify
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Query, SparseVector
from sentence_transformers import SentenceTransformer
from collections import Counter
import chromadb
import torch
import common

app = Flask(__name__)
RES_START = 100
res_len = RES_START

# Initialize model and client
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="documents")
model = common.model

@app.route('/search', methods=['GET'])
def search():
    # Get query parameter
    query_text = request.args.get('q', '').strip()
    
    if not query_text:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    
    query_embedding = model.encode(query_text)
    query_params = {
      'query_embeddings': query_embedding.tolist(),
      'n_results': res_len 
    }
    results = collection.query(**query_params)
    res = list(zip(
      results['ids'][0],
      results['distances'][0],
      results['metadatas'][0],
      results['documents'][0]
    ))
    
    formatted_results = []
    for doc_id, distance, metadata, document in reversed(res):
      formatted_results.append({
          "id": doc_id,
          "oneline": metadata['oneline'],
          "config": metadata['config'],
          "readme": document
      })
  
    return jsonify({
        "query": query_text,
        "results": formatted_results,
        "count": len(formatted_results)
    })
    

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "collection": collection_name})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
