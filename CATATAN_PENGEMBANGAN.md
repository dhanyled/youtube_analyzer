# 🛡️ Catatan Pengembangan & Arsitektur (Technical Post-Mortem & SOP)
**YouTube SERP & Trend Intelligence Platform**
*Pembaruan Terakhir: 5 November 2026*

---

## 1. ⚠️ Insiden Layar Putih (White Screen) Streamlit Cloud

### 1.1. Gejala Masalah
Setelah perubahan CSS/JS untuk menghilangkan elemen watermark atau avatar profil pada aplikasi di Streamlit Cloud (`*.streamlit.app`), aplikasi sempat muncul sesaat lalu layar berubah menjadi putih total (*blank white screen*), padahal di server log tidak ada exception Python (`200 OK`).

### 1.2. Root Cause Analysis (RCA)
1. **DOM Tree Streamlit Cloud**:
   Struktur DOM pada Streamlit Community Cloud (`window.parent.document`) berbeda dari Streamlit lokal:
   ```html
   <div class="_streamlitAppContainer_1j65n_1">
     <div class="_stateContainer_1j65n_26">
       <!-- 1. IFRAME APLIKASI (JANTUNG APLIKASI) -->
       <iframe class="_iframe_1j65n_26" src="..."></iframe>
       <!-- 2. STREAMLIT BADGE WATERMARK -->
       <a class="_container_gzau3_1 _viewerBadge_1j65n_23">...</a>
       <!-- 3. PROFILE CONTAINER / AVATAR -->
       <div class="_profileContainer_gzau3_53">
         <button class="_profileButton_gzau3_60">
           <img src="...avatar..." />
         </button>
       </div>
     </div>
   </div>
   ```
2. **Penyebab Kegagalan**:
   Selektor `[class*="_stateContainer_"]` merupakan pembungkus (*parent wrapper*) yang menaungi `<iframe class="_iframe_1j65n_26">`. 
   Ketika aturan CSS atau skrip JavaScript menyembunyikan kelas `[class*="_stateContainer_"]` menggunakan `display: none !important`, maka seluruh elemen iframe aplikasi ikut tersembunyi, menghasilkan layar putih kosong.

### 1.3. Solusi Permanen yang Diterapkan
1. **Aturan CSS/JS Wajib Proteksi Iframe**:
   ```css
   /* KUNCI MATI: Iframe dan StateContainer WAJIB dipaksa tampil dan full height */
   [class*="_stateContainer_"], [class*="_iframe_"] {
       display: block !important;
       visibility: visible !important;
       opacity: 1 !important;
       width: 100% !important;
       height: 100% !important;
   }
   
   /* HANYA sembunyikan badge dan profile container spesifik */
   [class*="_profileContainer_"], [class*="_profileButton_"], [class*="_viewerBadge_"] {
       display: none !important;
       visibility: hidden !important;
       opacity: 0 !important;
       pointer-events: none !important;
   }
   ```
2. **JavaScript Guard**:
   Pada `mutationObserver` dan `setInterval`, pastikan pengecekan traversal `el.contains(iframe)` atau `el.tagName === 'IFRAME'`. Jika elemen adalah atau berisi `iframe`, jangan pernah melakukan `style.display = 'none'`.

---

## 2. 📋 SOP Pengujian Frontend Sebelum Rilis

1. **Jalankan Verifikasi Sintaks & Unit Test**:
   ```bash
   uv run ruff check .
   uv run pytest -v
   ```
2. **Verifikasi Tampilan Live di Browser**:
   Gunakan browser devtools untuk memvalidasi:
   - Bounding box iframe aplikasi (misal `iframeWidth > 1000`, `iframeHeight > 500`).
   - Tidak ada elemen overlay full-screen transparan yang memblokir interaksi klik.
   - Text header dashboard (`YouTube Intelligence & Trend Studio`) benar-benar ter-render di dalam canvas DOM.
   - Profile container dan badge berhasil terisolasi tanpa mempengaruhi canvas utama.

---

## 3. 🏷️ Kebijakan Naming & Terminologi Independen

