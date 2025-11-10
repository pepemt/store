"""
Binary cache manager for term embeddings and mappings.

Stores:
- terms_embeddings.npz: Terms and their embeddings (NumPy)
- term_articles.pkl: Term → article_ids mapping (Pickle)
- metadata.json: Cache metadata and version info
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import numpy as np


class CacheManager:
    """Manage binary cache for term embeddings."""
    
    CACHE_VERSION = "1.0"
    
    def __init__(self, cache_dir: Path = None):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files (default: text/.cache)
        """
        if cache_dir is None:
            # Default to text/.cache relative to this file
            cache_dir = Path(__file__).parent / ".cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file paths
        self.embeddings_file = self.cache_dir / "terms_embeddings.npz"
        self.mappings_file = self.cache_dir / "term_articles.pkl"
        self.metadata_file = self.cache_dir / "metadata.json"
    
    def exists(self) -> bool:
        """Check if cache exists."""
        return (
            self.embeddings_file.exists() and
            self.mappings_file.exists() and
            self.metadata_file.exists()
        )
    
    def is_valid(self, max_age_days: int = 30) -> bool:
        """
        Check if cache is valid.
        
        Args:
            max_age_days: Maximum age in days (0 = no age check)
            
        Returns:
            True if cache exists and is valid
        """
        if not self.exists():
            return False
        
        try:
            metadata = self.load_metadata()
            
            # Check version
            if metadata.get('version') != self.CACHE_VERSION:
                print(f"Cache version mismatch: {metadata.get('version')} != {self.CACHE_VERSION}")
                return False
            
            # Check age if specified
            if max_age_days > 0:
                created_at = datetime.fromisoformat(metadata['created_at'])
                age = (datetime.now() - created_at).days
                if age > max_age_days:
                    print(f"Cache too old: {age} days > {max_age_days} days")
                    return False
            
            return True
        except Exception as e:
            print(f"Error validating cache: {e}")
            return False
    
    def save(
        self,
        terms: List[str],
        embeddings: np.ndarray,
        term_articles: Dict[str, List[str]],
        source_file: str = None,
        extra_metadata: Dict = None
    ):
        """
        Save cache files.
        
        Args:
            terms: List of terms
            embeddings: Array of embeddings, shape [len(terms), embedding_dim]
            term_articles: Dict mapping term → list of article_ids
            source_file: Source CSV file path
            extra_metadata: Additional metadata to save
        """
        if len(terms) != len(embeddings):
            raise ValueError(f"Length mismatch: {len(terms)} terms != {len(embeddings)} embeddings")
        
        print(f"Saving cache to {self.cache_dir}")
        
        # Save embeddings as compressed NumPy archive
        np.savez_compressed(
            self.embeddings_file,
            terms=np.array(terms, dtype=object),
            embeddings=embeddings.astype(np.float32)
        )
        print(f"  ✓ Saved {len(terms)} embeddings to {self.embeddings_file.name}")
        
        # Save term→articles mapping as pickle
        with open(self.mappings_file, 'wb') as f:
            pickle.dump(term_articles, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"  ✓ Saved {len(term_articles)} term mappings to {self.mappings_file.name}")
        
        # Save metadata
        metadata = {
            'version': self.CACHE_VERSION,
            'created_at': datetime.now().isoformat(),
            'num_terms': len(terms),
            'num_embeddings': len(embeddings),
            'embedding_dim': embeddings.shape[1],
            'source_file': source_file,
        }
        
        if extra_metadata:
            metadata.update(extra_metadata)
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ Saved metadata to {self.metadata_file.name}")
        
        print(f"Cache saved successfully: {len(terms)} terms, {embeddings.shape[1]} dims")
    
    def load(self) -> Tuple[List[str], np.ndarray, Dict[str, List[str]]]:
        """
        Load cache files.
        
        Returns:
            Tuple of (terms, embeddings, term_articles)
        """
        if not self.exists():
            raise FileNotFoundError("Cache files not found")
        
        print(f"Loading cache from {self.cache_dir}")
        
        # Load embeddings
        data = np.load(self.embeddings_file, allow_pickle=True)
        terms = data['terms'].tolist()
        embeddings = data['embeddings']
        print(f"  ✓ Loaded {len(terms)} embeddings from {self.embeddings_file.name}")
        
        # Load mappings
        with open(self.mappings_file, 'rb') as f:
            term_articles = pickle.load(f)
        print(f"  ✓ Loaded {len(term_articles)} term mappings from {self.mappings_file.name}")
        
        print(f"Cache loaded successfully: {len(terms)} terms, {embeddings.shape[1]} dims")
        
        return terms, embeddings, term_articles
    
    def load_metadata(self) -> Dict:
        """Load metadata from cache."""
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_file}")
        
        with open(self.metadata_file, 'r') as f:
            return json.load(f)
    
    def clear(self):
        """Delete all cache files."""
        files = [self.embeddings_file, self.mappings_file, self.metadata_file]
        for file in files:
            if file.exists():
                file.unlink()
                print(f"Deleted {file.name}")
        
        print("Cache cleared")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        if not self.exists():
            return {'exists': False}
        
        metadata = self.load_metadata()
        
        # Calculate file sizes
        embeddings_size = self.embeddings_file.stat().st_size / (1024 * 1024)  # MB
        mappings_size = self.mappings_file.stat().st_size / (1024 * 1024)  # MB
        total_size = embeddings_size + mappings_size
        
        return {
            'exists': True,
            'version': metadata.get('version'),
            'created_at': metadata.get('created_at'),
            'num_terms': metadata.get('num_terms'),
            'embedding_dim': metadata.get('embedding_dim'),
            'embeddings_size_mb': round(embeddings_size, 2),
            'mappings_size_mb': round(mappings_size, 2),
            'total_size_mb': round(total_size, 2),
            'source_file': metadata.get('source_file')
        }
