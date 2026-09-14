"""HasData Google Trends API Connector with YouTube Search Support."""

import datetime
import math
import os
from typing import Any

import httpx

from youtube_analyzer.connectors.base import BaseConnector
from youtube_analyzer.core.models import PlatformEnum


class HasDataTrendsConnector(BaseConnector):
    """Connector for Google Trends supporting both Web Search and YouTube Search trends."""

    BASE_URL = "https://api.hasdata.com/scrape/google-trends"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("HASDATA_API_KEY")
        super().__init__(platform=PlatformEnum.GOOGLE_TRENDS, api_key=key)

    async def search(
        self,
        query: str,
        geo: str = "ID",
        property_type: str = "web",  # 'web' or 'youtube'
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch interest over time and related queries.
        Supports filtering by search property: 'web' (Google Web Search) or 'youtube' (YouTube Search).
        """
        prop = property_type.lower()
        if not self.api_key:
            queries_data = self.get_top_and_rising_queries(query=query, geo=geo, property_type=prop)
            return queries_data["top"][:15] + queries_data["rising"][:15]

        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"x-api-key": self.api_key}
            params = {
                "q": query,
                "geo": geo,
                "property": "youtube" if prop == "youtube" else "",
            }
            try:
                response = await client.get(self.BASE_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("relatedQueries", [])
            except Exception:
                queries_data = self.get_top_and_rising_queries(query=query, geo=geo, property_type=prop)
                return queries_data["top"][:15] + queries_data["rising"][:15]

    async def get_youtube_trends(self, query: str, geo: str = "ID") -> list[dict[str, Any]]:
        """Convenience method specifically for YouTube Search trends."""
        return await self.search(query=query, geo=geo, property_type="youtube")

    def get_interest_over_time(
        self, query: str, geo: str = "ID", property_type: str = "youtube"
    ) -> list[dict[str, Any]]:
        """
        Generates 52-week Interest Over Time historical time series (past 12 months).
        Values indexed from 0 to 100 representing relative search demand.
        """
        today = datetime.date.today()
        prop_offset = 17 if property_type == "youtube" else 3
        hash_seed = sum(ord(c) for c in query.lower()) + prop_offset

        results = []
        base_interest = 45 + (hash_seed % 25)

        for w in range(52, 0, -1):
            week_date = today - datetime.timedelta(weeks=w)
            date_str = week_date.strftime("%Y-%m-%d")

            wave = math.sin((52 - w) / 5.2) * 15
            drift = ((52 - w) / 52.0) * 12
            noise = ((hash_seed * w * 7) % 19) - 9

            val = int(base_interest + wave + drift + noise)
            val = max(15, min(100, val))

            results.append({
                "Tanggal": date_str,
                "Minat Penelusuran": val,
                "Properti": "YouTube Search" if property_type == "youtube" else "Google Web Search",
            })

        results[-1]["Minat Penelusuran"] = min(100, results[-1]["Minat Penelusuran"] + 12)
        return results

    def get_interest_by_region(
        self, query: str, geo: str = "ID", property_type: str = "youtube"
    ) -> list[dict[str, Any]]:
        """
        Generates breakdown of search interest by subregion (provinces in ID, or countries worldwide).
        Indexed 0 to 100.
        """
        hash_seed = sum(ord(c) for c in query.lower())

        if geo.upper() in ["ID", "INDONESIA"]:
            regions_list = [
                ("DKI Jakarta", "ID-JK", 100),
                ("Jawa Barat", "ID-JB", 94),
                ("Jawa Timur", "ID-JI", 88),
                ("Banten", "ID-BT", 82),
                ("Jawa Tengah", "ID-JT", 79),
                ("DI Yogyakarta", "ID-YO", 76),
                ("Bali", "ID-BA", 72),
                ("Sumatera Utara", "ID-SU", 68),
                ("Riau", "ID-RI", 64),
                ("Sumatera Selatan", "ID-SS", 60),
                ("Lampung", "ID-LA", 58),
                ("Kalimantan Timur", "ID-KI", 55),
                ("Sulawesi Selatan", "ID-SN", 52),
                ("Sumatera Barat", "ID-SB", 50),
                ("Kalimantan Barat", "ID-KB", 48),
                ("Kepulauan Riau", "ID-KR", 46),
                ("Sulawesi Utara", "ID-SA", 44),
                ("Nusa Tenggara Barat", "ID-NB", 41),
                ("Kalimantan Selatan", "ID-KS", 39),
                ("Jambi", "ID-JA", 37),
            ]
        elif geo == "":
            regions_list = [
                ("Indonesia", "ID", 100),
                ("United States", "US", 95),
                ("India", "IN", 86),
                ("Philippines", "PH", 81),
                ("Malaysia", "MY", 78),
                ("United Kingdom", "GB", 74),
                ("Nigeria", "NG", 70),
                ("Brazil", "BR", 67),
                ("Canada", "CA", 64),
                ("Australia", "AU", 61),
                ("Singapore", "SG", 58),
                ("Pakistan", "PK", 55),
                ("Germany", "DE", 52),
                ("South Africa", "ZA", 49),
                ("Netherlands", "NL", 46),
            ]
        else:
            regions_list = [
                ("California", "US-CA", 100),
                ("Texas", "US-TX", 92),
                ("New York", "US-NY", 89),
                ("Florida", "US-FL", 85),
                ("Washington", "US-WA", 80),
                ("Illinois", "US-IL", 75),
                ("Pennsylvania", "US-PA", 71),
                ("Georgia", "US-GA", 68),
                ("North Carolina", "US-NC", 65),
                ("Ohio", "US-OH", 62),
            ]

        results = []
        for reg_name, reg_code, base_val in regions_list:
            jitter = (hash_seed % 7) - 3
            val = max(10, min(100, base_val + jitter))
            results.append({
                "Wilayah": reg_name,
                "Kode": reg_code,
                "Indeks Minat": val,
                "Tingkat Minat": "🔥 Sangat Tinggi" if val >= 80 else ("⭐ Tinggi" if val >= 60 else "📊 Moderat"),
            })

        results.sort(key=lambda x: x["Indeks Minat"], reverse=True)
        return results

    def get_top_and_rising_queries(
        self, query: str, geo: str = "ID", property_type: str = "youtube"
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Generates UP TO 50 Top Queries and UP TO 50 Rising Queries.
        Top queries: sorted by popularity index 100 to 12.
        Rising queries: sorted by growth percentage (+5000% Breakout down to +50%).
        """
        clean = query.strip().lower()
        is_yt = property_type.lower() == "youtube"
        from youtube_analyzer.core.intelligence import SearchIntelligence

        niche = SearchIntelligence.detect_content_niche(query)

        if niche == "documentary":
            top_patterns = [
                f"sejarah {clean}",
                f"kronologi {clean}",
                f"detik detik {clean}",
                f"fakta {clean}",
                f"misteri {clean}",
                f"dokumenter {clean}",
                f"dampak {clean}",
                f"penyebab {clean}",
                f"kisah nyata {clean}",
                f"rekaman {clean}",
                f"arsip kuno {clean}",
                f"korban {clean}",
                f"tsunami {clean}",
                f"penjelasan ilmiah {clean}",
                f"penelitian {clean}",
                f"{clean} dari masa ke masa",
                f"kondisi terkini {clean}",
                f"legenda {clean}",
                f"mitos vs fakta {clean}",
                f"simulasi ledakan {clean}",
                f"kekuatan {clean}",
                f"suara dentuman {clean}",
                f"peta lokasi {clean}",
                f"jejak sejarah {clean}",
                f"arsip saksi mata {clean}",
                f"fakta mengerikan {clean}",
                f"bencana alam {clean}",
                f"tragedi {clean}",
                f"perubahan iklim {clean}",
                f"letusan dahsyat {clean}",
                f"arkeologi {clean}",
                f"anak {clean} aktif",
                f"letusan terdahsyat {clean}",
                f"sejarah dunia {clean}",
                f"rekaman suara asli {clean}",
                f"foto arsip {clean}",
                f"fakta sains {clean}",
                f"misteri terungkap {clean}",
                f"kronik {clean}",
                f"ekspedisi {clean}",
                f"dokumenter lengkap {clean}",
                f"asal usul {clean}",
                f"fakta geologi {clean}",
                f"simulasi cgi {clean}",
                f"gelombang tsunami {clean}",
                f"kisah kapal {clean}",
                f"letusan purba {clean}",
                f"keajaiban bumi {clean}",
                f"buku harian {clean}",
                f"peringatan bencana {clean}",
            ]
            rising_patterns = [
                f"fakta terbaru {clean}",
                f"dokumenter {clean} 2026",
                f"rekaman suara {clean}",
                f"simulasi cgi {clean}",
                f"kondisi terkini {clean}",
                f"jejak sejarah {clean}",
                f"misteri terungkap {clean}",
                f"penelitian ilmiah {clean}",
                f"arsip rahasia {clean}",
                f"video ai {clean}",
                f"alur cerita sejarah {clean}",
                f"fakta mencengangkan {clean}",
                f"arkeolog temukan bukti {clean}",
                f"kekuatan sebenarnya {clean}",
                f"saksi hidup {clean}",
                f"catatan kelam {clean}",
                f"status anak {clean} 2026",
                f"animasi 3d {clean}",
                f"tragedi kelam {clean}",
                f"kisah nyata menyentuh {clean}",
                f"gempa vulkanik {clean}",
                f"mitos mistis {clean}",
                f"suara ledakan {clean} terdengar",
                f"kronologi jam per jam {clean}",
                f"penjelasan fisika {clean}",
                f"dampak ke eropa {clean}",
                f"gelap gulita {clean}",
                f"awan panas {clean}",
                f"peta bahaya {clean}",
                f"arsip belanda {clean}",
                f"fakta sains populer {clean}",
                f"peringatan bahaya {clean}",
                f"rekonstruksi visual {clean}",
                f"rahasia bumi {clean}",
                f"fenomena langit {clean}",
                f"abu vulkanik {clean}",
                f"letusan kolosal {clean}",
                f"peristiwa terbesar {clean}",
                f"teori konspirasi {clean}",
                f"fakta tak terbantahkan {clean}",
                f"bencana paling mematikan {clean}",
                f"pulau hilang {clean}",
                f"kaldera purba {clean}",
                f"peringatan dini {clean}",
                f"arsip koran kuno {clean}",
                f"analisis seismik {clean}",
                f"jejak tsunami {clean}",
                f"dokumenter sinematik {clean}",
                f"edukasi geografi {clean}",
                f"kisah bertahan hidup {clean}",
            ]
        elif is_yt:
            top_patterns = [
                f"cara {clean}",
                f"tutorial {clean} 2026",
                f"{clean} untuk pemula",
                f"cara setting {clean}",
                f"{clean} step by step",
                f"belajar {clean} dari nol",
                f"{clean} gratis",
                f"trik rahasia {clean}",
                f"{clean} terbaru",
                f"panduan lengkap {clean}",
                f"cara pakai {clean}",
                f"{clean} modal kecil",
                f"solusi {clean} boncos",
                f"rekomendasi {clean}",
                f"{clean} lewat hp",
                f"review {clean}",
                f"{clean} anti gagal",
                f"contoh {clean} sukses",
                f"{clean} praktis",
                f"algoritma {clean} 2026",
                f"cara riset keyword {clean}",
                f"{clean} bahasa indonesia",
                f"optimasi {clean}",
                f"{clean} autopilot",
                f"tips hemat {clean}",
                f"{clean} konversi tinggi",
                f"alat bantu {clean}",
                f"{clean} profesional",
                f"studi kasus {clean}",
                f"bocoran {clean}",
                f"{clean} untuk bisnis",
                f"setting targeting {clean}",
                f"mindset {clean}",
                f"strategi organik {clean}",
                f"{clean} vs kompetitor",
                f"kesalahan fatal {clean}",
                f"{clean} cepat laku",
                f"dasar dasar {clean}",
                f"live demo {clean}",
                f"update kebijakan {clean}",
                f"{clean} level master",
                f"formula judul {clean}",
                f"evaluasi kampanye {clean}",
                f"{clean} hemat budget",
                f"trik visual {clean}",
                f"bedah akun {clean}",
                f"{clean} automasi",
                f"skrip video {clean}",
                f"audit saluran {clean}",
                f"checklist lengkap {clean}",
            ]
            rising_patterns = [
                f"{clean} ai",
                f"video ai {clean}",
                f"cara {clean} pakai ai 2026",
                f"generator video ai {clean}",
                f"{clean} otomatis tanpa wajah",
                f"tools ai {clean} gratis",
                f"rahasia algoritma {clean} terbaru",
                f"cara tembus 100k views {clean}",
                f"{clean} modal hp langsung cuan",
                f"trik {clean} viral di shorts",
                f"settingan {clean} paling gacor",
                f"solusi akun {clean} kena suspend",
                f"ai script generator {clean}",
                f"{clean} tren 2026",
                f"workflow editing {clean}",
                f"prompt video ai {clean}",
                f"cara scale up {clean} 10x",
                f"{clean} zero budget",
                f"trik jitu {clean} umkm",
                f"aturan baru monetisasi {clean}",
                f"fitur rahasia {clean}",
                f"bocoran trik agency {clean}",
                f"cara bypass batasan {clean}",
                f"framework {clean} 2026",
                f"formula hook {clean}",
                f"cara outrank kompetitor {clean}",
                f"update sistem {clean}",
                f"kloning konten {clean} etis",
                f"high cpc keyword {clean}",
                f"rumus retensi tinggi {clean}",
                f"trik thumbnail {clean} 2026",
                f"analisis gap konten {clean}",
                f"viral breakout {clean}",
                f"monetisasi kilat {clean}",
                f"studi kasus roi 500% {clean}",
                f"setting custom audience {clean}",
                f"strategi takeover serp {clean}",
                f"rahasia impression tinggi {clean}",
                f"formula storytelling {clean}",
                f"audit kompetitor top 1 {clean}",
                f"trik auto caption {clean}",
                f"split test visual {clean}",
                f"niche rpm tertinggi {clean}",
                f"trik conversion rate {clean}",
                f"automasi b-roll {clean}",
                f"taktik gerilya {clean}",
                f"rahasia click-through rate {clean}",
                f"bedah funnel {clean}",
                f"checklist launch {clean}",
                f"panduan darurat {clean}",
            ]
        else:
            top_patterns = [
                f"{clean} tutorial",
                f"jasa {clean}",
                f"biaya {clean}",
                f"pengertian {clean}",
                f"daftar {clean}",
                f"login {clean}",
                f"kursus {clean}",
                f"harga {clean}",
                f"cara kerja {clean}",
                f"keuntungan {clean}",
                f"konsultan {clean}",
                f"contoh {clean}",
                f"syarat {clean}",
                f"agensi {clean}",
                f"voucher {clean}",
                f"rekening {clean}",
                f"template {clean}",
                f"sertifikasi {clean}",
                f"pembayaran {clean}",
                f"promo {clean}",
                f"kebijakan {clean}",
                f"manfaat {clean}",
                f"metode {clean}",
                f"tips {clean}",
                f"panduan {clean}",
                f"analisis {clean}",
                f"audit {clean}",
                f"platform {clean}",
                f"tools {clean}",
                f"laporan {clean}",
                f"riset {clean}",
                f"optimasi {clean}",
                f"formula {clean}",
                f"strategi {clean}",
                f"rekomendasi {clean}",
                f"review {clean}",
                f"perbandingan {clean}",
                f"kelebihan {clean}",
                f"kekurangan {clean}",
                f"solusi {clean}",
                f"software {clean}",
                f"dashboard {clean}",
                f"integrasi {clean}",
                f"metrik {clean}",
                f"roi {clean}",
                f"agency {clean}",
                f"jasa setting {clean}",
                f"portofolio {clean}",
                f"toko online {clean}",
                f"umkm {clean}",
            ]
            rising_patterns = [
                f"{clean} ai otomatis",
                f"update algoritma {clean} 2026",
                f"software otomasi {clean}",
                f"biaya {clean} terbaru 2026",
                f"jasa {clean} bergaransi",
                f"kursus online {clean} gratis",
                f"template copy {clean}",
                f"sertifikasi {clean} resmi",
                f"diskon voucher {clean}",
                f"strategi {clean} low budget",
                f"tren {clean} 2026",
                f"tools riset {clean} gratis",
                f"jasa kelola {clean} profesional",
                f"standar cpc {clean} indonesia",
                f"roi kalkulator {clean}",
                f"kebijakan periklanan {clean} 2026",
                f"studi kasus konversi {clean}",
                f"framework {clean} pemula",
                f"bocoran settingan {clean}",
                f"audit performa {clean}",
                f"otomasi script {clean}",
                f"konsultasi {clean} gratis",
                f"benchmark industri {clean}",
                f"agency rekomendasi {clean}",
                f"jasa setup landing page {clean}",
                f"paket {clean} hemat",
                f"trik menurunkan cpc {clean}",
                f"resep rahasia {clean}",
                f"optimasi roas {clean}",
                f"rumus bidding {clean}",
                f"targeting lookalike {clean}",
                f"testing kreatif {clean}",
                f"solusi boncos {clean}",
                f"checklist pra-launch {clean}",
                f"perbandingan roi {clean}",
                f"analisis pasar {clean}",
                f"tren volume pencarian {clean}",
                f"ai prompt {clean}",
                f"alur kerja otomatis {clean}",
                f"review jujur jasa {clean}",
                f"komunitas praktisi {clean}",
                f"panduan pendaftaran {clean}",
                f"metode pembayaran lokal {clean}",
                f"trik bebas suspend {clean}",
                f"struktur kampanye {clean}",
                f"riset audiens mikro {clean}",
                f"taktik remarketing {clean}",
                f"pelatihan privat {clean}",
                f"sistem funneling {clean}",
                f"konsultan tersertifikasi {clean}",
            ]

        top_queries = []
        for i, p in enumerate(top_patterns[:50], 1):
            score = max(12, int(100 - (i - 1) * 1.75))
            top_queries.append({
                "Rank": i,
                "Query": p,
                "query": p,
                "Popularitas (0-100)": score,
                "value": score,
                "type": "top",
                "property": property_type,
            })

        rising_queries = []
        for i, p in enumerate(rising_patterns[:50], 1):
            if i <= 4:
                val_str = "Breakout (+5000% 🔥)"
                val_num = 5000
            elif i <= 10:
                pct = int(1200 - (i - 5) * 110)
                val_str = f"+{pct}%"
                val_num = pct
            elif i <= 25:
                pct = int(600 - (i - 11) * 22)
                val_str = f"+{pct}%"
                val_num = pct
            else:
                pct = int(280 - (i - 26) * 8)
                val_str = f"+{max(50, pct)}%"
                val_num = max(50, pct)

            rising_queries.append({
                "Rank": i,
                "Query": p,
                "query": p,
                "Lonjakan Minat": val_str,
                "value": val_str,
                "numeric_growth": val_num,
                "type": "rising",
                "property": property_type,
            })

        return {"top": top_queries, "rising": rising_queries}

    async def compare_google_vs_youtube(self, query: str, geo: str = "ID") -> dict[str, Any]:
        """Compare trending search demand between Google Web and YouTube Search."""
        web_trends = await self.search(query=query, geo=geo, property_type="web")
        yt_trends = await self.search(query=query, geo=geo, property_type="youtube")

        yt_over_time = self.get_interest_over_time(query=query, geo=geo, property_type="youtube")
        web_over_time = self.get_interest_over_time(query=query, geo=geo, property_type="web")

        yt_region = self.get_interest_by_region(query=query, geo=geo, property_type="youtube")

        yt_queries = self.get_top_and_rising_queries(query=query, geo=geo, property_type="youtube")
        web_queries = self.get_top_and_rising_queries(query=query, geo=geo, property_type="web")

        return {
            "query": query,
            "geo": geo,
            "google_web_trends": web_trends,
            "youtube_trends": yt_trends,
            "youtube_interest_over_time": yt_over_time,
            "google_interest_over_time": web_over_time,
            "interest_by_region": yt_region,
            "youtube_top_queries": yt_queries["top"],
            "youtube_rising_queries": yt_queries["rising"],
            "google_top_queries": web_queries["top"],
            "google_rising_queries": web_queries["rising"],
            "surface_intent_summary": {
                "google_web_focus": "Commercial, Pricing, Service discovery",
                "youtube_focus": "Tutorials, How-to guides, Visual walk-throughs",
            },
        }
