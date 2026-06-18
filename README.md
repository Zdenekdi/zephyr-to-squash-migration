# Zephyr Scale ➔ Squash TM Migration Tool

Migrační nástroj pro přenos testovacích scénářů ze **Zephyr Scale** (Jira) do **Squash TM**.  
Podporuje dva režimy: **offline konverzi** (Excel → Excel) a **online migraci** přes REST API.

---

## 📥 Stažení a spuštění (Windows – nejjednodušší)

1. Stáhněte nejnovější **`ZephyrToSquash.exe`** ze [stránky Releases](https://github.com/Zdenekdi/zephyr-to-squash-migration/releases/latest)
2. Soubor spusťte poklepáním – otevře se GUI
3. Vyberte záložku **Offline Excel konverze** nebo **Online API migrace**

> Není třeba instalovat Python ani žádné závislosti.

---

## 📋 Záložka: Offline Excel konverze

Převede Zephyr Scale export (`.xlsx`) do formátu pro hromadný import do Squash TM.

### Postup

1. **Exportujte testy ze Zephyr Scale**  
   V Zephyr Scale / Jira zvolte export testovacích případů do `.xlsx`  
   (detailní šablona se stepy – každý step = jeden řádek, každý test = jeden IssueKey)

2. **Vyplňte pole v GUI:**

   | Pole | Popis | Příklad |
   |------|-------|---------|
   | Zephyr export | Vstupní `.xlsx` soubor ze Zephyru | `001.xlsx` |
   | Squash import | Výstupní soubor pro Squash TM | `squash_import.xlsx` |
   | Název projektu ve Squash | Přesný název projektu v Squash TM | `EDAZ` |
   | Cílová složka ve Squash | Název složky uvnitř projektu | `Importovane_testy` |

3. **Klikněte „Převést Excel soubor"**

4. **Importujte výsledný soubor v Squash TM:**  
   `Test Case Workspace → Import → vyberte squash_import.xlsx`

### Chování složky při importu

Složka zadaná v poli „Cílová složka" **se vytvoří automaticky** při importu do Squash TM  
(pokud ještě neexistuje). Squash TM ji odvodí z cesty `TC_PATH` v importním souboru.

Výsledná struktura v Squash TM:
```
/EDAZ
  └── Importovane_testy
        ├── Administrace_Správa blacklistu...
        ├── E-shop_hromadný nákup...
        └── ...
```

### Formát Zephyr exportu

| Sloupec Zephyr | Mapováno na Squash |
|----------------|--------------------|
| IssueKey | Zephyr key (uložen v popisu testu) |
| Summary | TC_NAME (název testu) |
| TestStep | TC_STEP_ACTION |
| ExpectedResult | TC_STEP_EXPECTED_RESULT |
| Status | TC_STATUS |
| Priority | TC_WEIGHT |
| Objective | TC_DESCRIPTION |
| Precondition | TC_PRE_REQUISITE |

> **Poznámka:** 1 test = 1 IssueKey, ale může mít více řádků (1 řádek = 1 krok).  
> Nástroj toto automaticky detekuje a seskupí kroky pod správný test.

---

## 🌐 Záložka: Online API migrace

Přímý přenos testů ze Zephyr Scale do Squash TM přes REST API.

### Předpoklady

- Přístup k **Zephyr Scale REST API** (Bearer token)
- Přístup k **Squash TM REST API** (Basic Auth – username + heslo)
- Numerické **ID projektu** ve Squash TM (zjistíte v administraci projektu)

### Vyplňte v GUI

**Zephyr Scale (Jira):**
| Pole | Popis | Příklad |
|------|-------|---------|
| URL REST API | Základní URL Zephyr API | `https://jira.firma.cz/rest/atm/1.0` |
| Bearer Token | API token ze Zephyr Scale | `eyJ0...` |
| Klíč projektu | Jira project key | `EDAZ` |

**Squash TM:**
| Pole | Popis | Příklad |
|------|-------|---------|
| URL REST API | Základní URL Squash API | `https://squash.firma.cz/squash/api/rest/v1` |
| Uživatelské jméno | Basic Auth login | `admin` |
| Heslo / Token | Basic Auth heslo | `••••••` |
| ID projektu (numerické) | Číslo projektu ve Squash | `42` |

### Co migrace provede

1. Načte strukturu složek ze Zephyru a rekurzivně ji vytvoří ve Squash TM
2. Pro každý test zkontroluje, zda v cílové složce již existuje (ochrana před duplicity)
3. Vytvoří test case a přidá kroky ve správném pořadí
4. Průběh zapisuje do `migration.log` ve složce nástroje

---

## 🖥️ Spuštění přes příkazový řádek (alternativa k `.exe`)

### Instalace závislostí

```bash
pip install -r requirements.txt
```

### Offline konverze

```bash
python convert.py \
  --input  cesta/k/zephyr_export.xlsx \
  --output squash_import.xlsx \
  --project "EDAZ" \
  --folder  "Importovane_testy"
```

### Online migrace

```bash
# 1. Vyplňte konfiguraci
cp .env.example .env
# (upravte .env dle vaší instalace)

# 2. Spusťte migraci
python main.py
```

### GUI (Python)

```bash
python gui.py
```

---

## 🏗️ Struktura projektu

```
zephyr-to-squash-migration/
├── gui.py           # Grafické uživatelské rozhraní (Tkinter)
├── main.py          # Orchestrace online migrace přes API
├── convert.py       # Offline konverze Excel → Excel
├── api_clients.py   # HTTP klienti pro Zephyr a Squash TM REST API
├── config.py        # Načítání konfigurace z .env
├── requirements.txt # Python závislosti
├── .env.example     # Šablona konfigurace pro online migraci
└── migration.log    # Log průběhu migrace (generuje se automaticky)
```

---

## ⚙️ Konfigurace (.env) – pouze pro online migraci

```env
# Zephyr Scale (Jira)
ZEPHYR_BASE_URL=https://jira.firma.cz/rest/atm/1.0
ZEPHYR_TOKEN=vas_bearer_token
ZEPHYR_PROJECT_KEY=EDAZ

# Squash TM
SQUASH_BASE_URL=https://squash.firma.cz/squash/api/rest/v1
SQUASH_USERNAME=admin
SQUASH_PASSWORD=heslo
SQUASH_PROJECT_ID=42
```

---

## 🔁 Verze

| Verze | Hlavní změny |
|-------|-------------|
| v1.2.16 | Oprava online API: stránkování složek, HAL response, rate limiting |
| v1.2.15 | UX: širší okno (1000px), větší vstupní pole, tab expand |
| v1.2.14 | **Kritická oprava:** TC_PATH nyní obsahuje celou cestu včetně jména testu |
| v1.2.13 | Info o složce přesunuto na vlastní řádek |
| v1.2.10 | TC_REFERENCE nastaven na prázdné (fix „inconsistent" chyby při reimportu) |
