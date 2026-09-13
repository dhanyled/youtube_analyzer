"""Topic normalizer and cross-surface expansion engine.

Translates a single Topic Seed into surface-specific queries (Google, YouTube, AI/AEO)
and clusters search results back into unified intent buckets.
"""

import re

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
        Produces synchronized clusters (e.g. Tutorial, Biaya/Commercial, Pemula).
        """
        buckets: dict[str, dict[str, str]] = {
            "Tutorial": {"intent": IntentEnum.TUTORIAL},
            "Biaya & Jasa": {"intent": IntentEnum.COMMERCIAL},
            "Pemula & Edukasi": {"intent": IntentEnum.INFORMATIONAL},
            "Evaluasi & Review": {"intent": IntentEnum.COMPARISON},
        }

        # Populate samples
        for term in google_terms:
            intent = cls.classify_intent(term)
            if intent == IntentEnum.TUTORIAL and "google" not in buckets["Tutorial"]:
                buckets["Tutorial"]["google"] = term
            elif intent == IntentEnum.COMMERCIAL and "google" not in buckets["Biaya & Jasa"]:
                buckets["Biaya & Jasa"]["google"] = term
            elif "google" not in buckets["Pemula & Edukasi"]:
                buckets["Pemula & Edukasi"]["google"] = term

        for term in youtube_terms:
            intent = cls.classify_intent(term)
            if intent == IntentEnum.TUTORIAL and "youtube" not in buckets["Tutorial"]:
                buckets["Tutorial"]["youtube"] = term
            elif intent == IntentEnum.COMMERCIAL and "youtube" not in buckets["Biaya & Jasa"]:
                buckets["Biaya & Jasa"]["youtube"] = term
            elif "youtube" not in buckets["Pemula & Edukasi"]:
                buckets["Pemula & Edukasi"]["youtube"] = term

        for query in aeo_queries:
            intent = cls.classify_intent(query)
            if intent == IntentEnum.TUTORIAL and "aeo" not in buckets["Tutorial"]:
                buckets["Tutorial"]["aeo"] = query
            elif intent == IntentEnum.COMMERCIAL and "aeo" not in buckets["Biaya & Jasa"]:
                buckets["Biaya & Jasa"]["aeo"] = query
            elif "aeo" not in buckets["Pemula & Edukasi"]:
                buckets["Pemula & Edukasi"]["aeo"] = query

        clusters: list[IntentCluster] = []
        for cluster_name, data in buckets.items():
            clusters.append(
                IntentCluster(
                    topic_id=topic_id,
                    cluster_name=cluster_name,
                    intent_type=data["intent"],
                    google_term_sample=data.get("google"),
                    youtube_term_sample=data.get("youtube"),
                    aeo_query_sample=data.get("aeo"),
                )
            )
        return clusters
