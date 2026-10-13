# save.py — сохранение и загрузка прогресса в JSON.

import json
import os

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")


def ensure_dir():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)


def save_game(state_dict) -> bool:
    """state_dict — словарь с полным состоянием игры."""
    try:
        ensure_dir()
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Ошибка сохранения:", e)
        return False


def load_game():
    """Возвращает dict или None, если сейва нет / ошибка."""
    try:
        if not os.path.exists(SAVE_FILE):
            return None
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Ошибка загрузки:", e)
        return None


def has_save() -> bool:
    return os.path.exists(SAVE_FILE)


def delete_save():
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
    except Exception as e:
        print("Ошибка удаления сейва:", e)