"""
api_clients.py
--------------
Obsahuje dva tenké HTTP klienty:
  - ZephyrClient  : komunikuje se Zephyr Scale REST API
  - SquashClient  : komunikuje se Squash TM REST API v1

Oba klienti:
  - Sdílejí helper _request() s jednotným error-handlingem
  - Automaticky přidávají autentizaci a Content-Type hlavičky
  - Vyvolávají requests.HTTPError při non-2xx odpovědi
  - Používají retry adapter pro přechodné 5xx chyby
"""

import logging
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Sdílená továrna na session s retry logikou                                  #
# --------------------------------------------------------------------------- #
def _build_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    """Vytvoří requests.Session s automatickým retry pro 5xx a connection chyby."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "PATCH"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# =========================================================================== #
# ZEPHYR CLIENT                                                                #
# =========================================================================== #
class ZephyrClient:
    """
    Klient pro Zephyr Scale REST API.
    Dokumentace: https://support.smartbear.com/zephyr-scale-cloud/api-docs/

    Autentizace: Bearer token (Zephyr Scale Cloud / Server)
    """

    def __init__(self) -> None:
        self.base_url = config.ZEPHYR_BASE_URL.rstrip("/")
        self._session = _build_session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.ZEPHYR_TOKEN}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug("[Zephyr] %s %s | params=%s", method, url, kwargs.get("params"))
        response = self._session.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ----------------------------------------------------------------------- #
    # Zephyr: Složky                                                           #
    # ----------------------------------------------------------------------- #
    def get_folders(self) -> list[dict]:
        """
        GET /folders?projectKey={key}&folderType=TEST_CASE

        Příklad odpovědi:
        [
          {"id": 1, "name": "Modul A",    "parentId": null},
          {"id": 2, "name": "Podmodul B", "parentId": 1}
        ]
        """
        return self._request(
            "GET",
            "/folders",
            params={
                "projectKey": config.ZEPHYR_PROJECT_KEY,
                "folderType": "TEST_CASE",
                "maxResults": 1000,
            },
        )

    # ----------------------------------------------------------------------- #
    # Zephyr: Testy (se stránkováním)                                          #
    # ----------------------------------------------------------------------- #
    def get_test_cases(self, folder_id: Optional[int] = None) -> list[dict]:
        """
        GET /testcases?projectKey={key}&folderId={id}

        Klíčová pole odpovědi:
          {
            "key":       "PROJ-T1",
            "name":      "Název testu",
            "objective": "<p>Popis</p>",   → Squash description
            "status":    "Draft",           → mapujeme přes STATUS_MAP
            "folder":    {"id": 2},
            "testScript": {
              "steps": [
                {"index": 1, "description": "...", "expectedResult": "..."},
                ...
              ]
            }
          }
        """
        params: dict = {
            "projectKey": config.ZEPHYR_PROJECT_KEY,
            "maxResults": 100,
            "startAt": 0,
        }
        if folder_id is not None:
            params["folderId"] = folder_id

        all_tests: list[dict] = []
        while True:
            data = self._request("GET", "/testcases", params=params)

            # Zephyr Scale vrací dict se stránkováním nebo rovnou seznam
            if isinstance(data, dict):
                items = data.get("values", data.get("testCases", []))
                total = data.get("total", len(items))
            else:
                items = data
                total = len(data)

            all_tests.extend(items)
            params["startAt"] += len(items)
            if params["startAt"] >= total or not items:
                break

        return all_tests

    # ----------------------------------------------------------------------- #
    # Zephyr: Kroky testu                                                      #
    # ----------------------------------------------------------------------- #
    def get_test_steps(self, test_key: str) -> list[dict]:
        """
        GET /testcases/{testCaseKey}/teststeps

        Klíčová pole každého kroku:
          {
            "index":          1,          → zachováváme pořadí
            "description":    "Krok 1",   → Squash 'action'
            "expectedResult": "Výsl. 1"   → Squash 'expected_result'
          }

        Poznámka: Starší API může mít pole 'step' místo 'description'.
        """
        data = self._request("GET", f"/testcases/{test_key}/teststeps")
        if isinstance(data, dict):
            return data.get("values", [])
        return data if isinstance(data, list) else []


# =========================================================================== #
# SQUASH CLIENT                                                                #
# =========================================================================== #
class SquashClient:
    """
    Klient pro Squash TM REST API v1.
    Autentizace: HTTP Basic Auth (username + password).
    """

    def __init__(self) -> None:
        self.base_url = config.SQUASH_BASE_URL.rstrip("/")
        self._session = _build_session()
        self._session.auth = (config.SQUASH_USERNAME, config.SQUASH_PASSWORD)
        self._session.headers.update({"Content-Type": "application/json"})

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug("[Squash] %s %s", method, url)
        response = self._session.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ----------------------------------------------------------------------- #
    # Squash: Root složka projektu                                             #
    # ----------------------------------------------------------------------- #
    def get_project_root_folder_id(self) -> int:
        """
        GET /projects/{projectId}/test-case-libraries
        Vrátí ID kořenové složky (knihovny testů) projektu.

        Odpověď (HAL formát):
          {"id": 42, "name": "...", "_type": "test-case-library", ...}
        """
        data = self._request("GET", f"/projects/{config.SQUASH_PROJECT_ID}/test-case-libraries")
        return data["id"]

    # ----------------------------------------------------------------------- #
    # Squash: Obsah složky                                                     #
    # ----------------------------------------------------------------------- #
    def get_folder_children(self, folder_id: int) -> list[dict]:
        """
        GET /test-case-folders/{folderId}/content

        Squash vrací HAL:
          {"_embedded": {"items": [...]}}
        kde každý item má '_type': 'test-case-folder' nebo 'test-case'.
        """
        data = self._request("GET", f"/test-case-folders/{folder_id}/content")
        embedded = data.get("_embedded", {})
        return embedded.get("items", embedded.get("test-cases", []))

    # ----------------------------------------------------------------------- #
    # Squash: Vytvoření složky (idempotentní)                                  #
    # ----------------------------------------------------------------------- #
    def find_or_create_folder(self, parent_folder_id: int, name: str) -> int:
        """
        Idempotentní: najde podsložku podle jména nebo ji vytvoří.
        Vrátí ID složky.

        POST /test-case-folders
        Tělo:
          {
            "_type":  "test-case-folder",
            "name":   "Název složky",
            "parent": {"id": 42}
          }
        """
        # Prohledáme existující podsložky
        for child in self.get_folder_children(parent_folder_id):
            if child.get("_type") in ("test-case-folder", "folder") and child.get("name") == name:
                logger.info("    [FOLDER SKIP] '%s' již existuje (id=%s)", name, child["id"])
                return child["id"]

        logger.info("    [FOLDER CREATE] '%s' → parent_id=%s", name, parent_folder_id)
        result = self._request(
            "POST",
            "/test-case-folders",
            json={
                "_type":  "test-case-folder",
                "name":   name,
                "parent": {"id": parent_folder_id},
            },
        )
        return result["id"]

    # ----------------------------------------------------------------------- #
    # Squash: Hledání testu v složce (ochrana proti duplicitám)               #
    # ----------------------------------------------------------------------- #
    def find_test_in_folder(self, folder_id: int, name: str) -> Optional[dict]:
        """Vrátí existující test se shodným názvem nebo None."""
        for child in self.get_folder_children(folder_id):
            if child.get("_type") == "test-case" and child.get("name") == name:
                return child
        return None

    # ----------------------------------------------------------------------- #
    # Squash: Vytvoření testu                                                  #
    # ----------------------------------------------------------------------- #
    def create_test_case(
        self, folder_id: int, name: str, description: str, status: str
    ) -> dict:
        """
        POST /test-cases
        Tělo:
          {
            "_type":       "test-case",
            "name":        "Název testu",
            "description": "<p>HTML popis</p>",
            "status":      "APPROVED",
            "parent":      {"id": 55}
          }

        Odpověď obsahuje 'id' nově vytvořeného testu.
        """
        return self._request(
            "POST",
            "/test-cases",
            json={
                "_type":       "test-case",
                "name":        name,
                "description": description or "",
                "status":      status,
                "parent":      {"id": folder_id},
            },
        )

    # ----------------------------------------------------------------------- #
    # Squash: Přidání kroku testu                                              #
    # ----------------------------------------------------------------------- #
    def add_test_step(self, test_case_id: int, action: str, expected_result: str) -> dict:
        """
        POST /test-cases/{testCaseId}/steps
        Tělo:
          {
            "_type":           "action-step",
            "action":          "Text akce",
            "expected_result": "Očekávaný výsledek"
          }

        Kroky se přidávají v pořadí volání → nutno volat se seřazenými kroky!
        """
        return self._request(
            "POST",
            f"/test-cases/{test_case_id}/steps",
            json={
                "_type":           "action-step",
                "action":          action or "",
                "expected_result": expected_result or "",
            },
        )
