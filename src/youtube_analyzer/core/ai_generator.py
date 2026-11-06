"""AI Generator Module for Natural, High-CTR YouTube Title Packaging & SEO.

Supports multi-provider LLMs via direct HTTP requests (no extra heavy SDK dependencies):
- Google Gemini (Gemini 1.5/2.0 Flash)
- Groq (Llama 3.3 70B, etc.)
- OpenAI (GPT-4o, GPT-4o-mini)
- OpenRouter (OpenRouter Multi-Model)
- Custom OpenAI-Compatible Endpoints
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-flash-lite-latest",
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "openrouter": "google/gemini-2.0-flash-001",
    "custom": "default",
}


def _clean_json_response(raw_text: str) -> str:
    """Strip markdown code fence blocks if returned by the LLM."""
    text = raw_text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


class AITitleGenerator:
    """Orchestrates AI-driven title and SEO packaging generation based on real competitor data."""

    @staticmethod
    def build_prompt(
        seed: str,
        niche: str,
        competitors: list[dict[str, Any]],
    ) -> str:
        """Construct the YouTube Strategist prompt enriched with actual competitor SERP titles."""
        comp_summaries = []
        for i, comp in enumerate(competitors[:5], 1):
            title = comp.get("title", "Tanpa Judul")
            views = comp.get("views", "N/A")
            channel = comp.get("channel", "Kompetitor")
            comp_summaries.append(f'{i}. Judul: "{title}" | Views: {views} | Channel: {channel}')

        comp_context = (
            "\n".join(comp_summaries)
            if comp_summaries
            else "1. Tidak ada data kompetitor langsung."
        )

        return f"""Kamu adalah YouTube SEO & Title Packaging Strategist tingkat dunia dengan spesialisasi Click-Through-Rate (CTR) tinggi dan retensi penonton.

Topik Seed / Kata Kunci: "{seed}"
Kategori/Niche Terdeteksi: "{niche}"

Berikut adalah daftar Video Kompetitor yang saat ini menduduki Peringkat Teratas (Halaman 1) di YouTube untuk topik ini:
{comp_context}

TUGAS ANDA:
1. Analisis mengapa video kompetitor ranking #1 mendapatkan views tinggi, dan identifikasi celah kemasan judulnya (title packaging gap).
2. Buat judul tandingan utama (Outranking Title) yang jauh lebih memikat, berbobot, dan mengalahkan video #1 menggunakan prinsip NLP (Open Loop, Pattern Interrupt, High Contrast, Specific Numbers).
3. Buat 4 Alternatif Variasi Judul berdasarkan 4 Sudut Pandang Psikologi Penonton:
   - Curiosity Gap (Rasa penasaran akut, informasi tersembunyi/misteri)
   - High-Stakes Storytelling (Intensitas tinggi, kronologi detik-demi-detik, urgensi/risiko nyata)
   - Contrarian / Mitos vs Fakta (Mendobrak kekeliruan umum penonton)
   - Deep Dive / Analisis Tuntas (Pembahasan paling komprehensif, terstruktur & kredibel)
4. Buat 2 kalimat pembuka deskripsi (hook NLP) yang memancing klik di hasil pencarian sebelum terpotong tombol '...more', timestamps babak pembahasan yang proporsional sesuai durasi video kompetitor (wajib dimulai dari 00:00 dan tidak melebihi durasi video), dan 4 hashtags SEO.
5. Buat 1 baris Video Tags (15–20 kata kunci relevan dipisahkan tanda koma, maksimal 450 karakter) yang siap disalin langsung ke kolom Tags YouTube Studio.

PANDUAN GAYA BAHASA & NLP (WAJIB DIPATUHI):
- Gunakan Bahasa Indonesia yang 100% natural, luwes, dan humanis seperti kreator YouTube profesional papan atas.
- JANGAN gunakan kata-kata template klise seperti: "Semua yang wajib kamu tahu...", "Fakta gila...", "Jangan lakukan ini...", "Panduan pemula modal kecil".
- Terapkan prinsip psikologi NLP: gunakan angka konkret (bukan 'untung besar' tapi sebut angka riil), kontras tajam (modal vs omzet, mitos vs fakta), dan hilangkan rasa takut gagal penonton (risk reversal).
- Judul HARUS secara spesifik dan cerdas mengangkat konteks nyata yang dibahas kompetitor (misal: jika kuliner sebut teknik/bahan kunci; jika bisnis sebut modal/omzet riil; jika tutorial sebut studi kasus spesifik).

