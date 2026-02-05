import os
from datetime import datetime
from tkinter import filedialog
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

class ReportManager:
    def generate_abc(self, df, history_path):
        if not history_path or not os.path.exists(history_path):
            raise FileNotFoundError("Histórico não encontrado.")

        # 1. Processar Histórico
        counts = {}
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    # Suporte legacy (|) e novo (;;;)
                    parts = line.split(";;;")
                    if len(parts) < 5: parts = line.split(" | ")
                    
                    if len(parts) >= 4:
                        op = parts[1].strip()
                        if "SAIDA" in op or "BAIXA" in op:
                            item = parts[2].strip()
                            qty = int(parts[3])
                            counts[item] = counts.get(item, 0) + qty
                except: continue

        # 2. Ranking
        ranking = []
        all_items = df.iloc[:, 1].tolist()
        
        for item in all_items:
            out_qty = counts.get(str(item), 0)
            cls = "C (Sem Giro)"
            if out_qty > 50: cls = "A (Alto Giro)"
            elif out_qty > 10: cls = "B (Médio Giro)"
            ranking.append([str(item), out_qty, cls])
        
        ranking.sort(key=lambda x: x[1], reverse=True)
        return [["Produto", "Saídas", "Classificação"]] + ranking

    def generate_stock_list(self, df):
        data = [["ID", "Produto", "Canoas", "PF"]]
        for idx, row in df.iterrows():
            c, pf = int(row.iloc[2]), int(row.iloc[3])
            if c > 0 or pf > 0:
                data.append([str(idx+2), str(row.iloc[1]), str(c), str(pf)])
        return data

    def save_pdf(self, title, data, filename):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=filename)
        # CORREÇÃO: Retorna False se o usuário cancelar
        if not path: return False
        
        try:
            doc = SimpleDocTemplate(path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 9)
            ]))
            
            elements.append(t)
            doc.build(elements)
            os.startfile(path)
            # CORREÇÃO: Retorna True se sucesso
            return True
        except:
            raise