1. **Prinsip Netral & Universal**:
   - Hindari ketergantungan pada nama brand tunggal pihak ketiga (seperti "Google Flow" atau "Veo 3.1") pada teks UI dashboard.
   - Gunakan terminologi universal:
     - **"Studio Storyboard Video AI"** (menggantikan Google Flow Studio).
     - **"Generator Video AI modern (Kling, Runway, Luma, Sora, CapCut AI)"** (menggantikan Google Flow / Veo).
     - **"Batch Prompts TXT"** & **"Manifest JSON Timeline Editor (CapCut/Premiere)"** untuk format ekspor.
2. **White-label Protection**:
   - Jangan memunculkan status internal engine teknis (misal SQLite, Python version, Antigravity MCP) di sidebar publik pengguna.
   - Jaga agar sidebar bersih dan fokus pada parameter input riset konten.

---

## 4. 📊 Penanganan Data Pandas & Fallback Streamlit

1. **Pencegahan `KeyError` pada Tabel DataFrame**:
   Data query dari Google Trends / Hasdata dapat berupa list kosong atau memiliki kunci bervariasi jika data wilayah tertentu minim pencarian.
   - Gunakan fungsi pembantu terpusat `_render_query_table(data_list, label)` yang menjamin fallback kolom:
     `["Rank", "Query", "Popularitas (0-100)", "Lonjakan Minat"]`.
   - Batasi data hingga maksimal 50 query sesuai kuota representasi SERP terlengkap.


---

## 5. 🚀 Arsitektur Full Interactive Dashboard di Vercel Serverless (`v2.0.0`)

### 5.1. Latar Belakang & Solusi
- **Masalah**: Vercel tidak mendukung proses WebSocket persisten bawaan Streamlit (`dashboard.py`), sehingga URL `https://youtubeanalyzer-sand.vercel.app/` sebelumnya hanya menampilkan kartu status API kecil (`v1.1.0`).
- **Solusi Permanen (`v2.0.0` - Commit `0001f26`)**:
  Membangun **Full Interactive Executive Dashboard UI** (`api/dashboard_ui.html`) yang dilayani langsung pada rute utama `GET /` oleh FastAPI (`api/index.py`) dan terhubung penuh ke engine `src/youtube_analyzer/`.

### 5.2. Daftar Endpoint Dashboard & WebMCP di Vercel (`api/index.py`)
1. `GET /`: Merender UI Dashboard Interaktif lengkap (Sidebar Riwayat & Pengaturan AI + Traffic Light Verdict + 4 Kartu Skor + 10 Tab Analisis).
2. `POST /api/dashboard/analyze`: Menjalankan live scraping 10 kompetitor YouTube, kalkulasi Opportunity Score, RPM Niche, AI Ratio, Outranking Title & 4 Psychological Angles, Spy Competitor Tags, Content Gaps, Outlier Multiplier, Faceless Viability, Shorts Clipping, Storyboard AI, dan Cross-Surface Intent Matrix.
3. `POST /api/dashboard/audit-video`: Mengaudit video YouTube Publik/Unlisted via URL/ID (ekstraksi metadata, transkrip `youtube-transcript-api`, skor audit, dan paket revamp SEO).
4. `POST /api/dashboard/pre-upload`: Merancang paket metadata peluncuran SEO dari poin-poin naskah draft sebelum di-upload.
5. `GET /api/dashboard/trending`: Live explorer YouTube Trending Feed berdasarkan perangkat (`desktop`/`mobile`), negara (`gl`), bahasa (`hl`), dan kategori.
6. `GET /api/dashboard/trends`: Komparasi tren Google Web vs YouTube Search (`gprop=youtube`) beserta feed real-time Google Daily Trends RSS.
7. `POST /api/shotlist`, `POST /api/admin/verify`, `GET /api/webmcp/tools`, `POST /api/webmcp/call`: Jembatan Serverless & WebMCP untuk Google Flow Dracin Studio dan Chrome DevTools AI Agent.

### 5.3. Konfigurasi Bundling Vercel (`vercel.json` & `api/requirements.txt`)
- `vercel.json` menyertakan `"includeFiles": "{src/**,api/*.html}"` agar seluruh modul `src/youtube_analyzer` dan template `api/dashboard_ui.html` ikut ter-bundle ke dalam fungsi serverless Vercel.
- `api/requirements.txt` dijaga tetap ramping (< 45MB, tanpa `streamlit`/`pyarrow`) agar selalu lolos batas 250MB AWS Lambda/Vercel dan memiliki *cold-start* instan (< 1 detik).

