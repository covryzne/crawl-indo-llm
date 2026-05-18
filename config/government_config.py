GOVERNMENT_SITES_CONFIG = {
    "BAPPENAS": {
        "pagination": {
            "type": "url",
        },
        "links": {
            "url": "https://www.bappenas.go.id/kategori-berita/207?page={page}",
            "schema": {
                "name": "BAPPENAS_LINKS",
                "baseSelector": "div.blog-posts",
                "fields": [
                    {
                        "name": "page",
                        "selector": "ul.pagination li.page-item.active",
                        "type": "text",
                    },
                    {
                        "name": "news_items",
                        "selector": "article.post.post-medium",
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "div.post-content a.text-decoration-none",
                                "type": "attribute",
                                "attribute": "title",
                            },
                            {
                                "name": "link",
                                "selector": "div.post-content a.text-decoration-none",
                                "type": "attribute",
                                "attribute": "href",
                            },
                        ],
                    },
                ],
            },
            "wait_for": "article.post.post-medium",
        },
        "detail": {
            "schema": {
                "name": "BAPPENAS_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "date",
                        "selector": "div.col-md-8 span",
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "div.moskie",
                        "type": "text",
                    },
                    # Ganti blok source_pdf lama dengan yang ini
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",  # Ubah jadi list biar dia nge-loop semua tag a
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",  # Targetin elemen itu sendiri
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            "wait_for": "div.moskie",
        },
    },
    "BGN": {
        "pagination": {
            "type": "url",
        },
        "links": {
            "url": "https://www.bgn.go.id/news/siaran-pers/?page={page}",
            "schema": {
                "name": "BGN_LINKS",
                "baseSelector": "section.grid > div",
                "fields": [
                    {
                        "name": "title",
                        "selector": "a h3",
                        "type": "text",
                    },
                    {
                        "name": "link",
                        "selector": "a",
                        "type": "attribute",
                        "attribute": "href",
                    },
                ],
            },
            "wait_for": "section.grid h3",
            "js_code": "window.scrollTo(0, 1000);",
        },
        "detail": {
            "schema": {
                "name": "BGN_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "date",
                        "selector": "h3.text-gray-500",
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "section.prose",
                        "type": "text",
                    },
                    # Ganti blok source_pdf lama dengan yang ini
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",  # Ubah jadi list biar dia nge-loop semua tag a
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",  # Targetin elemen itu sendiri
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            "wait_for": "section.prose",
        },
    },
    "ESDM": {
        "pagination": {
            "type": "url",
        },
        "links": {
            "url": "https://www.esdm.go.id/id/media-center/siaran-pers?page={page}",
            "schema": {
                "name": "ESDM_LINKS",
                "baseSelector": "div.row.list-berita",
                "fields": [
                    {
                        "name": "page",
                        "selector": "li.page.page-item.active a",
                        "type": "text",
                    },
                    {
                        "name": "news_items",
                        "selector": "div.berita-item",
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "h4.title a",
                                "type": "text",
                            },
                            {
                                "name": "link",
                                "selector": "h4.title a",
                                "type": "attribute",
                                "attribute": "href",
                            },
                        ],
                    },
                ],
            },
            "wait_for": "div.berita-item",
        },
        "detail": {
            "schema": {
                "name": "ESDM_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "date",
                        "selector": "div.date.mb-3 small",
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "div.news-read",
                        "type": "text",
                    },
                    # Ganti blok source_pdf lama dengan yang ini
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",  # Ubah jadi list biar dia nge-loop semua tag a
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",  # Targetin elemen itu sendiri
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            "wait_for": "div.news-read",
        },
    },
    "KOMDIGI": {
        "pagination": {
            "type": "js_click",
        },
        "links": {
            "url": "https://www.komdigi.go.id/berita/siaran-pers",
            "schema": {
                "name": "KOMDIGI_LINKS",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "news_items",
                        "selector": "div.flex.flex-col.gap-1",
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "a.text-base.line-clamp-2",
                                "type": "text",
                            },
                            {
                                "name": "link",
                                "selector": "a.text-base.line-clamp-2",
                                "type": "attribute",
                                "attribute": "href",
                            },
                        ],
                    },
                ],
            },
            "wait_for": "a.text-base.line-clamp-2",
        },
        "detail": {
            "schema": {
                "name": "KOMDIGI_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "date",
                        "selector": "section.flex.mt-5 span.text-body-l:not([style])",
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "section#section_text_body",
                        "type": "text",
                    },
                    # Ganti blok source_pdf lama dengan yang ini
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",  # Ubah jadi list biar dia nge-loop semua tag a
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",  # Targetin elemen itu sendiri
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            "wait_for": "section#section_text_body",
        },
    },
    "BPS": {
        "pagination": {
            "type": "url",
        },
        "links": {
            "url": "https://www.bps.go.id/id/news?page={page}",
            "schema": {
                "name": "BPS_LINKS",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "news_items",
                        "selector": "div.grid > div",
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "p.text-xl",
                                "type": "text",
                            },
                            {
                                "name": "link",
                                "selector": "a",
                                "type": "attribute",
                                "attribute": "href",
                            },
                            {
                                "name": "date",
                                "selector": "small",
                                "type": "text",
                            },
                        ],
                    },
                ],
            },
            "wait_for": "div.grid a",
        },
        "detail": {
            "schema": {
                "name": "BPS_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "title",
                        "selector": "h1",
                        "type": "text",
                    },
                    {
                        "name": "date",
                        "selector": "div.w-full > p:first-of-type",
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "div[class*='abstract'], div[class*='Abstract']",
                        "type": "text",
                    },
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            # ==================================================================
            # FIX BIANG KEROK: Longgarkan wait_for & Tambah Anti-Bot Protection
            # ==================================================================
            "wait_for": "body",  # Pindah ke body agar tidak nge-hang nunggu h1
            "wait_for_timeout": 5000,  # Maksimal nunggu 5 detik aja, ga usah sampai 30 detik
            "delay_before_scrape": 2.0,  # Kasih jeda human-like 2 detik sebelum ngeruk data detail
            "sleep_on_page_close": 1.5,  # Jeda napas browser sebelum menutup page
            "magic_context": True,  # Aktifkan auto-stealth browser fingerprinting
            # ==================================================================
        },
    },
    "KEMENKEU": {
        "pagination": {
            "type": "js_click",
            "js_code": "document.querySelector('ul.pagination a[aria-label=\"Next\"]').click();",
            "last_page_marker": None,
        },
        "links": {
            "url": "https://www.kemenkeu.go.id/informasi-publik/publikasi/siaran-pers",
            "schema": {
                "name": "KEMENKEU_LINKS",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "news_items",
                        # Ngambil pembungkus langsung dari headline dan grid item
                        "selector": "div[class*='content-first'] div.tw-flex.tw-flex-col, div[class*='content-other'] div.tw-flex.tw-flex-col",
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "a[href*='/siaran-pers/']",
                                "type": "text",
                            },
                            {
                                "name": "link",
                                "selector": "a[href*='/siaran-pers/']",
                                "type": "attribute",
                                "attribute": "href",
                            },
                            {
                                "name": "date",
                                "selector": "div[class*='date']",  # Bungkus p hari, tanggal, jam
                                "type": "text",
                            },
                        ],
                    },
                ],
            },
            # KUNCI UTAMA: Bot dipaksa nunggu sampe link beritanya kelar di-render sama Angular
            "wait_for": "div[class*='content-other'] a[href*='/siaran-pers/']",
        },
        "detail": {
            "schema": {
                "name": "KEMENKEU_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "title",
                        "selector": "div[class*='content-item__header'] p.tw-font-bold",
                        "type": "text",
                    },
                    {
                        "name": "date",
                        "selector": "div[class*='header-date'] div.tw-flex:first-child",
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "div[class*='detail__content__description']",
                        "type": "text",
                    },
                    # Ganti blok source_pdf lama dengan yang ini
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",  # Ubah jadi list biar dia nge-loop semua tag a
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",  # Targetin elemen itu sendiri
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            # Nunggu deskripsi artikel muncul
            "wait_for": "div[class*='detail__content__description']",
        },
    },
    "BRIN": {
        "pagination": {
            "type": "js_click",
            # JS ini bakal nyari tombol yang ada tulisan "Next" atau icon "»" terus di-click
            "js_code": "Array.from(document.querySelectorAll('a.page-link')).find(el => el.textContent.includes('Next') || el.textContent.includes('»')).click();",
        },
        "links": {
            "url": "https://brin.go.id/press-release",
            "schema": {
                "name": "BRIN_LINKS",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "news_items",
                        "selector": "div.media-body",  # Langsung tembak ke bungkus tiap berita
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "h5 a",
                                "type": "text",
                            },
                            {
                                "name": "link",
                                "selector": "h5 a",
                                "type": "attribute",
                                "attribute": "href",
                            },
                            {
                                "name": "date",
                                "selector": "div.date",
                                "type": "text",
                            },
                        ],
                    },
                ],
            },
            "wait_for": "div.media-body",
        },
        "detail": {
            "schema": {
                "name": "BRIN_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "date",
                        "selector": "div.press-conference-content p:nth-child(2) b",  # Tanggal biasanya ada di paragraf 2 dlm tag B
                        "type": "text",
                    },
                    {
                        "name": "text",
                        "selector": "div.press-conference-content",
                        "type": "text",
                    },
                    {
                        "name": "source_pdf",
                        "selector": "a[href$='.pdf']",
                        "type": "list",
                        "fields": [
                            {
                                "name": "url",
                                "selector": "",
                                "type": "attribute",
                                "attribute": "href",
                            }
                        ],
                    },
                ],
            },
            "wait_for": "div.press-conference-content",
        },
    },
    "BRIN_JDIH": {
        "pagination": {
            "type": "url",  # Karena JDIH pakai ?page=2 dst
        },
        "links": {
            "url": "https://jdih.brin.go.id/dokumen-hukum/peraturan?page={page}",
            "schema": {
                "name": "BRIN_JDIH_LINKS",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "news_items",
                        "selector": "div[data-testid='flowbite-card']",  # Card bawaan flowbite/tailwind
                        "type": "list",
                        "fields": [
                            {
                                "name": "title",
                                "selector": "h5",
                                "type": "text",
                            },
                            {
                                "name": "link",
                                "selector": "a[href*='/dokumen-hukum/peraturan/view/']",
                                "type": "attribute",
                                "attribute": "href",
                            },
                            {
                                "name": "date",
                                "selector": "p",  # Ngambil deskripsi singkat aja karena tgl rilis ga ada di list
                                "type": "text",
                            },
                        ],
                    },
                ],
            },
            "wait_for": "div[data-testid='flowbite-card']",
        },
        "detail": {
            "schema": {
                "name": "BRIN_JDIH_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {
                        "name": "table_data",
                        "selector": "table",
                        "type": "text",
                    }
                ],
            },
            # Cukup tunggu tabelnya muncul
            "wait_for": "table",
        },
    },
}

from config.pagination_config import get_government_pagination

SCRAPER_CONFIG = get_government_pagination()

# OUTPUT_LINKS_FILE = "siaran_pers_pemerintahan_links.json"
OUTPUT_DIR = "outputs"
