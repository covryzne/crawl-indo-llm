# extractor/page_router.py

from urllib.parse import urlparse

# Daftar Hitam (Whitelist) Domain Berita Populer Indonesia
NEWS_DOMAINS = [
    "detik.com",
    "kompas.com",
    "tribunnews.com",
    "rri.co.id",
    "antaranews.com",
    "cnnindonesia.com",
    "cnbcindonesia.com",
    "tempo.co",
    "liputan6.com",
    "merdeka.com",
    "suara.com",
    "jawapos.com",
    "bisnis.com",
    "kumparan.com",
    "idntimes.com",
    "cnbc.com",
    "bloomberg.com",
]

NEWS_PATH_KEYWORDS = [
    "/berita/",
    "/news/",
    "/siaran-pers/",
    "/press-release/",
    "/artikel/",
]
DOC_PATH_KEYWORDS = [
    "/dokumen/",
    "/unduhan/",
    "/download/",
    "/jdih/",
    "/juknis/",
    "/peraturan/",
]
PUB_PATH_KEYWORDS = [
    "/publikasi/",
    "/laporan/",
    "/kajian/",
    "/jurnal/",
    "/buku/",
    "/infografis/",
]


def classify_page_type(url, title="", text="", attachments=None):
    """
    Classify a page into news/document/publication/government/other
    using a weighted scoring system for AITF 2026.
    """
    scores = {"news": 0, "document": 0, "publication": 0, "government": 0}

    parsed_url = urlparse((url or "").lower())
    domain = parsed_url.netloc.replace("www.", "")
    path = parsed_url.path
    title_lower = (title or "").lower()

    # ==========================================
    # 1. DOMAIN CHECK (Bobot Mutlak / Tertinggi)
    # ==========================================
    if any(nd in domain for nd in NEWS_DOMAINS):
        scores["news"] += 15  # Pasti berita kalau domainnya portal berita
    elif domain.endswith(".go.id") or domain == "go.id":
        scores["government"] += 2  # Base poin buat situs pemerintah

    # ==========================================
    # 2. URL PATH CHECK (Indikator Kuat)
    # ==========================================
    if any(np in path for np in NEWS_PATH_KEYWORDS):
        scores["news"] += 5
    if any(dp in path for dp in DOC_PATH_KEYWORDS):
        scores["document"] += 5
    if any(pp in path for pp in PUB_PATH_KEYWORDS):
        scores["publication"] += 5

    # ==========================================
    # 3. TITLE CHECK (Indikator Konteks)
    # ==========================================
    if any(kw in title_lower for kw in ["siaran pers", "berita", "press release"]):
        scores["news"] += 3

    if any(
        kw in title_lower
        for kw in [
            "peraturan",
            "keputusan",
            "undang-undang",
            "juknis",
            "pedoman",
            "surat edaran",
        ]
    ):
        scores["document"] += 4

    if any(
        kw in title_lower
        for kw in ["laporan", "buku", "jurnal", "kajian", "publikasi", "statistik"]
    ):
        scores["publication"] += 4

    # ==========================================
    # 4. ATTACHMENT CHECK (Indikator Pendukung)
    # ==========================================
    # Kehadiran PDF HANYA nambahin 2 poin.
    if attachments and len(attachments) > 0:
        scores["document"] += 2

    # ==========================================
    # 5. KEPUTUSAN PEMENANG
    # ==========================================
    max_score = max(scores.values())

    # Kalau skornya 0 semua (halaman ga jelas / landing page biasa)
    if max_score == 0:
        if domain.endswith(".go.id"):
            return "government"
        return "other"

    # Kembalikan kategori dengan skor tertinggi
    best_match = max(scores, key=scores.get)
    return best_match