---

## 6. 🌐 Mesin Google People Also Ask (PAA) & Google Key Moments Timestamps (`v2.1.0`)

### 6.1. Latar Belakang & Solusi
- **Masalah**: Deskripsi video YouTube sering kehilangan potensi ribuan penayangan gratis dari Google Web Search karena stempel waktu (timestamps) tidak selaras dengan query pencarian interogatif Google.
- **Solusi (`GoogleSearchConnector` & `get_people_also_ask`)**:
  - Mengekstrak pertanyaan PAA riil langsung dari Google SERP menggunakan query prefix interogatif bahasa Indonesia (misal: *bagaimana cara*, *berapa biaya*, *apa penyebab*, *kenapa*, *apakah*).
  - Menyuntikkan pertanyaan PAA terpilih sebagai babak bertanda `[Google Key Moment]` pada stempel waktu video Landscape 16:9 di Tab 7 dan Tab 9 (*Cross-Surface Keywords*).

---

## 7. 💬 Penambangan Komentar Kompetitor & InnerTube Fallback (`v2.1.0`)

### 7.1. Latar Belakang & Arsitektur Dual Engine
- **Masalah**: Kreator sering kali hanya menyalin topik kompetitor tanpa mengetahui kendala atau pertanyaan penonton yang belum terjawab di video kompetitor. Selain itu, di serverless cloud Vercel, kuota YouTube Data API v3 dapat habis atau API Key tidak terpasang.
- **Solusi (`mine_competitor_comments`)**:
  1. *Mesin Utama (YouTube Data API v3)*: Membaca `commentThreads.list` dengan metrik likes dan balasan.
  2. *Mesin Fallback Mandiri (Unauthenticated InnerTube)*: Menembak endpoint publik YouTube `/youtubei/v1/next` dengan client `WEB` dan context publik untuk mengambil token kelanjutan komentar (`reloadContinuationData`) serta mem-parsing mutasi `commentEntityPayload`. **100% Berfungsi tanpa API Key!**
  3. Menyaring komentar menggunakan NLP heuristik untuk mengekstrak pertanyaan penonton, keluhan (*friction*), dan langsung merumuskan *Topic Gap Opportunities* di Tab 5 (*Content Gap*).

---

## 8. 🛡️ Arsitektur 5-Pillar Blindspot Audit Gate & Tag Relevancy Checker (`v2.2.0`)

### 8.1. Deteksi Blindspot Semantik & Metadata
- **Masalah**: Penggunaan tag generik spam seperti `fyp`, `viral`, `trending`, atau kata pemicu clickbait seperti `gratis` pada video berbayar memicu penalti retensi penonton dan melanggar kebijakan YouTube Spam & Metadata Deception.
- **Solusi (`TopicNormalizer.audit_tags_detailed` & `audit_content_blindspots`)**:
  1. **5 Pilar Audit Pengemasan Video**:
     - *Pillar 1: Judul (Title)* — Validasi panjang 45–65 karakter, deteksi risiko pemotongan layar mobile (>70 karakter).
     - *Pillar 2: Google Key Moments Timestamps* — Validasi wajib mulai di `00:00`, minimal 3 babak, dan memetakan kata kunci interogatif PAA.
     - *Pillar 3: Relevansi Tag & Anti-Spam* — Menyaring tag spam generik dan kata kunci bersyarat.
     - *Pillar 4: First-Fold Description Hook* — Memastikan 2 baris awal deskripsi memuat kata kunci utama sebelum tombol `...more`.
     - *Pillar 5: Kesesuaian Format & Pacing* — Memvalidasi pacing Shorts (<60s) vs Longform (>8 min untuk monetisasi mid-roll ad RPM).
  2. **Aturan Relevansi Tag "Gratis"**:
     - Jika naskah/topik video secara eksplisit membahas materi atau fitur gratis $\rightarrow$ status **`PASS (Relevan)`**.
     - Jika naskah tidak menawarkan hal gratis $\rightarrow$ status **`FAIL (Clickbait Unsupported)`** untuk melindungi channel dari bounce rate tinggi.
  3. **Penguji Tag Real-time di UI**:
     - Ditambahkan widget interaktif di Tab *Studio Optimasi Video (Audit & Revamp)* sehingga pengguna dapat mengetikkan kata kunci apa pun untuk diuji seketika terhadap naskah.

