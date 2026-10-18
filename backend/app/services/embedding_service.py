import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculates cosine similarity between two float vectors.
    Safely handles zero vectors, empty vectors, and non-finite values.
    Strictly bounded in [0.0, 1.0].
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = 0.0
    sum_a = 0.0
    sum_b = 0.0

    for a, b in zip(vec_a, vec_b):
        if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
            continue
        dot_product += a * b
        sum_a += a * a
        sum_b += b * b

    norm_a = math.sqrt(sum_a)
    norm_b = math.sqrt(sum_b)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot_product / (norm_a * norm_b)
    if math.isnan(sim) or math.isinf(sim):
        return 0.0

    return max(0.0, min(1.0, float(sim)))


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def create_embedding(self, text: str) -> List[float]:
        """Generates embedding vector for input text."""
        pass

    @abstractmethod
    def calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        """Calculates semantic similarity between two text snippets (0.0 to 1.0)."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if provider is reachable."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Returns provider and model metadata."""
        pass


class LightweightLocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Fast, deterministic, zero-dependency lexical subword vectorizer.
    
    CAPABILITIES & INTENDED USE:
    - Computes character 3-gram and word-level feature vectors using deterministic MD5 hash buckets.
    - Captures surface lexical similarity, common typographical variants, and morphological overlap.
    - Runs 100% offline with zero GPU, PyTorch, or HuggingFace dependency.
    - Safe startup without cold-start model weight downloads.
    
    LIMITATIONS & FAIRNESS BOUNDARIES:
    - This provider is a lexical/subword token heuristic, NOT a deep transformer neural embedding model.
    - It CANNOT infer deep semantic equivalences between non-overlapping vocabularies.
    - In accordance with HireLens rules, similarity values from this provider serve solely as an
      assistance/retrieval signal and must NEVER independently establish skill qualification.
    """

    DIMENSIONS = 128

    def __init__(self, model_name: str = "hirelens-subword-v1"):
        self.model_name = model_name

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s#+.]", " ", text.lower())
        tokens = [t.strip() for t in cleaned.split() if t.strip()]
        # Add character 3-grams for typo & morphology tolerance
        subwords = []
        for tok in tokens:
            subwords.append(tok)
            if len(tok) >= 4:
                for i in range(len(tok) - 2):
                    subwords.append(tok[i : i + 3])
        return subwords

    def create_embedding(self, text: str) -> List[float]:
        vec = [0.0] * self.DIMENSIONS
        if not text or not text.strip():
            return vec

        tokens = self._tokenize(text)
        if not tokens:
            return vec

        for token in tokens:
            # Deterministic, cross-process stable MD5 bucket hash (immune to PYTHONHASHSEED)
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.DIMENSIONS
            vec[h] += 1.0

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    def calculate_similarity(self, vector_a: List[float], vector_b: List[float]) -> float:
        return cosine_similarity(vector_a, vector_b)

    def calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0

        clean_a = text_a.strip().lower()
        clean_b = text_b.strip().lower()

        if not clean_a or not clean_b:
            return 0.0

        if clean_a == clean_b:
            return 1.0

        # Whole-word token set matching (prevents false positives like "go" in "algorithm")
        words_a = set(re.findall(r"\b\w+\b", clean_a))
        words_b = set(re.findall(r"\b\w+\b", clean_b))

        if words_a and words_b:
            intersection = words_a.intersection(words_b)
            if intersection:
                jaccard = len(intersection) / len(words_a.union(words_b))
                if words_a.issubset(words_b) or words_b.issubset(words_a):
                    # Subphrase match on whole words
                    return max(0.85, float(jaccard))

        vec_a = self.create_embedding(text_a)
        vec_b = self.create_embedding(text_b)
        return self.calculate_similarity(vec_a, vec_b)

    def health_check(self) -> bool:
        return True

    def get_model_info(self) -> Dict[str, Any]:

        return {
            "provider": "lightweight_local",
            "model_name": self.model_name,
            "dimensions": self.DIMENSIONS,
            "status": "OPERATIONAL",
        }


class HostedEmbeddingProvider(BaseEmbeddingProvider):
    """
    Hosted embedding provider for production (OpenAI-compatible or hosted BAAI/bge-m3).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.base_url = (base_url or getattr(settings, "EMBEDDING_BASE_URL", None) or getattr(settings, "HOSTED_AI_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or getattr(settings, "EMBEDDING_API_KEY", None) or getattr(settings, "HOSTED_AI_API_KEY", "")
        self.model_name = model_name or getattr(settings, "EMBEDDING_MODEL", None) or "BAAI/bge-m3"
        self.timeout = timeout
        self._fallback = LightweightLocalEmbeddingProvider()

    def health_check(self) -> bool:
        if not self.base_url:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/models", headers=headers)
                return res.status_code == 200
        except Exception:
            return False

    def create_embedding(self, text: str) -> List[float]:
        if not self.base_url:
            return self._fallback.create_embedding(text)

        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={"input": text, "model": self.model_name},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["data"][0]["embedding"]
        except Exception:
            pass
        return self._fallback.create_embedding(text)

    def calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        vec_a = self.create_embedding(text_a)
        vec_b = self.create_embedding(text_b)
        return cosine_similarity(vec_a, vec_b)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "hosted_embedding",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "status": "OPERATIONAL" if self.health_check() else "FALLBACK_LOCAL",
        }


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider_type = getattr(settings, "EMBEDDING_PROVIDER", "local").lower().strip()
    if provider_type in ("hosted", "remote"):
        return HostedEmbeddingProvider()
    return LightweightLocalEmbeddingProvider()
