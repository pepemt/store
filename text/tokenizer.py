"""
Tokenizer for extracting and normalizing terms from product text.

Based on Watson's tokenization strategy:
- Split on whitespace and punctuation
- Preserve acronyms (e.g., A.I., M.L.)
- Filter stopwords (Spanish and English)
- Validate term quality
"""

import re
from typing import List, Set
from stop_words import get_stop_words


class Tokenizer:
    """Extract and normalize terms from text."""
    
    # Punctuation to split on (excluding dots for acronyms)
    SPLIT_PATTERN = r'[,;:!?"\'()\[\]{}\\/|<>=+*&%$#@~\s]+'
    
    # Patterns for acronym detection
    ACRONYM_ALL_CAPS = re.compile(r'^[A-Z]{2,}$')  # AI, ML, CPU
    ACRONYM_WITH_DOTS = re.compile(r'^[A-Z](?:\.[A-Z])+\.?$')  # A.I., M.L.
    
    def __init__(self, min_length: int = 2, languages: List[str] = None):
        """
        Initialize tokenizer.
        
        Args:
            min_length: Minimum term length (default: 2)
            languages: Stopword languages (default: ['en', 'es'])
        """
        self.min_length = min_length
        
        # Load stopwords for multiple languages
        if languages is None:
            languages = ['en', 'es']
        
        self.stopwords: Set[str] = set()
        for lang in languages:
            try:
                self.stopwords.update(get_stop_words(lang))
            except Exception as e:
                print(f"Warning: Could not load stopwords for {lang}: {e}")
        
        # Add common product-specific stopwords
        self.stopwords.update([
            'item', 'product', 'new', 'sale', 'size', 'color',
            'tipo', 'producto', 'nuevo', 'oferta', 'talla', 'color',
        ])
    
    def is_acronym(self, token: str) -> bool:
        """Check if token is an acronym."""
        return bool(
            self.ACRONYM_ALL_CAPS.match(token) or 
            self.ACRONYM_WITH_DOTS.match(token)
        )
    
    def normalize_term(self, term: str) -> str:
        """Normalize a term (lowercase, remove dots from acronyms)."""
        # Remove dots from acronyms (A.I. -> ai)
        if '.' in term:
            term = term.replace('.', '')
        
        # Convert to lowercase
        return term.lower()
    
    def is_valid_term(self, term: str) -> bool:
        """
        Check if a term is valid.
        
        Valid terms must:
        - Be at least min_length characters
        - Contain at least one alphanumeric character
        - Not be purely numeric
        - Not be a stopword
        """
        # Check length
        if len(term) < self.min_length:
            return False
        
        # Must contain at least one alphanumeric
        if not any(c.isalnum() for c in term):
            return False
        
        # Reject pure numbers
        if term.isdigit():
            return False
        
        # Check stopwords
        if term in self.stopwords:
            return False
        
        return True
    
    def extract_terms(self, text: str) -> List[str]:
        """
        Extract unique terms from text.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            Sorted list of unique valid terms
        """
        if not text:
            return []
        
        # Split on whitespace and most punctuation
        raw_tokens = re.split(self.SPLIT_PATTERN, text)
        
        terms = set()
        for token in raw_tokens:
            if not token:
                continue
            
            # Preserve acronyms (don't normalize yet if it's an acronym)
            if self.is_acronym(token):
                normalized = self.normalize_term(token)
                if self.is_valid_term(normalized):
                    terms.add(normalized)
            else:
                # Normal word processing
                normalized = self.normalize_term(token)
                if self.is_valid_term(normalized):
                    terms.add(normalized)
        
        # Return sorted list for consistency
        return sorted(list(terms))
    
    def extract_terms_from_product(
        self,
        product_name: str = "",
        prod_name: str = "",
        product_type: str = "",
        colour: str = "",
        detail_desc: str = "",
        graphical_appearance: str = ""
    ) -> List[str]:
        """
        Extract terms from product fields.
        
        Combines multiple product fields and extracts unique terms.
        
        Args:
            product_name: Main product name
            prod_name: Short product name
            product_type: Product type/category
            colour: Color description
            detail_desc: Detailed description
            graphical_appearance: Graphical appearance description
            
        Returns:
            Sorted list of unique terms
        """
        # Combine all fields with spaces
        combined = " ".join(filter(None, [
            product_name,
            prod_name,
            product_type,
            colour,
            detail_desc,
            graphical_appearance
        ]))
        
        return self.extract_terms(combined)
