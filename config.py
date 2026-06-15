"""
config.py
---------
Načte a validuje konfiguraci z .env souboru.
Vyvolá výjimku ValueError, pokud chybí povinná proměnná.
"""

import os
from dotenv import load_dotenv

# Načteme proměnné ze souboru .env (pokud existuje)
load_dotenv()


# --------------------------------------------------------------------------- #
# Pomocná funkce: načte proměnnou nebo vyhodí smysluplnou chybu               #
# --------------------------------------------------------------------------- #
def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"Chybí povinná konfigurační proměnná: '{key}'. "
            f"Zkontroluj soubor .env nebo systémové proměnné prostředí."
        )
    return value


# --------------------------------------------------------------------------- #
# Zephyr (Jira / Zephyr Scale / Zephyr Squad)                                 #
# --------------------------------------------------------------------------- #
ZEPHYR_BASE_URL: str    = _require("ZEPHYR_BASE_URL")    # https://jira.example.com/rest/atm/1.0
ZEPHYR_TOKEN: str       = _require("ZEPHYR_TOKEN")       # Bearer token pro Zephyr API
ZEPHYR_PROJECT_KEY: str = _require("ZEPHYR_PROJECT_KEY") # Klíč projektu, např. "PROJ"

# --------------------------------------------------------------------------- #
# Squash TM                                                                    #
# --------------------------------------------------------------------------- #
SQUASH_BASE_URL: str   = _require("SQUASH_BASE_URL")    # https://squash.example.com/squash/api/rest/v1
SQUASH_USERNAME: str   = _require("SQUASH_USERNAME")    # Basic-auth uživatel
SQUASH_PASSWORD: str   = _require("SQUASH_PASSWORD")    # Basic-auth heslo
SQUASH_PROJECT_ID: int = int(_require("SQUASH_PROJECT_ID"))  # Numerické ID projektu ve Squash

# --------------------------------------------------------------------------- #
# Mapování statusů: Zephyr → Squash TM                                        #
# --------------------------------------------------------------------------- #
STATUS_MAP: dict[str, str] = {
    "Approved": "APPROVED",
    "Draft":    "WORK_IN_PROGRESS",
    # Fallback "UNDER_REVISION" je aplikován v main.py pomocí .get(status, "UNDER_REVISION")
}