KEMBALIKAN HANYA FORMAT JSON MURNI TANPA PENJELASAN LAIN dengan struktur persis seperti ini:
{{
  "competitor_analysis": {{
    "weakness": "Celah spesifik kemasan judul kompetitor #1",
    "counter_strategy": "Bagaimana judul & sudut pandang kita memposisikan diri lebih unggul"
  }},
  "outranking_title": "Judul tandingan utama yang mengalahkan video #1",
  "title_formula": "Rumus psikologi judul ini, misal: [Hasil Riil] + [Garansi Ketahanan/Anti Gagal] + [Teknik Kunci]",
  "psychological_angles": {{
    "curiosity_gap": {{
      "label": "🔍 Misteri & Curiosity Gap",
      "title": "Judul variasi rasa penasaran",
      "rationale": "Alasan psikologi judul ini memicu klik tinggi"
    }},
    "high_stakes": {{
      "label": "⚡ Kronologi & High-Stakes Storytelling",
      "title": "Judul variasi intensitas / kronologi",
      "rationale": "Alasan judul ini memikat audiens penyuka ketegangan"
    }},
    "contrarian": {{
      "label": "🤯 Mitos vs Fakta / Kontrarian",
      "title": "Judul variasi mendobrak asumsi",
      "rationale": "Alasan penonton akan kaget dan ingin membuktikan"
    }},
    "deep_dive": {{
      "label": "📚 Deep Dive / Analisis Tuntas",
      "title": "Judul variasi dokumenter/panduan lengkap",
      "rationale": "Alasan judul ini dipilih penonton yang cari info berbobot"
    }}
  }},
  "two_line_hook": "2 kalimat pembuka deskripsi video yang memikat pembaca",
  "timestamps": [
    "00:00 - Pengantar & Kilas Peristiwa",
    "02:15 - Titik Awal & Latar Belakang Masalah",
    "06:30 - Kronologi Puncak Kejadian / Langkah Kunci",
    "11:00 - Dampak, Pelajaran & Analisis Kritis",
    "15:20 - Rangkuman Akhir & Solusi / Tindakan Nyata"
  ],
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"],
  "video_tags": "tag 1, tag 2, tag 3, tag 4, tag 5, tag 6, tag 7, tag 8, tag 9, tag 10"
}}"""

    @classmethod
    def call_gemini(
        cls,
        prompt: str,
        api_key: str,
        model: str = "gemini-flash-lite-latest",
    ) -> dict[str, Any]:
        """Call Google Gemini generateContent REST API."""
        models_to_try = [model]
        for fallback in [
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
        ]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = None
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "response_mime_type": "application/json",
                },
            }
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 404:
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    cleaned = _clean_json_response(raw_text)
                    return json.loads(cleaned)
            except Exception as e:
                logger.warning("Gemini model %s failed (%s), trying next fallback...", m, e)
                last_error = e

        if last_error:
            raise last_error
        raise RuntimeError("Failed to generate content with any Gemini model.")

    @classmethod
    def call_openai_compatible(
        cls,
        prompt: str,
        api_key: str,
        base_url: str,
        model: str,
    ) -> dict[str, Any]:
        """Call OpenAI-compatible chat completions REST API (Groq, OpenAI, OpenRouter, etc.)."""
        endpoint = (
            f"{base_url.rstrip('/')}/chat/completions"
            if not base_url.endswith("/chat/completions")
            else base_url
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a YouTube SEO and Title Packaging Strategist. "
                        "Always respond ONLY with valid JSON matching the requested schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            cleaned = _clean_json_response(raw_text)
            return json.loads(cleaned)

    @classmethod
    def generate_strategy(
        cls,
        seed: str,
        niche: str,
        competitors: list[dict[str, Any]],
        provider: str,
        api_key: str,
        model_name: str | None = None,
        custom_base_url: str | None = None,
    ) -> dict[str, Any]:
        """Orchestrate the API call based on selected provider."""
        provider_clean = provider.strip().lower()
        model = model_name or DEFAULT_MODELS.get(provider_clean, "default")
        prompt = cls.build_prompt(seed, niche, competitors)

        if "gemini" in provider_clean:
            return cls.call_gemini(prompt=prompt, api_key=api_key, model=model)
        elif "groq" in provider_clean:
            return cls.call_openai_compatible(
                prompt=prompt,
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                model=model,
            )
        elif "openrouter" in provider_clean:
            return cls.call_openai_compatible(
                prompt=prompt,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                model=model,
            )
        elif "openai" in provider_clean:
            return cls.call_openai_compatible(
                prompt=prompt,
                api_key=api_key,
                base_url="https://api.openai.com/v1",
                model=model,
            )
        elif "custom" in provider_clean and custom_base_url:
            return cls.call_openai_compatible(
                prompt=prompt,
                api_key=api_key,
                base_url=custom_base_url,
                model=model,
            )
        else:
            # Fallback to OpenAI-compatible generic
            target_url = custom_base_url or "https://api.openai.com/v1"
            return cls.call_openai_compatible(
                prompt=prompt, api_key=api_key, base_url=target_url, model=model
            )

    @staticmethod
    def build_audit_prompt(
        video_details: dict[str, Any],
        transcript_text: str,
        competitors: list[dict[str, Any]],
    ) -> str:
        """Construct the prompt to audit and revamp an existing or unlisted YouTube video."""
        title = video_details.get("title", "")
        desc = video_details.get("description", "")
        tags = video_details.get("tags", [])
        tags_str = ", ".join(tags) if tags else "(Tidak ada tags terpasang)"
        views = video_details.get("views_display", "N/A")
        duration = video_details.get("duration", "N/A")
        channel = video_details.get("channel", "N/A")

        comp_summaries = []
        for i, comp in enumerate(competitors[:5], 1):
            c_title = comp.get("title", "Tanpa Judul")
            c_views = comp.get("views", "N/A")
            c_channel = comp.get("channel", "Kompetitor")
            comp_summaries.append(
                f'{i}. Judul: "{c_title}" | Views: {c_views} | Channel: {c_channel}'
            )
        comp_context = "\n".join(comp_summaries) if comp_summaries else "Tidak ada data kompetitor."

        transcript_preview = (
            transcript_text[:3500]
            if transcript_text
            else "(Transkrip/subtitle tidak tersedia, gunakan acuan judul & deskripsi)"
        )

        return f"""Kamu adalah YouTube SEO Auditor & Title Packaging Strategist tingkat dunia dengan spesialisasi Click-Through-Rate (CTR), NLP Hooks, dan Google Search SEO.

KITA SEDANG MENG-AUDIT & ME-REVAMP VIDEO YOUTUBE BERIKUT:
- Judul Video Saat Ini: "{title}"
- Channel: {channel} | Durasi: {duration} | Views: {views}
- Deskripsi Saat Ini:
\"\"\"{desc[:1000] if desc else "(Kosong)"}\"\"\"
- Tags Saat Ini: {tags_str}

KONTEN / TRANSKRIP ASLI YANG DIBICARAKAN DALAM VIDEO (Cuplikan):
\"\"\"{transcript_preview}\"\"\"

KOMPETITOR TOP RANKING DI YOUTUBE UNTUK TOPIK INI:
{comp_context}

TUGAS ANDA:
1. AUDIT & DIAGNOSIS:
   - Nilai judul saat ini (skor 1-10) dan sebutkan kelemahan fatalnya (misal: tidak ada hook rasa penasaran, kata-kata kaku, membosankan, atau tanpa kontras).
   - Nilai deskripsi saat ini (skor 1-10) dan sebutkan kelemahannya (misal: 2 baris awal terbuang sia-sia sebelum terpotong tombol '...more', tidak ada chapter timestamps, minim keyword pencarian Google).
   - Nilai tags saat ini (skor 1-10) dan kelemahannya.
2. OUTRANKING TITLE (JUDUL UTAMA BARU):
   - Buat 1 judul baru yang jauh lebih memikat, berbobot, dan mengalahkan kompetitor, menggunakan prinsip NLP (Open Loop, Pattern Interrupt, High Contrast, Specific Numbers/Proof).
   - Tuliskan rumus psikologinya (Title Formula).
