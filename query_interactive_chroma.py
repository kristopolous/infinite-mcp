#!/usr/bin/env python
import chromadb
import sys
import shlex
import readline
import subprocess
import atexit
import torch
import os
import spacy
import time
import common

sys.stdout.write("Starting...\n")
sys.stdout.flush()

HISTORY_FILE="history.txt"
if os.path.exists(HISTORY_FILE):
    readline.read_history_file(HISTORY_FILE)

readline.set_history_length(1000)
readline.set_auto_history(False)

atexit.register(readline.write_history_file, HISTORY_FILE)
RES_START = 4
res_len = RES_START

def quit():
    print("\nExiting...")
    sys.stdout.flush()
    sys.exit(0)

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="documents")
model = common.model

start_time=time.time()
query_last=None
query=""
while True:
  try:
    reshow = False
    processed_query = input("🤔 ▶ ").strip()

    query_embedding = model.encode(processed_query)

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
    
    shown = 0
    for doc_id, distance, metadata, document in reversed(res):
      print(f"{metadata['oneline']}")

    print(f" {res_len} | {time.time() - start_time:.3f} | {100 * shown / res_len:.2f}%")

  except KeyboardInterrupt:
    if len(query) == 0:
      quit()
    query = ""
    print("\n^C")
    continue
  except EOFError:
    quit()
  except Exception as e:
    print(f"Error: {e}")
