#!/usr/bin/env python3 
from tqdm import tqdm
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVector, SparseVectorParams
import os
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
import common

model = common.model

# Initialize Qdrant client
client = QdrantClient(path="./qdrant_db")

# Create collection with both dense and sparse vectors
collection_name = "documents"
try:
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(
                size=model.get_sentence_embedding_dimension(), 
                distance=Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams()
        }
    )
except:
    pass  # Collection already exists

BATCH_SIZE = 8

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def create_sparse_vector(text):
    """Create a simple BM25-style sparse vector from text"""
    # Tokenize and count
    words = text.lower().split()
    word_counts = Counter(words)
    
    # Create vocabulary mapping (simple hash)
    indices = []
    values = []
    for word, count in word_counts.items():
        # Use hash as index (Qdrant handles sparse vectors efficiently)
        idx = hash(word) % (2**31)  # Keep it positive
        indices.append(idx)
        # Simple TF weighting (you could add IDF if you track document frequencies)
        values.append(float(count))
    
    return SparseVector(indices=indices, values=values)

def move_batch(amount):
    global BATCH_SIZE
    BATCH_SIZE += amount
    BATCH_SIZE = max(1, BATCH_SIZE)
    print(f"\n*** New batch size {BATCH_SIZE}", flush=True)

def _increase_batch(signum, frame):
    move_batch(1)

def _decrease_batch(signum, frame):
    move_batch(-1)

signal.signal(signal.SIGUSR1, _increase_batch)
signal.signal(signal.SIGUSR2, _decrease_batch)

counter = 0
WORD_LEN = 3500
MIN_LEN = 2000
i = -1 

while True:
    texts = []
    valid_paths = []
    while len(valid_paths) < BATCH_SIZE:
        i += 1
        sys.stdout.write('.')
        sys.stdout.flush()
        fp = sys.stdin.readline().strip()
        if not os.path.isfile(fp):
            sys.exit(0)
        mime_type = magic.from_file(str(fp), mime=True)
        try:
            encoding = detect_encoding(fp) 
            with open(fp, 'r', encoding=encoding, errors='replace') as f:
                processed_text = f.read()
                texts.append(processed_text)
            valid_paths.append(str(fp))
        except Exception as e:
            print(f"{fp} => {e}")
    
    if len(texts) == 0:
        break
    
    try:
        with torch.no_grad():
            embeddings = model.encode(
                texts, 
                show_progress_bar=False,
                batch_size=len(texts),
                convert_to_numpy=True
            )
        
        torch.cuda.empty_cache()
        
        stubs = ["/".join(fp.split("/")[-3:]) for fp in valid_paths]  # Fixed slice
        
        # Prepare points for Qdrant
        points = []
        for idx, (embedding, text, stub) in enumerate(zip(embeddings, texts, stubs)):
            point_id = hash(stub) % (2**63)  # Generate unique ID
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector={
                        "dense": embedding.tolist(),
                        "sparse": create_sparse_vector(text)
                    },
                    payload={
                        "file_path": stub,
                        "text": text  # Store full text in payload
                    }
                )
            )
        
        try:
            client.upsert(
                collection_name=collection_name,
                points=points
            )
        except Exception as e:
            print(f"Error upserting: {e}")
            pass
        
        torch.cuda.empty_cache()
        counter += 1
        if counter > 25:
            move_batch(1)
            counter = 0
            
    except RuntimeError as e:
        i -= BATCH_SIZE
        move_batch(-1)
        counter = 0
        continue
