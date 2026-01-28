#!/usr/bin/env python3
from flask import Flask, request, jsonify
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Query, SparseVector
from sentence_transformers import SentenceTransformer
from collections import Counter
import chromadb
import torch
import common
import json

app = Flask(__name__)
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
      'n_results': 30
    }
    results = collection.query(**query_params)
    res = list(zip(
      results['ids'][0],
      results['distances'][0],
      results['metadatas'][0],
    ))
    
    #import pdb
    #pdb.set_trace()
    for a in res:
      mm = json.loads(a[2]['meta'])
      
      a[1] -= min(mm['stargazerCount'], 500) / 1000

    res = sorted(res, key=lambda x: x[1])

    formatted_results = []
    for doc_id, distance, metadata in res:
      cand = metadata['oneline']
      if 'npx' in cand or 'uvx' in cand:
          res = json.loads(metadata['oneline'])
          res['name'] = doc_id
          formatted_results.append(res)
  
    return jsonify({ "results": formatted_results })
    

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "collection": collection_name})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
