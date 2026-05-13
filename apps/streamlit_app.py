import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipelines.government_pipeline import crawl_content as crawl_general_content
from pipelines.government_pipeline import crawl_links as crawl_general_links
from pipelines.keyword_pipeline import run as run_keyword_pipeline
from pipelines.keyword_pipeline import run_keyword as run_dynamic_keyword_pipeline
from pipelines.komdigi_pipeline import crawl_content as crawl_komdigi_content
from pipelines.komdigi_pipeline import crawl_links as crawl_komdigi_links
from pipelines.komdigi_pipeline import remove_duplicates as clean_komdigi_links

st.set_page_config(page_title="IndoGov Crawler", layout="wide")
st.title("🏛️ Indonesian Government Data Crawler")
st.markdown("Modular crawling workflows for regulations and press releases.")


tab0, tab1, tab2 = st.tabs(["Dashboard", "Peraturan Go Id", "Siaran Pers"])
tab3 = st.sidebar.expander("Dynamic URL Crawl", expanded=False)


with tab0:
    st.info(
        "Entry points are now modular. Use the tabs to run a complete pipeline or a stage."
    )
    st.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


with tab1:
    st.subheader("Peraturan Go Id Pipeline")
    if st.button("Run full peraturan flow"):

        async def run_all_peraturan():
            await crawl_rekapitulasi()
            await crawl_all()
            await download_pdfs()
            await extract_pdf_metadata()

        with st.spinner("Running peraturan pipeline..."):
            asyncio.run(run_all_peraturan())
            st.success("Peraturan pipeline finished.")


with tab2:
    st.subheader("Siaran Pers Pipeline")
    if st.button("Run general news flow"):

        async def run_general():
            await crawl_general_links()
            await crawl_general_content()

        with st.spinner("Running general news pipeline..."):
            asyncio.run(run_general())
            st.success("General news pipeline finished.")

    if st.button("Run Komdigi flow"):

        async def run_komdigi():
            await crawl_komdigi_links()
            clean_komdigi_links()
            await crawl_komdigi_content()

        with st.spinner("Running Komdigi pipeline..."):
            asyncio.run(run_komdigi())
            st.success("Komdigi pipeline finished.")


with tab3:
    st.subheader("Dynamic Generic Crawl")
    dynamic_url = st.text_input(
        "Seed URL",
        placeholder="https://example.go.id/berita/...",
    )
    max_links = st.slider("Max internal links to keep", 5, 50, 20)

    if st.button("Run dynamic crawl"):
        if not dynamic_url.strip():
            st.warning("Please enter a URL first.")
        else:
            with st.spinner("Running dynamic crawler..."):
                result = run_keyword_pipeline(
                    dynamic_url.strip(),
                    output_name="dynamic_output.json",
                    max_links=max_links,
                )
                st.success("Dynamic crawl finished.")
                st.json(result)

    st.divider()
    st.subheader("Dynamic Keyword Crawl")
    dynamic_keyword = st.text_input(
        "Keyword",
        placeholder="badan gizi nasional",
    )
    keyword_seed_limit = st.slider("Max seed URLs from keyword", 3, 30, 10)
    keyword_go_id_only = st.checkbox("Only include go.id domains", value=False)

    if st.button("Run keyword crawl"):
        if not dynamic_keyword.strip():
            st.warning("Please enter a keyword first.")
        else:
            with st.spinner("Discovering seed URLs and crawling..."):
                keyword_result = run_dynamic_keyword_pipeline(
                    dynamic_keyword.strip(),
                    max_seed_results=keyword_seed_limit,
                    max_links=max_links,
                    output_prefix="dynamic_keyword",
                    require_go_id=keyword_go_id_only,
                )
                if not keyword_result.get("seed_urls"):
                    st.warning(
                        "No seed URLs discovered. This can happen due to SSL/provider blocking in your environment."
                    )
                else:
                    st.success("Keyword crawl finished.")
                st.write("Discovered seed URLs:")
                st.json(keyword_result.get("seed_urls", []))
                st.write("Crawl summary:")
                st.json(
                    {
                        "web_output_path": keyword_result.get("web_output_path"),
                        "pdf_queue_path": keyword_result.get("pdf_queue_path"),
                        "web_results_count": len(keyword_result.get("web_results", [])),
                        "pdf_queue_count": len(keyword_result.get("pdf_queue", [])),
                        "combined_output_path": keyword_result.get(
                            "combined_output_path"
                        ),
                    }
                )
