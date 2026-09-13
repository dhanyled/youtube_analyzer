"""Search Intelligence & YouTube Opportunity Engine.

Incorporates proven algorithms inspired by:
- VidIQ: Opportunity Score (Volume vs Competition), Video SEO Formulas
- TubeBuddy: Search Rank & Keyword Explorer Scoring
- NexLev: Outlier Detection (Viral Breakout multiplier) & Niche RPM Economics
"""

from typing import Any

from youtube_analyzer.core.models import IntentEnum


class SearchIntelligence:
    """Calculates keyword opportunity, outlier velocity, and monetization metrics."""

    # Benchmark RPM by Niche Categories (Estimated USD per 1,000 views)
    NICHE_RPM_BENCHMARKS: dict[str, dict[str, float]] = {
        "finance": {"low": 15.0, "avg": 24.0, "high": 40.0},
        "advertising": {"low": 12.0, "avg": 20.0, "high": 35.0},
        "tech": {"low": 7.0, "avg": 12.0, "high": 22.0},
        "business": {"low": 10.0, "avg": 18.0, "high": 30.0},
        "education": {"low": 4.0, "avg": 8.0, "high": 15.0},
        "gaming": {"low": 1.5, "avg": 2.8, "high": 5.0},
        "entertainment": {"low": 1.2, "avg": 2.5, "high": 4.5},
    }

    @staticmethod
    def calculate_opportunity_score(search_volume: int, competition_score: float) -> float:
        """
        Calculate VidIQ / TubeBuddy style overall opportunity score (0 - 100).
        - search_volume: Estimated monthly searches
        - competition_score: 0 (no competition) to 100 (saturated)
        """
        # Normalize search volume using logarithmic scale (10 to 100,000+)
        import math

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
        Calculate NexLev / VidIQ style Outlier Multiplier.
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
    def estimate_rpm(cls, topic_name: str) -> dict[str, Any]:
        """
        Estimate YouTube AdSense RPM (USD) based on topic keywords.
        NexLev-style monetization projection.
        """
        lowered = topic_name.lower()
        matched_niche = "business"

        if any(k in lowered for k in ["ads", "iklan", "marketing", "seo"]):
            matched_niche = "advertising"
        elif any(k in lowered for k in ["saham", "crypto", "keuangan", "finance", "investasi"]):
            matched_niche = "finance"
        elif any(k in lowered for k in ["coding", "python", "software", "tech", "gadget"]):
            matched_niche = "tech"
        elif any(k in lowered for k in ["game", "gaming", "play"]):
            matched_niche = "gaming"

        benchmark = cls.NICHE_RPM_BENCHMARKS.get(
            matched_niche, cls.NICHE_RPM_BENCHMARKS["business"]
        )
        return {
            "detected_niche": matched_niche,
            "rpm_range_usd": f"${benchmark['low']:.2f} - ${benchmark['high']:.2f}",
            "avg_rpm_usd": benchmark["avg"],
            "potential_earnings_per_100k_views": f"${benchmark['avg'] * 100:.2f}",
        }

    @staticmethod
    def generate_high_ctr_titles(seed: str, intent_type: IntentEnum) -> list[str]:
        """
        Generate high-CTR title formulas (VidIQ / TubeBuddy style)
        tailored to the target intent.
        """
        clean = seed.strip().title()

        if intent_type == IntentEnum.TUTORIAL:
            return [
                f"Cara {clean} dari Nol untuk Pemula (Step-by-Step 2026)",
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
                f"{clean}: Mana yang Lebih Menguntungkan di 2026?",
                f"Perbandingan Jujur {clean} Setelah 30 Hari Penggunaan",
            ]
        else:
            return [
                f"Apakah {clean} Masih Efektif di 2026? Data Membuktikannya",
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
