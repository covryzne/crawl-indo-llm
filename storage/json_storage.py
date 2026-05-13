import json
from pathlib import Path


def load_json(path):
    json_path = Path(path)
    with open(json_path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(path, data):
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2, ensure_ascii=False)
