import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

# Handle Windows Event Loop Policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Kita import modul keyword_pipeline secara utuh dulu biar ga langsung crash
import pipelines.keyword_pipeline as kp
from config.browser_config import GLOBAL_HEADLESS

# ==============================================================================
# SAFE & DYNAMIC IMPORT ENGINE
# ==============================================================================
# Import government pipeline aman
from pipelines.government_pipeline import run as run_government_pipeline

# Deteksi fungsi secara dinamis. Jika 'run_keyword' ada, pakai itu.
# Jika tidak ada, fallback ke fungsi 'run', atau sebaliknya.
if hasattr(kp, "run_keyword"):
    run_dynamic_keyword_pipeline = kp.run_keyword
elif hasattr(kp, "run"):
    run_dynamic_keyword_pipeline = kp.run
else:
    # Fallback terakhir jika nama fungsinya ternyata bukan keduanya (mencegah crash saat startup)
    run_dynamic_keyword_pipeline = None
# ==============================================================================

# Setup GMT+7 / WIB Timezone
WIB = timezone(timedelta(hours=7))

st.set_page_config(
    page_title="IndoGov Crawler & Early Warning Engine",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "session_headless" not in st.session_state:
    st.session_state.session_headless = GLOBAL_HEADLESS

session_headless = st.session_state.session_headless

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #e9ecef; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🏛️ Indonesian Government Data Crawler")
st.markdown(
    "Modular crawling workflows and automated issue labeling for government regulations and press releases."
)

st.session_state.session_headless = st.checkbox(
    "Headless mode (session)",
    value=st.session_state.session_headless,
    help="Berlaku untuk government dan keyword pipeline dalam sesi Streamlit ini.",
)
session_headless = st.session_state.session_headless

tab0, tab1, tab2 = st.tabs(
    [
        "📊 Dashboard & Analytics",
        "🏢 Government Website Pipeline",
        "🔍 Dynamic Keyword Pipeline",
    ]
)

# ==========================================
# TAB 0: DASHBOARD & MONITORING
# ==========================================
with tab0:
    st.subheader("Engine Status & Last Execution Summary")
    st.info(
        "💡 Entry points are now fully modular. Target pipelines utilize automated anti-bot routing and local page classification."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Current Environment Time (WIB)",
            value=datetime.now(WIB).strftime("%H:%M:%S"),
        )
    with col2:
        st.metric(
            label="Target Site Immunity Status", value="Active (Conditional Bypass)"
        )
    with col3:
        st.metric(label="Output Data Type", value="Enterprise-Grade JSON (V 1.1.0)")

    st.divider()
    st.caption(
        f"Engine Core initialized. System time: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')} GMT+7"
    )

# ==========================================
# TAB 1: GOVERNMENT SITES PIPELINE
# ==========================================
with tab1:
    st.subheader("Government Website Selector Pipeline")
    st.markdown(
        "Scrapes structured press releases using centralized configuration matrices."
    )

    selected_site = st.selectbox(
        "Choose Government Target Website:",
        ["BAPPENAS", "BGN", "ESDM", "KOMDIGI", "BPS", "KEMENKEU"],
        help="Each target features tailored browser fingerprinting via config/browser_config.py",
    )

    st.caption(f"ℹ️ Headless session aktif: {'ON' if session_headless else 'OFF'}")

    if st.button(f"🚀 Run {selected_site} Flow", type="primary"):
        with st.spinner(f"Spawning worker instance for {selected_site}..."):
            try:
                result_payload = asyncio.run(
                    run_government_pipeline(selected_site, headless=session_headless)
                )
                st.success(f"Successfully finished crawling {selected_site}!")

                if result_payload and "metadata" in result_payload:
                    meta = result_payload.get("metadata", {})
                    exec_metrics = meta.get("execution_metrics", {})
                    total_crawled = exec_metrics.get(
                        "total_extracted", len(result_payload.get("data", []))
                    )
                    success_rate = exec_metrics.get("success_rate", "0.0%")
                    duration = exec_metrics.get("duration_seconds", 0)
                    failed_urls = len(meta.get("errors", []))

                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    with m_col1:
                        st.metric("Total Crawled", total_crawled)
                    with m_col2:
                        st.metric("Success Rate", success_rate)
                    with m_col3:
                        st.metric("Duration", f"{duration}s")
                    with m_col4:
                        st.metric("Failed URLs", failed_urls)

                    with st.expander(
                        "📄 View Extracted Payloads (Data & Rich Metadata)",
                        expanded=True,
                    ):
                        st.json(result_payload)
                else:
                    # Fallback jika fungsi run() hanya mengembalikan dictionary biasa atau data raw
                    with st.expander("📄 View Extracted Payloads Data", expanded=True):
                        st.json(result_payload)
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

# ==========================================
# TAB 2: DYNAMIC KEYWORD PIPELINE
# ==========================================
with tab2:
    st.subheader("Dynamic Generic & Keyword Crawl")
    st.markdown(
        "Discovers seed URLs dynamically using Google Search / DuckDuckGo HTML Fallback engine."
    )

    col_key1, col_key2 = st.columns(2)
    with col_key1:
        dynamic_keyword = st.text_input(
            "Enter Target Keyword:",
            placeholder="e.g., Badan Gizi Nasional",
        )
    with col_key2:
        keyword_go_id_only = st.checkbox(
            "Strict domain mode (Only include .go.id websites)", value=True
        )

    st.caption(f"ℹ️ Headless session aktif: {'ON' if session_headless else 'OFF'}")

    with st.expander(
        "⚙️ Fine-Tune Scraper Thresholds (Config-Driven Limits)", expanded=False
    ):
        cfg_col1, cfg_col2 = st.columns(2)
        with cfg_col1:
            keyword_seed_limit = st.slider(
                "Max discovered seed URLs (MAX_SEED_RESULTS)", 5, 30, 10
            )
        with cfg_col2:
            max_links_to_crawl = st.slider(
                "Max depth articles to extract (MAX_LINKS_TO_CRAWL)", 5, 50, 20
            )

    if st.button("🔍 Run Intelligent Keyword Crawl"):
        if not run_dynamic_keyword_pipeline:
            st.error(
                "🛑 Error: No valid crawl function found in `pipelines/keyword_pipeline.py`. Please check your file content."
            )
        elif not dynamic_keyword.strip():
            st.warning("Validation Error: Keyword field cannot be empty.")
        else:
            with st.spinner("Executing Search Stealth Worker..."):
                try:
                    # Menjalankan fungsi yang berhasil dideteksi secara otomatis
                    keyword_result = run_dynamic_keyword_pipeline(
                        dynamic_keyword.strip(),
                        max_seed_results=keyword_seed_limit,
                        max_links=max_links_to_crawl,
                        output_prefix="dynamic_keyword",
                        require_go_id=keyword_go_id_only,
                        headless=session_headless,
                    )

                    if not keyword_result or not keyword_result.get("seed_urls"):
                        st.warning(
                            "⚠️ No seed URLs discovered. WAF Captcha triggered or no matching go.id domain found."
                        )
                    else:
                        st.success("✨ Keyword crawl completed successfully!")

                    st.subheader("📊 Execution Statistics")
                    sum_col1, sum_col2, sum_col3 = st.columns(3)
                    with sum_col1:
                        st.metric(
                            "Discovered Seeds",
                            (
                                len(keyword_result.get("seed_urls", []))
                                if keyword_result
                                else 0
                            ),
                        )
                    with sum_col2:
                        st.metric(
                            "Web Results Count",
                            (
                                len(keyword_result.get("web_results", []))
                                if keyword_result
                                else 0
                            ),
                        )
                    with sum_col3:
                        st.metric(
                            "PDF Queue Count",
                            (
                                len(keyword_result.get("pdf_queue", []))
                                if keyword_result
                                else 0
                            ),
                        )

                    with st.expander(
                        "📂 View Discovered Seed URLs Array", expanded=False
                    ):
                        st.json(
                            keyword_result.get("seed_urls", [])
                            if keyword_result
                            else []
                        )

                    with st.expander("📝 View Extracted Summary Paths", expanded=True):
                        if keyword_result:
                            st.json(
                                {
                                    "combined_output_path": keyword_result.get(
                                        "combined_output_path"
                                    ),
                                    "web_output_path": keyword_result.get(
                                        "web_output_path"
                                    ),
                                    "pdf_queue_path": keyword_result.get(
                                        "pdf_queue_path"
                                    ),
                                }
                            )

                except Exception as e:
                    st.error(f"Runtime Exception: {str(e)}")
