"""
main.py
-------
Hlavní migrační skript: Zephyr Scale → Squash TM

Spuštění:
    python main.py

Předpoklady:
    pip install requests python-dotenv
    Soubor .env vyplněný podle .env.example
"""

import logging
import sys
from typing import Optional

import requests

import config                              # načte .env a validuje proměnné
from api_clients import ZephyrClient, SquashClient


# =========================================================================== #
# LOGGING: konzole + soubor migration.log                                     #
# =========================================================================== #
def setup_logging() -> None:
    """Nastaví logger tak, aby psal na konzoli i do souboru migration.log."""
    fmt = "%(asctime)s [%(levelname)-8s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("migration.log", encoding="utf-8"),
        ],
    )

logger = logging.getLogger(__name__)


# =========================================================================== #
# KROK 1: Budování stromu složek Zephyr                                       #
# =========================================================================== #
def build_zephyr_folder_tree(folders: list[dict]) -> dict[int, dict]:
    """
    Ze seznamu Zephyr složek (plochý seznam s parentId) sestaví slovník:
      folder_id → {id, name, parentId, children: [...]}

    Zephyr vrací složky jako plochý seznam, ne jako strom.
    Tato funkce strom rekonstruuje pro správné pořadí vytváření.
    """
    by_id: dict[int, dict] = {}
    for f in folders:
        by_id[f["id"]] = {**f, "children": []}

    roots: list[dict] = []
    for f in by_id.values():
        parent_id = f.get("parentId")
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(f)
        else:
            roots.append(f)

    return by_id, roots


# =========================================================================== #
# KROK 2: Rekurzivní vytvoření struktury složek ve Squash TM                 #
# =========================================================================== #
def migrate_folders(
    squash: SquashClient,
    zephyr_nodes: list[dict],
    squash_parent_id: int,
    squash_folder_map: dict[int, int],      # zephyr_folder_id → squash_folder_id
) -> None:
    """
    Rekurzivně prochází strom složek ze Zephyru a vytváří je ve Squash TM.
    Výsledky ukládá do squash_folder_map (zephyr_id → squash_id).

    Squash TM vyžaduje znalost parent_id, proto zpracovává úroveň po úrovni.
    """
    for node in zephyr_nodes:
        zephyr_id   = node["id"]
        folder_name = node["name"]

        logger.info("[FOLDER] Zpracovávám složku '%s' (zephyr_id=%s)", folder_name, zephyr_id)

        try:
            squash_id = squash.find_or_create_folder(squash_parent_id, folder_name)
            squash_folder_map[zephyr_id] = squash_id
        except requests.HTTPError as exc:
            logger.error("[FOLDER ERROR] '%s': %s", folder_name, exc)
            continue

        # Rekurze do podsložek
        if node.get("children"):
            migrate_folders(squash, node["children"], squash_id, squash_folder_map)


# =========================================================================== #
# KROK 3: Mapování statusu                                                    #
# =========================================================================== #
def map_status(zephyr_status: str) -> str:
    """
    Převod statusu ze Zephyru na hodnotu akceptovanou Squash TM.

    Mapovací tabulka (z config.py):
      'Approved' → 'APPROVED'
      'Draft'    → 'WORK_IN_PROGRESS'
      cokoliv jiného → 'UNDER_REVISION'  (fallback)
    """
    return config.STATUS_MAP.get(zephyr_status, "UNDER_REVISION")


