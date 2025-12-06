# Zenith Store

Plataforma de e-commerce full-stack con asistente de inteligencia artificial integrado, sistema de recomendaciones basado en machine learning y busqueda semantica de productos. Desplegable en Oracle Cloud Infrastructure.

## Tabla de Contenidos

- [Caracteristicas](#caracteristicas)
- [Tecnologias](#tecnologias)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Requisitos Previos](#requisitos-previos)
- [Instalacion](#instalacion)
- [Configuracion](#configuracion)
- [Ejecucion](#ejecucion)
- [Despliegue en Produccion](#despliegue-en-produccion)
- [Infraestructura con Terraform](#infraestructura-con-terraform)
- [API Endpoints](#api-endpoints)
- [Arquitectura](#arquitectura)
- [Licencia](#licencia)

## Caracteristicas

### E-Commerce

- Catalogo de productos con filtros y busqueda
- Carrito de compras persistente
- Proceso de checkout con integracion Stripe
- Historial de pedidos
- Sistema de resenas y calificaciones
- Autenticacion JWT

### Inteligencia Artificial

- Asistente conversacional en tiempo real via WebSocket
- Busqueda semantica de productos y resenas
- Descubrimiento de productos basado en imagenes (Llama 3.2 Vision)
- Transcripcion de audio (Speech-to-Text con faster-whisper)
- Modelos: xAI Grok 4 y Meta Llama 3.2 Vision via OCI Generative AI

### Machine Learning

- Recomendaciones personalizadas con algoritmo ALS (Alternating Least Squares)
- Analisis de sentimiento en resenas
- Embeddings de texto y vectores para busqueda semantica
- Tracking de experimentos con MLflow

## Tecnologias

### Frontend

| Tecnologia | Version |
|------------|---------|
| React | 19 |
| TypeScript | 5.6 |
| Vite | 7 |
| Tailwind CSS | 4 |
| React Router | 7 |
| React Query | 5 |
| Framer Motion | 11 |

### Backend

| Tecnologia | Version |
|------------|---------|
| Python | 3.11+ |
| FastAPI | 0.115 |
| SQLAlchemy | 2.0 |
| Pydantic | 2.10 |
| Uvicorn | 0.34 |

### IA y Machine Learning

| Tecnologia | Uso |
|------------|-----|
| LangGraph | Orquestacion multi-agente |
| LangChain | Framework de IA |
| MLflow | Gestion del ciclo de vida ML |
| PySpark | Procesamiento distribuido |
| FAISS | Busqueda vectorial local |
| OCI Generative AI | Modelos Grok 4 y Llama 3.2 Vision |

### Bases de Datos

- PostgreSQL 14 (base de datos transaccional)
- Oracle Autonomous Database 23ai (busqueda vectorial con AI Vector Search)

### Infraestructura

- Docker con multi-stage build
- Docker Compose para servicios locales
- Terraform para Oracle Cloud Infrastructure
- MinIO (desarrollo local) / OCI Object Storage (produccion)
- Tailscale para acceso seguro al bastion

## Estructura del Proyecto

```
store/
    api/                        # Backend FastAPI
        src/
            routes/             # Endpoints de la API
            agents/             # Sistema multi-agente LangGraph
                nodes/          # Nodos del grafo (search, chat, etc.)
                tools/          # Herramientas de agentes
                orchestrator.py # Logica principal del agente
                graph.py        # Construccion del grafo
            main.py             # Punto de entrada
    app/                        # Frontend React
        src/
            pages/              # Componentes de pagina
            components/         # Componentes reutilizables
            services/           # Clientes API
            context/            # Contextos React (Auth, Cart, Chat)
            hooks/              # Hooks personalizados
    database/                   # Modelos SQLAlchemy
        models.py               # Article, Customer, Transaction, Order, Review
        lib.py                  # Conexion a base de datos
    ML/                         # Modelos de Machine Learning
        src/                    # Entrenamiento y serving
    text/                       # Procesamiento de texto
        embeddings.py           # Generacion de embeddings
        vector_store.py         # Base de datos vectorial
        indexer.py              # Indexacion
    images/                     # Procesamiento de imagenes
        vector_image.py         # Embeddings de imagenes
    sentimentAnalysis/          # Analisis de sentimiento
    initialization/             # Scripts de inicializacion de BD
    docs/                       # Diagramas de arquitectura (.drawio)
    ssh-keys/                   # Claves SSH generadas por Terraform
    .data/                      # Datos locales (wallets, minio)
    Dockerfile                  # Build multi-stage
    docker-compose.dev.yaml     # Servicios de desarrollo
    docker-entrypoint.sh        # Script de entrada Docker
    dev.sh                      # Script de desarrollo local
    main.tf                     # Infraestructura Terraform
    variables.tf                # Variables Terraform
    pyproject.toml              # Configuracion Python (uv workspace)
    uv.lock                     # Lock de dependencias
```

## Requisitos Previos

- Python 3.11 o superior
- Node.js 18 o superior
- uv (gestor de paquetes Python)
- pnpm (gestor de paquetes Node.js)
- Docker y Docker Compose
- Stripe CLI (para webhooks en desarrollo)
- OCI CLI (para despliegue en nube)
- Terraform 1.5+ (para infraestructura)

## Instalacion

### 1. Clonar el repositorio

```bash
git clone https://github.com/pepemt/store.git
cd store
```

### 2. Configurar variables de entorno

```bash
cp .env.sample .env
```

Editar el archivo `.env` con las credenciales correspondientes.

### 3. Instalar dependencias de Python

```bash
uv sync
```

### 4. Instalar dependencias del frontend

```bash
cd app
pnpm install
cd ..
```

### 5. Iniciar servicios auxiliares

```bash
docker compose -f docker-compose.dev.yaml up -d
```

Esto inicia MinIO (almacenamiento S3) y MLflow (tracking ML).

## Configuracion

### Variables de Entorno Principales

```env
# PostgreSQL
STORE_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/store

# JWT
JWT_SECRET=your-secret-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OCI Generative AI
OCI_GENAI_ENDPOINT=https://inference.generativeai.us-chicago-1.oci.oraclecloud.com
OCI_GENAI_COMPARTMENT_ID=ocid1.compartment...
OCI_GENAI_MODEL_ID=xai.grok-4-fast-non-reasoning
OCI_GENAI_VISION_MODEL_ID=meta.llama-3.2-90b-vision-instruct

# Oracle Autonomous Database (Vector Search)
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your-password
ORACLE_DSN=storedb_high
ORACLE_WALLET_LOCATION=.data/adb-wallet

# MinIO / S3
STORE_S3_ENDPOINT_URL=http://localhost:9000
STORE_S3_ACCESS_KEY_ID=minioadmin
STORE_S3_SECRET_ACCESS_KEY=minioadmin
STORE_S3_BUCKET=store

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
```

Ver `.env.sample` para la lista completa de variables.

## Ejecucion

### Desarrollo con Script Automatizado

El script `dev.sh` inicia todos los servicios necesarios:

```bash
./dev.sh
```

Este script:
1. Establece tunel SSH hacia la infraestructura en OCI
2. Inicia Stripe webhook listener (actualiza automaticamente STRIPE_WEBHOOK_SECRET)
3. Inicia el backend FastAPI
4. Inicia el frontend React

Presionar Ctrl+C para detener todos los servicios.

### Desarrollo Manual

Terminal 1 - Servicios Docker:

```bash
docker compose -f docker-compose.dev.yaml up -d
```

Terminal 2 - Backend:

```bash
uv run api
```

Terminal 3 - Frontend:

```bash
cd app && pnpm dev
```

Terminal 4 - Stripe webhooks:

```bash
stripe listen --forward-to localhost:8000/api/v1/checkout/webhook
```

### URLs de Desarrollo

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Documentacion API | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| MLflow UI | http://localhost:5000 |

## Despliegue en Produccion

### Docker Build

El Dockerfile usa multi-stage build optimizado:

```bash
docker build -t zenith-store .
```

El build:
1. Stage 1: Compila frontend React con Vite
2. Stage 2: Instala dependencias Python con uv
3. Stage 3: Imagen final optimizada con el frontend embebido

### Docker Run

```bash
docker run -d \
  --name zenith-store \
  -p 8000:8000 \
  -v /path/to/.oci:/root/.oci:ro \
  -v /path/to/adb-wallet:/app/.data/adb-wallet:ro \
  --env-file .env.prod \
  zenith-store
```

### Docker Compose (Desarrollo Completo)

```bash
docker compose -f docker-compose.dev.yaml up --build
```

Servicios incluidos:
- MinIO (S3-compatible storage)
- MLflow Server (con PostgreSQL backend)
- Bucket creation automático

## Infraestructura con Terraform

El archivo `main.tf` despliega la infraestructura completa en OCI:

### Recursos Creados

**Networking:**
- VCN (10.0.0.0/16)
- Subnet publica (bastion)
- Subnet privada (bases de datos)
- Internet Gateway, NAT Gateway, Service Gateway
- Security Lists y Network Security Groups

**Compute:**
- Bastion Host (VM.Standard.A1.Flex, 8 OCPUs, 48GB RAM)
  - Oracle Linux 8
  - Docker preinstalado
  - Tailscale para VPN
  - Cliente PostgreSQL

**Bases de Datos:**
- PostgreSQL Database System (OCI managed)
  - Version 14.17
  - Backups automaticos semanales
- Oracle Autonomous Database 23ai
  - AI Vector Search habilitado
  - mTLS requerido (wallet)

**Storage:**
- Object Storage bucket (S3-compatible)
- MLflow artifacts bucket
- Credenciales S3 generadas automaticamente

### Desplegar Infraestructura

```bash
# Inicializar Terraform
terraform init

# Ver plan de ejecucion
terraform plan

# Aplicar cambios
terraform apply
```

### Obtener Credenciales

```bash
# IP del bastion
terraform output bastion_public_ip

# Password de PostgreSQL
terraform output postgresql_admin_password

# Password de Oracle ADB
terraform output adb_admin_password

# Credenciales S3
terraform output s3_credentials_summary

# Comando SSH tunnel completo
terraform output ssh_tunnel_command
```

### Conexion via Bastion

```bash
# SSH tunnel para acceder a los servicios privados
ssh -i ./ssh-keys/private.pem \
    -L 5432:<POSTGRESQL_IP>:5432 \
    -L 1522:adb.us-chicago-1.oraclecloud.com:1522 \
    -N opc@<BASTION_IP>
```

## API Endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | /api/v1/auth/login | Iniciar sesion |
| POST | /api/v1/auth/signup | Registrar usuario |
| GET | /api/v1/products | Listar productos |
| GET | /api/v1/products/{id} | Detalle de producto |
| GET | /api/v1/cart | Obtener carrito |
| POST | /api/v1/cart | Agregar al carrito |
| DELETE | /api/v1/cart/{id} | Eliminar del carrito |
| POST | /api/v1/checkout | Procesar pago |
| GET | /api/v1/orders | Historial de pedidos |
| WS | /api/v1/chat | Chat con asistente IA |
| GET | /api/v1/recommendations | Recomendaciones personalizadas |
| GET | /api/v1/reviews/{product_id} | Resenas de producto |
| POST | /api/v1/reviews | Crear resena |
| GET | /api/v1/landing | Datos de pagina principal |
| POST | /transcribe | Transcripcion de audio |
| POST | /api/v1/images/upload | Subir imagen de producto |

Documentacion interactiva: `/docs` (Swagger UI) o `/redoc` (ReDoc).

## Arquitectura

### Componentes Principales

- **API Gateway**: FastAPI como punto de entrada
- **Sistema Multi-Agente**: LangGraph para orquestacion de agentes de IA
  - Nodo de busqueda de productos
  - Nodo de busqueda semantica
  - Nodo de chat conversacional
  - Nodo de analisis de resenas
  - Nodo de vision (imagenes)
- **Capa de Datos**: SQLAlchemy ORM con PostgreSQL
- **Busqueda Vectorial**: FAISS (local) y Oracle AI Vector Search (produccion)
- **Cache**: Sistema de cache para metadatos y landing page
- **Almacenamiento**: OCI Object Storage / MinIO para imagenes
- **ML Pipeline**: PySpark + MLflow para recomendaciones ALS

### Diagramas

Los diagramas de arquitectura se encuentran en `/docs`:

- `architecture-diagram.drawio` - Arquitectura general del sistema
- `multiagent-architecture.drawio` - Sistema de agentes LangGraph
- `ml-recommendations-system.drawio` - Pipeline de recomendaciones
- `infrastructure-diagram.drawio` - Infraestructura en OCI

## Licencia

Este proyecto es privado y propietario.
