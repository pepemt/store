"""LLM configuration and initialization"""
import os
from dotenv import load_dotenv
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain_core.rate_limiters import InMemoryRateLimiter
import oci


# Load environment variables
load_dotenv()


# Rate limiter for OCI Generative AI (more generous than Groq free tier)
# OCI on-demand has higher limits, adjusting to reasonable defaults
rate_limiter = InMemoryRateLimiter(
    requests_per_second=5.0,  # 300 RPM (much higher than Groq's 30 RPM)
    check_every_n_seconds=0.1,
    max_bucket_size=100,
)


# Load OCI config from default profile
# This uses the same authentication as Terraform
try:
    config = oci.config.from_file(profile_name="DEFAULT")
except Exception as e:
    raise ValueError(
        f"Failed to load OCI config: {e}\n"
        "Make sure ~/.oci/config exists with valid credentials."
    )


# LLM instance using OCI Generative AI
llm = ChatOCIGenAI(
    model_id=os.getenv("OCI_GENAI_MODEL_ID"),
    service_endpoint=os.getenv("OCI_GENAI_ENDPOINT"),
    compartment_id=os.getenv("OCI_GENAI_COMPARTMENT_ID"),
    auth_type="API_KEY",
    auth_profile="DEFAULT",
    model_kwargs={
        "temperature": 0.7,
        "max_tokens": 2000,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
    # Rate limiter to prevent hitting API limits
    rate_limiter=rate_limiter,
)