# =========================================================================== #
# KROK 4: Migrace testovacích kroků                                           #
# =========================================================================== #
def migrate_steps(
    zephyr: ZephyrClient,
    squash: SquashClient,
    test_key: str,
    squash_test_id: int,
    inline_steps: Optional[list[dict]] = None,
) -> None:
    """
    Načte kroky ze Zephyru a přidá je do Squash TM ve správném pořadí.

    Zephyr krok → Squash krok:
      step['description'] (nebo 'step') → action
      step['expectedResult']             → expected_result

    Pořadí je zachováno pomocí řazení podle klíče 'index'.
    Kroky přebírá buď z inline_steps (z detailu testu) nebo z API volání.
    """
    steps = inline_steps
    if not steps:
        try:
            steps = zephyr.get_test_steps(test_key)
        except requests.HTTPError as exc:
            logger.warning("[STEPS] Nepodařilo se načíst kroky testu %s: %s", test_key, exc)
            return

    if not steps:
        logger.info("    [STEPS] Test %s nemá žádné kroky.", test_key)
        return

    # Seřadíme striktně podle indexu (zachování pořadí)
    sorted_steps = sorted(steps, key=lambda s: s.get("index", 0))

    for i, step in enumerate(sorted_steps, start=1):
        # Zephyr Scale: pole 'description'; starší API: pole 'step'
        action          = step.get("description") or step.get("step", "")
        expected_result = step.get("expectedResult", "")

        try:
            squash.add_test_step(squash_test_id, action, expected_result)
            logger.debug("    [STEP %d] OK → akce='%s'", i, action[:60])
        except requests.HTTPError as exc:
            logger.error(
                "    [STEP ERROR] Test=%s krok=%d: %s", test_key, i, exc
            )


# =========================================================================== #
# KROK 5: Migrace testovacích případů                                         #
# =========================================================================== #
def migrate_tests(
    zephyr: ZephyrClient,
    squash: SquashClient,
    squash_folder_map: dict[int, int],
    squash_root_id: int,
) -> tuple[int, int, int]:
    """
    Načte všechny testy ze Zephyru a migruje je do správných složek ve Squash TM.

    Vrátí trojici (migrated, skipped, errors).

    Datamapa:
      Zephyr 'name'                      → Squash 'name'
      Zephyr 'objective' nebo 'description' → Squash 'description' (HTML zachováno)
      Zephyr 'status'                    → Squash 'status' (přes map_status())
    """
    logger.info("=" * 60)
    logger.info("Načítám testy ze Zephyru ...")
    tests = zephyr.get_test_cases()
    logger.info("Celkem načteno testů ze Zephyru: %d", len(tests))

    migrated, skipped, errors = 0, 0, 0

    for test in tests:
        test_key  = test.get("key", "N/A")
        test_name = test.get("name", "")

        # ------------------------------------------------------------------- #
        # Určíme cílovou složku ve Squash TM                                  #
        # ------------------------------------------------------------------- #
        zephyr_folder = test.get("folder", {}) or {}
        zephyr_folder_id = zephyr_folder.get("id")

        if zephyr_folder_id and zephyr_folder_id in squash_folder_map:
            target_squash_folder_id = squash_folder_map[zephyr_folder_id]
        else:
            # Test není ve žádné složce → půjde do root knihovny projektu
            target_squash_folder_id = squash_root_id
            if zephyr_folder_id:
                logger.warning(
                    "[TEST] %s: složka zephyr_id=%s nebyla namapována, "
                    "použit root.", test_key, zephyr_folder_id
                )

        logger.info(
            "[TEST] %s | '%s' → squash_folder_id=%s",
            test_key, test_name, target_squash_folder_id
        )

        # ------------------------------------------------------------------- #
        # IDEMPOTENCE: přeskočíme, pokud test v cílové složce již existuje    #
        # ------------------------------------------------------------------- #
        try:
            existing = squash.find_test_in_folder(target_squash_folder_id, test_name)
        except requests.HTTPError as exc:
            logger.error("[TEST ERROR] %s: chyba při kontrole duplicity: %s", test_key, exc)
            errors += 1
            continue

        if existing:
            logger.info("  [SKIP] Test '%s' v cílové složce již existuje.", test_name)
            skipped += 1
            continue

        # ------------------------------------------------------------------- #
        # Datamapa: Zephyr → Squash                                            #
        # ------------------------------------------------------------------- #
        # Zephyr 'objective' = popis (může obsahovat HTML) → Squash 'description'
        # Fallback na 'description' pokud 'objective' chybí
        description = test.get("objective") or test.get("description", "")
        status      = map_status(test.get("status", ""))

        # ------------------------------------------------------------------- #
        # POST /test-cases → vytvoří test ve Squash                           #
        # ------------------------------------------------------------------- #
        try:
            created = squash.create_test_case(
                folder_id=target_squash_folder_id,
                name=test_name,
                description=description,
                status=status,
            )
            squash_test_id = created["id"]
            logger.info("  [CREATED] Squash test_id=%s", squash_test_id)
        except requests.HTTPError as exc:
            logger.error("[TEST ERROR] %s: nepodařilo se vytvořit test: %s", test_key, exc)
            errors += 1
            continue  # přeskočíme, skript pokračuje dalším testem

        # ------------------------------------------------------------------- #
        # Migrace kroků                                                        #
        # Preferujeme inline kroky z detailu testu (šetří API volání)         #
        # ------------------------------------------------------------------- #
        inline_steps = (
            test.get("testScript", {}).get("steps")
            if isinstance(test.get("testScript"), dict)
            else None
        )
        migrate_steps(zephyr, squash, test_key, squash_test_id, inline_steps)

        migrated += 1

    return migrated, skipped, errors


