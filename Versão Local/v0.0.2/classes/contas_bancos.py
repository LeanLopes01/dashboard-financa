from classes.cadastros import EntryEditorDialog
from classes.funcoesAuxiliares import FOCUS_STYLE, MoneySpinBox, formatar_moeda_br, mostrar_mensagem, setup_combo_behavior, COLORS
from classes.pedidos import BaixaContaDialog
from classes.vizualizacao import DashboardCard
from .imports import *

class ContasReceberForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.setStyleSheet(FOCUS_STYLE) # Aplica o estilo de foco
        
        # Layout Principal
        main_layout = QVBoxLayout(self)
        
        # --- PARTE 1: FormulÃ¡rio de LanÃ§amento ---
        form_group = QFrame()
        form_group.setStyleSheet("background-color: #ecf0f1; border-radius: 8px; padding: 10px;")
        form_layout = QFormLayout(form_group)
        
        lbl_title = QLabel("ðŸ“‹ Nova Receita")
        lbl_title_font = QFont()
        lbl_title_font.setPointSize(14)
        lbl_title_font.setBold(True)
        lbl_title.setFont(lbl_title_font)
        lbl_title.setStyleSheet(f"color: {COLORS['success']};") 
        form_layout.addRow(lbl_title)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ex: Venda de ServiÃ§o, Consultoria...")
        form_layout.addRow("DescriÃ§Ã£o:", self.txt_desc)
        
        # Cliente
        hbox_cli = QHBoxLayout()
        self.cb_cli = QComboBox()
        setup_combo_behavior(self.cb_cli)
        self.load_cli()
        
        btn_reload = QPushButton("â†»")
        btn_reload.setFixedSize(30, 30)
        btn_reload.clicked.connect(self.load_cli)
        btn_reload.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 3px; border: none;")
        
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
        self.dt_venc.setCalendarPopup(True)
        self.dt_venc.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Vencimento:", self.dt_venc)
        
        # BotÃ£o LanÃ§ar
        btn_add = QPushButton("ðŸ’µ LanÃ§ar Receita")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.salvar)
        btn_add.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {COLORS['success']}; 
                color: white; font-weight: bold; padding: 10px; border: none; border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: #1e8449; }}
        """)
        form_layout.addRow(btn_add)
        
        main_layout.addWidget(form_group)
        
        # --- PARTE 2: Tabela ---
        lbl_pend = QLabel("Recebimentos Pendentes")
        lbl_pend.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px; color: #333;")
        main_layout.addWidget(lbl_pend)
        
        self.table = QTableWidget()
        # Colunas: ID, Cliente, DescriÃ§Ã£o, Valor, Vencimento, AÃ§Ã£o, Editar, Excluir (8 colunas)
        self.table.setColumnCount(8) 
        self.table.setHorizontalHeaderLabels(["ID", "Cliente", "DescriÃ§Ã£o", "Valor", "Vencimento", "AÃ§Ã£o", "Editar", "Excluir"])
        
        # Ajustes de Coluna
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Cliente
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # DescriÃ§Ã£o estica
        
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: white; color: black; border: 1px solid #ccc; }} 
            QHeaderView::section {{ background-color: {COLORS['secondary']}; color: white; font-weight: bold; padding: 8px; }}
        """)
        main_layout.addWidget(self.table)
        
        self.load_pendencias()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.focusNextChild()
        else:
            super().keyPressEvent(event)

    def load_cli(self):
        self.cb_cli.clear()
        self.cb_cli.addItem("Cliente Avulso / BalcÃ£o", None)
        try:
            self.db.cursor.execute("SELECT id, nome_razao FROM db_cli.entidades WHERE categoria = 'Cliente'")
            for i, n in self.db.cursor.fetchall(): self.cb_cli.addItem(n, i)
        except: pass

    def dar_baixa(self, id_conta):
        dlg = BaixaContaDialog(self.db, id_conta, tipo="Receber", parent=self)
        if dlg.exec():
            self.load_pendencias()

    def showEvent(self, event):
        """Sempre que esta tela for exibida (clicar na aba), recarrega a tabela."""
        self.load_pendencias()
        self.load_cli() # Aproveita e atualiza a lista de clientes tambÃ©m
        super().showEvent(event)
        
    def salvar(self):
        try:
            cid = self.cb_cli.currentData()
            st = self.cb_st.currentText()
            dr = datetime.now().strftime("%Y-%m-%d") if st == "Recebido" else None
            
            dados = (self.txt_desc.text(), cid, self.spin_val.value(), 
                     self.dt_venc.date().toString("yyyy-MM-dd"), dr, st, "Dinheiro", "")
            
            self.db.cursor.execute('''
                INSERT INTO db_fin.contas_receber 
                (descricao, cliente_id, valor_previsto, data_vencimento, data_recebimento, status, forma_pagamento, obs) 
                VALUES (?,?,?,?,?,?,?,?)
            ''', dados)
            self.db.conn.commit()
            
            self.txt_desc.setText("")
            self.spin_val.setValue(0)
            self.load_pendencias()
            
            mostrar_mensagem(self, 'sucesso', 'Sucesso', "Receita lanÃ§ada com sucesso!")
            
        except Exception as e: 
            mostrar_mensagem(self, 'erro', 'Erro', str(e))

    def load_pendencias(self):
        self.table.setRowCount(0)
        df = self.db.get_pendencias("Receber")
        
        for i, row in df.iterrows():
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            
            # --- COLUNA CLIENTE ---
            cliente_nome = "BalcÃ£o / Avulso"
            try:
                # Se o DF nÃ£o trouxer o nome, buscamos pelo ID
                if 'nome_razao' in row and row['nome_razao']:
                    cliente_nome = row['nome_razao']
                elif row.get('cliente_id'):
                    self.db.cursor.execute("SELECT nome_razao FROM db_cli.entidades WHERE id=?", (row['cliente_id'],))
                    res = self.db.cursor.fetchone()
                    if res: cliente_nome = res[0]
            except: pass
            
            self.table.setItem(i, 1, QTableWidgetItem(cliente_nome))
            
            # DescriÃ§Ã£o
            self.table.setItem(i, 2, QTableWidgetItem(row['descricao']))
            
            # Valor
            val = row.get('valor_previsto', row.get('valor', 0.0))
            self.table.setItem(i, 3, QTableWidgetItem(f"R$ {val:,.2f}"))
            
            # Data
            dt_fmt = datetime.strptime(row['data_vencimento'], "%Y-%m-%d").strftime("%d/%m/%Y")
            self.table.setItem(i, 4, QTableWidgetItem(dt_fmt))
            
            # BotÃ£o Baixar
            btn_baixa = QPushButton("âœ… Receber")
            btn_baixa.setStyleSheet("background-color: #27ae60; color: white; border-radius: 4px; padding: 6px; border: none;")
            btn_baixa.clicked.connect(lambda checked, id_c=row['id']: self.dar_baixa(id_c))
            self.table.setCellWidget(i, 5, btn_baixa)

            # BotÃ£o Editar
            btn_edit = QPushButton("âœï¸")
            btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius:4px; padding:6px; border: none;")
            btn_edit.clicked.connect(lambda checked, id_c=row['id']: self.open_editor(id_c))
            self.table.setCellWidget(i, 6, btn_edit)

            # BotÃ£o Excluir
            btn_del = QPushButton("ðŸ—‘ï¸")
            btn_del.setStyleSheet("background-color: #c0392b; color: white; border-radius:4px; padding:6px; border: none;")
            btn_del.clicked.connect(lambda checked, id_c=row['id']: self.excluir_conta(id_c))
            self.table.setCellWidget(i, 7, btn_del)

    def open_editor(self, id_conta):
        dlg = EntryEditorDialog(self.db, 'receber', id_conta, self)
        if dlg.exec():
            self.load_pendencias()

    def excluir_conta(self, id_conta):
        if mostrar_mensagem(self, 'confirma_exclusao', 'Excluir', "Deseja realmente excluir esta receita?"):
            try:
                self.db.cursor.execute("DELETE FROM db_fin.contas_receber WHERE id=?", (id_conta,))
                self.db.conn.commit()
                self.load_pendencias()
            except Exception as e:
                mostrar_mensagem(self, 'erro', 'Erro', str(e))

class ContasPagarForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        
        # --- APLICA O ESTILO DE FOCO NESTA TELA ---
        self.setStyleSheet(FOCUS_STYLE)

        # Layout Principal dividido em 2 partes
        main_layout = QVBoxLayout(self)
        
        # --- PARTE 1: FormulÃ¡rio de LanÃ§amento ---
        form_group = QFrame()
        form_group.setStyleSheet("background-color: #ecf0f1; border-radius: 8px; padding: 10px;")
        form_layout = QFormLayout(form_group)
        
        lbl_title = QLabel("ðŸ“‹ Nova Conta a Pagar")
        lbl_title_font = QFont()
        lbl_title_font.setPointSize(14)
        lbl_title_font.setBold(True)
        lbl_title.setFont(lbl_title_font)
        lbl_title.setStyleSheet(f"color: {COLORS['accent']};")
        form_layout.addRow(lbl_title)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ex: Conta de Luz, Aluguel...")
        form_layout.addRow("DescriÃ§Ã£o:", self.txt_desc)
        
        self.cb_forn = QComboBox()
        setup_combo_behavior(self.cb_forn) 
        self.load_forn()
        form_layout.addRow("Fornecedor:", self.cb_forn)
        
        self.cb_cat = QComboBox()
        self.cb_cat.addItems(["Custos Operacionais", "Despesas Administrativas", "Impostos", "Fornecedores/Estoque", "Pessoal/SalÃ¡rios"])
        setup_combo_behavior(self.cb_cat) 
        form_layout.addRow("Categoria:", self.cb_cat)
        
        hbox_val = QHBoxLayout()
        self.spin_val = QDoubleSpinBox()
        self.spin_val.setMaximum(9999999)
        self.spin_val.setPrefix("R$ ")
        
        self.cb_st = QComboBox()
        self.cb_st.addItems(["Pendente", "Pago"])
        setup_combo_behavior(self.cb_st) 
        
        hbox_val.addWidget(self.spin_val)
        hbox_val.addWidget(self.cb_st)
        form_layout.addRow("Valor / Status:", hbox_val)
        
        self.dt_venc = QDateEdit(QDate.currentDate())
        self.dt_venc.setCalendarPopup(True)  # CalendÃ¡rio
        self.dt_venc.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Vencimento:", self.dt_venc)
        
        btn_add = QPushButton("ðŸ’³ LanÃ§ar Conta")
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
        
        # --- PARTE 2: Tabela de PendÃªncias ---
        lbl_pend = QLabel("Contas Pendentes")
        lbl_pend.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px; color: #333;")
        main_layout.addWidget(lbl_pend)
        
        self.table = QTableWidget()
        # Aumentado para 7 colunas para caber o Excluir
        self.table.setColumnCount(7) 
        self.table.setHorizontalHeaderLabels(["ID", "DescriÃ§Ã£o", "Valor", "Vencimento", "AÃ§Ã£o", "Editar", "Excluir"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: white; color: black; border: 1px solid #ccc; }} 
            QHeaderView::section {{ background-color: {COLORS['secondary']}; color: white; font-weight: bold; padding: 8px; }}
        """)
        main_layout.addWidget(self.table)
        
        self.load_pendencias() 

    # FunÃ§Ã£o para transformar ENTER em TAB
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
        # --- VALIDAÃ‡ÃƒO (IMPEDE SALVAR VAZIO) ---
        descricao = self.txt_desc.text().strip()
        valor = self.spin_val.value()

        if not descricao:
            # Usando sua funÃ§Ã£o customizada para aviso
            mostrar_mensagem(self, 'aviso', "AtenÃ§Ã£o", "Por favor, informe uma <b>DescriÃ§Ã£o</b> para a conta.")
            self.txt_desc.setFocus()
            return
        
        if valor <= 0:
            # Usando sua funÃ§Ã£o customizada para aviso
            mostrar_mensagem(self, 'aviso', "AtenÃ§Ã£o", "O <b>Valor</b> deve ser maior que zero.")
            self.spin_val.setFocus()
            return
        # ---------------------------------------

        try:
            fid = self.cb_forn.currentData()
            st = self.cb_st.currentText()
            dp = datetime.now().strftime("%Y-%m-%d") if st == "Pago" else None
            
            dados = (descricao, fid, self.cb_cat.currentText(), valor, 
                    self.dt_venc.date().toString("yyyy-MM-dd"), dp, st, "Dinheiro", "")
            
            self.db.cursor.execute('INSERT INTO db_fin.contas_pagar (descricao, fornecedor_id, categoria, valor, data_vencimento, data_pagamento, status, forma_pagamento, obs) VALUES (?,?,?,?,?,?,?,?,?)', dados)
            self.db.conn.commit()
            
            # Limpeza de campos
            self.txt_desc.clear()
            self.spin_val.setValue(0)
            self.load_pendencias()
            
            # Feedback visual no placeholder
            self.txt_desc.setPlaceholderText("âœ… Conta Salva!")
            QTimer.singleShot(2000, lambda: self.txt_desc.setPlaceholderText("Ex: Conta de Luz, Aluguel..."))
            
            # OPCIONAL: Se quiser um popup de sucesso tambÃ©m:
            # mostrar_mensagem(self, 'info', "Sucesso", "Conta lanÃ§ada com sucesso!")
            
        except Exception as e: 
            # Usando sua funÃ§Ã£o customizada para erro crÃ­tico
            mostrar_mensagem(self, 'erro', "Erro CrÃ­tico", f"NÃ£o foi possÃ­vel salvar os dados.\n\nErro: {e}")

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
            
            # BotÃ£o Baixar
            btn_baixa = QPushButton("âœ… Pagar")
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

            # BotÃ£o Editar
            btn_edit = QPushButton("âœï¸")
            btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius:4px; padding:6px; border:none;")
            btn_edit.clicked.connect(lambda checked, id_c=row['id']: self.open_editor(id_c))
            self.table.setCellWidget(i, 5, btn_edit)

            # BotÃ£o Excluir (NOVO)
            btn_del = QPushButton("ðŸ—‘ï¸")
            btn_del.setStyleSheet("background-color: #c0392b; color: white; border-radius:4px; padding:6px; border:none;")
            btn_del.clicked.connect(lambda checked, id_c=row['id']: self.excluir_conta(id_c))
            self.table.setCellWidget(i, 6, btn_del)

    def open_editor(self, id_conta):
        dlg = EntryEditorDialog(self.db, 'pagar', id_conta, self)
        if dlg.exec():
            self.load_pendencias()

    def dar_baixa(self, id_conta):
        if self.db.baixar_conta(id_conta, "Pagar"):
            self.load_pendencias()

    def excluir_conta(self, id_conta):
        reply = QMessageBox.question(self, 'Confirmar ExclusÃ£o', 
                                     "Tem certeza que deseja excluir esta conta permanentemente?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.cursor.execute("DELETE FROM db_fin.contas_pagar WHERE id=?", (id_conta,))
                self.db.conn.commit()
                self.load_pendencias() # Recarrega a tabela
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao excluir: {str(e)}")

class GestaoBancaria(QWidget):
    """
    Sistema integrado e unificado de gestão bancária.
    Combina contas, movimentações, recebimentos, taxas e extratos.
    """
    recebimento_adicionado_signal = pyqtSignal()
    
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        
        # --- ESTILO GERAL (CSS) ---
        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: {COLORS['bg']}; 
                color: {COLORS['text']}; 
                font-family: 'Segoe UI', sans-serif;
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
                color: {COLORS['text']}; 
                background-color: white;
                border: 1px solid {COLORS['border']};
                padding: 6px;
                border-radius: 4px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #3498db;
            }}
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 20px;
                font-weight: bold;
                background-color: white;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QTableWidget {{
                background-color: white;
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['secondary']};
                color: white;
                font-weight: bold;
                padding: 5px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        titulo = QLabel("🏦 Gestão de Contas Bancárias")
        titulo.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['primary']}; padding: 5px;")
        layout.addWidget(titulo)
        
        # Cards com resumo
        cards_layout = QHBoxLayout()
        self.card_saldo_total = DashboardCard("Saldo Total", "R$ 0,00", "💰", "#27ae60")
        self.card_contas_ativas = DashboardCard("Contas Ativas", "0", "🏦", "#3498db")
        self.card_movimentacoes_mes = DashboardCard("Movimentações Mês", "0", "📊", "#9b59b6")
        
        cards_layout.addWidget(self.card_saldo_total)
        cards_layout.addWidget(self.card_contas_ativas)
        cards_layout.addWidget(self.card_movimentacoes_mes)
        
        layout.addLayout(cards_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; border-radius: 5px; background: white; }}
            QTabBar::tab {{ 
                background: #ecf0f1; padding: 10px 20px; border: 1px solid {COLORS['border']};
                border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px;
                color: {COLORS['text']};
            }}
            QTabBar::tab:selected {{ background: white; font-weight: bold; border-top: 3px solid {COLORS['primary']}; }}
        """)
        
        # Adiciona Tabs
        self.tabs.addTab(self.criar_tab_contas(), "🏦 Contas")
        self.tabs.addTab(self.criar_tab_movimentacoes(), "📋 Movimentações")
        self.tabs.addTab(self.criar_tab_recebimentos(), "💰 Recebimentos")
        layout.addWidget(self.tabs)
        
        # Carrega dados iniciais
        self.atualizar_cards()
        self.carregar_contas()
        self.carregar_movimentacoes()
    
    def criar_tab_contas(self):
        """Cria tab de cadastro de contas"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        
        # Formulário de cadastro
        form_group = QGroupBox("Nova Conta / Editar")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.txt_banco = QLineEdit()
        self.txt_banco.setPlaceholderText("Ex: Banco do Brasil, Itaú, Stone...")
        form_layout.addRow("Banco:", self.txt_banco)
        
        self.txt_agencia = QLineEdit()
        self.txt_agencia.setPlaceholderText("Ex: 0001")
        form_layout.addRow("Agência:", self.txt_agencia)
        
        self.txt_numero_conta = QLineEdit()
        self.txt_numero_conta.setPlaceholderText("Ex: 12345-6")
        form_layout.addRow("Número da Conta:", self.txt_numero_conta)
        
        self.cb_tipo_conta = QComboBox()
        self.cb_tipo_conta.addItems(["Corrente", "Poupança", "Caixa Interno", "Maquininha"])
        self.cb_tipo_conta.currentTextChanged.connect(self.ao_mudar_tipo_conta)
        form_layout.addRow("Tipo:", self.cb_tipo_conta)
        
        self.spin_saldo_inicial = MoneySpinBox()
        form_layout.addRow("Saldo Inicial:", self.spin_saldo_inicial)
        
        # Taxas
        self.lbl_taxas = QLabel("⚙️ Configuração de Taxas:")
        self.lbl_taxas.setStyleSheet("font-weight: bold; margin-top: 10px; color: #e67e22;")
        form_layout.addRow(self.lbl_taxas)
        
        self.spin_taxa_debito = QDoubleSpinBox()
        self.spin_taxa_debito.setDecimals(2)
        self.spin_taxa_debito.setMaximum(100)
        self.spin_taxa_debito.setValue(1.99)
        self.spin_taxa_debito.setSuffix(" %")
        self.lbl_taxa_debito = QLabel("Taxa Débito:")
        form_layout.addRow(self.lbl_taxa_debito, self.spin_taxa_debito)
        
        self.spin_taxa_credito_vista = QDoubleSpinBox()
        self.spin_taxa_credito_vista.setDecimals(2)
        self.spin_taxa_credito_vista.setMaximum(100)
        self.spin_taxa_credito_vista.setValue(2.99)
        self.spin_taxa_credito_vista.setSuffix(" %")
        self.lbl_taxa_credito_vista = QLabel("Taxa Créd. Vista:")
        form_layout.addRow(self.lbl_taxa_credito_vista, self.spin_taxa_credito_vista)
        
        self.spin_taxa_credito_parcelado = QDoubleSpinBox()
        self.spin_taxa_credito_parcelado.setDecimals(2)
        self.spin_taxa_credito_parcelado.setMaximum(100)
        self.spin_taxa_credito_parcelado.setValue(3.99)
        self.spin_taxa_credito_parcelado.setSuffix(" %")
        self.lbl_taxa_credito_parcelado = QLabel("Taxa Créd. Parc.:")
        form_layout.addRow(self.lbl_taxa_credito_parcelado, self.spin_taxa_credito_parcelado)
        
        self.txt_observacoes = QLineEdit()
        self.txt_observacoes.setPlaceholderText("Observações opcionais")
        form_layout.addRow("Observações:", self.txt_observacoes)
        
        form_group.setLayout(form_layout)
        content_layout.addWidget(form_group)
        
        # Botões
        btn_layout = QHBoxLayout()
        self.btn_salvar_conta = QPushButton("✅ Salvar Conta")
        self.btn_salvar_conta.setStyleSheet(f"background-color: {COLORS['success']}; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.btn_salvar_conta.clicked.connect(self.salvar_conta)
        btn_layout.addWidget(self.btn_salvar_conta)
        
        self.btn_cancelar_conta = QPushButton("❌ Cancelar")
        self.btn_cancelar_conta.setStyleSheet(f"background-color: {COLORS['shadow']}; color: white; padding: 10px; border-radius: 5px;")
        self.btn_cancelar_conta.clicked.connect(self.limpar_form_conta)
        btn_layout.addWidget(self.btn_cancelar_conta)
        
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)
        
        # Lista de contas
        self.table_contas = QTableWidget()
        self.table_contas.setMinimumHeight(250)
        self.table_contas.setColumnCount(7)
        self.table_contas.setHorizontalHeaderLabels(["ID", "Banco", "Agência", "Conta", "Tipo", "Saldo Atual", "Ações"])
        self.table_contas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_contas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_contas.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        content_layout.addWidget(self.table_contas)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        self.ao_mudar_tipo_conta("Corrente") # Esconde taxas no início
        return widget
    
    def criar_tab_movimentacoes(self):
        """Cria tab de movimentações bancárias"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        filtros = QHBoxLayout()
        filtros.setSpacing(10)
        
        filtros.addWidget(QLabel("Conta:"))
        self.cb_filtro_conta = QComboBox()
        self.cb_filtro_conta.setMinimumWidth(150)
        filtros.addWidget(self.cb_filtro_conta)
        
        filtros.addWidget(QLabel("Período:"))
        self.dt_filtro_inicio = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_filtro_inicio.setCalendarPopup(True)
        self.dt_filtro_inicio.setDisplayFormat("dd/MM/yyyy")
        filtros.addWidget(self.dt_filtro_inicio)
        
        filtros.addWidget(QLabel("até"))
        self.dt_filtro_fim = QDateEdit(QDate.currentDate())
        self.dt_filtro_fim.setCalendarPopup(True)
        self.dt_filtro_fim.setDisplayFormat("dd/MM/yyyy")
        filtros.addWidget(self.dt_filtro_fim)
        
        btn_filtrar = QPushButton("🔍 Filtrar")
        btn_filtrar.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        btn_filtrar.clicked.connect(self.carregar_movimentacoes)
        filtros.addWidget(btn_filtrar)
        
        filtros.addStretch()
        layout.addLayout(filtros)
        
        self.table_movimentacoes = QTableWidget()
        self.table_movimentacoes.setColumnCount(9)
        self.table_movimentacoes.setHorizontalHeaderLabels([
            "ID", "Data", "Conta", "Tipo", "Valor Bruto", "Taxa", 
            "Valor Líquido", "Origem", "Conciliado"
        ])
        self.table_movimentacoes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_movimentacoes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_movimentacoes)
        
        self.lbl_resumo_mov = QLabel()
        self.lbl_resumo_mov.setStyleSheet("background-color: white; padding: 15px; border: 1px solid #bdc3c7; border-radius: 5px; font-weight: bold;")
        layout.addWidget(self.lbl_resumo_mov)
        
        return widget
    
    def criar_tab_recebimentos(self):
        """Cria tab para processar recebimentos"""
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        
        info = QLabel("💡 Processe recebimentos de vendas e contas a receber aqui")
        info.setStyleSheet("background-color: #d5f4e6; padding: 15px; border-radius: 5px; color: #27ae60; font-weight: bold; border: 1px solid #27ae60;")
        layout.addWidget(info)
        
        form_group = QGroupBox("Processar Recebimento")
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.cb_conta_recebimento = QComboBox()
        self.cb_conta_recebimento.setMinimumHeight(30)
        # O signal é conectado depois do preenchimento para evitar erros de índice 0
        self.cb_conta_recebimento.currentIndexChanged.connect(lambda: self.ao_mudar_forma_pagamento(self.cb_forma_pagamento_rec.currentText()))
        form_layout.addRow("Conta Destino:", self.cb_conta_recebimento)
        
        self.cb_forma_pagamento_rec = QComboBox()
        self.cb_forma_pagamento_rec.setMinimumHeight(30)
        self.cb_forma_pagamento_rec.addItems(["Dinheiro", "PIX", "Transferência", "Débito", "Crédito Vista", "Crédito Parcelado"])
        self.cb_forma_pagamento_rec.currentTextChanged.connect(self.ao_mudar_forma_pagamento)
        form_layout.addRow("Forma Pagamento:", self.cb_forma_pagamento_rec)
        
        self.spin_valor_recebimento = MoneySpinBox()
        self.spin_valor_recebimento.setMinimumHeight(30)
        self.spin_valor_recebimento.valueChanged.connect(lambda: self.ao_mudar_forma_pagamento(self.cb_forma_pagamento_rec.currentText()))
        form_layout.addRow("Valor:", self.spin_valor_recebimento)
        
        self.lbl_info_taxa = QLabel()
        self.lbl_info_taxa.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")
        form_layout.addRow("", self.lbl_info_taxa)
        
        self.txt_descricao_rec = QLineEdit()
        self.txt_descricao_rec.setMinimumHeight(30)
        self.txt_descricao_rec.setPlaceholderText("Ex: Venda #123, Recebimento Cliente X")
        form_layout.addRow("Descrição:", self.txt_descricao_rec)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        btn_processar = QPushButton("💰 Processar Recebimento")
        btn_processar.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['success']}; color: white; padding: 15px; font-size: 16px; font-weight: bold; border-radius: 5px; }}
            QPushButton:hover {{ background-color: #219150; }}
        """)
        btn_processar.clicked.connect(self.processar_recebimento)
        layout.addWidget(btn_processar)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        return container
    
    def ao_mudar_tipo_conta(self, tipo):
        """Mostra/esconde campos de taxa conforme tipo de conta"""
        mostrar_taxas = (tipo == "Maquininha")
        self.lbl_taxas.setVisible(mostrar_taxas)
        self.spin_taxa_debito.setVisible(mostrar_taxas)
        self.spin_taxa_credito_vista.setVisible(mostrar_taxas)
        self.spin_taxa_credito_parcelado.setVisible(mostrar_taxas)
        
        if hasattr(self, 'lbl_taxa_debito'):
            self.lbl_taxa_debito.setVisible(mostrar_taxas)
            self.lbl_taxa_credito_vista.setVisible(mostrar_taxas)
            self.lbl_taxa_credito_parcelado.setVisible(mostrar_taxas)
    
    def ao_mudar_forma_pagamento(self, forma):
        """Atualiza info de taxa ao mudar forma de pagamento ou conta"""
        conta_id = self.cb_conta_recebimento.currentData()
        
        if forma in ["Débito", "Crédito Vista", "Crédito Parcelado"] and conta_id is not None:
            # Busca a conta diretamente pela função do DB
            conta = self.db.obter_conta_bancaria(conta_id)
            
            # Verifica se retornou dados e se o tipo é Maquininha (índice 4 pode variar no seu DB, ajustado com base no original)
            if conta and conta[4] == "Maquininha": 
                taxa = conta[8] if forma == "Débito" else (conta[9] if forma == "Crédito Vista" else conta[10])
                
                valor = self.spin_valor_recebimento.value()
                valor_taxa = valor * (taxa / 100)
                valor_liquido = valor - valor_taxa
                
                self.lbl_info_taxa.setText(
                    f"⚠️ Taxa: {taxa:.2f}% = {formatar_moeda_br(valor_taxa)} | "
                    f"Líquido: {formatar_moeda_br(valor_liquido)}"
                )
                self.lbl_info_taxa.setVisible(True)
            else:
                self.lbl_info_taxa.setVisible(False)
        else:
            self.lbl_info_taxa.setVisible(False)
    
    def salvar_conta(self):
        """Salva conta bancária"""
        try:
            dados = {
                'id': getattr(self, 'conta_editando_id', None),
                'banco': self.txt_banco.text().strip(),
                'agencia': self.txt_agencia.text().strip(),
                'numero_conta': self.txt_numero_conta.text().strip(),
                'tipo_conta': self.cb_tipo_conta.currentText(),
                'saldo_inicial': self.spin_saldo_inicial.value(),
                'taxa_debito': self.spin_taxa_debito.value(),
                'taxa_credito_vista': self.spin_taxa_credito_vista.value(),
                'taxa_credito_parcelado': self.spin_taxa_credito_parcelado.value(),
                'observacoes': self.txt_observacoes.text().strip(),
                'ativa': 1
            }
            
            if not dados['banco']:
                QMessageBox.warning(self, "Atenção", "Informe o nome do banco!")
                return
            if not dados['numero_conta']:
                QMessageBox.warning(self, "Atenção", "Informe o número da conta!")
                return
            
            if self.db.salvar_conta_bancaria(dados):
                QMessageBox.information(self, "Sucesso", "✅ Conta salva com sucesso!")
                self.limpar_form_conta()
                self.carregar_contas()
                self.atualizar_cards()
            else:
                QMessageBox.critical(self, "Erro", "Erro ao salvar conta!")
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro: {e}")
    
    def limpar_form_conta(self):
        self.conta_editando_id = None
        self.txt_banco.clear()
        self.txt_agencia.clear()
        self.txt_numero_conta.clear()
        self.cb_tipo_conta.setCurrentIndex(0)
        self.spin_saldo_inicial.setValue(0)
        self.spin_taxa_debito.setValue(1.99)
        self.spin_taxa_credito_vista.setValue(2.99)
        self.spin_taxa_credito_parcelado.setValue(3.99)
        self.txt_observacoes.clear()
        self.btn_salvar_conta.setText("✅ Salvar Conta")
    
    def carregar_contas(self):
        """Carrega contas na tabela e nos combos usando userData para segurança"""
        try:
            contas = self.db.obter_contas_bancarias(apenas_ativas=True)
            self.table_contas.setRowCount(len(contas))
            
            self.cb_filtro_conta.blockSignals(True)
            self.cb_conta_recebimento.blockSignals(True)
            
            self.cb_filtro_conta.clear()
            self.cb_filtro_conta.addItem("Todas as Contas", None) # None significa sem filtro
            
            self.cb_conta_recebimento.clear()
            
            for i, conta in enumerate(contas):
                # Preenchimento seguro para evitar erro de desempacotamento
                c = conta + (None,) * (15 - len(conta)) 
                
                c_id = c[0]
                banco = str(c[1] or "")
                agencia = str(c[2] or "")
                numero = str(c[3] or "")
                tipo = str(c[4] or "Corrente")
                # Se não houver saldo atual (índice 6), usa o inicial (índice 5), senão 0.0
                saldo_atual = float(c[6] if c[6] is not None else (c[5] or 0.0))
                
                self.table_contas.setItem(i, 0, QTableWidgetItem(str(c_id)))
                self.table_contas.setItem(i, 1, QTableWidgetItem(banco))
                self.table_contas.setItem(i, 2, QTableWidgetItem(agencia))
                self.table_contas.setItem(i, 3, QTableWidgetItem(numero))
                self.table_contas.setItem(i, 4, QTableWidgetItem(tipo))
                self.table_contas.setItem(i, 5, QTableWidgetItem(formatar_moeda_br(saldo_atual)))
                
                widget_acoes = QWidget()
                layout_acoes = QHBoxLayout(widget_acoes)
                layout_acoes.setContentsMargins(5, 0, 5, 0)
                
                btn_editar = QPushButton("✏️")
                btn_editar.setFixedSize(30, 25)
                btn_editar.setStyleSheet(f"background-color: {COLORS['warning']}; color: white; border: none; border-radius: 3px;")
                # Passa a tupla original; o novo editar_conta tratará o tamanho com segurança
                btn_editar.clicked.connect(lambda ch, cont=conta: self.editar_conta(cont))
                layout_acoes.addWidget(btn_editar)
                
                btn_inativar = QPushButton("🔒")
                btn_inativar.setFixedSize(30, 25)
                btn_inativar.setStyleSheet(f"background-color: {COLORS['accent']}; color: white; border: none; border-radius: 3px;")
                btn_inativar.clicked.connect(lambda ch, cid=c_id: self.inativar_conta(cid))
                layout_acoes.addWidget(btn_inativar)
                
                layout_acoes.addStretch()
                self.table_contas.setCellWidget(i, 6, widget_acoes)
                
                # ADICIONA NOS COMBOS COM DATA SECRETA (c_id)
                texto = f"{banco} - {numero}"
                self.cb_filtro_conta.addItem(texto, c_id)
                self.cb_conta_recebimento.addItem(texto, c_id)
                
            self.cb_filtro_conta.blockSignals(False)
            self.cb_conta_recebimento.blockSignals(False)
            
        except Exception as e:
            print(f"Erro ao carregar contas: {e}")
            import traceback
            traceback.print_exc()
    
    def editar_conta(self, conta):
        """Carrega conta para edição com segurança contra tuplas curtas (IndexError)"""
        # Garante que a tupla tenha pelo menos 15 posições, preenchendo o resto com None
        c = conta + (None,) * (15 - len(conta))
        
        self.conta_editando_id = c[0]
        self.txt_banco.setText(str(c[1] or ""))
        self.txt_agencia.setText(str(c[2] or ""))
        self.txt_numero_conta.setText(str(c[3] or ""))
        self.cb_tipo_conta.setCurrentText(str(c[4] or "Corrente"))
        self.spin_saldo_inicial.setValue(float(c[5] or 0.0))
        
        # Prevenção dupla: evita IndexError e evita erro de setValue(None)
        self.spin_taxa_debito.setValue(float(c[8] if c[8] is not None else 1.99))
        self.spin_taxa_credito_vista.setValue(float(c[9] if c[9] is not None else 2.99))
        self.spin_taxa_credito_parcelado.setValue(float(c[10] if c[10] is not None else 3.99))
        
        self.txt_observacoes.setText(str(c[11] or ""))
        self.btn_salvar_conta.setText("💾 Atualizar Conta")
        
        # Volta pro tab de contas
        self.tabs.setCurrentIndex(0)
    
    def inativar_conta(self, conta_id):
        resp = QMessageBox.question(self, "Confirmar", "Deseja inativar esta conta?\nEla não aparecerá mais nas listas.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            try:
                self.db.cursor.execute("UPDATE db_fin.contas_bancarias SET ativa = 0 WHERE id = ?", (conta_id,))
                self.db.conn.commit()
                self.carregar_contas()
                self.atualizar_cards()
                QMessageBox.information(self, "Sucesso", "Conta inativada!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))
    
    def carregar_movimentacoes(self):
        try:
            # Obtém ID com segurança usando currentData
            conta_id = self.cb_filtro_conta.currentData()
            
            data_inicio = self.dt_filtro_inicio.date().toString("yyyy-MM-dd")
            data_fim = self.dt_filtro_fim.date().toString("yyyy-MM-dd")
            
            if conta_id:
                movimentacoes = self.db.obter_movimentacoes_conta(conta_id, data_inicio, data_fim)
            else:
                self.db.cursor.execute("""
                    SELECT * FROM db_fin.movimentacoes_bancarias
                    WHERE data_movimentacao BETWEEN ? AND ?
                    ORDER BY data_movimentacao DESC
                """, (data_inicio, data_fim))
                movimentacoes = self.db.cursor.fetchall()
            
            self.table_movimentacoes.setRowCount(len(movimentacoes))
            
            t_entradas = 0
            t_saidas = 0
            t_taxas = 0
            
            for i, mov in enumerate(movimentacoes):
                conta = self.db.obter_conta_bancaria(mov[1])
                nome_conta = f"{conta[1]} - {conta[3]}" if conta else "N/A"
                
                self.table_movimentacoes.setItem(i, 0, QTableWidgetItem(str(mov[0])))
                self.table_movimentacoes.setItem(i, 1, QTableWidgetItem(mov[3]))
                self.table_movimentacoes.setItem(i, 2, QTableWidgetItem(nome_conta))
                
                tipo_item = QTableWidgetItem(mov[2])
                if mov[2] == "Entrada":
                    tipo_item.setBackground(QColor("#d5f4e6"))
                    tipo_item.setForeground(QColor("#27ae60"))
                    t_entradas += mov[4]
                else:
                    tipo_item.setBackground(QColor("#fadbd8"))
                    tipo_item.setForeground(QColor("#e74c3c"))
                    t_saidas += mov[4]
                self.table_movimentacoes.setItem(i, 3, tipo_item)
                
                self.table_movimentacoes.setItem(i, 4, QTableWidgetItem(formatar_moeda_br(mov[4])))
                self.table_movimentacoes.setItem(i, 5, QTableWidgetItem(formatar_moeda_br(mov[5])))
                self.table_movimentacoes.setItem(i, 6, QTableWidgetItem(formatar_moeda_br(mov[6])))
                self.table_movimentacoes.setItem(i, 7, QTableWidgetItem(mov[8] or ""))
                
                concil = "✅" if mov[12] else "⏳"
                self.table_movimentacoes.setItem(i, 8, QTableWidgetItem(concil))
                t_taxas += mov[5]
            
            self.lbl_resumo_mov.setText(
                f"📈 Entradas: {formatar_moeda_br(t_entradas)} | "
                f"📉 Saídas: {formatar_moeda_br(t_saidas)} | "
                f"💳 Taxas: {formatar_moeda_br(t_taxas)} | "
                f"💰 Saldo Período: {formatar_moeda_br(t_entradas - t_saidas)}"
            )
            
        except Exception as e:
            pass # print(f"Erro nas movs: {e}")
    
    def processar_recebimento(self):
        try:
            # Pega ID secreto invisível ao invés do split de string propenso a falhas
            conta_id = self.cb_conta_recebimento.currentData()
            
            if conta_id is None:
                QMessageBox.warning(self, "Atenção", "Selecione uma conta válida!")
                return
                
            valor = self.spin_valor_recebimento.value()
            if valor <= 0:
                QMessageBox.warning(self, "Atenção", "Informe o valor!")
                return
            
            descricao = self.txt_descricao_rec.text().strip()
            if not descricao:
                QMessageBox.warning(self, "Atenção", "Informe a descrição!")
                return
            
            forma = self.cb_forma_pagamento_rec.currentText()
            
            sucesso, valor_liquido = self.db.registrar_movimentacao_bancaria(
                conta_id, "Entrada", valor, forma, "Recebimento Manual", None, descricao
            )
            
            if sucesso:
                msg = f"✅ Recebimento processado!\n\n"
                if valor != valor_liquido:
                    taxa = valor - valor_liquido
                    msg += f"Valor Bruto: {formatar_moeda_br(valor)}\n"
                    msg += f"Taxa: {formatar_moeda_br(taxa)}\n"
                    msg += f"Valor Líquido: {formatar_moeda_br(valor_liquido)}"
                else:
                    msg += f"Valor: {formatar_moeda_br(valor)}"
                
                QMessageBox.information(self, "Sucesso", msg)
                self.spin_valor_recebimento.setValue(0)
                self.txt_descricao_rec.clear()
                self.atualizar_cards()
                self.carregar_contas()
                self.carregar_movimentacoes()
            else:
                QMessageBox.critical(self, "Erro", "Erro ao processar recebimento!")
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro: {e}")
            
    def atualizar_cards(self):
        try:
            saldo_total = self.db.obter_saldo_total_contas()
            self.card_saldo_total.atualizar_valor(formatar_moeda_br(saldo_total))
            
            contas = self.db.obter_contas_bancarias(apenas_ativas=True)
            self.card_contas_ativas.atualizar_valor(str(len(contas)))
            
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
            self.db.cursor.execute("SELECT COUNT(*) FROM db_fin.movimentacoes_bancarias WHERE data_movimentacao >= ?", (inicio_mes,))
            qtd_mov = self.db.cursor.fetchone()[0]
            self.card_movimentacoes_mes.atualizar_valor(str(qtd_mov))
            
        except Exception as e:
            print(f"Erro ao atualizar cards: {e}")

