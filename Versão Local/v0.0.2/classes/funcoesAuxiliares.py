from openpyxl import Workbook
from .imports import *

def mostrar_mensagem(parent, tipo, titulo, texto):
    """
    Exibe popups personalizados.
    Tipos: 'sucesso', 'info', 'aviso', 'erro', 'confirma', 'confirma_exclusao'
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(titulo)
    msg.setText(texto)
    
    # --- ESTILO BASE (Blindado contra herança de cor branca) ---
    # background-color: Define o fundo do popup
    # QLabel { color: #2c3e50 } : Força a letra ser cinza escuro/preto
    style_base = """
        QMessageBox { background-color: #fdfefe; }
        QLabel { color: #2c3e50; font-weight: bold; font-size: 13px; min-width: 300px; }
        QPushButton { 
            color: white; border-radius: 4px; 
            padding: 6px 15px; font-weight: bold; min-width: 80px; border: none;
        }
    """

    # --- TIPO: SUCESSO (Verde) ou INFO (Azul) ---
    if tipo == 'sucesso' or tipo == 'info':
        msg.setIcon(QMessageBox.Icon.Information)
        # Se for sucesso, botão verde. Se info, azul.
        cor_btn = "#27ae60" if tipo == 'sucesso' else "#3498db"
        cor_hover = "#219150" if tipo == 'sucesso' else "#2980b9"
        
        msg.setStyleSheet(style_base + f"""
            QPushButton {{ background-color: {cor_btn}; }} 
            QPushButton:hover {{ background-color: {cor_hover}; }}
        """)
        msg.exec()
        return True

    # --- TIPO: AVISO (Laranja) ---
    elif tipo == 'aviso':
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setStyleSheet(style_base + """
            QPushButton { background-color: #f39c12; } 
            QPushButton:hover { background-color: #d35400; }
        """)
        msg.exec()
        return True

    # --- TIPO: ERRO (Vermelho) ---
    elif tipo == 'erro':
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setStyleSheet(style_base + """
            QPushButton { background-color: #c0392b; } 
            QPushButton:hover { background-color: #a93226; }
        """)
        msg.exec()
        return True

    # --- TIPO: CONFIRMAÇÃO GENÉRICA (Verde) ---
    elif tipo == 'confirma':
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        # Aplica o estilo base PRIMEIRO
        msg.setStyleSheet(style_base)
        
        botao_sim = msg.button(QMessageBox.StandardButton.Yes)
        botao_sim.setText("Sim")
        botao_sim.setStyleSheet("background-color: #27ae60; color: white; border-radius: 4px; padding: 6px; border: none;")
        
        botao_nao = msg.button(QMessageBox.StandardButton.No)
        botao_nao.setText("Cancelar")
        botao_nao.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 4px; padding: 6px; border: none;")
        
        return msg.exec() == QMessageBox.StandardButton.Yes

    # --- TIPO: CONFIRMAÇÃO DE EXCLUSÃO (Vermelho) ---
    elif tipo == 'confirma_exclusao':
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        # Aplica o estilo base PRIMEIRO
        msg.setStyleSheet(style_base)
        
        botao_sim = msg.button(QMessageBox.StandardButton.Yes)
        botao_sim.setText("Sim, Excluir")
        botao_sim.setStyleSheet("background-color: #c0392b; color: white; border-radius: 4px; padding: 6px; border: none;")
        
        botao_nao = msg.button(QMessageBox.StandardButton.No)
        botao_nao.setText("Cancelar")
        botao_nao.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 4px; padding: 6px; border: none;")
        
        return msg.exec() == QMessageBox.StandardButton.Yes

    # Caso padrão (fallback)
    msg.exec()
    return True

class FinanceiroService:
    """
    Camada de Serviço para padronizar as operações financeiras em todo o sistema.
    """
    
    @staticmethod
    def criar_recebimento(cursor, cliente_id, descricao, valor, vencimento, 
                          forma_pagamento, venda_id=None, num_parcela="1/1", 
                          status="Aberto", data_recebimento=None, obs=""):
        """
        Insere um registro na tabela contas_receber de forma padronizada.
        Recebe o 'cursor' como parâmetro para poder participar de Transações Atômicas (Rollback).
        """
        cursor.execute("""
            INSERT INTO db_fin.contas_receber (
                venda_id, cliente_id, descricao, num_parcela, 
                valor_previsto, data_vencimento, status, forma_pagamento, 
                data_recebimento, obs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (venda_id, cliente_id, descricao, num_parcela, valor, 
              vencimento, status, forma_pagamento, data_recebimento, obs))
        
def setup_combo_behavior(combo):
    """
    Faz o combobox abrir automaticamente APENAS quando recebe foco via TAB.
    Evita o loop infinito ao fechar o popup com Enter.
    """
    # Guarda a referência original do método focusInEvent da classe ou instância
    old_focus_in = combo.focusInEvent

    def new_focus_in(event):
        # Chama o comportamento padrão (para pintar a borda azul, etc)
        old_focus_in(event)
        
        # AQUI ESTÁ A CORREÇÃO:
        # Só abre o popup se o motivo do foco for a tecla TAB ou SHIFT+TAB
        if event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason):
            QTimer.singleShot(100, combo.showPopup)

    # Substitui o método da instância
    combo.focusInEvent = new_focus_in

class MoneySpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.setMaximum(9999999.99)
        self.setGroupSeparatorShown(True)
        self.setDecimals(2)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()
    
    def stepBy(self, steps):
        pass

# --- NOVA CLASSE PARA INTEIROS (QUANTIDADE) ---
class IntSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Opcional: Remove botões de subir/descer
        # self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons) 
        self.setMaximum(9999999)
        self.setGroupSeparatorShown(True) # Coloca ponto no milhar (1.000)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll() # Seleciona tudo ao clicar

FOCUS_STYLE = """
    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox {
        padding: 8px;
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        background-color: white;
    }
    /* Quando o campo está sendo editado (foco) */
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus {
        background-color: #e8f6f3; /* Fundo levemente esverdeado/azulado */
        border: 2px solid #3498db; /* Borda Azul destaque */
    }
"""

PATH_LOGO = os.path.join("images", "logo.png")

# --- PALETA DE CORES MODERNA ---
COLORS = {
    "primary": "#3498db",
    "primary_hover": "#2980b9",
    "secondary": "#2c3e50",
    "accent": "#e74c3c",
    "success": "#27ae60",
    "warning": "#f39c12",
    "light_bg": "#ecf0f1",
    "white": "#ffffff",
    "text": "#2c3e50",
    "border": "#bdc3c7",
    "shadow": "#95a5a6",
    'bg': '#f0f2f5'
}

def validar_cpf(cpf):
    """Valida CPF brasileiro"""
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    
    # Validação do segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    
    return cpf[-2:] == f"{digito1}{digito2}"

def validar_cnpj(cnpj):
    """Valida CNPJ brasileiro"""
    cnpj = re.sub(r'[^0-9]', '', str(cnpj))
    
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    
    # Validação do primeiro dígito
    pesos1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    digito1 = 0 if soma % 11 < 2 else 11 - (soma % 11)
    
    # Validação do segundo dígito
    pesos2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 0 if soma % 11 < 2 else 11 - (soma % 11)
    
    return cnpj[-2:] == f"{digito1}{digito2}"

def formatar_cpf(cpf):
    """Formata CPF: 000.000.000-00"""
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

def formatar_cnpj(cnpj):
    """Formata CNPJ: 00.000.000/0000-00"""
    cnpj = re.sub(r'[^0-9]', '', str(cnpj))
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

def formatar_moeda_br(valor):
    """Formata valor para moeda brasileira"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# Tabela Simples Nacional 2024 (Anexo III - Serviços)
TABELA_SIMPLES_NACIONAL = [
    {"ate": 180000, "aliquota": 0.06, "deduzir": 0},
    {"ate": 360000, "aliquota": 0.112, "deduzir": 9360},
    {"ate": 720000, "aliquota": 0.135, "deduzir": 17640},
    {"ate": 1800000, "aliquota": 0.16, "deduzir": 35640},
    {"ate": 3600000, "aliquota": 0.21, "deduzir": 125640},
    {"ate": 4800000, "aliquota": 0.33, "deduzir": 648000}
]

def calcular_imposto_simples(faturamento_anual):
    """Calcula imposto pelo Simples Nacional"""
    for faixa in TABELA_SIMPLES_NACIONAL:
        if faturamento_anual <= faixa["ate"]:
            imposto = (faturamento_anual * faixa["aliquota"]) - faixa["deduzir"]
            return max(0, imposto)
    return 0

def calcular_margem_lucro(preco_venda, preco_custo):
    """Calcula margem de lucro percentual"""
    try:
        if preco_venda <= 0:
            return 0
        margem = ((preco_venda - preco_custo) / preco_venda) * 100
        return round(margem, 2)
    except:
        return 0

# ==================== FUNÇÕES PIX ====================

def gerar_pix_payload(chave, valor, nome_beneficiario, cidade, descricao=""):
    """Gera payload PIX (Copia e Cola) conforme padrão BACEN"""
    try:
        # Simplificado - em produção usar biblioteca pyemv
        chave = str(chave)
        nome = str(nome_beneficiario)[:25]  # Máximo 25 caracteres
        cidade = str(cidade)[:15]  # Máximo 15 caracteres
        
        payload = f"00020126580014BR.GOV.BCB.PIX01{len(chave):02d}{chave}"
        payload += "52040000"
        payload += "5303986"
        payload += f"54{len(str(valor)):02d}{valor:.2f}"
        payload += "5802BR"
        payload += f"59{len(nome):02d}{nome}"
        payload += f"60{len(cidade):02d}{cidade}"
        
        if descricao:
            desc = str(descricao)[:50]
            payload += f"62{len(desc)+4:02d}05{len(desc):02d}{desc}"
        
        payload += "6304"
        
        # CRC16
        import binascii
        crc = binascii.crc_hqx(payload.encode(), 0xFFFF)
        payload += f"{crc:04X}"
        
        return payload
    except Exception as e:
        print(f"Erro ao gerar PIX: {e}")
        return None

def gerar_qr_code_pix(payload, tamanho=300):
    """Gera QR Code PIX"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converte para base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"Erro ao gerar QR Code: {e}")
        return None

# ==================== FUNÇÕES BOLETO ====================

def calcular_fator_vencimento_boleto(data_vencimento):
    """Calcula fator de vencimento (dias desde 07/10/1997)"""
    try:
        data_base = datetime(1997, 10, 7).date()
        if isinstance(data_vencimento, str):
            data_vencimento = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
        diferenca = (data_vencimento - data_base).days
        return diferenca
    except Exception as e:
        print(f"Erro ao calcular fator: {e}")
        return 0

def calcular_dv_modulo11(codigo):
    """Calcula dígito verificador módulo 11 para boleto"""
    try:
        sequencia = [2,3,4,5,6,7,8,9] * 10
        soma = sum(int(codigo[i]) * sequencia[i] for i in range(len(codigo)))
        resto = soma % 11
        return 1 if resto in [0, 1] else 11 - resto
    except:
        return 1

def gerar_codigo_barras_boleto(banco, valor, data_vencimento, nosso_numero, agencia, conta):
    """Gera código de barras do boleto"""
    try:
        cod_banco = str(banco).zfill(3)
        cod_moeda = "9"
        fator_venc = str(calcular_fator_vencimento_boleto(data_vencimento)).zfill(4)
        valor_str = str(int(valor * 100)).zfill(10)
        
        # Campo livre (simplificado)
        agencia_str = str(agencia).zfill(4)
        conta_str = str(conta).zfill(10)
        nosso_num_str = str(nosso_numero).zfill(11)
        
        campo_livre = agencia_str + conta_str + nosso_num_str
        
        # Código sem DV
        codigo_sem_dv = cod_banco + cod_moeda + fator_venc + valor_str + campo_livre
        
        # Calcula DV
        dv = calcular_dv_modulo11(codigo_sem_dv)
        
        # Insere DV na posição 5
        codigo_barras = codigo_sem_dv[0:4] + str(dv) + codigo_sem_dv[4:]
        
        return codigo_barras
    except Exception as e:
        print(f"Erro ao gerar código de barras: {e}")
        return None

def gerar_linha_digitavel_boleto(codigo_barras):
    """Gera linha digitável a partir do código de barras"""
    try:
        if not codigo_barras or len(codigo_barras) < 44:
            return None
            
        # Campo 1
        campo1 = codigo_barras[0:4] + codigo_barras[19:24]
        dv1 = str(calcular_dv_modulo11(campo1))
        campo1_fmt = f"{campo1[0:5]}.{campo1[5:10]}{dv1}"
        
        # Campo 2
        campo2 = codigo_barras[24:34]
        dv2 = str(calcular_dv_modulo11(campo2))
        campo2_fmt = f"{campo2[0:5]}.{campo2[5:10]}{dv2}"
        
        # Campo 3
        campo3 = codigo_barras[34:44]
        dv3 = str(calcular_dv_modulo11(campo3))
        campo3_fmt = f"{campo3[0:5]}.{campo3[5:10]}{dv3}"
        
        # Campo 4 (DV geral)
        campo4 = codigo_barras[4]
        
        # Campo 5 (fator + valor)
        campo5 = codigo_barras[5:19]
        
        return f"{campo1_fmt} {campo2_fmt} {campo3_fmt} {campo4} {campo5}"
    except Exception as e:
        print(f"Erro ao gerar linha digitável: {e}")
        return None

# ==================== FUNÇÕES EXPORTAÇÃO EXCEL ====================

def exportar_excel_generico(dados, colunas, titulo, filepath=None):
    """Exporta dados genéricos para Excel"""
    try:
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"{titulo.replace(' ', '_')}_{timestamp}.xlsx"
        
        wb = Workbook()
        ws = wb.active
        
        # Título
        ws.merge_cells('A1:' + get_column_letter(len(colunas)) + '1')
        cell = ws['A1']
        cell.value = titulo
        cell.font = Font(size=16, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30
        
        # Data
        ws.merge_cells('A2:' + get_column_letter(len(colunas)) + '2')
        ws['A2'] = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws['A2'].font = Font(size=10, italic=True)
        ws['A2'].alignment = Alignment(horizontal='center')
        
        # Cabeçalho
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for col_num, coluna in enumerate(colunas, 1):
            cell = ws.cell(row=4, column=col_num)
            cell.value = coluna
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="3498DB", end_color="3498DB", fill_type="solid")
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border
        
        # Dados
        for linha_num, registro in enumerate(dados, 5):
            for col_num, valor in enumerate(registro, 1):
                cell = ws.cell(row=linha_num, column=col_num)
                cell.value = valor
                cell.alignment = Alignment(horizontal='left', vertical='center')
                cell.border = border
        
        # Ajusta largura
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max(max_length + 2, 15), 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        wb.save(filepath)
        return True, filepath
    except Exception as e:
        return False, str(e)

# ==================== CLASSE CPF/CNPJ COM VALIDAÇÃO ====================

class CPFCNPJLineEdit(QLineEdit):
    """Campo com validação automática de CPF/CNPJ"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("000.000.000-00 ou 00.000.000/0000-00")
        self.textChanged.connect(self.formatar_e_validar)
        
    def formatar_e_validar(self):
        """Formata e valida em tempo real"""
        texto = re.sub(r'[^0-9]', '', self.text())
        cursor_pos = self.cursorPosition()
        
        if len(texto) <= 11:  # CPF
            if len(texto) >= 10:
                texto_formatado = formatar_cpf(texto)
            else:
                texto_formatado = texto
        else:  # CNPJ
            texto_formatado = formatar_cnpj(texto)
        
        self.blockSignals(True)
        self.setText(texto_formatado)
        self.setCursorPosition(min(cursor_pos + 1, len(texto_formatado)))
        self.blockSignals(False)
        
        # Validação visual
        self.validar_visual()
    
    def validar_visual(self):
        """Muda cor conforme validade"""
        doc = re.sub(r'[^0-9]', '', self.text())
        
        if len(doc) == 0:
            self.setStyleSheet("border: 1px solid #bdc3c7;")
        elif len(doc) == 11:
            if validar_cpf(doc):
                self.setStyleSheet("border: 2px solid #27ae60; background-color: #e8f8f5;")
            else:
                self.setStyleSheet("border: 2px solid #e74c3c; background-color: #fadbd8;")
        elif len(doc) == 14:
            if validar_cnpj(doc):
                self.setStyleSheet("border: 2px solid #27ae60; background-color: #e8f8f5;")
            else:
                self.setStyleSheet("border: 2px solid #e74c3c; background-color: #fadbd8;")
        else:
            self.setStyleSheet("border: 2px solid #f39c12; background-color: #fef5e7;")
    
    def is_valid(self):
        """Verifica se é válido"""
        doc = re.sub(r'[^0-9]', '', self.text())
        if len(doc) == 11:
            return validar_cpf(doc)
        elif len(doc) == 14:
            return validar_cnpj(doc)
        return False
    
class MoneySpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.setMaximum(9999999.99)
        self.setGroupSeparatorShown(True)
        self.setDecimals(2)

    def focusInEvent(self, event):
        # Ao clicar/focar, seleciona tudo para facilitar a substituição do valor
        super().focusInEvent(event)
        self.selectAll()

    def stepBy(self, steps):
        # Desabilita a rodinha do mouse para evitar acidentes
        pass