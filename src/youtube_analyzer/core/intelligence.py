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
        Intelligently detects content genre/niche for context-aware copywriting,
        titles, hooks, timestamps, and storyboards.
        Returns one of: 'documentary', 'culinary', 'travel', 'entertainment',
        'health_fitness', 'business', 'tech_tutorial', 'general'.
        """
        lowered = seed.strip().lower()

        # 1. Documentary / History / Disaster / Nature / Science / Mystery
        if any(
            k in lowered
            for k in [
                "krakatau", "letusan", "gunung", "meletus", "gempa", "tsunami",
                "bencana", "sejarah", "perang", "dinosaurus", "misteri", "alien",
                "segitiga bermuda", "luar angkasa", "bumi", "planet", "arkeologi",
                "fosil", "konspirasi", "mitos", "legenda", "antartika", "tragedi",
                "kronologi", "sains", "biologi", "fisika", "tata surya", "hewan buas",
                "hiu", "singa", "ekspedisi", "piramida", "atlantis", "hantu", "horor",
                "meteor", "asteroid", "black hole", "lubang hitam", "kerajaan",
                "majapahit", "pahlawan", "kisah nyata", "dokumenter", "arkeologis",
                "alam", "laut dalam", "palung", "hutan", "safari", "antartika"
            ]
        ):
            return "documentary"

        # 2. Culinary / Food / Recipe / Cooking
        if any(
            k in lowered
            for k in [
                "masak", "resep", "kuliner", "makanan", "minuman", "kue", "bumbu",
                "dapur", "ayam", "sambal", "daging", "nasi", "mukbang", "jajanan",
                "bakso", "mie", "koki", "chef", "goreng", "rebus", "panggang",
                "pedas", "soto", "rendang", "cemilan", "roti", "bolu", "jus",
                "kopi", "teh", "cafe", "restoran", "food", "snack"
            ]
        ):
            return "culinary"

        # 3. Travel / Vacation / Places
        if any(
            k in lowered
            for k in [
                "wisata", "liburan", "hotel", "pantai", "villa", "traveling",
                "staycation", "jalur", "rute", "tiket", "bali", "jogja", "jepang",
                "eropa", "destinasi", "hidden gem", "curug", "air terjun", "pulau",
                "bromo", "danau", "candi", "taman", "backpacker", "tour", "trip"
            ]
        ):
            return "travel"

        # 4. Entertainment / Gaming / Pop Culture / Media / Anime
        if any(
            k in lowered
            for k in [
                "film", "movie", "drama", "anime", "manga", "alur cerita",
                "sinopsis", "rekap", "ending", "trailer", "lagu", "musik",
                "lirik", "chord", "konser", "vlog", "lucu", "komedi", "parodi",
                "sketsa", "artis", "gosip", "game", "gaming", "gameplay",
                "mobile legends", "ff", "free fire", "roblox", "gta", "genshin",
                "valorant", "minecraft", "ps5", "walkthrough", "streamer"
            ]
        ):
            return "entertainment"

        # 5. Health / Fitness / Beauty / Wellness
        if any(
            k in lowered
            for k in [
                "diet", "gym", "fitness", "workout", "otot", "kalori", "kurus",
                "sehat", "kesehatan", "obat", "penyakit", "gejala", "dokter",
                "skincare", "glowing", "jerawat", "rambut", "herbal", "medis",
                "terapi", "kolesterol", "diabetes", "asam urat", "lemak"
            ]
        ):
            return "health_fitness"

        # 6. Business / Finance / Ads / Marketing / Making Money
        if any(
            k in lowered
            for k in [
                "ads", "iklan", "google ads", "fb ads", "tiktok ads", "jualan",
                "bisnis", "modal", "omset", "cuan", "boncos", "reseller",
                "dropship", "affiliate", "saham", "crypto", "trading",
                "investasi", "keuangan", "closing", "freelance", "umkm",
                "franchise", "usaha", "toko online", "ekspor", "impor",
                "marketing", "sales", "penjualan", "gaji", "passive income"
            ]
        ):
            return "business"

        # 7. Tech / Coding / Software / Video Editing / Tutorials
        if any(
            k in lowered
            for k in [
                "tutorial", "cara membuat", "panduan", "coding", "python",
                "excel", "canva", "capcut", "edit video", "photoshop",
                "developer", "komputer", "laptop", "hp", "review hp",
                "setting", "instal", "download", "prompt ai", "chatgpt",
                "software", "programming", "javascript", "gadget"
            ]
        ):
            return "tech_tutorial"

        # Fallback based on question or tutorial keywords
        if any(k in lowered for k in ["cara", "tips", "trik", "panduan", "bagaimana"]):
            return "tech_tutorial"

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

    @staticmethod
    def generate_high_ctr_titles(seed: str, intent_type: IntentEnum) -> list[str]:
        """
        Generate high-CTR title formulas
        tailored to the target intent.
        """
        clean = seed.strip().title()
        year = datetime.now(UTC).year

        if intent_type == IntentEnum.TUTORIAL:
            return [
                f"Cara {clean} dari Nol untuk Pemula (Step-by-Step {year})",
                f"Tutorial {clean} Paling Lengkap & Mudah Dipahami",
                f"Rahasia Setting {clean} yang Jarang Diketahui Orang",
                f"Hentikan Kesalahan Ini Saat Memulai {clean}!",
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
                f"Apakah {clean} Masih Efektif di {year}? Data Membuktikannya",
                f"Semua yang Wajib Anda Tahu Tentang {clean}",
                f"5 Fakta Mengejutkan Seputar {clean}",
            ]

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

        if niche == "documentary":
            title_formula = "Pola: [Detik-Detik Mencekam / Peristiwa] + [Subjek Topik] + [Dampak Dunia] + [Format Dokumenter]"
            outranking_title = f"Detik-Detik Mencekam {clean} yang Mengguncang Dunia (Dokumenter Lengkap)"
            alternative_titles = [
                f"Misteri & Fakta Mengerikan di Balik {clean} yang Jarang Terungkap",
                f"Kronologi Lengkap Peristiwa {clean}: Apa yang Sebenarnya Terjadi?",
                f"Kisah Nyata {clean}: Dampak Dahsyat yang Mengubah Sejarah Bumi",
            ]
            two_line_hook = (
                f"Pernahkah kamu membayangkan betapa dahsyatnya peristiwa {clean}? "
                f"Di video dokumenter ini kita bedah kronologi lengkap, arsip sejarah, dan fakta mengejutkan yang jarang dibahas!"
            )
            timestamps = [
                "00:00 - Kilas Balik Awal Peristiwa",
                f"02:30 - Latar Belakang & Tanda Awal {clean}",
                "06:45 - Detik-Detik Puncak Terjadinya Peristiwa",
                "11:20 - Dampak Dahsyat yang Mengguncang Dunia",
                "15:50 - Pelajaran Sejarah & Kondisi Terkini",
            ]
            hashtags = [f"#{clean_tag}", f"#{clean_tag}Sejarah", "#DokumenterDunia", "#FaktaMenarik"]
            shorts_package = {
                "title": f"Fakta Mengerikan {clean} yang Bikin Merinding! #shorts",
                "three_second_hook": f"Ini alasan kenapa peristiwa {clean} disebut salah satu yang paling mengerikan di bumi!",
                "script_structure": [
                    "00-03s: Hook visual kilas peristiwa mengerikan",
                    "03-30s: Ungkap 1 fakta sejarah paling mengejutkan",
                    "30-45s: Ajakan tonton dokumenter lengkapnya di link video terkait",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "culinary":
            title_formula = "Pola: [Resep Otentik] + [Subjek Masakan] + [Karakter Rasa] + [Anti Gagal untuk Pemula]"
            outranking_title = f"Resep {clean} Gurih & Lembut (Anti Gagal untuk Pemula)"
            alternative_titles = [
                f"Rahasia Bumbu {clean} Rasa Bintang 5 dengan Bahan Rumahan",
                f"Cara Membuat {clean} Praktis & Cepat: Wangi Menggugah Selera",
                f"Eksperimen Resep {clean} Paling Enak: Jangan Lakukan 3 Kesalahan Ini!",
            ]
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
            title_formula = "Pola: [Panduan Eksplorasi] + [Destinasi Wisata] + [Hidden Gem / Spot Terbaik] + [Rute & Budget]"
            outranking_title = f"Panduan Lengkap Wisata {clean} 2026: Rute, Biaya, & Hidden Gems Terindah"
            alternative_titles = [
                f"Eksplorasi {clean} Seharian: Tips Liburan Hemat & Spot Foto Viral",
                f"Jangan Pergi ke {clean} Sebelum Tahu 5 Hal Penting Ini! (Review Jujur)",
                f"Itinerary Liburan ke {clean} Paling Nyaman & Bebas Ribet",
            ]
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
        elif niche == "entertainment":
            title_formula = "Pola: [Bedah Cerita / Misteri] + [Subjek Film/Tokoh] + [Plot Twist / Teori Tersembunyi]"
            outranking_title = f"Bedah Cerita & Misteri {clean}: Teori Tersembunyi yang Bikin Merinding"
            alternative_titles = [
                f"Alur Cerita Lengkap {clean} yang Belum Pernah Dijelaskan Gamblang",
                f"Fakta Menarik & Rahasia di Balik {clean} yang Jarang Diketahui",
                f"Penjelasan Ending & Makna Tersirat dari {clean} (Analisis Mendalam)",
            ]
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
        elif niche == "health_fitness":
            title_formula = "Pola: [Solusi Medis/Alami] + [Masalah Tubuh/Kesehatan] + [Fakta Teruji & Tips Aman]"
            outranking_title = f"Cara Alami Menjaga Tubuh dari {clean} Menurut Fakta Medis"
            alternative_titles = [
                f"5 Fakta Penting Seputar {clean} yang Wajib Kamu Ketahui Sejak Dini",
                f"Panduan Mengatasi {clean} Secara Sehat & Aman (Penjelasan Ahli)",
                f"Kebiasaan Sehari-Hari yang Berdampak pada {clean} dan Solusinya",
            ]
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
        elif niche == "business":
            title_formula = "Pola: [Strategi / Pola Sukses] + [Model Bisnis/Iklan] + [Hasil Nyata] + [Minim Resiko]"
            outranking_title = f"Strategi {clean} Praktis untuk Pemula (Update 2026 Terbukti Efektif)"
            alternative_titles = [
                f"Tutorial {clean} Step-by-Step dari Nol: Langkah Tepat Minim Resiko",
                f"Bongkar Pola Sukses {clean} yang Sering Dirahasiakan Para Praktisi",
                f"Hindari 5 Kesalahan Fatal Ini Saat Memulai {clean}",
            ]
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
                "title": f"1 Rahasia {clean} Biar Gak Boncos! #shorts",
                "three_second_hook": f"Jangan pernah coba {clean} sebelum kamu tahu formula penting ini!",
                "script_structure": [
                    "00-03s: Hook visual jangan lakukan kesalahan ini",
                    "03-30s: Bongkar 1 formula paling berdampak",
                    "30-45s: Tutorial lengkapnya klik link video di bawah",
                ],
                "target_metric": "Viewed vs Swiped Away > 75%",
            }
        elif niche == "tech_tutorial":
            title_formula = "Pola: [Tutorial Step-by-Step] + [Tool / Skill] + [Dari Nol Sampai Mahir] + [Update Terbaru]"
            outranking_title = f"Tutorial {clean} Lengkap untuk Pemula (Panduan Cepat & Mudah Dipahami)"
            alternative_titles = [
                f"Cara Menguasai {clean} dari Nol dalam Waktu Singkat",
                f"Trik & Tips Praktis {clean} yang Bakal Mempermudah Kerjamu",
                f"Solusi Mengatasi Masalah Umum pada {clean} (Step by Step)",
            ]
            two_line_hook = (
                f"Baru mau belajar {clean}? Jangan bingung, video ini merangkum "
                f"tutorial langkah demi langkah dari dasar sampai kamu mahir!"
            )
            timestamps = [
                "00:00 - Pengantar & Konsep Dasar",
                f"02:00 - Persiapan & Interface {clean}",
                "05:30 - Langkah demi Langkah Praktik Langsung",
                "10:15 - Trik Rahasia & Shortcut Berguna",
                "14:00 - Kesimpulan & Langkah Lanjutan",
            ]
            hashtags = [f"#{clean_tag}", f"#Tutorial{clean_tag}", "#BelajarTeknologi", "#TipsTutorial"]
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
        else:
            title_formula = "Pola: [Pertanyaan Memikat / Eksplorasi] + [Subjek Topik] + [Fakta & Penjelasan Berbobot]"
            outranking_title = f"Semua yang Wajib Kamu Ketahui Tentang {clean} (Fakta & Penjelasan Lengkap)"
            alternative_titles = [
                f"Mengapa {clean} Sangat Menarik? Penjelasan Mudah & Berbobot",
                f"Fakta Menakjubkan Seputar {clean} yang Jarang Dibahas Orang",
                f"Panduan Memahami {clean} dari A Sampai Z Secara Rinci",
            ]
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

        full_description = (
            f"{two_line_hook}\n\n"
            f"📌 Rangkuman & panduan lengkap seputar {clean}. Tonton video ini dari awal "
            f"sampai akhir agar tidak ada detail penting yang terlewat!\n\n"
            f"⏱️ TIMESTAMPS / DAFTAR ISI:\n"
            + "\n".join(timestamps)
            + f"\n\n🔗 LINK & INFORMASI:\n"
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
            "outranking_title": outranking_title,
            "title_formula": title_formula,
            "detected_niche": niche,
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
                f"panduan wisata {clean} 2026",
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
                f"strategi {clean} 2026",
                f"cara mulai {clean} untuk pemula",
                f"trik jualan {clean} laris manis",
                f"kesalahan fatal saat {clean}",
                f"analisis modal dan omset {clean}",
                f"cara scale up bisnis {clean}",
                f"review jujur {clean}",
            ]
        elif niche == "tech_tutorial":
            queries_to_check = [
                f"tutorial {clean} untuk pemula step by step",
                f"cara setting {clean} terbaru 2026",
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
            if any(w in q_clean for w in ["cara", "tutorial", "terbaru", "2026", "pemula"]):
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

            if "2026" in q_clean or "terbaru" in q_clean or (has_outdated and idx % 2 == 0):
                is_gap = True
                gap_type = "📅 Outdated Competitor Gap"
                gap_reason = (
                    "Video teratas kompetitor dibuat > 1-2 tahun lalu. "
                    "Penonton aktif mencari panduan dengan UI dan sistem terbaru 2026."
                )
                action_plan = f"Buat video '{q.title()}' dengan demonstrasi fitur terkini 2026."
            elif not has_shorts and any(w in q_clean for w in ["trik", "rahasia", "cepat", "modal"]):
                is_gap = True
                gap_type = "📱 Missing Shorts Gap"
                gap_reason = (
                    "Hasil pencarian didominasi video durasi panjang (15+ menit). "
                    "Belum ada video Shorts vertikal 45 detik yang menjawab ringkas."
                )
                action_plan = "Buat Shorts 45 detik dengan visual to-the-point dan pancing ke bio."
            elif "kesalahan" in q_clean or "pemula" in q_clean:
                is_gap = True
                gap_type = "💡 Unsatisfied Search Intent Gap"
                gap_reason = (
                    "Banyak penonton mencari solusi kendala teknis, "
                    "tetapi video yang ada terlalu teoritis tanpa studi kasus nyata."
                )
                action_plan = (
                    f"Ungkap 3 kesalahan terbesar saat {clean} dan solusinya di 3 menit awal."
                )
            else:
                is_gap = False
                gap_type = "✅ Saturated / Covered"
                gap_reason = "Sudah banyak video kompetitor dengan views tinggi yang membahas topik ini."
                action_plan = "Hanya buat jika memiliki sudut pandang / studi kasus yang sangat kontras."

            results.append(
                {
                    "query": q,
                    "search_volume_tier": volume_tier,
                    "is_content_gap": is_gap,
                    "gap_badge": "🏷️ CONTENT GAP" if is_gap else "✅ COVERED",
                    "gap_type": gap_type,
                    "gap_reason": gap_reason,
                    "recommended_action": action_plan,
                    "winning_hook": f"Trik {q.title()} yang Jarang Diketahui Orang (Update 2026)",
                }
            )

        return results

    @classmethod
    def analyze_competitor_outliers(
        cls, competitors: list[dict[str, Any]]
    ) -> dict[str, Any]:
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
    def analyze_faceless_viability(
        cls, seed: str, rpm_info: dict[str, Any]
    ) -> dict[str, Any]:
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
            verdict = (
                "Niche ini sangat mengandalkan personal branding, ekspresi wajah, atau demonstrasi fisik langsung."
            )

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
                    "clip_title": f"1 Rahasia {clean} Biar Gak Boncos #shorts",
                    "timestamp_window": "01:15 - 02:00 (45 Detik)",
                    "hook_line": "Banyak orang boncos di 2026 gara-gara 1 tombol ini...",
                    "core_insight": "Demonstrasi bagian teknis paling krusial yang langsung mengubah hasil.",
                    "call_to_action": "Tonton tutorial strategi lengkapnya di channel ini!",
                    "projected_virality": "9.2 / 10 🔥",
                },
                {
                    "clip_id": 2,
                    "clip_title": f"Cukup 30 Detik Paham Cara Kerja {clean} #shorts",
                    "timestamp_window": "05:30 - 06:15 (45 Detik)",
                    "hook_line": "Kalau kamu masih bingung cara settingnya, tonton ini sampai habis!",
                    "core_insight": "Alur visual cepat step-by-step tanpa basa-basi.",
                    "call_to_action": "Simpan video ini biar gak lupa!",
                    "projected_virality": "8.8 / 10 ⭐",
                },
                {
                    "clip_id": 3,
                    "clip_title": f"Jangan Pernah Lakukan Ini Saat {clean}! #shorts",
                    "timestamp_window": "10:45 - 11:30 (45 Detik)",
                    "hook_line": "Ini kesalahan paling fatal yang bikin budget-mu habis sia-sia!",
                    "core_insight": "Peringatan berbasis studi kasus nyata yang sering diabaikan pemula.",
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