# =========================================================================== #
# ORCHESTRACE: hlavní funkce                                                   #
# =========================================================================== #
def main() -> None:
    setup_logging()

    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║   Zephyr → Squash TM Migration Tool              ║")
    logger.info("╚══════════════════════════════════════════════════╝")
    logger.info("Projekt Zephyr: %s", config.ZEPHYR_PROJECT_KEY)
    logger.info("Squash projekt ID: %s", config.SQUASH_PROJECT_ID)

    # Inicializace klientů
    zephyr = ZephyrClient()
    squash = SquashClient()

    # ----------------------------------------------------------------------- #
    # 1. Získáme root ID projektu ve Squash TM                                #
    # ----------------------------------------------------------------------- #
    logger.info("\n[1/3] Načítám root složku Squash projektu ...")
    try:
        squash_root_id = squash.get_project_root_folder_id()
        logger.info("Squash root folder id = %s", squash_root_id)
    except requests.HTTPError as exc:
        logger.critical("Nepodařilo se načíst root složku Squash projektu: %s", exc)
        sys.exit(1)

    # ----------------------------------------------------------------------- #
    # 2. Načteme a migrujeme strukturu složek ze Zephyru                      #
    # ----------------------------------------------------------------------- #
    logger.info("\n[2/3] Načítám a migruji strukturu složek ze Zephyru ...")
    try:
        zephyr_folders = zephyr.get_folders()
        logger.info("Načteno složek ze Zephyru: %d", len(zephyr_folders))
    except requests.HTTPError as exc:
        logger.critical("Nepodařilo se načíst složky ze Zephyru: %s", exc)
        sys.exit(1)

    # Sestavíme strom (plochy seznam → strom)
    _folder_by_id, root_nodes = build_zephyr_folder_tree(zephyr_folders)

    # squash_folder_map: zephyr_folder_id → squash_folder_id
    squash_folder_map: dict[int, int] = {}
    migrate_folders(squash, root_nodes, squash_root_id, squash_folder_map)
    logger.info("Namapováno složek: %d", len(squash_folder_map))

    # ----------------------------------------------------------------------- #
    # 3. Migrujeme testy (s kroky)                                             #
    # ----------------------------------------------------------------------- #
    logger.info("\n[3/3] Migruji testovací případy ...")
    migrated, skipped, errors = migrate_tests(
        zephyr, squash, squash_folder_map, squash_root_id
    )

    # ----------------------------------------------------------------------- #
    # Závěrečný souhrn                                                         #
    # ----------------------------------------------------------------------- #
    logger.info("\n╔══════════════════════════════════════════════════╗")
    logger.info("║   SOUHRN MIGRACE                                  ║")
    logger.info("╠══════════════════════════════════════════════════╣")
    logger.info("║  ✓ Úspěšně migrováno:  %-5d                      ║", migrated)
    logger.info("║  ⏭  Přeskočeno (dup.): %-5d                      ║", skipped)
    logger.info("║  ✗ Chyby:              %-5d                      ║", errors)
    logger.info("╚══════════════════════════════════════════════════╝")
    logger.info("Detail viz soubor: migration.log")

    if errors > 0:
        sys.exit(1)   # nenulový exit code signalizuje částečný neúspěch


if __name__ == "__main__":
    main()
