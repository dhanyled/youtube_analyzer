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
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-1.5-flash",
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
2. Buat judul tandingan utama (Outranking Title) yang jauh lebih memikat, berbobot, dan mengalahkan video #1 tanpa menggunakan clickbait murahan.
3. Buat 4 Alternatif Variasi Judul berdasarkan 4 Sudut Pandang Psikologi Penonton:
   - Curiosity Gap (Rasa penasaran akut, informasi tersembunyi/misteri)
   - High-Stakes Storytelling (Intensitas tinggi, kronologi detik-demi-detik, urgensi/risiko nyata)
   - Contrarian / Mitos vs Fakta (Mendobrak kekeliruan umum penonton)
   - Deep Dive / Analisis Tuntas (Pembahasan paling komprehensif, terstruktur & kredibel)
4. Buat 2 kalimat pembuka deskripsi (hook) yang memancing klik, 5 timestamps relevan, dan 4 hashtags SEO.

PANDUAN GAYA BAHASA (WAJIB DIPATUHI):
- Gunakan Bahasa Indonesia yang 100% natural, luwes, dan humanis.
- JANGAN gunakan kata-kata template klise seperti: "Semua yang wajib kamu tahu...", "Fakta gila...", "Jangan lakukan ini...", "Panduan pemula modal kecil".
- Judul HARUS secara spesifik dan cerdas mengangkat konteks nyata yang dibahas kompetitor (misal: jika bencana alam, sebut detail peristiwa/kronologinya; jika kisah survival/pendaki, sebut misteri jalur/evakuasi nyatanya; jika tutorial/bisnis, sebut studi kasus spesifiknya).

KEMBALIKAN HANYA FORMAT JSON MURNI TANPA PENJELASAN LAIN dengan struktur persis seperti ini:
{{
  "competitor_analysis": {{
    "weakness": "Celah spesifik kemasan judul kompetitor #1",
    "counter_strategy": "Bagaimana judul & sudut pandang kita memposisikan diri lebih unggul"
  }},
  "outranking_title": "Judul tandingan utama yang mengalahkan video #1",
  "title_formula": "Rumus psikologi judul ini, misal: [Emosi Penasaran] + [Topik Spesifik] + [Dampak Nyata]",
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
  "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"]
}}"""

    @classmethod
    def call_gemini(
        cls,
        prompt: str,
        api_key: str,
        model: str = "gemini-1.5-flash",
    ) -> dict[str, Any]:
        """Call Google Gemini generateContent REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "response_mime_type": "application/json",
            },
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = _clean_json_response(raw_text)
            return json.loads(cleaned)

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
