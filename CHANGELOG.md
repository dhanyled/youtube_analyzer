# CHANGELOG

Semua pembaruan, perbaikan bug, dan rilis versi sistem **YouTube Search & Competitor Intelligence** (`youtube-analyzer`) didokumentasikan di sini mengikuti standar [Keep a Changelog](https://keepachangelog.com/id/1.0.0/).

---

## [2.3.1] - 2026-11-06 (YouTube Shorts Metadata, Duration & Thumbnail Fix)

### 🐛 Perbaikan Bug & Peningkatan Metadata
* **YouTube Shorts Thumbnail Auto-Fallback (404 Error Fix):**
  * Memperbaiki masalah gambar thumbnail rusak pada video vertikal YouTube Shorts. Endpoint CDN `https://img.youtube.com/vi/<id>/maxresdefault.jpg` yang mengembalikan HTTP 404 pada Shorts kini secara otomatis menggunakan fallback ke `https://i.ytimg.com/vi/<id>/hqdefault.jpg` yang dijamin tersedia, serta memanfaatkan thumbnail beresolusi tinggi dari response oEmbed YouTube.
* **YouTube Shorts Duration & Format Recognition:**
  * Menambahkan parser fallback langsung ke endpoint `https://www.youtube.com/shorts/{video_id}` untuk mengekstrak durasi riil (`itemprop="duration"` format ISO-8601 seperti `PT0M44S`, `approxDurationMs`, atau `lengthSeconds`).
  * Video Shorts tanpa transkrip ucapan kini berhasil mendeteksi durasi secara presisi (contoh: `00:44`) dan tidak lagi menampilkan `N/A`.
  * Memperbaiki deteksi format otomatis dari `LANDSCAPE` menjadi `SHORTS` secara akurat pada audit video tunggal.
* **Update URL Produksi & Environment Sync:**
  * Memperbarui URL repositori dan homepage production di `pyproject.toml` ke deployment aktif `https://youtubeanalyzer-taupe.vercel.app/`.

---

## [2.3.0] - 2026-11-06 (Algorithmic Outlier & Zero-Blindspot White-Label Edition)

### 🚀 Fitur Baru & Peningkatan Utama
* **Algorithmic 3-Point Niche Validation Scorecard:**
  * Mengevaluasi topik riset terhadap 3 kriteria algoritma YouTube:
    1. *Channel Cluster*: Minimal 3-5 channel independen berhasil memonetisasi topik (bukan one-hit wonder).
    2. *Breakout Proof*: Terdapat bukti penayangan video mencapai views tinggi (>=20K views).
    3. *Search Demand*: Autocomplete YouTube Suggest aktif menghasilkan minimal 3 variasi kueri.
  * Menghasilkan status keputusan `🟢 VALIDATED NICHE` vs `🟡 CAUTION (NICHE SEMPIT)`.
* **Outlier Multiplier Engine & Viral Breakout Sorting:**
  * Menghitung rasio performa kompetitor: $\text{Views} / \text{Median Views}$ secara matematis.
  * Menampilkan badge visual cerdas: `🔥 VIRAL BREAKOUT (>=5.0x)`, `⭐ STRONG OUTLIER (>=2.5x)`, dan `📈 ABOVE AVERAGE (>=1.3x)`.
  * Tombol interaktif *Urutkan Outlier Tertinggi (Viral Breakout Mode)* untuk beralih antara ranking default SERP dan klip dengan multiplier ledakan views terbesar.
* **Studio Thumbnail Lab: AI Prompt Generator:**
  * Mereverse-engineer formula visual dari video peringkat #1 atau outlier tertinggi.
  * Menghasilkan prompt AI siap pakai untuk model **Google Flow (Nano Banana Pro)** dan **Midjourney v6.1**.
  * Menyertakan rekomendasi *3-Word Punchy Text Overlay* berdaya tarik tinggi.
* **Off-Platform Funnel Intelligence (Monetisasi Eksternal):**
  * Scanner regex cerdas yang memeriksa deskripsi video kompetitor untuk mendeteksi funnel pendapatan di luar AdSense:
    * Kursus Online / LMS (Teachable, Kajabi, Udemy).
    * Komunitas Berbayar / Membership (Skool, Discord VIP, Patreon, Substack).
    * Link Afiliasi (Shopee, Tokopedia, Amazon, Bitly, Linktree).
    * Sponsorship / Endorsement Resmi.
* **Dual-Tier Credential Resolution & UI Settings Modal:**
  * Tombol header `⚙️ Pengaturan AI & API Key` dan dialog modal interaktif.
  * Otomatis membaca kredensial `YOUTUBE_API_KEY` dan `GEMINI_API_KEY` dari environment variable `.env` (server/cloud) tanpa konfigurasi manual.
  * Menyediakan opsi input manual di UI yang tersimpan persisten di `localStorage` sebagai fallback / override.
  * Endpoint `GET /api/credentials/status` untuk verifikasi visual status koneksi API.
* **100% White-Label & Prohibited Brand Scrubbing:**
  * Pembersihan menyeluruh terhadap semua nama brand komersial pihak ketiga dari antarmuka pengguna (UI), API response, komentar kode, dan dokumentasi.
  * Peningkatan automated brand guardrail di `tests/verify_suite.py` yang mencakup file `.html`, `.js`, `.css`, `.py`, `.md`.

### 🐛 Perbaikan Bug & Blindspot
* **Real Data Integrity Fix (Durasi & Views N/A):**
  * Memperbaiki logika ekstraksi data video kompetitor dan audit video studio agar durasi dan views selalu memuat angka riil terformat (contoh: `12:45` dan `125.4K views`) dan tidak pernah lagi menghasilkan `N/A`.
* **Synchronization & Stability:**
  * Menjaga keselarasan 100% antara `src/youtube_analyzer` dan `api/youtube_analyzer`.
  * 68 unit test lolos secara lengkap (`uv run pytest tests/unit/`).

---

## [2.2.0] - 2026-11-06 (Dual-Engine Blindspot Edition)

### 🚀 Fitur Baru & Peningkatan Utama
* **5-Pillar Packaging & SEO Blindspot Audit Gate:**
  * Implementasi sistem deteksi blindspot otomatis pada naskah dan kemasan video sebelum dipublikasikan:
    1. *Pillar 1: Judul (Title) & Mobile Truncation Risk* — mendeteksi judul terpotong di layar mobile (>70 karakter) atau terlalu pendek (<30 karakter).
    2. *Pillar 2: Google Key Moments Timestamps* — memvalidasi stempel waktu wajib diawali `00:00`, minimal 3 babak, dan memetakan kata kunci interogatif PAA.
    3. *Pillar 3: Relevansi Tag & Anti-Spam Stuffing* — menyaring tag generik manipulatif dan memvalidasi kata kunci bersyarat.
    4. *Pillar 4: First-Fold Description Hook* — memastikan 2 baris awal deskripsi memuat kata kunci utama sebelum tombol `...more`.
    5. *Pillar 5: Kesesuaian Format & Pacing* — memeriksa pacing Shorts (<60s) vs Longform (>8 min untuk optimalisasi mid-roll ad RPM).
* **Tag Relevancy & Clickbait Diagnostics Gate (`TopicNormalizer.audit_tags_detailed`):**
  * Mendeteksi dan mengkategorikan tag ke dalam status `PASS` (Relevan Tematik / Relevan Bersyarat) dan `FAIL` (Unconditional Spam / Unsupported Clickbait / Duplikat / Overlength).
  * **Aturan Khusus Tag "Gratis" / "Free Download":**
    * Jika naskah/topik video secara eksplisit membahas materi atau fitur gratis -> status **`PASS (Relevan)`**.
    * Jika naskah tidak menawarkan hal gratis (misal materi berbayar/konsultasi) -> status **`FAIL (Clickbait Unsupported)`** untuk melindungi channel dari bounce rate tinggi dan sanksi algoritma.
* **Interactive Realtime Tag Tester di Dashboard UI:**
  * Pengguna dapat menguji kata kunci apa saja (misal: "gratis", "fyp", "modal 0") secara langsung terhadap topik dan ringkasan naskah mereka di Tab *Studio Optimasi Video (Audit & Revamp)*.
* **Ekspansi WebMCP Tools:**
  * Menambahkan 2 alat WebMCP baru ke dalam katalog resmi:
    * `audit_tag_relevance`: Audit kepatuhan tag terhadap naskah.
    * `audit_content_blindspots`: Audit 5-pilar pengemasan SEO video.
  * Total WebMCP tools aktif di serverless/cloud meningkat menjadi 8 tools terdaftar.
* **API Endpoints Baru:**
  * `POST /api/dashboard/audit-tags`: Endpoint audit tag mandiri dengan rincian per-tag dan rekomendasi.
  * `POST /api/dashboard/audit-blindspots`: Endpoint audit 5-pilar blindspot video.

### 🧪 Pengujian & Sinkronisasi
* Menambahkan test suite baru di `tests/unit/test_normalizer.py` dan `tests/unit/test_api_endpoints.py`.
* 67 unit test lolos 100% (`uv run pytest tests/`).
* Sinkronisasi mutlak antara `src/youtube_analyzer` dan `api/youtube_analyzer` terverifikasi via `test_package_sync.py`.

---

## [2.1.0] - 2026-11-06 (Google PAA & Comment Mining Edition)

### 🚀 Fitur Baru
* **Google People Also Ask (PAA) Engine:**
  * Penggalian pertanyaan interogatif langsung dari Google Search SERP untuk disuntikkan ke babak *Google Key Moments* video landscape.
  * Integrasi Tab 9 (*Cross-Surface Keywords*) dan Tab 7 (*Landscape 16:9*).
* **Dual-Engine Competitor Comment Mining (Zero API Key Fallback):**
  * Menambang pertanyaan audiens yang diabaikan kompetitor menggunakan YouTube Data API v3 dengan fallback unauthenticated InnerTube public watch/next endpoint.
  * Deteksi otomatis *Content Gap Goldmines* dari komentar penonton.

---

## [2.0.0] - 2026-11-05 (Serverless Cloud & Interactive UI Edition)

### 🚀 Fitur Baru
* Migrasi penuh ke arsitektur FastAPI Serverless Vercel dengan UI Tailwind CSS mandiri (10 Tab Interaktif).
* Integrasi resmi widget tren Google Trends interaktif (12 bulan time-series).
* Integrasi WebMCP Bridge (`window.WebMCP` dan `navigator.modelContext`) untuk orkestrasi AI Agent.
