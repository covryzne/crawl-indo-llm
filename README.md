# crawl-indo-llm

![GitHub stars](https://img.shields.io/github/stars/covryzne/crawl-indo-llm?style=for-the-badge&logo=github) ![GitHub forks](https://img.shields.io/github/forks/covryzne/crawl-indo-llm?style=for-the-badge&logo=github) ![GitHub issues](https://img.shields.io/github/issues/covryzne/crawl-indo-llm?style=for-the-badge&logo=github)

## 📑 Table of Contents

- [Description](#description)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## 📝 Description

crawl-indo-llm is a specialized web crawling and data collection framework designed to curate high-quality Indonesian language datasets specifically for training and fine-tuning Large Language Models (LLMs). By automating the extraction and preprocessing of localized web content, this project provides a robust pipeline for developers and researchers aiming to improve the performance and cultural nuance of AI models within the Indonesian linguistic landscape. It streamlines the data acquisition process, ensuring that the resulting corpora are clean, formatted, and ready for integration into advanced machine learning workflows.

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/covryzne/crawl-indo-llm
cd crawl-indo-llm

# 2. Create and activate a virtual environment (now run with Python 3.11.9)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# if some error please Install Playwright browsers if using JS-based pagination
playwright install --with-deps

# 4. How to Run

# Option A: Run the Streamlit UI
streamlit run apps/streamlit_app.py

# Option B: Run the CLI Pipelines
python apps/cli_pipeline.py

# Or run specific pipelines directly:
# python pipelines/government_pipeline.py
# python pipelines/keyword_pipeline.py
```

## 📁 Project Structure

```
.
├── apps
│   ├── backupcli_pipeline.py
│   ├── cli_pipeline.py
│   └── streamlit_app.py
├── config
│   └── government_config.py
├── crawler
│   ├── base_crawler.py
│   ├── batch_crawler.py
│   └── pagination
│       ├── js_click_pagination.py
│       └── url_pagination.py
├── extractor
│   ├── __init__.py
│   ├── generic_content.py
│   ├── link_discovery.py
│   ├── page_router.py
│   ├── pdf_discovery.py
│   └── structured_extractor.py
├── komdigi_siaran_pers_pemerintahan.json
├── komdigi_siaran_pers_pemerintahan_links.json
├── outputs
│   ├── combined_keyword_dynamic_keyword.json
│   ├── debug_keyword_dynamic_keyword.json
│   ├── dynamic_keyword_web.json
│   ├── keyword_pdf_queue_bgn_go_id__root.json
│   ├── siaran_pers.json
│   ├── siaran_pers_bappenas.json
│   ├── siaran_pers_bps.json
│   ├── siaran_pers_kemenkeu.json
│   └── siaran_pers_komdigi.json
├── pipelines
│   ├── government_pipeline.py
│   └── keyword_pipeline.py
├── siaran_pers_general.json
├── siaran_pers_general_links.json
├── siaran_pers_komdigi_links.json
└── storage
    ├── json_storage.py
    └── output_formatter.py
```

## 👥 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Clone** your fork: `git clone [https://github.com/covryzne/crawl-indo-llm](https://github.com/covryzne/crawl-indo-llm)`
3. **Create** a new branch: `git checkout -b feature/your-feature`
4. **Commit** your changes: `git commit -am 'Add some feature'`
5. **Push** to your branch: `git push origin feature/your-feature`
6. **Open** a pull request

Please ensure your code follows the project's style guidelines and includes tests where applicable.

---

_This README was generated with ❤️ by [Covryzne](https://github.com/covryzne)_
