import pandas as pd
import os
import shutil
from datetime import datetime

class StockManager:
    def __init__(self):
        self.df = None
        self.file_path = None
        self.history_path = None
        self.history_buffer = [] # Nome correto da variável

    def load_file(self, path):
        """Carrega e limpa os dados do Excel."""
        try:
            self.df = pd.read_excel(path, header=0)
            self.file_path = path
            
            # Define caminho do histórico
            base = os.path.splitext(path)[0]
            self.history_path = f"{base}_historico.txt"
            self.history_buffer = []

            # Limpeza de dados (Garante numérico)
            self.df.iloc[:, 2] = pd.to_numeric(self.df.iloc[:, 2], errors='coerce').fillna(0)
            self.df.iloc[:, 3] = pd.to_numeric(self.df.iloc[:, 3], errors='coerce').fillna(0)
            return True, "Carregado com sucesso"
        except Exception as e:
            return False, str(e)

    def add_item(self, name, qty_c, qty_pf):
        """Adiciona um novo item ao DataFrame."""
        if self.df is None: return False
        
        try:
            # Lógica inteligente de ID
            next_id = 1
            if not self.df.empty:
                try:
                    max_id = pd.to_numeric(self.df.iloc[:, 0], errors='coerce').max()
                    if pd.notna(max_id): next_id = int(max_id) + 1
                    else: next_id = len(self.df) + 1
                except: next_id = len(self.df) + 1

            # Cria linha compatível com colunas extras
            row_data = [next_id, name, qty_c, qty_pf]
            current_cols = len(self.df.columns)
            if current_cols > 4:
                row_data.extend([None] * (current_cols - 4))
            
            new_df = pd.DataFrame([row_data], columns=self.df.columns)
            self.df = pd.concat([self.df, new_df], ignore_index=True)
            self.log_memory(name, "CADASTRO", 0, f"C={qty_c}/PF={qty_pf}")
            return True
        except Exception as e:
            print(e)
            return False

    def remove_item(self, index):
        """Remove item pelo índice do DataFrame."""
        if self.df is None: return
        name = self.df.iat[index, 1]
        self.log_memory(name, "EXCLUSAO", 0, "Item removido")
        self.df = self.df.drop(index).reset_index(drop=True)
        return name

    def update_stock(self, index, operation, qty, location, transfer_direction=None):
        """Atualiza quantidades e valida regras de negócio."""
        col_c, col_pf = 2, 3
        # Pega valores atuais
        bal_c = self.df.iat[index, col_c]
        bal_pf = self.df.iat[index, col_pf]
        item_name = self.df.iat[index, 1]
        detail = ""

        if operation == "Transf":
            detail = transfer_direction
            if "Canoas -> PF" in transfer_direction:
                if bal_c < qty: raise ValueError(f"Saldo insuficiente em Canoas ({bal_c})")
                self.df.iat[index, col_c] -= qty
                self.df.iat[index, col_pf] += qty
            else:
                if bal_pf < qty: raise ValueError(f"Saldo insuficiente em PF ({bal_pf})")
                self.df.iat[index, col_pf] -= qty # Correção: era qtd no original
                self.df.iat[index, col_c] += qty
        else:
            detail = f"{operation} em {location}"
            target_col = col_c if location == "Canoas" else col_pf
            
            if operation == "Saida":
                current = self.df.iat[index, target_col]
                if current < qty: raise ValueError(f"Saldo insuficiente. Disp: {current}")
                self.df.iat[index, target_col] -= qty
            else:
                self.df.iat[index, target_col] += qty

        self.log_memory(item_name, operation.upper(), qty, detail)
        return item_name

    def log_memory(self, item, op, qty, detail):
        dt = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        msg = f"{dt};;;{op};;;{item};;;{qty};;;{detail}\n"
        self.history_buffer.append(msg) # CORRIGIDO: history_buffer

    def save_data(self):
        """Realiza Backup, Salva Excel e Escreve Histórico."""
        if self.df is None or not self.file_path: return False, "Sem dados"

        try:
            # 1. Backup
            backup_dir = os.path.join(os.path.dirname(self.file_path), "backups")
            if not os.path.exists(backup_dir): os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            backup_name = f"{base_name}_{timestamp}.xlsx"
            
            try:
                shutil.copy2(self.file_path, os.path.join(backup_dir, backup_name))
            except: pass 

            # 2. Salvar Excel (Proteção contra arquivo aberto)
            try:
                self.df.to_excel(self.file_path, index=False)
            except PermissionError:
                raise PermissionError("Arquivo aberto no Excel. Feche-o primeiro.")

            # 3. Salvar Histórico
            # CORRIGIDO: Verifica self.history_buffer em vez de self.buffer_historico
            if self.history_buffer and self.history_path:
                with open(self.history_path, "a", encoding="utf-8") as f:
                    for line in self.history_buffer: f.write(line)
                self.history_buffer = []

            return True, backup_name
        except Exception as e:
            return False, str(e)

    def get_totals(self):
        if self.df is None: return 0, 0
        return int(self.df.iloc[:, 2].sum()), int(self.df.iloc[:, 3].sum())