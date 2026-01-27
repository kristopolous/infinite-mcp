#!/usr/bin/env python3 
from tqdm import tqdm
from pathlib import Path
import chromadb
import os
import sys
import torch
import magic
import html2text
import chardet
import signal
import re
import spacy
import common
from sentence_transformers import SentenceTransformer

model = common.model
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="documents")
BATCH_SIZE = 8

def detect_encoding(file_path):
      with open(file_path, 'rb') as f:
          raw_data = f.read()
      result = chardet.detect(raw_data)
      return result['encoding']

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

i = -1 
while True:
    texts = []
    configs = []
    onelines = []
    valid_paths = []
    while len(valid_paths) < BATCH_SIZE:
        i += 1
        sys.stdout.write('.')
        sys.stdout.flush()
        fp = sys.stdin.readline().strip()
        if not os.path.isfile(fp):
            sys.exit(0)

        try:
            config = Path(os.path.dirname(fp)) / "_mcp-config.json"
            if not os.path.isfile(config):
              print(f"can't do {fp} no config")
              continue
            with open(config, 'r') as f:
              if f.read().strip() == "none":
                print(f"can't do {config} bad json")

            oneline = Path(os.path.dirname(fp)) / "_one-liner.json"
            if not os.path.isfile(oneline):
              print(f"can't do {fp} no oneline")
              continue
            with open(oneline, 'r') as f:
              if f.read().strip() == "none":
                print(f"can't do {oneline} bad json")

            encoding = detect_encoding(fp) 
            with open(config, 'r', encoding=encoding, errors='replace') as f:
              lines = []
              for what in f.readlines():
                if "`" not in what:
                  lines.append(what)
              configs.append("\n".join(lines))

            with open(oneline, 'r', encoding=encoding, errors='replace') as f:
              lines = []
              for what in f.readlines():
                if "`" not in what:
                  lines.append(what)
              onelines.append("\n".join(lines))

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
      
      meta = []
      stubs = []
      for i in range(len(valid_paths)):
        stub = "/".join(valid_paths[i].split("/")[-3:-1])
        stubs.append(stub)
        meta.append({'file_path': stub, 'config': configs[i], 'oneline': onelines[i] })

      try:
        collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            ids=[f"doc_{j.replace('/', '_')}" for j in stubs],
            metadatas=meta
        )
      except:
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

