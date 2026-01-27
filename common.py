import torch
from sentence_transformers import SentenceTransformer
_model='Octen/Octen-Embedding-8B'
try:
  model = SentenceTransformer(_model, trust_remote_code=True, device="cuda", model_kwargs={ "attn_implementation": "sdpa", 'dtype': torch.bfloat16  })
except:
  model = SentenceTransformer(_model, trust_remote_code=True, device="cpu", model_kwargs={ "attn_implementation": "sdpa", 'dtype': torch.bfloat16  })

