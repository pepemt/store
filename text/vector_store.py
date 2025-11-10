"""
Oracle 23ai Vector Store integration.

Provides vector similarity search using Oracle's native VECTOR type
and HNSW indexing for fast cosine similarity queries.
"""

import os
import json
import array
from typing import List, Dict, Tuple, Optional
import numpy as np
import oracledb


class OracleVectorStore:
    """Oracle 23ai Vector Search integration."""
    
    def __init__(
        self,
        user: str = None,
        password: str = None,
        dsn: str = None,
        wallet_location: str = None
    ):
        """
        Initialize Oracle Vector Store.

        Args:
            user: Database user (or from ORACLE_USER env)
            password: Database password (or from ORACLE_PASSWORD env)
            dsn: Database DSN (or from ORACLE_DSN env)
            wallet_location: Path to wallet directory (for Autonomous DB)
        """
        self.user = user or os.getenv("ORACLE_USER", "admin")
        self.password = password or os.getenv("ORACLE_PASSWORD")
        self.dsn = dsn or os.getenv("ORACLE_DSN")
        
        if not self.password:
            raise ValueError("Oracle password not provided (set ORACLE_PASSWORD env)")
        if not self.dsn:
            raise ValueError("Oracle DSN not provided (set ORACLE_DSN env)")
        
        # Setup wallet for Autonomous Database if provided
        if wallet_location:
            oracledb.init_oracle_client(
                config_dir=wallet_location
            )
        
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=self.dsn
            )
            print(f"Connected to Oracle Database: {self.dsn}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Oracle: {e}")
    
    def create_table(self, embedding_dim: int = 1536, drop_if_exists: bool = False):
        """
        Create term vectors table with VECTOR type.
        
        Args:
            embedding_dim: Dimension of embeddings (default: 1536 for Qwen3)
            drop_if_exists: Drop table if it exists
        """
        cursor = self.connection.cursor()
        
        try:
            if drop_if_exists:
                cursor.execute("DROP TABLE term_vectors CASCADE CONSTRAINTS")
                print("Dropped existing term_vectors table")
        except Exception:
            pass  # Table doesn't exist
        
        # Create table with VECTOR type
        create_table_sql = f"""
        CREATE TABLE term_vectors (
            term_id NUMBER PRIMARY KEY,
            term VARCHAR2(255) UNIQUE NOT NULL,
            embedding VECTOR({embedding_dim}, FLOAT32),
            article_ids CLOB NOT NULL,
            frequency NUMBER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_sql)
        print(f"Created term_vectors table (embedding_dim={embedding_dim})")
        
        # Create regular index for term lookups
        cursor.execute("CREATE INDEX term_lookup_idx ON term_vectors(term)")
        print("Created term lookup index")
        
        self.connection.commit()
        cursor.close()
    
    def create_vector_index(
        self,
        index_name: str = "term_emb_idx",
        target_accuracy: int = 95,
        neighbors: int = 40,
        drop_if_exists: bool = False
    ):
        """
        Create HNSW vector index for fast similarity search.
        
        Args:
            index_name: Name of the vector index
            target_accuracy: Target accuracy percentage (90-100)
            neighbors: Max neighbors per layer (HNSW M parameter)
            drop_if_exists: Drop index if it exists
        """
        cursor = self.connection.cursor()
        
        try:
            if drop_if_exists:
                cursor.execute(f"DROP INDEX {index_name}")
                print(f"Dropped existing index: {index_name}")
        except Exception:
            pass  # Index doesn't exist
        
        # Create HNSW index
        create_index_sql = f"""
        CREATE VECTOR INDEX {index_name}
        ON term_vectors(embedding)
        ORGANIZATION INMEMORY NEIGHBOR GRAPH
        DISTANCE COSINE
        WITH TARGET ACCURACY {target_accuracy}
        PARAMETERS (
            type HNSW,
            neighbors {neighbors}
        )
        """
        
        cursor.execute(create_index_sql)
        print(f"Created HNSW vector index: {index_name} (accuracy={target_accuracy}%)")
        
        self.connection.commit()
        cursor.close()
    
    def bulk_insert(
        self,
        terms: List[str],
        embeddings: np.ndarray,
        term_articles: Dict[str, List[str]],
        batch_size: int = 10000,
        clear_existing: bool = True
    ):
        """
        Bulk insert term embeddings.
        
        Args:
            terms: List of terms
            embeddings: Array of embeddings [len(terms), embedding_dim]
            term_articles: Dict mapping term → article_ids
            batch_size: Batch size for executemany
            clear_existing: Clear existing data before inserting
        """
        if len(terms) != len(embeddings):
            raise ValueError(f"Length mismatch: {len(terms)} != {len(embeddings)}")
        
        cursor = self.connection.cursor()
        
        # Clear existing data if requested
        if clear_existing:
            cursor.execute("DELETE FROM term_vectors")
            print("Cleared existing term vectors")
        
        # Prepare data for bulk insert
        data = []
        for i, term in enumerate(terms):
            # Convert embedding to array (required by oracledb)
            embedding_array = array.array('f', embeddings[i].tolist())
            
            # Get article IDs for this term (as JSON string)
            article_ids = term_articles.get(term, [])
            article_ids_json = json.dumps(article_ids)
            
            # Frequency is number of articles
            frequency = len(article_ids)
            
            data.append((
                i,  # term_id
                term,
                embedding_array,
                article_ids_json,
                frequency
            ))
        
        # Bulk insert with executemany
        insert_sql = """
        INSERT INTO term_vectors (term_id, term, embedding, article_ids, frequency)
        VALUES (:1, :2, :3, :4, :5)
        """
        
        print(f"Bulk inserting {len(data)} term vectors (batch_size={batch_size})...")
        cursor.executemany(insert_sql, data, batcherrors=True, batch_size=batch_size)
        
        # Check for errors
        errors = cursor.getbatcherrors()
        if errors:
            print(f"Warning: {len(errors)} errors during bulk insert")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  Row {error.offset}: {error.message}")
        
        self.connection.commit()
        cursor.close()
        
        print(f"Successfully inserted {len(data) - len(errors)} term vectors")
    
    def find_similar_terms(
        self,
        query_embedding: np.ndarray,
        top_k: int = 20,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, List[str], float]]:
        """
        Find similar terms using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of (term, article_ids, similarity_score) tuples
        """
        cursor = self.connection.cursor()
        
        # Convert embedding to array
        query_vec = array.array('f', query_embedding.tolist())
        
        # Query with cosine distance
        # Note: Cosine distance = 1 - cosine similarity
        # We convert to similarity for easier interpretation
        query_sql = """
        SELECT 
            term,
            article_ids,
            1 - VECTOR_DISTANCE(embedding, :query_vec, COSINE) as similarity
        FROM term_vectors
        WHERE 1 - VECTOR_DISTANCE(embedding, :query_vec, COSINE) >= :min_sim
        ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
        FETCH FIRST :top_k ROWS ONLY
        """
        
        cursor.execute(
            query_sql,
            query_vec=query_vec,
            top_k=top_k,
            min_sim=min_similarity
        )
        
        results = []
        for term, article_ids_json, similarity in cursor.fetchall():
            article_ids = json.loads(article_ids_json)
            results.append((term, article_ids, float(similarity)))
        
        cursor.close()
        return results
    
    def get_term_embedding(self, term: str) -> Optional[np.ndarray]:
        """
        Get embedding for a specific term.
        
        Args:
            term: Term to lookup
            
        Returns:
            Embedding vector or None if not found
        """
        cursor = self.connection.cursor()
        
        # Setup output type handler to convert VECTOR to list
        def output_type_handler(cursor, metadata):
            if metadata.type_code is oracledb.DB_TYPE_VECTOR:
                return cursor.var(
                    metadata.type_code,
                    arraysize=cursor.arraysize,
                    outconverter=list
                )
        
        self.connection.outputtypehandler = output_type_handler
        
        cursor.execute(
            "SELECT embedding FROM term_vectors WHERE term = :term",
            term=term
        )
        
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return np.array(result[0], dtype=np.float32)
        return None
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        cursor = self.connection.cursor()
        
        # Count terms
        cursor.execute("SELECT COUNT(*) FROM term_vectors")
        total_terms = cursor.fetchone()[0]
        
        # Get embedding dimension
        cursor.execute("""
            SELECT DBMS_VECTOR.vector_dimension(embedding) as dim
            FROM term_vectors
            WHERE ROWNUM = 1
        """)
        result = cursor.fetchone()
        embedding_dim = result[0] if result else None
        
        cursor.close()
        
        return {
            'total_terms': total_terms,
            'embedding_dim': embedding_dim
        }
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("Database connection closed")
