"""
Product term indexer - Main pipeline for indexing product terms.

Orchestrates the complete flow:
1. Read articles CSV
2. Extract terms from product fields
3. Generate embeddings for unique terms
4. Build term → article_ids mapping
5. Save to binary cache
6. Load into Oracle 23ai Vector Search
"""

import csv
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
import numpy as np

from .tokenizer import Tokenizer
from .embeddings import EmbeddingModel
from .cache import CacheManager
from .vector_store import OracleVectorStore


class ProductTermIndexer:
    """Pipeline for indexing product terms with embeddings."""
    
    # CSV columns to combine for term extraction
    PRODUCT_FIELDS = [
        'product_name',
        'prod_name',
        'product_type_name',
        'colour_group_name',
        'detail_desc',
        'graphical_appearance_name'
    ]
    
    def __init__(
        self,
        model_name: str = "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
        cache_dir: Path = None,
        use_cache: bool = True,
        use_gpu: bool = True
    ):
        """
        Initialize indexer.

        Args:
            model_name: HuggingFace model name (default: Qwen2-1.5B)
            cache_dir: Cache directory (default: text/.cache)
            use_cache: Whether to use cached embeddings
            use_gpu: Use GPU for embeddings
        """
        self.use_cache = use_cache

        # Initialize tokenizer
        self.tokenizer = Tokenizer(min_length=2, languages=['en', 'es'])

        # Initialize cache manager
        self.cache = CacheManager(cache_dir=cache_dir)

        # Initialize embedding model (lazy load)
        self._embedding_model = None
        self._model_name = model_name
        self._use_gpu = use_gpu

    @property
    def embedding_model(self) -> EmbeddingModel:
        """Lazy load embedding model."""
        if self._embedding_model is None:
            print("Loading embedding model...")
            self._embedding_model = EmbeddingModel(
                model_name=self._model_name,
                use_gpu=self._use_gpu
            )

        return self._embedding_model
    
    def extract_product_terms(self, article_row: Dict) -> List[str]:
        """
        Extract terms from a product article row.
        
        Args:
            article_row: Dict with product fields
            
        Returns:
            List of extracted terms
        """
        # Combine relevant fields
        field_values = []
        for field in self.PRODUCT_FIELDS:
            value = article_row.get(field, '')
            if value and isinstance(value, str):
                field_values.append(value)
        
        combined_text = ' '.join(field_values)
        
        # Extract terms
        terms = self.tokenizer.extract_terms(combined_text)
        
        return terms
    
    def process_csv(
        self,
        csv_path: str,
        article_id_field: str = 'article_id',
        sample_size: Optional[int] = None
    ) -> tuple[Dict[str, Set[str]], List[str]]:
        """
        Process articles CSV and build term→articles mapping.
        
        Args:
            csv_path: Path to articles CSV
            article_id_field: Column name for article ID
            sample_size: Optional: only process first N articles (for testing)
            
        Returns:
            Tuple of (term_articles, all_unique_terms)
            - term_articles: Dict mapping term → set of article_ids
            - all_unique_terms: List of all unique terms found
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        print(f"Processing articles from {csv_path.name}")
        
        # Build term → article_ids mapping
        term_articles: Dict[str, Set[str]] = defaultdict(set)
        articles_processed = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                article_id = row.get(article_id_field)
                if not article_id:
                    continue
                
                # Extract terms
                terms = self.extract_product_terms(row)
                
                # Map terms to article
                for term in terms:
                    term_articles[term].add(str(article_id))
                
                articles_processed += 1
                
                if articles_processed % 10000 == 0:
                    print(f"  Processed {articles_processed} articles, found {len(term_articles)} unique terms")
                
                # Stop if sample size reached
                if sample_size and articles_processed >= sample_size:
                    print(f"  Reached sample size limit: {sample_size}")
                    break
        
        print(f"Processed {articles_processed} articles")
        print(f"Found {len(term_articles)} unique terms")
        
        # Convert sets to sorted lists
        term_articles_lists = {
            term: sorted(list(articles))
            for term, articles in term_articles.items()
        }
        
        # Get sorted list of unique terms
        all_terms = sorted(list(term_articles.keys()))
        
        return term_articles_lists, all_terms
    
    def generate_embeddings(
        self,
        terms: List[str],
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for terms.
        
        Args:
            terms: List of terms to embed
            show_progress: Show progress bar
            
        Returns:
            Array of embeddings [len(terms), embedding_dim]
        """
        print(f"Generating embeddings for {len(terms)} terms...")
        embeddings = self.embedding_model.embed_batch(terms, show_progress=show_progress)
        print(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def index_from_csv(
        self,
        csv_path: str,
        force_rebuild: bool = False,
        upload_to_oracle: bool = True,
        sample_size: Optional[int] = None
    ):
        """
        Complete indexing pipeline from CSV to Oracle.
        
        Args:
            csv_path: Path to articles CSV
            force_rebuild: Force rebuild even if cache exists
            upload_to_oracle: Upload to Oracle 23ai after processing
            sample_size: Optional: only process first N articles (for testing)
        """
        csv_path = Path(csv_path)
        
        # Check cache
        if self.use_cache and not force_rebuild and self.cache.is_valid():
            print("Valid cache found, loading from cache...")
            terms, embeddings, term_articles = self.cache.load()
        else:
            print("Building index from scratch...")
            
            # Step 1: Process CSV and extract terms
            term_articles, terms = self.process_csv(
                csv_path,
                sample_size=sample_size
            )
            
            # Step 2: Generate embeddings
            embeddings = self.generate_embeddings(terms, show_progress=True)
            
            # Step 3: Save to cache
            if self.use_cache:
                self.cache.save(
                    terms=terms,
                    embeddings=embeddings,
                    term_articles=term_articles,
                    source_file=str(csv_path),
                    extra_metadata={
                        'sample_size': sample_size,
                        'num_articles_total': sum(len(articles) for articles in term_articles.values())
                    }
                )
        
        # Step 4: Upload to Oracle if requested
        if upload_to_oracle:
            print("\nUploading to Oracle 23ai...")
            self.upload_to_oracle(terms, embeddings, term_articles)
        
        print("\n✓ Indexing complete!")
        print(f"  Total terms: {len(terms)}")
        print(f"  Embedding dimension: {embeddings.shape[1]}")
        print(f"  Total term-article associations: {sum(len(articles) for articles in term_articles.values())}")
    
    def upload_to_oracle(
        self,
        terms: List[str],
        embeddings: np.ndarray,
        term_articles: Dict[str, List[str]],
        create_table: bool = True,
        create_index: bool = True
    ):
        """
        Upload terms and embeddings to Oracle 23ai.
        
        Args:
            terms: List of terms
            embeddings: Array of embeddings
            term_articles: Dict mapping term → article_ids
            create_table: Create table if it doesn't exist
            create_index: Create vector index after loading
        """
        # Initialize Oracle store
        store = OracleVectorStore()
        
        try:
            # Create table if needed
            if create_table:
                embedding_dim = embeddings.shape[1]
                store.create_table(
                    embedding_dim=embedding_dim,
                    drop_if_exists=True
                )
            
            # Bulk insert
            store.bulk_insert(
                terms=terms,
                embeddings=embeddings,
                term_articles=term_articles,
                batch_size=10000,
                clear_existing=True
            )
            
            # Create vector index if needed
            if create_index:
                store.create_vector_index(
                    drop_if_exists=True,
                    target_accuracy=95
                )
            
            # Show stats
            stats = store.get_stats()
            print(f"\nOracle Vector Store Stats:")
            print(f"  Total terms: {stats['total_terms']}")
            print(f"  Embedding dimension: {stats['embedding_dim']}")
            
        finally:
            store.close()
