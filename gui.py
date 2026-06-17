#!/usr/bin/env python3
"""
gui.py
------
Grafické uživatelské rozhraní (GUI) pro Zephyr → Squash TM migraci.
Umožňuje spouštět jak online API migraci, tak offline Excel konverzi.
"""

import os
import sys
import subprocess
import threading
import queue
import traceback

# --- Bezpečný import tkinter ---
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError as e:
    print(f"CHYBA: Nepodařilo se načíst tkinter: {e}")
    print("Ujistěte se, že máte nainstalovaný Python s podporou tkinter.")
    sys.exit(1)

# --- Bezpečný import tkinterdnd2 (drag & drop) ---
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    TKDND_AVAILABLE = True
except ImportError:
    TKDND_AVAILABLE = False

# --- Bezpečný import dotenv ---
try:
    from dotenv import load_dotenv, set_key
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

    def load_dotenv(*args, **kwargs):
        pass  # No-op fallback

    def set_key(*args, **kwargs):
        pass  # No-op fallback

# --------------------------------------------------------------------------- #
# Detekce frozen (PyInstaller .exe) vs. běžný Python režim               #
# --------------------------------------------------------------------------- #
IS_FROZEN = getattr(sys, "frozen", False)

# Při frozen režimu importujeme logiku přímo (subprocess nefunguje v .exe)
if IS_FROZEN:
    try:
        import convert as _convert_module
    except ImportError:
        _convert_module = None
    try:
        import main as _main_module
    except ImportError:
        _main_module = None

# --------------------------------------------------------------------------- #
# Barevné téma (Premium Dark Mode)                                            #
# --------------------------------------------------------------------------- #
BG_MAIN = "#1a1a22"       # Hlavní pozadí okna
BG_CARD = "#242430"       # Pozadí karet a formulářů
BG_INPUT = "#323242"      # Pozadí vstupních polí
FG_TEXT = "#e2e2e9"       # Hlavní barva textu
FG_MUTED = "#8c8ca3"      # Mírně tlumený text
COLOR_ACCENT = "#3b82f6"   # Akcentní modrá pro tlačítka
COLOR_SUCCESS = "#10b981"  # Zelená pro úspěch/start
COLOR_BORDER = "#2f2f3e"   # Ohraničení prvků
BG_CONSOLE = "#111116"     # Pozadí terminálu
FG_CONSOLE = "#a7f3d0"     # Text terminálu (mentolová/světle zelená)

# Výběr fontu – Segoe UI je dostupný na Windows, jinak fallback
FONT_MAIN = "Segoe UI" if sys.platform == "win32" else "Arial"


class MigrationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zephyr Scale ➔ Squash TM Migration Tool")
        self.root.geometry("850x750")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)

        # Fronta pro předávání zpráv ze subprocesu do GUI vlákna
        self.log_queue = queue.Queue()
        self.running_process = None

        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.env_path = os.path.join(self.project_dir, ".env")
        load_dotenv(self.env_path)

        # Nastavení stylů ttk
        self.setup_styles()
        # Vytvoření komponent rozhraní
        self.create_widgets()

        # Periodické čtení z logovací fronty
        self.root.after(100, self.poll_log_queue)

        # Upozornění pokud python-dotenv chybí
        if not DOTENV_AVAILABLE:
            self.root.after(500, lambda: messagebox.showwarning(
                "Chybějící balíček",
                "Balíček 'python-dotenv' není nainstalovaný.\n"
                "Předvyplnění z .env souboru nebude fungovat.\n\n"
                "Spusťte: pip install python-dotenv"
            ))

    def setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # Fallback pokud "clam" není dostupný

        # Konfigurace základních elementů
        style.configure(".", bg=BG_MAIN, fg=FG_TEXT, font=(FONT_MAIN, 10))

        # Notebook (Záložky)
        style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=FG_MUTED,
                        borderwidth=1, bordercolor=COLOR_BORDER, padding=(12, 6),
                        font=(FONT_MAIN, 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_MAIN)],
                  foreground=[("selected", COLOR_ACCENT)])

        # Tlačítka
        style.configure("TButton", background=COLOR_ACCENT, foreground="#ffffff",
                        borderwidth=0, padding=(12, 6), font=(FONT_MAIN, 10, "bold"))
        style.map("TButton", background=[("active", "#2563eb")])

        style.configure("Success.TButton", background=COLOR_SUCCESS, foreground="#ffffff",
                        borderwidth=0, padding=(12, 6), font=(FONT_MAIN, 10, "bold"))
        style.map("Success.TButton", background=[("active", "#059669")])

        # Popisky a labely
        style.configure("TLabel", background=BG_CARD, foreground=FG_TEXT)
        style.configure("Header.TLabel", background=BG_CARD, foreground=FG_TEXT,
                        font=(FONT_MAIN, 12, "bold"))
        style.configure("Sub.TLabel", background=BG_MAIN, foreground=FG_MUTED,
                        font=(FONT_MAIN, 9))

    def create_widgets(self):
        # Hlavní kontejner
        main_frame = tk.Frame(self.root, bg=BG_MAIN)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Hlavička aplikace
        header_frame = tk.Frame(main_frame, bg=BG_MAIN)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = tk.Label(
            header_frame,
            text="Zephyr Scale ➔ Squash TM Migration Tool",
            bg=BG_MAIN, fg="#ffffff",
            font=(FONT_MAIN, 16, "bold")
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            header_frame,
            text="Migrační nástroj pro přenos testovacích scénářů přes REST API nebo offline Excel konverzi.",
            style="Sub.TLabel"
        )
        subtitle_label.pack(anchor=tk.W)

        # Záložky (Notebook)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.configure(height=330)  # height patří do configure(), ne pack()
        self.notebook.pack(fill=tk.BOTH, expand=False)

        # Vytvoření jednotlivých záložek
        self.tab_online = tk.Frame(self.notebook, bg=BG_CARD,
                                   highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.tab_offline = tk.Frame(self.notebook, bg=BG_CARD,
                                    highlightbackground=COLOR_BORDER, highlightthickness=1)

        self.notebook.add(self.tab_online, text=" Online API migrace ")
        self.notebook.add(self.tab_offline, text=" Offline Excel konverze ")

        # Naplnění záložek
        self.setup_online_tab()
        self.setup_offline_tab()

        # Spodní část - Výstup logů (Konzole)
        console_frame = tk.Frame(main_frame, bg=BG_MAIN)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        console_header = tk.Label(
            console_frame,
            text="Výstup logů (Průběh migrace):",
            bg=BG_MAIN, fg=FG_TEXT,
            font=(FONT_MAIN, 10, "bold")
        )
        console_header.pack(anchor=tk.W, pady=(0, 5))

        # Textbox pro logy
        self.log_text = tk.Text(
            console_frame,
            bg=BG_CONSOLE, fg=FG_CONSOLE,
            insertbackground="#ffffff",
            font=("Courier New", 9),
            wrap=tk.WORD,
            borderwidth=1, relief=tk.FLAT
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar pro logy
        scrollbar = ttk.Scrollbar(console_frame, orient=tk.VERTICAL,
                                  command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # Tlačítka pro správu logu a zastavení
        ctrl_frame = tk.Frame(main_frame, bg=BG_MAIN)
        ctrl_frame.pack(fill=tk.X, pady=(10, 0))

        self.btn_stop = ttk.Button(ctrl_frame, text="Zastavit proces",
                                   command=self.stop_process, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 10))

        btn_clear = ttk.Button(ctrl_frame, text="Vyčistit log",
                               command=self.clear_logs)
        btn_clear.pack(side=tk.LEFT)

    def setup_online_tab(self):
        # Mřížka s formulářem
        form_frame = tk.Frame(self.tab_online, bg=BG_CARD, padx=15, pady=15)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Nastavení šířky sloupců
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        # --- ZEPHYR SEKCE ---
        lbl_zephyr = ttk.Label(form_frame, text="Nastavení Zephyr Scale (Jira)",
                                style="Header.TLabel")
        lbl_zephyr.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        self.add_field(form_frame, "ZEPHYR_BASE_URL", "URL REST API:", 1, 0,
                       default="https://jira.example.com/rest/atm/1.0")
        self.add_field(form_frame, "ZEPHYR_TOKEN", "Bearer Token:", 2, 0,
                       is_password=True)
        self.add_field(form_frame, "ZEPHYR_PROJECT_KEY", "Klíč projektu:", 3, 0,
                       default="PROJ")

        # --- SQUASH SEKCE ---
        lbl_squash = ttk.Label(form_frame, text="Nastavení Squash TM",
                                style="Header.TLabel")
        lbl_squash.grid(row=0, column=2, columnspan=2, sticky=tk.W,
                        pady=(0, 10), padx=(20, 0))

        self.add_field(form_frame, "SQUASH_BASE_URL", "URL REST API:", 1, 2,
                       default="https://squash.example.com/squash/api/rest/v1",
                       pad_x=20)
        self.add_field(form_frame, "SQUASH_USERNAME", "Uživatelské jméno:", 2, 2,
                       pad_x=20)
        self.add_field(form_frame, "SQUASH_PASSWORD", "Heslo / Token:", 3, 2,
                       is_password=True, pad_x=20)
        self.add_field(form_frame, "SQUASH_PROJECT_ID", "ID projektu (numerické):",
                       4, 2, pad_x=20)

        # Tlačítko start
        btn_start_online = ttk.Button(
            form_frame, text="Spustit API migraci",
            style="Success.TButton", command=self.run_online_migration
        )
        btn_start_online.grid(row=5, column=0, columnspan=4,
                              pady=(20, 0), sticky=tk.E)

    def setup_offline_tab(self):
        form_frame = tk.Frame(self.tab_offline, bg=BG_CARD, padx=15, pady=15)
        form_frame.pack(fill=tk.BOTH, expand=True)

        form_frame.columnconfigure(1, weight=1)

        lbl_offline = ttk.Label(form_frame, text="Offline konverze souborů",
                                 style="Header.TLabel")
        lbl_offline.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        # Vstupní soubor
        dnd_hint = " (nebo sem přetáhněte soubor)" if TKDND_AVAILABLE else ""
        ttk.Label(form_frame, text=f"Zephyr export (.xlsx){dnd_hint}:").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.entry_input_file = tk.Entry(
            form_frame, bg=BG_INPUT, fg=FG_TEXT,
            insertbackground="#ffffff", borderwidth=0,
            highlightthickness=1, highlightcolor=COLOR_ACCENT,
            highlightbackground=COLOR_BORDER
        )
        self.entry_input_file.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)
        btn_browse_in = ttk.Button(form_frame, text="Procházet...",
                                   command=self.browse_input_file)
        btn_browse_in.grid(row=1, column=2, pady=5)

        # Registrace drag & drop na vstupní pole
        if TKDND_AVAILABLE:
            self.entry_input_file.drop_target_register(DND_FILES)
            self.entry_input_file.dnd_bind("<<Drop>>", self._on_drop_input_file)
            self.entry_input_file.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.entry_input_file.dnd_bind("<<DragLeave>>", self._on_drag_leave)

        # Výstupní soubor
        ttk.Label(form_frame, text="Squash import (.xlsx):").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.entry_output_file = tk.Entry(
            form_frame, bg=BG_INPUT, fg=FG_TEXT,
            insertbackground="#ffffff", borderwidth=0,
            highlightthickness=1, highlightcolor=COLOR_ACCENT,
            highlightbackground=COLOR_BORDER
        )
        self.entry_output_file.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)
        self.entry_output_file.insert(0, "squash_import.xlsx")
        btn_browse_out = ttk.Button(form_frame, text="Uložit jako...",
                                    command=self.browse_output_file)
        btn_browse_out.grid(row=2, column=2, pady=5)

        # Název projektu Squash
        ttk.Label(form_frame, text="Název projektu ve Squash:").grid(
            row=3, column=0, sticky=tk.W, pady=5)
        self.entry_proj_name = tk.Entry(
            form_frame, bg=BG_INPUT, fg=FG_TEXT,
            insertbackground="#ffffff", borderwidth=0,
            highlightthickness=1, highlightcolor=COLOR_ACCENT,
            highlightbackground=COLOR_BORDER
        )
        self.entry_proj_name.grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)
        default_proj = os.getenv("ZEPHYR_PROJECT_KEY") or "Imported_Project"
        self.entry_proj_name.insert(0, default_proj)

        # Tlačítko start
        btn_start_offline = ttk.Button(
            form_frame, text="Převést Excel soubor",
            style="Success.TButton", command=self.run_offline_conversion
        )
        btn_start_offline.grid(row=4, column=0, columnspan=3,
                               pady=(30, 0), sticky=tk.E)

    # --------------------------------------------------------------------------- #
    # Pomocné metody pro formuláře                                                #
    # --------------------------------------------------------------------------- #
    def add_field(self, parent, env_key, label_text, row, col,
                  default="", is_password=False, pad_x=0):
        # Popisek
        lbl = ttk.Label(parent, text=label_text)
        lbl.grid(row=row, column=col, sticky=tk.W, pady=6, padx=(pad_x, 10))

        # Vstupní pole
        show_char = "*" if is_password else None
        entry = tk.Entry(
            parent, show=show_char,
            bg=BG_INPUT, fg=FG_TEXT,
            insertbackground="#ffffff", borderwidth=0,
            highlightthickness=1, highlightcolor=COLOR_ACCENT,
            highlightbackground=COLOR_BORDER
        )
        entry.grid(row=row, column=col + 1, sticky=tk.EW, pady=6)

        # Předvyplnění hodnoty (z .env nebo default)
        val = os.getenv(env_key) or default
        if val:
            entry.insert(0, val)

        # Uložíme referenci
        if not hasattr(self, "form_entries"):
            self.form_entries = {}
        self.form_entries[env_key] = entry

    def browse_input_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if path:
            self.entry_input_file.delete(0, tk.END)
            self.entry_input_file.insert(0, path)

    def _on_drop_input_file(self, event):
        """Handler pro drag & drop souboru na vstupní pole."""
        path = event.data.strip()
        # tkinterdnd2 zabaluje cesty s mezerami do složených závorek
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        # Odebereme případné uvozovky
        path = path.strip('"')
        self.entry_input_file.configure(highlightbackground=COLOR_BORDER)
        self.entry_input_file.delete(0, tk.END)
        self.entry_input_file.insert(0, path)
        return event.action

    def _on_drag_enter(self, event):
        """Vizuální feedback při najetí souboru nad pole."""
        self.entry_input_file.configure(highlightbackground=COLOR_ACCENT,
                                        highlightthickness=2)
        return event.action

    def _on_drag_leave(self, event):
        """Reset vizuálního feedbacku po opuštění pole."""
        self.entry_input_file.configure(highlightbackground=COLOR_BORDER,
                                        highlightthickness=1)

    def browse_output_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if path:
            self.entry_output_file.delete(0, tk.END)
            self.entry_output_file.insert(0, path)

    # --------------------------------------------------------------------------- #
    # Spouštění procesů na pozadí                                                 #
    # --------------------------------------------------------------------------- #
    def save_env_values(self):
        """Uloží aktuální hodnoty z online formuláře do souboru .env."""
        if not DOTENV_AVAILABLE:
            self.log_to_console("[GUI INFO] python-dotenv není dostupný, .env se neukládá.\n")
            return
        try:
            # Vytvoříme .env soubor pokud neexistuje
            if not os.path.exists(self.env_path):
                with open(self.env_path, "w", encoding="utf-8") as f:
                    f.write("# Zephyr to Squash TM configuration\n")

            for key, entry in self.form_entries.items():
                val = entry.get().strip()
                set_key(self.env_path, key, val)
        except Exception as e:
            self.log_to_console(
                f"[GUI ERROR] Nepodařilo se uložit konfiguraci do .env: {e}\n"
            )

    def run_online_migration(self):
        if self.running_process:
            messagebox.showwarning(
                "Varování",
                "Nějaký proces již běží. Nejprve jej dokončete nebo zastavte."
            )
            return

        self.save_env_values()
        self.clear_logs()
        self.log_to_console(">>> Startuji online API migraci...\n")
        self.btn_stop.configure(state=tk.NORMAL)

        if IS_FROZEN and _main_module:
            # .exe režim: voláme main() přímo s přesměrováním stdout
            threading.Thread(
                target=self._run_frozen_module,
                args=(_main_module, "main", []),
                daemon=True
            ).start()
        else:
            # Python režim: spustíme jako subprocess
            cmd = [sys.executable, os.path.join(self.project_dir, "main.py")]
            threading.Thread(target=self.execute_subprocess, args=(cmd,),
                             daemon=True).start()

    def run_offline_conversion(self):
        if self.running_process:
            messagebox.showwarning("Varování", "Nějaký proces již běží.")
            return

        in_file = self.entry_input_file.get().strip()
        out_file = self.entry_output_file.get().strip()
        proj_name = self.entry_proj_name.get().strip()

        if not in_file:
            messagebox.showerror("Chyba", "Vyberte vstupní soubor ze Zephyru.")
            return
        if not out_file:
            out_file = "squash_import.xlsx"

        self.clear_logs()
        self.log_to_console(">>> Startuji offline konverzi Excel souboru...\n")
        self.btn_stop.configure(state=tk.NORMAL)

        if IS_FROZEN and _convert_module:
            # .exe režim: voláme parse + write přímo v threadu
            threading.Thread(
                target=self._run_frozen_conversion,
                args=(in_file, out_file, proj_name),
                daemon=True
            ).start()
        else:
            # Python režim: subprocess
            cmd = [
                sys.executable, os.path.join(self.project_dir, "convert.py"),
                "-i", in_file, "-o", out_file, "-p", proj_name
            ]
            threading.Thread(target=self.execute_subprocess, args=(cmd,),
                             daemon=True).start()

    def _run_frozen_conversion(self, in_file, out_file, proj_name):
        """Spustí konverzi přímo (frozen .exe režim) s přesměrováním výpisů."""
        import io
        old_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(
            io.BytesIO(), encoding="utf-8", errors="replace", line_buffering=True
        )
        # Nahradíme stdout vlastním write, který posílá řádky do fronty
        class QueueWriter:
            def __init__(self, q):
                self.q = q
                self.buf = ""
            def write(self, text):
                self.buf += text
                while "\n" in self.buf:
                    line, self.buf = self.buf.split("\n", 1)
                    self.q.put(line + "\n")
            def flush(self):
                if self.buf:
                    self.q.put(self.buf)
                    self.buf = ""
        sys.stdout = QueueWriter(self.log_queue)
        try:
            test_cases = _convert_module.parse_zephyr_excel(in_file)
            if not test_cases:
                self.log_queue.put("Chyba: V souboru nebyly nalezeny žádné testovací případy.\n")
            else:
                _convert_module.write_squash_excel(test_cases, out_file, proj_name)
                self.log_queue.put("\n>>> HOTOVO: Soubor uspěšně uložen.\n")
                self.log_queue.put(f">>> Soubor: {os.path.abspath(out_file)}\n")
        except Exception as e:
            import traceback
            self.log_queue.put(f"\n>>> CHYBA: {e}\n")
            self.log_queue.put(traceback.format_exc())
        finally:
            sys.stdout = old_stdout
            self.log_queue.put("__PROCESS_FINISHED__")

    def _run_frozen_module(self, module, func_name, args):
        """Spustí libovolnou funkci modulu s přesměrováním stdout."""
        import io
        old_stdout = sys.stdout
        class QueueWriter:
            def __init__(self, q):
                self.q = q
                self.buf = ""
            def write(self, text):
                self.buf += text
                while "\n" in self.buf:
                    line, self.buf = self.buf.split("\n", 1)
                    self.q.put(line + "\n")
            def flush(self):
                if self.buf:
                    self.q.put(self.buf)
                    self.buf = ""
        sys.stdout = QueueWriter(self.log_queue)
        try:
            fn = getattr(module, func_name)
            fn(*args)
            self.log_queue.put("\n>>> HOTOVO (Exit code 0).\n")
        except Exception as e:
            import traceback
            self.log_queue.put(f"\n>>> CHYBA: {e}\n")
            self.log_queue.put(traceback.format_exc())
        finally:
            sys.stdout = old_stdout
            self.log_queue.put("__PROCESS_FINISHED__")

    def execute_subprocess(self, cmd):
        try:
            # Nastavení kódování pro Windows
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"

            # Na Windows skryjeme konzolové okno subprocesu
            popen_kwargs = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=self.project_dir,
                env=env,
            )
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.running_process = subprocess.Popen(cmd, **popen_kwargs)

            # Čteme výstup řádek po řádku
            for line in iter(self.running_process.stdout.readline, ""):
                self.log_queue.put(line)

            self.running_process.stdout.close()
            return_code = self.running_process.wait()

            if return_code == 0:
                self.log_queue.put("\n>>> HOTOVO: Proces skončil úspěšně (Exit code 0).\n")
            else:
                self.log_queue.put(
                    f"\n>>> CHYBA: Proces skončil s chybou (Exit code {return_code}).\n"
                )

        except Exception as e:
            self.log_queue.put(f"\n>>> NEOČEKÁVANÁ CHYBA: {e}\n")
        finally:
            self.running_process = None
            self.log_queue.put("__PROCESS_FINISHED__")

    def stop_process(self):
        if self.running_process:
            if messagebox.askyesno("Zrušit", "Opravdu chcete běžící migraci zastavit?"):
                self.running_process.terminate()
                self.log_to_console("\n[Zrušeno uživatelem]\n")
                self.btn_stop.configure(state=tk.DISABLED)

    # --------------------------------------------------------------------------- #
    # Logování do konzole v GUI vlákně                                            #
    # --------------------------------------------------------------------------- #
    def log_to_console(self, msg):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def clear_logs(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def poll_log_queue(self):
        """Metoda volaná periodicky v hlavním vlákně pro vyzvednutí logů ze subprocesu."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__PROCESS_FINISHED__":
                    self.btn_stop.configure(state=tk.DISABLED)
                else:
                    self.log_to_console(msg)
                self.log_queue.task_done()
        except queue.Empty:
            pass
        finally:
            # Naplánovat další kontrolu za 100 ms
            self.root.after(100, self.poll_log_queue)


def main():
    try:
        # Použijeme TkinterDnD.Tk() pokud je dostupné (podporuje drag & drop)
        if TKDND_AVAILABLE:
            root = TkinterDnD.Tk()
        else:
            root = tk.Tk()
        app = MigrationGUI(root)
        root.mainloop()
    except Exception as e:
        # Pokud se okno nepodaří spustit, vypíšeme chybu do konzole
        error_msg = traceback.format_exc()
        print(f"\n=== KRITICKÁ CHYBA ===\n{error_msg}")
        try:
            # Pokusíme se zobrazit chybové okno
            import tkinter.messagebox as mb
            mb.showerror("Kritická chyba", f"Aplikaci se nepodařilo spustit:\n\n{e}")
        except Exception:
            pass
        try:
            # input() nefunguje v .exe bez konzole (lost sys.stdin) – ignorujeme
            input("\nStiskněte Enter pro zavření...")
        except (EOFError, RuntimeError, OSError):
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
