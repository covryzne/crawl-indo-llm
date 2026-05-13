import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipelines.government_pipeline import run as run_government_pipeline
from pipelines.keyword_pipeline import run as run_keyword_pipeline
from pipelines.keyword_pipeline import run_keyword as run_dynamic_keyword_pipeline
from pipelines.komdigi_pipeline import run as run_komdigi_pipeline


def main():
    crawl_dir = Path(__file__).parent.parent.absolute()
    os.chdir(crawl_dir)

    print("Starting Scraping Pipeline...")

    pipelines = {
        "1": ("Regulation Pipeline (peraturan.go.id)", run_peraturan_pipeline),
        "2": ("Komdigi News Pipeline", run_komdigi_pipeline),
        "3": ("General News Pipeline (BAPPENAS, BGN, ESDM)", run_government_pipeline),
    }

    print("\nSelect Pipeline to run:")
    print("1. Regulation Pipeline (Rekap -> Scrape -> Download PDF -> Metadata)")
    print("2. Komdigi News Pipeline (Links -> Clean -> Scrape Content)")
    print("3. General News Pipeline (Links -> Scrape Content)")
    print("4. Run ALL")
    print("5. URL Crawl")
    print("6. Keyword Crawl")
    print("Q. Quit")

    choice = input("\nEnter choice: ").strip().lower()

    if choice == "1":
        pipelines["1"][1]()
    elif choice == "2":
        pipelines["2"][1]()
    elif choice == "3":
        pipelines["3"][1]()
    elif choice == "4":
        run_peraturan_pipeline()
        run_komdigi_pipeline()
        run_government_pipeline()
    elif choice == "5":
        url = input("Enter URL to crawl: ").strip()
        if not url:
            print("No URL provided.")
            return
        run_keyword_pipeline(url, output_name="dynamic_output.json")
    elif choice == "6":
        keyword = input("Enter keyword: ").strip()
        if not keyword:
            print("No keyword provided.")
            return
        only_go_id = input("Only include go.id domains? (y/n): ").strip().lower()
        require_go_id = only_go_id == "y"
        result = run_dynamic_keyword_pipeline(
            keyword,
            max_seed_results=10,
            max_links=20,
            output_prefix="dynamic_keyword",
            require_go_id=require_go_id,
        )
        print(f"Seed discovery source: {result.get('seed_discovery_source')}")
        if result.get("seed_discovery_error"):
            print(f"Seed discovery note: {result.get('seed_discovery_error')}")
        if not result.get("seed_urls"):
            print("No seed URLs discovered.")
        else:
            print("Discovered seed URLs:")
            for url in result.get("seed_urls", []):
                print(f"- {url}")

        if result.get("combined_output_path"):
            print(f"Combined output: {result.get('combined_output_path')}")
    elif choice == "q":
        return
    else:
        print("Invalid choice.")
        return

    print("\nPipeline execution finished!")


if __name__ == "__main__":
    main()
