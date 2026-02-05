import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import threading
import requests
import os
import sys
import subprocess
import pandas as pd
from PIL import Image

# Importa módulos locais
from config import CONFIG
from models.stock_manager import StockManager
from services.image_manager import ImageManager
from services.report_manager import ReportManager

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Inicializa Gerenciadores
        self.stock = StockManager()
        self.img_mgr = ImageManager()
        self.rep_mgr = ReportManager()
        
        # CACHE DE IMAGENS: Impede o erro pyimage e melhora performance
        self.image_cache = {}
        
        # Configuração UI
        ctk.set_appearance_mode(CONFIG["THEME"])
        ctk.set_default_color_theme(CONFIG["COLOR"])
        self.title(f"Sistema Estoque RS - v{CONFIG['VERSION']}")
        self.geometry("1200x800")
        
        self.selected_item_name = None
        
        self._setup_layout()
        
        # Thread de Update
        self.after(2000, lambda: threading.Thread(target=self._check_update_silent, daemon=True).start())

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="ESTOQUE RS", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(30,10))
        
        # Foto do Produto
        self.frm_photo = ctk.CTkFrame(self.sidebar, width=180, fg_color="transparent")
        self.frm_photo.pack(pady=10)
        self.lbl_photo = ctk.CTkLabel(self.frm_photo, text="[Sem Foto]", width=180, height=180, fg_color="gray20", corner_radius=10)
        self.lbl_photo.pack()
        
        # Botões de Foto
        self.btn_photo = ctk.CTkButton(self.frm_photo, text="📷 Alterar Foto", width=180, height=25, fg_color="#444", state="disabled", command=self.action_upload_photo)
        self.btn_photo.pack(pady=(5, 2))
        
        self.btn_remove_photo = ctk.CTkButton(self.frm_photo, text="🗑️ Remover Foto", width=180, height=25, fg_color="transparent", text_color="#e74c3c", hover_color="#331111", state="disabled", command=self.action_remove_photo)
        self.btn_remove_photo.pack(pady=2)

        # Menu
        self._create_btn("📂 Abrir Excel", self.action_load)
        self._create_btn("➕ Novo Item", self.action_new_item)
        self._create_btn("🗑️ Excluir Item", self.action_delete, color="#e74c3c", hover="#5a1e1e")
        self._create_btn("📜 Histórico", self.action_history)
        self._create_btn("📄 Relatórios", self.action_reports, color="#f39c12", hover="#5c3c00")
        self._create_btn("🔄 Update", self.action_check_update_manual, color="#34495e")
        
        self.btn_save = ctk.CTkButton(self.sidebar, text="💾 SALVAR TUDO", height=50, fg_color="#27ae60", hover_color="#219150", font=ctk.CTkFont(weight="bold"), command=self.action_save)
        self.btn_save.pack(pady=20, padx=20, side="bottom")

        # --- ÁREA PRINCIPAL ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure((0,1), weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Cards e Filtros (Omitidos para brevidade, mas mantidos na lógica real)
        self.card_c = self._create_card("ESTOQUE CANOAS", "#1f538d", 0, 0)
        self.card_pf = self._create_card("ESTOQUE PASSO FUNDO", "#d35400", 0, 1)
        self.lbl_tot_c = self.card_c.winfo_children()[1]
        self.lbl_tot_pf = self.card_pf.winfo_children()[1]

        self.frm_filter = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frm_filter.grid(row=1, column=0, columnspan=2, pady=(15,5), sticky="ew")
        self.var_filter = ctk.StringVar(value="Todos")
        ctk.CTkOptionMenu(self.frm_filter, width=150, values=["Todos", "Saldo Canoas", "Zero Canoas", "Saldo PF", "Zero PF"], variable=self.var_filter, command=lambda x: self.update_table()).pack(side="left", padx=(0,10))
        self.entry_search = ctk.CTkEntry(self.frm_filter, placeholder_text="🔍 Pesquisar produto...", height=35)
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", lambda x: self.update_table())

        # Tabela
        self.frm_table = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frm_table.grid(row=2, column=0, columnspan=2, sticky="nsew")
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, font=("Segoe UI", 10), rowheight=30)
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[('selected', '#2980b9')])

        self.scroll = ctk.CTkScrollbar(self.frm_table)
        self.scroll.pack(side="right", fill="y")
        self.tree = ttk.Treeview(self.frm_table, columns=("ID","NOME","C","PF"), show="headings", yscrollcommand=self.scroll.set)
        self.scroll.configure(command=self.tree.yview)
        
        self.tree.heading("ID", text="#"); self.tree.column("ID", width=50, anchor="center")
        self.tree.heading("NOME", text="PRODUTO"); self.tree.column("NOME", width=500)
        self.tree.heading("C", text="CANOAS"); self.tree.column("C", width=100, anchor="center")
        self.tree.heading("PF", text="PF"); self.tree.column("PF", width=100, anchor="center")
        
        self.tree.tag_configure('positivo', foreground='#2ecc71')
        self.tree.tag_configure('zerado', foreground='#e74c3c')
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Painel Ações
        self.frm_actions = ctk.CTkFrame(self, height=120, corner_radius=15, fg_color="#2b2b2b")
        self.frm_actions.grid(row=1, column=1, sticky="ew", padx=20, pady=(0,20))
        self.lbl_sel = ctk.CTkLabel(self.frm_actions, text="Selecione um item...", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_sel.pack(pady=5)
        self.frm_ctrl = ctk.CTkFrame(self.frm_actions, fg_color="transparent")
        self.frm_ctrl.pack(pady=5)
        self.var_op = ctk.StringVar(value="Saida")
        ctk.CTkRadioButton(self.frm_ctrl, text="Baixa", variable=self.var_op, value="Saida", command=self._adjust_ui, fg_color="#e74c3c").pack(side="left", padx=10)
        ctk.CTkRadioButton(self.frm_ctrl, text="Entrada", variable=self.var_op, value="Entrada", command=self._adjust_ui, fg_color="#27ae60").pack(side="left", padx=10)
        ctk.CTkRadioButton(self.frm_ctrl, text="Transf", variable=self.var_op, value="Transferencia", command=self._adjust_ui, fg_color="#f39c12").pack(side="left", padx=10)
        self.var_loc = ctk.StringVar(value="Canoas")
        self.cmb_loc = ctk.CTkComboBox(self.frm_ctrl, values=["Canoas", "Passo Fundo"], variable=self.var_loc)
        self.cmb_loc.pack(side="left", padx=10)
        self.var_transf = ctk.StringVar(value="Canoas -> PF")
        self.cmb_transf = ctk.CTkComboBox(self.frm_ctrl, values=["Canoas -> PF", "PF -> Canoas"], variable=self.var_transf)
        self.entry_qty = ctk.CTkEntry(self.frm_ctrl, width=60, justify="center"); self.entry_qty.insert(0, "1")
        self.entry_qty.pack(side="left", padx=5)
        self.btn_ok = ctk.CTkButton(self.frm_ctrl, text="CONFIRMAR", width=100, fg_color="#e74c3c", command=self.action_process)
        self.btn_ok.pack(side="left", padx=15)

    def _create_btn(self, txt, cmd, color="transparent", hover=None):
        btn = ctk.CTkButton(self.sidebar, text=txt, height=35, fg_color=color, border_width=2 if color=="transparent" else 0, command=cmd)
        if hover: btn.configure(hover_color=hover)
        btn.pack(pady=5, padx=20)
        return btn

    def _create_card(self, title, color, r, c):
        f = ctk.CTkFrame(self.main_frame, fg_color=color, height=80)
        f.grid(row=r, column=c, padx=(0 if c==0 else 10, 10 if c==0 else 0), sticky="ew")
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(weight="bold")).pack(pady=(10,0))
        ctk.CTkLabel(f, text="0", font=ctk.CTkFont(size=30, weight="bold")).pack(pady=(0,10))
        return f

    # --- LÓGICA DE IMAGEM ---
    def _display_product_image(self, item_name):
        self.lbl_photo.configure(image="", text="Carregando...")
        
        if item_name in self.image_cache:
            self.lbl_photo.configure(image=self.image_cache[item_name], text="")
            self.btn_remove_photo.configure(state="normal")
            return

        path = self.img_mgr.find_image_path(item_name)
        if path:
            try:
                pil_img = Image.open(path)
                pil_img.thumbnail((180, 180))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self.image_cache[item_name] = ctk_img
                self.lbl_photo.configure(image=ctk_img, text="")
                self.btn_remove_photo.configure(state="normal")
            except:
                self.lbl_photo.configure(image="", text="Erro Foto")
                self.btn_remove_photo.configure(state="disabled")
        else:
            self.lbl_photo.configure(image="", text="[Sem Foto]")
            self.btn_remove_photo.configure(state="disabled")

    # --- EVENTOS ---
    def _on_select(self, e):
        sel = self.tree.selection()
        if sel:
            name = self.tree.item(sel[0])['values'][1]
            self.selected_item_name = name
            self.lbl_sel.configure(text=f"Selecionado: {name}", text_color="#3498db")
            self.btn_photo.configure(state="normal")
            self._display_product_image(name)
        else:
            self.selected_item_name = None
            self.lbl_sel.configure(text="Selecione um item...", text_color="white")
            self.btn_photo.configure(state="disabled")
            self.btn_remove_photo.configure(state="disabled")
            self.lbl_photo.configure(image="", text="[Sem Foto]")

    def action_upload_photo(self):
        if not self.selected_item_name: return
        path = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg *.jpeg *.png")])
        if path:
            try:
                self.img_mgr.save_image(path, self.selected_item_name)
                if self.selected_item_name in self.image_cache:
                    del self.image_cache[self.selected_item_name]
                self._display_product_image(self.selected_item_name)
                messagebox.showinfo("Sucesso", "Foto salva!")
            except Exception as e: messagebox.showerror("Erro", str(e))

    def action_remove_photo(self):
        """Desvincula e apaga a foto do item selecionado."""
        if not self.selected_item_name: return
        
        if messagebox.askyesno("Confirmar", f"Deseja remover permanentemente a foto de:\n{self.selected_item_name}?"):
            try:
                # 1. Apaga do HD
                self.img_mgr.delete_image(self.selected_item_name)
                
                # 2. Limpa o Cache
                if self.selected_item_name in self.image_cache:
                    del self.image_cache[self.selected_item_name]
                
                # 3. Atualiza UI
                self._display_product_image(self.selected_item_name)
                messagebox.showinfo("Sucesso", "Foto removida com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível remover a foto: {e}")

    # --- RESTANTE DAS FUNÇÕES (Filtros, Processamento, etc.) ---
    def update_table(self):
        if self.stock.df is None: return
        self.tree.delete(*self.tree.get_children())
        term = self.entry_search.get().lower()
        flt = self.var_filter.get()
        for idx, row in self.stock.df.iterrows():
            name = str(row.iloc[1])
            if term in name.lower():
                c, pf = int(row.iloc[2]), int(row.iloc[3])
                show = True
                if flt == "Saldo Canoas" and c <= 0: show = False
                elif flt == "Zero Canoas" and c > 0: show = False
                elif flt == "Saldo PF" and pf <= 0: show = False
                elif flt == "Zero PF" and pf > 0: show = False
                if show:
                    tag = 'positivo' if (c > 0 or pf > 0) else 'zerado'
                    raw_id = row.iloc[0]
                    display_id = idx + 2
                    if pd.notna(raw_id) and str(raw_id).strip() != "":
                        try: display_id = int(raw_id)
                        except: display_id = str(raw_id)
                    self.tree.insert("", "end", iid=idx, values=(display_id, name, c, pf), tags=(tag,))
        tc, tpf = self.stock.get_totals()
        self.lbl_tot_c.configure(text=str(tc)); self.lbl_tot_pf.configure(text=str(tpf))

    def _adjust_ui(self):
        op = self.var_op.get()
        if op == "Transferencia":
            self.cmb_loc.pack_forget(); self.cmb_transf.pack(side="left", padx=10, before=self.entry_qty)
            self.btn_ok.configure(text="TRANSFERIR", fg_color="#f39c12")
        else:
            self.cmb_transf.pack_forget(); self.cmb_loc.pack(side="left", padx=10, before=self.entry_qty)
            self.btn_ok.configure(text=op.upper(), fg_color="#27ae60" if op == "Entrada" else "#e74c3c")

    def action_load(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xls")])
        if path:
            ok, msg = self.stock.load_file(path)
            if ok: self.update_table(); messagebox.showinfo("Sucesso", msg)
            else: messagebox.showerror("Erro", msg)

    def action_save(self):
        ok, msg = self.stock.save_data()
        if ok: messagebox.showinfo("Sucesso", f"Dados salvos!\nBackup: {msg}")
        else: messagebox.showerror("Erro", msg)

    def action_new_item(self):
        if self.stock.df is None: return
        top = ctk.CTkToplevel(self); top.geometry("400x350"); top.attributes("-topmost", True)
        ctk.CTkLabel(top, text="Novo Item", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkLabel(top, text="Nome:").pack(anchor="w", padx=20); en = ctk.CTkEntry(top); en.pack(fill="x", padx=20)
        ctk.CTkLabel(top, text="Canoas:").pack(anchor="w", padx=20); ec = ctk.CTkEntry(top); ec.insert(0, "0"); ec.pack(fill="x", padx=20)
        ctk.CTkLabel(top, text="PF:").pack(anchor="w", padx=20); ep = ctk.CTkEntry(top); ep.insert(0, "0"); ep.pack(fill="x", padx=20)
        def save():
            try:
                qc, qp = int(ec.get()), int(ep.get())
                if self.stock.add_item(en.get().upper(), qc, qp):
                    self.update_table(); top.destroy(); self.tree.yview_moveto(1); messagebox.showinfo("Sucesso", "Item criado.")
            except: messagebox.showerror("Erro", "Verifique os números.")
        ctk.CTkButton(top, text="Salvar", command=save, fg_color="#27ae60").pack(pady=20)

    def action_delete(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("Confirmar", "Apagar item selecionado?"):
            self.stock.remove_item(int(sel[0])); self.update_table(); messagebox.showinfo("Sucesso", "Removido. Salve para confirmar.")

    def action_process(self):
        sel = self.tree.selection()
        if not sel: return
        try:
            qty = int(self.entry_qty.get())
            if qty <= 0: raise ValueError
            idx = int(sel[0])
            self.stock.update_stock(idx, self.var_op.get(), qty, self.var_loc.get(), self.var_transf.get())
            self.update_table(); self.tree.selection_set(str(idx))
        except ValueError as ve: messagebox.showerror("Erro", str(ve))
        except Exception as e: messagebox.showerror("Erro", str(e))

    def action_reports(self):
        if self.stock.df is None: return
        top = ctk.CTkToplevel(self); top.geometry("300x250"); top.attributes("-topmost", True)
        def gen(tipo):
            top.destroy()
            try:
                res = False
                if tipo == "abc": res = self.rep_mgr.save_pdf("Relatório ABC", self.rep_mgr.generate_abc(self.stock.df, self.stock.history_path), "ABC.pdf")
                else: res = self.rep_mgr.save_pdf("Estoque Atual", self.rep_mgr.generate_stock_list(self.stock.df), "Estoque.pdf")
                if res: messagebox.showinfo("Sucesso", "PDF Gerado!")
            except Exception as e: messagebox.showerror("Erro", str(e))
        ctk.CTkButton(top, text="Estoque Atual", command=lambda: gen("stock")).pack(pady=5)
        ctk.CTkButton(top, text="Curva ABC", command=lambda: gen("abc"), fg_color="#8e44ad").pack(pady=5)

    def action_history(self):
        if not self.stock.history_path or not os.path.exists(self.stock.history_path): return
        top = ctk.CTkToplevel(self); top.geometry("800x500"); top.attributes("-topmost", True)
        tree = ttk.Treeview(top, columns=("D","O","I","Q","X"), show="headings"); tree.pack(fill="both", expand=True)
        for c in ("D","O","I","Q","X"): tree.heading(c, text=c)
        with open(self.stock.history_path, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                p = line.strip().split(";;;")
                if len(p)>=5: tree.insert("", "end", values=p)

    def _check_update_silent(self):
        try:
            r = requests.get(CONFIG["URL_VERSION"], timeout=5)
            if r.status_code == 200 and r.text.strip() != CONFIG["VERSION"]: self.action_check_update_manual()
        except: pass

    def action_check_update_manual(self):
        try:
            r = requests.get(CONFIG["URL_VERSION"], timeout=5)
            if r.status_code == 200:
                rem = r.text.strip()
                if rem != CONFIG["VERSION"]:
                    if messagebox.askyesno("Update", f"Baixar v{rem}?"): self._download_update()
                else: messagebox.showinfo("Info", "Atualizado.")
        except: messagebox.showerror("Erro", "Sem conexão.")

    def _download_update(self):
        def run():
            try:
                p = os.path.join(os.environ["TEMP"], "Setup.exe")
                r = requests.get(CONFIG["URL_INSTALLER"])
                with open(p, 'wb') as f: f.write(r.content)
                subprocess.Popen([p], shell=True); self.destroy()
            except: pass
        threading.Thread(target=run, daemon=True).start()