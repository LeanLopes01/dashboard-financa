import sys
import os
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time
import ctypes
import shutil
import hashlib
import subprocess
import calendar
from keyauth import api
import platform
import hashlib

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QListWidget, QListWidgetItem, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFrame, QFormLayout,
                             QLineEdit, QDateEdit, QComboBox, QScrollArea, QDoubleSpinBox,
                             QInputDialog, QProgressBar, QFileDialog, QMessageBox,
                             QCalendarWidget, QDialog, QGridLayout, QSpinBox, QCheckBox,
                             QSizePolicy, QAbstractItemView, QTabWidget)
from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QIcon, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- CONSTANTES GLOBAIS ---
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
    "shadow": "#95a5a6"
}

# --- 0 FICAR BONITINHO ---

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

# --- FUNÇÃO AUXILIAR PARA ABRIR COMBOBOX NO TAB ---
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

# --- 1. CAMADA DE DADOS (Multi-Database Architecture) ---

class DataContext:
    def __init__(self):
        self.data_dir = "data"
        self.ensure_directory()
        
        # Arquivos de banco separados
        self.db_clientes = os.path.join(self.data_dir, "clientes.db")
        self.db_produtos = os.path.join(self.data_dir, "produtos.db")
        self.db_vendas = os.path.join(self.data_dir, "vendas.db")
        self.db_financeiro = os.path.join(self.data_dir, "financeiro.db")
        
        # Conexão principal
        self.conn = sqlite3.connect(self.db_vendas)
        self.cursor = self.conn.cursor()
        
        # Anexar os outros bancos (Aliases: db_cli, db_prod, db_fin)
        self.attach_databases()
        self.create_tables()
        
        # REMOVIDO: self.seed_data() -> Não gera mais dados de exemplo

    def ensure_directory(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def attach_databases(self):
        self.cursor.execute(f"ATTACH DATABASE '{self.db_clientes}' AS db_cli")
        self.cursor.execute(f"ATTACH DATABASE '{self.db_produtos}' AS db_prod")
        self.cursor.execute(f"ATTACH DATABASE '{self.db_financeiro}' AS db_fin")

    def create_tables(self):
        # 1. Clientes
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_cli.entidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_pessoa TEXT, categoria TEXT, 
            nome_razao TEXT NOT NULL, nome_fantasia TEXT, cpf_cnpj TEXT, ie_rg TEXT, 
            endereco TEXT, bairro TEXT, cidade TEXT, uf TEXT, cep TEXT, telefone TEXT, 
            email TEXT, data_registro DATE)''')

        # 2. Produtos
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_prod.produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, 
            descricao TEXT, categoria TEXT, preco_custo REAL, preco_venda REAL, 
            estoque_atual REAL, unidade_medida TEXT, data_cadastro DATE)''')

        # 3. Vendas (Cabeçalho) - ATUALIZADO
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            data_venda DATE NOT NULL, 
            cliente_id INTEGER, 
            vendedor TEXT,
            valor_bruto REAL,
            desconto_geral REAL,
            valor_liquido REAL,
            status TEXT, -- Aguardando, Faturado, Cancelado
            nota_fiscal TEXT,
            forma_pagamento_prevista TEXT,
            obs TEXT
        )''')

        # 3.1 Itens da Venda (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            produto_id INTEGER,
            quantidade REAL,
            preco_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(venda_id) REFERENCES vendas(id)
        )''')

        # 4. Contas a Pagar
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL, fornecedor_id INTEGER,
            categoria TEXT, valor REAL NOT NULL, data_vencimento DATE, data_pagamento DATE,
            status TEXT, forma_pagamento TEXT, obs TEXT)''')

        # 5. Contas a Receber - ATUALIZADO
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_receber (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,           -- Vínculo com a venda
            descricao TEXT NOT NULL,
            cliente_id INTEGER,
            num_parcela TEXT,           -- Ex: "1/3"
            valor_previsto REAL NOT NULL,
            valor_recebido REAL,        -- Quanto caiu na conta
            data_vencimento DATE,
            data_recebimento DATE,
            status TEXT,                -- Aberto, Pago, Atrasado
            forma_pagamento TEXT,
            conta_destino TEXT,         -- Itaú, Caixa, Cofre
            comprovante_path TEXT,      -- Link do arquivo
            obs TEXT
        )''')
        self.conn.commit()
    
    def get_sales_chart_data(self):
        query = "SELECT strftime('%Y-%m', data_venda) as mes, SUM(valor_liquido) FROM main.vendas WHERE status = 'Concluido' GROUP BY mes ORDER BY mes"
        return pd.read_sql_query(query, self.conn)
    
    def get_fluxo_caixa(self, data_inicio, data_fim):
        """Une Vendas, Contas Pagas e Recebidas em um extrato."""
        # CORREÇÃO: valor_total -> valor_liquido | valor -> valor_recebido (na parte de contas_receber)
        query = f'''
            SELECT origem, origem_id, data, descricao, valor, tipo FROM (
                SELECT 'venda' as origem, id as origem_id, data_venda as data, 'Venda (ID ' || id || ')' as descricao, valor_liquido as valor, 'Entrada' as tipo
                FROM main.vendas WHERE status = 'Concluido' AND data_venda BETWEEN '{data_inicio}' AND '{data_fim}'
                UNION ALL
                SELECT 'receber' as origem, id as origem_id, data_recebimento as data, descricao, valor_recebido as valor, 'Entrada' as tipo
                FROM db_fin.contas_receber WHERE status = 'Recebido' AND data_recebimento BETWEEN '{data_inicio}' AND '{data_fim}'
                UNION ALL
                SELECT 'pagar' as origem, id as origem_id, data_pagamento as data, descricao, -valor as valor, 'Saida' as tipo
                FROM db_fin.contas_pagar WHERE status = 'Pago' AND data_pagamento BETWEEN '{data_inicio}' AND '{data_fim}'
            ) ORDER BY data DESC
        '''
        return pd.read_sql_query(query, self.conn)
    
    def get_dre_data(self, data_inicio, data_fim):
        """Agrupa para o DRE."""
        
        query_receita = f'''
            SELECT 'Receita Bruta' as grupo, 'Vendas de Produtos' as categoria, SUM(valor_liquido) as valor
            FROM main.vendas WHERE data_venda BETWEEN '{data_inicio}' AND '{data_fim}' AND status = 'Concluido'
            UNION ALL
            SELECT 'Receita Bruta', descricao, SUM(valor_recebido)
            FROM db_fin.contas_receber WHERE data_recebimento BETWEEN '{data_inicio}' AND '{data_fim}' AND status = 'Recebido'
        '''
        
        query_despesa = f'''
            SELECT 
                CASE 
                    WHEN categoria LIKE '%Impostos%' THEN '(-) Impostos'
                    WHEN categoria LIKE '%Custo%' OR categoria LIKE '%Fornecedor%' THEN '(-) Custos (CMV)'
                    ELSE '(-) Despesas Operacionais'
                END as grupo, categoria, SUM(valor) as valor
            FROM db_fin.contas_pagar WHERE data_pagamento BETWEEN '{data_inicio}' AND '{data_fim}' AND status = 'Pago' 
            GROUP BY categoria
        '''
        
        df_rec = pd.read_sql_query(query_receita, self.conn)
        df_desp = pd.read_sql_query(query_despesa, self.conn)
        
        # CORREÇÃO: fillna(0) seguido de astype(float) elimina o aviso
        df_rec['valor'] = df_rec['valor'].fillna(0).astype(float)
        df_desp['valor'] = df_desp['valor'].fillna(0).astype(float)
        
        return df_rec, df_desp
    
    def get_evolucao_financeira(self, data_inicio, data_fim):
        """
        Retorna o consolidado POR DATA dentro do período escolhido.
        [Data, Receitas, Despesas, Saldo]
        """
        # 1. Receitas
        query_receitas = f'''
            SELECT data, SUM(valor) as receitas FROM (
                SELECT data_venda as data, valor_liquido as valor FROM main.vendas 
                WHERE status='Concluido' AND data_venda BETWEEN '{data_inicio}' AND '{data_fim}'
                UNION ALL
                SELECT data_recebimento as data, valor_recebido as valor FROM db_fin.contas_receber 
                WHERE status='Recebido' AND data_recebimento BETWEEN '{data_inicio}' AND '{data_fim}'
            ) GROUP BY data
        '''
        
        # 2. Despesas
        query_despesas = f'''
            SELECT data_pagamento as data, SUM(valor) as despesas 
            FROM db_fin.contas_pagar 
            WHERE status='Pago' AND data_pagamento BETWEEN '{data_inicio}' AND '{data_fim}'
            GROUP BY data
        '''
        
        df_rec = pd.read_sql_query(query_receitas, self.conn)
        df_desp = pd.read_sql_query(query_despesas, self.conn)
        
        if df_rec.empty and df_desp.empty:
            return pd.DataFrame(columns=['data', 'receitas', 'despesas', 'saldo'])
            
        # Junta os dois DataFrames pela DATA
        df_final = pd.merge(df_rec, df_desp, on='data', how='outer')
        
        # CORREÇÃO: Preenche 0 e força conversão para float para evitar o FutureWarning
        df_final['receitas'] = df_final['receitas'].fillna(0).astype(float)
        df_final['despesas'] = df_final['despesas'].fillna(0).astype(float)
        
        # Calcula o Saldo
        df_final['saldo'] = df_final['receitas'] - df_final['despesas']
        
        # Ordena por data cronologicamente
        df_final = df_final.sort_values('data')
        
        return df_final
    
    def get_despesas_por_categoria(self):
        """Retorna as despesas REAIS pagas agrupadas por categoria"""
        query = '''
            SELECT categoria, SUM(valor) 
            FROM db_fin.contas_pagar 
            WHERE status = 'Pago' 
            GROUP BY categoria
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall() # Retorna lista de tuplas [('Energia', 150.0), ...]
    
    # --- Adicione estes métodos na classe DataContext ---

    def get_receita_total(self):
        """Soma Vendas (Concluido) + Contas a Receber (Recebido)"""
        # 1. Vendas
        # CORREÇÃO: valor_total -> valor_liquido
        query_vendas = "SELECT SUM(valor_liquido) FROM main.vendas WHERE status = 'Concluido'"
        self.cursor.execute(query_vendas)
        vendas = self.cursor.fetchone()[0] or 0.0
        
        # 2. Outras Receitas
        # CORREÇÃO: valor -> valor_recebido
        query_outras = "SELECT SUM(valor_recebido) FROM db_fin.contas_receber WHERE status = 'Recebido'"
        self.cursor.execute(query_outras)
        outras = self.cursor.fetchone()[0] or 0.0
        
        return vendas + outras

    def get_pendencias(self, tipo):
        """Busca contas pendentes. tipo='Pagar' ou 'Receber'"""
        if tipo == "Pagar":
            tabela = "db_fin.contas_pagar"
            # Na tabela de pagar, o nome ainda é 'valor'
            coluna_valor = "valor"
        else:
            tabela = "db_fin.contas_receber"
            # Na tabela de receber, usamos 'valor_previsto' e apelidamos de 'valor'
            # para que o resto do código (que espera 'valor') continue funcionando
            coluna_valor = "valor_previsto as valor"

        # Note o uso de {coluna_valor} na query abaixo
        query = f"SELECT id, descricao, {coluna_valor}, data_vencimento FROM {tabela} WHERE status = 'Pendente'"
        
        return pd.read_sql_query(query, self.conn)

    def get_meses_com_movimento(self):
        """
        Retorna uma lista de tuplas (Ano, Mês) ordenada do mais recente para o antigo.
        Baseia-se nas datas de venda, pagamento e recebimento.
        """
        query = '''
            SELECT DISTINCT strftime('%Y', data) as ano, strftime('%m', data) as mes 
            FROM (
                SELECT data_venda as data FROM main.vendas WHERE status = 'Concluido'
                UNION
                SELECT data_pagamento as data FROM db_fin.contas_pagar WHERE status = 'Pago'
                UNION
                SELECT data_recebimento as data FROM db_fin.contas_receber WHERE status = 'Recebido'
            ) 
            WHERE data IS NOT NULL 
            ORDER BY ano DESC, mes DESC
        '''
        try:
            return pd.read_sql_query(query, self.conn).values.tolist()
        except:
            return []
        
    def baixar_conta(self, id_conta, tipo):
        """Muda status para Pago/Recebido e define data de hoje"""
        tabela = "db_fin.contas_pagar" if tipo == "Pagar" else "db_fin.contas_receber"
        novo_status = "Pago" if tipo == "Pagar" else "Recebido"
        coluna_data = "data_pagamento" if tipo == "Pagar" else "data_recebimento"
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        try:
            self.cursor.execute(f"UPDATE {tabela} SET status = ?, {coluna_data} = ? WHERE id = ?", (novo_status, hoje, id_conta))
            self.conn.commit()
            return True
        except Exception as e:
            print(e)
            return False

    def criar_backup(self, pasta_destino):
        """Cria backup de todos os bancos de dados em uma pasta específica"""
        try:
            # Cria pasta com data e hora do backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pasta_backup = os.path.join(pasta_destino, f"backup_financeiro_{timestamp}")
            os.makedirs(pasta_backup, exist_ok=True)
            
            # Lista de bancos a fazer backup
            bancos = [
                (self.db_vendas, "vendas.db"),
                (self.db_clientes, "clientes.db"),
                (self.db_produtos, "produtos.db"),
                (self.db_financeiro, "financeiro.db")
            ]
            
            # Fecha a conexão temporariamente
            self.conn.close()
            
            # Copia cada banco
            for caminho_db, nome_arquivo in bancos:
                if os.path.exists(caminho_db):
                    shutil.copy2(caminho_db, os.path.join(pasta_backup, nome_arquivo))
                    print(f"✓ Backup de {nome_arquivo} criado")
            
            # Reconecta
            self.conn = sqlite3.connect(self.db_vendas)
            self.cursor = self.conn.cursor()
            self.attach_databases()
            
            return True, pasta_backup
        except Exception as e:
            print(f"✗ Erro ao criar backup: {e}")
            # Reconecta mesmo em caso de erro
            try:
                self.conn = sqlite3.connect(self.db_vendas)
                self.cursor = self.conn.cursor()
                self.attach_databases()
            except:
                pass
            return False, str(e)

# --- 2. COMPONENTES DE UI ---

def mostrar_mensagem(parent, tipo, titulo, texto):
    """
    Exibe popups com estilo forçado para corrigir o bug visual (branco sobre branco).
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(titulo)
    msg.setText(texto)
    
    # Estilo forçado para garantir visibilidade
    style_popup = """
        QMessageBox { background-color: #fdfefe; }
        QLabel { color: #2c3e50; font-weight: bold; font-size: 13px; }
        QPushButton { 
            background-color: #3498db; color: white; border-radius: 4px; 
            padding: 6px 15px; font-weight: bold; min-width: 80px;
        }
        QPushButton:hover { background-color: #2980b9; }
    """
    msg.setStyleSheet(style_popup)

    if tipo == 'info':
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        return True
    elif tipo == 'aviso':
        msg.setIcon(QMessageBox.Icon.Warning)
        # Botão laranja para aviso
        msg.setStyleSheet(style_popup.replace("#3498db", "#f39c12")) 
        msg.exec()
        return True
    elif tipo == 'erro':
        msg.setIcon(QMessageBox.Icon.Critical)
        # Botão vermelho para erro
        msg.setStyleSheet(style_popup.replace("#3498db", "#c0392b"))
        msg.exec()
        return True
    elif tipo == 'confirma':
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        botao_sim = msg.button(QMessageBox.StandardButton.Yes)
        botao_sim.setText("Sim, Excluir")
        botao_sim.setStyleSheet("background-color: #c0392b; color: white; border-radius: 4px; padding: 6px;")
        
        botao_nao = msg.button(QMessageBox.StandardButton.No)
        botao_nao.setText("Cancelar")
        botao_nao.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 4px; padding: 6px;")
        
        return msg.exec() == QMessageBox.StandardButton.Yes
    
class PlotlyWidget(QWebEngineView):
    def set_figure(self, fig):
        html = fig.to_html(include_plotlyjs='cdn')
        self.setHtml(html)

class DashboardTab(QWidget):
    def __init__(self, data_context):
        super().__init__()
        self.db = data_context
        self.COLORS = {
            'bg_claro': '#f8f9fa', 'branco': '#ffffff', 'borda': '#e0e0e0',
            'texto_principal': '#2c3e50', 'texto_secundario': '#7f8c8d',
            'azul': '#3498db', 'verde': '#2ecc71', 'vermelho': '#e74c3c',
            'roxo': '#9b59b6', 'laranja': '#e67e22'
        }
        self.setStyleSheet(f"background-color: {self.COLORS['bg_claro']}; color: black;")
        
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        
        # --- HEADER ---
        header_frame = QFrame()
        header_frame.setFixedHeight(70)
        header_frame.setStyleSheet(f"background-color: {self.COLORS['branco']}; border-bottom: 1px solid {self.COLORS['borda']};")
        top_bar = QHBoxLayout(header_frame)
        top_bar.setContentsMargins(25, 0, 25, 0)
        
        title = QLabel("📊 Dashboard")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.COLORS['texto_principal']}; border: none;") 
        
        # 1. COMBOBOX (Seleção Rápida)
        self.cb_periodo = QComboBox()
        self.cb_periodo.setMinimumWidth(180)
        self.cb_periodo.setStyleSheet("QComboBox { padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px; background: white; color: black; font-weight: bold; }")
        self.carregar_periodos()
        
        # 2. CAMPOS DE DATA (Seleção Fina)
        style_date = "QDateEdit { background-color: white; color: black; border: 1px solid #bdc3c7; border-radius: 4px; padding: 5px; min-width: 110px; }"
        
        self.date_ini = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_ini.setCalendarPopup(True)
        self.date_ini.setDisplayFormat("dd/MM/yyyy")
        self.date_ini.setStyleSheet(style_date)
        
        self.date_fim = QDateEdit(QDate.currentDate())
        self.date_fim.setCalendarPopup(True)
        self.date_fim.setDisplayFormat("dd/MM/yyyy")
        self.date_fim.setStyleSheet(style_date)
        
        # Conecta o Combo às Datas (Ao mudar o combo, muda as datas)
        self.cb_periodo.currentIndexChanged.connect(self.atualizar_datas_pelo_combo)
        
        # Botão Atualizar (Usa as datas que estiverem nos campos)
        btn_refresh = QPushButton("🔄 Atualizar")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background-color: {self.COLORS['azul']}; color: white; border: none; padding: 8px 15px; border-radius: 5px; font-weight: bold; }} 
            QPushButton:hover {{ background-color: #2980b9; }}
        """)
        btn_refresh.clicked.connect(self.refresh_charts)
        
        # Monta a barra superior
        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Período Rápido:", styleSheet="color: #2c3e50; font-weight: bold; border:none;"))
        top_bar.addWidget(self.cb_periodo)
        top_bar.addWidget(QLabel("  De:", styleSheet="color: #2c3e50; font-weight: bold; border:none;"))
        top_bar.addWidget(self.date_ini)
        top_bar.addWidget(QLabel("Até:", styleSheet="color: #2c3e50; font-weight: bold; border:none;"))
        top_bar.addWidget(self.date_fim)
        top_bar.addWidget(btn_refresh)
        
        layout_principal.addWidget(header_frame)

        # --- ÁREA DE SCROLL ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(content_widget)
        self.scroll_layout.setSpacing(25)
        self.scroll_layout.setContentsMargins(30, 30, 30, 30)
        
        scroll.setWidget(content_widget)
        layout_principal.addWidget(scroll)

        # KPIs
        self.kpi_layout = QHBoxLayout()
        self.scroll_layout.addLayout(self.kpi_layout)
        
        # Gráficos
        self.web_evolution = PlotlyWidget()
        self.web_evolution.setFixedHeight(350)
        self.scroll_layout.addWidget(self._wrap_in_card("Fluxo de Caixa Diário", self.web_evolution))
        
        grid_charts = QGridLayout()
        grid_charts.setSpacing(20)
        
        self.web_acumulado = PlotlyWidget()
        self.web_acumulado.setFixedHeight(300)
        grid_charts.addWidget(self._wrap_in_card("Saldo Acumulado", self.web_acumulado), 0, 0)
        
        self.web_pie = PlotlyWidget()
        self.web_pie.setFixedHeight(300)
        grid_charts.addWidget(self._wrap_in_card("Categorias", self.web_pie), 0, 1)

        self.web_pay_methods = PlotlyWidget()
        self.web_pay_methods.setFixedHeight(300)
        grid_charts.addWidget(self._wrap_in_card("Formas de Pagamento", self.web_pay_methods), 1, 0)
        
        self.web_bar = PlotlyWidget()
        self.web_bar.setFixedHeight(300)
        grid_charts.addWidget(self._wrap_in_card("Resumo", self.web_bar), 1, 1)

        self.scroll_layout.addLayout(grid_charts)
        self.scroll_layout.addStretch()
        
        # Inicializa datas com base na primeira seleção do combo
        self.atualizar_datas_pelo_combo()
        self.refresh_charts()

    def carregar_periodos(self):
        self.cb_periodo.clear()
        self.cb_periodo.addItem("Todo o Período", userData="ALL")
        meses = self.db.get_meses_com_movimento()
        nomes_meses = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril', '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
        for ano, mes in meses:
            self.cb_periodo.addItem(f"{nomes_meses.get(mes, mes)} {ano}", userData=(ano, mes))

    def atualizar_datas_pelo_combo(self):
        """Quando o usuário escolhe no Combo, atualiza os campos de Data"""
        data = self.cb_periodo.currentData()
        
        if data == "ALL" or data is None:
            # Período amplo
            d_ini = QDate(2000, 1, 1)
            d_fim = QDate(2100, 12, 31)
        else:
            ano, mes = int(data[0]), int(data[1])
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            d_ini = QDate(ano, mes, 1)
            d_fim = QDate(ano, mes, ultimo_dia)
        
        # Atualiza os widgets visuais
        self.date_ini.setDate(d_ini)
        self.date_fim.setDate(d_fim)
        # Opcional: já disparar o refresh
        # self.refresh_charts() 

    def refresh_charts(self):
        # PEGA AS DATAS DOS CAMPOS MANUAIS (que podem ter sido preenchidos pelo combo)
        d_ini = self.date_ini.date().toString("yyyy-MM-dd")
        d_fim = self.date_fim.date().toString("yyyy-MM-dd")
        
        df_evolucao = self.db.get_evolucao_financeira(d_ini, d_fim)
        
        query_cat = f'''
            SELECT categoria, SUM(valor) as total 
            FROM db_fin.contas_pagar 
            WHERE status='Pago' AND data_pagamento BETWEEN '{d_ini}' AND '{d_fim}'
            GROUP BY categoria ORDER BY total DESC
        '''
        df_cat = pd.read_sql_query(query_cat, self.db.conn)

        query_pag = f'''
            SELECT forma_pagamento, SUM(valor) as total
            FROM db_fin.contas_pagar
            WHERE status='Pago' AND data_pagamento BETWEEN '{d_ini}' AND '{d_fim}'
            GROUP BY forma_pagamento ORDER BY total DESC
        '''
        try: df_pag = pd.read_sql_query(query_pag, self.db.conn)
        except: df_pag = pd.DataFrame(columns=['forma_pagamento', 'total'])

        receitas = df_evolucao['receitas'].sum() if not df_evolucao.empty else 0
        despesas = df_evolucao['despesas'].sum() if not df_evolucao.empty else 0
        saldo = receitas - despesas
        
        self.update_kpi(receitas, despesas, saldo)
        
        self.plot_evolution_chart(df_evolucao)
        self.plot_cumulative_chart(df_evolucao)
        self.plot_expense_pie_chart(df_cat)
        self.plot_payment_methods_chart(df_pag)
        self.plot_summary_column_chart(df_evolucao)

    def _wrap_in_card(self, title_text, widget):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {self.COLORS['branco']}; border-radius: 10px; border: 1px solid {self.COLORS['borda']}; }}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        lbl = QLabel(title_text.upper())
        lbl.setStyleSheet(f"color: {self.COLORS['texto_secundario']}; font-weight: bold; font-size: 11px; border: none;")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return card

    # ... MANTENHA OS MÉTODOS GRÁFICOS (plot_evolution_chart, etc) DO CÓDIGO ANTERIOR ...
    def plot_evolution_chart(self, df):
        fig = go.Figure()
        if not df.empty:
            if 'saldo' not in df.columns: df['saldo'] = df['receitas'] - df['despesas']
            fig.add_trace(go.Bar(x=df['data'], y=df['receitas'], name='Receitas', marker_color='#2ecc71'))
            fig.add_trace(go.Bar(x=df['data'], y=df['despesas'], name='Despesas', marker_color='#e74c3c'))
            fig.add_trace(go.Scatter(x=df['data'], y=df['saldo'], name='Saldo Líquido', mode='lines+markers', line=dict(color='#2c3e50', width=3), marker=dict(size=6, color='white', line=dict(width=2, color='#2c3e50'))))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"), barmode='group', plot_bgcolor='white', paper_bgcolor='white', hovermode="x unified")
        self.web_evolution.set_figure(fig)

    def plot_cumulative_chart(self, df):
        fig = go.Figure()
        if not df.empty:
            if 'saldo' not in df.columns: df['saldo'] = df['receitas'] - df['despesas']
            df['saldo_acum'] = df['saldo'].cumsum()
            fig.add_trace(go.Scatter(x=df['data'], y=df['saldo_acum'], fill='tozeroy', mode='lines+markers', name='Acumulado', line=dict(color=self.COLORS['azul'], width=3), marker=dict(size=5)))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor='white', paper_bgcolor='white')
        self.web_acumulado.set_figure(fig)

    def plot_expense_pie_chart(self, df):
        fig = go.Figure()
        if not df.empty: fig.add_trace(go.Pie(labels=df['categoria'], values=df['total'], hole=0.5, textinfo='percent', marker=dict(colors=['#e74c3c', '#e67e22', '#f1c40f', '#95a5a6', '#34495e'])))
        else: fig.add_trace(go.Pie(labels=["Sem Dados"], values=[1], hole=0.5, marker=dict(colors=['#ecf0f1'])))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
        self.web_pie.set_figure(fig)

    def plot_payment_methods_chart(self, df):
        fig = go.Figure()
        if not df.empty: fig.add_trace(go.Bar(y=df['forma_pagamento'], x=df['total'], orientation='h', marker_color=self.COLORS['roxo'], text=[f"R$ {v:,.0f}" for v in df['total']], textposition='auto'))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed"))
        self.web_pay_methods.set_figure(fig)

    def plot_summary_column_chart(self, df):
        fig = go.Figure()
        if not df.empty:
            tot_rec = df['receitas'].sum()
            tot_desp = df['despesas'].sum()
            tot_lucro = tot_rec - tot_desp
            fig.add_trace(go.Bar(x=['Receita', 'Despesa', 'Saldo'], y=[tot_rec, tot_desp, tot_lucro], marker_color=[self.COLORS['verde'], self.COLORS['vermelho'], self.COLORS['azul']], text=[f"R$ {v:,.0f}" for v in [tot_rec, tot_desp, tot_lucro]], textposition='auto'))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
        self.web_bar.set_figure(fig)

    def update_kpi(self, receitas, despesas, saldo):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        kpis = [("TOTAL RECEITAS", receitas, self.COLORS['verde'], "⬆"), ("TOTAL DESPESAS", despesas, self.COLORS['vermelho'], "⬇"), ("SALDO LÍQUIDO", saldo, self.COLORS['azul'], "∑")]
        for title, value, color, icon in kpis:
            card = QFrame()
            card.setFixedHeight(110)
            card.setStyleSheet(f"QFrame {{ background-color: {self.COLORS['branco']}; border-radius: 12px; border: 1px solid {self.COLORS['borda']}; border-bottom: 4px solid {color}; }}")
            lay = QVBoxLayout(card)
            head = QHBoxLayout()
            lbl_t = QLabel(title); lbl_t.setStyleSheet(f"color: {self.COLORS['texto_secundario']}; font-weight: bold; font-size: 11px; border: none;")
            lbl_i = QLabel(icon); lbl_i.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; border: none;")
            head.addWidget(lbl_t); head.addStretch(); head.addWidget(lbl_i)
            val = QLabel(f"R$ {value:,.2f}"); val.setStyleSheet(f"color: {self.COLORS['texto_principal']}; font-size: 24px; font-weight: 800; border: none;")
            lay.addLayout(head); lay.addWidget(val)
            self.kpi_layout.addWidget(card)

class GerenciamentoEntidades(QWidget):
    def __init__(self, db_context, tipo_entidade="Cliente"):
        super().__init__()
        self.db = db_context
        self.tipo = tipo_entidade 
        self.id_em_edicao = None 
        
        # Layout Principal
        self.layout = QVBoxLayout(self)
        
        # Área de Rolagem (Caso a tela seja pequena)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        self.layout.addWidget(scroll)

        layout_content = QVBoxLayout(content)

        # --- 1. FORMULÁRIO (Topo) ---
        self.frame_form = QFrame()
        self.frame_form.setStyleSheet("background-color: #f7f9f9; border-radius: 8px; border: 1px solid #bdc3c7;")
        form_layout = QFormLayout(self.frame_form)
        
        # Título
        lbl_titulo = QLabel(f"👤 Cadastro de {self.tipo}")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        form_layout.addRow(lbl_titulo)

        # Campos Principais
        self.cb_tipo_pessoa = QComboBox()
        self.cb_tipo_pessoa.addItems(["Pessoa Jurídica", "Pessoa Física"])
        setup_combo_behavior(self.cb_tipo_pessoa) # Certifique-se que essa função helper existe
        
        self.txt_doc = QLineEdit()
        self.txt_doc.setPlaceholderText("CPF ou CNPJ (Obrigatório)")
        
        self.txt_ie = QLineEdit() # Campo Novo
        self.txt_ie.setPlaceholderText("Inscrição Estadual / RG")

        self.txt_nome = QLineEdit()
        self.txt_nome.setPlaceholderText(f"Razão Social / Nome (Obrigatório)")
        
        self.txt_fantasia = QLineEdit()
        self.txt_fantasia.setPlaceholderText("Nome Fantasia")
        
        # Adiciona ao Form
        form_layout.addRow("Tipo:", self.cb_tipo_pessoa)
        form_layout.addRow("Documento:", self.txt_doc)
        form_layout.addRow("Inscrição/RG:", self.txt_ie)
        form_layout.addRow("Nome/Razão:", self.txt_nome)
        form_layout.addRow("Fantasia:", self.txt_fantasia)
        
        # Grupo de Endereço (CEP, Rua, Bairro, Cidade, UF)
        lbl_end = QLabel("Endereço e Contato")
        lbl_end.setStyleSheet("font-weight: bold; margin-top: 10px; color: #2c3e50;")
        form_layout.addRow(lbl_end)

        hbox_cep = QHBoxLayout()
        self.txt_cep = QLineEdit()
        self.txt_cep.setPlaceholderText("CEP")
        self.txt_endereco = QLineEdit()
        self.txt_endereco.setPlaceholderText("Rua, Número")
        hbox_cep.addWidget(self.txt_cep)
        hbox_cep.addWidget(self.txt_endereco)
        form_layout.addRow("CEP / Rua:", hbox_cep)

        hbox_loc = QHBoxLayout()
        self.txt_bairro = QLineEdit()
        self.txt_bairro.setPlaceholderText("Bairro")
        self.txt_cidade = QLineEdit()
        self.txt_cidade.setPlaceholderText("Cidade")
        self.txt_uf = QLineEdit()
        self.txt_uf.setPlaceholderText("UF")
        self.txt_uf.setFixedWidth(50)
        
        hbox_loc.addWidget(self.txt_bairro)
        hbox_loc.addWidget(self.txt_cidade)
        hbox_loc.addWidget(self.txt_uf)
        form_layout.addRow("Localização:", hbox_loc)

        # Contato
        hbox_contato = QHBoxLayout()
        self.txt_telefone = QLineEdit()
        self.txt_email = QLineEdit()
        hbox_contato.addWidget(self.txt_telefone)
        hbox_contato.addWidget(QLabel("Email:"))
        hbox_contato.addWidget(self.txt_email)
        form_layout.addRow("Tel / Email:", hbox_contato)

        # Botões
        hbox_btn = QHBoxLayout()
        self.btn_salvar = QPushButton(f"✅ Salvar {self.tipo}")
        self.btn_salvar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_salvar.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_salvar.clicked.connect(self.salvar)
        
        self.btn_cancelar = QPushButton("Cancelar Edição")
        self.btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar.setStyleSheet("background-color: #95a5a6; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_cancelar.clicked.connect(self.limpar_form)
        self.btn_cancelar.hide()

        hbox_btn.addStretch()
        hbox_btn.addWidget(self.btn_cancelar)
        hbox_btn.addWidget(self.btn_salvar)
        form_layout.addRow(hbox_btn)

        layout_content.addWidget(self.frame_form)

        # --- 2. TABELA DE LISTAGEM (Baixo) ---
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6) # ID, Nome, Doc, Cidade, Tel, Ações
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome/Razão", "CPF/CNPJ", "Cidade/UF", "Telefone", "Ações"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setMinimumHeight(300)
        self.tabela.setStyleSheet("QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; }")
        
        layout_content.addWidget(self.tabela)
        self.carregar_tabela()

    def salvar(self):
        # Validação Anti-Fantasma
        nome = self.txt_nome.text().strip()
        doc = self.txt_doc.text().strip()
        
        if not nome:
            mostrar_mensagem(self, 'aviso', 'Atenção', f"O campo Nome/Razão Social é obrigatório.")
            self.txt_nome.setFocus()
            return
        if not doc:
            mostrar_mensagem(self, 'aviso', 'Atenção', "O campo CPF ou CNPJ é obrigatório.")
            self.txt_doc.setFocus()
            return

        # Coleta de Dados
        dados = (
            self.cb_tipo_pessoa.currentText(),
            self.tipo, # Categoria (Cliente ou Fornecedor)
            nome,
            self.txt_fantasia.text().strip(),
            doc,
            self.txt_ie.text().strip(),
            self.txt_endereco.text().strip(),
            self.txt_bairro.text().strip(),
            self.txt_cidade.text().strip(),
            self.txt_uf.text().strip(),
            self.txt_cep.text().strip(),
            self.txt_telefone.text().strip(),
            self.txt_email.text().strip(),
            datetime.now().strftime("%Y-%m-%d") # Data Registro
        )

        try:
            if self.id_em_edicao:
                # UPDATE
                self.db.cursor.execute("""
                    UPDATE db_cli.entidades SET 
                        tipo_pessoa=?, categoria=?, nome_razao=?, nome_fantasia=?, cpf_cnpj=?, 
                        ie_rg=?, endereco=?, bairro=?, cidade=?, uf=?, cep=?, telefone=?, email=?, data_registro=?
                    WHERE id=?
                """, dados + (self.id_em_edicao,))
                mostrar_mensagem(self, 'info', 'Sucesso', f"{self.tipo} atualizado com sucesso!")
            else:
                # INSERT
                self.db.cursor.execute("""
                    INSERT INTO db_cli.entidades (
                        tipo_pessoa, categoria, nome_razao, nome_fantasia, cpf_cnpj, 
                        ie_rg, endereco, bairro, cidade, uf, cep, telefone, email, data_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, dados)
                mostrar_mensagem(self, 'info', 'Sucesso', f"{self.tipo} cadastrado com sucesso!")
            
            self.db.conn.commit()
            self.limpar_form()
            self.carregar_tabela()
            
        except Exception as e:
            mostrar_mensagem(self, 'erro', 'Erro Crítico', f"Erro ao salvar no banco de dados: {str(e)}")

    def carregar_tabela(self):
        self.tabela.setRowCount(0)
        # Busca apenas a categoria atual (Cliente ou Fornecedor)
        query = f"SELECT id, nome_razao, cpf_cnpj, cidade, uf, telefone FROM db_cli.entidades WHERE categoria = '{self.tipo}' ORDER BY id DESC"
        
        try:
            df = pd.read_sql_query(query, self.db.conn)
            for i, row in df.iterrows():
                self.tabela.insertRow(i)
                pid = row['id']
                self.tabela.setItem(i, 0, QTableWidgetItem(str(pid)))
                self.tabela.setItem(i, 1, QTableWidgetItem(row['nome_razao']))
                self.tabela.setItem(i, 2, QTableWidgetItem(row['cpf_cnpj']))
                
                loc = f"{row['cidade']}/{row['uf']}" if row['cidade'] else ""
                self.tabela.setItem(i, 3, QTableWidgetItem(loc))
                self.tabela.setItem(i, 4, QTableWidgetItem(row['telefone']))
                
                # Ações
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(0,0,0,0)
                layout.setSpacing(5)
                
                btn_edit = QPushButton("✏️")
                btn_edit.setFixedSize(28, 24)
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border: none; border-radius: 3px;")
                btn_edit.clicked.connect(lambda ch, id_e=pid: self.carregar_para_edicao(id_e))
                
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(28, 24)
                btn_del.setStyleSheet("background-color: #c0392b; color: white; border: none; border-radius: 3px;")
                btn_del.clicked.connect(lambda ch, id_e=pid: self.excluir(id_e))
                
                layout.addWidget(btn_edit)
                layout.addWidget(btn_del)
                layout.addStretch()
                self.tabela.setCellWidget(i, 5, widget)
        except Exception as e:
             print(f"Erro ao carregar tabela: {e}")

    def carregar_para_edicao(self, id_entidade):
        self.db.cursor.execute("SELECT * FROM db_cli.entidades WHERE id=?", (id_entidade,))
        row = self.db.cursor.fetchone()
        if not row: return
        
        # Mapeamento baseado na ordem do INSERT acima
        # id(0), tipo(1), cat(2), nome(3), fant(4), doc(5), ie(6), end(7), bair(8), cid(9), uf(10), cep(11), tel(12), email(13)
        self.id_em_edicao = row[0]
        self.cb_tipo_pessoa.setCurrentText(row[1])
        self.txt_nome.setText(row[3])
        self.txt_fantasia.setText(row[4] or "")
        self.txt_doc.setText(row[5])
        self.txt_ie.setText(row[6] or "")
        self.txt_endereco.setText(row[7] or "")
        self.txt_bairro.setText(row[8] or "")
        self.txt_cidade.setText(row[9] or "")
        self.txt_uf.setText(row[10] or "")
        self.txt_cep.setText(row[11] or "")
        self.txt_telefone.setText(row[12] or "")
        self.txt_email.setText(row[13] or "")
        
        self.btn_salvar.setText("💾 Salvar Alterações")
        self.btn_cancelar.show()
        # Rola para o topo para ver o formulário
        self.layout.itemAt(0).widget().verticalScrollBar().setValue(0)

    def excluir(self, id_entidade):
        if mostrar_mensagem(self, 'confirma', 'Excluir', f"Deseja realmente excluir este {self.tipo}?"):
            try:
                self.db.cursor.execute("DELETE FROM db_cli.entidades WHERE id=?", (id_entidade,))
                self.db.conn.commit()
                self.carregar_tabela()
                self.limpar_form()
            except Exception as e:
                mostrar_mensagem(self, 'erro', 'Erro', str(e))

    def limpar_form(self):
        self.id_em_edicao = None
        campos = [self.txt_nome, self.txt_doc, self.txt_fantasia, self.txt_ie, 
                  self.txt_endereco, self.txt_bairro, self.txt_cidade, self.txt_uf, 
                  self.txt_cep, self.txt_telefone, self.txt_email]
        for c in campos: c.clear()
        
        self.btn_salvar.setText(f"✅ Salvar {self.tipo}")
        self.btn_cancelar.hide()

class CadastroProdutoForm(QWidget):
    produto_salvo_signal = pyqtSignal()

    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.label_style = "color: #2c3e50; font-weight: bold; font-size: 14px;"
        
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; color: #2c3e50; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { 
                background-color: white; color: black; border: 1px solid #bdc3c7; padding: 6px; border-radius: 4px;
            }
            QTableWidget { background-color: white; border: 1px solid #bdc3c7; selection-background-color: #3498db; }
            QHeaderView::section { background-color: #2c3e50; color: white; padding: 5px; font-weight: bold; }
        """)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        
        self.layout_content = QVBoxLayout(content) # Layout principal do scroll
        self.layout_content.setSpacing(20)
        
        # --- PARTE 1: CADASTRO (FORMULÁRIO) ---
        gb_cadastro = QFrame()
        gb_cadastro.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        form_layout = QFormLayout(gb_cadastro)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)
        
        # Título
        lbl_title = QLabel("Novo Produto")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; border: none;")
        form_layout.addRow(lbl_title)
        
        # Campos
        self.txt_sku = QLineEdit(placeholderText="Ex: TEC-001")
        form_layout.addRow("SKU / Código:", self.txt_sku)
        
        self.txt_nome = QLineEdit()
        form_layout.addRow("Nome do Produto:", self.txt_nome)
        
        self.txt_desc = QLineEdit()
        form_layout.addRow("Descrição Detalhada:", self.txt_desc)
        
        # Categoria
        hbox_cat = QHBoxLayout()
        self.cb_categoria = QComboBox()
        self.cb_categoria.setEditable(True)
        
        btn_add_cat = QPushButton("+")
        btn_add_cat.setFixedSize(40,30)
        btn_add_cat.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; border-radius: 4px; border: none;")
        btn_add_cat.clicked.connect(self.add_cat)
        
        hbox_cat.addWidget(self.cb_categoria)
        hbox_cat.addWidget(btn_add_cat)
        form_layout.addRow("Categoria:", hbox_cat)
        
        # Preços
        hbox_pr = QHBoxLayout()
        self.spin_custo = QDoubleSpinBox(); self.spin_custo.setPrefix("R$ "); self.spin_custo.setMaximum(999999.99)
        self.spin_venda = QDoubleSpinBox(); self.spin_venda.setPrefix("R$ "); self.spin_venda.setMaximum(999999.99)
        hbox_pr.addWidget(QLabel("Custo:")); hbox_pr.addWidget(self.spin_custo)
        hbox_pr.addWidget(QLabel("Venda:")); hbox_pr.addWidget(self.spin_venda)
        form_layout.addRow("Formação de Preço:", hbox_pr)
        
        # Estoque
        hbox_est = QHBoxLayout()
        self.spin_est = QDoubleSpinBox(); self.spin_est.setMaximum(999999)
        self.cb_un = QComboBox(); self.cb_un.addItems(["UN", "KG", "M", "L", "CX", "KIT"])
        hbox_est.addWidget(QLabel("Qtd Atual:")); hbox_est.addWidget(self.spin_est)
        hbox_est.addWidget(QLabel("Unidade:")); hbox_est.addWidget(self.cb_un)
        form_layout.addRow("Estoque:", hbox_est)
        
        # Data
        self.date_cad = QDateEdit(QDate.currentDate())
        self.date_cad.setCalendarPopup(True); self.date_cad.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Data Cadastro:", self.date_cad)
        
        # Botão Salvar
        btn_salvar = QPushButton("✅ Salvar Produto")
        btn_salvar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_salvar.clicked.connect(self.salvar)
        btn_salvar.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; padding: 12px; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #7d3c98; }")
        form_layout.addRow(btn_salvar)
        
        self.layout_content.addWidget(gb_cadastro)
        
        # --- PARTE 2: GERENCIAMENTO (TABELA + FILTRO) ---
        self.setup_gerenciamento_ui()
        
        # Finaliza setup
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        
        self.carregar_categorias()
        self.carregar_tabela()

    def setup_gerenciamento_ui(self):
        """Cria a parte inferior da tela para editar produtos"""
        gb_ger = QFrame()
        gb_ger.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        layout = QVBoxLayout(gb_ger)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header Filtros
        hbox_filt = QHBoxLayout()
        lbl_titulo = QLabel("Gerenciar Produtos")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; border: none;")
        
        self.cb_filtro_cat = QComboBox()
        self.cb_filtro_cat.setMinimumWidth(200)
        self.cb_filtro_cat.addItem("Todas as Categorias", None)
        self.cb_filtro_cat.currentIndexChanged.connect(self.carregar_tabela)
        
        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 4px; border: none;")
        btn_refresh.clicked.connect(lambda: (self.carregar_categorias(), self.carregar_tabela()))
        
        hbox_filt.addWidget(lbl_titulo)
        hbox_filt.addStretch()
        hbox_filt.addWidget(QLabel("Filtrar por:", styleSheet="border:none"))
        hbox_filt.addWidget(self.cb_filtro_cat)
        hbox_filt.addWidget(btn_refresh)
        
        layout.addLayout(hbox_filt)
        
        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "SKU", "Produto", "Categoria", "Preço Venda", "Ação"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(300)
        self.table.setStyleSheet("border: 1px solid #bdc3c7;")
        
        layout.addWidget(self.table)
        self.layout_content.addWidget(gb_ger)

    def carregar_categorias(self):
        # Carrega categorias para o cadastro E para o filtro
        pads = ["Hardware", "Software", "Serviços"]
        
        # 1. Combo Cadastro
        self.cb_categoria.clear()
        self.cb_categoria.addItems(pads)
        
        # 2. Combo Filtro
        current_filter = self.cb_filtro_cat.currentText()
        self.cb_filtro_cat.blockSignals(True)
        self.cb_filtro_cat.clear()
        self.cb_filtro_cat.addItem("Todas as Categorias", None)
        
        try:
            self.db.cursor.execute("SELECT DISTINCT categoria FROM db_prod.produtos ORDER BY categoria")
            cats = [c[0] for c in self.db.cursor.fetchall() if c[0]]
            
            # Popula Cadastro
            for c in cats:
                if c not in pads: self.cb_categoria.addItem(c)
            
            # Popula Filtro
            self.cb_filtro_cat.addItems(cats)
            
        except: pass
        
        # Restaura seleção do filtro se possível
        idx = self.cb_filtro_cat.findText(current_filter)
        if idx >= 0: self.cb_filtro_cat.setCurrentIndex(idx)
        self.cb_filtro_cat.blockSignals(False)

    def carregar_tabela(self):
        cat_filtro = self.cb_filtro_cat.currentText()
        is_all = self.cb_filtro_cat.currentData() is None and cat_filtro == "Todas as Categorias"
        
        query = "SELECT id, sku, nome, categoria, preco_venda FROM db_prod.produtos"
        params = ()
        
        if not is_all:
            query += " WHERE categoria = ?"
            params = (cat_filtro,)
            
        query += " ORDER BY id DESC"
        
        try:
            self.db.cursor.execute(query, params)
            rows = self.db.cursor.fetchall()
            
            self.table.setRowCount(0)
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                pid, sku, nome, cat, valor = row
                
                self.table.setItem(i, 0, QTableWidgetItem(str(pid)))
                self.table.setItem(i, 1, QTableWidgetItem(sku))
                self.table.setItem(i, 2, QTableWidgetItem(nome))
                self.table.setItem(i, 3, QTableWidgetItem(cat))
                self.table.setItem(i, 4, QTableWidgetItem(f"R$ {valor:,.2f}"))
                
                # Botão Editar
                btn_edit = QPushButton("✏️ Editar")
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius: 4px; font-weight: bold; border: none; padding: 4px;")
                btn_edit.clicked.connect(lambda checked, id_p=pid: self.abrir_editor(id_p))
                self.table.setCellWidget(i, 5, btn_edit)
                
        except Exception as e:
            print(e)

    def abrir_editor(self, produto_id):
        dlg = ProdutoEditorDialog(self.db, produto_id, self)
        if dlg.exec(): # Se salvou
            self.carregar_tabela() # Atualiza lista
            self.produto_salvo_signal.emit() # Avisa outras telas

    def add_cat(self):
        text, ok = QInputDialog.getText(self, "Nova Categoria", "Nome:")
        if ok and text:
            if self.cb_categoria.findText(text) == -1:
                self.cb_categoria.addItem(text)
                self.cb_filtro_cat.addItem(text) # Adiciona no filtro também
            self.cb_categoria.setCurrentText(text)

    def salvar(self):
        try:
            dados = (self.txt_sku.text(), self.txt_nome.text(), self.txt_desc.text(), 
                     self.cb_categoria.currentText(), self.spin_custo.value(), self.spin_venda.value(), 
                     self.spin_est.value(), self.cb_un.currentText(), self.date_cad.date().toString("yyyy-MM-dd"))
            
            self.db.cursor.execute('INSERT INTO db_prod.produtos (sku, nome, descricao, categoria, preco_custo, preco_venda, estoque_atual, unidade_medida, data_cadastro) VALUES (?,?,?,?,?,?,?,?,?)', dados)
            self.db.conn.commit()
            
            # Limpar
            self.txt_nome.setText("")
            self.txt_desc.setText("")
            self.spin_est.setValue(0)
            self.spin_custo.setValue(0)
            self.spin_venda.setValue(0)
            
            self.produto_salvo_signal.emit()
            self.carregar_tabela() # Atualiza a tabela na hora
            self.carregar_categorias() # Garante que nova categoria apareça no filtro
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Sucesso")
            msg.setText("✅ Produto cadastrado com sucesso!")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; } QPushButton { background-color: #2c3e50; color: white; padding: 5px 15px; }")
            msg.exec()
            
        except Exception as e: 
            msg = QMessageBox(self)
            msg.setText(f"Erro: {str(e)}")
            msg.exec()

    def excluir_produto(self, id_produto):
        if mostrar_mensagem(self, 'confirma', 'Excluir Produto', "Tem certeza? Isso pode afetar o histórico de vendas."):
            try:
                self.db.cursor.execute("DELETE FROM db_prod.produtos WHERE id=?", (id_produto,))
                self.db.conn.commit()
                self.carregar_tabela()
            except Exception as e:
                mostrar_mensagem(self, 'erro', 'Erro', str(e))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.focusNextChild()
        else:
            super().keyPressEvent(event)

class ProdutoEditorDialog(QDialog):
    def __init__(self, db_context, produto_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Produto")
        self.setFixedWidth(500)
        self.db = db_context
        self.produto_id = produto_id
        
        # Estilo
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { color: #2c3e50; font-weight: bold; }
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit { 
                padding: 6px; border: 1px solid #bdc3c7; border-radius: 4px; background-color: white; color: black;
            }
            QPushButton { padding: 8px; border-radius: 4px; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        
        # Carregar dados do banco
        self.db.cursor.execute("SELECT sku, nome, descricao, categoria, preco_custo, preco_venda, estoque_atual, unidade_medida FROM db_prod.produtos WHERE id=?", (produto_id,))
        dados = self.db.cursor.fetchone()
        
        if not dados:
            QMessageBox.critical(self, "Erro", "Produto não encontrado.")
            self.reject()
            return

        sku, nome, desc, cat, custo, venda, est, un = dados

        # Campos
        self.txt_sku = QLineEdit(sku)
        self.txt_nome = QLineEdit(nome)
        self.txt_desc = QLineEdit(desc)
        
        self.cb_cat = QComboBox()
        self.cb_cat.setEditable(True)
        # Carrega categorias existentes
        self.db.cursor.execute("SELECT DISTINCT categoria FROM db_prod.produtos")
        cats = [c[0] for c in self.db.cursor.fetchall() if c[0]]
        self.cb_cat.addItems(cats)
        self.cb_cat.setCurrentText(cat)
        
        self.spin_custo = QDoubleSpinBox(); self.spin_custo.setMaximum(999999); self.spin_custo.setValue(custo); self.spin_custo.setPrefix("R$ ")
        self.spin_venda = QDoubleSpinBox(); self.spin_venda.setMaximum(999999); self.spin_venda.setValue(venda); self.spin_venda.setPrefix("R$ ")
        self.spin_est = QDoubleSpinBox(); self.spin_est.setMaximum(999999); self.spin_est.setValue(est)
        self.cb_un = QComboBox(); self.cb_un.addItems(["UN", "KG", "M", "L", "CX", "KIT"]); self.cb_un.setCurrentText(un)

        # Adiciona ao layout
        form.addRow("SKU:", self.txt_sku)
        form.addRow("Nome:", self.txt_nome)
        form.addRow("Descrição:", self.txt_desc)
        form.addRow("Categoria:", self.cb_cat)
        form.addRow("Custo:", self.spin_custo)
        form.addRow("Venda:", self.spin_venda)
        form.addRow("Estoque:", self.spin_est)
        form.addRow("Unidade:", self.cb_un)
        
        layout.addLayout(form)
        
        # Botões
        hbox = QHBoxLayout()
        btn_salvar = QPushButton("💾 Salvar Alterações")
        btn_salvar.setStyleSheet("background-color: #27ae60; color: white; border: none;")
        btn_salvar.clicked.connect(self.salvar)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("background-color: #e74c3c; color: white; border: none;")
        btn_cancel.clicked.connect(self.reject)
        
        hbox.addWidget(btn_cancel)
        hbox.addWidget(btn_salvar)
        layout.addLayout(hbox)

    def salvar(self):
        nome = self.txt_nome.text().strip()
        sku = self.txt_sku.text().strip()
        
        if not nome:
            mostrar_mensagem(self, 'aviso', 'Inválido', "O produto precisa de um Nome.")
            return
        if not sku:
            mostrar_mensagem(self, 'aviso', 'Inválido', "O produto precisa de um SKU (código).")
            return
        
        try:
            sql = '''
                UPDATE db_prod.produtos SET 
                sku=?, nome=?, descricao=?, categoria=?, preco_custo=?, preco_venda=?, estoque_atual=?, unidade_medida=?
                WHERE id=?
            '''
            dados = (
                self.txt_sku.text(), self.txt_nome.text(), self.txt_desc.text(), self.cb_cat.currentText(),
                self.spin_custo.value(), self.spin_venda.value(), self.spin_est.value(), self.cb_un.currentText(),
                self.produto_id
            )
            self.db.cursor.execute(sql, dados)
            self.db.conn.commit()
            QMessageBox.information(self, "Sucesso", "Produto atualizado!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

class EntryEditorDialog(QDialog):
    def __init__(self, db_context, tipo, id_conta, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✏️ Editar Lançamento")
        self.setModal(True)
        self.resize(400, 350)
        
        self.db = db_context
        self.tipo = tipo  # 'pagar' ou 'receber'
        self.id_conta = id_conta
        
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Formulário
        form_group = QFrame()
        form_layout = QFormLayout(form_group)
        
        # Campos
        self.txt_desc = QLineEdit()
        self.spin_val = QDoubleSpinBox()
        self.spin_val.setMaximum(9999999)
        self.spin_val.setPrefix("R$ ")
        
        # --- AQUI ESTÁ A CONFIGURAÇÃO DO CALENDÁRIO QUE VOCÊ PEDIU ---
        self.dt_venc = QDateEdit()
        self.dt_venc.setCalendarPopup(True) # Ativa o calendário pop-up
        self.dt_venc.setDisplayFormat("dd/MM/yyyy")
        
        self.txt_cat = QLineEdit() # Categoria (pode ser texto livre na edição)
        self.txt_obs = QLineEdit()
        
        form_layout.addRow("Descrição:", self.txt_desc)
        form_layout.addRow("Valor:", self.spin_val)
        form_layout.addRow("Vencimento:", self.dt_venc)
        form_layout.addRow("Categoria:", self.txt_cat)
        form_layout.addRow("Observação:", self.txt_obs)
        
        layout.addWidget(form_group)
        
        # Botões Salvar / Cancelar
        hbox_btn = QHBoxLayout()
        btn_save = QPushButton("💾 Salvar")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        btn_save.clicked.connect(self.salvar_alteracoes)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        hbox_btn.addWidget(btn_save)
        hbox_btn.addWidget(btn_cancel)
        layout.addLayout(hbox_btn)
        
        # Carregar dados atuais
        self.carregar_dados()

    def carregar_dados(self):
        tabela = "db_fin.contas_pagar" if self.tipo == "pagar" else "db_fin.contas_receber"
        try:
            self.db.cursor.execute(f"SELECT descricao, valor, data_vencimento, categoria, obs FROM {tabela} WHERE id = ?", (self.id_conta,))
            row = self.db.cursor.fetchone()
            if row:
                self.txt_desc.setText(row[0])
                self.spin_val.setValue(row[1])
                # Converter data string YYYY-MM-DD para QDate
                qdate = QDate.fromString(row[2], "yyyy-MM-dd")
                self.dt_venc.setDate(qdate)
                self.txt_cat.setText(row[3] if row[3] else "")
                self.txt_obs.setText(row[4] if row[4] else "")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados: {e}")

    def salvar_alteracoes(self):
        tabela = "db_fin.contas_pagar" if self.tipo == "pagar" else "db_fin.contas_receber"
        
        desc = self.txt_desc.text()
        val = self.spin_val.value()
        dt = self.dt_venc.date().toString("yyyy-MM-dd")
        cat = self.txt_cat.text()
        obs = self.txt_obs.text()
        
        query = f"""
            UPDATE {tabela} 
            SET descricao=?, valor=?, data_vencimento=?, categoria=?, obs=?
            WHERE id=?
        """
        try:
            self.db.cursor.execute(query, (desc, val, dt, cat, obs, self.id_conta))
            self.db.conn.commit()
            QMessageBox.information(self, "Sucesso", "Lançamento atualizado!")
            self.accept() # Fecha a janela com sucesso
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao atualizar: {e}")

class ContasPagarForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        
        # --- APLICA O ESTILO DE FOCO NESTA TELA ---
        self.setStyleSheet(FOCUS_STYLE)

        # Layout Principal dividido em 2 partes
        main_layout = QVBoxLayout(self)
        
        # --- PARTE 1: Formulário de Lançamento ---
        form_group = QFrame()
        form_group.setStyleSheet("background-color: #ecf0f1; border-radius: 8px; padding: 10px;")
        form_layout = QFormLayout(form_group)
        
        lbl_title = QLabel("📋 Nova Conta a Pagar")
        lbl_title_font = QFont()
        lbl_title_font.setPointSize(14)
        lbl_title_font.setBold(True)
        lbl_title.setFont(lbl_title_font)
        lbl_title.setStyleSheet(f"color: {COLORS['accent']};")
        form_layout.addRow(lbl_title)

        self.txt_desc = QLineEdit()
        form_layout.addRow("Descrição:", self.txt_desc)
        
        self.cb_forn = QComboBox()
        setup_combo_behavior(self.cb_forn) # <--- Abre com TAB
        self.load_forn()
        form_layout.addRow("Fornecedor:", self.cb_forn)
        
        self.cb_cat = QComboBox()
        self.cb_cat.addItems(["Custos Operacionais", "Despesas Administrativas", "Impostos", "Fornecedores/Estoque", "Pessoal/Salários"])
        setup_combo_behavior(self.cb_cat) # <--- Abre com TAB
        form_layout.addRow("Categoria:", self.cb_cat)
        
        hbox_val = QHBoxLayout()
        self.spin_val = QDoubleSpinBox()
        self.spin_val.setMaximum(9999999)
        self.spin_val.setPrefix("R$ ")
        
        self.cb_st = QComboBox()
        self.cb_st.addItems(["Pendente", "Pago"])
        setup_combo_behavior(self.cb_st) # <--- Abre com TAB
        
        hbox_val.addWidget(self.spin_val)
        hbox_val.addWidget(self.cb_st)
        form_layout.addRow("Valor / Status:", hbox_val)
        
        self.dt_venc = QDateEdit(QDate.currentDate())
        self.dt_venc.setCalendarPopup(True)  # Calendário
        self.dt_venc.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Vencimento:", self.dt_venc)
        
        btn_add = QPushButton("💳 Lançar Conta")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.salvar)
        btn_add.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['accent']}; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
        """)
        form_layout.addRow(btn_add)
        
        main_layout.addWidget(form_group)
        
        # --- PARTE 2: Tabela de Pendências ---
        lbl_pend = QLabel("Contas Pendentes (Selecione para Baixar)")
        lbl_pend.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px; color: #333;")
        main_layout.addWidget(lbl_pend)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Descrição", "Valor", "Vencimento", "Ação", "Editar"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: white; color: black; border: 1px solid #ccc; }} 
            QHeaderView::section {{ background-color: {COLORS['secondary']}; color: white; font-weight: bold; padding: 8px; }}
        """)
        main_layout.addWidget(self.table)
        
        self.load_pendencias() 

    # Função para transformar ENTER em TAB
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.focusNextChild()
        else:
            super().keyPressEvent(event)

    def load_forn(self):
        self.cb_forn.clear()
        self.cb_forn.addItem("Avulso", None)
        try:
            self.db.cursor.execute("SELECT id, nome_razao FROM db_cli.entidades WHERE categoria = 'Fornecedor'")
            for i, n in self.db.cursor.fetchall(): self.cb_forn.addItem(n, i)
        except: pass

    def salvar(self):
        try:
            fid = self.cb_forn.currentData()
            st = self.cb_st.currentText()
            dp = datetime.now().strftime("%Y-%m-%d") if st == "Pago" else None
            
            dados = (self.txt_desc.text(), fid, self.cb_cat.currentText(), self.spin_val.value(), 
                     self.dt_venc.date().toString("yyyy-MM-dd"), dp, st, "Dinheiro", "")
            
            self.db.cursor.execute('INSERT INTO db_fin.contas_pagar (descricao, fornecedor_id, categoria, valor, data_vencimento, data_pagamento, status, forma_pagamento, obs) VALUES (?,?,?,?,?,?,?,?,?)', dados)
            self.db.conn.commit()
            
            self.txt_desc.setText("")
            self.spin_val.setValue(0)
            self.load_pendencias()
            print("Conta Salva!")
        except Exception as e: print(e)

    def load_pendencias(self):
        self.table.setRowCount(0)
        df = self.db.get_pendencias("Pagar")
        
        for i, row in df.iterrows():
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['descricao']))
            self.table.setItem(i, 2, QTableWidgetItem(f"R$ {row['valor']:,.2f}"))
            
            dt_fmt = datetime.strptime(row['data_vencimento'], "%Y-%m-%d").strftime("%d/%m/%Y")
            self.table.setItem(i, 3, QTableWidgetItem(dt_fmt))
            
            btn_baixa = QPushButton("✅ Pagar")
            btn_baixa.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {COLORS['success']}; 
                    color: white; 
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 10px;
                }}
                QPushButton:hover {{
                    background-color: #1e8449;
                }}
            """)
            btn_baixa.clicked.connect(lambda checked, id_c=row['id']: self.dar_baixa(id_c))
            self.table.setCellWidget(i, 4, btn_baixa)

            btn_edit = QPushButton("✏️ Editar")
            btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius:4px; padding:6px;")
            btn_edit.clicked.connect(lambda checked, id_c=row['id']: self.open_editor(id_c))
            self.table.setCellWidget(i, 5, btn_edit)

    def open_editor(self, id_conta):
        dlg = EntryEditorDialog(self.db, 'pagar', id_conta, self)
        if dlg.exec():
            self.load_pendencias()

    def dar_baixa(self, id_conta):
        if self.db.baixar_conta(id_conta, "Pagar"):
            self.load_pendencias()

class NovaVendaForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.itens_carrinho = []
        
        # --- ESTILO GERAL DA TELA ---
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; color: #2c3e50; }
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox { 
                padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px; background-color: white; min-height: 20px;
            }
            QLabel { font-weight: bold; }
            QTableWidget { border: 1px solid #bdc3c7; background-color: white; }
            QHeaderView::section { background-color: #34495e; color: white; padding: 6px; font-weight: bold; border: none; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # --- TÍTULO ---
        lbl_titulo = QLabel("🛒 Nova Venda / Pedido")
        lbl_titulo.setStyleSheet("font-size: 22px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(lbl_titulo)
        
        # --- CABEÇALHO (Card Branco) ---
        gb_header = QFrame()
        gb_header.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        form_h = QFormLayout(gb_header)
        form_h.setSpacing(15)
        form_h.setContentsMargins(20, 20, 20, 20)
        
        # Linha 1: Cliente e Data
        hbox1 = QHBoxLayout()
        self.cb_cli = QComboBox()
        self.cb_cli.setMinimumWidth(300)
        self.load_clientes()
        
        self.dt_emissao = QDateEdit(QDate.currentDate())
        self.dt_emissao.setCalendarPopup(True)
        self.dt_emissao.setDisplayFormat("dd/MM/yyyy")
        self.dt_emissao.setFixedWidth(120)
        
        hbox1.addWidget(QLabel("Cliente:"))
        hbox1.addWidget(self.cb_cli)
        hbox1.addStretch()
        hbox1.addWidget(QLabel("Data Emissão:"))
        hbox1.addWidget(self.dt_emissao)
        
        # Linha 2: Vendedor, NF, Status
        hbox2 = QHBoxLayout()
        self.txt_vendedor = QLineEdit(); self.txt_vendedor.setPlaceholderText("Nome do Vendedor")
        self.txt_nf = QLineEdit(); self.txt_nf.setPlaceholderText("000000")
        self.txt_nf.setFixedWidth(100)
        self.cb_status = QComboBox(); self.cb_status.addItems(["Aguardando Faturamento", "Faturado", "Entregue", "Cancelado"])
        
        hbox2.addWidget(QLabel("Vendedor:"))
        hbox2.addWidget(self.txt_vendedor)
        hbox2.addWidget(QLabel("NF-e:"))
        hbox2.addWidget(self.txt_nf)
        hbox2.addWidget(QLabel("Status:"))
        hbox2.addWidget(self.cb_status)
        
        form_h.addRow(hbox1)
        form_h.addRow(hbox2)
        layout.addWidget(gb_header)
        
        # --- PRODUTOS (Card Branco) ---
        gb_prod = QFrame()
        gb_prod.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        l_prod = QVBoxLayout(gb_prod)
        l_prod.setContentsMargins(20, 20, 20, 20)
        
        # Seletor de Produto
        hbox_p = QHBoxLayout()
        
        self.cb_produto = QComboBox()
        self.cb_produto.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed) # Faz esticar
        self.cb_produto.setEditable(True) # Permite digitar para buscar
        self.cb_produto.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.load_produtos() # <--- Carrega aqui
        self.cb_produto.currentIndexChanged.connect(self.atualizar_preco_input)

        self.spin_qtd = QDoubleSpinBox(); self.spin_qtd.setPrefix("Qtd: "); self.spin_qtd.setValue(1); self.spin_qtd.setFixedWidth(100)
        self.spin_preco = QDoubleSpinBox(); self.spin_preco.setPrefix("R$ "); self.spin_preco.setMaximum(999999); self.spin_preco.setFixedWidth(120)
        
        btn_add = QPushButton("Adicionar")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.adicionar_item)
        btn_add.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; font-weight: bold; border-radius: 4px; padding: 8px 15px; border: none; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        
        hbox_p.addWidget(self.cb_produto, 4) # Peso 4 para ocupar mais espaço
        hbox_p.addWidget(self.spin_qtd, 1)
        hbox_p.addWidget(self.spin_preco, 1)
        hbox_p.addWidget(btn_add, 1)
        l_prod.addLayout(hbox_p)
        
        # Tabela
        self.tb_itens = QTableWidget()
        self.tb_itens.setColumnCount(5)
        self.tb_itens.setHorizontalHeaderLabels(["ID", "Produto", "Qtd", "Unitário", "Subtotal"])
        self.tb_itens.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tb_itens.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tb_itens.verticalHeader().setVisible(False)
        self.tb_itens.setMinimumHeight(200)
        l_prod.addWidget(self.tb_itens)
        
        # Total
        hbox_tot = QHBoxLayout()
        self.lbl_total = QLabel("Total: R$ 0,00")
        self.lbl_total.setStyleSheet("font-size: 24px; font-weight: 900; color: #27ae60; margin-top: 10px;")
        hbox_tot.addStretch()
        hbox_tot.addWidget(self.lbl_total)
        l_prod.addLayout(hbox_tot)
        
        layout.addWidget(gb_prod)
        
        # --- FINANCEIRO (Card Verde Claro) ---
        gb_fin = QFrame()
        gb_fin.setStyleSheet("background-color: #e8f8f5; border-radius: 8px; border: 1px solid #a3e4d7;")
        l_fin = QHBoxLayout(gb_fin)
        l_fin.setContentsMargins(20, 15, 20, 15)
        
        self.cb_forma = QComboBox(); self.cb_forma.addItems(["Dinheiro", "Pix", "Cartão Crédito", "Cartão Débito", "Boleto"])
        self.spin_parcelas = QSpinBox(); self.spin_parcelas.setPrefix("Parcelas: "); self.spin_parcelas.setRange(1, 24)
        
        self.chk_receber_agora = QCheckBox("Pagamento da 1ª parcela realizado agora")
        self.chk_receber_agora.setStyleSheet("font-weight: bold; color: #16a085; margin-left: 10px;")
        
        l_fin.addWidget(QLabel("Forma de Pagamento:"))
        l_fin.addWidget(self.cb_forma)
        l_fin.addWidget(self.spin_parcelas)
        l_fin.addWidget(self.chk_receber_agora)
        l_fin.addStretch()
        
        layout.addWidget(gb_fin)
        
        # --- BOTÃO SALVAR ---
        btn_salvar = QPushButton("✅ FINALIZAR VENDA")
        btn_salvar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_salvar.setMinimumHeight(50)
        btn_salvar.clicked.connect(self.finalizar_venda)
        btn_salvar.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; color: white; font-size: 16px; font-weight: bold; border-radius: 8px; border: none; 
            }
            QPushButton:hover { background-color: #219150; }
            QPushButton:pressed { background-color: #1e8449; }
        """)
        layout.addWidget(btn_salvar)

    def load_clientes(self):
        self.cb_cli.clear()
        self.cb_cli.addItem("Consumidor Final / Avulso", None)
        try:
            self.db.cursor.execute("SELECT id, nome_razao FROM db_cli.entidades WHERE categoria='Cliente' ORDER BY nome_razao")
            for i, n in self.db.cursor.fetchall(): self.cb_cli.addItem(n, i)
        except: pass

    def load_produtos(self):
        """ Carrega produtos no ComboBox. """
        self.cb_produto.clear()
        try:
            # Garante que as colunas existem antes de chamar
            self.db.cursor.execute("SELECT id, nome, preco_venda FROM db_prod.produtos ORDER BY nome")
            produtos = self.db.cursor.fetchall()
            
            if not produtos:
                self.cb_produto.addItem("Nenhum produto cadastrado", None)
                return

            for pid, nome, preco in produtos:
                # UserData guarda o dicionário completo para acesso rápido
                item_text = f"{nome}  ---  R$ {preco:.2f}"
                self.cb_produto.addItem(item_text, userData={'id': pid, 'nome': nome, 'preco': preco})
                
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            self.cb_produto.addItem("Erro ao carregar", None)

    def atualizar_preco_input(self):
        data = self.cb_produto.currentData()
        if data and isinstance(data, dict): 
            self.spin_preco.setValue(data['preco'])
        else:
            self.spin_preco.setValue(0)

    def adicionar_item(self):
        data = self.cb_produto.currentData()
        if not data or not isinstance(data, dict): 
            QMessageBox.warning(self, "Aviso", "Selecione um produto válido.")
            return
        
        qtd = self.spin_qtd.value()
        if qtd <= 0: return

        preco = self.spin_preco.value()
        subtotal = qtd * preco
        
        item = {
            'id': data['id'],
            'nome': data['nome'],
            'qtd': qtd,
            'preco': preco,
            'subtotal': subtotal
        }
        self.itens_carrinho.append(item)
        
        row = self.tb_itens.rowCount()
        self.tb_itens.insertRow(row)
        self.tb_itens.setItem(row, 0, QTableWidgetItem(str(item['id'])))
        self.tb_itens.setItem(row, 1, QTableWidgetItem(item['nome']))
        self.tb_itens.setItem(row, 2, QTableWidgetItem(f"{item['qtd']:.2f}"))
        self.tb_itens.setItem(row, 3, QTableWidgetItem(f"R$ {item['preco']:.2f}"))
        self.tb_itens.setItem(row, 4, QTableWidgetItem(f"R$ {item['subtotal']:.2f}"))
        
        self.recalcular_total()

    def recalcular_total(self):
        total = sum(i['subtotal'] for i in self.itens_carrinho)
        self.lbl_total.setText(f"Total: R$ {total:,.2f}")
        return total

    def finalizar_venda(self):
        if not self.itens_carrinho:
            QMessageBox.warning(self, "Vazio", "Adicione produtos antes de finalizar.")
            return

        valor_total = self.recalcular_total()
        cli_id = self.cb_cli.currentData()
        dt_venda = self.dt_emissao.date().toString("yyyy-MM-dd")
        
        try:
            # 1. Salva Venda
            self.db.cursor.execute('''
                INSERT INTO main.vendas (data_venda, cliente_id, vendedor, valor_bruto, valor_liquido, status, nota_fiscal, forma_pagamento_prevista)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (dt_venda, cli_id, self.txt_vendedor.text(), valor_total, valor_total, self.cb_status.currentText(), self.txt_nf.text(), self.cb_forma.currentText()))
            venda_id = self.db.cursor.lastrowid
            
            # 2. Salva Itens e Baixa Estoque
            for item in self.itens_carrinho:
                self.db.cursor.execute('INSERT INTO main.itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?,?,?,?,?)', 
                                       (venda_id, item['id'], item['qtd'], item['preco'], item['subtotal']))
                
                self.db.cursor.execute("UPDATE db_prod.produtos SET estoque_atual = estoque_atual - ? WHERE id = ?", (item['qtd'], item['id']))

            # 3. Gera Parcelas
            parcelas = self.spin_parcelas.value()
            valor_parc = valor_total / parcelas
            receber_agora = self.chk_receber_agora.isChecked()
            
            for i in range(1, parcelas + 1):
                # Vencimento: 1ª parc hoje ou em 30 dias? Aqui assumi 30 dias para a 2ª em diante
                dias_add = (i - 1) * 30 if receber_agora else i * 30
                if receber_agora and i == 1: dias_add = 0
                
                vencimento = self.dt_emissao.date().addDays(dias_add).toString("yyyy-MM-dd")
                
                status = "Pendente"
                dt_receb = None
                val_rec = None
                conta = ""
                
                if i == 1 and receber_agora:
                    status = "Recebido"
                    dt_receb = dt_venda
                    val_rec = valor_parc
                    conta = "Caixa Balcão"
                
                self.db.cursor.execute('''
                    INSERT INTO db_fin.contas_receber 
                    (venda_id, descricao, cliente_id, num_parcela, valor_previsto, valor_recebido, data_vencimento, data_recebimento, status, forma_pagamento, conta_destino)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (venda_id, f"Venda #{venda_id} ({i}/{parcelas})", cli_id, f"{i}/{parcelas}", 
                      valor_parc, val_rec, vencimento, dt_receb, status, self.cb_forma.currentText(), conta))

            self.db.conn.commit()
            QMessageBox.information(self, "Sucesso", f"Venda #{venda_id} realizada com sucesso!")
            
            # Reset
            self.itens_carrinho = []
            self.tb_itens.setRowCount(0)
            self.lbl_total.setText("Total: R$ 0,00")
            self.load_produtos() # Recarrega para atualizar estoque se quiser mostrar depois
            
        except Exception as e:
            self.db.conn.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao salvar venda: {e}")

class BaixaContaDialog(QDialog):
    def __init__(self, db_context, conta_id, tipo="Receber", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Baixa de {tipo}")
        self.setFixedWidth(450) # Um pouco mais largo
        self.db = db_context
        self.conta_id = conta_id
        self.tipo = tipo
        self.comprovante_path = ""
        
        # Estilo Limpo
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { color: #2c3e50; font-size: 14px; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { 
                padding: 6px; border: 1px solid #bdc3c7; border-radius: 4px; background-color: white; 
            }
            QPushButton { border-radius: 4px; padding: 8px; font-weight: bold; }
        """)
        
        # Dados do Banco
        tabela = "db_fin.contas_receber" if tipo == "Receber" else "db_fin.contas_pagar"
        col_val = "valor_previsto" if tipo == "Receber" else "valor"
        
        self.db.cursor.execute(f"SELECT descricao, {col_val}, data_vencimento FROM {tabela} WHERE id=?", (conta_id,))
        row = self.db.cursor.fetchone()
        
        if not row:
            QMessageBox.critical(self, "Erro", "Conta não encontrada!")
            self.reject()
            return
            
        desc, valor_orig, vencto = row
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- HEADER INFORMATIVO ---
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: white; border-radius: 6px; border: 1px solid #ddd;")
        info_layout = QVBoxLayout(info_frame)
        
        l_desc = QLabel(desc)
        l_desc.setStyleSheet("font-size: 16px; font-weight: bold; color: #34495e;")
        l_val = QLabel(f"Valor Original: R$ {valor_orig:,.2f}")
        l_val.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        l_venc = QLabel(f"Vencimento: {datetime.strptime(vencto, '%Y-%m-%d').strftime('%d/%m/%Y')}")
        l_venc.setStyleSheet("font-size: 14px; color: #e74c3c; font-weight: bold;")
        
        info_layout.addWidget(l_desc)
        info_layout.addWidget(l_val)
        info_layout.addWidget(l_venc)
        layout.addWidget(info_frame)
        
        # --- FORMULÁRIO ---
        form = QFormLayout()
        form.setSpacing(10)
        
        self.dt_baixa = QDateEdit(QDate.currentDate())
        self.dt_baixa.setCalendarPopup(True)
        self.dt_baixa.setDisplayFormat("dd/MM/yyyy")
        
        self.spin_val_final = QDoubleSpinBox()
        self.spin_val_final.setMaximum(9999999)
        self.spin_val_final.setValue(valor_orig)
        self.spin_val_final.setPrefix("R$ ")
        
        self.cb_conta = QComboBox()
        self.cb_conta.addItems(["Banco Itaú", "Banco Bradesco", "Banco do Brasil", "Caixa Econômica", "Caixa Interno (Dinheiro)", "Cofre"])
        
        form.addRow("Data Pagamento:", self.dt_baixa)
        form.addRow("Valor Pago:", self.spin_val_final)
        form.addRow("Conta Destino:", self.cb_conta)
        layout.addLayout(form)
        
        # --- ANEXO ---
        self.btn_anexo = QPushButton("📎 Anexar Comprovante")
        self.btn_anexo.setStyleSheet("background-color: #3498db; color: white; border: none;")
        self.btn_anexo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_anexo.clicked.connect(self.selecionar_anexo)
        layout.addWidget(self.btn_anexo)
        
        # --- BOTÃO CONFIRMAR ---
        btn_confirm = QPushButton("✅ CONFIRMAR BAIXA")
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("background-color: #27ae60; color: white; border: none; font-size: 14px; margin-top: 10px;")
        btn_confirm.clicked.connect(self.confirmar)
        layout.addWidget(btn_confirm)

    def selecionar_anexo(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Selecionar Comprovante", "", "Arquivos (*.pdf *.jpg *.png *.jpeg)")
        if fname:
            self.comprovante_path = fname
            self.btn_anexo.setText(f"📎 {os.path.basename(fname)}")
            self.btn_anexo.setStyleSheet("background-color: #2ecc71; color: white; border: none;")

    def confirmar(self):
        val_final = self.spin_val_final.value()
        dt_baixa = self.dt_baixa.date().toString("yyyy-MM-dd")
        conta = self.cb_conta.currentText()
        
        tabela = "db_fin.contas_receber" if self.tipo == "Receber" else "db_fin.contas_pagar"
        status = "Recebido" if self.tipo == "Receber" else "Pago"
        col_data = "data_recebimento" if self.tipo == "Receber" else "data_pagamento"
        col_val_real = "valor_recebido" if self.tipo == "Receber" else "valor"
        
        try:
            if self.tipo == "Receber":
                self.db.cursor.execute(f'''
                    UPDATE {tabela} SET 
                    status=?, {col_data}=?, valor_recebido=?, conta_destino=?, comprovante_path=?
                    WHERE id=?
                ''', (status, dt_baixa, val_final, conta, self.comprovante_path, self.conta_id))
            else:
                # Adaptação para tabela de pagar
                self.db.cursor.execute(f'''
                    UPDATE {tabela} SET 
                    status=?, {col_data}=?, valor=?
                    WHERE id=?
                ''', (status, dt_baixa, val_final, self.conta_id))
                
            self.db.conn.commit()
            QMessageBox.information(self, "Sucesso", "Baixa realizada com sucesso!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao baixar conta: {e}")

class ContasReceberForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.setStyleSheet(FOCUS_STYLE) # Aplica o estilo de foco
        
        # Layout Principal
        main_layout = QVBoxLayout(self)
        
        # --- PARTE 1: Formulário de Lançamento (Estilo Frame Cinza) ---
        form_group = QFrame()
        form_group.setStyleSheet("background-color: #ecf0f1; border-radius: 8px; padding: 10px;")
        form_layout = QFormLayout(form_group)
        
        lbl_title = QLabel("📋 Nova Receita")
        lbl_title_font = QFont()
        lbl_title_font.setPointSize(14)
        lbl_title_font.setBold(True)
        lbl_title.setFont(lbl_title_font)
        # Usa cor de sucesso (Verde) para diferenciar do Pagar (Vermelho) mas mantendo o layout
        lbl_title.setStyleSheet(f"color: {COLORS['success']};") 
        form_layout.addRow(lbl_title)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ex: Venda de Serviço, Consultoria...")
        form_layout.addRow("Descrição:", self.txt_desc)
        
        # Cliente
        hbox_cli = QHBoxLayout()
        self.cb_cli = QComboBox()
        setup_combo_behavior(self.cb_cli) # Abre no Tab
        self.load_cli()
        
        btn_reload = QPushButton("↻")
        btn_reload.setFixedSize(30, 30)
        btn_reload.clicked.connect(self.load_cli)
        btn_reload.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 3px;")
        
        hbox_cli.addWidget(self.cb_cli)
        hbox_cli.addWidget(btn_reload)
        form_layout.addRow("Cliente:", hbox_cli)
        
        # Valores
        hbox_val = QHBoxLayout()
        self.spin_val = QDoubleSpinBox()
        self.spin_val.setMaximum(9999999)
        self.spin_val.setPrefix("R$ ")
        
        self.cb_st = QComboBox()
        self.cb_st.addItems(["Pendente", "Recebido"])
        setup_combo_behavior(self.cb_st)
        
        hbox_val.addWidget(self.spin_val)
        hbox_val.addWidget(self.cb_st)
        form_layout.addRow("Valor / Status:", hbox_val)
        
        # Vencimento
        self.dt_venc = QDateEdit(QDate.currentDate())
        self.dt_venc.setCalendarPopup(True) # Calendário
        self.dt_venc.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Vencimento:", self.dt_venc)
        
        # Botão Lançar
        btn_add = QPushButton("💵 Lançar Receita")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.salvar)
        btn_add.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['success']}; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: #1e8449;
            }}
        """)
        form_layout.addRow(btn_add)
        
        main_layout.addWidget(form_group)
        
        # --- PARTE 2: Tabela de Pendências ---
        lbl_pend = QLabel("Recebimentos Pendentes")
        lbl_pend.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px; color: #333;")
        main_layout.addWidget(lbl_pend)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6) # Colunas: ID, Desc, Valor, Data, Ação, Editar
        self.table.setHorizontalHeaderLabels(["ID", "Descrição", "Valor", "Vencimento", "Ação", "Editar"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Estilo tabela clean
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: white; color: black; border: 1px solid #ccc; }} 
            QHeaderView::section {{ background-color: {COLORS['secondary']}; color: white; font-weight: bold; padding: 8px; }}
        """)
        main_layout.addWidget(self.table)
        
        self.load_pendencias() # Carrega dados ao abrir

    # Permitir navegação com Enter
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.focusNextChild()
        else:
            super().keyPressEvent(event)

    def load_cli(self):
        self.cb_cli.clear()
        self.cb_cli.addItem("Cliente Avulso / Balcão", None)
        try:
            self.db.cursor.execute("SELECT id, nome_razao FROM db_cli.entidades WHERE categoria = 'Cliente'")
            for i, n in self.db.cursor.fetchall(): self.cb_cli.addItem(n, i)
        except: pass

    def dar_baixa(self, id_conta):
        # Em vez de baixar direto, abre o diálogo detalhado
        dlg = BaixaContaDialog(self.db, id_conta, tipo="Receber", parent=self)
        if dlg.exec():
            self.load_pendencias() # Recarrega a tabela
            QMessageBox.information(self, "Sucesso", "Conta baixada com sucesso!")

    def salvar(self):
        try:
            cid = self.cb_cli.currentData()
            st = self.cb_st.currentText()
            dr = datetime.now().strftime("%Y-%m-%d") if st == "Recebido" else None
            
            dados = (self.txt_desc.text(), cid, self.spin_val.value(), 
                     self.dt_venc.date().toString("yyyy-MM-dd"), dr, st, "Dinheiro", "")
            
            self.db.cursor.execute('INSERT INTO db_fin.contas_receber (descricao, cliente_id, valor, data_vencimento, data_recebimento, status, forma_pagamento, obs) VALUES (?,?,?,?,?,?,?,?)', dados)
            self.db.conn.commit()
            
            self.txt_desc.setText("")
            self.spin_val.setValue(0)
            self.load_pendencias()
            print("Receita Salva!")
        except Exception as e: print(e)

    def load_pendencias(self):
        self.table.setRowCount(0)
        df = self.db.get_pendencias("Receber")
        
        for i, row in df.iterrows():
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['descricao']))
            self.table.setItem(i, 2, QTableWidgetItem(f"R$ {row['valor']:,.2f}"))
            
            dt_fmt = datetime.strptime(row['data_vencimento'], "%Y-%m-%d").strftime("%d/%m/%Y")
            self.table.setItem(i, 3, QTableWidgetItem(dt_fmt))
            
            # Botão Baixar
            btn_baixa = QPushButton("✅ Receber")
            btn_baixa.setStyleSheet("background-color: #27ae60; color: white; border-radius: 4px; padding: 6px;")
            btn_baixa.clicked.connect(lambda checked, id_c=row['id']: self.dar_baixa(id_c))
            self.table.setCellWidget(i, 4, btn_baixa)

            # Botão Editar
            btn_edit = QPushButton("✏️ Editar")
            btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius:4px; padding:6px;")
            btn_edit.clicked.connect(lambda checked, id_c=row['id']: self.open_editor(id_c))
            self.table.setCellWidget(i, 5, btn_edit)

    def open_editor(self, id_conta):
        dlg = EntryEditorDialog(self.db, 'receber', id_conta, self)
        if dlg.exec():
            self.load_pendencias()

    def dar_baixa(self, id_conta):
        if self.db.baixar_conta(id_conta, "Receber"):
            self.load_pendencias()

class RelatorioDREForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        main = QVBoxLayout(self)
        
        # --- FILTROS ---
        filt = QFrame()
        filt.setStyleSheet("background-color: #ecf0f1; border-radius: 8px; padding: 10px;")
        hf = QHBoxLayout(filt)
        
        # Combo
        self.cb_periodo = QComboBox()
        self.cb_periodo.setMinimumWidth(180)
        self.cb_periodo.setStyleSheet("QComboBox { padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px; background: white; color: black; font-weight: bold; }")
        self.carregar_periodos()
        
        # Datas
        style_date = "QDateEdit { background-color: white; color: black; border: 1px solid #bdc3c7; border-radius: 4px; padding: 4px; min-width: 110px; }"
        
        self.di = QDateEdit(QDate.currentDate().addDays(-30))
        self.di.setCalendarPopup(True)
        self.di.setDisplayFormat("dd/MM/yyyy")
        self.di.setStyleSheet(style_date)
        
        self.df = QDateEdit(QDate.currentDate())
        self.df.setCalendarPopup(True)
        self.df.setDisplayFormat("dd/MM/yyyy")
        self.df.setStyleSheet(style_date)
        
        self.cb_periodo.currentIndexChanged.connect(self.atualizar_datas_pelo_combo)
        
        btn = QPushButton("Gerar DRE")
        btn.clicked.connect(self.gerar)
        btn.setStyleSheet("""
            QPushButton { background-color: #2c3e50; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background-color: #34495e; }
        """)
        
        hf.addWidget(QLabel("Período:", styleSheet="color:black; font-weight:bold;"))
        hf.addWidget(self.cb_periodo)
        hf.addWidget(QLabel(" De:", styleSheet="color:black; font-weight:bold;"))
        hf.addWidget(self.di)
        hf.addWidget(QLabel("Até:", styleSheet="color:black; font-weight:bold;"))
        hf.addWidget(self.df)
        hf.addWidget(btn)
        hf.addStretch()
        main.addWidget(filt)
        
        # --- TABELA ---
        self.tb = QTableWidget()
        self.tb.setColumnCount(3)
        self.tb.setHorizontalHeaderLabels(["Grupo", "Detalhe", "Valor"])
        self.tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tb.setStyleSheet("""
            QTableWidget { background-color: white; color: black; font-size: 14px; border: 1px solid #bdc3c7; } 
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 6px; }
        """)
        self.tb.setShowGrid(False)
        self.tb.verticalHeader().setVisible(False)
        main.addWidget(self.tb)
        
        self.atualizar_datas_pelo_combo()
        self.gerar()

    def carregar_periodos(self):
        self.cb_periodo.clear()
        self.cb_periodo.addItem("Todo o Período", userData="ALL")
        meses = self.db.get_meses_com_movimento()
        nomes_meses = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril', '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
        for ano, mes in meses:
            self.cb_periodo.addItem(f"{nomes_meses.get(mes, mes)} {ano}", userData=(ano, mes))

    def atualizar_datas_pelo_combo(self):
        data = self.cb_periodo.currentData()
        if data == "ALL" or data is None:
            self.di.setDate(QDate(2000, 1, 1))
            self.df.setDate(QDate(2100, 12, 31))
        else:
            ano, mes = int(data[0]), int(data[1])
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            self.di.setDate(QDate(ano, mes, 1))
            self.df.setDate(QDate(ano, mes, ultimo_dia))

    def add(self, lb, val, tot=False, sub=False):
        r = self.tb.rowCount()
        self.tb.insertRow(r)
        i1 = QTableWidgetItem(lb)
        i2 = QTableWidgetItem("")
        i3 = QTableWidgetItem(f"R$ {val:,.2f}")
        i3.setTextAlignment(Qt.AlignmentFlag.AlignRight)
        if tot:
            c = QColor("#27ae60") if val >= 0 else QColor("#c0392b")
            for x in [i1,i2,i3]: x.setBackground(c); x.setForeground(Qt.GlobalColor.white); x.setFont(self.font_bold())
        elif sub:
            c = QColor("#ecf0f1")
            for x in [i1,i2,i3]: x.setBackground(c); x.setFont(self.font_bold()); x.setForeground(Qt.GlobalColor.black)
        self.tb.setItem(r,0,i1); self.tb.setItem(r,1,i2); self.tb.setItem(r,2,i3)

    def add_det(self, nm, val):
        r = self.tb.rowCount()
        self.tb.insertRow(r)
        self.tb.setItem(r,0,QTableWidgetItem(""))
        self.tb.setItem(r,1,QTableWidgetItem(nm))
        it = QTableWidgetItem(f"({val:,.2f})")
        it.setForeground(Qt.GlobalColor.red); it.setTextAlignment(Qt.AlignmentFlag.AlignRight)
        self.tb.setItem(r,2,it)

    def font_bold(self):
        f = self.font(); f.setBold(True); return f

    def gerar(self):
        self.tb.setRowCount(0)
        # USA AS DATAS DOS CAMPOS
        di = self.di.date().toString("yyyy-MM-dd")
        df_end = self.df.date().toString("yyyy-MM-dd")
        
        df_r, df_d = self.db.get_dre_data(di, df_end)
        
        rb = df_r['valor'].sum() if not df_r.empty else 0.0
        imp = df_d[df_d['grupo'] == '(-) Impostos']
        t_imp = imp['valor'].sum() if not imp.empty else 0.0
        rl = rb - t_imp
        cust = df_d[df_d['grupo'] == '(-) Custos (CMV)']
        t_cust = cust['valor'].sum() if not cust.empty else 0.0
        lb = rl - t_cust
        desp = df_d[df_d['grupo'] == '(-) Despesas Operacionais']
        t_desp = desp['valor'].sum() if not desp.empty else 0.0
        ll = lb - t_desp
        
        self.add("(=) RECEITA BRUTA", rb, sub=True)
        if not df_r.empty:
            for _, r in df_r.iterrows():
                row = self.tb.rowCount()
                self.tb.insertRow(row)
                self.tb.setItem(row, 1, QTableWidgetItem(f"   + {r['categoria']}"))
                self.tb.setItem(row, 2, QTableWidgetItem(f"{r['valor']:,.2f}"))

        self.add("(-) IMPOSTOS", -t_imp)
        for _, r in imp.iterrows(): self.add_det(r['categoria'], r['valor'])
        self.add("(=) RECEITA LÍQUIDA", rl, sub=True)
        self.add("(-) CUSTOS (CMV)", -t_cust)
        for _, r in cust.iterrows(): self.add_det(r['categoria'], r['valor'])
        self.add("(=) LUCRO BRUTO", lb, sub=True)
        self.add("(-) DESPESAS OP.", -t_desp)
        for _, r in desp.iterrows(): self.add_det(r['categoria'], r['valor'])
        self.tb.insertRow(self.tb.rowCount())
        self.add("(=) LUCRO LÍQUIDO", ll, tot=True)

class FluxoCaixaForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        main = QVBoxLayout(self)
        
        # --- FILTROS ---
        filt = QFrame()
        filt.setStyleSheet("background-color: #ffffff; border: 2px solid #3498db; border-radius: 8px; padding: 12px;")
        hf = QHBoxLayout(filt)
        
        self.cb_periodo = QComboBox()
        self.cb_periodo.setMinimumWidth(180)
        self.cb_periodo.setStyleSheet("QComboBox { padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px; background: white; color: black; font-weight: bold; }")
        self.carregar_periodos()
        
        style_date = "QDateEdit { background-color: white; color: black; border: 1px solid #bdc3c7; border-radius: 4px; padding: 5px; min-width: 110px; }"
        
        self.di = QDateEdit(QDate.currentDate().addDays(-30))
        self.di.setCalendarPopup(True)
        self.di.setDisplayFormat("dd/MM/yyyy")
        self.di.setStyleSheet(style_date)
        
        self.df = QDateEdit(QDate.currentDate())
        self.df.setCalendarPopup(True)
        self.df.setDisplayFormat("dd/MM/yyyy")
        self.df.setStyleSheet(style_date)
        
        self.cb_periodo.currentIndexChanged.connect(self.atualizar_datas_pelo_combo)
        
        btn = QPushButton("🔍 Filtrar")
        btn.clicked.connect(self.load)
        btn.setStyleSheet("""
            QPushButton { background-color: #2c3e50; color: white; font-weight: bold; padding: 8px 16px; border: none; border-radius: 5px; }
            QPushButton:hover { background-color: #3498db; }
        """)
        
        hf.addWidget(QLabel("Período:", styleSheet="color: #2c3e50; font-weight: bold;"))
        hf.addWidget(self.cb_periodo)
        hf.addWidget(QLabel(" De:", styleSheet="color: #2c3e50; font-weight: bold;"))
        hf.addWidget(self.di)
        hf.addWidget(QLabel("Até:", styleSheet="color: #2c3e50; font-weight: bold;"))
        hf.addWidget(self.df)
        hf.addWidget(btn)
        hf.addStretch()
        main.addWidget(filt)
        
        # --- KPIS ---
        hk = QHBoxLayout()
        self.k_ent = self.mk_kpi("Entradas", "#27ae60")
        self.k_sai = self.mk_kpi("Saídas", "#c0392b")
        self.k_sal = self.mk_kpi("Saldo", "#2980b9")
        hk.addWidget(self.k_ent)
        hk.addWidget(self.k_sai)
        hk.addWidget(self.k_sal)
        main.addLayout(hk)
        
        # --- TABELA ---
        self.tb = QTableWidget()
        self.tb.setColumnCount(5)
        self.tb.setHorizontalHeaderLabels(["Data", "Descrição", "Tipo", "Valor", "Editar"])
        self.tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tb.setStyleSheet("""
            QTableWidget { background-color: white; color: black; border: 1px solid #bdc3c7; } 
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 8px; }
        """)
        main.addWidget(self.tb)
        
        self.atualizar_datas_pelo_combo()
        self.load()

    def carregar_periodos(self):
        self.cb_periodo.clear()
        self.cb_periodo.addItem("Todo o Período", userData="ALL")
        meses = self.db.get_meses_com_movimento()
        nomes_meses = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril', '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
        for ano, mes in meses:
            self.cb_periodo.addItem(f"{nomes_meses.get(mes, mes)} {ano}", userData=(ano, mes))

    def atualizar_datas_pelo_combo(self):
        data = self.cb_periodo.currentData()
        if data == "ALL" or data is None:
            self.di.setDate(QDate(2000, 1, 1))
            self.df.setDate(QDate(2100, 12, 31))
        else:
            ano, mes = int(data[0]), int(data[1])
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            self.di.setDate(QDate(ano, mes, 1))
            self.df.setDate(QDate(ano, mes, ultimo_dia))

    def mk_kpi(self, t, c):
        f = QFrame()
        f.setStyleSheet(f"background-color: {c}; border-radius: 8px; color: white;")
        f.setFixedHeight(80)
        v = QVBoxLayout(f)
        l1 = QLabel(t)
        l2 = QLabel("R$ 0,00")
        l2.setStyleSheet("font-size: 20px; font-weight: bold;")
        v.addWidget(l1); v.addWidget(l2)
        f.val = l2
        return f

    def load(self):
        # USA AS DATAS DOS CAMPOS
        di = self.di.date().toString("yyyy-MM-dd")
        df_end = self.df.date().toString("yyyy-MM-dd")
        
        df = self.db.get_fluxo_caixa(di, df_end)
        
        self.tb.setRowCount(len(df))
        te, ts = 0.0, 0.0
        
        for i, r in df.iterrows():
            v = r['valor']
            dt = datetime.strptime(r['data'], "%Y-%m-%d").strftime("%d/%m/%Y")
            self.tb.setItem(i,0,QTableWidgetItem(dt))
            self.tb.setItem(i,1,QTableWidgetItem(r['descricao']))
            self.tb.setItem(i,2,QTableWidgetItem(r['tipo']))
            it = QTableWidgetItem(f"R$ {v:,.2f}")
            if v < 0: it.setForeground(Qt.GlobalColor.red); ts += v
            else: it.setForeground(Qt.GlobalColor.darkGreen); te += v
            self.tb.setItem(i,3,it)

            origem = r.get('origem', None)
            origem_id = int(r.get('origem_id')) if pd.notnull(r.get('origem_id')) else None
            
            if origem in ['pagar', 'receber'] and origem_id:
                btn_edit = QPushButton("✏️")
                btn_edit.setFixedSize(30, 30)
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius:4px; font-weight:bold;")
                btn_edit.clicked.connect(lambda checked, o=origem, oid=origem_id: self.edit_entry(o, oid))
                self.tb.setCellWidget(i, 4, btn_edit)
            else:
                self.tb.setItem(i, 4, QTableWidgetItem("-"))
        
        self.k_ent.val.setText(f"R$ {te:,.2f}")
        self.k_sai.val.setText(f"R$ {ts:,.2f}")
        self.k_sal.val.setText(f"R$ {te+ts:,.2f}")

    def edit_entry(self, origem, origem_id):
        if not origem or not origem_id: return
        try:
            dlg = EntryEditorDialog(self.db, origem, origem_id, self)
            if dlg.exec(): self.load()
        except NameError:
            QMessageBox.critical(self, "Erro", "EntryEditorDialog não encontrada.")

class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 300)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint) # Remove a barra de título
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Fundo transparente para arredondar

        # Layout Principal com fundo arredondado
        self.main_layout = QVBoxLayout(self)
        self.frame = QFrame()
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #1e272e;
                border-radius: 15px;
                border: 2px solid #34495e;
            }
        """)
        self.main_layout.addWidget(self.frame)
        
        self.layout_frame = QVBoxLayout(self.frame)
        self.layout_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- LOGO ---
        self.logo_label = QLabel()
        
        if os.path.exists(PATH_LOGO):
            pixmap = QPixmap(PATH_LOGO)
            self.logo_label.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_label.setText("FINANCE\nCONTROL")
            self.logo_label.setStyleSheet("color: #0fbcf9; font-weight: bold; font-size: 25px;")
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        self.layout_frame.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout_frame.addSpacing(20)

        # --- TEXTO "CARREGANDO" ---
        self.lbl_loading = QLabel("Carregando módulos...")
        self.lbl_loading.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        self.layout_frame.addWidget(self.lbl_loading, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout_frame.addSpacing(10)

        # --- BARRA DE PROGRESSO ---
        self.progress = QProgressBar()
        self.progress.setFixedWidth(300)
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False) # Esconde a porcentagem dentro da barra
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #2f3542;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #0fbcf9; /* Azul Neon */
                border-radius: 5px;
            }
        """)
        self.layout_frame.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

    def update_progress(self, valor, texto):
        self.progress.setValue(valor)
        self.lbl_loading.setText(texto)
        
# --- 3. JANELA PRINCIPAL (Main Window) ---

# --- TELA DE LOGIN KEYAUTH ---
class LoginDialog(QDialog):
    def __init__(self, api_instance):
        super().__init__()
        self.api = api_instance
        self.setWindowTitle("Autenticação")
        self.setFixedSize(400, 300)
        self.setStyleSheet(f"background-color: {COLORS['light_bg']};")

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Logo ou Título
        lbl_title = QLabel("Login do Usuário")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['primary']}; margin-bottom: 10px;")
        layout.addWidget(lbl_title)

        # Campos de entrada
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Usuário")
        self.user_input.setStyleSheet(FOCUS_STYLE) # Usa seu estilo existente
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Senha")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet(FOCUS_STYLE)

        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)

        # Botão Entrar
        self.btn_login = QPushButton("ENTRAR")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
        """)
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)

        # Status
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {COLORS['accent']}; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.setLayout(layout)

    def handle_login(self):
        username = self.user_input.text()
        password = self.pass_input.text()

        if not username or not password:
            self.lbl_status.setText("Preencha todos os campos!")
            return

        self.btn_login.setText("Verificando...")
        self.btn_login.setEnabled(False)
        QApplication.processEvents() # Atualiza UI

        # Chamada ao KeyAuth
        self.api.login(username, password)
        
        if self.api.check():
            self.accept() # Fecha o diálogo com sucesso
        else:
            self.lbl_status.setText("Login falhou. Verifique suas credenciais.")
            self.btn_login.setText("ENTRAR")
            self.btn_login.setEnabled(True)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema Financeiro Integrado")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        # Define ícone da janela
        if os.path.exists(PATH_LOGO):
            icon = QIcon(PATH_LOGO)
            if not icon.isNull():
                self.setWindowIcon(icon)
        
        # Inicializa o contexto de dados
        self.db_context = DataContext()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SIDEBAR (Barra Lateral) ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet("""
            QFrame { background-color: #2c2c2c; color: #d2dae2; } 
            QListWidget { border: none; background-color: transparent; outline: none; margin-top: 10px;} 
            QListWidget::item { padding: 12px 20px; font-size: 15px; } 
            QListWidget::item:selected { background-color: #3c40c6; color: white; border-left: 4px solid #0fbcf9; } 
            QListWidget::item:hover { background-color: #485460; }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # --- LOGO ---
        lbl_logo = QLabel()
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(PATH_LOGO):
            pix = QPixmap(PATH_LOGO)
            lbl_logo.setPixmap(pix.scaled(150, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_logo.setStyleSheet("padding: 30px 0;")
        else:
            lbl_logo.setText("FINANCE\nCONTROL")
            lbl_logo.setStyleSheet("font-size: 20px; font-weight: 900; color: #0fbcf9; padding: 30px 0;")
            
        sidebar_layout.addWidget(lbl_logo)

        # --- MENU LATERAL ---
        self.menu_list = QListWidget()
        self.menu_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.menu_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        sidebar_layout.addWidget(self.menu_list, 1)

        # --- BOTÃO DE BACKUP ---
        btn_backup = QPushButton("💾 Fazer Backup")
        btn_backup.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['warning']}; 
                color: white; 
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 5px;
                margin: 10px;
            }}
            QPushButton:hover {{
                background-color: #d68910;
            }}
        """)
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.clicked.connect(self.fazer_backup)
        sidebar_layout.addWidget(btn_backup)
        
        main_layout.addWidget(self.sidebar)

        # --- ÁREA DE CONTEÚDO (STACK) ---
        # ATENÇÃO: Criamos a área de conteúdo ANTES de adicionar os widgets
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("background-color: #f1f2f6;")
        main_layout.addWidget(self.content_area)

        # --- INICIALIZAÇÃO DAS TELAS ---
        self.tab_nova_venda = NovaVendaForm(self.db_context)
        self.tab_cadastro_prod = CadastroProdutoForm(self.db_context)
        # Conecta sinal de produto salvo para atualizar a venda
        self.tab_cadastro_prod.produto_salvo_signal.connect(self.tab_nova_venda.load_produtos)

        # Instancia as telas de Clientes e Fornecedores (Nova Classe Unificada)
        self.page_clientes = GerenciamentoEntidades(self.db_context, "Cliente")
        self.page_fornecedores = GerenciamentoEntidades(self.db_context, "Fornecedor")

        # --- MAPEAMENTO DO MENU ---
        self.items_map = [
            ("📊 Dashboard Gerencial", DashboardTab(self.db_context)),
            ("👥 Cadastro de Clientes", self.page_clientes), 
            ("🏢 Cadastro de Fornecedores", self.page_fornecedores),
            ("📦 Cadastro de Produtos", self.tab_cadastro_prod), 
            ("💳 Contas a Pagar", ContasPagarForm(self.db_context)),
            ("🛒 Nova Venda / Pedido", self.tab_nova_venda), 
            ("💰 Contas a Receber", ContasReceberForm(self.db_context)),
            ("💵 Fluxo de Caixa", FluxoCaixaForm(self.db_context)),
            ("📈 Relatório DRE", RelatorioDREForm(self.db_context))
        ]
        
        # Popula o menu e a Stack ao mesmo tempo
        for nome, widget in self.items_map:
            self.menu_list.addItem(QListWidgetItem(nome))
            self.content_area.addWidget(widget)
            
        self.menu_list.currentRowChanged.connect(self.switch_tab)

    def switch_tab(self, index):
        self.content_area.setCurrentIndex(index)

    def fazer_backup(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecione a pasta para salvar o backup", os.path.expanduser("~"))
        if pasta: 
            sucesso, resultado = self.db_context.criar_backup(pasta)
            if sucesso:
                # Usa a função mostrar_mensagem que criamos lá no topo do arquivo
                try:
                    mostrar_mensagem(self, 'info', "Sucesso", f"Backup salvo em:\n\n{resultado}")
                except:
                    QMessageBox.information(self, "Sucesso", f"Backup salvo em:\n\n{resultado}")
            else:
                try:
                    mostrar_mensagem(self, 'erro', "Erro", f"Não foi possível criar o backup.\n\nErro: {resultado}")
                except:
                    QMessageBox.critical(self, "Erro", f"Não foi possível criar o backup.\n\nErro: {resultado}")

# --- FUNÇÃO AUXILIAR DE CHECKSUM (Necessária para o KeyAuth) ---
def get_checksum():
    md5_hash = hashlib.md5()
    try:
        file = open(sys.argv[0], "rb")
        md5_hash.update(file.read())
        file.close()
    except:
        pass # Em alguns ambientes de dev pode falhar, mas ok
    return md5_hash.hexdigest()

if __name__ == "__main__":
    # Define ID para o Windows agrupar ícones corretamente na barra de tarefas
    myappid = 'minhaempresa.meusistema.financeiro.2.0' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
        
    # Estilo Global Corrigido (Incluindo Calendário)
    app.setStyleSheet("""
        QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox { 
            padding: 8px; 
            border: 1px solid #ccc; 
            border-radius: 4px; 
            background: white; 
            color: black; 
        } 
        QComboBox QAbstractItemView { 
            color: black; 
            background-color: white; 
            selection-background-color: #3c40c6; 
            selection-color: white; 
        } 
        QLabel { color: #333; }
        
        /* Estilo do Calendário */
        QCalendarWidget QWidget { background-color: white; color: black; }
        QCalendarWidget QTableView { background-color: white; color: black; }
        QCalendarWidget QToolButton { color: black; icon-size: 20px; }
        QCalendarWidget QMenu { background-color: white; color: black; }
        QCalendarWidget QSpinBox { background-color: white; color: black; }
        QCalendarWidget QAbstractItemView:enabled {
            color: black;
            background-color: white;
            selection-background-color: #3498db;
            selection-color: white;
        }
    """)
    
    # --- CONFIGURAÇÃO DO KEYAUTH ---
    # Pegue estes dados no site https://keyauth.cc/app/
    # keyauthapp = api(
    #     name = "dashpoin.auth",     # Application Name
    #     ownerid = os.getenv("KEYAUTH_OWNER_ID", "your-keyauth-owner-id"),     # Owner ID
    #     #secret = "d0d44aa9b59a242c81539b0120c3857ad7c301e9739be67f623407da5d8a3840",        # Application Secret
    #     version = "1.0",              # Application Version
    #     hash_to_check = get_checksum()
    # )

    # --- TELA DE LOGIN ---
    #login = LoginDialog(keyauthapp)
    
    # Se o login for bem-sucedido (retornar accepted)
    # if login.exec() == QDialog.DialogCode.Accepted:
    #     # Inicializa a janela principal
    #     # IMPORTANTE: Verifique se sua classe principal se chama MainWindow
    #     # Se for DashboardTab ou outra, altere abaixo:
    #     window = MainWindow() 
    #     window.show()
    #     sys.exit(app.exec())
    # else:
    #     # Se fechar a janela de login ou falhar
    #     sys.exit()

    # 1. Tela de Carregamento
    splash = LoadingScreen()
    splash.show()
    
    # Centraliza Splash
    ag = splash.frameGeometry()
    cp = app.primaryScreen().availableGeometry().center()
    ag.moveCenter(cp)
    splash.move(ag.topLeft())

    # 2. Carregamento simulado
    splash.update_progress(10, "Iniciando sistema...")
    app.processEvents()
    time.sleep(0.3)
    
    splash.update_progress(30, "Verificando estrutura de dados...")
    # Ao instanciar MainWindow, o DataContext roda e cria as novas tabelas (itens_venda, etc)
    window = MainWindow() 
    app.processEvents()
    
    splash.update_progress(70, "Carregando módulos de vendas...")
    app.processEvents()
    time.sleep(0.3)
    
    splash.update_progress(100, "Sistema pronto!")
    app.processEvents()
    time.sleep(0.3)
    
    splash.close()
    window.show()
    
    sys.exit(app.exec())