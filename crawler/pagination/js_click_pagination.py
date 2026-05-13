# crawler/pagination/js_click_pagination.py


def get_js_click_config(
    pagination_config,
    page_num,
):
    if page_num <= 1:
        return {
            "js_code": None,
            "js_only": False,
        }

    return {
        "js_code": pagination_config.get("js_code"),
        "js_only": True,
    }


def is_last_page(
    result_html,
    pagination_config,
):
    last_page_marker = pagination_config.get("last_page_marker")

    if not last_page_marker:
        return False

    return last_page_marker in result_html
