"""Topic normalizer and cross-surface expansion engine.

Translates a single Topic Seed into surface-specific queries (Google, YouTube, AI/AEO)
and clusters search results back into unified intent buckets.
"""

import re
from typing import Any

from youtube_analyzer.core.models import IntentCluster, IntentEnum, PlatformEnum


class TopicNormalizer:
    """Orchestrates seed expansion and intent clustering across Google, YouTube, and AI."""

    # Linguistic cues for intent classification (ID & EN supported)
    INTENT_PATTERNS: dict[IntentEnum, list[str]] = {
        IntentEnum.TUTORIAL: [
            "cara",
            "tutorial",
            "panduan",
            "step by step",
            "langkah",
            "setting",
            "pasang",
            "how to",
            "setup",
            "guide",
        ],
        IntentEnum.COMMERCIAL: [
            "jasa",
            "harga",
            "biaya",
            "agency",
            "konsultan",
            "layanan",
            "tarif",
            "service",
            "pricing",
            "cost",
            "cheap",
            "murah",
            "terbaik",
            "best",
        ],
        IntentEnum.TRANSACTIONAL: [
            "beli",
            "order",
            "daftar",
            "sewa",
            "promo",
            "diskon",
            "hire",
            "buy",
        ],
        IntentEnum.COMPARISON: [
            "vs",
            "versus",
            "perbandingan",
            "beda",
            "review",
            "kelebihan",
            "kekurangan",
            "compare",
        ],
        IntentEnum.INFORMATIONAL: [
            "apa itu",
            "apakah",
            "kenapa",
            "mengapa",
            "pengertian",
            "definisi",
            "bagaimana",
            "what is",
            "why",
            "efektif",
        ],
    }

    @staticmethod
    def generate_canonical_id(seed: str, prefix: str = "TOPIC") -> str:
        """Generate clean deterministic canonical identifier from seed string."""
        clean = re.sub(r"[^a-zA-Z0-9]+", "-", seed.strip()).strip("-").upper()
        parts = clean.split("-")[:3]
        short_code = "".join(p[:3] for p in parts)
        return f"{prefix}-{short_code}"

    @classmethod
    def classify_intent(cls, text: str) -> IntentEnum:
        """Classify search query or keyword intent based on linguistic markers."""
        lowered = text.lower()
        for intent, patterns in cls.INTENT_PATTERNS.items():
            if any(re.search(rf"\b{re.escape(pattern)}\b", lowered) for pattern in patterns):
                return intent
        return IntentEnum.INFORMATIONAL

    @classmethod
    def expand_seed_surfaces(cls, seed: str) -> dict[PlatformEnum, list[str]]:
        """
        Cross-surface expansion from a single seed topic.
        Does NOT duplicate raw keywords blindly, but tailors seed variants to platform search habits.
        """
        cleaned = seed.strip()
        lowered = cleaned.lower()

        # Google Search/GKP: Commercial, cost, services, business context
        google_variants = [
            lowered,
            f"jasa {lowered}",
            f"biaya {lowered}",
            f"{lowered} pemula",
            f"{lowered} murah",
            f"cara {lowered}",
        ]

        # YouTube: Tutorials, setup, step-by-step, demonstrations
        youtube_variants = [
            lowered,
            f"cara {lowered}",
            f"tutorial {lowered}",
            f"tutorial {lowered} pemula",
            f"setting {lowered} dari nol",
            f"{lowered} review",
        ]

        # AI / AEO Prompts: Conversational, decision-making, evaluation queries
        aeo_variants = [
            f"apakah {lowered} efektif?",
            f"berapa biaya {lowered}?",
            f"bagaimana cara mulai {lowered}?",
            f"jasa {lowered} terbaik",
            f"tips {lowered} untuk pemula",
        ]

        return {
            PlatformEnum.GOOGLE_SEARCH: list(dict.fromkeys(google_variants)),
            PlatformEnum.YOUTUBE_SEARCH: list(dict.fromkeys(youtube_variants)),
            PlatformEnum.AI_SEARCH: list(dict.fromkeys(aeo_variants)),
        }

    @classmethod
    def create_intent_clusters(
        cls,
        topic_id: int,
        google_terms: list[str],
        youtube_terms: list[str],
        aeo_queries: list[str],
    ) -> list[IntentCluster]:
        """
        Group cross-surface terms into unified intent clusters.
        Produces synchronized clusters (e.g. Tutorial, Commercial, Informational, Comparison, Transactional).
        """
        bucket_definitions: list[tuple[str, IntentEnum]] = [
            ("Tutorial", IntentEnum.TUTORIAL),
            ("Biaya & Jasa", IntentEnum.COMMERCIAL),
            ("Transaksi & Pembelian", IntentEnum.TRANSACTIONAL),
            ("Evaluasi & Review", IntentEnum.COMPARISON),
            ("Pemula & Edukasi", IntentEnum.INFORMATIONAL),
        ]

        clusters_map: dict[IntentEnum, dict[str, Any]] = {
            intent: {
                "name": name,
                "google": None,
                "youtube": None,
                "aeo": None,
            }
            for name, intent in bucket_definitions
        }

        def populate_samples(terms: list[str], surface_key: str) -> None:
            for term in terms:
                intent = cls.classify_intent(term)
                if intent in clusters_map and clusters_map[intent][surface_key] is None:
                    clusters_map[intent][surface_key] = term

        populate_samples(google_terms, "google")
        populate_samples(youtube_terms, "youtube")
        populate_samples(aeo_queries, "aeo")

        clusters: list[IntentCluster] = []
        for intent, data in clusters_map.items():
            # Include cluster if at least one surface sample exists
            if any([data["google"], data["youtube"], data["aeo"]]):
                clusters.append(
                    IntentCluster(
                        topic_id=topic_id,
                        cluster_name=data["name"],
                        intent_type=intent,
                        google_term_sample=data["google"],
                        youtube_term_sample=data["youtube"],
                        aeo_query_sample=data["aeo"],
                    )
                )
        return clusters
