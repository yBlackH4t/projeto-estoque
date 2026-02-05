import pandas as pd
import os
import shutil
from datetime import datetime

class InventoryController:
    def __init__(self):
        self.df = None
        self.caminho_arquivo = None
        self.caminho_historico = None
        self.buffer_historico = []
        self.separador = " | " # Voltando ao seu padrão original para manter compatibilidade

    def carregar_excel(self, caminho):
        self.df = pd.read_excel(caminho, header=0)
        self.caminho_arquivo = caminho
        base_name = os.path.splitext(caminho)[0]
        self.caminho_historico = f"{base_name}_historico.txt"
        # Tratamento de dados original
        self.df.iloc[:, 2] = pd.to_numeric(self.df.iloc[:, 2], errors='coerce').fillna(0).astype(int)
        self.df.iloc[:, 3] = pd.to_numeric(self.df.iloc[:, 3], errors='coerce').fillna(0).astype(int)

    def registrar_log(self, item, op, qtd, detalhe=""):
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        msg = f"{data_hora} | {op} | {item} | {qtd} | {detalhe}\n"
        self.buffer_historico.append(msg)

    def movimentar(self, idx, op, local_ou_dir, qtd):
        """Lógica completa de Entrada, Saída e Transferência."""
        idx = int(idx)
        col_c, col_pf = 2, 3
        saldo_c = self.df.iat[idx, col_c]
        saldo_pf = self.df.iat[idx, col_pf]
        nome = self.df.iat[idx, 1]

        if op == "Transf":
            if "Canoas -> PF" in local_ou_dir:
                if saldo_c < qtd: raise ValueError(f"Saldo insuficiente em Canoas ({saldo_c})")
                self.df.iat[idx, col_c] -= qtd
                self.df.iat[idx, col_pf] += qtd
            else:
                if saldo_pf < qtd: raise ValueError(f"Saldo insuficiente em PF ({saldo_pf})")
                self.df.iat[idx, col_pf] -= qtd
                self.df.iat[idx, col_c] += qtd
        else:
            col = col_c if local_ou_dir == "Canoas" else col_pf
            if op == "Saida":
                if self.df.iat[idx, col] < qtd:
                    raise ValueError(f"Saldo insuficiente! Disponível: {self.df.iat[idx, col]}")
                self.df.iat[idx, col] -= qtd
            else:
                self.df.iat[idx, col] += qtd
        
        self.registrar_log(nome, op.upper(), qtd, local_ou_dir)
        return nome

    def excluir_item(self, idx):
        nome = self.df.iat[idx, 1]
        self.registrar_log(nome, "EXCLUSAO", 0, "Item removido")
        self.df = self.df.drop(idx).reset_index(drop=True)
        return nome

    def adicionar_item(self, nome, qc, qp):
        # Lógica de ID original
        prox_id = 1
        if not self.df.empty:
            max_id = pd.to_numeric(self.df.iloc[:, 0], errors='coerce').max()
            prox_id = int(max_id) + 1 if pd.notna(max_id) else len(self.df) + 1
        
        dados_linha = [prox_id, nome.upper(), qc, qp]
        # Garante compatibilidade com colunas extras
        if len(self.df.columns) > 4:
            dados_linha.extend([None] * (len(self.df.columns) - 4))
        
        novo_df = pd.DataFrame([dados_linha], columns=self.df.columns)
        self.df = pd.concat([self.df, novo_df], ignore_index=True)
        self.registrar_log(nome, "CADASTRO", 0, f"C={qc}/PF={qp}")
        return nome

    def salvar(self):
        try:
            # Backup
            pasta_backup = os.path.join(os.path.dirname(self.caminho_arquivo), "backups")
            os.makedirs(pasta_backup, exist_ok=True)
            dt = datetime.now().strftime("%Y-%m-%d_%H-%M")
            nome_bkp = f"BKP_{dt}_{os.path.basename(self.caminho_arquivo)}"
            shutil.copy2(self.caminho_arquivo, os.path.join(pasta_backup, nome_bkp))
            
            # Salvar Excel e Histórico
            self.df.to_excel(self.caminho_arquivo, index=False)
            if self.buffer_historico and self.caminho_historico:
                with open(self.caminho_historico, "a", encoding="utf-8") as f:
                    for log in self.buffer_historico: f.write(log)
                self.buffer_historico = []
            return nome_bkp
        except PermissionError:
            raise Exception("Feche o Excel antes de salvar!")