# config/browser_config.py

from crawl4ai import BrowserConfig

SEARCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

REALISTIC_HEADERS = {
    "User-Agent": SEARCH_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Google Chrome";v="135", "Chromium";v="135", "Not:A-Brand";v="8"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def get_browser_config(
    site_name: str, headless: bool = True, verbose: bool = False
) -> BrowserConfig:
    """
    Generate BrowserConfig secara dinamis berdasarkan site_name.
    """
    custom_extra_args = []

    # Aturan KEMENKEU: Butuh bypass CORS yang hardcore
    if site_name == "KEMENKEU":
        custom_extra_args = [
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--ignore-certificate-errors",
        ]
        return BrowserConfig(
            headless=headless,
            verbose=verbose,
            headers=REALISTIC_HEADERS,
            ignore_https_errors=True,
            extra_args=custom_extra_args,
        )

    # Aturan KOMDIGI & BAPPENAS: Butuh headers realistis biar ga dikira bot murahan
    elif site_name in ["KOMDIGI", "BAPPENAS"]:
        return BrowserConfig(
            headless=headless,
            verbose=verbose,
            headers=REALISTIC_HEADERS,
            ignore_https_errors=True,
        )

    # Aturan DEFAULT (BPS, BGN, ESDM dll): Polosan aja, satpamnya lebih santuy
    else:
        return BrowserConfig(
            headless=headless,
            verbose=verbose,
            # BPS sering nge-block kalau kita over-engineering headers-nya
        )


# # config/browser_config.py


# SEARCH_USER_AGENT = (
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#     "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
# )

# REALISTIC_HEADERS = {
#     "User-Agent": SEARCH_USER_AGENT,
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Accept-Encoding": "gzip, deflate, br",
#     "DNT": "1",
#     "Connection": "keep-alive",
#     "Upgrade-Insecure-Requests": "1",
#     "Sec-Fetch-Dest": "document",
#     "Sec-Fetch-Mode": "navigate",
#     "Sec-Fetch-Site": "none",
#     "Sec-Fetch-User": "?1",
#     "sec-ch-ua": '"Google Chrome";v="135", "Chromium";v="135", "Not:A-Brand";v="8"',
#     "sec-ch-ua-mobile": "?0",
#     "sec-ch-ua-platform": '"Windows"',
# }


# def get_browser_config(
#     site_name: str, headless: bool = True, verbose: bool = False
# ) -> BrowserConfig:
#     """
#     Generate BrowserConfig secara dinamis berdasarkan site_name.
#     """
#     custom_extra_args = [
#         "--no-sandbox",
#         "--disable-dev-shm-usage",
#         "--disable-blink-features=AutomationControlled",
#     ]

#     # Aturan Menu 1: KEMENKEU & BGN (Bypass Hardcore + Headers)
#     if site_name in ["KEMENKEU", "BGN"]:
#         custom_extra_args.extend(
#             [
#                 "--disable-web-security",
#                 "--disable-features=IsolateOrigins,site-per-process",
#                 "--ignore-certificate-errors",
#             ]
#         )
#         return BrowserConfig(
#             headless=headless,
#             verbose=verbose,
#             headers=REALISTIC_HEADERS,  # KEMBALIKAN HEADERS
#             ignore_https_errors=True,
#             extra_args=custom_extra_args,
#         )

#     # Aturan Menu 1: KOMDIGI & BAPPENAS (Cuma Butuh Headers)
#     elif site_name in ["KOMDIGI", "BAPPENAS"]:
#         return BrowserConfig(
#             headless=headless,
#             verbose=verbose,
#             headers=REALISTIC_HEADERS,  # KEMBALIKAN HEADERS
#             ignore_https_errors=True,
#             extra_args=custom_extra_args,
#         )

#     # Aturan Menu 2 (Keyword/Google) & Default Lainnya
#     else:
#         return BrowserConfig(
#             headless=headless,
#             verbose=verbose,
#             ignore_https_errors=True,
#             extra_args=custom_extra_args,
#             # DIBIARKAN KOSONG TANPA HEADERS biar magic=True Crawl4AI jalan sempurna di Google
#         )
