import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import pandas as pd
from groq import Groq
import warnings

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────
GROQ_API_KEY = "GROQ_API_KEY"
TMDB_API_KEY = "TMDB_API_KEY"

client = Groq(api_key=GROQ_API_KEY)
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# ──────────────────────────────────────────────
#  Paleta
# ──────────────────────────────────────────────
C = {
    "bg":         "#0e0e0e",
    "surface":    "#111111",
    "input_bg":   "#161616",
    "border":     "#222222",
    "border_dim": "#1a1a1a",
    "accent":     "#c9a96e",
    "accent_dim": "#a8885a",
    "text":       "#e8e4dc",
    "subtext":    "#555555",
    "muted":      "#3a3a3a",
    "output_bg":  "#111111",
    "tag_bg":     "#1a1a1a",
    "error":      "#c0574a",
}

# ──────────────────────────────────────────────
#  Carregar dados IMDb
# ──────────────────────────────────────────────
def carregar_dados():
    try:
        df_akas    = pd.read_csv('title.akas.tsv.gz',    sep='\t', compression='gzip', nrows=1000, low_memory=False)
        df_basics  = pd.read_csv('title.basics.tsv.gz',  sep='\t', compression='gzip', nrows=1000, low_memory=False)
        df_crew    = pd.read_csv('title.crew.tsv.gz',    sep='\t', compression='gzip', nrows=1000)
        df_ratings = pd.read_csv('title.ratings.tsv.gz', sep='\t', compression='gzip', nrows=1000)
        amostra = df_basics['primaryTitle'].dropna().head(10).tolist()
        return f"Amostra de títulos no banco: {amostra}. Tabelas Akas, Crew e Ratings carregadas."
    except Exception as e:
        return f"Arquivos IMDb não encontrados: {e}"


class CineMatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CineMatch")
        self.root.geometry("700x740")
        self.root.resizable(True, True)
        self.root.configure(bg=C["bg"])
        self.root.minsize(560, 620)

        print("Carregando dados IMDb...")
        self.dados_contexto = carregar_dados()
        print("✓ Pronto.\n")

        self._build()

    # ──────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.root, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=40, pady=32)

        # ── Cabeçalho ──
        tk.Label(
            outer,
            text="CineMatch",
            font=("Georgia", 26, "bold"),
            fg=C["text"], bg=C["bg"],
        ).pack(anchor="w")

        tk.Label(
            outer,
            text="RECOMENDAÇÃO POR INTELIGÊNCIA ARTIFICIAL",
            font=("Trebuchet MS", 9),
            fg=C["subtext"], bg=C["bg"],
        ).pack(anchor="w", pady=(2, 0))

        self._divider(outer, top=14, bottom=20)

        # ── Campos ──
        self.e_ator   = self._field(outer, "ATOR / ATRIZ FAVORITO",  "ex: Cate Blanchett")
        self.e_dir    = self._field(outer, "DIRETOR(A) FAVORITO",    "ex: Alfonso Cuarón")
        self.e_filme  = self._field(outer, "FILME FAVORITO",         "ex: Clube da Luta")

        # ── Botão ──
        btn_row = tk.Frame(outer, bg=C["bg"])
        btn_row.pack(fill="x", pady=(6, 0))

        self.btn = tk.Button(
            btn_row,
            text="Recomendar",
            font=("Trebuchet MS", 12, "bold"),
            bg=C["accent"], fg="#0a0a0a",
            activebackground=C["accent_dim"],
            activeforeground="#0a0a0a",
            relief="flat", bd=0, cursor="hand2",
            command=self._on_click,
        )
        self.btn.pack(side="left", ipadx=24, ipady=10)

        self.btn_clear = tk.Button(
            btn_row,
            text="Limpar",
            font=("Trebuchet MS", 10),
            bg=C["input_bg"], fg=C["subtext"],
            activebackground=C["border"],
            activeforeground=C["text"],
            relief="flat", bd=0, cursor="hand2",
            command=self._clear,
        )
        self.btn_clear.pack(side="left", ipadx=16, ipady=10, padx=(10, 0))

        # ── Barra de progresso ──
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Gold.Horizontal.TProgressbar",
            troughcolor=C["border_dim"],
            background=C["accent"],
            thickness=2,
        )
        self.progress = ttk.Progressbar(
            outer, mode="indeterminate",
            style="Gold.Horizontal.TProgressbar",
        )

        # ── Status ──
        self.status_var = tk.StringVar(value="")
        tk.Label(
            outer,
            textvariable=self.status_var,
            font=("Trebuchet MS", 9, "italic"),
            fg=C["subtext"], bg=C["bg"], anchor="w",
        ).pack(fill="x", pady=(6, 0))

        self._divider(outer, top=14, bottom=14)

        # ── Área de resultado ──
        tk.Label(
            outer,
            text="RESULTADO",
            font=("Trebuchet MS", 9),
            fg=C["subtext"], bg=C["bg"],
        ).pack(anchor="w", pady=(0, 8))

        self.output = scrolledtext.ScrolledText(
            outer,
            font=("Trebuchet MS", 11),
            bg=C["output_bg"],
            fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=0,
            wrap="word",
            state="disabled",
            cursor="arrow",
            spacing1=3, spacing3=5,
            padx=16, pady=14,
            highlightthickness=1,
            highlightbackground=C["border_dim"],
            highlightcolor=C["border"],
        )
        self.output.pack(fill="both", expand=True)

        self.output.tag_config("loading", foreground=C["subtext"],   font=("Trebuchet MS", 11, "italic"))
        self.output.tag_config("result",  foreground=C["text"],      font=("Trebuchet MS", 11))
        self.output.tag_config("tag",     foreground=C["accent"],    font=("Trebuchet MS", 10, "bold"))
        self.output.tag_config("error",   foreground=C["error"],     font=("Trebuchet MS", 11))
        self.output.tag_config("label",   foreground=C["subtext"],   font=("Trebuchet MS", 9))

        # ── Rodapé ──
        tk.Label(
            outer,
            text="Groq · LLaMA 3.1 · IMDb",
            font=("Trebuchet MS", 8),
            fg=C["muted"], bg=C["bg"],
        ).pack(pady=(10, 0))

        self.e_ator.focus_set()

    def _field(self, parent, label_txt, placeholder):
        """Cria label + entry estilizado."""
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x", pady=(0, 14))

        tk.Label(
            wrap,
            text=label_txt,
            font=("Trebuchet MS", 9),
            fg=C["subtext"], bg=C["bg"],
        ).pack(anchor="w", pady=(0, 5))

        container = tk.Frame(
            wrap,
            bg=C["input_bg"],
            highlightbackground=C["border"],
            highlightthickness=1,
        )
        container.pack(fill="x")

        entry = tk.Entry(
            container,
            font=("Trebuchet MS", 12),
            bg=C["input_bg"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=0,
        )
        entry.pack(fill="x", ipady=9, padx=12)
        entry.bind("<Return>", lambda e: self._on_click())

        # Placeholder
        entry.insert(0, placeholder)
        entry.config(fg=C["muted"])

        def on_focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.config(fg=C["text"])

        def on_focus_out(e):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(fg=C["muted"])

        def on_focus_border(e):
            container.config(highlightbackground=C["accent"])

        def off_focus_border(e):
            container.config(highlightbackground=C["border"])

        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusIn>",  on_focus_border, add="+")
        entry.bind("<FocusOut>", on_focus_out)
        entry.bind("<FocusOut>", off_focus_border, add="+")

        entry._placeholder = placeholder
        return entry

    def _divider(self, parent, top=8, bottom=8):
        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", pady=(top, bottom)
        )

    # ──────────────────────────────────────────
    #  Ações
    # ──────────────────────────────────────────
    def _get_val(self, entry):
        v = entry.get().strip()
        return "" if v == entry._placeholder else v

    def _on_click(self):
        ator   = self._get_val(self.e_ator)
        diretor = self._get_val(self.e_dir)
        filme  = self._get_val(self.e_filme)

        if not (ator or diretor or filme):
            self._write([("⚠  Preencha ao menos um campo.", "error")])
            return

        self.btn.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.start(10)
        self.status_var.set("  Analisando padrões...")

        self._write([("✦  Gerando recomendações...", "loading")])

        threading.Thread(
            target=self._worker,
            args=(ator, diretor, filme),
            daemon=True,
        ).start()

    def _worker(self, ator, diretor, filme):
        prompt = f"""
Você é um sistema de recomendação. O usuário gosta de:
- Ator: {ator or '(não informado)'}
- Diretor: {diretor or '(não informado)'}
- Filme: {filme or '(não informado)'}

Contexto banco de dados: {self.dados_contexto}

Recomende 3 filmes na mesma vibe. Explique em 1 ou 2 linhas o porquê de cada.
"""
        try:
            resposta = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
            )
            texto = resposta.choices[0].message.content
            self.root.after(0, lambda: self._finish(texto, ator, diretor, filme))
        except Exception as e:
            self.root.after(0, lambda: self._finish(None, error=str(e)))

    def _finish(self, texto, ator="", diretor="", filme="", error=None):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_var.set("")
        self.btn.configure(state="normal")
        self.btn_clear.configure(state="normal")

        if error:
            self._write([(f"❌  Erro na API: {error}", "error")])
            return

        segments = []
        if ator:    segments.append((f"🎭 {ator}   ", "tag"))
        if diretor: segments.append((f"🎬 {diretor}   ", "tag"))
        if filme:   segments.append((f"🎞 {filme}", "tag"))
        if segments:
            segments.append(("\n\n", "label"))
        segments.append((texto, "result"))

        self._write(segments)
        self.e_ator.focus_set()

    def _write(self, segments):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        for text, tag in segments:
            self.output.insert("end", text, tag)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _clear(self):
        self._write([])
        self.status_var.set("")
        for entry in [self.e_ator, self.e_dir, self.e_filme]:
            entry.delete(0, "end")
            entry.insert(0, entry._placeholder)
            entry.config(fg=C["muted"])
        self.e_ator.focus_set()


# ──────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = CineMatchApp(root)
    root.mainloop()