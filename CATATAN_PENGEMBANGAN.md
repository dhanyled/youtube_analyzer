# 🛡️ Catatan Pengembangan & Arsitektur (Technical Post-Mortem & SOP)
**YouTube SERP & Trend Intelligence Platform**
*Pembaruan Terakhir: September 2026*

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