---

## 9. 🔄 Arsitektur Instant Multi-Channel Switcher & OAuth Brand Account Manager (`v2.2.0`)

### 9.1. Latar Belakang & Solusi
- **Masalah**: Pengguna memiliki banyak channel (baik Brand Accounts di bawah 1 Gmail yang sama maupun akun Gmail terpisah) dan ingin memantau performa, membedah rasio format video, serta menghitung target monetisasi tanpa harus login/logout Google berulang kali.
- **Solusi Dua Jalur**:
  1. **Instant Switcher (Dashboard UI)**:
     - Endpoint `GET /api/dashboard/my-channel?identifier=@handle` memungkinkan pergantian channel secara instan.
     - Mengambil profil, subscribers, total views, dan 20 video terbaru menggunakan YouTube Data API & Scraper publik.
     - Menyimpan daftar channel yang sering dibuka ke dalam `localStorage` browser (*Quick Switch Pills*).
     - Memperbarui matriks perbandingan multi-kompetitor dan roadmap monetisasi secara otomatis.
  2. **OAuth Brand Account Switcher (Lokal)**:
     - Pada `YouTubeStudioConnector.authenticate_interactive`, parameter disetel menjadi `prompt="select_account consent"`.
     - Google OAuth akan selalu memunculkan layar dialog pemilihan akun dan daftar *Brand Accounts*, memungkinkan otorisasi resmi berpindah ke sub-channel mana pun.


---

## 3. AUDIT BLINDSPOT GITHUB & PENGUATAN EKOSISTEM (v2.2.0 Hardening)

### A. Temuan Blindspot Repositori GitHub (dhanyled/youtube_analyzer)
1. **Nol Git Release Tag di GitHub Remote (SELESAI DIPERBAIKI):**
   - *Masalah:* Meskipun codebase telah mencapai v2.0.0 dan v2.2.0, perintah git tag -l kosong. Repositori GitHub tidak memiliki release tags resmi sehingga tool eksternal atau developer tidak bisa menarik tarball versi stabil.
   - *Solusi:* Dibuat dan di-push tag resmi v2.0.0 dan v2.2.0 ke remote origin.
2. **Metadata Package Placeholder di pyproject.toml (SELESAI DIPERBAIKI):**
   - *Masalah:* description = 'Add your description here' masih tertinggal sejak inisialisasi repositori.
   - *Solusi:* Diperbarui dengan deskripsi produksi lengkap serta tautan [project.urls] (Homepage Vercel dan GitHub Repository) dan keywords.
