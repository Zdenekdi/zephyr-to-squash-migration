# Zephyr ➔ Squash TM Migration Tool

Komplexní migrační nástroj pro automatický přenos testovacích scénářů ze **Zephyr Scale** (Jira) do **Squash TM**. Podporuje přímý online přenos přes REST API i offline konverzi ze souborů Excel a disponuje grafickým uživatelským rozhraním (GUI).

---

## 🏗️ Struktura projektu

```
zephyr-to-squash-migration/
├── gui.py                  # Grafické uživatelské rozhraní (Tkinter)
├── main.py                 # Hlavní orchestrační logika online migrace (API)
├── convert.py              # Skript pro offline konverzi Excel souborů
├── api_clients.py          # HTTP klienti pro REST API Zephyr a Squash TM
├── config.py               # Načítání a validace konfigurace z .env
├── requirements.txt        # Definice knihoven (requests, openpyxl, atd.)
├── pyproject.toml          # Standardní Python balíčkování
├── Spustit_Migraci.command # macOS spouštěč (dvojklik)
├── Spustit_Migraci.bat     # Windows spouštěč (dvojklik)
├── .env.example            # Šablona konfigurace
└── migration.log           # Log průběhu migrace (generuje se automaticky)
```

---

## 🚀 Způsoby spuštění

Pro maximální jednoduchost máš k dispozici 3 možnosti spuštění:

### Možnost A: Přes grafické rozhraní (Doporučeno)
Nemusíš psát žádné příkazy do terminálu. V kořenové složce projektu stačí spustit:
* **Windows**: Dvakrát klikni na [Spustit_Migraci.bat](file:///Users/zdenekdias/Library/CloudStorage/GoogleDrive-dias.zd@gmail.com/Můj%20disk/Archiv-Projektů/zephyr-to-squash-migration/Spustit_Migraci.bat)
* **macOS**: Dvakrát klikni na [Spustit_Migraci.command](file:///Users/zdenekdias/Library/CloudStorage/GoogleDrive-dias.zd@gmail.com/Můj%20disk/Archiv-Projektů/zephyr-to-squash-migration/Spustit_Migraci.command)

Aplikace si sama vytvoří virtuální prostředí `.venv`, nainstaluje závislosti a otevře okno, kde si vybereš požadovaný režim (Online / Offline).

### Možnost B: Spuštění přes CLI (Příkazový řádek)
Nainstaluj závislosti:
```bash
pip install -r requirements.txt
```

1. **Pro přímou online migraci**:
   Zkopíruj `.env.example` do `.env`, doplň své údaje a spusť:
   ```bash
   python main.py
   ```
2. **Pro offline Excel konverzi**:
   Vyexportuj testy ze Zephyru jako Excel (detailní step-by-step šablona) a převeď ho:
   ```bash
   python convert.py --input cesta_k_exportu.xlsx --output squash_import.xlsx --project "MujSquashProjekt"
   ```
   Výsledný soubor `squash_import.xlsx` pak naimportuj přímo v rozhraní Squash TM.

### Možnost C: Instalace jako Python balíček
Nástroj můžeš nainstalovat globálně nebo do svého prostředí:
```bash
pip install .
```
Poté můžeš GUI spustit odkudkoliv z terminálu pouhým zadáním:
```bash
zephyr-to-squash
```

---

## ⚙️ Konfigurace (.env)

Pokud provádíš online migraci přes API, nakonfiguruj v `.env` následující klíče:

| Proměnná | Popis |
|---|---|
| `ZEPHYR_BASE_URL` | URL Zephyr REST API (atm/1.0) |
| `ZEPHYR_TOKEN` | Bearer token pro Zephyr Scale |
| `ZEPHYR_PROJECT_KEY` | Klíč projektu v Jira (např. `PROJ`) |
| `SQUASH_BASE_URL` | URL Squash TM REST API v1 |
| `SQUASH_USERNAME` | Uživatel pro Basic Auth |
| `SQUASH_PASSWORD` | Heslo pro Basic Auth |
| `SQUASH_PROJECT_ID` | Numerické ID projektu ve Squash TM |

---

## 🔄 Datamapa a logika migrace

1. **Složky**: Rekonstruuje stromovou strukturu ze Zephyru a rekurzivně ji založí ve Squash TM (zabraňuje duplicitním složkám).
2. **Testy**: Ověří, zda test již v cílové složce existuje (ochrana před duplicitami).
3. **Kroky**: Přidá kroky v seřazeném pořadí, přičemž pole `step_data` ze Zephyru automaticky vnoří jako součást popisu kroku.
4. **Formátování**: Texty popisů i očekávaných výsledků jsou převáděny do validního HTML formátu požadovaného Squash TM.

*Detailní informace k průběhu a struktuře naleznete v souboru logu `migration.log`.*
