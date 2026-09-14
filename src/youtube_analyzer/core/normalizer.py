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

        from youtube_analyzer.core.intelligence import SearchIntelligence

        niche = SearchIntelligence.detect_content_niche(seed)

        if niche == "documentary":
            google_variants = [
                lowered,
                f"sejarah {lowered}",
                f"kronologi {lowered}",
                f"penyebab {lowered}",
                f"dampak {lowered}",
                f"fakta ilmiah {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"dokumenter {lowered}",
                f"detik detik {lowered}",
                f"kisah nyata {lowered}",
                f"rekaman suara {lowered}",
                f"penjelasan ilmiah {lowered}",
            ]
            aeo_variants = [
                f"apa penyebab utama {lowered}?",
                f"bagaimana kronologi terjadinya {lowered}?",
                f"apa dampak terbesar {lowered} bagi dunia?",
                f"fakta menarik tentang {lowered} yang jarang dibahas",
                f"apakah {lowered} bisa terjadi lagi di masa depan?",
            ]
        elif niche == "culinary":
            google_variants = [
                lowered,
                f"resep {lowered}",
                f"bumbu {lowered}",
                f"cara membuat {lowered}",
                f"resep {lowered} empuk",
                f"tips masak {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"cara masak {lowered}",
                f"resep {lowered} praktis",
                f"rahasia bumbu {lowered}",
                f"{lowered} ala restoran",
                f"resep {lowered} anti gagal",
            ]
            aeo_variants = [
                f"bagaimana resep dan bumbu {lowered} yang enak?",
                f"apa bumbu utama untuk {lowered}?",
                f"tips agar {lowered} empuk dan bumbu meresap",
                f"berapa lama waktu memasak {lowered}?",
                f"resep {lowered} takaran rumahan",
            ]
        elif niche == "travel":
            google_variants = [
                lowered,
                f"harga tiket {lowered}",
                f"rute ke {lowered}",
                f"hotel dekat {lowered}",
                f"itinerary {lowered}",
                f"biaya liburan ke {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"vlog wisata {lowered}",
                f"panduan liburan ke {lowered}",
                f"hidden gem {lowered}",
                f"tips hemat ke {lowered}",
                f"spot foto terbaik {lowered}",
            ]
            aeo_variants = [
                f"kapan waktu terbaik berkunjung ke {lowered}?",
                f"berapa perkiraan biaya liburan ke {lowered}?",
                f"rekomendasi itinerary liburan di {lowered}",
                f"tips aman jalan-jalan ke {lowered}",
                f"transportasi terbaik menuju {lowered}",
            ]
        elif niche == "entertainment":
            google_variants = [
                lowered,
                f"sinopsis {lowered}",
                f"pemeran {lowered}",
                f"penjelasan ending {lowered}",
                f"alur cerita {lowered}",
                f"review {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"alur cerita {lowered}",
                f"bedah film {lowered}",
                f"teori {lowered}",
                f"fakta tersembunyi {lowered}",
                f"penjelasan ending {lowered}",
            ]
            aeo_variants = [
                f"apa makna ending dari {lowered}?",
                f"siapa karakter penting di {lowered}?",
                f"rangkuman alur cerita lengkap {lowered}",
                f"penjelasan teori tersembunyi di {lowered}",
                f"apa pesan moral dari cerita {lowered}?",
            ]
        elif niche == "health_fitness":
            google_variants = [
                lowered,
                f"gejala {lowered}",
                f"penyebab {lowered}",
                f"cara mengatasi {lowered}",
                f"obat alami {lowered}",
                f"pantangan {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"cara mengatasi {lowered}",
                f"tips hidup sehat {lowered}",
                f"gerakan terapi {lowered}",
                f"penjelasan dokter tentang {lowered}",
                f"kebiasaan pemicu {lowered}",
            ]
            aeo_variants = [
                f"apa tanda-tanda awal {lowered}?",
                f"bagaimana cara mengatasi {lowered} secara aman?",
                f"pantangan makanan saat mengalami {lowered}",
                f"kapan harus periksa dokter untuk {lowered}?",
                f"apakah {lowered} bisa sembuh secara alami?",
            ]
        elif niche == "business":
            google_variants = [
                lowered,
                f"jasa {lowered}",
                f"biaya {lowered}",
                f"{lowered} pemula",
                f"{lowered} murah",
                f"cara {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"cara {lowered}",
                f"tutorial {lowered}",
                f"tutorial {lowered} pemula",
                f"setting {lowered} dari nol",
                f"{lowered} review",
            ]
            aeo_variants = [
                f"apakah {lowered} efektif?",
                f"berapa biaya {lowered}?",
                f"bagaimana cara mulai {lowered}?",
                f"jasa {lowered} terbaik",
                f"tips {lowered} untuk pemula",
            ]
        elif niche == "tech_tutorial":
            google_variants = [
                lowered,
                f"cara menggunakan {lowered}",
                f"download {lowered}",
                f"panduan {lowered}",
                f"solusi error {lowered}",
                f"spesifikasi {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"tutorial {lowered} pemula",
                f"cara setting {lowered}",
                f"tips dan trik {lowered}",
                f"review {lowered}",
                f"shortcut penting {lowered}",
            ]
            aeo_variants = [
                f"bagaimana cara setting {lowered} dari awal?",
                f"bagaimana mengatasi error umum pada {lowered}?",
                f"rekomendasi shortcut terbaik untuk {lowered}",
                f"apa kelebihan dan kekurangan {lowered}?",
                f"panduan instalasi lengkap {lowered}",
            ]
        else:
            google_variants = [
                lowered,
                f"apa itu {lowered}",
                f"sejarah {lowered}",
                f"fakta {lowered}",
                f"manfaat {lowered}",
                f"contoh {lowered}",
            ]
            youtube_variants = [
                lowered,
                f"penjelasan lengkap {lowered}",
                f"fakta unik {lowered}",
                f"kenapa {lowered} viral",
                f"analisis mendalam {lowered}",
                f"rangkuman {lowered}",
            ]
            aeo_variants = [
                f"apa arti dan makna dari {lowered}?",
                f"kenapa {lowered} penting untuk diketahui?",
                f"bagaimana asal usul dan sejarah {lowered}?",
                f"apa pengaruh {lowered} saat ini?",
                f"fakta menarik seputar {lowered}",
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