3. 4 SUDUT PANDANG VARIASI JUDUL (PSYCHOLOGICAL ANGLES):
   - Curiosity Gap (Rasa penasaran akut / misteri)
   - High-Stakes Storytelling (Urgensi tinggi / kronologi / risiko)
   - Contrarian / Mitos vs Fakta (Mendobrak kekeliruan umum penonton)
   - Deep Dive / Panduan Tuntas (Pembahasan paling komprehensif & kredibel)
4. REVAMPED DESCRIPTION (DESKRIPSI LENGKAP SIAP PAKAI):
   - two_line_hook: 2 kalimat pembuka deskripsi yang memancing klik di hasil pencarian YouTube & Google snippet sebelum terpotong tombol '...more'.
   - full_description: Deskripsi lengkap siap copy-paste ke YouTube Studio yang berisi:
     * 2-line hook di atas
     * Sinopsis konten berbobot yang merangkum poin-poin utama yang dibicarakan dalam transkrip/video
     * Timestamps / Chapters babak pembahasan lengkap (gunakan acuan waktu dari transkrip atau durasi video {duration})
     * Call-To-Action (CTA) subscribe & interaksi
     * 4-5 Hashtags SEO (#...)
5. VIDEO TAGS:
   - 1 baris video tags (15-20 kata kunci relevan dipisahkan tanda koma, maksimal 450 karakter) siap di-copy ke kolom Tags YouTube Studio.
6. GOOGLE SEO STRATEGY:
   - 2-3 tips singkat bagaimana video ini bisa muncul di Google Search Video Carousel dan fitur Google "Key Moments".

PANDUAN GAYA BAHASA & NLP (WAJIB DIPATUHI):
- Gunakan Bahasa Indonesia yang 100% natural, humanis, luwes seperti YouTuber papan atas.
- DILARANG menggunakan kata-kata klise robotik: "Semua yang wajib kamu tahu...", "Fakta mengejutkan...", "Jangan lakukan ini...", "Panduan pemula modal kecil".
- Selaraskan judul dan deskripsi dengan apa yang BENAR-BENAR dibahas dalam transkrip/video.
- ATURAN KETAT RELEVANSI TAGS & HASHTAGS (ANTI-CLICKBAIT):
  * Seluruh tags dan hashtags WAJIB 100% relevan dengan apa yang benar-benar dibahas dalam transkrip/video.
  * DILARANG KERAS menyematkan tag clickbait/spam yang tidak relevan (seperti 'gratis', 'free', 'tanpa modal', 'download', 'viral', 'fyp') KECUALI jika isi/topik video memang secara eksplisit membahas konten gratis/free/tanpa modal.
  * Jika video membahas materi berbayar atau umum (bukan materi gratis), kata 'gratis' tidak boleh dimunculkan sama sekali di tags.

KEMBALIKAN HANYA FORMAT JSON MURNI TANPA MARKDOWN LAIN dengan struktur persis seperti ini:
{{
  "audit": {{
    "title_score": 5,
    "title_flaws": "Penjelasan kelemahan judul lama...",
    "description_score": 4,
    "description_flaws": "Penjelasan kelemahan deskripsi lama...",
    "tags_score": 4,
    "tags_flaws": "Penjelasan kelemahan tags lama..."
  }},
  "outranking_title": "Judul baru hasil revamp yang siap mengalahkan kompetitor",
  "title_formula": "[Formula psikologi judul ini]",
  "psychological_angles": {{
    "curiosity_gap": {{
      "label": "🔍 Misteri & Curiosity Gap",
      "title": "Variasi judul penasaran",
      "rationale": "Alasan psikologi klik"
    }},
    "high_stakes": {{
      "label": "⚡ Kronologi & High-Stakes Storytelling",
      "title": "Variasi judul intensitas/kronologi",
      "rationale": "Alasan psikologi klik"
    }},
    "contrarian": {{
      "label": "🤯 Mitos vs Fakta / Kontrarian",
      "title": "Variasi judul mendobrak mitos",
      "rationale": "Alasan psikologi klik"
    }},
    "deep_dive": {{
      "label": "📚 Deep Dive / Analisis Tuntas",
      "title": "Variasi judul masterclass tuntas",
      "rationale": "Alasan psikologi klik"
    }}
  }},
  "two_line_hook": "2 kalimat pembuka deskripsi video untuk memancing klik snippet...",
  "full_description": "Teks lengkap deskripsi video siap salin...",
  "video_tags": "tag 1, tag 2, tag 3, tag 4, tag 5, tag 6, tag 7, tag 8, tag 9, tag 10, tag 11, tag 12, tag 13, tag 14, tag 15",
  "google_seo_strategy": "Tips spesifik agar masuk Google Video Carousel & Key Moments..."
}}"""

    @staticmethod
    def build_pre_upload_prompt(
        topic: str,
        content_notes: str,
        target_format: str,
        duration: str,
        competitors: list[dict[str, Any]],
    ) -> str:
        """Construct the prompt to package a not-yet-uploaded video based on notes/script outline."""
        comp_summaries = []
        for i, comp in enumerate(competitors[:5], 1):
            c_title = comp.get("title", "Tanpa Judul")
            c_views = comp.get("views", "N/A")
            c_channel = comp.get("channel", "Kompetitor")
            comp_summaries.append(
                f'{i}. Judul: "{c_title}" | Views: {c_views} | Channel: {c_channel}'
            )
        comp_context = "\n".join(comp_summaries) if comp_summaries else "Tidak ada data kompetitor."

        return f"""Kamu adalah YouTube SEO Strategist & Launch Director tingkat dunia dengan spesialisasi Click-Through-Rate (CTR), NLP Hooks, dan Google Search SEO.

KITA SEDANG MERANCANG STRATEGI PELUNCURAN VIDEO YOUTUBE YANG BELUM DIUPLOAD (DRAFT PRE-UPLOAD):
- Topik / Judul Sementara: "{topic}"
- Format Rencana: {target_format} (Landscape 16:9 atau Shorts 9:16)
- Estimasi Durasi: {duration}
- Ringkasan Naskah / Poin-Poin Bahasan Video:
\"\"\"{content_notes[:3500]}\"\"\"

KOMPETITOR TOP RANKING DI YOUTUBE SAAT INI UNTUK TOPIK INI:
{comp_context}

TUGAS ANDA:
1. DETEKSI & RANGKUMAN INTI KONTEN:
   - Rangkum dalam 1-2 kalimat apa inti nilai jual (unique value proposition) dari video ini berdasarkan poin bahasan di atas.
2. OUTRANKING TITLE (JUDUL UTAMA PELUNCURAN):
   - Buat 1 judul utama yang berdaya ledak CTR tinggi dengan NLP (Open Loop, Pattern Interrupt, Kontras Nyata, Angka Konkret).
   - Tuliskan rumus psikologinya (Title Formula).
3. 4 SUDUT PANDANG VARIASI JUDUL (PSYCHOLOGICAL ANGLES):
   - Curiosity Gap (Rasa penasaran akut / rahasia)
   - High-Stakes Storytelling (Urgensi / risiko / kronologi)
   - Contrarian / Mitos vs Fakta (Mendobrak kekeliruan umum)
   - Deep Dive / Panduan Tuntas (Pembahasan terstruktur & berbobot)
4. PAKET DESKRIPSI LENGKAP:
   - two_line_hook: 2 kalimat pembuka deskripsi yang memancing klik di hasil pencarian.
   - full_description: Deskripsi lengkap siap copy-paste ke YouTube Studio yang berisi:
     * 2-line hook
     * Sinopsis poin bahasan
     * Timestamps draft babak pembahasan (rancang babak 00:00 hingga durasi {duration})
     * Call-To-Action (CTA)
     * 4-5 Hashtags SEO (#...)
5. VIDEO TAGS:
   - 1 baris video tags (15-20 kata kunci dipisahkan koma, < 450 karakter) siap paste ke kolom Tags YouTube Studio.
6. BEST PRACTICE PELUNCURAN (PRE-LAUNCH CHECKLIST):
   - 3 tips taktis sebelum mem-publish video (tips upload Unlisted terlebih dahulu untuk processing resolusi tinggi & subtitle otomatis, tips hook 5 detik pertama, tips thumbnail).

PANDUAN GAYA BAHASA & NLP (WAJIB DIPATUHI):
- Bahasa Indonesia yang 100% natural, humanis, luwes tanpa kata-kata klise robotik.
- Sesuaikan secara presisi dengan poin bahasan yang diberikan.
- ATURAN KETAT RELEVANSI TAGS & HASHTAGS (ANTI-CLICKBAIT):
  * Seluruh tags dan hashtags WAJIB 100% relevan dengan apa yang benar-benar dibahas dalam poin materi naskah.
  * DILARANG KERAS menyematkan tag clickbait/spam yang tidak relevan (seperti 'gratis', 'free', 'tanpa modal', 'download', 'viral', 'fyp') KECUALI jika materi naskah memang secara eksplisit membahas konten gratis/free/tanpa modal.
  * Jika video tidak membahas konten gratis, kata 'gratis' tidak boleh dimunculkan sama sekali di tags.

KEMBALIKAN HANYA FORMAT JSON MURNI TANPA MARKDOWN LAIN dengan struktur persis seperti ini:
{{
  "detected_content_summary": "Rangkuman 1-2 kalimat tentang inti nilai jual video...",
  "outranking_title": "Judul utama peluncuran dengan CTR tinggi",
  "title_formula": "[Formula psikologi judul ini]",
  "psychological_angles": {{
    "curiosity_gap": {{
      "label": "🔍 Misteri & Curiosity Gap",
      "title": "Variasi judul penasaran",
      "rationale": "Alasan psikologi klik"
    }},
    "high_stakes": {{
      "label": "⚡ Kronologi & High-Stakes Storytelling",
      "title": "Variasi judul intensitas/kronologi",
      "rationale": "Alasan psikologi klik"
    }},
    "contrarian": {{
      "label": "🤯 Mitos vs Fakta / Kontrarian",
      "title": "Variasi judul mendobrak mitos",
      "rationale": "Alasan psikologi klik"
    }},
    "deep_dive": {{
      "label": "📚 Deep Dive / Analisis Tuntas",
      "title": "Variasi judul masterclass tuntas",
      "rationale": "Alasan psikologi klik"
    }}
  }},
  "two_line_hook": "2 kalimat pembuka deskripsi...",
  "full_description": "Teks lengkap deskripsi draft video siap salin...",
  "video_tags": "tag 1, tag 2, tag 3, tag 4, tag 5, tag 6, tag 7, tag 8, tag 9, tag 10, tag 11, tag 12, tag 13, tag 14, tag 15",
  "launch_checklist": [
    "Upload sebagai Unlisted (Tidak Publik) selama 2-4 jam agar pemrosesan resolusi 4K/1080p dan transkrip otomatis tuntas.",
    "Pastikan hook 5 detik pertama langsung menjawab janji pada judul tanpa basa-basi intro panjang.",
    "Gunakan thumbnail dengan kontras tajam (maksimal 3 kata kunci besar) yang melengkapi rasa penasaran judul."
  ]
}}"""

    @classmethod
    def _execute_llm(
        cls,
        prompt: str,
        provider: str,
        api_key: str,
        model_name: str | None = None,
        custom_base_url: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch LLM prompt to the selected provider."""
        provider_clean = provider.strip().lower()
        model = model_name or DEFAULT_MODELS.get(provider_clean, "default")
        if "gemini" in provider_clean:
            return cls.call_gemini(prompt=prompt, api_key=api_key, model=model)
        elif "groq" in provider_clean:
            return cls.call_openai_compatible(
                prompt=prompt,
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
                model=model,
            )
        elif "openrouter" in provider_clean:
            return cls.call_openai_compatible(
                prompt=prompt, api_key=api_key, base_url="https://openrouter.ai/api/v1", model=model
            )
        elif "openai" in provider_clean:
            return cls.call_openai_compatible(
                prompt=prompt, api_key=api_key, base_url="https://api.openai.com/v1", model=model
            )
        else:
            target_url = custom_base_url or "https://api.openai.com/v1"
            return cls.call_openai_compatible(
                prompt=prompt, api_key=api_key, base_url=target_url, model=model
            )

    @classmethod
    def generate_synchronized_timestamps(
        cls,
        topic: str,
        duration: str | int | None,
        transcript_data: dict[str, Any] | None = None,
        chapter_labels: list[str] | None = None,
    ) -> list[str]:
        """
        Generate YouTube chapter timestamps strictly synchronized with actual video duration.
        - Guarantees 00:00 start (mandatory for YouTube).
        - Guarantees NO timestamp exceeds video duration.
        - If real transcript points exist, derives chapters from actual speech moments.
        - If Shorts (<= 60s), returns empty list (chapters don't apply).
        - If custom chapter_labels provided, dynamically positions them proportionally across the video.
        """
        from youtube_analyzer.connectors.youtube import YouTubeConnector

        total_sec = YouTubeConnector.parse_duration_to_seconds(duration)
        if total_sec <= 0:
            total_sec = 600  # Default 10 mins if duration unknown

        # Shorts do not use chapter timestamps on YouTube
        if total_sec <= 60:
            return []

        def _fmt_ts(s: int) -> str:
            h = s // 3600
            m = (s % 3600) // 60
            sec = s % 60
            return f"{h}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"

        default_labels = [
            "Pengantar & Masalah Utama",
            "Titik Kritis yang Sering Diabaikan",
            "Bedah Konsep & Strategi Inti",
            "Studi Kasus & Eksekusi Lapangan",
            "Rangkuman & Langkah Selanjutnya",
        ]
        target_labels = (
            chapter_labels if (chapter_labels and len(chapter_labels) >= 3) else default_labels
        )

        # 1. Try deriving from real transcript if available
        if transcript_data and transcript_data.get("available"):
            raw_text = transcript_data.get("timestamped_text", "")
            matches = re.findall(r"\[(\d{1,2}):(\d{2})\]\s*(.*)", raw_text)
            if matches and len(matches) >= 3:
                parsed_snippets = []
                for m_str, s_str, txt in matches:
                    sec_val = int(m_str) * 60 + int(s_str)
                    if sec_val < total_sec * 0.95:
                        parsed_snippets.append((sec_val, txt.strip()))

                if len(parsed_snippets) >= 3:
                    num_targets = min(len(target_labels), len(parsed_snippets))
                    step = max(1, len(parsed_snippets) // num_targets)
                    picked = [parsed_snippets[0]]
                    for i in range(1, num_targets):
                        idx = min(i * step, len(parsed_snippets) - 1)
                        if parsed_snippets[idx][0] > picked[-1][0] + 25:
                            picked.append(parsed_snippets[idx])

                    res = ["00:00 - " + target_labels[0]]
                    for i, (ts_sec, _) in enumerate(picked[1:], 1):
                        label = target_labels[i] if i < len(target_labels) else f"Babak {i + 1}"
                        res.append(f"{_fmt_ts(ts_sec)} - {label}")
                    return res

        # 2. Proportional chapters strictly scaled within duration
        chapters = []
        n_labels = len(target_labels)
        for i, label in enumerate(target_labels):
            if i == 0:
                ts_sec = 0
            else:
                pct = min(0.88, (i / max(n_labels - 1, 1)) * 0.85)
                ts_sec = int(total_sec * pct)
            chapters.append(f"{_fmt_ts(ts_sec)} - {label}")

        return chapters

    @classmethod
    def audit_and_revamp(
        cls,
        video_details: dict[str, Any],
        transcript_data: dict[str, Any] | None = None,
        competitors: list[dict[str, Any]] | None = None,
        provider: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        custom_base_url: str | None = None,
    ) -> dict[str, Any]:
        """Execute audit and revamp on a live or unlisted YouTube video."""
        transcript_data = transcript_data or {}
        competitors = competitors or []
        transcript_text = (
            transcript_data.get("timestamped_text") or transcript_data.get("full_text") or ""
        )
        prompt = cls.build_audit_prompt(video_details, transcript_text, competitors)

        raw_title = video_details.get("title", "Video YouTube")
        clean_topic = raw_title.split("-")[0].split("|")[0].strip()
        raw_dur = video_details.get("duration", "10:00")

        # AI mode is triggered when provider is requested and key exists
        effective_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GROQ_API_KEY")
        )
        effective_provider = provider or "gemini"

        if effective_key and provider is not None:
            try:
                res = cls._execute_llm(
                    prompt=prompt,
                    provider=effective_provider,
                    api_key=effective_key,
                    model_name=model_name,
                    custom_base_url=custom_base_url,
                )
                if "hashtags" in res and isinstance(res["hashtags"], list):
                    res["hashtags"] = [
                        h
                        for h in res["hashtags"]
                        if h.lower() not in ["#youtubeseo", "#videomarketing"]
                    ]

                from youtube_analyzer.core.normalizer import TopicNormalizer

                full_audit_ctx = f"{raw_title} {video_details.get('description', '')} {transcript_text} {' '.join(c.get('title', '') for c in competitors)}".strip()
                if "video_tags" in res and isinstance(res["video_tags"], str):
                    res["tag_audit"] = TopicNormalizer.audit_tags_detailed(
                        res["video_tags"], context_text=full_audit_ctx
                    )
                    res["video_tags"] = res["tag_audit"]["clean_comma_string"]
                else:
                    res["tag_audit"] = TopicNormalizer.audit_tags_detailed(
                        "", context_text=full_audit_ctx
                    )

                res["blindspot_audit"] = TopicNormalizer.audit_content_blindspots(
                    title=res.get("outranking_title", raw_title),
                    description=res.get("full_description", ""),
                    tags=res.get("video_tags", ""),
                    context_notes=f"{transcript_text} {video_details.get('description', '')}",
                    target_format=str(video_details.get("format", "LANDSCAPE (16:9)")),
                )
                if "hashtags" in res and isinstance(res["hashtags"], list):
                    res["hashtags"] = [
                        h
                        for h in res["hashtags"]
                        if TopicNormalizer.is_tag_relevant(
                            h.lstrip("#"), context_text=full_audit_ctx
                        )
                    ]

                from youtube_analyzer.connectors.youtube import parse_duration_to_seconds

                max_sec = parse_duration_to_seconds(raw_dur)
                if max_sec <= 60 or "short" in str(video_details.get("format", "")).lower():
                    res["timestamps"] = []
                elif "timestamps" in res and isinstance(res["timestamps"], list):
                    has_overflow = False
                    for ts in res["timestamps"]:
                        parts = str(ts).split("-")[0].strip().split(":")
                        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                            if int(parts[0]) * 60 + int(parts[1]) > max_sec:
                                has_overflow = True
                                break
                    if has_overflow or len(res["timestamps"]) < 3:
                        res["timestamps"] = cls.generate_synchronized_timestamps(
                            clean_topic, raw_dur, transcript_data
                        )
                return res
            except Exception as e:
                logger.warning(f"AI audit generation failed: {e}. Falling back to heuristic audit.")

        # Fallback heuristic audit with truthful real-data evaluation
        title_words = raw_title.split()
        title_score = 7 if len(title_words) >= 6 else 5
        desc = video_details.get("description", "")
        desc_score = 7 if len(desc) > 300 and ("00:00" in desc or "0:00" in desc) else 4
        studio_tags = video_details.get("studio_tags") or video_details.get("tags", [])
        desc_hashtags = video_details.get("desc_hashtags") or [
            f"#{w}" for w in re.findall(r"#([a-zA-Z0-9_\u00c0-\u00ff]+)", desc) if w
        ]

        if studio_tags:
            tags_count = len(studio_tags)
            tags_score = min(9, max(6, tags_count // 2))
            tags_flaws = f"Terpasang {tags_count} tags riil di YouTube Studio. Optimalkan dengan kata kunci bervolume tinggi yang terbukti dipakai kompetitor ranking 1."
        elif desc_hashtags:
            tags_score = 5
            tags_flaws = f"Kolom Tags YouTube Studio masih kosong (0 tags), baru terpasang {len(desc_hashtags)} hashtag di deskripsi. Sangat disarankan mengisi 15–20 kata kunci ke kolom Tags Studio."
        else:
            tags_score = 3
            tags_flaws = "Belum ada tags di YouTube Studio maupun hashtag di deskripsi. Sangat disarankan memasang 15–20 keyword turunan relevan."

        clean_topic = raw_title.split("-")[0].split("|")[0].strip()
        outranking_title = (
            f"Bongkar Fakta {clean_topic}: Analisis Tuntas & Strategi yang Terbukti Efektif"
        )

        raw_dur = video_details.get("duration", "10:00")
        timestamps_list = cls.generate_synchronized_timestamps(
            clean_topic, raw_dur, transcript_data
        )
        if timestamps_list:
            timestamps_block = "⏳ TIMESTAMPS BABAK PEMBAHASAN:\n" + "\n".join(timestamps_list)
        else:
            timestamps_block = "⚡ Video Format Shorts (Tanpa Chapters)"

        # Generate topic-specific hashtags (NO generic #YouTubeSEO!)
        clean_tag = "".join(w.capitalize() for w in clean_topic.split() if w.isalnum())
        hashtags = [
            f"#{clean_tag}",
            f"#{clean_tag}Indonesia",
            f"#Tips{clean_tag}",
            f"#Tutorial{clean_tag}",
        ]

        # Gather real competitor tags if provided and filter for strict content relevance
        from youtube_analyzer.core.normalizer import TopicNormalizer

        full_audit_ctx = f"{raw_title} {desc} {transcript_text} {' '.join(c.get('title', '') for c in competitors)}".strip()
        comp_tags = []
        for c in competitors or []:
            if c.get("tags"):
                comp_tags.extend(c.get("tags", []))
        comp_tags = TopicNormalizer.filter_relevant_tags(comp_tags, context_text=full_audit_ctx)

        if comp_tags:
            merged_tags = comp_tags[:12]
            focus_tags = [
                clean_topic.lower(),
                f"tutorial {clean_topic.lower()}",
                f"cara {clean_topic.lower()}",
            ]
            for ft in focus_tags:
                if ft not in [t.lower() for t in merged_tags]:
                    merged_tags.append(ft)
            video_tags_str = TopicNormalizer.clean_comma_tags(
                ", ".join(merged_tags[:18]), context_text=full_audit_ctx
            )
        else:
            raw_vtags = f"{clean_topic.lower()}, panduan {clean_topic.lower()}, tips {clean_topic.lower()}, cara {clean_topic.lower()}, belajar {clean_topic.lower()}, {clean_topic.lower()} indonesia, tutorial {clean_topic.lower()}"
            video_tags_str = TopicNormalizer.clean_comma_tags(
                raw_vtags, context_text=full_audit_ctx
            )

        tag_audit = TopicNormalizer.audit_tags_detailed(video_tags_str, context_text=full_audit_ctx)
        video_tags_str = tag_audit["clean_comma_string"]
        blindspot_audit = TopicNormalizer.audit_content_blindspots(
            title=outranking_title,
            description=f"Apakah Anda yakin pemahaman tentang {clean_topic} sudah benar? Simak bedah tuntas fakta lapangan dan langkah praktisnya di video ini.\n\nDalam video ini, kita membedah secara mendalam topik {clean_topic} mulai dari konsep dasar hingga studi kasus nyata.\n\n{timestamps_block}\n\n📌 Jangan lupa Like, Comment, dan Subscribe agar tidak ketinggalan analisis mendalam berikutnya!\n\n{' '.join(hashtags)}",
            tags=video_tags_str,
            context_notes=f"{transcript_text} {video_details.get('description', '')}",
            target_format=str(video_details.get("format", "LANDSCAPE (16:9)")),
        )

        return {
            "audit": {
                "title_score": title_score,
                "title_flaws": "Judul kurang menyematkan kontras tajam atau angka spesifik yang memicu rasa penasaran alami.",
                "description_score": desc_score,
                "description_flaws": "Dua baris pertama belum optimal sebagai hook pencarian, dan struktur timestamps/chapters belum lengkap.",
                "tags_score": tags_score,
                "tags_flaws": tags_flaws,
            },
            "tag_audit": tag_audit,
            "blindspot_audit": blindspot_audit,
            "outranking_title": outranking_title,
            "title_formula": "[Kontras/Bongkar Fakta] + [Topik Utama] + [Solusi Nyata]",
            "psychological_angles": {
                "curiosity_gap": {
                    "label": "🔍 Misteri & Curiosity Gap",
                    "title": f"Hal yang Jarang Dibahas Orang tentang {clean_topic} (Dan Kenapa Ini Penting)",
                    "rationale": "Memicu 'takut ketinggalan informasi berharga' bagi penonton.",
                },
                "high_stakes": {
                    "label": "⚡ Kronologi & High-Stakes Storytelling",
                    "title": f"Detik-Detik Krusial {clean_topic}: Pelajaran Nyata dari Lapangan",
                    "rationale": "Memberikan kesan urgensi dan intensitas tinggi.",
                },
                "contrarian": {
                    "label": "🤯 Mitos vs Fakta / Kontrarian",
                    "title": f"Salah Kaprah Terbesar Soal {clean_topic} yang Sering Menyesatkan Banyak Orang",
                    "rationale": "Mendobrak asumsi umum sehingga audiens ingin membuktikan kebenarannya.",
                },
                "deep_dive": {
                    "label": "📚 Deep Dive / Analisis Tuntas",
                    "title": f"Panduan Lengkap {clean_topic}: Bedah Tuntas Langkah demi Langkah dari Nol",
                    "rationale": "Menargetkan penonton berniat riset yang mencari konten paling komprehensif.",
                },
            },
            "two_line_hook": f"Apakah Anda yakin pemahaman tentang {clean_topic} sudah benar? Simak bedah tuntas fakta lapangan dan langkah praktisnya di video ini.",
            "full_description": f"Apakah Anda yakin pemahaman tentang {clean_topic} sudah benar? Simak bedah tuntas fakta lapangan dan langkah praktisnya di video ini.\n\nDalam video ini, kita membedah secara mendalam topik {clean_topic} mulai dari konsep dasar hingga studi kasus nyata.\n\n{timestamps_block}\n\n📌 Jangan lupa Like, Comment, dan Subscribe agar tidak ketinggalan analisis mendalam berikutnya!\n\n{' '.join(hashtags)}",
            "video_tags": video_tags_str,
            "google_seo_strategy": "Sertakan timestamps di deskripsi agar Google Web mendeteksi 'Key Moments', dan gunakan kata tanya alami (apa, bagaimana, kenapa) di judul babak.",
        }

    @classmethod
    def plan_pre_upload(
        cls,
        topic: str,
        content_notes: str,
        target_format: str,
        duration: str,
        competitors: list[dict[str, Any]],
        provider: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        custom_base_url: str | None = None,
    ) -> dict[str, Any]:
        """Execute pre-upload packaging strategy on draft notes/script."""
        prompt = cls.build_pre_upload_prompt(
            topic, content_notes, target_format, duration, competitors
        )

        # AI mode is triggered when provider is requested and key exists
        effective_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GROQ_API_KEY")
        )
        effective_provider = provider or "gemini"

        if effective_key and provider is not None:
            try:
                res = cls._execute_llm(
                    prompt=prompt,
                    provider=effective_provider,
                    api_key=effective_key,
                    model_name=model_name,
                    custom_base_url=custom_base_url,
                )
                from youtube_analyzer.core.normalizer import TopicNormalizer

                pre_ctx = f"{topic} {content_notes} {' '.join(c.get('title', '') for c in competitors)}".strip()
                if "video_tags" in res and isinstance(res["video_tags"], str):
                    res["tag_audit"] = TopicNormalizer.audit_tags_detailed(
                        res["video_tags"], context_text=pre_ctx
                    )
                    res["video_tags"] = res["tag_audit"]["clean_comma_string"]
                else:
                    res["tag_audit"] = TopicNormalizer.audit_tags_detailed("", context_text=pre_ctx)
                if "hashtags" in res and isinstance(res["hashtags"], list):
                    res["hashtags"] = [
                        h
                        for h in res["hashtags"]
                        if h.lower() not in ["#youtubeseo", "#videomarketing"]
                        and TopicNormalizer.is_tag_relevant(h.lstrip("#"), context_text=pre_ctx)
                    ]
                res["blindspot_audit"] = TopicNormalizer.audit_content_blindspots(
                    title=res.get("outranking_title", topic),
                    description=res.get("full_description", ""),
                    tags=res.get("video_tags", ""),
                    context_notes=content_notes,
                    target_format=target_format,
                )
                return res
            except Exception as e:
                logger.warning(f"AI pre-upload plan failed: {e}. Falling back to heuristic plan.")

        clean = topic.strip().title()
        is_shorts = "9:16" in target_format or "short" in target_format.lower()
        suffix = " #shorts" if is_shorts else ""

        # Synchronized timestamps strictly within user duration
        ts_list = cls.generate_synchronized_timestamps(clean, duration)
        if ts_list:
            ts_block = "⏳ TIMESTAMPS PEMBAHASAN:\n" + "\n".join(ts_list)
        else:
            ts_block = "⚡ Video Format Shorts (Pacing Cepat Tanpa Chapters)"

        # Topical hashtags without generic tags
        clean_tag = "".join(w.capitalize() for w in clean.split() if w.isalnum())
        hashtags_pre = [
            f"#{clean_tag}",
            f"#{clean_tag}Indonesia",
            f"#Tips{clean_tag}",
            f"#Tutorial{clean_tag}",
        ]

        # Competitor tags integration if available, filtered for strict content relevance
        from youtube_analyzer.core.normalizer import TopicNormalizer

        pre_ctx = (
            f"{topic} {content_notes} {' '.join(c.get('title', '') for c in competitors)}".strip()
        )
        comp_tags = []
        for c in competitors or []:
            if c.get("tags"):
                comp_tags.extend(c.get("tags", []))
        comp_tags = TopicNormalizer.filter_relevant_tags(comp_tags, context_text=pre_ctx)

        if comp_tags:
            merged_tags = comp_tags[:12]
            focus_tags = [clean.lower(), f"tutorial {clean.lower()}", f"cara {clean.lower()}"]
            for ft in focus_tags:
                if ft not in [t.lower() for t in merged_tags]:
                    merged_tags.append(ft)
            v_tags_str = TopicNormalizer.clean_comma_tags(
                ", ".join(merged_tags[:18]), context_text=pre_ctx
            )
        else:
            raw_pre_tags = f"{clean.lower()}, cara {clean.lower()}, tutorial {clean.lower()}, tips {clean.lower()}, belajar {clean.lower()}, strategi {clean.lower()}, {clean.lower()} indonesia, panduan {clean.lower()}"
            v_tags_str = TopicNormalizer.clean_comma_tags(raw_pre_tags, context_text=pre_ctx)

        tag_audit = TopicNormalizer.audit_tags_detailed(v_tags_str, context_text=pre_ctx)
        v_tags_str = tag_audit["clean_comma_string"]
        heuristic_title = (
            f"Rahasia Praktis {clean}: Langkah demi Langkah yang Benar-Benar Berhasil{suffix}"
        )
        heuristic_desc = f"Ingin tahu cara paling efektif dalam {clean}? Simak ringkasan poin-poin penting yang langsung bisa Anda terapkan hari ini.\n\nDalam video ini kita membahas tuntas materi {clean} dengan fokus pada hal-hal yang sering diabaikan namun berdampak besar.\n\n{ts_block}\n\n📌 Subscribe untuk tips dan strategi mendalam berikutnya!\n\n{' '.join(hashtags_pre)}"
        blindspot_audit = TopicNormalizer.audit_content_blindspots(
            title=heuristic_title,
            description=heuristic_desc,
            tags=v_tags_str,
            context_notes=content_notes,
            target_format=target_format,
        )

        return {
            "detected_content_summary": f"Video edukatif dan aplikatif mengenai {clean} yang fokus pada solusi nyata dan hasil terukur.",
            "tag_audit": tag_audit,
            "blindspot_audit": blindspot_audit,
            "outranking_title": heuristic_title,
            "title_formula": "[Janji Hasil] + [Topik Utama] + [Validasi/Bukti]",
            "psychological_angles": {
                "curiosity_gap": {
                    "label": "🔍 Misteri & Curiosity Gap",
                    "title": f"Banyak Orang Gagal di {clean} Karena 1 Kesalahan Sepele Ini{suffix}",
                    "rationale": "Menimbulkan rasa takut melakukan kesalahan serupa.",
                },
                "high_stakes": {
                    "label": "⚡ Kronologi & High-Stakes Storytelling",
                    "title": f"Eksperimen Nyata {clean}: Dari Titik Terendah Menuju Hasil Maksimal{suffix}",
                    "rationale": "Alur cerita transformasi yang memikat retensi tinggi.",
                },
                "contrarian": {
                    "label": "🤯 Mitos vs Fakta / Kontrarian",
                    "title": f"Jangan Asal {clean} Sebelum Tahu Fakta Krusial Ini{suffix}",
                    "rationale": "Memicu pattern interrupt saat penonton scrolling beranda.",
                },
                "deep_dive": {
                    "label": "📚 Deep Dive / Analisis Tuntas",
                    "title": f"Masterclass {clean}: Panduan Terlengkap untuk Hasil Konsisten{suffix}",
                    "rationale": "Menjadi rujukan definitif bagi penonton dengan intensi belajar tinggi.",
                },
            },
            "two_line_hook": f"Ingin tahu cara paling efektif dalam {clean}? Simak ringkasan poin-poin penting yang langsung bisa Anda terapkan hari ini.",
            "full_description": heuristic_desc,
            "video_tags": v_tags_str,
            "launch_checklist": [
                "Upload video dalam status 'Unlisted' (Tidak Publik) selama 2-4 jam agar video selesai diproses dalam resolusi maksimal (1080p/4K) dan subtitle otomatis terbuat sebelum dipublikasikan.",
                "Pastikan 5 detik pertama langsung menjawab ekspektasi judul tanpa intro animasi bertele-tele.",
                "Buat thumbnail dengan teks maksimal 3-4 kata yang memicu kontras emosional dan tidak mengulang persis kata-kata di judul.",
            ],
        }

    @staticmethod
    def generate_video_schema_jsonld(
        title: str,
        description: str,
        video_id: str = "VIDEO_ID",
        thumbnail_url: str = "",
        duration: str = "10:00",
        upload_date: str = "",
        timestamps_text: str = "",
    ) -> str:
        """Generate Google-compliant Schema.org VideoObject JSON-LD with Key Moments Clips."""
        # Convert duration to ISO 8601 (e.g. PT12M30S)
        parts = [int(p) for p in duration.split(":") if p.isdigit()]
        if len(parts) == 2:
            iso_dur = f"PT{parts[0]}M{parts[1]}S"
        elif len(parts) == 3:
            iso_dur = f"PT{parts[0]}H{parts[1]}M{parts[2]}S"
        else:
            iso_dur = "PT10M0S"

        pattern = r"(?:\[)?(\d{1,2}:\d{2}(?::\d{2})?)(?:\])?\s*[-–:]?\s*(.+)"
        clips_raw = []
        if timestamps_text:
            for line in timestamps_text.splitlines():
                m = re.search(pattern, line.strip())
                if m:
                    time_str = m.group(1)
                    label = m.group(2).strip()
                    time_parts = [int(p) for p in time_str.split(":") if p.isdigit()]
                    if len(time_parts) == 2:
                        sec = time_parts[0] * 60 + time_parts[1]
                    elif len(time_parts) == 3:
                        sec = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                    else:
                        sec = 0
                    clips_raw.append({"sec": sec, "label": label})

        clips = []
        for i, c in enumerate(clips_raw):
            s = c["sec"]
            e = clips_raw[i + 1]["sec"] if i + 1 < len(clips_raw) else s + 180
            clips.append(
                {
                    "@type": "Clip",
                    "name": c["label"],
                    "startOffset": s,
                    "endOffset": e,
                    "url": f"https://www.youtube.com/watch?v={video_id}&t={s}s",
                }
            )

        schema_obj: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": title,
            "description": description[:500] if description else title,
            "thumbnailUrl": [
                thumbnail_url or f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            ],
            "uploadDate": upload_date or datetime.now().astimezone().isoformat(),
            "duration": iso_dur,
            "embedUrl": f"https://www.youtube.com/embed/{video_id}",
            "contentUrl": f"https://www.youtube.com/watch?v={video_id}",
        }
        if clips:
            schema_obj["hasPart"] = clips

        return json.dumps(schema_obj, indent=2, ensure_ascii=False)
