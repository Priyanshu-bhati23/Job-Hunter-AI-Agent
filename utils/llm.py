# utils/llm.py
"""
LLM abstraction layer
Primary:  OpenAI (GPT-4o / GPT-4o-mini)
Fallback: Ollama (Mistral / Llama3 - free local)
"""

import os
from typing import Optional
from loguru import logger

from config.settings import LLM_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL, OLLAMA_MODEL


def get_llm(provider: Optional[str] = None):
    """
    Returns a LangChain-compatible LLM based on config.
    Falls back gracefully if primary is unavailable.
    """
    provider = provider or LLM_PROVIDER

    # ── OpenAI (Primary) ──────────────────────────────────
    if provider == "openai" and OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            logger.info(f"Using OpenAI ({OPENAI_MODEL}) as LLM")
            return ChatOpenAI(
                model=OPENAI_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as e:
            logger.warning(f"OpenAI unavailable: {e}. Falling back to Ollama.")

    # ── Ollama Fallback (free/local) ──────────────────────
    try:
        from langchain_community.chat_models import ChatOllama
        logger.info(f"Using Ollama ({OLLAMA_MODEL}) as LLM fallback")
        return ChatOllama(
            model=OLLAMA_MODEL,
            temperature=0.3,
        )
    except Exception as e:
        logger.error(f"Ollama also unavailable: {e}")
        raise RuntimeError(
            "No LLM available. Check OPENAI_API_KEY in .env or install Ollama."
        )


def get_embeddings():
    """
    Returns OpenAI embeddings if API key set,
    else free HuggingFace sentence-transformers.
    """
    if OPENAI_API_KEY:
        try:
            from langchain_openai import OpenAIEmbeddings
            logger.info("Using OpenAI text-embedding-3-small")
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=OPENAI_API_KEY,
            )
        except Exception as e:
            logger.warning(f"OpenAI embeddings failed: {e}. Using HuggingFace.")

    # Free fallback
    from langchain_community.embeddings import HuggingFaceEmbeddings
    logger.info("Using HuggingFace sentence-transformers (free fallback)")
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def call_llm(prompt: str, system: str = "", provider: Optional[str] = None) -> str:
    """Simple wrapper to call LLM and get string response"""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm(provider)
    messages = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return response.content
