import asyncio
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.government_config import GOVERNMENT_SITES_CONFIG
from pipelines.government_pipeline import run as run_government_pipeline

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def show_main_menu():
    print("\n=== CRAWLER MENU ===")
    print("1. Crawl Government Website")
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

                run_government_pipeline(selected_site)

                print(f"\n=== FINISHED [{selected_site}] ===\n")

            elif choice == 0:
                print("\nExit crawler.")
                break

            else:
                print("Invalid choice.")

        except ValueError:
            print("Input must be number.")


if __name__ == "__main__":
    main()
