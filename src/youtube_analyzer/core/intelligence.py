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

        outranking_title = f"Cara {clean} dari Nol untuk Pemula (Update 2026 - Anti Boncos)"
        alternative_titles = [
            f"Tutorial {clean} Lengkap 2026 | Modal Kecil Hasil Maksimal",
            f"Bongkar Rahasia {clean} yang Jarang Dibahas Orang (Panduan Pemula)",
            f"Hentikan Kesalahan Ini Saat Setting {clean}! (Step by Step)",
        ]

        two_line_hook = (
            f"Bingung cara mulai {clean} tanpa takut boncos? Di video ini kita bedah "
            f"panduan lengkap {clean} dari nol khusus pemula sampai berhasil dapat hasil!"
        )

        timestamps = [
            "00:00 - Kenapa Harus Mulai Sekarang?",
            f"02:15 - Riset & Persiapan {clean}",
            "06:30 - Langkah Setting Step-by-Step",
            "12:45 - Trik Budget Minimal Anti Boncos",
            "17:20 - Evaluasi & Cara Skalasi Hasil",
        ]

        clean_tag = "".join(clean.split())
        hashtags = [f"#{clean_tag}", f"#{clean_tag}Pemula", "#BelajarDigital"]

        full_description = (
            f"{two_line_hook}\n\n"
            f"📌 Di video ini, Anda akan mempelajari cara setting dan strategi terbaik "
            f"untuk {clean} yang sudah terbukti efektif di tahun 2026. Tonton dari awal "
            f"sampai akhir agar tidak ada langkah penting yang terlewat!\n\n"
            f"⏱️ TIMESTAMPS / DAFTAR ISI:\n"
            + "\n".join(timestamps)
            + f"\n\n🔗 LINK & RESOURCE TERKAIT:\n"
            f"- Download Template Gratis: https://example.com\n"
            f"- Konsultasi / Diskusi: https://example.com/komunitas\n\n"
            f"{' '.join(hashtags)}"
        )

        shorts_package = {
            "title": f"Trik Rahasia {clean} Biar Gak Rugi! #shorts",
            "three_second_hook": f"Jangan pernah coba {clean} sebelum kamu tahu 1 tombol rahasia ini!",
            "script_structure": [
                "00-03s: Hook visual ('Jangan lakukan ini!')",
                "03-30s: Bongkar 1 tips paling berdampak",
                "30-45s: Call to action ('Tutorial lengkapnya klik link video di bawah!')",
            ],
            "target_metric": "Viewed vs Swiped Away > 75%",
        }

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

        # 5 Structured Core Scenes for a high-retention video
        scene_templates = [
            {
                "scene_num": 1,
                "role": "Hook (00-05s)",
                "duration": 4,
                "action": f"Close-up intense shot of a modern creator analyzing {clean} on a glowing holographic workstation, shocked expression, subtle cinematic lighting",
                "camera": "Slow cinematic push-in to eye level, 35mm anamorphic lens",
                "audio_script": f"Jangan pernah coba {clean} sebelum kamu tahu rahasia penting ini!",
            },
            {
                "scene_num": 2,
                "role": "The Problem (05-12s)",
                "duration": 6,
                "action": "Dramatic overhead view of scattered business charts and messy ad dashboard showing budget loss with red indicators, cinematic contrast",
                "camera": "High-angle slow tilt down, moody corporate lighting",
                "audio_script": f"Banyak pemula boncos jutaan rupiah karena melewatkan 1 setting krusial di {clean}.",
            },
            {
                "scene_num": 3,
                "role": "The Discovery / Solution (12-20s)",
                "duration": 6,
                "action": "Futuristic clean minimalist office, smiling entrepreneur pointing at a green skyrocketing growth graph on a transparent glass monitor",
                "camera": "Smooth horizontal track left to right, golden hour natural light",
                "audio_script": "Padahal solusinya sederhana kalau kamu paham alur langkah demi langkahnya.",
            },
            {
                "scene_num": 4,
                "role": "Execution Breakdown (20-28s)",
                "duration": 8,
                "action": f"Hyper-detailed macro shot of hands clicking a futuristic luminous keyboard, screen displaying step-by-step verified workflow for {clean}",
                "camera": "Macro dolly zoom, vibrant cyber accents, depth of field",
                "audio_script": "Cukup ikuti 3 tahapan ini dan sistem akan bekerja secara otomatis untuk bisnismu.",
            },
            {
                "scene_num": 5,
                "role": "Call to Action / Outro (28-35s)",
                "duration": 6,
                "action": "Wide panoramic shot of an inspiring modern skyline at sunrise, clean minimalist logo placeholder hovering gently",
                "camera": "Epic slow drone pull-back, cinematic 8k, warm morning sunlight",
                "audio_script": "Ketik 'MAU' di komentar atau klik link di deskripsi untuk dapatkan blueprint lengkapnya sekarang!",
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
        queries_to_check = autocomplete_queries or [
            f"cara {seed} terbaru 2026",
            f"tutorial {seed} pemula step by step",
            f"{seed} tanpa modal",
            f"kesalahan fatal {seed}",
            f"{seed} gratis vs berbayar",
            f"trik rahasia {seed}",
            f"{seed} review jujur",
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
        return [
            {
                "clip_id": 1,
                "clip_title": f"Trik Terlarang {clean} yang Jarang Diungkap #shorts",
                "timestamp_window": "01:15 - 02:00 (45 Detik)",
                "hook_line": "Banyak orang boncos di 2026 gara-gara 1 tombol ini...",
                "core_insight": "Demonstrasi bagian teknis paling krusial yang langsung mengubah hasil.",
                "call_to_action": "Tonton tutorial full 15 menit di channel ini!",
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
                "hook_line": "Ini kesalahan paling fatal yang bikin akunmu kena suspend!",
                "core_insight": "Peringatan kontroversial berbasis pengalaman nyata yang memicu perdebatan di komentar.",
                "call_to_action": "Komen pendapatmu di bawah, pernah ngalamin juga?",
                "projected_virality": "9.5 / 10 🔥",
            },
        ]
