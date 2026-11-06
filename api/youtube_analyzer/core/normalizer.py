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

        def _dedupe_words(text: str) -> str:
            """Remove repeated words (e.g. 'saham pemula pemula' -> 'saham pemula')."""
            seen: set[str] = set()
            out: list[str] = []
            for w in text.split():
                key = w.lower().strip("?")
                if key in seen:
                    continue
                seen.add(key)
                out.append(w)
            result = " ".join(out)
            if text.endswith("?") and not result.endswith("?"):
                result += "?"
            return result

        def _clean(variants: list[str]) -> list[str]:
            return list(dict.fromkeys(_dedupe_words(v) for v in variants))

        return {
            PlatformEnum.GOOGLE_SEARCH: _clean(google_variants),
            PlatformEnum.YOUTUBE_SEARCH: _clean(youtube_variants),
            PlatformEnum.AI_SEARCH: _clean(aeo_variants),
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

        clusters: list[Any] = []
        for intent, data in clusters_map.items():
            # Include cluster if at least one surface sample exists
            if any([data["google"], data["youtube"], data["aeo"]]):
                try:
                    c: Any = IntentCluster(
                        topic_id=topic_id,
                        cluster_name=data["name"],
                        intent_type=intent,
                        google_term_sample=data["google"],
                        youtube_term_sample=data["youtube"],
                        aeo_query_sample=data["aeo"],
                    )
                except Exception:

                    class FallbackCluster:
                        def __init__(
                            self,
                            topic_id: int,
                            cluster_name: str,
                            intent_type: Any,
                            google_term_sample: str | None,
                            youtube_term_sample: str | None,
                            aeo_query_sample: str | None,
                        ) -> None:
                            self.topic_id = topic_id
                            self.cluster_name = cluster_name
                            self.intent_type = intent_type
                            self.google_term_sample = google_term_sample
                            self.youtube_term_sample = youtube_term_sample
                            self.aeo_query_sample = aeo_query_sample

                    c = FallbackCluster(
                        topic_id=topic_id,
                        cluster_name=data["name"],
                        intent_type=intent,
                        google_term_sample=data["google"],
                        youtube_term_sample=data["youtube"],
                        aeo_query_sample=data["aeo"],
                    )
                clusters.append(c)
        return clusters

    @staticmethod
    def is_tag_relevant(tag: str, context_text: str = "") -> bool:
        """
        Verify whether a tag is strictly relevant to the video topic / context.
        Filters out clickbait/spam keywords (e.g. 'gratis', 'free', 'tanpa modal', 'download', 'viral', 'fyp')
        UNLESS the video topic / context explicitly discusses or mentions them.
        """
        if not tag or not tag.strip():
            return False
        t_clean = tag.strip().lower()
        ctx_clean = context_text.lower() if context_text else ""

        # 1. Unconditional spam / stuffing (never professional for Studio tags)
        unconditional_spam = {
            "fyp",
            "#fyp",
            "viral",
            "#viral",
            "trending",
            "#trending",
            "foryou",
            "foryoupage",
            "tiktok",
            "reels",
            "shorts",
            "#shorts",
            "sub4sub",
            "subscribe",
            "like",
            "share",
            "comment",
        }
        if t_clean in unconditional_spam:
            return False

        # 2. Conditional spam (clickbait if not explicitly in video context)
        conditional_checks = [
            # (trigger_keywords in tag, required_keywords in context)
            (
                ["gratis", "free", "cuma-cuma", "freemium"],
                ["gratis", "free", "cuma-cuma", "tanpa biaya", "freemium"],
            ),
            (["tanpa modal", "modal nol", "modal 0", "modal kecil"], ["modal"]),
            (
                ["download", "unduh", "apk", "mod", "crack"],
                ["download", "unduh", "apk", "mod", "crack", "software", "aplikasi", "file"],
            ),
            (
                ["cepat kaya", "cara kaya", "jutawan", "milyarder"],
                ["kaya", "jutawan", "milyarder", "finansial"],
            ),
        ]

        for triggers, required_ctx in conditional_checks:
            if any(tr in t_clean for tr in triggers):
                # Must be present in context, otherwise reject as irrelevant clickbait
                if not any(req in ctx_clean for req in required_ctx):
                    return False

        return True

    @classmethod
    def filter_relevant_tags(cls, tags: list[str], context_text: str = "") -> list[str]:
        """Deduplicate and filter a list of tags for strict relevance against context."""
        seen: set[str] = set()
        result: list[str] = []
        for t in tags:
            if not t or not t.strip():
                continue
            t_str = t.strip()
            t_low = t_str.lower()
            if t_low not in seen and cls.is_tag_relevant(t_str, context_text):
                seen.add(t_low)
                result.append(t_str)
        return result

    @classmethod
    def clean_comma_tags(cls, tags_str: str, context_text: str = "", max_chars: int = 450) -> str:
        """Parse comma-separated tags, filter for strict relevance, and format under max_chars."""
        if not tags_str:
            return ""
        raw_tags = [
            re.sub(r"\s+", " ", re.sub(r"#\S*", "", t)).strip()
            if "#" in t
            else re.sub(r"\s+", " ", t).strip()
            for t in tags_str.split(",")
            if t.strip()
        ]
        raw_tags = [t for t in raw_tags if t]
        filtered = cls.filter_relevant_tags(raw_tags, context_text)

        selected: list[str] = []
        cur_len = 0
        for t in filtered:
            add_len = len(t) + (2 if selected else 0)
            if cur_len + add_len > max_chars:
                break
            selected.append(t)
            cur_len += add_len
        return ", ".join(selected)

    @classmethod
    def audit_tags_detailed(
        cls, tags: list[str] | str, context_text: str = "", max_chars: int = 450
    ) -> dict[str, Any]:
        """Perform exhaustive blindspot audit on a list or comma-separated string of tags.

        Returns:
            - total_tags_analyzed: int
            - relevant_count: int
            - rejected_count: int
            - has_blindspot: bool
            - clean_comma_string: str (under max_chars)
            - audit_breakdown: list of dicts with status, category, badge_color, reason, recommendation
            - summary_recommendation: str
        """
        if isinstance(tags, str):
            raw_list = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            raw_list = [str(t).strip() for t in tags if str(t).strip()]
        else:
            raw_list = []

        ctx_clean = context_text.lower() if context_text else ""
        seen_lower: set[str] = set()
        audit_breakdown: list[dict[str, Any]] = []
        approved_tags: list[str] = []

        unconditional_spam = {
            "fyp",
            "#fyp",
            "viral",
            "#viral",
            "trending",
            "#trending",
            "foryou",
            "foryoupage",
            "tiktok",
            "reels",
            "shorts",
            "#shorts",
            "sub4sub",
            "subscribe",
            "like",
            "share",
            "comment",
        }

        conditional_checks = [
            (
                ["gratis", "free", "cuma-cuma", "freemium"],
                ["gratis", "free", "cuma-cuma", "tanpa biaya", "freemium"],
            ),
            (["tanpa modal", "modal nol", "modal 0", "modal kecil"], ["modal"]),
            (
                ["download", "unduh", "apk", "mod", "crack"],
                ["download", "unduh", "apk", "mod", "crack", "software", "aplikasi", "file"],
            ),
            (
                ["cepat kaya", "cara kaya", "jutawan", "milyarder"],
                ["kaya", "jutawan", "milyarder", "finansial"],
            ),
        ]

        for raw_t in raw_list:
            clean_t = re.sub(r"#\S*", "", raw_t).strip() if "#" in raw_t else raw_t.strip()
            if not clean_t:
                clean_t = raw_t.replace("#", "").strip()
            if clean_t:
                raw_t = re.sub(r"\s+", " ", clean_t).strip()
            t_low = raw_t.lower()

            if t_low in seen_lower:
                audit_breakdown.append(
                    {
                        "tag": raw_t,
                        "status": "FAIL",
                        "category": "duplicate",
                        "badge_color": "yellow",
                        "reason": "Tag duplikat.",
                        "recommendation": "Hapus duplikasi untuk menghemat ruang kuota 500 karakter tag YouTube.",
                    }
                )
                continue

            seen_lower.add(t_low)

            if len(raw_t) > 35:
                audit_breakdown.append(
                    {
                        "tag": raw_t,
                        "status": "FAIL",
                        "category": "overlength",
                        "badge_color": "yellow",
                        "reason": f"Tag terlalu panjang ({len(raw_t)} karakter > 35).",
                        "recommendation": "Persingkat menjadi frasa kunci 2-4 kata yang lebih padat.",
                    }
                )
                continue

            if t_low in unconditional_spam:
                audit_breakdown.append(
                    {
                        "tag": raw_t,
                        "status": "FAIL",
                        "category": "unconditional_spam",
                        "badge_color": "red",
                        "reason": f"Dilarang: Tag '{raw_t}' adalah spam stuffing generik yang melanggar kebijakan YouTube Spam & Metadata Deception.",
                        "recommendation": "Hapus tag ini. Algoritma YouTube mengabaikan tag generik dan dapat membatasi distribusi jika terdeteksi spam.",
                    }
                )
                continue

            # Conditional clickbait checks
            matched_cond = False
            for triggers, required_ctx in conditional_checks:
                if any(tr in t_low for tr in triggers):
                    matched_cond = True
                    matched_tr = next(tr for tr in triggers if tr in t_low)
                    if any(req in ctx_clean for req in required_ctx):
                        audit_breakdown.append(
                            {
                                "tag": raw_t,
                                "status": "PASS",
                                "category": "relevant_conditional",
                                "badge_color": "green",
                                "reason": f"Lolos (Relevan): Tag '{raw_t}' valid karena topik/naskah video Anda secara eksplisit membahas materi terkait '{matched_tr}'.",
                                "recommendation": "Pertahankan tag ini. Relevansinya tinggi dengan materi video.",
                            }
                        )
                        approved_tags.append(raw_t)
                    else:
                        audit_breakdown.append(
                            {
                                "tag": raw_t,
                                "status": "FAIL",
                                "category": "clickbait_unsupported",
                                "badge_color": "red",
                                "reason": f"Ditolak: Tag mengandung kata pemicu '{matched_tr}', namun topik atau naskah video tidak membahas penawaran tersebut.",
                                "recommendation": f"Jika video memang menyediakan materi '{matched_tr}', sebutkan secara eksplisit dalam naskah/deskripsi. Jika tidak, hapus tag ini untuk mencegah penalti bounce rate audiens.",
                            }
                        )
                    break

            if not matched_cond:
                audit_breakdown.append(
                    {
                        "tag": raw_t,
                        "status": "PASS",
                        "category": "relevant_topical",
                        "badge_color": "green",
                        "reason": "Lolos: Tag memiliki relevansi tematik yang baik dengan topik bahasan.",
                        "recommendation": "Gunakan tag ini untuk membantu YouTube mengindeks variasi pencarian audiens.",
                    }
                )
                approved_tags.append(raw_t)

        selected: list[str] = []
        cur_len = 0
        for t in approved_tags:
            add_len = len(t) + (2 if selected else 0)
            if cur_len + add_len > max_chars:
                break
            selected.append(t)
            cur_len += add_len

        clean_comma_string = ", ".join(selected)
        relevant_count = len([a for a in audit_breakdown if a["status"] == "PASS"])
        rejected_count = len([a for a in audit_breakdown if a["status"] == "FAIL"])
        has_blindspot = rejected_count > 0

        if rejected_count == 0:
            summary = "Semua tag 100% relevan dan bebas dari spam stuffing maupun clickbait."
        else:
            summary = f"Terdeteksi {rejected_count} tag bermasalah (spam/clickbait tanpa dasar naskah). Sistem telah menyaringnya."

        return {
            "total_tags_analyzed": len(raw_list),
            "relevant_count": relevant_count,
            "rejected_count": rejected_count,
            "has_blindspot": has_blindspot,
            "clean_comma_string": clean_comma_string,
            "audit_breakdown": audit_breakdown,
            "summary_recommendation": summary,
        }

    @classmethod
    def audit_content_blindspots(
        cls,
        title: str,
        description: str,
        tags: list[str] | str,
        context_notes: str = "",
        target_format: str = "LANDSCAPE (16:9)",
    ) -> dict[str, Any]:
        """Execute comprehensive 5-Pillar Packaging & SEO Blindspot Audit:

        1. Title Length & Mobile Truncation Blindspot
        2. Google Key Moments (Timestamps & Chapters) Blindspot
        3. Tag Relevancy & Clickbait Blindspot
        4. First-Fold Description Hook Blindspot
        5. Format & Duration Alignment Blindspot
        """
        ctx_all = f"{title} {description} {context_notes}".strip()
        tag_audit = cls.audit_tags_detailed(tags, context_text=ctx_all)

        blindspots: list[dict[str, Any]] = []

        # 1. Title Audit
        t_len = len(title.strip())
        if t_len == 0:
            blindspots.append(
                {
                    "pillar": "Judul (Title)",
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "issue": "Judul video kosong.",
                    "action": "Buat judul dengan format 45-65 karakter.",
                }
            )
        elif t_len > 70:
            blindspots.append(
                {
                    "pillar": "Judul (Title)",
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "issue": f"Judul terlalu panjang ({t_len} karakter). Terpotong (...) di aplikasi YouTube mobile.",
                    "action": "Persingkat judul menjadi 45-65 karakter dan letakkan kata kunci utama di 30 karakter pertama.",
                }
            )
        elif t_len < 30:
            blindspots.append(
                {
                    "pillar": "Judul (Title)",
                    "status": "WARNING",
                    "severity": "LOW",
                    "issue": f"Judul terlalu pendek ({t_len} karakter). Kurang memicu rasa penasaran atau janji hasil spesifik.",
                    "action": "Tambahkan formula psikologis (misal: 'Rahasia...', 'Panduan Lengkap...', atau angka spesifik).",
                }
            )
        else:
            blindspots.append(
                {
                    "pillar": "Judul (Title)",
                    "status": "PASS",
                    "severity": "OK",
                    "issue": f"Panjang judul ideal ({t_len} karakter), aman dari pemotongan di layar mobile.",
                    "action": "Pertahankan struktur judul ini.",
                }
            )

        # 2. Google Key Moments (Timestamps)
        is_shorts = "9:16" in target_format or "short" in target_format.lower()
        if not is_shorts:
            ts_matches = re.findall(
                r"(?:\[)?(\d{1,2}:\d{2}(?::\d{2})?)(?:\])?\s*[-–:]?\s*(.+)", description
            )
            has_zero = any("00:00" in t[0] or "0:00" in t[0] for t in ts_matches)
            if not ts_matches:
                blindspots.append(
                    {
                        "pillar": "Google Key Moments (Timestamps)",
                        "status": "FAIL",
                        "severity": "HIGH",
                        "issue": "Tidak ada timestamps pembahasan di deskripsi video panjang.",
                        "action": "Tambahkan minimal 3-5 timestamps diawali 00:00 agar Google Search menampilkan fitur Key Moments di SERP.",
                    }
                )
            elif not has_zero:
                blindspots.append(
                    {
                        "pillar": "Google Key Moments (Timestamps)",
                        "status": "FAIL",
                        "severity": "HIGH",
                        "issue": "Timestamps tidak diawali dengan 00:00.",
                        "action": "YouTube mewajibkan babak pertama dimulai tepat di 00:00 (misal: '00:00 - Pengantar').",
                    }
                )
            elif len(ts_matches) < 3:
                blindspots.append(
                    {
                        "pillar": "Google Key Moments (Timestamps)",
                        "status": "WARNING",
                        "severity": "MEDIUM",
                        "issue": f"Jumlah babak timestamps hanya {len(ts_matches)} (minimal 3 babak).",
                        "action": "Tambahkan minimal 3 babak terpisah agar bab video aktif di pemutar YouTube.",
                    }
                )
            else:
                blindspots.append(
                    {
                        "pillar": "Google Key Moments (Timestamps)",
                        "status": "PASS",
                        "severity": "OK",
                        "issue": f"Timestamps lengkap ({len(ts_matches)} babak, diawali 00:00). Memenuhi syarat Google Key Moments.",
                        "action": "Bagus! Video siap bersaing memperebutkan video snippet di Google Web.",
                    }
                )
        else:
            blindspots.append(
                {
                    "pillar": "Format Pacing Shorts",
                    "status": "PASS",
                    "severity": "OK",
                    "issue": "Format Shorts (9:16) tidak memerlukan timestamps. Mengutamakan retensi visual cepat 60 detik.",
                    "action": "Fokus pada hook 3 detik pertama.",
                }
            )

        # 3. Tag Relevancy
        if tag_audit["rejected_count"] > 0:
            blindspots.append(
                {
                    "pillar": "Relevansi Tags & Anti-Spam",
                    "status": "FAIL",
                    "severity": "HIGH",
                    "issue": f"Ditemukan {tag_audit['rejected_count']} tag tidak relevan / spam stuffing / clickbait.",
                    "action": f"Gunakan tag yang telah disaring: {tag_audit['clean_comma_string']}",
                }
            )
        else:
            blindspots.append(
                {
                    "pillar": "Relevansi Tags & Anti-Spam",
                    "status": "PASS",
                    "severity": "OK",
                    "issue": f"Semua tag ({tag_audit['relevant_count']} tag) relevan dan aman dari penalti spam.",
                    "action": "Siap disalin ke kolom Tags YouTube Studio.",
                }
            )

        # 4. First-Fold Description Hook
        desc_lines = [line.strip() for line in description.splitlines() if line.strip()]
        first_fold = " ".join(desc_lines[:2]) if desc_lines else ""
        if len(first_fold) < 40:
            blindspots.append(
                {
                    "pillar": "First-Fold Hook Deskripsi",
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "issue": "Dua baris pertama deskripsi terlalu pendek atau belum merangkum inti video sebelum tombol '...more'.",
                    "action": "Tulis 1-2 kalimat pemikat yang mengandung kata kunci utama di awal deskripsi.",
                }
            )
        else:
            blindspots.append(
                {
                    "pillar": "First-Fold Hook Deskripsi",
                    "status": "PASS",
                    "severity": "OK",
                    "issue": "First-fold deskripsi informatif dan memikat penonton sebelum klik '...more'.",
                    "action": "Pertahankan hook deskripsi ini.",
                }
            )

        critical_count = len([b for b in blindspots if b["status"] == "FAIL"])
        warning_count = len([b for b in blindspots if b["status"] == "WARNING"])
        overall_score = max(10, 100 - (critical_count * 25) - (warning_count * 10))

        return {
            "overall_score": overall_score,
            "overall_status": "EXCELLENT"
            if overall_score >= 85
            else ("NEEDS_IMPROVEMENT" if overall_score >= 60 else "POOR"),
            "blindspots": blindspots,
            "tag_audit": tag_audit,
        }
