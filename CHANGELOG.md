# CHANGELOG

Semua pembaruan, perbaikan bug, dan rilis versi sistem **YouTube Search & Competitor Intelligence** (`youtube-analyzer`) didokumentasikan di sini mengikuti standar [Keep a Changelog](https://keepachangelog.com/id/1.0.0/).

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
