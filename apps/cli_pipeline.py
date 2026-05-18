import asyncio
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.government_config import GOVERNMENT_SITES_CONFIG
from config.keyword_config import MAX_LINKS_TO_CRAWL, MAX_SEED_RESULTS
from pipelines.government_pipeline import run as run_government_pipeline
from pipelines.keyword_pipeline import run_by_keyword

# IMPORT BARU BUAT SITEMAP PIPELINE
from pipelines.sitemap_pipeline import run_sitemap_pipeline

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def show_main_menu():
    print("\n=== CRAWLER MENU ===")
    print("1. Crawl Government Website")
    print("2. Keyword Crawl")
    print("3. Sitemap Crawl (Fast Extraction)")
    print("0. Exit")


def choose_government_site():
    sites = list(GOVERNMENT_SITES_CONFIG.keys())

    print("\n=== GOVERNMENT WEBSITE LIST ===")

    for index, site_name in enumerate(sites, start=1):
        print(f"{index}. {site_name}")

    print("0. Back")

    while True:
        try:
            choice = int(input("\nChoose website: "))

            if choice == 0:
                return None

            if 1 <= choice <= len(sites):
                return sites[choice - 1]

            print("Invalid choice.")

        except ValueError:
            print("Input must be number.")


def main():
    while True:
        show_main_menu()

        try:
            choice = int(input("\nChoose menu: "))

            if choice == 1:
                selected_site = choose_government_site()

                if not selected_site:
                    continue

                print(f"\n=== START CRAWLING [{selected_site}] ===\n")

                asyncio.run(run_government_pipeline(selected_site))

                print(f"\n=== FINISHED [{selected_site}] ===\n")

            elif choice == 2:
                keyword = input("\nEnter keyword: ").strip()
                if not keyword:
                    print("Keyword cannot be empty.")
                    continue

                only_go_id = (
                    input("Only include go.id domains? (y/n): ").strip().lower()
                )
                require_go_id = only_go_id == "y"

                print(f"\n=== START KEYWORD CRAWL [{keyword}] ===\n")

                result = run_by_keyword(
                    keyword,
                    max_seed_results=MAX_SEED_RESULTS,
                    max_links=MAX_LINKS_TO_CRAWL,
                    output_prefix="dynamic_keyword",
                    require_go_id=require_go_id,
                )

                if result:
                    print(
                        f"Seed discovery source: {result.get('seed_discovery_source')}"
                    )
                    if result.get("seed_discovery_error"):
                        print(
                            f"Seed discovery note: {result.get('seed_discovery_error')}"
                        )

                    seed_urls = result.get("seed_urls", [])
                    print(f"Discovered seed URLs: {len(seed_urls)}")
                    for url in seed_urls:
                        print(f"- {url}")

                    if result.get("combined_output_path"):
                        print(f"Output file: {result.get('combined_output_path')}")
                else:
                    print("No results found.")

                print(f"\n=== FINISHED KEYWORD CRAWL [{keyword}] ===\n")

            # ============================================================
            # 🔥 BLOK OPSI 3: SITEMAP CRAWL
            # ============================================================
            elif choice == 3:
                print("\n=== SITEMAP CRAWLER ===")
                sitemap_url = input(
                    "Masukkan URL Sitemap (contoh: https://brin.go.id/sitemap.xml): "
                ).strip()
                if not sitemap_url:
                    print("URL Sitemap tidak boleh kosong.")
                    continue

                source_name = input(
                    "Masukkan Nama Source (contoh: BRIN_SITEMAP): "
                ).strip()
                if not source_name:
                    print("Nama Source tidak boleh kosong.")
                    continue

                try:
                    limit_input = input(
                        "Berapa maksimal artikel yang mau ditarik? (Kosongkan jika ingin tarik SEMUA): "
                    )
                    limit_urls = int(limit_input) if limit_input.strip() else None
                except ValueError:
                    limit_urls = None

                print(f"\n=== START SITEMAP CRAWL [{source_name}] ===\n")

                asyncio.run(run_sitemap_pipeline(sitemap_url, source_name, limit_urls))

                print(f"\n=== FINISHED SITEMAP CRAWL [{source_name}] ===\n")
            # ============================================================

            elif choice == 0:
                print("\nExit crawler.")
                break

            else:
                print("Invalid choice.")

        except ValueError:
            print("Input must be number.")


if __name__ == "__main__":
    main()
