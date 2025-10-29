"""LLM configuration and initialization"""
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.rate_limiters import InMemoryRateLimiter


# Load environment variables
load_dotenv()


# Verify API key
if not os.getenv("GROQ_API_KEY"):
    raise ValueError(
        "GROQ_API_KEY not found. "
        "Copy .env.example to .env and add your API key."
    )


# Rate limiter for Groq free tier (30 RPM)
rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.48,
    check_every_n_seconds=0.1,
    max_bucket_size=30,
)


# LLM instance
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    rate_limiter=rate_limiter,
    temperature=0.7,
    max_retries=3,
)
