# Text Module - Semantic Product Search

Sistema de búsqueda semántica basado en términos para productos, inspirado en la arquitectura de Watson.

## Características

- **Vectorización de términos**: Usa Qwen3 (ONNX) para generar embeddings
- **Oracle 23ai Vector Search**: Almacenamiento y búsqueda de vectores nativa
- **Cache binario**: Guarda términos y vectores en `.npz`/`.pkl` para carga rápida
- **Búsqueda semántica**: Expande queries con términos similares
- **Integración LangGraph**: Herramienta disponible para el agente

## Arquitectura

```
text/
├── tokenizer.py        # Extracción y normalización de términos
├── embeddings.py       # Modelo sentence-transformers (Qwen3)
├── cache.py            # Cache binario (NumPy + Pickle)
├── vector_store.py     # Oracle 23ai Vector Search
├── indexer.py          # Pipeline completo
└── .cache/             # Cache binario
    ├── terms_embeddings.npz
    ├── term_articles.pkl
    └── metadata.json
```

## Setup

### 1. Instalar dependencias

```bash
cd /Users/albertovelazquez/Documents/Github/store
uv sync
```

**Nota**: El modelo se descarga automáticamente de HuggingFace la primera vez que ejecutas el indexer. No necesitas descargarlo manualmente.

### 2. Configurar Oracle 23ai

Asegúrate de tener estas variables de entorno en `.env`:

```bash
# Oracle 23ai connection (via SSH tunnel)
ORACLE_USER=admin
ORACLE_PASSWORD=5%40SoTmD_lDJ3cY8L
ORACLE_DSN=localhost:1522/storedb_high

# For Autonomous Database with wallet
# ORACLE_WALLET_LOCATION=/path/to/wallet
```

### 4. Abrir SSH tunnel

```bash
ssh -i ./ssh-keys/private.pem \
    -L 5432:10.0.2.182:5432 \
    -L 1522:adb.us-chicago-1.oraclecloud.com:1522 \
    -N opc@170.9.237.37
```

## Uso

### Indexar productos (una sola vez)

```bash
# Opción 1: Durante initialization
uv run initialization

# Opción 2: Ejecutar indexer directamente
cd text
python -m indexer ../.data/raw/articles.csv
```

**Primera ejecución (sin cache)**:
- Lee articles.csv
- Extrae términos de cada producto
- Genera embeddings (puede tardar ~30 min para 100K productos)
- Guarda cache binario
- Carga a Oracle 23ai

**Ejecuciones siguientes (con cache)**:
- Detecta cache válido
- Carga directamente desde `.npz`/`.pkl` (< 1 minuto)
- Inserta a Oracle 23ai

### Búsqueda semántica en API

La búsqueda semántica se integra automáticamente en el flujo del agente:

```python
# El agente usa semantic_product_search automáticamente
# cuando el usuario hace una búsqueda

# Ejemplo de query:
User: "quiero pantalones negros"

# Pipeline interno:
# 1. Extrae términos: ["pantalones", "negros"]
# 2. Vectoriza cada término
# 3. Busca términos similares en Oracle:
#    - "pantalones" → ["jeans", "trousers", "pants", ...]
#    - "negros" → ["black", "dark", "negro", ...]
# 4. Agrega article_ids de términos similares
# 5. Rankea por relevancia (similarity score)
# 6. Retorna top 10 productos
```

## Comandos útiles

### Ver estadísticas de cache

```python
from text.cache import CacheManager

cache = CacheManager()
if cache.exists():
    stats = cache.get_stats()
    print(stats)
    # {
    #   'num_terms': 15432,
    #   'embedding_dim': 1536,
    #   'total_size_mb': 125.3,
    #   'created_at': '2025-11-10T04:30:00'
    # }
```

### Forzar re-indexación

```python
from text.indexer import ProductTermIndexer

indexer = ProductTermIndexer(use_cache=False)
indexer.index_from_csv(
    csv_path=".data/raw/articles.csv",
    force_rebuild=True
)
```

### Limpiar cache

```python
from text.cache import CacheManager

cache = CacheManager()
cache.clear()
```

### Búsqueda manual

```python
from text.vector_store import OracleVectorStore
from text.embeddings import EmbeddingModel

# Conectar a Oracle
store = OracleVectorStore()

# Cargar modelo (descarga automáticamente si es necesario)
model = EmbeddingModel(
    model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct",
    use_gpu=True
)

# Buscar
query_embedding = model.embed("pantalones")
results = store.find_similar_terms(query_embedding, top_k=20)

for term, article_ids, similarity in results:
    print(f"{term}: {similarity:.3f} - {len(article_ids)} productos")

store.close()
```

## Ventajas del diseño

✅ **Cache binario** - Evita re-vectorización (muy rápido)  
✅ **Oracle 23ai** - Permite eliminar/recargar DB sin perder datos  
✅ **Términos vs documentos** - Más flexible que embeddings completos  
✅ **Expansión automática** - Encuentra términos similares  
✅ **Fallback inteligente** - Si falla, usa búsqueda literal  
✅ **Integración natural** - Herramienta transparente para el agente  

## Troubleshooting

### Error: "Could not download model"
```bash
# Si la descarga automática falla, descarga manualmente:
huggingface-cli download Alibaba-NLP/gte-Qwen2-1.5B-instruct

# O configura un proxy si estás detrás de un firewall
export HF_ENDPOINT=https://hf-mirror.com
```

### Error: "Could not connect to Oracle"
```bash
# Verifica que el SSH tunnel esté activo
ps aux | grep "ssh.*1522"

# Verifica variables de entorno
echo $ORACLE_PASSWORD
```

### Error: "Cache too old"
```bash
# Limpia y regenera cache
python -c "from text.cache import CacheManager; CacheManager().clear()"
uv run initialization
```

### Búsqueda semántica muy lenta
```bash
# Verifica que GPU esté disponible
python -c "import torch; print(torch.cuda.is_available())"
# Debe retornar True

# Si no hay GPU, el modelo usa CPU (más lento pero funciona)
# Para instalar soporte CUDA:
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

## Próximos pasos

- [ ] Agregar soporte para actualizaciones incrementales
- [ ] Implementar re-ranking con BM25
- [ ] Agregar filtros adicionales (precio, stock)
- [ ] Optimizar batch size para diferentes GPUs
- [ ] Implementar métricas de calidad de búsqueda

## Referencias

- [Watson codebase](https://github.com/user/watson) - Arquitectura original
- [Qwen3 model](https://huggingface.co/Alibaba-NLP/gte-Qwen2-1.5B-instruct)
- [Oracle 23ai Vector Search](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/)