3. **Absennya Dependabot Security Updates (SELESAI DIPERBAIKI):**
   - *Masalah:* Belum ada .github/dependabot.yml, sehingga scanning dependensi otomatis dihentikan oleh GitHub.
   - *Solusi:* Dibuat konfigurasi .github/dependabot.yml untuk ekosistem github-actions dan pip. Saat diaktifkan, Dependabot langsung mendeteksi 6 pembaruan dependensi (PR #4 s.d. PR #9).
4. **Pytest Asyncio Deprecation Warning (SELESAI DIPERBAIKI):**
   - *Masalah:* Muncul PytestDeprecationWarning: The configuration option 'asyncio_default_fixture_loop_scope' is unset pada setiap eksekusi unit test.
   - *Solusi:* Ditambahkan asyncio_default_fixture_loop_scope = 'function' pada [tool.pytest.ini_options] di pyproject.toml.
5. **Celah Kebocoran Secret di .gitignore (SELESAI DIPERBAIKI):**
   - *Masalah:* File .gitignore hanya mencantumkan string singular client_secret.json. Padahal Google Cloud Console secara default menamai file kredensial OAuth sebagai client_secrets.json atau client_secret_<client_id>.json.
   - *Solusi:* Diganti dengan pola glob client_secret*.json, client_secrets*.json, credentials*.json, token*.json, *.token.json.

### B. Temuan Blindspot Komunitas Open Source YouTube di GitHub
1. **YouTube BotGuard / Proof-of-Origin (PO) Token Rollout (2024-2025):**
   - *Fenomena Komunitas (yt-dlp, pytube, youtube-transcript-api):* YouTube memperketat request unauthenticated dari IP datacenter (AWS, Vercel, GCP) dengan challenge 'Sign in to confirm you are not a bot'.
   - *Proteksi di Proyek Ini:* Arsitektur dual-tier (YouTube Studio Data API v3 resmi via OAuth 2.0 untuk user autentikasi + InnerTube fallback unauthenticated untuk scraping publik). Fallback unauthenticated dilengkapi penanganan try-except berlapis dan fallback data aman tanpa memutus eksekusi dashboard (nol 500 error).
2. **Caveat Kompatibilitas SQLAlchemy vs SQLModel (Dependabot PR #9):**
   - *Temuan Kritis:* Dependabot mengusulkan bump sqlalchemy ke >=2.1.6. Namun sqlmodel==0.0.22 memiliki constraint ketat sqlalchemy >= 2.0.14, < 2.1.0. Mem-merge PR #9 tanpa meng-upgrade SQLModel akan memicu dependency resolution conflict di uv sync. PR #9 wajib ditahan hingga SQLModel merilis kompatibilitas SQLAlchemy 2.1+.

---

## 10. ⚡ Intelligence Algoritmik, Dual-Tier Kredensial, dan Kebijakan Zero-Third-Party Brand Guardrail (v2.3.0)

### 10.1. Arsitektur Resolusi Kredensial Dual-Tier (resolve_effective_keys)
- **Masalah**: Pengguna ingin fleksibilitas penggunaan API Key: jika sudah tersimpan di .env lokal atau serverless environment variables, sistem harus langsung menggunakannya secara otomatis tanpa memaksa pengguna menginput manual. Namun jika belum ada di .env atau pengguna ingin menguji key alternatif, dashboard harus menyediakan modal pengaturan manual.
- **Solusi**:
  1. Dibuat fungsi helper resolve_effective_keys(override_key, env_var_name) di api/index.py.
  2. Alur resolusi bertingkat: Override Key dari UI Modal -> Key dari os.environ / .env -> Fallback None.
  3. UI menyediakan tombol 'Pengaturan AI & API Key' yang menyimpan input ke localStorage browser dan mengirimkannya via payload API.
  4. Endpoint visual GET /api/credentials/status melaporkan status ketersediaan key tanpa membocorkan isi key rahasia ke publik (hanya mask 4 karakter awal).

### 10.2. Algoritma Outlier Multiplier & Niche Scorecard
- **Formula Outlier**: Multiplier = Views Video / Median Views Kompetitor Halaman 1.
  - Multiplier >= 5.0x -> VIRAL BREAKOUT
  - Multiplier >= 2.5x -> STRONG OUTLIER
  - Multiplier >= 1.3x -> ABOVE AVERAGE
- **Pilar Validasi Niche**:
  1. *Channel Cluster*: Minimal 3 channel unik di SERP untuk memastikan niche tidak dimonopoli 1 kreator.
  2. *Proof of Views*: Minimal ada 1 video berpenayangan >= 20.000 views sebagai bukti audiens aktif.
  3. *Search Demand*: Autocomplete YouTube Suggest aktif >= 3 variasi kueri.

### 10.3. Kebijakan Mutlak White-Label & Automated Brand Guardrail
- **Larangan Pihak Ketiga**:
  - Dilarang keras menampilkan nama platform komersial pihak ketiga mana pun pada UI, respons JSON, maupun komentar kode.
  - Semua fitur menggunakan penamaan proprietary berbasis fungsi: Algorithmic Niche Validation Scorecard, Viral Breakout Mode, Off-Platform Funnel Intelligence, Studio Thumbnail Lab.
- **Automated Guardrail (tests/verify_suite.py)**:
  - Seluruh file berekstensi .html, .js, .css, .py, .md, .toml, .json dipindai secara rekursif dalam automated test suite.
  - Jika kata terlarang terdeteksi, build otomatis dihentikan dengan status exit code 1.
