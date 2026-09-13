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
                "menggunakan Google Flow/Veo dengan kecepatan produksi 5x lebih cepat."
            )

        best_practices = [
            "1. Centang Wajib Disclosure: Selalu beri tanda 'Altered or synthetic content' saat upload di YouTube Studio agar bebas resiko penalti.",
            "2. Hook 3 Detik Pertama: Algoritma YouTube memprioritaskan Watch Time & Retention, bukan menghukum label AI. Pastikan visual pembuka langsung to-the-point.",
            "3. Pacing B-Roll Cepat: Gunakan klip video Google Flow berdurasi 4-6 detik per scene agar penonton tidak bosan.",
            "4. Expressive Audio: Gabungkan visual Google Flow dengan voiceover bernada emosional (ElevenLabs / human voice), hindari suara robotik flat.",
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
        Generate a production-ready Google Flow (Imagen 4 + Veo 3.1) Storyboard & Shotlist.
        Compatible with:
        - flow-agent / gflow-cli (prompts.txt batch format)
        - AutoFlowCut (CapCut / Premiere scene JSON)
        - veo-mcp (Direct Veo 3.1 API payload)
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
                    "tool": "kodelyx/flow-agent",
                    "command": f"flow batch flow_prompts_{clean.replace(' ', '_').lower()}.txt --type video --aspect {aspect_name}",
                    "best_for": "Akun Google Flow gratis/berlangganan via Chrome extension bridge.",
                },
                {
                    "tool": "AutoFlowCut",
                    "command": "Import manifest JSON -> Auto-generate visuals -> Export 1-klik ke CapCut / Premiere Pro",
                    "best_for": "Editing cepat langsung ke timeline video editor (CapCut/Premiere).",
                },
                {
                    "tool": "veo-mcp",
                    "command": "start_batch_video_generation(jobs, concurrency=2)",
                    "best_for": "Direct Google AI Studio API via MCP agent.",
                },
            ],
        }
