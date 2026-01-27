import torch
from sentence_transformers import SentenceTransformer
_model='Octen/Octen-Embedding-8B'
device="cuda"
model = SentenceTransformer(_model, trust_remote_code=True, device=device, model_kwargs={ "attn_implementation": "sdpa", 'dtype': torch.bfloat16  })

