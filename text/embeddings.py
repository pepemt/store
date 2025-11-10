"""
Embedding model using sentence-transformers.

Generates dense vector embeddings for text using transformer models.
Supports GPU acceleration with CUDA.
"""

from pathlib import Path
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """
    Sentence-transformers based embedding model for generating text embeddings.
    
    Much simpler than ONNX - no conversion needed, works directly with HuggingFace models.
    """
    
    def __init__(
        self,
        model_name: str = "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
        use_gpu: bool = True,
        cache_folder: Union[str, Path] = None
    ):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name or path
            use_gpu: Whether to use GPU acceleration
            cache_folder: Where to cache downloaded models (default: ~/.cache/huggingface)
        """
        self.model_name = model_name
        
        # Determine device
        device = "cuda" if use_gpu else "cpu"
        
        # Load model
        print(f"Loading embedding model: {model_name}")
        if cache_folder:
            cache_folder = Path(cache_folder)
            cache_folder.mkdir(parents=True, exist_ok=True)
        
        self.model = SentenceTransformer(
            model_name,
            device=device,
            cache_folder=str(cache_folder) if cache_folder else None
        )
        
        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        print(f"Model loaded on {device}: embedding_dim={self.embedding_dim}")
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Normalized embedding vector (float32)
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        # Generate embedding (already normalized by sentence-transformers)
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        return embedding.astype(np.float32)
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            show_progress: Show progress bar
            
        Returns:
            Array of embeddings, shape [len(texts), embedding_dim]
        """
        if not texts:
            return np.array([], dtype=np.float32)
        
        # Generate embeddings in batches
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress
        )
        
        return embeddings.astype(np.float32)
