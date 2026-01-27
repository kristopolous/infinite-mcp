#!/usr/bin/env python3
from qdrant_client.models import Prefetch, Query
from tqdm import tqdm
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVector, SparseVectorParams, FusionQuery
import common
import os, json
import sys
import torch
import magic
import html2text
import chardet
import signal
import re
import spacy
from sentence_transformers import SentenceTransformer
from collections import Counter
import numpy as np

device="cuda"
model = SentenceTransformer(common.model, trust_remote_code=True, device=device, model_kwargs={ "attn_implementation": "sdpa", 'dtype': torch.bfloat16  })

# Initialize Qdrant client
client = QdrantClient(path="./qdrant_db")

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

# Encode your query
query_embedding = model.encode("your search query")
query_sparse = create_sparse_vector("your search query")

"""
# Hybrid search
results = client.query_points(
    collection_name="documents",
    prefetch=[
        Prefetch(query=query_embedding, using="dense", limit=20),
        Prefetch(query=query_sparse, using="sparse", limit=20)
    ],
    query=FusionQuery(fusion="rrf"),  # Reciprocal Rank Fusion
    limit=10
)
"""
results = client.query_points(
    collection_name="documents",
    using="dense",
    query=query_embedding,
    limit=10
)
formatted_results = []
for point in results.points:
  formatted_results.append({
      "id": str(point.id),  # Convert to string
      "score": float(point.score) if point.score else 0.0,  # Ensure float
      "file_path": point.payload.get("file_path", ""),
      "text_preview": point.payload.get("text", "")[:500]
  })

print(json.dumps({
  "results": formatted_results,
  "count": len(formatted_results)
}))
