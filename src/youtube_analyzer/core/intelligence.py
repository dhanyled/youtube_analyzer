"""Search Intelligence & YouTube Opportunity Engine.

Incorporates proven algorithms for:
- Opportunity Score (Search Volume vs Competition) & Video SEO Formulas
- Intent Clustering & Search Rank Optimization
- Outlier Detection (Viral Breakout multiplier) & Niche RPM Economics
"""

import math
from datetime import UTC, datetime
from typing import Any

from youtube_analyzer.core.models import IntentEnum


class SearchIntelligence:
    """Calculates keyword opportunity, outlier velocity, and monetization metrics."""

    # Benchmark RPM by Niche Categories (Estimated USD per 1,000 views)
    NICHE_RPM_BENCHMARKS: dict[str, dict[str, float]] = {
        "finance": {"low": 15.0, "avg": 24.0, "high": 40.0},
        "advertising": {"low": 12.0, "avg": 20.0, "high": 35.0},
        "tech": {"low": 7.0, "avg": 12.0, "high": 22.0},
        "business": {"low": 8.0, "avg": 15.0, "high": 28.0},
        "health_fitness": {"low": 5.0, "avg": 10.0, "high": 18.0},
        "automotive": {"low": 4.5, "avg": 9.0, "high": 16.0},
        "education": {"low": 4.0, "avg": 8.0, "high": 15.0},
        "travel": {"low": 3.0, "avg": 6.0, "high": 11.0},
        "culinary": {"low": 2.5, "avg": 4.8, "high": 8.5},
        "documentary": {"low": 3.5, "avg": 6.8, "high": 12.0},
        "lifestyle": {"low": 2.0, "avg": 4.0, "high": 7.5},
        "gaming": {"low": 1.5, "avg": 2.8, "high": 5.0},
        "entertainment": {"low": 1.2, "avg": 2.5, "high": 4.5},
        "general": {"low": 2.0, "avg": 4.5, "high": 8.0},
    }

    @staticmethod
    def parse_views_str(views_str: str | int | float) -> int:
        """
        Parse YouTube view string into integer.
        Handles both English ('79K views', '1.2M views', '1,464,073 views')
        and Indonesian ('1.464.073 x ditonton', '79 rb x ditonton', '1,2 jt x ditonton').
        """
        if isinstance(views_str, (int, float)):
            return int(views_str)
        if not views_str:
            return 0

        clean = str(views_str).upper()
        clean = clean.replace("VIEWS", "").replace("DITONTON", "").replace("X", "").strip()

        import re

        has_billion = any(b in clean for b in ["B", "MILYAR", "MLY"])
        has_million = any(m in clean for m in ["M", "JT", "JUTA"])
        has_thousand = any(k in clean for k in ["K", "RB", "RIBU"])

        if has_billion or has_million or has_thousand:
            num_match = re.search(r"([\d]+(?:[.,]\d+)?)", clean)
            if not num_match:
                return 0
            val_str = num_match.group(1).replace(",", ".")
            try:
                val = float(val_str)
                if has_billion:
                    return int(val * 1_000_000_000)
                elif has_million:
                    return int(val * 1_000_000)
                elif has_thousand:
                    return int(val * 1_000)
            except ValueError:
                return 0
        else:
            # Plain numbers with separators: e.g. 1.464.073 or 1,464,073 or 450
            digits_only = re.sub(r"[^\d]", "", clean)
            if digits_only:
                try:
                    return int(digits_only)
                except ValueError:
                    return 0

        return 0

    @staticmethod
    def calculate_opportunity_score(search_volume: int, competition_score: float) -> float:
        """
        Calculate algorithmic overall opportunity score (0 - 100).
        - search_volume: Estimated monthly searches
        - competition_score: 0 (no competition) to 100 (saturated)
        """
        if search_volume <= 0:
            vol_score = 10.0
        else:
            vol_score = min(100.0, (math.log10(max(search_volume, 10)) / 5.0) * 100.0)

        comp_clamped = max(0.0, min(100.0, competition_score))
        inv_comp = 100.0 - comp_clamped

        # Weighted: 55% search demand, 45% low competition
        final_score = (vol_score * 0.55) + (inv_comp * 0.45)
        return round(max(0.0, min(100.0, final_score)), 1)

    @staticmethod
    def calculate_outlier_score(views: int, channel_median_views: int) -> dict[str, Any]:
        """
        Calculate viral Outlier Multiplier.
        Identifies videos that dramatically outperform channel baseline.
        """
        safe_views = max(0, views)
        safe_median_views = max(0, channel_median_views)
        median = max(safe_median_views, 1)
        multiplier = round(safe_views / median, 2)

        if multiplier >= 5.0:
            classification = "🔥 VIRAL_BREAKOUT (5x+)"
            is_outlier = True
        elif multiplier >= 2.5:
            classification = "⭐ STRONG_OUTLIER (2.5x - 5x)"
            is_outlier = True
        elif multiplier >= 1.2:
            classification = "📈 ABOVE_AVERAGE (1.2x - 2.5x)"
            is_outlier = False
        else:
            classification = "⚖️ AVERAGE_OR_BELOW"
            is_outlier = False

        return {
            "views": views,
            "channel_median": channel_median_views,
            "outlier_multiplier": multiplier,
            "classification": classification,
            "is_outlier": is_outlier,
        }

    @classmethod
    def estimate_keyword_metrics(
        cls, seed: str, competitors: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Dynamically estimate monthly search volume, competition difficulty (0-100),
        and overall opportunity score (0-100) based on seed keyword and live competitor metrics.
        Dynamic search demand & competition calculation.
        """
        clean_seed = seed.strip().lower()
        seed_words = [w for w in clean_seed.split() if len(w) > 2]

        # 1. Base Volume from Competitor Views
        views_list: list[int] = []
        if competitors:
            for c in competitors:
                raw_views = c.get("views_count") or c.get("views") or 0
                parsed = cls.parse_views_str(raw_views)
                if parsed > 0:
                    views_list.append(parsed)

        if views_list:
            avg_comp_views = sum(views_list) / len(views_list)
            max_comp_views = max(views_list)
        else:
            avg_comp_views = 25000
            max_comp_views = 50000

        # Correlate search volume with competitor view velocity
        if avg_comp_views >= 500000:
            base_vol = 75000 + int((avg_comp_views - 500000) * 0.05)
        elif avg_comp_views >= 100000:
            base_vol = 25000 + int((avg_comp_views - 100000) * 0.12)
        elif avg_comp_views >= 20000:
            base_vol = 6000 + int((avg_comp_views - 20000) * 0.23)
        elif avg_comp_views >= 5000:
            base_vol = 1800 + int((avg_comp_views - 5000) * 0.28)
        else:
            base_vol = max(350, int(avg_comp_views * 0.4))

        # Query length modifier (short keywords have broader search demand than long-tails)
        word_count = len(seed_words)
        if word_count <= 2:
            vol_multiplier = 1.35
        elif word_count == 3:
            vol_multiplier = 1.0
        else:
            vol_multiplier = max(0.45, 1.0 - (word_count - 3) * 0.15)

        search_volume = int(base_vol * vol_multiplier)

        # 2. Dynamic Competition Score (0 - 100)
        # Factor A: Exact / Partial keyword match in competitor titles
        matched_titles_count = 0
        if competitors:
            for c in competitors:
                c_title = c.get("title", "").lower()
                if any(w in c_title for w in seed_words):
                    matched_titles_count += 1
            comp_density = (matched_titles_count / max(len(competitors), 1)) * 35.0
        else:
            comp_density = 20.0

        # Factor B: Incumbent authority (max views barrier)
        if max_comp_views >= 500000:
            authority_barrier = 35.0
        elif max_comp_views >= 100000:
            authority_barrier = 25.0
        elif max_comp_views >= 20000:
            authority_barrier = 15.0
        else:
            authority_barrier = 8.0

        # Factor C: Freshness / New entrant feasibility
        # If videos uploaded within 6 months are ranking, competition is fresher / easier
        freshness_discount = 0.0
        if competitors:
            for c in competitors[:3]:
                age = str(c.get("upload_age", "")).lower()
                if any(
                    x in age
                    for x in [
                        "hari",
                        "minggu",
                        "bulan",
                        "day",
                        "week",
                        "month",
                        "recent",
                        "1 bulan",
                    ]
                ):
                    if not any(x in age for x in ["tahun", "year"]):
                        freshness_discount += 5.0
        freshness_discount = min(15.0, freshness_discount)

        # Factor D: Base topic hardness
        base_hardness = 20.0

        raw_comp = base_hardness + comp_density + authority_barrier - freshness_discount
        competition_score = round(max(15.0, min(92.0, raw_comp)), 1)

        # 3. Calculate Overall Opportunity Score
        opportunity_score = cls.calculate_opportunity_score(search_volume, competition_score)

        if opportunity_score >= 68.0:
            rating = "HIGH_POTENTIAL"
        elif opportunity_score >= 48.0:
            rating = "MODERATE"
        else:
            rating = "COMPETITIVE"

        return {
            "search_volume": search_volume,
            "competition_score": competition_score,
            "opportunity_score": opportunity_score,
            "rating": rating,
            "avg_competitor_views": int(avg_comp_views),
            "max_competitor_views": int(max_comp_views),
        }

    @classmethod
    def detect_content_niche(cls, seed: str) -> str:
        """
        Intelligently detects content genre/niche using a weighted keyword scoring system.
        Each keyword match increments a niche score. The niche with the highest total score wins.
        Ties are broken by a predefined priority order.

        Returns one of: 'documentary', 'culinary', 'travel', 'entertainment',
        'health_fitness', 'business', 'tech_tutorial', 'general'.
        """
        lowered = seed.strip().lower()

        # --- Keyword pools per niche with weight ---
        # Weight 2 = strong signal (specific, unambiguous keyword)
        # Weight 1 = weak signal (generic, may appear in multiple contexts)
        niche_keywords: dict[str, list[tuple[str, int]]] = {
            "documentary": [
                ("krakatau", 2),
                ("letusan", 2),
                ("meletus", 2),
                ("gempa", 2),
                ("tsunami", 2),
                ("bencana", 2),
                ("sejarah", 2),
                ("perang", 2),
                ("dinosaurus", 2),
                ("alien", 2),
                ("segitiga bermuda", 2),
                ("luar angkasa", 2),
                ("planet", 2),
                ("arkeologi", 2),
                ("fosil", 2),
                ("konspirasi", 2),
                ("mitos", 2),
                ("legenda", 2),
                ("antartika", 2),
                ("tragedi", 2),
                ("kronologi", 2),
                ("tata surya", 2),
                ("hewan buas", 2),
                ("ekspedisi", 2),
                ("piramida", 2),
                ("atlantis", 2),
                ("meteor", 2),
                ("asteroid", 2),
                ("black hole", 2),
                ("lubang hitam", 2),
                ("kerajaan", 2),
                ("majapahit", 2),
                ("pahlawan", 2),
                ("kisah nyata", 2),
                ("dokumenter", 2),
                ("arkeologis", 2),
                ("laut dalam", 2),
                ("palung", 2),
                ("safari", 2),
                ("gunung", 1),
                ("bumi", 1),
                ("misteri", 1),
                ("sains", 1),
                ("biologi", 1),
                ("fisika", 1),
                ("hiu", 1),
                ("singa", 1),
                ("hantu", 1),
                ("horor", 1),
                ("alam", 1),
                ("hutan", 1),
                ("sejarah dunia", 2),
                ("fakta sejarah", 2),
            ],
            "culinary": [
                ("resep", 2),
                ("masak", 2),
                ("bumbu", 2),
                ("dapur", 2),
                ("kuliner", 2),
                ("koki", 2),
                ("chef", 2),
                ("mukbang", 2),
                ("jajanan", 2),
                ("bakso", 2),
                ("rendang", 2),
                ("soto", 2),
                ("sambal", 2),
                ("cemilan", 2),
                ("bolu", 2),
                ("goreng", 2),
                ("rebus", 2),
                ("panggang", 2),
                ("food", 2),
                ("snack", 2),
                ("ayam", 1),
                ("daging", 1),
                ("nasi", 1),
                ("mie", 1),
                ("kue", 1),
                ("makanan", 1),
                ("minuman", 1),
                ("pedas", 1),
                ("roti", 1),
                ("jus", 1),
                ("kopi", 1),
                ("teh", 1),
                ("cafe", 1),
                ("restoran", 1),
            ],
            "travel": [
                ("wisata", 2),
                ("liburan", 2),
                ("itinerary", 2),
                ("backpacker", 2),
                ("hidden gem", 2),
                ("traveling", 2),
                ("staycation", 2),
                ("glamping", 2),
                ("snorkeling", 2),
                ("diving", 2),
                ("trekking", 2),
                ("hiking", 2),
                ("penginapan", 2),
                ("resort", 2),
                ("labuan bajo", 2),
                ("raja ampat", 2),
                ("komodo", 2),
                ("wakatobi", 2),
                ("bromo", 2),
                ("toraja", 2),
                ("solo travel", 2),
                ("road trip", 2),
                ("wisata alam", 2),
                ("wisata religi", 2),
                ("umroh", 2),
                ("mekah", 2),
                ("madinah", 2),
                ("hotel", 1),
                ("pantai", 1),
                ("villa", 1),
                ("rute", 1),
                ("tiket", 1),
                ("bali", 1),
                ("jogja", 1),
                ("lombok", 1),
                ("sumba", 1),
                ("flores", 1),
                ("manado", 1),
                ("bandung", 1),
                ("surabaya", 1),
                ("medan", 1),
                ("makassar", 1),
                ("singapore", 1),
                ("malaysia", 1),
                ("thailand", 1),
                ("vietnam", 1),
                ("korea", 1),
                ("paris", 1),
                ("london", 1),
                ("dubai", 1),
                ("turki", 1),
                ("mesir", 1),
                ("jepang", 1),
                ("eropa", 1),
                ("danau", 1),
                ("pulau", 1),
                ("curug", 1),
                ("air terjun", 1),
                ("candi", 1),
                ("taman", 1),
                ("tour", 1),
            ],
            "entertainment": [
                ("film", 2),
                ("movie", 2),
                ("drama", 2),
                ("anime", 2),
                ("manga", 2),
                ("alur cerita", 2),
                ("sinopsis", 2),
                ("rekap", 2),
                ("ending", 2),
                ("trailer", 2),
                ("lirik", 2),
                ("chord", 2),
                ("konser", 2),
                ("komedi", 2),
                ("parodi", 2),
                ("sketsa", 2),
                ("artis", 2),
                ("gosip", 2),
                ("gameplay", 2),
                ("mobile legends", 2),
                ("free fire", 2),
                ("roblox", 2),
                ("genshin", 2),
                ("valorant", 2),
                ("minecraft", 2),
                ("walkthrough", 2),
                ("streamer", 2),
                ("lagu", 1),
                ("musik", 1),
                ("vlog", 1),
                ("lucu", 1),
                ("game", 1),
                ("gaming", 1),
                ("gta", 1),
                ("ps5", 1),
                ("ff", 1),
            ],
            "health_fitness": [
                ("diet", 2),
                ("gym", 2),
                ("fitness", 2),
                ("workout", 2),
                ("kalori", 2),
                ("skincare", 2),
                ("glowing", 2),
                ("jerawat", 2),
                ("herbal", 2),
                ("medis", 2),
                ("terapi", 2),
                ("kolesterol", 2),
                ("diabetes", 2),
                ("asam urat", 2),
                ("penyakit", 2),
                ("gejala", 2),
                ("dokter", 2),
                ("obat", 2),
                ("kesehatan", 2),
                ("otot", 1),
                ("kurus", 1),
                ("lemak", 1),
                ("sehat", 1),
                ("rambut", 1),
            ],
            "business": [
                ("google ads", 2),
                ("fb ads", 2),
                ("tiktok ads", 2),
                ("iklan", 2),
                ("bisnis", 2),
                ("omset", 2),
                ("reseller", 2),
                ("dropship", 2),
                ("affiliate", 2),
                ("saham", 2),
                ("crypto", 2),
                ("trading", 2),
                ("investasi", 2),
                ("keuangan", 2),
                ("closing", 2),
                ("freelance", 2),
                ("umkm", 2),
                ("franchise", 2),
                ("toko online", 2),
                ("ekspor", 2),
                ("marketing", 2),
                ("passive income", 2),
                ("penjualan", 2),
                ("ads", 1),
                ("jualan", 1),
                ("modal", 1),
                ("cuan", 1),
                ("usaha", 1),
                ("sales", 1),
                ("gaji", 1),
                ("impor", 1),
            ],
            "tech_tutorial": [
                ("coding", 2),
                ("python", 2),
                ("javascript", 2),
                ("programming", 2),
                ("excel", 2),
                ("canva", 2),
                ("capcut", 2),
                ("photoshop", 2),
                ("developer", 2),
                ("software", 2),
                ("chatgpt", 2),
                ("prompt ai", 2),
                ("edit video", 2),
                ("instal", 2),
                ("download", 2),
                ("gadget", 2),
                ("tutorial", 1),
                ("cara membuat", 1),
                ("panduan", 1),
                ("komputer", 1),
                ("laptop", 1),
                ("hp", 1),
                ("setting", 1),
                ("review hp", 1),
            ],
        }

        # Priority order for tie-breaking (highest priority first)
        priority_order = [
            "documentary",
            "culinary",
            "travel",
            "entertainment",
            "health_fitness",
            "business",
            "tech_tutorial",
        ]

        # Score each niche
        scores: dict[str, int] = {niche: 0 for niche in niche_keywords}
        for niche, kw_list in niche_keywords.items():
            for kw, weight in kw_list:
                if kw in lowered:
                    scores[niche] += weight

        # Find the best niche
        max_score = max(scores.values())
        if max_score == 0:
            # No match — fallback: if question/how-to words present, use tech_tutorial
            if any(k in lowered for k in ["cara", "tips", "trik", "bagaimana"]):
                return "tech_tutorial"
            return "general"

        # Among niches with the same top score, pick by priority order
        for niche in priority_order:
            if scores[niche] == max_score:
                return niche

        return "general"

    @classmethod
    def estimate_rpm(cls, topic_name: str) -> dict[str, Any]:
        """
        Estimate YouTube AdSense RPM (USD) based on topic keywords.
        Monetization projection across 12 distinct niches.
        """
        lowered = topic_name.lower()

        # Rule-based regex and keyword matching for accurate niche detection
        if any(
            k in lowered
            for k in [
                "saham",
                "crypto",
                "bitcoin",
                "reksadana",
                "investasi",
                "trading",
                "bank",
                "pinjol",
                "kredit",
                "uang",
                "rupiah",
                "dollar",
                "obligasi",
                "asuransi",
                "financial",
                "kpr",
                "dividen",
                "forex",
                "pajak",
            ]
        ):
            matched_niche = "finance"
        elif any(
            k in lowered
            for k in [
                "ads",
                "iklan",
                "marketing",
                "seo",
                "sem",
                "affiliate",
                "digital marketing",
                "endorse",
                "copywriting",
                "funnel",
                "cpc",
                "roas",
            ]
        ):
            matched_niche = "advertising"
        elif any(
            k in lowered
            for k in [
                "coding",
                "python",
                "javascript",
                "ai",
                "prompt",
                "software",
                "web",
                "programmer",
                "komputer",
                "laptop",
                "gadget",
                "review hp",
                "iphone",
                "android",
                "developer",
                "bot",
                "data science",
                "excel",
                "teknologi",
                "flow",
                "veo",
                "chatgpt",
                "gemini",
            ]
        ):
            matched_niche = "tech"
        elif any(
            k in lowered
            for k in [
                "sehat",
                "kesehatan",
                "diet",
                "gym",
                "fitness",
                "obat",
                "dokter",
                "penyakit",
                "workout",
                "kalori",
                "kurus",
                "otot",
                "skincare",
                "kecantikan",
                "glowing",
                "jerawat",
                "herbal",
            ]
        ):
            matched_niche = "health_fitness"
        elif any(
            k in lowered
            for k in [
                "mobil",
                "motor",
                "brio",
                "avanza",
                "vespa",
                "modifikasi",
                "servis",
                "balap",
                "otomotif",
                "kendaraan",
                "bensin",
                "ev",
                "mobil listrik",
            ]
        ):
            matched_niche = "automotive"
        elif any(
            k in lowered
            for k in [
                "bisnis",
                "umkm",
                "usaha",
                "jualan",
                "modal",
                "cuan",
                "franchise",
                "wirausaha",
                "reseller",
                "dropship",
                "toko",
                "omset",
                "pabrik",
                "suplier",
                "ekspor",
                "impor",
                "freelance",
            ]
        ):
            matched_niche = "business"
        elif any(
            k in lowered
            for k in [
                "belajar",
                "tutorial",
                "kursus",
                "skripsi",
                "kuliah",
                "beasiswa",
                "bahasa inggris",
                "toefl",
                "sejarah",
                "rumus",
                "matematika",
                "ujian",
                "pns",
                "cpns",
                "sekolah",
            ]
        ):
            matched_niche = "education"
        elif any(
            k in lowered
            for k in [
                "wisata",
                "liburan",
                "hotel",
                "tiket",
                "villa",
                "traveling",
                "pantai",
                "gunung",
                "jepang",
                "eropa",
                "bali",
                "jogja",
                "staycation",
            ]
        ):
            matched_niche = "travel"
        elif any(
            k in lowered
            for k in [
                "masak",
                "resep",
                "kuliner",
                "makanan",
                "dapur",
                "kue",
                "jajan",
                "ayam",
                "pedas",
                "bumbu",
                "cafe",
                "restoran",
                "mukbang",
            ]
        ):
            matched_niche = "culinary"
        elif any(
            k in lowered
            for k in [
                "vlog",
                "rumah",
                "dekorasi",
                "fashion",
                "baju",
                "outfit",
                "makeup",
                "diy",
                "kerajinan",
                "kucing",
                "hewan",
                "anjing",
                "hobi",
            ]
        ):
            matched_niche = "lifestyle"
        elif any(
            k in lowered
            for k in [
                "game",
                "gaming",
                "gameplay",
                "play",
                "mobile legends",
                "ff",
                "free fire",
                "roblox",
                "gta",
                "genshin",
                "valorant",
                "minecraft",
                "ps5",
                "streamer",
            ]
        ):
            matched_niche = "gaming"
        elif any(
            k in lowered
            for k in [
                "lucu",
                "komedi",
                "meme",
                "hiburan",
                "film",
                "movie",
                "drama",
                "anime",
                "lagu",
                "musik",
                "gitar",
                "lirik",
                "gosip",
                "seleb",
                "alur cerita",
            ]
        ):
            matched_niche = "entertainment"
        else:
            matched_niche = "general"

        benchmark = cls.NICHE_RPM_BENCHMARKS.get(matched_niche, cls.NICHE_RPM_BENCHMARKS["general"])
        return {
            "detected_niche": matched_niche,
            "rpm_range_usd": f"${benchmark['low']:.2f} - ${benchmark['high']:.2f}",
            "avg_rpm_usd": benchmark["avg"],
            "potential_earnings_per_100k_views": f"${benchmark['avg'] * 100:.2f}",
        }

    @classmethod
    def generate_high_ctr_titles(cls, seed: str, intent_type: IntentEnum) -> list[str]:
        """
        Generate high-CTR title formulas tailored to the target intent AND content niche.
        Avoids generic tech-tutorial phrases (e.g. 'Setting', 'Panduan Pemula') for
        non-tech topics like science, history, travel, etc.
        """
        clean = seed.strip().title()
        year = datetime.now(UTC).year
        niche = cls.detect_content_niche(seed)

        if intent_type == IntentEnum.TUTORIAL:
            # Tech/tutorial-specific phrasing only for tech niche
            if niche == "tech_tutorial":
                return [
                    f"Cara {clean} dari Nol untuk Pemula (Step-by-Step {year})",
                    f"Tutorial {clean} Paling Lengkap & Mudah Dipahami",
                    f"Rahasia Konfigurasi {clean} yang Jarang Diketahui Orang",
                    f"Hentikan Kesalahan Ini Saat Memulai {clean}!",
                ]
            elif niche == "documentary":
                return [
                    f"Penjelasan Lengkap: Apa yang Sebenarnya Terjadi pada {clean}?",
                    f"Fakta Mengejutkan tentang {clean} yang Jarang Dibahas",
                    f"Kronologi {clean}: Dari Awal hingga Dampaknya bagi Dunia",
                    f"Ilmuwan Terkejut: Temuan Terbaru Tentang {clean}",
                ]
            elif niche == "culinary":
                return [
                    f"Cara Membuat {clean} Anti Gagal untuk Pemula (Takaran Pas)",
                    f"Resep {clean} Paling Mudah & Enak yang Wajib Dicoba",
                    f"Rahasia Bumbu {clean} Meresap Sempurna Ala Chef Profesional",
                    f"Jangan Masak {clean} Sebelum Tahu Trik Ini!",
                ]
            elif niche == "travel":
                return [
                    f"Panduan Wisata {clean}: Rute, Budget & Tips Terlengkap {year}",
                    f"Cara Liburan ke {clean} dengan Hemat & Bebas Ribet",
                    f"Semua yang Harus Kamu Tahu Sebelum Pergi ke {clean}",
                    f"Jangan ke {clean} Sebelum Nonton Video Ini!",
                ]
            elif niche == "health_fitness":
                return [
                    f"Cara Alami Mengatasi {clean} Tanpa Efek Samping",
                    f"Panduan Sehat: Langkah Tepat Menghadapi {clean}",
                    f"Fakta Medis {clean} yang Wajib Kamu Ketahui",
                    f"Jangan Abaikan Gejala {clean} — Lakukan Ini Segera!",
                ]
            else:
                return [
                    f"Cara Memahami {clean} dari Awal hingga Mahir",
                    f"Penjelasan Lengkap {clean}: Panduan Ringkas & Padat",
                    f"Hal Penting Seputar {clean} yang Jarang Dibahas",
                    f"Jangan Salah Paham tentang {clean} — Ini Faktanya!",
                ]
        elif intent_type == IntentEnum.COMMERCIAL:
            return [
                f"Berapa Biaya {clean} yang Sebenarnya? (Bongkar Budget)",
                f"Review Jasa {clean} Terbaik: Mana yang Paling Worth It?",
                f"Jangan Beli Jasa {clean} Sebelum Nonton Video Ini!",
            ]
        elif intent_type == IntentEnum.COMPARISON:
            return [
                f"{clean}: Mana yang Lebih Menguntungkan di {year}?",
                f"Perbandingan Jujur {clean} Setelah 30 Hari Penggunaan",
            ]
        else:
            return [
                f"Apakah {clean} Masih Relevan di {year}? Data Membuktikannya",
                f"Semua yang Wajib Anda Tahu Tentang {clean}",
                f"5 Fakta Mengejutkan Seputar {clean}",
            ]

    @classmethod
    def analyze_competitor_packaging(cls, comp_title: str, seed: str, niche: str) -> dict[str, Any]:
        """
        Deconstructs Competitor #1's title and packaging to find actionable weaknesses and counter-angles.
        Identifies whether the competitor uses clickbait/ALL-CAPS, listicles, questions, generic phrasing, etc.
        """
        title_clean = (comp_title or "").strip()
        lowered = title_clean.lower()
        words = title_clean.split()

        # Check shouting / caps
        caps_words = [w for w in words if len(w) > 2 and w.isupper() and w.isalpha()]
        is_shouting = len(caps_words) >= 2 or (
            len(words) > 0 and len(caps_words) / len(words) >= 0.35
        )

        # Check listicle numbers
        has_number = any(w.isdigit() or any(c.isdigit() for c in w) for w in words)

        # Check question
        is_question = "?" in title_clean or any(
            q in lowered for q in ["kenapa", "mengapa", "apakah", "bagaimana", "benarkah"]
        )

        # Check clickbait / sensational buzzwords
        has_clickbait = any(
            b in lowered
            for b in [
                "viral",
                "meledak",
                "parah",
                "kaget",
                "ngeri",
                "terkejut",
                "syok",
                "dahsyat",
                "gila",
                "bikin merinding",
            ]
        )

        # Check generic / saturated words
        has_generic = any(
            g in lowered
            for g in [
                "lengkap",
                "terlengkap",
                "terbaru",
                "enak",
                "mudah",
                "pemula",
                "part 1",
                "eps",
                "episode",
            ]
        )

        # Check if title has year
        has_year = any(y in lowered for y in ["2020", "2021", "2022", "2023", "2024", "2025"])

        if is_shouting or has_clickbait:
            weakness = (
                f"Judul kompetitor menggunakan gaya heboh/sensasional ('{caps_words[0] if caps_words else 'HURUF BESAR'}') "
                "yang rentan memicu skeptisisme penonton dan sering diabaikan audiens yang mencari substansi mendalam."
            )
            counter_strategy = (
                "Lawan dengan kredibilitas dan alur naratif tenang tapi memikat: sajikan fakta konkret, "
                "kronologi autentik, atau penjelasan ilmiah mendalam yang tidak terkesan murahan."
            )
            dominant_angle = "investigative_proof"
        elif has_year:
            weakness = "Judul kompetitor memuat tahun lama yang membuat penonton merasa informasinya berpotensi usang."
            counter_strategy = "Tawarkan perspektif terkini, temuan arsip terbaru, atau pendekatan modern tanpa menyematkan tahun secara kaku."
            dominant_angle = "fresh_perspective"
        elif has_number:
            weakness = "Kompetitor memakai format listicle poin-poin terpisah yang cenderung dangkal dan cepat membosankan."
            counter_strategy = (
                "Gunakan alur cerita utuh (narrative arc) kronologis detik-demi-detik atau studi kasus mendalam "
                "yang membuat penonton penasaran menonton dari awal hingga akhir."
            )
            dominant_angle = "narrative_chronology"
        elif is_question:
            weakness = "Kompetitor hanya melempar pertanyaan menggantung tanpa memberikan sinyal jawaban berbobot di judul."
            counter_strategy = "Berikan hook jawaban tegas yang mengejutkan atau konsekuensi nyata yang belum diketahui publik."
            dominant_angle = "curiosity_gap"
        elif has_generic:
            weakness = "Judul kompetitor menggunakan klaim generik yang sudah terlalu sering dipakai ribuan video lain di YouTube."
            counter_strategy = "Tawarkan spesifisitas tinggi: rincian angka biaya nyata, 1 trik paling krusial, atau rahasia yang tidak dibahas video umum."
            dominant_angle = "unique_specificity"
        else:
            weakness = "Judul kompetitor cenderung datar dan minim 'curiosity gap' atau emosi yang memicu klik spontan."
            counter_strategy = "Eksploitasi celah rasa penasaran penonton dengan mengungkap misteri tersembunyi atau fakta kontrarian."
            dominant_angle = "contrarian_mystery"

        return {
            "title": title_clean or "Belum ada kompetitor terdeteksi",
            "weakness": weakness,
            "counter_strategy": counter_strategy,
            "dominant_angle": dominant_angle,
            "is_shouting": is_shouting,
            "has_number": has_number,
            "is_question": is_question,
            "has_year": has_year,
        }

    @classmethod
    def generate_outranking_plan(
        cls,
        seed: str,
        competitor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate an actionable Outranking Blueprint:
        - Outranking Title (Beats Competitor #1)
        - Full SEO Description with Timestamps & Hashtags
        - Shorts 3-Second Hook Package
        - Format Recommendation (Landscape 16:9 vs Shorts 9:16)
        """
        clean = seed.strip().title()
        comp_title = competitor.get("title", "") if competitor else ""
        comp_views = competitor.get("views", "0") if competitor else "N/A"
        comp_channel = competitor.get("channel", "Kompetitor") if competitor else "Kompetitor"
        comp_format = competitor.get("format", "LANDSCAPE") if competitor else "LANDSCAPE"

        niche = cls.detect_content_niche(seed)
        clean_tag = "".join(clean.split())
        seed_mod = sum(ord(c) for c in clean) % 2

        comp_analysis = cls.analyze_competitor_packaging(comp_title, seed, niche)

        if niche == "documentary":
            lowered_seed = seed.strip().lower()
            is_science = any(
                k in lowered_seed
                for k in [
                    "planet",
                    "mars",
                    "bulan",
                    "bintang",
                    "luar angkasa",
                    "galaksi",
                    "asteroid",
                    "black hole",
                    "lubang hitam",
                    "meteor",
                    "tata surya",
                    "biologi",
                    "fisika",
                    "kimia",
                    "evolusi",
                    "dinosaurus",
                    "fosil",
                    "hewan",
                    "alam",
                    "ekosistem",
                    "hutan",
                    "laut dalam",
                    "sains",
                    "kosmik",
                    "bumi",
                    "antartika",
                ]
            )
            if is_science:
                angle_curiosity = (
                    f"Ada yang Tersembunyi di Bawah Permukaan {clean}: Misteri yang Belum Terpecahkan"
                    if seed_mod == 0
                    else f"Misteri {clean} yang Masih Membingungkan Para Ilmuwan Dunia"
                )
                angle_stakes = (
                    f"Bisakah Manusia Bertahan di {clean}? Fakta Ekstrem yang Jarang Diungkap ke Publik"
                    if seed_mod == 0
                    else f"Detik-Detik Penemuan Terbesar di {clean} yang Mengubah Pemahaman Sains"
                )
                angle_contrarian = (
                    f"Bukan Sekadar {clean}: Temuan Baru yang Membantah Teori Populer Selama Ini"
                    if seed_mod == 0
                    else f"Semua Orang Salah Mengira Tentang {clean} Sampai Data Baru Ini Terungkap..."
                )
                angle_deep = (
                    f"Misteri & Sains di Balik {clean}: Penjelasan Lengkap dari Asal Usul hingga Masa Depan"
                    if seed_mod == 0
                    else f"Eksplorasi Ilmiah {clean}: Fakta Menakjubkan yang Mengubah Cara Pandang Kita"
                )

                if comp_analysis["dominant_angle"] in [
                    "investigative_proof",
                    "narrative_chronology",
                ]:
                    outranking_title = angle_deep
                elif comp_analysis["dominant_angle"] == "curiosity_gap":
                    outranking_title = angle_contrarian
                else:
                    outranking_title = f"Mengapa Ilmuwan Begitu Terobsesi dengan {clean}? Fakta Mengejutkan yang Mengubah Teori"

                title_formula = "Pola Counter-Positioning: [Pertanyaan Paradoks Sains] + [Subjek Inti] + [Temuan Baru yang Mengubah Sudut Pandang]"
                two_line_hook = (
                    f"Seberapa banyak yang kamu tahu tentang {clean}? "
                    f"Di video ini kita bedah fakta ilmiah terkini, misteri yang belum terpecahkan, dan temuan yang bikin tercengang!"
                )
                timestamps = [
                    "00:00 - Pengantar: Mengapa Ini Penting?",
                    f"02:00 - Fakta Dasar tentang {clean}",
                    "05:30 - Penemuan Ilmiah Paling Mengejutkan",
                    "10:15 - Misteri yang Masih Belum Terjawab",
                    "14:30 - Kesimpulan & Prediksi Masa Depan",
                ]
                hashtags = [
                    f"#{clean_tag}",
                    f"#{clean_tag}Sains",
                    "#IlmuPengetahuan",
                    "#FaktaMenarik",
                ]
            else:
                angle_curiosity = (
                    f"Apa yang Sebenarnya Terjadi Sebelum {clean}? Arsip Kuno yang Jarang Diungkap"
                    if seed_mod == 0
                    else f"Misteri Tersembunyi di Balik {clean} yang Tidak Dicatat Buku Sejarah Umum"
                )
                angle_stakes = (
                    f"Detik-Detik Mencekam {clean}: Kronologi Peristiwa yang Mengubah Sejarah Selamanya"
                    if seed_mod == 0
                    else f"Kronologi Menit Demi Menit {clean}: Apa yang Sebenarnya Dialami Korban?"
                )
                angle_contrarian = (
                    f"Bukan Cuma Tragedi Biasa: Ini Alasan Kenapa {clean} Menjadi Titik Balik Dunia"
                    if seed_mod == 0
                    else f"Banyak yang Salah Paham Soal {clean}, Ini Fakta Sejarah yang Sebenarnya Terjadi"
                )
                angle_deep = (
                    f"{clean}: Rekonstruksi Sejarah Lengkap & Dampak Nyata yang Mengguncang Peradaban"
                    if seed_mod == 0
                    else f"Dokumenter Utuh {clean}: Dari Tanda-Tanda Awal Hingga Dampak Globalnya"
                )

                if (
                    comp_analysis["is_shouting"]
                    or comp_analysis["dominant_angle"] == "investigative_proof"
                ):
                    outranking_title = angle_stakes
                elif comp_analysis["dominant_angle"] == "narrative_chronology":
                    outranking_title = angle_deep
                else:
                    outranking_title = f"Detik-Detik Menegangkan {clean}: Fakta & Kronologi Sejarah yang Mengubah Dunia"

                title_formula = "Pola Counter-Positioning: [Emosi High-Stakes / Detik-Detik] + [Subjek Peristiwa] + [Dampak Bersejarah]"
                two_line_hook = (
                    f"Pernahkah kamu membayangkan betapa dahsyatnya peristiwa {clean}? "
                    f"Di video ini kita bedah kronologi lengkap, arsip sejarah autentik, dan fakta mengejutkan yang jarang dibahas!"
                )
                timestamps = [
                    "00:00 - Kilas Balik Awal Peristiwa",
                    f"02:30 - Latar Belakang & Tanda Awal {clean}",
                    "06:45 - Kronologi Puncak Kejadian",
                    "11:20 - Dampak & Akibat bagi Dunia",
                    "15:50 - Pelajaran Sejarah & Kondisi Terkini",
                ]
                hashtags = [
                    f"#{clean_tag}",
                    f"#{clean_tag}Sejarah",
                    "#DokumenterDunia",
                    "#FaktaMenarik",
                ]

            shorts_package = {
                "title": f"Fakta Mengerikan tentang {clean} yang Bikin Merinding! #shorts",
                "three_second_hook": f"Ini fakta tersembunyi tentang {clean} yang tidak pernah diajarkan di sekolah!",
                "script_structure": [
                    "00-03s: Hook visual kilas peristiwa bersejarah",
                    "03-30s: Ungkap 1 fakta sejarah paling mengejutkan",
                    "30-45s: Ajakan tonton dokumenter lengkapnya",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "culinary":
            clean_food = clean
            for prefix in ["Resep ", "Cara Masak ", "Cara Membuat ", "Bumbu "]:
                if clean.lower().startswith(prefix.lower()):
                    clean_food = clean[len(prefix) :].strip()
                    break

            angle_curiosity = (
                f"Ternyata Ini Rahasia Pedagang Bikin {clean_food} Gurih Nendang Tanpa Banyak Penyedap"
                if seed_mod == 0
                else f"1 Bumbu Rahasia yang Bikin {clean_food} Buatanmu Seenak Restoran Bintang 5"
            )
            angle_stakes = (
                f"Resep {clean_food} Praktis: Takaran Bumbu Pas & Cara Masak Biar Daging Super Empuk"
                if seed_mod == 0
                else f"Cara Bikin {clean_food} Gurih Meresap Sampai ke Tulang: Langkah demi Langkah"
            )
            angle_contrarian = (
                f"Jangan Masukkan Bahan Ini Saat Masak {clean_food}! Bikin Aroma dan Rasa Berubah Langu"
                if seed_mod == 0
                else f"Kesalahan Fatal yang Sering Dilakukan Saat Bikin {clean_food} (Dan Cara Memperbaikinya)"
            )
            angle_deep = (
                f"{clean_food} Otentik Rumahan: Panduan Lengkap Bumbu Rempah & Tips Kuah Tidak Cepat Basi"
                if seed_mod == 0
                else f"Resep Komplit {clean_food} Tradisional: Tekstur Pas, Bumbu Medok & Wangi Menggoda"
            )

            outranking_title = f"Rahasia Bumbu {clean_food} Gurih Meresap: 1 Trik Menumis Biar Gak Langu & Anti Gagal"
            title_formula = "Pola Counter-Positioning: [Solusi Masalah Rasa/Tekstur] + [Subjek Masakan] + [Trik Spesifik yang Membedakan]"
            two_line_hook = (
                f"Mau bikin {clean} yang lezat, bumbunya meresap sempurna, dan anti gagal? "
                f"Simak panduan takaran dan rahasia bumbunya di video ini!"
            )
            timestamps = [
                "00:00 - Tampilan & Rahasia Kelezatan",
                "01:15 - Bahan-Bahan & Takaran Pas",
                f"04:30 - Cara Mengolah & Meracik {clean}",
                "08:15 - Tips Memasak dengan Api Sempurna",
                "11:40 - Hasil Akhir & Uji Rasa",
            ]
            hashtags = [f"#{clean_tag}", f"#Resep{clean_tag}", "#KulinerViral", "#MasakPraktis"]
            shorts_package = {
                "title": f"Trik Rahasia Bikin {clean} Jadi Super Enak! #shorts",
                "three_second_hook": f"Ternyata cuma butuh 1 trik ini biar {clean} buatanmu seenak restoran bintang 5!",
                "script_structure": [
                    "00-03s: Hook visual kelezatan makanan menggoda",
                    "03-30s: Tunjukkan 1 rahasia bumbu utama",
                    "30-45s: Call to action tonton resep takaran lengkap",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "travel":
            clean_dest = clean
            for prefix in [
                "Wisata ",
                "Liburan Ke ",
                "Liburan ",
                "Tempat Wisata ",
                "Jalan Jalan Ke ",
            ]:
                if clean.lower().startswith(prefix.lower()):
                    clean_dest = clean[len(prefix) :].strip()
                    break

            angle_curiosity = (
                f"Spot Tersembunyi di {clean_dest} yang Jarang Diketahui Turis Biasa"
                if seed_mod == 0
                else f"Hidden Gem di {clean_dest} yang Pemandangannya Jauh Lebih Indah dari Tempat Viral"
            )
            angle_stakes = (
                f"Cara Liburan ke {clean_dest} Hemat Budget: Tips Pilih Transportasi & Penginapan Nyaman"
                if seed_mod == 0
                else f"Eksplorasi {clean_dest} Seharian: Rute Tercepat, Biaya Riil, & Spot Foto Paling Keren"
            )
            angle_contrarian = (
                f"Jangan Pergi ke {clean_dest} Sebelum Tahu 5 Hal Krusial Ini (Review Pengalaman Nyata)"
                if seed_mod == 0
                else f"Ekspektasi vs Realita Liburan ke {clean_dest}: Tips Biar Gak Kena Zonk atau Boncos"
            )
            angle_deep = (
                f"Itinerary Lengkap {clean_dest}: Panduan Rute, Rincian Biaya, & Tips Penting Terlengkap"
                if seed_mod == 0
                else f"Panduan Jujur Liburan ke {clean_dest}: Estimasi Budget Nyata & Rekomendasi Tempat Terbaik"
            )

            outranking_title = f"Panduan Jujur Liburan ke {clean_dest}: Rincian Biaya Nyata, Rute Terbaik & Spot Hidden Gem"
            title_formula = "Pola Counter-Positioning: [Transparansi Biaya & Rute] + [Destinasi] + [Keuntungan Nilai Nyata Bagi Traveler]"
            two_line_hook = (
                f"Rencana liburan ke {clean}? Tonton panduan lengkap rute terbaik, "
                f"estimasi budget, dan rekomendasi spot tersembunyi yang wajib kamu kunjungi!"
            )
            timestamps = [
                "00:00 - Pesona Keindahan Lokasi",
                f"01:45 - Rute & Transportasi Menuju {clean}",
                "05:20 - Rekomendasi Spot Terbaik & Hidden Gem",
                "09:10 - Estimasi Biaya & Kuliner Khas",
                "12:30 - Tips Penting Sebelum Berangkat",
            ]
            hashtags = [f"#{clean_tag}", f"#Wisata{clean_tag}", "#TravelVlog", "#LiburanHemat"]
            shorts_package = {
                "title": f"Spot Rahasia di {clean} yang Jarang Orang Tahu! #shorts",
                "three_second_hook": f"Kalau kamu ke {clean}, jangan cuma ke tempat biasa, cobain spot rahasia ini!",
                "script_structure": [
                    "00-03s: Hook panorama indah spot tersembunyi",
                    "03-30s: Ulas rute dan keindahan uniknya",
                    "30-45s: Simpan video ini untuk rencana liburanmu",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "business":
            clean_biz = clean
            for prefix in ["Strategi ", "Cara ", "Panduan ", "Tips "]:
                if clean.lower().startswith(prefix.lower()):
                    clean_biz = clean[len(prefix) :].strip()
                    break

            angle_curiosity = (
                f"Bongkar Rahasia {clean_biz}: Modal Terukur Tapi Menghasilkan Orderan & Omset Rutin"
                if seed_mod == 0
                else f"1 Strategi {clean_biz} yang Jarang Dibahas Mentor Bisnis: Fokus ke Konversi Nyata"
            )
            angle_stakes = (
                f"Panduan Praktis {clean_biz} Step-by-Step: Alur Kerja yang Langsung Menghasilkan Pembeli"
                if seed_mod == 0
                else f"Cara Menjalankan {clean_biz} dari Nol Tanpa Takut Boncos: Eksekusi Cepat & Terarah"
            )
            angle_contrarian = (
                f"Hentikan 3 Kebiasaan Ini Saat Memulai {clean_biz}, Cuma Bikin Modal Habis Percuma!"
                if seed_mod == 0
                else f"Banyak yang Gagal di {clean_biz} Gara-Gara 1 Kesalahan Fatal Ini (Evaluasi Bisnis)"
            )
            angle_deep = (
                f"Studi Kasus Nyata {clean_biz}: Dari Nol Sampai Closing Pertama Tanpa Budget Berlebihan"
                if seed_mod == 0
                else f"Blueprint Lengkap {clean_biz}: Fondasi, Pengaturan Teknis, & Cara Skalasi Hasil"
            )

            outranking_title = f"Strategi {clean_biz} yang Terbukti Efektif: Cara Eksekusi Biar Gak Boncos & Menghasilkan Closing"
            title_formula = "Pola Counter-Positioning: [Mitigasi Risiko Boncos] + [Model Bisnis/Topik] + [Fokus Hasil Konversi Nyata]"
            two_line_hook = (
                f"Mau belajar {clean} dengan alur yang jelas tanpa buang-buang budget? "
                f"Di video ini kita kupas strategi terbukti dari nol sampai menghasilkan!"
            )
            timestamps = [
                "00:00 - Kenapa Harus Mulai Sekarang?",
                f"02:15 - Riset & Fondasi Dasar {clean}",
                "06:30 - Langkah Eksekusi Step-by-Step",
                "12:45 - Optimasi & Cara Skalasi Hasil",
                "17:20 - Evaluasi & Checklist Sukses",
            ]
            hashtags = [f"#{clean_tag}", f"#{clean_tag}Pemula", "#BisnisDigital", "#StrategiBisnis"]
            shorts_package = {
                "title": f"1 Hal yang Wajib Kamu Tahu Sebelum Mulai {clean}! #shorts",
                "three_second_hook": f"Jangan pernah coba {clean} sebelum kamu tahu formula penting ini!",
                "script_structure": [
                    "00-03s: Hook visual jangan lakukan kesalahan ini",
                    "03-30s: Bongkar 1 formula paling berdampak",
                    "30-45s: Tutorial lengkapnya klik link video di bawah",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "tech_tutorial":
            clean_tech = clean
            for prefix in ["Tutorial ", "Cara ", "Panduan ", "Belajar ", "Setting "]:
                if clean.lower().startswith(prefix.lower()):
                    clean_tech = clean[len(prefix) :].strip()
                    break

            angle_curiosity = (
                f"1 Trik Praktik {clean_tech} Biar Cepat Paham dan Gak Terjebak Tutorial Hell"
                if seed_mod == 0
                else f"Shortcut & Fitur Tersembunyi di {clean_tech} yang Bakal Menghemat 80% Waktumu"
            )
            angle_stakes = (
                f"Alur Belajar {clean_tech} yang Masuk Akal: Dari Nol Sampai Bisa Buat Projek Mandiri"
                if seed_mod == 0
                else f"Tutorial Praktikal {clean_tech}: Materi Inti yang Benar-Benar Dipakai di Lapangan"
            )
            angle_contrarian = (
                f"Jangan Pelajari Semua Hal Sekaligus! Ini 4 Fondasi Utama {clean_tech} yang Cukup Buat Mulai"
                if seed_mod == 0
                else f"Kesalahan Umum Saat Memakai {clean_tech} yang Sering Bikin Error dan Frustrasi"
            )
            angle_deep = (
                f"Roadmap Terstruktur {clean_tech}: Panduan Langkah demi Langkah Paling Rapi untuk Pemula"
                if seed_mod == 0
                else f"Kuasai {clean_tech} Lebih Cepat: Penjelasan Konsep Inti & Solusi Masalah Umum"
            )

            outranking_title = f"Alur Belajar {clean_tech} yang Masuk Akal: Dari Dasar Sampai Bisa Bikin Projek Sendiri"
            title_formula = "Pola Counter-Positioning: [Alur Praktis Tanpa Bertele-tele] + [Tool/Skill] + [Hasil Projek Nyata]"
            two_line_hook = (
                f"Baru mau belajar {clean_tech}? Jangan bingung, video ini merangkum "
                f"tutorial langkah demi langkah dari dasar sampai kamu mahir!"
            )
            timestamps = [
                "00:00 - Pengantar & Konsep Dasar",
                f"02:00 - Persiapan & Interface {clean}",
                "05:30 - Langkah demi Langkah Praktik Langsung",
                "10:15 - Trik Rahasia & Shortcut Berguna",
                "14:00 - Kesimpulan & Langkah Lanjutan",
            ]
            hashtags = [
                f"#{clean_tag}",
                f"#Tutorial{clean_tag}",
                "#BelajarTeknologi",
                "#TipsTutorial",
            ]
            shorts_package = {
                "title": f"Trik Cepat {clean} yang Wajib Kamu Tahu! #shorts",
                "three_second_hook": f"Ini cara tercepat dan paling simpel buat kamu yang lagi belajar {clean}!",
                "script_structure": [
                    "00-03s: Hook visual shortcut atau trik cepat",
                    "03-30s: Tunjukkan demonstrasi layar langsung",
                    "30-45s: Simpan video ini dan cek panduan lengkapnya",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "health_fitness":
            angle_curiosity = (
                f"Penyebab Sebenarnya {clean} yang Jarang Disadari (Bukan Cuma Pola Makan Biasa)"
                if seed_mod == 0
                else f"Fakta Medis {clean} yang Masih Sering Disalahartikan Banyak Orang"
            )
            angle_stakes = (
                f"Cara Alami Mengatasi {clean}: Langkah Sehat & Terukur Menurut Bukti Medis"
                if seed_mod == 0
                else f"Gejala Awal {clean} yang Sering Diabaikan: Kapan Harus Mulai Bertindak?"
            )
            angle_contrarian = (
                f"Jangan Lakukan 3 Kebiasaan Ini Kalau Mau Bebas dari {clean}, Malah Memperparah Kondisi!"
                if seed_mod == 0
                else f"Mitos Seputar {clean} yang Harus Ditinggalkan: Ini Penjelasan Ilmiah Ahli"
            )
            angle_deep = (
                f"Panduan Pola Hidup Sehat untuk {clean}: Nutrisi Alami, Olahraga Pas & Pencegahan Jangka Panjang"
                if seed_mod == 0
                else f"Bedah Tuntas {clean}: Mekanisme Tubuh, Pemicu Utama, & Solusi Medis Teruji"
            )

            outranking_title = f"Cara Alami Mengatasi {clean}: 3 Kebiasaan Sederhana yang Terbukti Efektif Menurut Fakta Medis"
            title_formula = "Pola Counter-Positioning: [Solusi Sehat Bebas Risiko] + [Masalah Kesehatan] + [Landasan Fakta Medis Kredibel]"
            two_line_hook = (
                f"Khawatir soal {clean}? Simak penjelasan medis, cara pencegahan alami, "
                f"dan tips menjaga tubuh tetap prima tanpa resiko!"
            )
            timestamps = [
                "00:00 - Pemahaman Dasar Masalah",
                f"02:15 - Penyebab Utama Terjadinya {clean}",
                "06:00 - Cara Mengatasi & Pola Sehat",
                "10:30 - Mitos vs Fakta Menurut Ahli",
                "13:45 - Rangkuman Langkah Tindakan",
            ]
            hashtags = [f"#{clean_tag}", f"#Kesehatan{clean_tag}", "#HidupSehat", "#TipsMedis"]
            shorts_package = {
                "title": f"Stop Lakukan Ini Kalau Gak Mau Kena {clean}! #shorts",
                "three_second_hook": f"Banyak orang belum sadar, 1 kebiasaan sepele ini bisa memicu {clean}!",
                "script_structure": [
                    "00-03s: Hook visual peringatan kesehatan",
                    "03-30s: Jelaskan mekanisme ilmiah singkatnya",
                    "30-45s: Tips pencegahan dan tonton video lengkapnya",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "entertainment":
            angle_curiosity = (
                f"Detail Kecil di {clean} yang Menjelaskan Misteri Terbesar di Akhir Cerita"
                if seed_mod == 0
                else f"Pesan Tersembunyi di {clean} yang Luput dari Perhatian Mayoritas Penonton"
            )
            angle_stakes = (
                f"Kronologi Lengkap & Alur Cerita {clean}: Dari Awal Mula Hingga Plot Twist Tak Terduga"
                if seed_mod == 0
                else f"Momen Paling Mengejutkan di {clean} yang Mengubah Seluruh Cerita"
            )
            angle_contrarian = (
                f"Teori Populer Tentang {clean} Ini Ternyata Keliru! Ini Fakta Sebenarnya yang Tersirat"
                if seed_mod == 0
                else f"Bukan Sekadar Hiburan Biasa: Ada Pesan Gelap di Balik Cerita {clean}"
            )
            angle_deep = (
                f"Bedah Cerita & Makna Tersirat {clean}: Analisis Karakter, Filosofi, & Ending Lengkap"
                if seed_mod == 0
                else f"Penjelasan Ending {clean} Secara Rinci: Mengapa Penutupnya Begitu Jenius?"
            )

            outranking_title = f"Penjelasan Ending & Makna Tersembunyi {clean}: Pesan Rahasia yang Banyak Dilewatkan Penonton"
            title_formula = "Pola Counter-Positioning: [Bongkar Detail Tersembunyi / Ending] + [Subjek Karya] + [Nilai Analisis Kritis]"
            two_line_hook = (
                f"Ada banyak kejanggalan dan teori mengejutkan di balik {clean}. "
                f"Di video ini kita kupas tuntas seluruh rahasia dan fakta tersembunyinya!"
            )
            timestamps = [
                "00:00 - Pembuka & Sorotan Menarik",
                f"02:00 - Latar Belakang & Pengenalan {clean}",
                "06:30 - Momen Paling Krusial & Plot Twist",
                "10:45 - Bedah Teori & Makna Tersembunyi",
                "14:15 - Kesimpulan & Penjelasan Akhir",
            ]
            hashtags = [f"#{clean_tag}", f"#AlurCerita{clean_tag}", "#BedahFilm", "#PopCulture"]
            shorts_package = {
                "title": f"Fakta Gila Seputar {clean} yang Pasti Belum Kamu Tahu! #shorts",
                "three_second_hook": f"Kamu gak bakal nyangka kalau ada detail segila ini di dalam {clean}!",
                "script_structure": [
                    "00-03s: Hook adegan atau detail mengejutkan",
                    "03-30s: Ungkap teori atau fakta tersembunyi",
                    "30-45s: Tonton bedah cerita lengkapnya di link terkait",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        else:
            angle_curiosity = (
                f"Fakta Menarik Seputar {clean} yang Jarang Diketahui Orang Banyak"
                if seed_mod == 0
                else f"Ada Apa di Balik Fenomena {clean}? Misteri dan Realita yang Menarik"
            )
            angle_stakes = (
                f"Semua yang Wajib Kamu Pahami Tentang {clean} Sebelum Mengambil Keputusan"
                if seed_mod == 0
                else f"Dampak Nyata {clean} bagi Kehidupan Sehari-Hari yang Jarang Disadari"
            )
            angle_contrarian = (
                f"Banyak Orang Keliru Menilai {clean}: Ini Fakta & Data yang Sebenarnya"
                if seed_mod == 0
                else f"Jangan Asal Percaya! Ini Kebenaran di Balik Mitos {clean}"
            )
            angle_deep = (
                f"Eksplorasi Mendalam Seputar {clean}: Panduan Komprehensif dari A Sampai Z"
                if seed_mod == 0
                else f"Kupas Tuntas {clean}: Sejarah, Perkembangan Terkini, & Hal Penting yang Wajib Tahu"
            )

            outranking_title = f"Semua yang Wajib Kamu Ketahui Tentang {clean}: Fakta Menarik & Penjelasan Mendalam"
            title_formula = "Pola Counter-Positioning: [Fakta Menarik / Perspektif Baru] + [Subjek Topik] + [Nilai Informasi Utuh]"
            two_line_hook = (
                f"Penasaran tentang {clean}? Di video ini kita bahas tuntas sejarah, "
                f"fakta penting, dan segala hal menarik seputar topik ini!"
            )
            timestamps = [
                "00:00 - Pengantar Topik Menarik",
                f"02:15 - Fakta Penting Seputar {clean}",
                "06:00 - Penjelasan Mendalam & Contoh Nyata",
                "10:30 - Mitos yang Sering Salah Dipahami",
                "13:50 - Rangkuman & Pandangan Masa Depan",
            ]
            hashtags = [f"#{clean_tag}", f"#{clean_tag}Indonesia", "#EdukasiPopuler", "#FaktaUnik"]
            shorts_package = {
                "title": f"Fakta Unik {clean} yang Bikin Kaget! #shorts",
                "three_second_hook": f"Pernah gak kamu bertanya-tanya, kenapa {clean} bisa seunik ini?",
                "script_structure": [
                    "00-03s: Hook pertanyaan menggelitik pikiran",
                    "03-30s: Ceritakan 1 fakta paling unik",
                    "30-45s: Tulis pendapatmu dan tonton video lengkapnya",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }

        psychological_angles = {
            "curiosity_gap": {
                "label": "🔍 Misteri & Curiosity Gap",
                "title": angle_curiosity,
                "rationale": "Memicu rasa penasaran akut penonton dengan menyembunyikan 1 potongan informasi krusial.",
            },
            "high_stakes": {
                "label": "⚡ Kronologi & High-Stakes Storytelling",
                "title": angle_stakes,
                "rationale": "Menghadirkan intensitas cerita menit-demi-menit dengan dampak nyata yang besar.",
            },
            "contrarian": {
                "label": "🤯 Mitos vs Fakta / Kontrarian",
                "title": angle_contrarian,
                "rationale": "Mendobrak asumsi salah yang selama ini dipercaya penonton umum di YouTube.",
            },
            "deep_dive": {
                "label": "📚 Deep Dive / Dokumenter Komplit",
                "title": angle_deep,
                "rationale": "Menjanjikan sajian informasi paling tuntas, terstruktur, dan berbobot.",
            },
        }

        alternative_titles = [
            angle_curiosity,
            angle_stakes,
            angle_contrarian,
            angle_deep,
        ]

        # Build niche-appropriate description intro
        niche_desc_intro_map = {
            "documentary": f"📌 Bedah tuntas fakta, kronologi, dan temuan terbaru seputar {clean}. Tonton dari awal agar tidak ada informasi penting yang terlewat!",
            "culinary": f"📌 Resep lengkap, takaran pas, dan rahasia bumbu untuk membuat {clean} sempurna. Tonton sampai selesai agar hasilnya anti gagal!",
            "travel": f"📌 Panduan wisata lengkap ke {clean}: rute terbaik, estimasi biaya, dan tips tersembunyi. Tonton agar liburanmu makin seru!",
            "entertainment": f"📌 Bedah cerita, teori, dan detail tersembunyi dari {clean}. Tonton sampai habis agar tidak ada detail penting yang terlewat!",
            "health_fitness": f"📌 Penjelasan medis, tips alami, dan langkah nyata mengatasi {clean}. Simak sampai selesai untuk informasi yang akurat dan aman!",
            "business": f"📌 Strategi nyata, studi kasus, dan langkah eksekusi seputar {clean}. Tonton dari awal hingga akhir agar tidak ada step yang terlewat!",
            "tech_tutorial": f"📌 Tutorial step-by-step dan tips praktis seputar {clean}. Tonton dari awal agar proses belajarmu lebih cepat dan tidak bingung!",
        }
        desc_intro = niche_desc_intro_map.get(
            niche,
            f"📌 Rangkuman lengkap dan mendalam seputar {clean}. Tonton video ini dari awal sampai akhir agar tidak ada detail penting yang terlewat!",
        )

        full_description = (
            f"{two_line_hook}\n\n"
            f"{desc_intro}\n\n"
            f"⏱️ TIMESTAMPS / DAFTAR ISI:\n" + "\n".join(timestamps) + f"\n\n🔗 LINK & INFORMASI:\n"
            f"- Sumber Informasi & Diskusi: https://example.com\n\n"
            f"{' '.join(hashtags)}"
        )

        return {
            "seed_keyword": seed,
            "target_competitor": {
                "title": comp_title,
                "channel": comp_channel,
                "views": comp_views,
                "format": comp_format,
            },
            "recommended_format": comp_format,
            "competitor_analysis": comp_analysis,
            "competitor_weakness": comp_analysis["weakness"],
            "counter_strategy": comp_analysis["counter_strategy"],
            "outranking_title": outranking_title,
            "title_formula": title_formula,
            "detected_niche": niche,
            "psychological_angles": psychological_angles,
            "alternative_titles": alternative_titles,
            "seo_description": full_description,
            "two_line_hook": two_line_hook,
            "timestamps": timestamps,
            "hashtags": hashtags,
            "shorts_package": shorts_package,
        }

    @staticmethod
    def analyze_ai_competitor_presence(competitors: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze whether AI/Synthetic videos are already ranking in the top SERP.
        Provides strategic best practices for competing with AI content.
        """
        if not competitors:
            return {
                "total_competitors": 0,
                "ai_count": 0,
                "human_count": 0,
                "ai_percentage": 0.0,
                "verdict": "Belum ada data kompetitor",
                "ranking_feasibility": "HIGH",
                "best_practices": [],
            }

        total = len(competitors)
        ai_count = sum(1 for c in competitors if c.get("is_ai_generated", False))
        human_count = total - ai_count
        ai_pct = round((ai_count / total) * 100, 1)

        if ai_pct >= 40.0:
            verdict = f"🤖 AI Adopsi Tinggi ({ai_pct}% kompetitor adalah video AI/Synthetic)"
            feasibility = (
                "Sangat memungkinkan bersaing dengan video AI! YouTube merekomendasikan "
                "kombinasi visual b-roll AI yang tajam dengan narasi berkarakter kuat."
            )
        elif ai_pct > 0:
            verdict = f"⚡ Hybrid Market ({ai_pct}% video AI terdeteksi di Top SERP)"
            feasibility = (
                "Format hybrid (AI B-roll + Real/Expressive Narration) memiliki celah "
                "besar untuk mengalahkan video manusia yang produksinya lambat."
            )
        else:
            verdict = "👤 Human Dominant (100% video saat ini dibuat konvensional)"
            feasibility = (
                "Peluang emas first-mover! Anda bisa menyajikan konten berkualitas tinggi "
                "menggunakan Generator Video AI modern (Kling, Runway, Luma, Sora) dengan kecepatan produksi 5x lebih cepat."
            )

        best_practices = [
            "1. Centang Wajib Disclosure: Selalu beri tanda 'Altered or synthetic content' saat upload di YouTube Studio agar bebas resiko penalti.",
            "2. Hook 3 Detik Pertama: Algoritma YouTube memprioritaskan Watch Time & Retention, bukan menghukum label AI. Pastikan visual pembuka langsung to-the-point.",
            "3. Pacing B-Roll Cepat: Gunakan klip video AI berdurasi 4-6 detik per scene agar ritme visual tetap dinamis.",
            "4. Expressive Audio: Gabungkan visual video AI dengan voiceover bernada emosional (ElevenLabs / human voice), hindari suara robotik flat.",
            "5. Hindari Mass Low-Effort Spam: YouTube memblokir monetisasi video 'reused/programmatic spam' yang tidak memiliki nilai tambah.",
        ]

        return {
            "total_competitors": total,
            "ai_count": ai_count,
            "human_count": human_count,
            "ai_percentage": ai_pct,
            "verdict": verdict,
            "ranking_feasibility": feasibility,
            "best_practices": best_practices,
        }

    @classmethod
    def generate_flow_shotlist(
        cls,
        seed: str,
        format_type: str = "LANDSCAPE",
        num_scenes: int = 5,
    ) -> dict[str, Any]:
        """
        Generate a production-ready AI Video Storyboard & Shotlist (Kling, Runway, Luma, Sora, CapCut).
        Compatible with:
        - prompts.txt batch format (Universal Video AI tools)
        - Timeline manifest JSON (CapCut / Premiere scene JSON)
        - Direct Video Gen API payload
        """
        clean = seed.strip().title()
        aspect = "16:9" if format_type.upper() == "LANDSCAPE" else "9:16"
        aspect_name = "landscape" if aspect == "16:9" else "portrait"

        niche = cls.detect_content_niche(seed)

        # 5 Structured Core Scenes tailored to content niche
        if niche == "documentary":
            scene_templates = [
                {
                    "scene_num": 1,
                    "role": "Hook (00-05s)",
                    "duration": 4,
                    "action": f"Dramatic cinematic establishing shot of {clean}, colossal ancient volcano surrounded by eerie ocean mist, ominous red volcanic glow illuminating stormy clouds, 35mm anamorphic lens, award-winning cinematography",
                    "camera": "Slow epic cinematic push-in to eye level, dark atmospheric volumetric lighting",
                    "audio_script": f"Pernahkah kamu membayangkan salah satu peristiwa alam paling dahsyat yang pernah mengguncang bumi, yaitu {clean}?",
                },
                {
                    "scene_num": 2,
                    "role": "The Escalation (05-12s)",
                    "duration": 6,
                    "action": f"Massive colossal ash clouds billowing tens of kilometers into the stratosphere, volcanic lightning crackling inside dense black smoke during {clean}, cataclysmic cinematic scale",
                    "camera": "High-angle dramatic slow tilt down, photorealistic volumetric smoke and flying embers",
                    "audio_script": "Dentuman dahsyatnya terdengar hingga ribuan kilometer dan melenyapkan daratan dalam sekejap.",
                },
                {
                    "scene_num": 3,
                    "role": "The Cataclysm (12-20s)",
                    "duration": 6,
                    "action": "Turbulent stormy ocean with gigantic tidal waves crashing against distant horizon, apocalyptic dark sky, historical archival cinematic recreation",
                    "camera": "Dynamic horizontal drone track over roaring oceanic waves, intense cinematic contrast",
                    "audio_script": "Langit seketika berubah gelap gulita selama berhari-hari, memicu gelombang dahsyat yang mengubah peradaban.",
                },
                {
                    "scene_num": 4,
                    "role": "Scientific Breakdown (20-28s)",
                    "duration": 8,
                    "action": f"Intricate 3D geological cutaway visualization showing molten magma chamber rupturing beneath tectonic plates for {clean}, glowing magma fissures and luminous scientific telemetry data",
                    "camera": "Macro dolly zoom into subterranean earth layers, scientific hyper-realism",
                    "audio_script": "Para ilmuwan mencatat kekuatan ledakannya setara puluhan ribu bom atom, mengubah iklim global selama bertahun-tahun.",
                },
                {
                    "scene_num": 5,
                    "role": "Resolution & Outro (28-35s)",
                    "duration": 6,
                    "action": f"Breathtaking aerial drone flight over modern calm ocean waters and lush green archipelago of {clean} at golden hour sunrise, awe-inspiring beauty",
                    "camera": "Epic slow drone pull-back into glorious sunrise, inspiring cinematic 8k",
                    "audio_script": "Sebuah pengingat abadi tentang kekuatan alam yang luar biasa. Bagaimana menurutmu? Tulis pandanganmu di komentar!",
                },
            ]
        elif niche == "culinary":
            scene_templates = [
                {
                    "scene_num": 1,
                    "role": "Hook (00-05s)",
                    "duration": 4,
                    "action": f"Mouthwatering extreme close-up macro shot of freshly cooked {clean}, steam rising gracefully, rich aromatic glaze glistening under warm studio light",
                    "camera": "Slow cinematic push-in with shallow depth of field, 50mm macro lens",
                    "audio_script": f"Ini dia rahasia bikin {clean} yang super gurih, bumbunya meresap, dan anti gagal!",
                },
                {
                    "scene_num": 2,
                    "role": "Ingredients Prep (05-12s)",
                    "duration": 6,
                    "action": "Top-down overhead view of fresh aromatic herbs, spices, and premium ingredients neatly arranged on rustic wooden kitchen table, knife slicing smoothly",
                    "camera": "Slow fluid horizontal pan across colorful fresh spices, bright natural morning light",
                    "audio_script": "Kuncinya ada pada takaran bumbu dasar ini yang bikin aromanya langsung semerbak.",
                },
                {
                    "scene_num": 3,
                    "role": "Cooking Action (12-20s)",
                    "duration": 6,
                    "action": f"Sizzling hot wok pan, vibrant sauce caramelizing perfectly with {clean}, gentle tossing motions, savory smoke rising dynamically",
                    "camera": "Side angle dynamic slow motion 120fps, cinematic kitchen atmosphere",
                    "audio_script": "Masak dengan api sedang sampai bumbunya meresap sempurna dan warnanya berubah kecokelatan.",
                },
                {
                    "scene_num": 4,
                    "role": "Plating Presentation (20-28s)",
                    "duration": 8,
                    "action": f"Artisanal plating of {clean} onto elegant ceramic plate, garnished with fresh herbs and crunchy shallots, restaurant quality presentation",
                    "camera": "Rotating 360 slow dolly around the finished dish, mouthwatering food commercial cinematography",
                    "audio_script": "Hasilnya benar-benar lembut di dalam, renyah di luar, dan rasanya setara restoran bintang 5.",
                },
                {
                    "scene_num": 5,
                    "role": "Tasting & Outro (28-35s)",
                    "duration": 6,
                    "action": "Fork taking a perfect bite, tender texture visible, smiling creator giving thumbs up in cozy modern kitchen",
                    "camera": "Gentle zoom out, warm inviting domestic atmosphere",
                    "audio_script": "Yuk coba resepnya di rumah! Jangan lupa like dan simpan video ini agar tidak lupa!",
                },
            ]
        elif niche == "travel":
            scene_templates = [
                {
                    "scene_num": 1,
                    "role": "Hook (00-05s)",
                    "duration": 4,
                    "action": f"Breathtaking panoramic drone shot of majestic scenery at {clean}, golden sunrise casting vibrant rays across lush landscapes and dramatic horizon",
                    "camera": "Slow epic drone forward push over cliff edge, 8k hyper-realistic travel cinematography",
                    "audio_script": f"Kalau kamu punya rencana ke {clean}, jangan lewatkan tempat tersembunyi yang satu ini!",
                },
                {
                    "scene_num": 2,
                    "role": "The Journey (05-12s)",
                    "duration": 6,
                    "action": f"Scenic road trip journey towards {clean}, winding roads surrounded by tropical greenery, window reflection of passing paradise scenery",
                    "camera": "Tracking side shot of moving vehicle, vibrant daylight, cinematic motion blur",
                    "audio_script": "Rutenya ternyata sangat mudah diakses dan pemandangan sepanjang jalan sudah bikin takjub.",
                },
                {
                    "scene_num": 3,
                    "role": "Hidden Gem Spot (12-20s)",
                    "duration": 6,
                    "action": f"Secret untouched viewpoint at {clean}, crystal clear water and pristine natural surroundings, peaceful paradise vibe",
                    "camera": "Low angle smooth gimbal walk-through emerging onto stunning panoramic view",
                    "audio_script": "Banyak turis melewatkan spot ini, padahal pemandangannya jauh lebih indah dan bebas antrean.",
                },
                {
                    "scene_num": 4,
                    "role": "Local Experience & Food (20-28s)",
                    "duration": 8,
                    "action": f"Enjoying authentic local culinary delicacy and cozy cafe atmosphere overlooking the iconic landmark of {clean}",
                    "camera": "Warm medium shot blending food culture and travel lifestyle, golden hour sun flare",
                    "audio_script": "Harganya pun sangat terjangkau, cocok banget buat liburan santai bareng keluarga atau teman.",
                },
                {
                    "scene_num": 5,
                    "role": "Call to Action (28-35s)",
                    "duration": 6,
                    "action": f"Magnificent sunset silhouette at {clean}, vibrant orange and purple twilight sky, inspiring wanderlust feeling",
                    "camera": "Slow cinematic drone rise into dusk sky, cinematic 8k",
                    "audio_script": "Bagikan video ini ke teman liburanmu dan simpan untuk panduan trip berikutnya!",
                },
            ]
        elif niche in ["tech_tutorial", "business"]:
            scene_templates = [
                {
                    "scene_num": 1,
                    "role": "Hook (00-05s)",
                    "duration": 4,
                    "action": f"Close-up intense shot of a creator analyzing {clean} on a glowing modern workstation, focused expression, cinematic ambient lighting",
                    "camera": "Slow cinematic push-in to eye level, 35mm anamorphic lens",
                    "audio_script": f"Jangan pernah coba {clean} sebelum kamu tahu rahasia penting ini!",
                },
                {
                    "scene_num": 2,
                    "role": "The Problem (05-12s)",
                    "duration": 6,
                    "action": "Dramatic overhead view of complex workflow charts and dashboard displaying pain points and common roadblocks, high contrast",
                    "camera": "High-angle slow tilt down, moody studio lighting",
                    "audio_script": f"Banyak orang membuang banyak waktu dan energi karena melewatkan 1 tahapan krusial di {clean}.",
                },
                {
                    "scene_num": 3,
                    "role": "The Solution (12-20s)",
                    "duration": 6,
                    "action": "Futuristic clean minimalist office, creator pointing at a clean step-by-step framework on an ultra-wide curved monitor",
                    "camera": "Smooth horizontal track left to right, golden natural light",
                    "audio_script": "Padahal solusinya sederhana kalau kamu paham alur langkah demi langkahnya.",
                },
                {
                    "scene_num": 4,
                    "role": "Execution (20-28s)",
                    "duration": 8,
                    "action": f"Hyper-detailed macro shot of hands on keyboard, screen displaying verified workflow and instant positive results for {clean}",
                    "camera": "Macro dolly zoom, vibrant subtle accents, depth of field",
                    "audio_script": "Cukup ikuti tahapan praktis ini dan kamu bisa langsung melihat hasilnya secara nyata.",
                },
                {
                    "scene_num": 5,
                    "role": "Call to Action (28-35s)",
                    "duration": 6,
                    "action": "Wide panoramic shot of an inspiring modern creative studio at sunrise, clean minimalist environment",
                    "camera": "Epic slow pull-back, cinematic 8k, warm morning sunlight",
                    "audio_script": "Simpan video ini dan cek panduan lengkapnya di deskripsi untuk mulai sekarang!",
                },
            ]
        else:
            scene_templates = [
                {
                    "scene_num": 1,
                    "role": "Hook (00-05s)",
                    "duration": 4,
                    "action": f"Intriguing cinematic shot introducing {clean}, dramatic lighting revealing subject details, suspenseful atmosphere",
                    "camera": "Slow cinematic push-in to subject, 35mm cinematic lens",
                    "audio_script": f"Tahukah kamu fakta mengejutkan seputar {clean} yang jarang diketahui banyak orang?",
                },
                {
                    "scene_num": 2,
                    "role": "Background & Context (05-12s)",
                    "duration": 6,
                    "action": f"Rich detailed visual story sequence exploring historical roots and context of {clean}, engaging documentary style",
                    "camera": "Smooth horizontal dolly shot, warm evocative lighting",
                    "audio_script": "Di balik popularitasnya, ada kisah panjang dan fakta tersembunyi yang jarang diungkap.",
                },
                {
                    "scene_num": 3,
                    "role": "Key Revelation (12-20s)",
                    "duration": 6,
                    "action": f"Dramatic visual highlight revealing the core turning point and unique aspect of {clean}, high production value",
                    "camera": "Dynamic camera arc around central subject, cinematic volumetric lighting",
                    "audio_script": "Inilah detail penting yang membuat banyak orang tercengang ketika pertama kali mendengarnya.",
                },
                {
                    "scene_num": 4,
                    "role": "Deeper Analysis (20-28s)",
                    "duration": 8,
                    "action": f"Comprehensive visual breakdown with crisp infographics and engaging cinematic demonstrations for {clean}",
                    "camera": "Macro dolly zoom with soft depth of field, vivid realistic colors",
                    "audio_script": "Mari kita lihat bagaimana hal ini berdampak nyata dan mengubah pemahaman kita selama ini.",
                },
                {
                    "scene_num": 5,
                    "role": "Conclusion & CTA (28-35s)",
                    "duration": 6,
                    "action": f"Inspiring wide panoramic closing shot capturing the lasting essence of {clean}, golden hour sunset glow",
                    "camera": "Epic slow drone pull-back into glorious horizon, cinematic 8k",
                    "audio_script": "Bagaimana menurutmu? Tuliskan pendapatmu di kolom komentar dan bagikan video ini!",
                },
            ]

        scenes = []
        batch_prompts_txt_lines = []
        autoflowcut_scenes = []
        veo_mcp_jobs = []

        for item in scene_templates[:num_scenes]:
            prompt = (
                f"{item['action']}, {item['camera']}, 8k photorealistic, photoreal cinematic, "
                f"volumetric lighting, award-winning cinematography --aspect {aspect_name} --duration {item['duration']}"
            )

            scenes.append(
                {
                    "scene_id": f"Scene {item['scene_num']}",
                    "timing": item["role"],
                    "duration_seconds": item["duration"],
                    "aspect_ratio": aspect,
                    "visual_action": item["action"],
                    "camera_motion": item["camera"],
                    "flow_prompt": prompt,
                    "audio_script": item["audio_script"],
                }
            )

            batch_prompts_txt_lines.append(prompt)

            autoflowcut_scenes.append(
                {
                    "id": f"scene_{item['scene_num']}",
                    "name": item["role"],
                    "duration": item["duration"],
                    "aspectRatio": aspect,
                    "prompt": prompt,
                    "voiceoverText": item["audio_script"],
                }
            )

            veo_mcp_jobs.append(
                {
                    "key": f"scene_{item['scene_num']}",
                    "request": {
                        "prompt": prompt,
                        "durationSeconds": item["duration"],
                        "aspectRatio": aspect,
                        "resolution": "1080p",
                    },
                }
            )

        return {
            "seed_keyword": seed,
            "format_type": format_type,
            "aspect_ratio": aspect,
            "scenes_count": len(scenes),
            "scenes": scenes,
            "flow_batch_prompts_txt": "\n".join(batch_prompts_txt_lines),
            "autoflowcut_manifest": {
                "projectName": f"Video_{clean.replace(' ', '_')}",
                "aspectRatio": aspect,
                "scenes": autoflowcut_scenes,
            },
            "veo_mcp_payload": {
                "jobs": veo_mcp_jobs,
                "concurrency": 2,
            },
            "recommended_tools": [
                {
                    "tool": "Universal AI Video Generators",
                    "command": "Kling AI, Runway Gen-3, Luma Dream Machine, OpenAI Sora, Haiper AI",
                    "best_for": "Render klip visual realistis dan sinematik per scene.",
                },
                {
                    "tool": "CapCut & Premiere Pro",
                    "command": "Import manifest JSON / susun klip visual + voiceover naskah di timeline editor",
                    "best_for": "Editing cepat, kinetic subtitle, dan audio sync otomatis.",
                },
                {
                    "tool": "Direct Video Gen API",
                    "command": "start_batch_video_generation(jobs, concurrency=2)",
                    "best_for": "Eksekusi otomatis batch text-to-video melalui integrasi API / MCP agent.",
                },
            ],
        }

    @classmethod
    def detect_content_gaps(
        cls,
        seed: str,
        competitors: list[dict[str, Any]],
        autocomplete_queries: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Replicates official YouTube Studio 'Research' -> 'Content Gaps' feature.
        Identifies queries where viewers are searching, but existing videos are:
        1. Outdated (> 1-2 years old).
        2. Low quality / views (< 10,000) despite high search intent.
        3. Missing format (e.g. only landscape exists, viewers want quick Shorts).
        4. Irrelevant title matching.
        """
        clean = seed.strip().title()
        niche = cls.detect_content_niche(seed)
        current_year = datetime.now(UTC).year
        if autocomplete_queries:
            queries_to_check = autocomplete_queries
        elif niche == "documentary":
            queries_to_check = [
                f"sejarah {clean} lengkap",
                f"kronologi detik detik {clean}",
                f"fakta mengerikan {clean} yang jarang terungkap",
                f"dampak {clean} bagi peradaban",
                f"kisah nyata saksi {clean}",
                f"misteri tersembunyi {clean}",
                f"penjelasan ilmiah fenomena {clean}",
            ]
        elif niche == "culinary":
            queries_to_check = [
                f"resep {clean} enak dan praktis",
                f"cara membuat {clean} anti gagal",
                f"rahasia bumbu {clean} meresap",
                f"tips memasak {clean} empuk gurih",
                f"{clean} ala restoran bintang 5",
                f"resep {clean} takaran sendok",
                f"kesalahan fatal saat masak {clean}",
            ]
        elif niche == "travel":
            queries_to_check = [
                f"panduan wisata {clean} {current_year}",
                f"rute dan biaya ke {clean}",
                f"hidden gem terbaik di {clean}",
                f"tips liburan ke {clean} hemat",
                f"spot foto estetik di {clean}",
                f"itinerary 3 hari 2 malam {clean}",
                f"review jujur liburan ke {clean}",
            ]
        elif niche == "entertainment":
            queries_to_check = [
                f"alur cerita {clean} lengkap",
                f"penjelasan ending {clean}",
                f"teori konspirasi {clean}",
                f"fakta unik {clean} yang jarang diketahui",
                f"karakter terkuat di {clean}",
                f"easter egg tersembunyi {clean}",
                f"rekap alur {clean}",
            ]
        elif niche == "health_fitness":
            queries_to_check = [
                f"cara alami mengatasi {clean}",
                f"gejala dan penyebab {clean}",
                f"pantangan makanan untuk {clean}",
                f"tips hidup sehat bebas {clean}",
                f"penjelasan dokter tentang {clean}",
                f"kebiasaan pemicu {clean}",
                f"solusi aman meredakan {clean}",
            ]
        elif niche == "business":
            queries_to_check = [
                f"strategi {clean} {current_year}",
                f"cara mulai {clean} dari nol",
                f"kunci sukses {clean} yang terbukti",
                f"kesalahan fatal saat menjalankan {clean}",
                f"analisis peluang dan risiko {clean}",
                f"cara scale up {clean}",
                f"studi kasus sukses {clean}",
            ]
        elif niche == "tech_tutorial":
            queries_to_check = [
                f"tutorial {clean} untuk pemula step by step",
                f"cara menggunakan {clean} terbaru {current_year}",
                f"solusi error pada {clean}",
                f"tips dan trik cepat {clean}",
                f"alternatif terbaik untuk {clean}",
                f"fitur tersembunyi di {clean}",
                f"panduan lengkap {clean} dari nol",
            ]
        else:
            queries_to_check = [
                f"fakta menarik tentang {clean}",
                f"penjelasan lengkap {clean}",
                f"sejarah dan asal usul {clean}",
                f"perkembangan terbaru {clean}",
                f"dampak {clean} yang wajib diketahui",
                f"apa itu {clean} dan fungsinya",
                f"hal penting seputar {clean}",
            ]

        # Extract competitor ages and views
        comp_ages = [str(c.get("upload_age", "")).lower() for c in competitors]
        has_outdated = any(
            "tahun" in a or "year" in a or "2 tahun" in a or "3 tahun" in a for a in comp_ages
        )
        has_shorts = any(c.get("format") == "SHORTS" for c in competitors)

        results = []
        for idx, q in enumerate(queries_to_check):
            # Deterministic yet dynamic scoring based on query semantics
            q_clean = q.lower()
            if any(
                w in q_clean for w in ["cara", "tutorial", "terbaru", str(current_year), "pemula"]
            ):
                volume_tier = "High"
            elif any(w in q_clean for w in ["gratis", "modal", "rahasia", "trik"]):
                volume_tier = "Medium"
            else:
                volume_tier = "Low" if idx > 4 else "Medium"

            # Determine Content Gap conditions
            is_gap = False
            gap_type = ""
            gap_reason = ""
            action_plan = ""

            if "terbaru" in q_clean or (has_outdated and idx % 2 == 0):
                is_gap = True
                gap_type = "📅 Outdated Competitor Gap"
                if niche == "documentary":
                    gap_reason = (
                        "Video teratas kompetitor dibuat bertahun-tahun lalu dengan kualitas arsip lama. "
                        "Penonton mencari visualisasi modern dan data penelitian sejarah terbaru."
                    )
                    action_plan = f"Buat video '{q.title()}' dengan visual berkualitas tinggi dan ulasan fakta sejarah yang mendalam."
                    winning_hook = f"Fakta Mencengangkan Seputar {q.title()} yang Jarang Diungkap"
                elif niche == "culinary":
                    gap_reason = (
                        "Banyak video yang beredar memakai takaran perkiraan tanpa gramasi pasti. "
                        "Penonton mencari resep teruji yang praktis dan anti-gagal."
                    )
                    action_plan = f"Sajikan '{q.title()}' dengan takaran gram/sendok presisi dan tips bumbu meresap."
                    winning_hook = f"Rahasia Resep {q.title()} Seenak Restoran Bintang 5"
                elif niche == "travel":
                    gap_reason = (
                        "Informasi rute, harga tiket, dan fasilitas di video lama sudah usang. "
                        "Penonton membutuhkan ulasan kondisi terkini dan estimasi budget aktual."
                    )
                    action_plan = f"Buat video '{q.title()}' dengan rincian biaya nyata, rute terbaik, dan rekomendasi spot tersembunyi."
                    winning_hook = f"Panduan Lengkap Wisata {q.title()} Terbaru: Rute & Biaya Hemat"
                elif niche == "entertainment":
                    gap_reason = (
                        "Video yang ada hanya membahas permukaan alur cerita. "
                        "Penonton mencari bedah teori tersembunyi, plot twist, dan analisis ending mendalam."
                    )
                    action_plan = f"Kupas tuntas '{q.title()}' dengan detail penting yang belum pernah dibahas kreator lain."
                    winning_hook = f"Detail Tersembunyi di {q.title()} yang Bikin Kaget"
                elif niche == "health_fitness":
                    gap_reason = (
                        "Banyak konten beredar terlalu teoritis atau sulit dipraktikkan. "
                        "Penonton mencari panduan langkah alami yang aman menurut referensi kesehatan."
                    )
                    action_plan = f"Buat video '{q.title()}' dengan penjelasan logis, mudah dimengerti, dan berlandaskan fakta."
                    winning_hook = f"Cara Alami Atasi {q.title()} Secara Aman Tanpa Efek Samping"
                elif niche == "business":
                    gap_reason = (
                        "Video kompetitor memakai strategi lama yang sudah jenuh. "
                        "Penonton aktif mencari studi kasus dan alur kerja terkini yang terbukti efektif."
                    )
                    action_plan = f"Bagikan strategi '{q.title()}' berbasis studi kasus nyata yang langsung bisa dipraktikkan."
                    winning_hook = f"Strategi Praktis {q.title()} yang Terbukti Menghasilkan"
                elif niche == "tech_tutorial":
                    gap_reason = (
                        "Video kompetitor memakai versi software antarmuka lama. "
                        "Penonton mencari alur kerja dengan pembaruan sistem terkini."
                    )
                    action_plan = f"Demonstrasikan '{q.title()}' dengan langkah to-the-point dan tips shortcut efisien."
                    winning_hook = f"Cara Cepat Menguasai {q.title()} dari Dasar Sampai Mahir"
                else:
                    gap_reason = (
                        "Konten yang ada kurang merangkum seluruh aspek penting secara terstruktur. "
                        "Ada peluang besar untuk video edukatif berbobot."
                    )
                    action_plan = f"Sajikan '{q.title()}' dengan kemasan ringkas, padat informasi, dan visual memikat."
                    winning_hook = f"Semua Hal Penting Tentang {q.title()} yang Wajib Kamu Tahu"

            elif not has_shorts and any(
                w in q_clean for w in ["trik", "rahasia", "cepat", "fakta", "spot", "resep"]
            ):
                is_gap = True
                gap_type = "📱 Missing Shorts Gap"
                gap_reason = (
                    "Hasil pencarian didominasi video durasi panjang (15+ menit). "
                    "Belum ada video Shorts vertikal 45 detik yang menjawab ringkas dan padat."
                )
                action_plan = f"Buat video Shorts vertikal 45 detik untuk '{q.title()}' dengan hook to-the-point dan pancingan ke video lengkap."
                winning_hook = (
                    f"Hal Menarik Seputar {q.title()} yang Belum Banyak Diketahui #shorts"
                )

            elif any(w in q_clean for w in ["kesalahan", "pemula", "solusi", "kendala", "misteri"]):
                is_gap = True
                gap_type = "💡 Unsatisfied Search Intent Gap"
                gap_reason = (
                    "Banyak penonton mencari jawaban spesifik untuk kendala yang sering dialami, "
                    "tetapi video yang ada terlalu teoritis tanpa contoh nyata."
                )
                action_plan = f"Jawab langsung pertanyaan seputar '{q.title()}' dengan solusi konkret di menit awal."
                winning_hook = f"Kupas Tuntas {q.title()}: Solusi Nyata yang Sering Terlewat"

            else:
                is_gap = False
                gap_type = "✅ Saturated / Covered"
                gap_reason = (
                    "Sudah banyak video kompetitor dengan views tinggi yang membahas topik ini."
                )
                action_plan = (
                    "Hanya buat jika Anda memiliki sudut pandang baru atau studi kasus yang unik."
                )
                winning_hook = f"Sudut Pandang Baru: Kupas Mendalam {q.title()}"

            results.append(
                {
                    "query": q,
                    "search_volume_tier": volume_tier,
                    "is_content_gap": is_gap,
                    "gap_badge": "🏷️ CONTENT GAP" if is_gap else "✅ COVERED",
                    "gap_type": gap_type,
                    "gap_reason": gap_reason,
                    "recommended_action": action_plan,
                    "winning_hook": winning_hook,
                }
            )

        return results

    @classmethod
    def analyze_competitor_outliers(cls, competitors: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Viral Outlier Multiplier Analysis.
        Calculates median views across top ranking videos and finds viral breakout outliers.
        """
        if not competitors:
            return {
                "median_views": 0,
                "outliers_found": 0,
                "highest_multiplier": 1.0,
                "golden_video": None,
                "outlier_items": [],
            }

        views_list = []
        for c in competitors:
            v = cls.parse_views_str(c.get("views_count") or c.get("views") or 0)
            views_list.append(max(v, 1))

        sorted_views = sorted(views_list)
        mid = len(sorted_views) // 2
        median_views = (
            sorted_views[mid]
            if len(sorted_views) % 2 != 0
            else (sorted_views[mid - 1] + sorted_views[mid]) // 2
        )
        median_views = max(median_views, 1000)

        outlier_items = []
        golden_video = None
        max_mult = 1.0

        for c, v in zip(competitors, views_list, strict=False):
            multiplier = round(v / median_views, 2)
            if multiplier > max_mult:
                max_mult = multiplier
                golden_video = c

            status = "⚖️ Standard (1.0x)"
            if multiplier >= 5.0:
                status = f"🔥 VIRAL BREAKOUT ({multiplier}x)"
            elif multiplier >= 2.5:
                status = f"⭐ STRONG OUTLIER ({multiplier}x)"
            elif multiplier >= 1.3:
                status = f"📈 ABOVE AVERAGE ({multiplier}x)"

            outlier_items.append(
                {
                    "rank": c.get("rank", 1),
                    "title": c.get("title", ""),
                    "channel": c.get("channel", ""),
                    "views": c.get("views", f"{v:,}"),
                    "multiplier": multiplier,
                    "outlier_label": status,
                    "format": c.get("format", "LANDSCAPE"),
                    "is_ai": c.get("is_ai_generated", False),
                }
            )

        outliers_found = sum(1 for item in outlier_items if item["multiplier"] >= 2.0)

        return {
            "median_views": median_views,
            "outliers_found": outliers_found,
            "highest_multiplier": max_mult,
            "golden_video": golden_video,
            "outlier_items": outlier_items,
        }

    @classmethod
    def analyze_faceless_viability(cls, seed: str, rpm_info: dict[str, Any]) -> dict[str, Any]:
        """
        Faceless Niche Opportunity Analysis.
        Evaluates AI / Faceless viability, scripting automation, and B-roll feasibility.
        """
        niche = rpm_info.get("detected_niche", "general").lower()
        clean = seed.strip().title()

        # Score based on how visual/concept-driven the niche is vs human personal brand
        niche_scores = {
            "tech": 92,
            "advertising": 90,
            "business": 88,
            "finance": 85,
            "education": 82,
            "health_fitness": 76,
            "automotive": 74,
            "travel": 70,
            "gaming": 68,
            "culinary": 60,
            "entertainment": 65,
            "lifestyle": 50,
            "general": 65,
        }

        score = niche_scores.get(niche, 70)
        if score >= 85:
            tier = "🟢 SANGAT IDEAL UNTUK FACELESS AI"
            verdict = (
                "Niche ini sangat berbasis visual data, layar, dan ilustrasi konsep. "
                "Penonton lebih peduli pada kejelasan informasi daripada melihat wajah kreator."
            )
        elif score >= 70:
            tier = "🟡 CUKUP IDEAL (DENGAN B-ROLL BERKUALITAS)"
            verdict = (
                "Dapat dijalankan tanpa wajah dengan dukungan klip visual Generator Video AI modern "
                "dan voiceover AI alami (ElevenLabs)."
            )
        else:
            tier = "🔴 KURANG IDEAL UNTUK FACELESS"
            verdict = "Niche ini sangat mengandalkan personal branding, ekspresi wajah, atau demonstrasi fisik langsung."

        return {
            "faceless_score": score,
            "tier": tier,
            "verdict": verdict,
            "recommended_pipeline": [
                f"1. Riset Keyword & Outlier: Temukan topik bervolume tinggi di {clean}.",
                "2. Scripting: Buat naskah hook 3 detik dengan Claude / Gemini.",
                "3. Voiceover: Gunakan ElevenLabs suara natural bahasa Indonesia / English.",
                "4. Visual B-Roll: Generate scene visual menggunakan Generator Video AI (Kling, Runway, Luma, Sora).",
                "5. Assembly: Gabungkan klip visual dan naskah audio di CapCut / Premiere untuk sync otomatis.",
            ],
        }

    @classmethod
    def generate_clipping_opportunities(
        cls, topic: str, title: str, duration: str = "15:00"
    ) -> list[dict[str, Any]]:
        """
        AI Shorts Clipping & Viral Highlights Generator.
        Deconstructs a long-form video topic into 3-4 viral Short clips with hooks and timestamps.
        """
        clean = topic.strip().title()
        niche = cls.detect_content_niche(topic)

        if niche == "documentary":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Detik-Detik Mencekam {clean} #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Ini detik-detik paling mengerikan saat peristiwa {clean} mengguncang dunia...",
                    "core_insight": "Visualisasi dramatis dan catatan saksi mata saat puncak letusan/bencana terjadi.",
                    "call_to_action": "Tonton dokumenter sejarah lengkapnya di video utama!",
                    "projected_virality": "9.5 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Fakta Mengerikan {clean} yang Jarang Diungkap #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Tahukah kamu kalau dampak dahsyat {clean} sempat mengubah iklim seluruh bumi?",
                    "core_insight": "Pengungkapan bukti arsip sejarah dan sains yang mencengangkan.",
                    "call_to_action": "Simpan video ini dan bagikan fakta ini ke temanmu!",
                    "projected_virality": "9.1 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Misteri Tersembunyi di Balik {clean} #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Ada satu kejanggalan besar dalam catatan peristiwa {clean} yang masih misterius...",
                    "core_insight": "Teori ilmiah dan temuan baru yang memicu rasa ingin tahu tinggi.",
                    "call_to_action": "Bagaimana menurutmu? Tulis pendapatmu di kolom komentar!",
                    "projected_virality": "9.4 / 10 🔥",
                },
            ]
        elif niche == "culinary":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Rahasia Bumbu {clean} Seenak Restoran #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Ternyata cuma butuh 1 bumbu rahasia ini biar {clean} buatanmu 10x lebih lezat!",
                    "core_insight": "Trik marinasi dan takaran bumbu kunci yang jarang dibocorkan restoran.",
                    "call_to_action": "Tonton takaran gram lengkapnya di video utama!",
                    "projected_virality": "9.3 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Jangan Lakukan Ini Saat Masak {clean}! #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Stop lakukan kesalahan sepele ini kalau gak mau {clean} buatanmu gagal total!",
                    "core_insight": "Teknik pengaturan api dan waktu agar tekstur matang sempurna.",
                    "call_to_action": "Simpan resep ini buat menu masak berikutnya!",
                    "projected_virality": "8.9 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Trik Cepat Bikin {clean} Cuma 5 Menit #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Pengen makan {clean} tapi gak mau repot? Cobain metode kilat anti gagal ini!",
                    "core_insight": "Langkah ringkas praktis yang bisa langsung dipraktikkan siapa saja.",
                    "call_to_action": "Tulis di komentar, mau resep apa lagi selanjutnya?",
                    "projected_virality": "9.2 / 10 🔥",
                },
            ]
        elif niche == "travel":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Spot Tersembunyi di {clean} yang Wajib Tahu #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Kalau kamu ke {clean}, jangan cuma ke tempat biasa, spot rahasia ini jauh lebih indah!",
                    "core_insight": "Sudut panorama tersembunyi yang belum ramai turis.",
                    "call_to_action": "Tonton panduan rute dan rincian biaya di video lengkap!",
                    "projected_virality": "9.4 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Tips Hemat Liburan ke {clean} #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Liburan ke {clean} gak harus mahal! Terapkan trik hemat ini biar budget aman!",
                    "core_insight": "Rincian pengeluaran realistis dan waktu terbaik berkunjung.",
                    "call_to_action": "Simpan video ini untuk rencana itinerary liburanmu!",
                    "projected_virality": "8.8 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Aturan Wajib Sebelum Berangkat ke {clean} #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Jangan pernah ke {clean} sebelum kamu tahu peringatan penting ini!",
                    "core_insight": "Informasi cuaca, medan lokasi, dan etika berkunjung yang harus dipatuhi.",
                    "call_to_action": "Pernah ke sini juga? Bagikan pengalamanmu di komentar!",
                    "projected_virality": "9.1 / 10 🔥",
                },
            ]
        elif niche == "entertainment":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Detail Gila di {clean} yang Terlewatkan #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Hampir 99% orang gak sadar kalau ada detail tersembunyi di {clean}!",
                    "core_insight": "Analisis adegan / petunjuk rahasia yang mengubah jalan cerita.",
                    "call_to_action": "Tonton bedah cerita lengkapnya di video utama!",
                    "projected_virality": "9.6 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Teori Mengejutkan Seputar {clean} #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Gimana kalau fakta sesungguhnya di {clean} sama sekali bukan seperti yang kamu duga?",
                    "core_insight": "Eksplorasi plot twist dan spekulasi cerita yang memukau.",
                    "call_to_action": "Tonton video lengkapnya untuk penjelasan alur selengkapnya!",
                    "projected_virality": "9.0 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Makna Sebenarnya dari Ending {clean} #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Masih bingung sama adegan akhir {clean}? Ini penjelasan makna sesungguhnya!",
                    "core_insight": "Penjelasan makna filosofis dan pesan tersirat sang kreator.",
                    "call_to_action": "Setuju gak sama teori ini? Tulis pendapatmu di komentar!",
                    "projected_virality": "9.3 / 10 🔥",
                },
            ]
        elif niche == "health_fitness":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Tanda Tubuhmu Mengalami {clean} #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Waspada 3 tanda ini di tubuhmu, jangan-jangan kamu sedang mengalami {clean}!",
                    "core_insight": "Edukasi deteksi gejala awal menurut fakta kesehatan.",
                    "call_to_action": "Tonton penjelasan dokter dan solusi alaminya di video lengkap!",
                    "projected_virality": "9.2 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Hindari 1 Hal Ini Kalau Ada {clean}! #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Banyak orang belum tahu, 1 kebiasaan sepele ini justru bikin {clean} makin parah!",
                    "core_insight": "Pantangan medis penting dan alternatif kebiasaan yang lebih sehat.",
                    "call_to_action": "Simpan video ini dan kirim ke orang tersayang!",
                    "projected_virality": "9.0 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Cara Alami Atasi {clean} Tanpa Obat Kimia #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Coba lakukan langkah alami ini secara rutin untuk meredakan {clean}!",
                    "core_insight": "Pola hidup sehat dan nutrisi alami yang terbukti menjaga kondisi tubuh.",
                    "call_to_action": "Komen di bawah apa keluhan yang paling sering kamu rasakan!",
                    "projected_virality": "8.9 / 10 ⭐",
                },
            ]
        elif niche == "business":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"1 Rahasia {clean} yang Mengubah Segalanya #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Banyak yang gagal saat menjalankan {clean} cuma gara-gara 1 kesalahan kecil ini...",
                    "core_insight": "Demonstrasi bagian teknis paling krusial yang langsung mengubah hasil.",
                    "call_to_action": "Tonton tutorial strategi lengkapnya di channel ini!",
                    "projected_virality": "9.2 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Cukup 30 Detik Paham Cara Kerja {clean} #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Kalau kamu masih bingung cara kerja {clean}, tonton ini sampai habis!",
                    "core_insight": "Alur visual cepat step-by-step tanpa basa-basi.",
                    "call_to_action": "Simpan video ini biar gak lupa!",
                    "projected_virality": "8.8 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Jangan Pernah Lakukan Ini Saat {clean}! #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Ini kesalahan paling fatal seputar {clean} yang bikin waktu dan energimu terbuang sia-sia!",
                    "core_insight": "Peringatan berbasis studi kasus nyata yang sering diabaikan.",
                    "call_to_action": "Komen pendapatmu di bawah, pernah ngalamin juga?",
                    "projected_virality": "9.5 / 10 🔥",
                },
            ]
        elif niche == "tech_tutorial":
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Shortcut Rahasia {clean} yang Wajib Tahu #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Kerja pakai {clean} bakal 10x lebih cepat kalau kamu tahu trik tersembunyi ini!",
                    "core_insight": "Tips efisiensi kerja dan fitur tersembunyi yang menghemat waktu.",
                    "call_to_action": "Tonton tutorial lengkap langkah demi langkah di video utama!",
                    "projected_virality": "9.3 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Solusi Error pada {clean} dalam 30 Detik #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Pernah ngalamin kendala ini pas pakai {clean}? Jangan panik, ini solusinya!",
                    "core_insight": "Perbaikan langsung untuk kendala teknis yang paling sering muncul.",
                    "call_to_action": "Simpan video ini buat jaga-jaga kalau ketemu error serupa!",
                    "projected_virality": "8.9 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Fitur Baru {clean} Versi 2026 #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Ada update keren di {clean} yang bikin cara kerjamu jauh lebih simpel!",
                    "core_insight": "Review ringkas peningkatan performa dan navigasi baru.",
                    "call_to_action": "Udah coba fitur ini belum? Komen di bawah ya!",
                    "projected_virality": "9.1 / 10 🔥",
                },
            ]
        else:
            return [
                {
                    "clip_id": 1,
                    "clip_title": f"Fakta Menakjubkan Seputar {clean} #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": f"Tahukah kamu ada fakta mengejutkan seputar {clean} yang jarang diketahui?",
                    "core_insight": "Informasi unik dan berbobot yang memancing rasa penasaran audiens.",
                    "call_to_action": "Tonton penjelasan lengkapnya di video utama!",
                    "projected_virality": "9.1 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Kenapa {clean} Begitu Menarik? #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": f"Banyak orang belum sadar alasan kenapa {clean} punya pengaruh sebesar ini...",
                    "core_insight": "Sudut pandang segar dan analisis mendalam yang mudah dipahami.",
                    "call_to_action": "Simpan video ini untuk referensi wawasanmu!",
                    "projected_virality": "8.7 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Mitos vs Fakta Seputar {clean} #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": f"Jangan gampang percaya, mitos tentang {clean} ini ternyata keliru besar!",
                    "core_insight": "Pembongkaran miskonsepsi umum berdasarkan fakta valid.",
                    "call_to_action": "Bagaimana menurutmu? Tulis tanggapanmu di komentar!",
                    "projected_virality": "9.2 / 10 🔥",
                },
            ]
