from classes.funcoesAuxiliares import FinanceiroService, IntSpinBox, MoneySpinBox, formatar_moeda_br, gerar_codigo_barras_boleto, gerar_linha_digitavel_boleto, gerar_pix_payload, gerar_qr_code_pix, mostrar_mensagem
from .imports import *

class ExtendedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def showPopup(self):
        super().showPopup()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            if not self.view().isVisible():
                self.showPopup()
        else:
            super().mousePressEvent(event)

class LancarPedido(QWidget):
    pedido_salvo_signal = pyqtSignal()

    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.itens_carrinho = []
        self.anexo_atual = None
        self.venda_id_edicao = None 
        self.parcelas_geradas = [] # Armazena dados complexos das parcelas geradas
        
        # --- ATUALIZAÇÃO AUTOMÁTICA DE TABELAS ---
        try:
            self.db.cursor.execute("ALTER TABLE main.vendas ADD COLUMN descricao_pedido TEXT")
            self.db.conn.commit()
        except: pass

        # --- ESTILO GERAL ---
        self.setStyleSheet("""
            QWidget { background-color: #f0f2f5; color: #2c3e50; font-family: 'Segoe UI'; }
            QFrame#card { background-color: white; border-radius: 8px; border: 1px solid #d1d5db; }
            
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox { 
                padding: 8px; border: 1px solid #bdc3c7; border-radius: 5px; 
                background-color: white; min-height: 25px; font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #00aff0; background-color: #fdfdfd; }
            
            QLabel { font-weight: 600; color: #34495e; font-size: 12px; }
            QLabel#titulo { font-size: 20px; font-weight: 800; color: #1e293b; }
            QLabel#total_label { font-size: 26px; font-weight: 900; color: #27ae60; }
            
            QTableWidget { border: 1px solid #e5e7eb; gridline-color: #f3f4f6; background-color: white; }
            QHeaderView::section { background-color: #f8f9fa; border: none; padding: 6px; font-weight: bold; color: #555; }
        """)
        
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # --- 1. CABEÇALHO ---
        self.lbl_titulo = QLabel("🛒 Lançar Pedido")
        self.lbl_titulo.setObjectName("titulo")
        self.layout.addWidget(self.lbl_titulo)
        
        gb_header = QFrame()
        gb_header.setObjectName("card")
        form_h = QFormLayout(gb_header)
        form_h.setSpacing(12)
        form_h.setContentsMargins(20, 20, 20, 20)
        
        # Linha 1: Cliente e Emissão
        hbox1 = QHBoxLayout()
        self.cb_cli = ExtendedComboBox() 
        self.cb_cli.setMinimumWidth(300)
        self.load_clientes()
        
        self.dt_emissao = QDateEdit(QDate.currentDate())
        self.dt_emissao.setCalendarPopup(True); self.dt_emissao.setDisplayFormat("dd/MM/yyyy")
        self.dt_emissao.setFixedWidth(120)
        
        hbox1.addWidget(QLabel("Cliente:"))
        hbox1.addWidget(self.cb_cli, 1) 
        hbox1.addWidget(QLabel("Emissão:"))
        hbox1.addWidget(self.dt_emissao)
        
        # Linha 2: Vendedor, NF, Status
        hbox2 = QHBoxLayout()
        self.cb_vendedor = ExtendedComboBox()
        self.cb_vendedor.setEditable(True)
        self.carregar_vendedores()
        
        self.txt_nf = QLineEdit()
        self.txt_nf.setPlaceholderText("000")
        self.txt_nf.setFixedWidth(80)
        
        self.cb_status = ExtendedComboBox()
        self.cb_status.addItems(["Pedido", "Orçamento", "Aguardando Faturamento", "Faturado", "Entregue", "Cancelado"])
        self.cb_status.setFixedWidth(180)

        hbox2.addWidget(QLabel("Vendedor:"))
        hbox2.addWidget(self.cb_vendedor, 1) 
        hbox2.addWidget(QLabel("NF-e:"))
        hbox2.addWidget(self.txt_nf)
        hbox2.addWidget(QLabel("Status:"))
        hbox2.addWidget(self.cb_status)

        # Linha 3: Descrição
        hbox3 = QHBoxLayout()
        self.txt_descricao = QLineEdit()
        self.txt_descricao.setPlaceholderText("Descrição personalizada do pedido")
        hbox3.addWidget(QLabel("Descrição:"))
        hbox3.addWidget(self.txt_descricao)
        
        form_h.addRow(hbox1)
        form_h.addRow(hbox2)
        form_h.addRow(hbox3)
        self.layout.addWidget(gb_header)
        
        # --- 2. ADIÇÃO DE PRODUTOS ---
        gb_prod = QFrame()
        gb_prod.setObjectName("card")
        l_prod = QVBoxLayout(gb_prod)
        l_prod.setContentsMargins(20, 20, 20, 20)
        l_prod.addWidget(QLabel("📦 Adicionar Itens", styleSheet="font-size:16px; color:#00aff0;"))
        
        # Seleção de Produto
        hbox_busca = QHBoxLayout()
        self.cb_produto = ExtendedComboBox()
        self.cb_produto.setEditable(True)
        self.cb_produto.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cb_produto.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        completer = self.cb_produto.completer()
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.load_produtos()
        self.cb_produto.currentIndexChanged.connect(self.preencher_dados_produto)
        self.cb_produto.lineEdit().returnPressed.connect(self.ao_pressionar_enter_combo)
        
        hbox_busca.addWidget(QLabel("Produto (Obrigatório):"))
        hbox_busca.addWidget(self.cb_produto)
        l_prod.addLayout(hbox_busca)
        
        grid_det = QGridLayout()
        grid_det.setSpacing(10)
        self.spin_preco = MoneySpinBox()
        self.spin_preco.setPrefix("Venda: R$ ")
        self.spin_qtd = IntSpinBox(); self.spin_qtd.setRange(1, 9999999); self.spin_qtd.setPrefix("Qtd: "); self.spin_qtd.setFixedWidth(120)
        grid_det.addWidget(QLabel("Preço Unit. (Venda):"), 0, 0)
        grid_det.addWidget(self.spin_preco, 0, 1)
        grid_det.addWidget(QLabel("Quantidade:"), 0, 2)
        grid_det.addWidget(self.spin_qtd, 0, 3)
        self.spin_ipi = QDoubleSpinBox(); self.spin_ipi.setSuffix("%"); self.spin_ipi.setRange(0, 100); self.spin_ipi.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_icms = QDoubleSpinBox(); self.spin_icms.setSuffix("%"); self.spin_icms.setRange(0, 100); self.spin_icms.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.txt_variacao = QLineEdit(); self.txt_variacao.setPlaceholderText("Variação (Opcional)")
        grid_det.addWidget(QLabel("IPI %:"), 1, 0)
        grid_det.addWidget(self.spin_ipi, 1, 1)
        grid_det.addWidget(QLabel("ICMS %:"), 1, 2)
        grid_det.addWidget(self.spin_icms, 1, 3)
        grid_det.addWidget(QLabel("Obs/Detalhe:"), 1, 4)
        grid_det.addWidget(self.txt_variacao, 1, 5)
        l_prod.addLayout(grid_det)
        
        # Botões Produto
        hbox_action = QHBoxLayout()
        self.btn_anexo = QPushButton("📎 Anexar Arquivo")
        self.btn_anexo.setStyleSheet("background-color: #95a5a6; color: white; border: none; padding: 8px; border-radius: 4px;")
        self.btn_anexo.clicked.connect(self.selecionar_anexo_item)
        btn_add = QPushButton("➕ ADICIONAR")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self.adicionar_item)
        btn_add.setStyleSheet("QPushButton { background-color: #00aff0; color: white; font-weight: bold; border-radius: 4px; padding: 10px 20px; border: none; } QPushButton:hover { background-color: #009ad6; }")
        hbox_action.addWidget(self.btn_anexo)
        hbox_action.addStretch()
        hbox_action.addWidget(btn_add)
        l_prod.addLayout(hbox_action)
        
        # Tabela Itens
        self.tb_itens = QTableWidget()
        self.tb_itens.setColumnCount(7)
        self.tb_itens.setHorizontalHeaderLabels(["ID", "Produto", "Variação", "Qtd", "Unitário", "Total", "Anexo"])
        self.tb_itens.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tb_itens.setMinimumHeight(180)
        l_prod.addWidget(self.tb_itens)
        
        hbox_tot = QHBoxLayout()
        self.lbl_total = QLabel("Total Pedido: R$ 0,00")
        self.lbl_total.setObjectName("total_label")
        hbox_tot.addStretch(); hbox_tot.addWidget(self.lbl_total)
        l_prod.addLayout(hbox_tot)
        self.layout.addWidget(gb_prod)
        
        # --- 3. FINANCEIRO ---
        gb_fin = QFrame()
        gb_fin.setObjectName("card")
        l_fin = QVBoxLayout(gb_fin)
        l_fin.setContentsMargins(20, 20, 20, 20)
        l_fin.addWidget(QLabel("💰 Condições de Pagamento", styleSheet="font-size:16px; color:#27ae60;"))
        
        grid_fin = QGridLayout()
        grid_fin.setSpacing(10)

        # Dropdown Condição
        self.cb_condicao = ExtendedComboBox()
        self.cb_condicao.addItems([
            "À Vista", "30 Dias", "30 / 60 Dias", "30 / 60 / 90 Dias", 
            "15 / 30 / 45 / 60 Dias", "Entrada + 30 Dias", "Personalizado (Intervalo Fixo)"
        ])
        self.cb_condicao.currentIndexChanged.connect(self.ao_mudar_condicao)
        
        self.btn_custom_cond = QPushButton("+")
        self.btn_custom_cond.setFixedSize(30, 30)
        self.btn_custom_cond.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_cond.setToolTip("Criar condição personalizada avançada")
        self.btn_custom_cond.clicked.connect(self.abrir_dialogo_personalizado)
        self.btn_custom_cond.setStyleSheet("QPushButton { background-color: #3498db; color: white; border-radius: 4px; font-weight: bold; font-size: 16px; border: none; } QPushButton:hover { background-color: #2980b9; }")

        container_condicao = QWidget()
        layout_cond = QHBoxLayout(container_condicao)
        layout_cond.setContentsMargins(0, 0, 0, 0)
        layout_cond.setSpacing(5)
        layout_cond.addWidget(self.cb_condicao)
        layout_cond.addWidget(self.btn_custom_cond)

        # Campos Intervalo
        self.lbl_qtd_parc = QLabel("Qtd. Parcelas:")
        self.spin_qtd_parc = QSpinBox(); self.spin_qtd_parc.setRange(1, 120); self.spin_qtd_parc.setValue(1)
        self.lbl_intervalo = QLabel("Intervalo (Dias):")
        self.spin_dias_intervalo = QSpinBox(); self.spin_dias_intervalo.setRange(1, 365); self.spin_dias_intervalo.setValue(30)
        
        self.dt_pri_venc = QDateEdit(QDate.currentDate())
        self.dt_pri_venc.setCalendarPopup(True)
        self.dt_pri_venc.setDisplayFormat("dd/MM/yyyy")
        
        self.cb_forma_padrao = ExtendedComboBox()
        self.cb_forma_padrao.addItems(["Boleto", "Pix", "Cartão Crédito", "Cartão Débito", "Dinheiro", "Transferência"])
        
        self.cb_conta_bancaria = ExtendedComboBox()
        self.carregar_contas_bancarias_combo()
        
        grid_fin.addWidget(QLabel("Condição:"), 0, 0)
        grid_fin.addWidget(container_condicao, 0, 1, 1, 2)
        grid_fin.addWidget(QLabel("1º Vencimento (Parcelas):"), 0, 3) 
        grid_fin.addWidget(self.dt_pri_venc, 0, 4)
        grid_fin.addWidget(QLabel("Forma Pagto:"), 0, 5)
        grid_fin.addWidget(self.cb_forma_padrao, 0, 6)
        
        grid_fin.addWidget(self.lbl_qtd_parc, 1, 0)
        grid_fin.addWidget(self.spin_qtd_parc, 1, 1)
        grid_fin.addWidget(self.lbl_intervalo, 1, 2)
        grid_fin.addWidget(self.spin_dias_intervalo, 1, 3)

        self.cb_conta_bancaria.clear()
        self.cb_conta_bancaria.addItem("Selecione a conta...", None)
        grid_fin.addWidget(QLabel("Conta Destino (Preferencial):"), 2, 0)
        grid_fin.addWidget(self.cb_conta_bancaria, 2, 1, 1, 3)

        btn_gerar_parc = QPushButton("⚡ GERAR PARCELAS / PREVISÃO")
        btn_gerar_parc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gerar_parc.clicked.connect(self.gerar_parcelas_flexivel)
        btn_gerar_parc.setStyleSheet("QPushButton { background-color: #f39c12; color: white; border: none; padding: 10px; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #e67e22; }")
        
        l_fin.addLayout(grid_fin)
        l_fin.addWidget(btn_gerar_parc)
        
        # --- TABELA 5 COLUNAS (COM TAXA DE MAQUININHA) ---
        self.tb_parcelas = QTableWidget()
        self.tb_parcelas.setColumnCount(5)
        self.tb_parcelas.setHorizontalHeaderLabels(["Vencimento", "Valor Bruto", "Taxa Est.", "Líquido Est.", "Forma Pagamento"])
        self.tb_parcelas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tb_parcelas.setMinimumHeight(200)
        l_fin.addWidget(self.tb_parcelas)
        
        # Botões Digitais e Finais
        digital_layout = QHBoxLayout()
        self.btn_gerar_pix = QPushButton("📱 Gerar PIX"); self.btn_gerar_pix.setStyleSheet("background-color: #27ae60; color: white; padding: 12px; font-weight: bold; border-radius: 5px;"); self.btn_gerar_pix.clicked.connect(self.gerar_pix_venda)
        digital_layout.addWidget(self.btn_gerar_pix)
        self.btn_gerar_boleto = QPushButton("📄 Gerar Boleto"); self.btn_gerar_boleto.setStyleSheet("background-color: #3498db; color: white; padding: 12px; font-weight: bold; border-radius: 5px;"); self.btn_gerar_boleto.clicked.connect(self.gerar_boleto_venda)
        digital_layout.addWidget(self.btn_gerar_boleto)
        digital_layout.addStretch()
        l_fin.addLayout(digital_layout)
        
        self.layout.addWidget(gb_fin)
        
        self.btn_finalizar = QPushButton("✅ SALVAR VENDA")
        self.btn_finalizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finalizar.setMinimumHeight(50)
        self.btn_finalizar.clicked.connect(self.finalizar_venda)
        self.btn_finalizar.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-size: 16px; font-weight: bold; border-radius: 6px; border: none; } QPushButton:hover { background-color: #219150; }")
        self.layout.addWidget(self.btn_finalizar)

        self.btn_cancelar_edicao = QPushButton("❌ Cancelar Edição")
        self.btn_cancelar_edicao.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar_edicao.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; border-radius: 6px; padding: 10px;")
        self.btn_cancelar_edicao.clicked.connect(self.limpar_tela_completa)
        self.btn_cancelar_edicao.hide()
        
        self.ao_mudar_condicao()

    def showEvent(self, event):
        self.load_clientes()
        self.load_produtos()
        self.carregar_vendedores()
        self.carregar_contas_bancarias_combo()
        super().showEvent(event)

    def carregar_contas_bancarias_combo(self):
        self.cb_conta_bancaria.clear()
        self.cb_conta_bancaria.addItem("Selecione a conta...", None)
        try:
            contas = self.db.obter_contas_bancarias(apenas_ativas=True)
            for c in contas:
                texto = f"{c[1]} - {c[4]}"
                self.cb_conta_bancaria.addItem(texto, c[0])
        except: pass

    def ao_mudar_condicao(self):
        txt = self.cb_condicao.currentText()
        is_custom = "Personalizado" in txt
        
        self.spin_qtd_parc.setEnabled(is_custom)
        self.spin_dias_intervalo.setEnabled(is_custom)
        
        color = "#2c3e50" if is_custom else "#95a5a6"
        self.lbl_qtd_parc.setStyleSheet(f"color: {color};")
        self.lbl_intervalo.setStyleSheet(f"color: {color};")

    def carregar_vendedores(self):
        self.cb_vendedor.clear()
        vendedores = self.db.get_lista_vendedores()
        self.cb_vendedor.addItems(vendedores)

    def load_clientes(self):
        current = self.cb_cli.currentData()
        self.cb_cli.blockSignals(True)
        self.cb_cli.clear()
        self.cb_cli.addItem("Consumidor Final / Avulso", None)
        try:
            self.db.cursor.execute("SELECT id, nome_razao FROM db_cli.entidades WHERE categoria='Cliente' ORDER BY nome_razao")
            for i, n in self.db.cursor.fetchall(): self.cb_cli.addItem(n, i)
        except: pass
        if current:
            idx = self.cb_cli.findData(current)
            if idx >= 0: self.cb_cli.setCurrentIndex(idx)
        self.cb_cli.blockSignals(False)

    def load_produtos(self):
        self.cb_produto.blockSignals(True)
        self.cb_produto.clear()
        self.cb_produto.addItem("", None)
        try:
            self.db.cursor.execute("SELECT id, nome, preco_venda, preco_custo FROM db_prod.produtos ORDER BY nome")
            for pid, nome, pv, pc in self.db.cursor.fetchall():
                self.cb_produto.addItem(f"{nome}", {'id': pid, 'nome': nome, 'pv': pv, 'pc': pc})
        except: pass
        self.cb_produto.blockSignals(False)

    def preencher_dados_produto(self):
        data = self.cb_produto.currentData()
        if data and isinstance(data, dict):
            self.spin_preco.setValue(data['pv'])
            self.txt_variacao.clear(); self.anexo_atual = None; self.btn_anexo.setText("📎 Anexar Arquivo")
        else:
            self.spin_preco.setValue(0)

    def ao_pressionar_enter_combo(self):
        text = self.cb_produto.currentText()
        idx = self.cb_produto.findText(text, Qt.MatchFlag.MatchContains)
        if idx >= 0: self.cb_produto.setCurrentIndex(idx)

    def selecionar_anexo_item(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Selecionar Anexo", "", "Arquivos (*.pdf *.jpg *.png)")
        if fname:
            self.anexo_atual = fname
            self.btn_anexo.setText(f"📎 {os.path.basename(fname)}")

    def adicionar_item(self):
        data = self.cb_produto.currentData()
        if not data: 
            mostrar_mensagem(self, 'aviso', 'Produto', "Selecione um produto.")
            return
        
        qtd = self.spin_qtd.value()
        if qtd <= 0: qtd = 1
        
        custo_produto = data.get('pc', 0.0)
        
        item = {
            'id': data['id'], 
            'nome': data['nome'], 
            'variacao': self.txt_variacao.text().strip(),
            'custo': custo_produto,
            'preco': self.spin_preco.value(), 
            'qtd': qtd,
            'ipi': self.spin_ipi.value(), 
            'icms': self.spin_icms.value(), 
            'anexo': self.anexo_atual,
            'subtotal': qtd * self.spin_preco.value(),
            'total_final': qtd * self.spin_preco.value() # IMPORTANTE
        }
        self.itens_carrinho.append(item)
        row = self.tb_itens.rowCount()
        self.tb_itens.insertRow(row)
        self.tb_itens.setItem(row, 0, QTableWidgetItem(str(item['id'])))
        self.tb_itens.setItem(row, 1, QTableWidgetItem(item['nome']))
        self.tb_itens.setItem(row, 2, QTableWidgetItem(item['variacao']))
        self.tb_itens.setItem(row, 3, QTableWidgetItem(f"{item['qtd']}"))
        self.tb_itens.setItem(row, 4, QTableWidgetItem(f"R$ {item['preco']:.2f}"))
        self.tb_itens.setItem(row, 5, QTableWidgetItem(f"R$ {item['subtotal']:.2f}"))
        self.tb_itens.setItem(row, 6, QTableWidgetItem("Sim" if item['anexo'] else ""))
        
        self.txt_variacao.clear(); self.anexo_atual = None; self.btn_anexo.setText("📎 Anexar Arquivo"); self.cb_produto.setCurrentIndex(0); self.cb_produto.setFocus()
        self.recalcular_total()

    def recalcular_total(self):
        total = sum(i['subtotal'] for i in self.itens_carrinho)
        self.lbl_total.setText(f"Total Pedido: R$ {total:,.2f}")
        return total

    def gerar_parcelas_flexivel(self):
        total = self.recalcular_total()
        if total <= 0:
            mostrar_mensagem(self, 'aviso', 'Atenção', 'Adicione itens para calcular as parcelas.')
            return
        
        condicao = self.cb_condicao.currentText()
        dt_hoje = QDate.currentDate()
        dt_base_parcelas = self.dt_pri_venc.date()
        forma = self.cb_forma_padrao.currentText()
        
        # Define a taxa estimada com base na forma escolhida (para Orçamentos)
        taxa_percentual = 0.0
        if "Débito" in forma:
            taxa_percentual = 1.99
        elif "Crédito" in forma and ("Vista" in condicao or condicao == "À Vista"): 
            taxa_percentual = 2.99
        elif "Crédito" in forma: 
            taxa_percentual = 3.99
            
        lista_parcelas_info = []

        if condicao == "À Vista":
            lista_parcelas_info = [(dt_hoje, 1.0)]
        elif condicao == "30 Dias":
            lista_parcelas_info = [(dt_base_parcelas, 1.0)]
        elif condicao == "30 / 60 Dias":
            lista_parcelas_info = [(dt_base_parcelas, 0.5), (dt_base_parcelas.addDays(30), 0.5)]
        elif condicao == "30 / 60 / 90 Dias":
            lista_parcelas_info = [(dt_base_parcelas, 0.3333), (dt_base_parcelas.addDays(30), 0.3333), (dt_base_parcelas.addDays(60), 0.3334)]
        elif condicao == "15 / 30 / 45 / 60 Dias":
            lista_parcelas_info = [(dt_base_parcelas, 0.25), (dt_base_parcelas.addDays(15), 0.25), (dt_base_parcelas.addDays(30), 0.25), (dt_base_parcelas.addDays(45), 0.25)]
        elif condicao == "Entrada + 30 Dias":
            lista_parcelas_info = [(dt_hoje, 0.5), (dt_base_parcelas, 0.5)]
        else: # Personalizado (Intervalo Fixo)
            qtd = self.spin_qtd_parc.value()
            interv = self.spin_dias_intervalo.value()
            for i in range(qtd):
                data = dt_base_parcelas.addDays(i * interv)
                lista_parcelas_info.append((data, 1/qtd))

        # Renderizar na Tabela e salvar em memória
        self.tb_parcelas.setRowCount(0)
        self.parcelas_geradas = []
        saldo_acumulado = 0.0
        
        for i, (data_venc, fator) in enumerate(lista_parcelas_info):
            self.tb_parcelas.insertRow(i)
            
            if i == len(lista_parcelas_info) - 1:
                valor_bruto = total - saldo_acumulado
            else:
                valor_bruto = round(total * fator, 2)
                saldo_acumulado += valor_bruto

            valor_taxa = valor_bruto * (taxa_percentual / 100)
            valor_liquido = valor_bruto - valor_taxa
            
            num_str = f"{i+1}/{len(lista_parcelas_info)}"
            data_str = data_venc.toString("yyyy-MM-dd")
            
            # Salva na memória para usar ao Salvar o Pedido
            self.parcelas_geradas.append({
                'numero': num_str,
                'vencimento': data_str,
                'valor': valor_bruto,
                'taxa': valor_taxa,
                'liquido': valor_liquido
            })

            item_venc = QTableWidgetItem(data_venc.toString("dd/MM/yyyy"))
            item_bruto = QTableWidgetItem(formatar_moeda_br(valor_bruto))
            
            texto_taxa = f"- {formatar_moeda_br(valor_taxa)}" if valor_taxa > 0 else "R$ 0,00"
            item_taxa = QTableWidgetItem(texto_taxa)
            if valor_taxa > 0: item_taxa.setForeground(QColor("#c0392b"))
            
            item_liquido = QTableWidgetItem(formatar_moeda_br(valor_liquido))
            item_liquido.setForeground(QColor("#27ae60"))
            
            for item in [item_venc, item_bruto, item_taxa, item_liquido]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.tb_parcelas.setItem(i, 0, item_venc)
            self.tb_parcelas.setItem(i, 1, item_bruto)
            self.tb_parcelas.setItem(i, 2, item_taxa)
            self.tb_parcelas.setItem(i, 3, item_liquido)
            
            cb = ExtendedComboBox()
            cb.addItems(["Boleto", "Pix", "Cartão Crédito", "Cartão Débito", "Dinheiro", "Transferência"])
            cb.setCurrentText(forma)
            cb.currentTextChanged.connect(self.gerar_parcelas_flexivel) 
            self.tb_parcelas.setCellWidget(i, 4, cb)

    def abrir_dialogo_personalizado(self):
        total = self.recalcular_total()
        if total <= 0:
            mostrar_mensagem(self, 'aviso', 'Atenção', 'Adicione itens ao carrinho antes de configurar o pagamento.')
            return

        # Assumindo que você tem CustomPaymentDialog importado/definido
        try:
            dlg = CustomPaymentDialog(total, self.dt_pri_venc.date(), self)
            if dlg.exec():
                parcelas = dlg.parcelas_geradas
                forma_padrao = self.cb_forma_padrao.currentText()
                
                self.tb_parcelas.setRowCount(0)
                self.parcelas_geradas = []
                
                for i, p in enumerate(parcelas):
                    self.tb_parcelas.insertRow(i)
                    val_bruto = p.get('val', 0.0)
                    dt_venc = p.get('dt', QDate.currentDate())
                    
                    self.parcelas_geradas.append({
                        'numero': f"{i+1}/{len(parcelas)}",
                        'vencimento': dt_venc.toString("yyyy-MM-dd"),
                        'valor': val_bruto,
                        'taxa': 0.0,
                        'liquido': val_bruto
                    })

                    item_venc = QTableWidgetItem(dt_venc.toString("dd/MM/yyyy"))
                    item_bruto = QTableWidgetItem(formatar_moeda_br(val_bruto))
                    item_taxa = QTableWidgetItem("R$ 0,00")
                    item_liquido = QTableWidgetItem(formatar_moeda_br(val_bruto))
                    item_liquido.setForeground(QColor("#27ae60"))

                    for item in [item_venc, item_bruto, item_taxa, item_liquido]:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    self.tb_parcelas.setItem(i, 0, item_venc)
                    self.tb_parcelas.setItem(i, 1, item_bruto)
                    self.tb_parcelas.setItem(i, 2, item_taxa)
                    self.tb_parcelas.setItem(i, 3, item_liquido)
                    
                    cb = ExtendedComboBox()
                    cb.addItems(["Boleto", "Pix", "Cartão Crédito", "Dinheiro", "Transferência"])
                    cb.setCurrentText(forma_padrao)
                    self.tb_parcelas.setCellWidget(i, 4, cb)
                
                self.cb_condicao.setCurrentIndex(-1)
        except Exception as e:
            mostrar_mensagem(self, 'erro', 'Erro', str(e))

    def carregar_pedido_para_edicao(self, venda_id):
        self.limpar_tela_completa()
        self.venda_id_edicao = venda_id
        
        self.lbl_titulo.setText(f"✏️ Editando Pedido #{venda_id}")
        self.lbl_titulo.setStyleSheet("color: #f39c12; font-size: 20px; font-weight: 800;")
        self.btn_finalizar.setText("💾 SALVAR ALTERAÇÕES")
        self.btn_cancelar_edicao.show()

        try:
            self.db.cursor.execute("""
                SELECT data_venda, cliente_id, vendedor, status, nota_fiscal, descricao_pedido, conta_id
                FROM main.vendas 
                WHERE id = ?
            """, (venda_id,))
            row = self.db.cursor.fetchone()
            
            if not row: 
                mostrar_mensagem(self, 'erro', 'Erro', 'Pedido não encontrado.')
                return
            
            r_data, r_cli_id, r_vendedor, r_status, r_nf, r_desc, r_conta_id = row

            try: dt = datetime.strptime(r_data, "%Y-%m-%d")
            except: dt = QDate.currentDate()
            self.dt_emissao.setDate(dt)
            
            idx = self.cb_cli.findData(r_cli_id)
            if idx >= 0: self.cb_cli.setCurrentIndex(idx)
            
            self.cb_vendedor.setCurrentText(str(r_vendedor) if r_vendedor else "")
            self.cb_status.setCurrentText(str(r_status) if r_status else "")
            self.txt_nf.setText(str(r_nf) if r_nf else "")
            self.txt_descricao.setText(str(r_desc) if r_desc else "")
            
            if r_conta_id:
                idx_conta = self.cb_conta_bancaria.findData(r_conta_id)
                if idx_conta >= 0: self.cb_conta_bancaria.setCurrentIndex(idx_conta)

            self.db.cursor.execute("""
                SELECT iv.id, iv.produto_id, iv.quantidade, iv.preco_unitario, iv.subtotal, 
                       iv.detalhes, iv.variacao, iv.preco_custo, iv.ipi, iv.icms, iv.anexo_path,
                       p.nome 
                FROM main.itens_venda iv
                JOIN db_prod.produtos p ON iv.produto_id = p.id
                WHERE iv.venda_id = ?
            """, (venda_id,))
            itens_db = self.db.cursor.fetchall()
            
            self.itens_carrinho = []
            self.tb_itens.setRowCount(0)

            for item_db in itens_db:
                i_qtd = int(item_db[2]) if item_db[2] else 1
                item = {
                    'id': item_db[1], 'nome': item_db[11],
                    'variacao': item_db[6] if item_db[6] else "",
                    'custo': float(item_db[7]) if item_db[7] else 0.0,
                    'preco': float(item_db[3]) if item_db[3] else 0.0,
                    'qtd': i_qtd,
                    'ipi': float(item_db[8]) if item_db[8] else 0.0,
                    'icms': float(item_db[9]) if item_db[9] else 0.0,
                    'anexo': item_db[10],
                    'subtotal': float(item_db[4]) if item_db[4] else 0.0,
                    'total_final': float(item_db[4]) if item_db[4] else 0.0
                }
                self.itens_carrinho.append(item)
                r = self.tb_itens.rowCount()
                self.tb_itens.insertRow(r)
                self.tb_itens.setItem(r, 0, QTableWidgetItem(str(item['id'])))
                self.tb_itens.setItem(r, 1, QTableWidgetItem(item['nome']))
                self.tb_itens.setItem(r, 2, QTableWidgetItem(item['variacao']))
                self.tb_itens.setItem(r, 3, QTableWidgetItem(f"{item['qtd']}"))
                self.tb_itens.setItem(r, 4, QTableWidgetItem(f"R$ {item['preco']:.2f}"))
                self.tb_itens.setItem(r, 5, QTableWidgetItem(f"R$ {item['subtotal']:.2f}"))
                self.tb_itens.setItem(r, 6, QTableWidgetItem("Sim" if item['anexo'] else ""))

            self.recalcular_total()

            self.db.cursor.execute("SELECT data_vencimento, valor_previsto, forma_pagamento FROM db_fin.contas_receber WHERE venda_id = ?", (venda_id,))
            parcelas_db = self.db.cursor.fetchall()
            
            self.tb_parcelas.setRowCount(0)
            self.parcelas_geradas = []
            
            for i, p in enumerate(parcelas_db):
                self.tb_parcelas.insertRow(i)
                
                try: 
                    dt_v = datetime.strptime(p[0], "%Y-%m-%d")
                    dt_str = dt_v.strftime("%d/%m/%Y")
                    dt_db = dt_v.strftime("%Y-%m-%d")
                except: 
                    dt_str = str(p[0])
                    dt_db = str(p[0])
                
                val_bruto = float(p[1])
                
                self.parcelas_geradas.append({
                    'numero': f"{i+1}/{len(parcelas_db)}",
                    'vencimento': dt_db,
                    'valor': val_bruto,
                    'taxa': 0.0,
                    'liquido': val_bruto
                })
                
                item_venc = QTableWidgetItem(dt_str)
                item_bruto = QTableWidgetItem(formatar_moeda_br(val_bruto))
                item_taxa = QTableWidgetItem("R$ 0,00")
                item_liquido = QTableWidgetItem(formatar_moeda_br(val_bruto))
                item_liquido.setForeground(QColor("#27ae60"))

                for item in [item_venc, item_bruto, item_taxa, item_liquido]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.tb_parcelas.setItem(i, 0, item_venc)
                self.tb_parcelas.setItem(i, 1, item_bruto)
                self.tb_parcelas.setItem(i, 2, item_taxa)
                self.tb_parcelas.setItem(i, 3, item_liquido)
                
                cb = ExtendedComboBox()
                cb.addItems(["Boleto", "Pix", "Cartão Crédito", "Dinheiro", "Transferência"])
                cb.setCurrentText(str(p[2]) if p[2] else "Dinheiro")
                self.tb_parcelas.setCellWidget(i, 4, cb)
                
            self.cb_condicao.setCurrentText("Personalizado (Intervalo Fixo)")

        except Exception as e:
            mostrar_mensagem(self, 'erro', 'Erro Carregar', f"Detalhe do erro: {str(e)}")

    def limpar_tela_completa(self):
        self.venda_id_edicao = None
        self.itens_carrinho = []
        self.parcelas_geradas = []
        self.tb_itens.setRowCount(0)
        self.tb_parcelas.setRowCount(0)
        self.lbl_total.setText("Total Pedido: R$ 0,00")
        
        self.cb_vendedor.setCurrentIndex(-1)
        self.txt_nf.clear()
        self.txt_descricao.clear() 
        self.cb_cli.setCurrentIndex(0)
        self.cb_status.setCurrentIndex(0)
        self.dt_emissao.setDate(QDate.currentDate())
        
        self.cb_condicao.setCurrentIndex(0)
        self.dt_pri_venc.setDate(QDate.currentDate())
        self.cb_conta_bancaria.setCurrentIndex(0)
        
        self.lbl_titulo.setText("🛒 Lançar Pedido")
        self.lbl_titulo.setStyleSheet("font-size: 20px; font-weight: 800; color: #1e293b;")
        self.btn_finalizar.setText("✅ SALVAR VENDA")
        self.btn_cancelar_edicao.hide()

    def finalizar_venda(self):
        if not self.itens_carrinho:
            mostrar_mensagem(self, "aviso", "Carrinho Vazio", "Adicione produtos antes de salvar.")
            return

        cliente_id = self.cb_cli.currentData()
        if not cliente_id:
            mostrar_mensagem(self, "aviso", "Cliente Inválido", "Selecione um cliente.")
            return

        vendedor_nome = self.cb_vendedor.currentText()
        nota_fiscal = self.txt_nf.text()
        status = self.cb_status.currentText()
        condicao_pagamento = self.cb_condicao.currentText()
        data_venda = self.dt_emissao.date().toString("yyyy-MM-dd")
        descricao = self.txt_descricao.text()
        
        valor_bruto = sum(i['total_final'] for i in self.itens_carrinho)
        desconto_geral = 0.0 
        valor_liquido = valor_bruto - desconto_geral

        try:
            # --- TRANSAÇÃO ATÔMICA (SEGURANÇA FINANCEIRA) ---
            self.db.cursor.execute("BEGIN TRANSACTION")

            if self.venda_id_edicao:
                self.db.cursor.execute("""
                    UPDATE main.vendas SET 
                        cliente_id=?, vendedor=?, valor_bruto=?, desconto_geral=?, 
                        valor_liquido=?, status=?, nota_fiscal=?, 
                        forma_pagamento_prevista=?, data_venda=?, descricao_pedido=?
                    WHERE id=?
                """, (cliente_id, vendedor_nome, valor_bruto, desconto_geral, 
                      valor_liquido, status, nota_fiscal, 
                      condicao_pagamento, data_venda, descricao, self.venda_id_edicao))
                
                venda_id = self.venda_id_edicao
                
                self.db.cursor.execute("DELETE FROM main.itens_venda WHERE venda_id=?", (venda_id,))
                self.db.cursor.execute("DELETE FROM db_fin.contas_receber WHERE venda_id=?", (venda_id,))
                
            else:
                self.db.cursor.execute("""
                    INSERT INTO main.vendas (
                        data_venda, cliente_id, vendedor, valor_bruto, desconto_geral, 
                        valor_liquido, status, nota_fiscal, forma_pagamento_prevista, descricao_pedido
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (data_venda, cliente_id, vendedor_nome, valor_bruto, desconto_geral, 
                      valor_liquido, status, nota_fiscal, condicao_pagamento, descricao))
                
                venda_id = self.db.cursor.lastrowid

            # Inserir Itens
            for item in self.itens_carrinho:
                prod_id = item['id']
                qtd = item['qtd']
                preco_unit = item['preco'] 
                subtotal = item['subtotal']
                detalhes = item.get('variacao', '')
                custo = item.get('custo', 0)
                
                self.db.cursor.execute("""
                    INSERT INTO main.itens_venda (
                        venda_id, produto_id, quantidade, preco_unitario, subtotal, 
                        detalhes, preco_custo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (venda_id, prod_id, qtd, preco_unit, subtotal, detalhes, custo))
                
                if status in ["Faturado", "Entregue", "Concluido"]:
                    self.db.cursor.execute("""
                        UPDATE db_prod.produtos 
                        SET estoque_atual = estoque_atual - ? 
                        WHERE id = ?
                    """, (qtd, prod_id))

            # 4. Gerar Financeiro VIA SERVICE
            if self.parcelas_geradas:
                for p in self.parcelas_geradas:
                    FinanceiroService.criar_recebimento(
                        cursor=self.db.cursor,
                        cliente_id=cliente_id,
                        descricao=f"Pedido #{venda_id} - {descricao}",
                        valor=p['valor'],
                        vencimento=p['vencimento'],
                        forma_pagamento=condicao_pagamento,
                        venda_id=venda_id,
                        num_parcela=p['numero']
                    )
            else:
                FinanceiroService.criar_recebimento(
                    cursor=self.db.cursor,
                    cliente_id=cliente_id,
                    descricao=f"Pedido #{venda_id}",
                    valor=valor_liquido,
                    vencimento=data_venda,
                    forma_pagamento=condicao_pagamento,
                    venda_id=venda_id,
                    num_parcela='1/1'
                )

            self.db.conn.commit()
            mostrar_mensagem(self, "sucesso", "Sucesso", f"Pedido #{venda_id} salvo corretamente!")
            
            self.limpar_tela_completa()
            self.pedido_salvo_signal.emit()
            
        except Exception as e:
            self.db.conn.rollback()
            print(f"Erro ao salvar pedido: {e}")
            traceback.print_exc()
            mostrar_mensagem(self, "erro", "Erro Crítico", f"Falha ao salvar pedido.\nNenhuma alteração foi feita.\nErro: {e}")

    def gerar_pix_venda(self):
        """Gera QR Code PIX para a venda"""
        total_atual = self.recalcular_total()
        
        if total_atual <= 0:
            QMessageBox.warning(self, "Atenção", "Adicione itens à venda primeiro!")
            return
        
        try:
            chave = self.db.obter_configuracao("pix_chave", "")
            if not chave:
                resp = QMessageBox.question(self, "Configurar PIX",
                    "Chave PIX não configurada!\n\nDeseja configurar agora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if resp == QMessageBox.StandardButton.Yes:
                    chave, ok = QInputDialog.getText(self, "Chave PIX", 
                        "Digite sua chave PIX (email, telefone ou CPF/CNPJ):")
                    if ok and chave:
                        self.db.salvar_configuracao("pix_chave", chave)
                    else:
                        return
                else:
                    return
            
            empresa = self.db.obter_configuracao("empresa_nome", "Minha Empresa")
            cidade = self.db.obter_configuracao("empresa_cidade", "Sao Paulo")
            
            payload = gerar_pix_payload(chave, total_atual, empresa, cidade, "Venda")
            if not payload:
                QMessageBox.critical(self, "Erro", "Erro ao gerar PIX!")
                return
            
            qr_code = gerar_qr_code_pix(payload)
            if not qr_code:
                QMessageBox.critical(self, "Erro", "Erro ao gerar QR Code!")
                return
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"PIX - {formatar_moeda_br(total_atual)}")
            dialog.setMinimumSize(450, 550)
            
            layout = QVBoxLayout()
            
            titulo = QLabel(f"💰 Pagamento PIX\n{formatar_moeda_br(total_atual)}")
            titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #27ae60; padding: 10px;")
            titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(titulo)
            
            label_qr = QLabel()
            pixmap = QPixmap()
            img_data = base64.b64decode(qr_code.split(',')[1])
            pixmap.loadFromData(img_data)
            pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
            label_qr.setPixmap(pixmap)
            label_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label_qr)
            
            inst = QLabel("📱 Escaneie o QR Code\nou copie o código abaixo:")
            inst.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inst.setStyleSheet("font-size: 12px; color: #7f8c8d;")
            layout.addWidget(inst)
            
            text_codigo = QLineEdit(payload)
            text_codigo.setReadOnly(True)
            text_codigo.setStyleSheet("padding: 8px; font-size: 10px;")
            layout.addWidget(text_codigo)
            
            btn_layout = QHBoxLayout()
            
            btn_copiar = QPushButton("📋 Copiar")
            btn_copiar.setStyleSheet("background-color: #3498db; color: white; padding: 10px; border-radius: 5px;")
            btn_copiar.clicked.connect(lambda: QApplication.clipboard().setText(payload))
            btn_layout.addWidget(btn_copiar)
            
            btn_fechar = QPushButton("✓ Fechar")
            btn_fechar.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; border-radius: 5px;")
            btn_fechar.clicked.connect(dialog.accept)
            btn_layout.addWidget(btn_fechar)
            
            layout.addLayout(btn_layout)
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PIX:\n\n{str(e)}")
    
    def gerar_boleto_venda(self):
        """Gera boleto bancário para a venda"""
        total_atual = self.recalcular_total()

        if total_atual <= 0:
            QMessageBox.warning(self, "Atenção", "Adicione itens à venda primeiro!")
            return
        
        try:
            banco = self.db.obter_configuracao("banco_codigo", "")
            agencia = self.db.obter_configuracao("banco_agencia", "")
            conta = self.db.obter_configuracao("banco_conta", "")
            
            if not all([banco, agencia, conta]):
                QMessageBox.warning(self, "Configuração", 
                    "Configure os dados bancários primeiro!\n\n"
                    "Necessário: Código do Banco, Agência e Conta")
                return
            
            venc, ok = QInputDialog.getText(self, "Vencimento",
                "Data de vencimento (DD/MM/AAAA):",
                text=(datetime.now() + timedelta(days=3)).strftime("%d/%m/%Y"))
            
            if not ok or not venc:
                return
            
            try:
                dia, mes, ano = venc.split('/')
                data_venc = f"{ano}-{mes}-{dia}"
            except:
                QMessageBox.warning(self, "Erro", "Data inválida!")
                return
            
            nosso_numero = str(int(time.time()))[-11:]
            
            codigo_barras = gerar_codigo_barras_boleto(
                banco, total_atual, data_venc, nosso_numero, agencia, conta
            )
            
            if not codigo_barras:
                QMessageBox.critical(self, "Erro", "Erro ao gerar boleto!")
                return
            
            linha_digitavel = gerar_linha_digitavel_boleto(codigo_barras)
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Boleto - {formatar_moeda_br(total_atual)}")
            dialog.setMinimumSize(650, 450)
            
            layout = QVBoxLayout()
            
            titulo = QLabel(f"📄 Boleto Bancário\n{formatar_moeda_br(total_atual)}")
            titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #3498db; padding: 10px;")
            titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(titulo)
            
            info = QLabel(f"🏦 Banco: {banco} | 📅 Vencimento: {venc}")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info.setStyleSheet("font-size: 12px; color: #7f8c8d; margin-bottom: 10px;")
            layout.addWidget(info)
            
            lbl_linha = QLabel("📋 Linha Digitável:")
            lbl_linha.setStyleSheet("font-weight: bold; margin-top: 15px;")
            layout.addWidget(lbl_linha)
            
            text_linha = QLineEdit(linha_digitavel)
            text_linha.setReadOnly(True)
            text_linha.setStyleSheet("font-family: monospace; font-size: 11px; padding: 10px;")
            layout.addWidget(text_linha)
            
            lbl_codigo = QLabel("Código de Barras:")
            lbl_codigo.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(lbl_codigo)
            
            text_codigo = QLineEdit(codigo_barras)
            text_codigo.setReadOnly(True)
            text_codigo.setStyleSheet("font-family: monospace; font-size: 9px; padding: 10px;")
            layout.addWidget(text_codigo)
            
            btn_layout = QHBoxLayout()
            
            btn_copiar = QPushButton("📋 Copiar Linha")
            btn_copiar.setStyleSheet("background-color: #3498db; color: white; padding: 10px; border-radius: 5px;")
            btn_copiar.clicked.connect(lambda: QApplication.clipboard().setText(linha_digitavel))
            btn_layout.addWidget(btn_copiar)
            
            btn_fechar = QPushButton("✓ Fechar")
            btn_fechar.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; border-radius: 5px;")
            btn_fechar.clicked.connect(dialog.accept)
            btn_layout.addWidget(btn_fechar)
            
            layout.addLayout(btn_layout)
            layout.addStretch()
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar boleto:\n\n{str(e)}")

class ExtendedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def showPopup(self):
        super().showPopup()

    def mousePressEvent(self, event):
        # Se for clicável e não tiver o popup aberto, abre
        if event.button() == Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            if not self.view().isVisible():
                self.showPopup()
        else:
            super().mousePressEvent(event)

class CustomPaymentDialog(QDialog):
    def __init__(self, total_venda, data_base_parcelas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Condição Personalizada")
        self.setFixedSize(500, 550) # Aumentei um pouco
        self.total = total_venda
        
        # Data Base Parcelas = O que está no campo "1º Vencimento" da tela principal
        self.dt_base_parcelas = data_base_parcelas 
        self.parcelas_geradas = []

        layout = QVBoxLayout(self)

        # --- RESUMO ---
        lbl_total = QLabel(f"Total do Pedido: R$ {self.total:,.2f}")
        lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_total)

        gb_config = QFrame()
        gb_config.setStyleSheet("background-color: #f8f9fa; border: 1px solid #bdc3c7; border-radius: 5px;")
        l_conf = QFormLayout(gb_config)

        # 1. Entrada (Com DATA diferente)
        self.spin_entrada = QDoubleSpinBox()
        self.spin_entrada.setPrefix("R$ ")
        self.spin_entrada.setMaximum(self.total)
        self.spin_entrada.setValue(0.0)
        self.spin_entrada.valueChanged.connect(self.atualizar_saldo)
        
        # Campo novo: DATA DA ENTRADA
        self.dt_entrada = QDateEdit(QDate.currentDate())
        self.dt_entrada.setCalendarPopup(True)
        self.dt_entrada.setDisplayFormat("dd/MM/yyyy")
        
        hbox_entrada = QHBoxLayout()
        hbox_entrada.addWidget(self.spin_entrada)
        hbox_entrada.addWidget(QLabel("Data:"))
        hbox_entrada.addWidget(self.dt_entrada)
        
        l_conf.addRow("Valor Entrada:", hbox_entrada)

        self.lbl_saldo = QLabel(f"Restante a Parcelar: R$ {self.total:,.2f}")
        self.lbl_saldo.setStyleSheet("color: #e74c3c; font-weight: bold;")
        l_conf.addRow("", self.lbl_saldo)
        
        # Separador visual
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Sunken)
        l_conf.addRow(line)
        
        l_info_base = QLabel(f"As parcelas começarão a contar de: {self.dt_base_parcelas.toString('dd/MM/yyyy')}")
        l_info_base.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        l_conf.addRow(l_info_base)

        # 2. Configuração dos Dias (Parcelas)
        self.txt_dias = QLineEdit()
        self.txt_dias.setPlaceholderText("Ex: 0, 30, 60")
        self.txt_dias.setToolTip("0 = Dia do 1º Vencimento. 30 = 30 dias após o 1º Vencimento.")
        l_conf.addRow("Dias (após 1º Venc.):", self.txt_dias)

        layout.addWidget(gb_config)
        
        btn_simular = QPushButton("🔄 Simular Parcelas")
        btn_simular.clicked.connect(self.simular)
        btn_simular.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        layout.addWidget(btn_simular)

        # --- PREVIEW ---
        self.tb_preview = QTableWidget()
        self.tb_preview.setColumnCount(5) # Mudou de 3 para 5
        self.tb_preview.setHorizontalHeaderLabels([
            "Parcela", "Vencimento", "Valor Bruto", "Taxa Est.", "Valor Líquido"
        ])
        # Ajusta o tamanho das colunas para caber certinho
        self.tb_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Botões Finais
        hbox = QHBoxLayout()
        btn_ok = QPushButton("✅ Confirmar")
        btn_ok.clicked.connect(self.confirmar)
        btn_ok.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        hbox.addWidget(btn_cancel)
        hbox.addWidget(btn_ok)
        layout.addLayout(hbox)

    def atualizar_saldo(self):
        restante = self.total - self.spin_entrada.value()
        self.lbl_saldo.setText(f"Restante a Parcelar: R$ {restante:,.2f}")

    def simular(self):
        entrada = self.spin_entrada.value()
        saldo = self.total - entrada
        
        txt_dias = self.txt_dias.text().replace(" ", "")
        
        # Se tem saldo mas não digitou dias
        if not txt_dias and saldo > 0:
            QMessageBox.warning(self, "Aviso", "Digite os dias para as parcelas do saldo restante.\nEx: Digite '0' para a primeira parcela ser na data base.")
            return

        self.parcelas_geradas = []
        self.tb_preview.setRowCount(0)

        # 1. Adiciona Entrada (se houver) usando a DATA DA ENTRADA
        if entrada > 0:
            self.parcelas_geradas.append({'dt': self.dt_entrada.date(), 'val': entrada})

        # 2. Processa o saldo (Parcelas)
        if saldo > 0:
            try:
                lista_dias = [int(d) for d in txt_dias.split(',') if d != '']
                if not lista_dias: raise ValueError
                
                valor_parc = saldo / len(lista_dias)
                
                # A base de cálculo é a data que veio da tela anterior (dt_base_parcelas)
                for dias_offset in lista_dias:
                    dt_venc = self.dt_base_parcelas.addDays(dias_offset)
                    self.parcelas_geradas.append({'dt': dt_venc, 'val': valor_parc})
            except:
                QMessageBox.warning(self, "Erro", "Formato de dias inválido.\nUse números separados por vírgula (ex: 0,30,60).")
                return

        # Renderiza na tabela
        self.tb_preview.setRowCount(len(self.parcelas_geradas))
        for i, p in enumerate(self.parcelas_geradas):
            self.tb_preview.setItem(i, 0, QTableWidgetItem(p['dt'].toString("dd/MM/yyyy")))
            self.tb_preview.setItem(i, 1, QTableWidgetItem(f"R$ {p['val']:,.2f}"))

    def confirmar(self):
        if not self.parcelas_geradas:
            self.simular()
        
        soma = sum([p['val'] for p in self.parcelas_geradas])
        if abs(soma - self.total) > 0.05:
             QMessageBox.warning(self, "Erro", f"A soma das parcelas ({soma}) não bate com o total ({self.total}).")
             return
             
        self.accept()
                
class DialogoParcelasHoje(QDialog):
    def __init__(self, db_context, parent=None):
        super().__init__(parent)
        self.db = db_context
        self.setWindowTitle("📅 Parcelas Vencendo Hoje")
        self.setFixedWidth(600)
        self.setStyleSheet("""
            QDialog { background-color: #f0f2f5; }
            
            QTableWidget { 
                background-color: white; 
                color: #2c3e50; /* <--- ADICIONE ISTO: Força a letra a ser cinza escuro/preto */
                border: 1px solid #bdc3c7; 
                gridline-color: #ecf0f1;
            }
            
            /* Para garantir que o cabeçalho continue legível (fundo escuro, letra clara) */
            QHeaderView::section { 
                background-color: #34495e; 
                color: white; 
                font-weight: bold; 
                padding: 4px;
                border: none;
            }

            QLabel { font-size: 14px; color: #2c3e50; font-weight: bold; }
            QPushButton { padding: 8px; border-radius: 4px; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self)
        
        # Cabeçalho
        lbl_info = QLabel("As seguintes parcelas vencem hoje. Selecione as que deseja baixar:")
        layout.addWidget(lbl_info)
        
        # Tabela
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["", "ID", "Cliente", "Descrição", "Valor"])
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.tabela)
        
        # Botões
        hbox_btn = QHBoxLayout()
        self.lbl_total = QLabel("Total: R$ 0,00")
        
        btn_lancar = QPushButton("💰 Lançar Selecionadas")
        btn_lancar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_lancar.setStyleSheet("background-color: #27ae60; color: white;")
        btn_lancar.clicked.connect(self.lancar_parcelas)
        
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fechar.setStyleSheet("background-color: #95a5a6; color: white;")
        btn_fechar.clicked.connect(self.reject)
        
        hbox_btn.addWidget(self.lbl_total)
        hbox_btn.addStretch()
        hbox_btn.addWidget(btn_fechar)
        hbox_btn.addWidget(btn_lancar)
        layout.addLayout(hbox_btn)
        
        self.carregar_dados()

    def carregar_dados(self):
        hoje = QDate.currentDate().toString("yyyy-MM-dd")
        
        # Busca parcelas vencendo hoje que ainda não foram pagas
        query = """
            SELECT r.id, c.nome_razao, r.descricao, r.valor_previsto 
            FROM db_fin.contas_receber r
            LEFT JOIN db_cli.entidades c ON r.cliente_id = c.id
            WHERE r.data_vencimento = ? AND r.status != 'Recebido'
        """
        try:
            self.db.cursor.execute(query, (hoje,))
            rows = self.db.cursor.fetchall()
            
            self.tabela.setRowCount(0)
            total = 0.0
            
            for i, row in enumerate(rows):
                self.tabela.insertRow(i)
                rid, cli, desc, val = row
                
                # Checkbox (Selecionado por padrão)
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                chk_item.setCheckState(Qt.CheckState.Checked)
                self.tabela.setItem(i, 0, chk_item)
                
                self.tabela.setItem(i, 1, QTableWidgetItem(str(rid)))
                self.tabela.setItem(i, 2, QTableWidgetItem(cli if cli else "Avulso"))
                self.tabela.setItem(i, 3, QTableWidgetItem(desc))
                self.tabela.setItem(i, 4, QTableWidgetItem(f"R$ {val:,.2f}"))
                
                total += val
                
            self.lbl_total.setText(f"Total Hoje: R$ {total:,.2f}")
        except Exception as e:
            print(f"Erro ao carregar parcelas do dia: {e}")

    def lancar_parcelas(self):
        ids_para_baixar = []
        for i in range(self.tabela.rowCount()):
            # Verifica se o checkbox está marcado
            if self.tabela.item(i, 0).checkState() == Qt.CheckState.Checked:
                rid = int(self.tabela.item(i, 1).text())
                ids_para_baixar.append(rid)
        
        if not ids_para_baixar:
            mostrar_mensagem(self, 'aviso', 'Atenção', 'Nenhuma parcela selecionada.')
            return

        if mostrar_mensagem(self, 'confirma', 'Confirmar Baixa', f"Deseja baixar {len(ids_para_baixar)} parcelas selecionadas?"):
            hoje = QDate.currentDate().toString("yyyy-MM-dd")
            try:
                for rid in ids_para_baixar:
                    # Atualiza para Recebido
                    self.db.cursor.execute("""
                        UPDATE db_fin.contas_receber 
                        SET status='Recebido', data_recebimento=?, valor_recebido=valor_previsto 
                        WHERE id=?
                    """, (hoje, rid))
                
                self.db.conn.commit()
                mostrar_mensagem(self, 'sucesso', 'Sucesso', "Parcelas lançadas com sucesso!")
                self.accept() # Fecha o diálogo
            except Exception as e:
                self.db.conn.rollback()
                mostrar_mensagem(self, 'erro', 'Erro', str(e))

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox

class DialogoReceberParcela(QDialog):
    """Pop-up detalhado para receber uma parcela de um pedido/orçamento"""
    def __init__(self, db_context, parcela_id, valor_original, parent=None):
        super().__init__(parent)
        self.db = db_context
        self.parcela_id = parcela_id
        self.valor_original = float(valor_original)
        
        self.setWindowTitle("💰 Processar Recebimento")
        self.setMinimumSize(450, 350)
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-weight: bold; color: #2c3e50; font-size: 13px; }
            QComboBox { padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px; background: white; }
            QPushButton { font-weight: bold; border-radius: 4px; padding: 10px; color: white; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Cabeçalho
        lbl_titulo = QLabel(f"Recebendo Parcela ID: {parcela_id}")
        lbl_titulo.setStyleSheet("font-size: 16px; color: #27ae60; margin-bottom: 10px;")
        layout.addWidget(lbl_titulo)

        # Valor original
        self.lbl_valor = QLabel(f"Valor Previsto: {formatar_moeda_br(self.valor_original)}")
        self.lbl_valor.setStyleSheet("font-size: 14px; background: #ecf0f1; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.lbl_valor)

        # Conta Bancária
        layout.addWidget(QLabel("Conta de Destino:"))
        self.cb_conta = QComboBox()
        self.cb_conta.currentIndexChanged.connect(self.atualizar_taxas)
        layout.addWidget(self.cb_conta)

        # Forma de Pagamento
        layout.addWidget(QLabel("Forma de Pagamento:"))
        self.cb_forma = QComboBox()
        self.cb_forma.addItems(["Dinheiro", "PIX", "Transferência", "Débito", "Crédito Vista", "Crédito Parcelado"])
        self.cb_forma.currentTextChanged.connect(self.atualizar_taxas)
        layout.addWidget(self.cb_forma)

        # Info de Taxa (Escondida por padrão)
        self.lbl_taxa = QLabel("")
        self.lbl_taxa.setStyleSheet("color: #c0392b; font-size: 13px; font-weight: bold; padding: 5px;")
        self.lbl_taxa.setVisible(False)
        layout.addWidget(self.lbl_taxa)

        # Botões
        btn_layout = QHBoxLayout()
        btn_confirmar = QPushButton("✅ Confirmar Recebimento")
        btn_confirmar.setStyleSheet("background-color: #27ae60;")
        btn_confirmar.clicked.connect(self.confirmar)
        
        btn_cancelar = QPushButton("❌ Cancelar")
        btn_cancelar.setStyleSheet("background-color: #95a5a6;")
        btn_cancelar.clicked.connect(self.reject)

        btn_layout.addWidget(btn_confirmar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)

        self.carregar_contas()
        self.atualizar_taxas()

    def carregar_contas(self):
        self.cb_conta.clear()
        contas = self.db.obter_contas_bancarias(apenas_ativas=True)
        for conta in contas:
            # Padding de segurança caso a tupla seja curta
            c = conta + (None,) * (15 - len(conta))
            texto = f"ID {c[0]} - {c[1]} ({c[4]})"
            self.cb_conta.addItem(texto, c[0]) # Salva o ID real no userData

    def atualizar_taxas(self):
        conta_id = self.cb_conta.currentData()
        forma = self.cb_forma.currentText()

        if conta_id and forma in ["Débito", "Crédito Vista", "Crédito Parcelado"]:
            conta = self.db.obter_conta_bancaria(conta_id)
            c = conta + (None,) * (15 - len(conta)) if conta else None
            
            if c and c[4] == "Maquininha":
                taxa = float(c[8] if forma == "Débito" else (c[9] if forma == "Crédito Vista" else c[10]))
                valor_taxa = self.valor_original * (taxa / 100)
                valor_liquido = self.valor_original - valor_taxa
                
                self.lbl_taxa.setText(f"⚠️ Taxa Maquininha ({taxa}%): -{formatar_moeda_br(valor_taxa)} | Líquido a Receber: {formatar_moeda_br(valor_liquido)}")
                self.lbl_taxa.setVisible(True)
                return
                
        self.lbl_taxa.setVisible(False)

    def confirmar(self):
        conta_id = self.cb_conta.currentData()
        forma = self.cb_forma.currentText()
        
        if not conta_id:
            QMessageBox.warning(self, "Aviso", "Selecione uma conta!")
            return
            
        # 1. Atualizar a conta a receber para 'Recebido'
        from datetime import datetime
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        try:
            self.db.cursor.execute("""
                UPDATE db_fin.contas_receber 
                SET status = 'Recebido', data_recebimento = ?, forma_pagamento = ?
                WHERE id = ?
            """, (hoje, forma, self.parcela_id))
            
            # 2. Registrar na movimentação bancária com a taxa calculada
            sucesso, v_liquido = self.db.registrar_movimentacao_bancaria(
                conta_id, "Entrada", self.valor_original, forma, "Recebimento de Pedido", self.parcela_id, f"Recebimento Parcela #{self.parcela_id}"
            )
            
            if sucesso:
                self.db.conn.commit()
                QMessageBox.information(self, "Sucesso", "✅ Parcela recebida e saldo em conta atualizado!")
                self.accept()
            else:
                self.db.conn.rollback()
                QMessageBox.critical(self, "Erro", "Erro ao atualizar saldo da conta bancária.")
                
        except Exception as e:
            self.db.conn.rollback()
            QMessageBox.critical(self, "Erro", f"Erro crítico: {e}")

class DialogoDetalhesParcelas(QDialog):
    def __init__(self, db, venda_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.venda_id = venda_id
        self.setWindowTitle(f"💲 Parcelas do Pedido #{venda_id}")
        self.setFixedWidth(550)
        self.setStyleSheet("""
            QDialog { background-color: #f0f2f5; }
            QTableWidget { background-color: white; border: 1px solid #bdc3c7; }
            QPushButton { padding: 6px; border-radius: 4px; font-weight: bold; }
            QLabel { font-size: 14px; font-weight: bold; color: #2c3e50; }
        """)

        layout = QVBoxLayout(self)
        
        # Resumo
        self.lbl_resumo = QLabel("Carregando...")
        layout.addWidget(self.lbl_resumo)

        # Tabela de Parcelas
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["Parc.", "Vencimento", "Valor", "Status", "Ação"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabela.verticalHeader().setVisible(False)
        layout.addWidget(self.tabela)

        # Botão Fechar
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("background-color: #95a5a6; color: white;")
        layout.addWidget(btn_close)

        self.carregar_parcelas()

    def carregar_parcelas(self):
        self.tabela.setRowCount(0)
        
        # Busca todas as parcelas dessa venda
        query = """
            SELECT id, num_parcela, data_vencimento, valor_previsto, status, forma_pagamento
            FROM db_fin.contas_receber
            WHERE venda_id = ?
            ORDER BY data_vencimento ASC
        """
        self.db.cursor.execute(query, (self.venda_id,))
        rows = self.db.cursor.fetchall()

        total_pendente = 0.0
        total_pago = 0.0

        for i, row in enumerate(rows):
            pid, num, data, valor, status, forma = row
            self.tabela.insertRow(i)

            # Formata Data
            try: dt_fmt = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
            except: dt_fmt = data

            self.tabela.setItem(i, 0, QTableWidgetItem(str(num)))
            self.tabela.setItem(i, 1, QTableWidgetItem(dt_fmt))
            self.tabela.setItem(i, 2, QTableWidgetItem(f"R$ {valor:,.2f}"))
            
            # Status Colorido
            item_st = QTableWidgetItem(status)
            if status == "Recebido":
                item_st.setForeground(Qt.GlobalColor.darkGreen)
                item_st.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                total_pago += valor
            else:
                item_st.setForeground(Qt.GlobalColor.darkRed)
                total_pendente += valor
            self.tabela.setItem(i, 3, item_st)

            # Botão de Ação (Se pendente, permite baixar. Se pago, mostra OK)
            if status != "Recebido":
                btn_baixa = QPushButton("✅ Receber")
                btn_baixa.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_baixa.setStyleSheet("background-color: #27ae60; color: white; border: none;")
                btn_baixa.clicked.connect(lambda ch, id_p=pid: self.baixar_parcela(id_p))
                self.tabela.setCellWidget(i, 4, btn_baixa)
            else:
                lbl_ok = QLabel("Pago")
                lbl_ok.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_ok.setStyleSheet("color: green; font-weight: bold;")
                self.tabela.setCellWidget(i, 4, lbl_ok)

        self.lbl_resumo.setText(f"Recebido: R$ {total_pago:,.2f} | Pendente: R$ {total_pendente:,.2f}")

    def baixar_parcela(self, parcela_id):
        """Abre o pop-up inteligente de baixa de parcela ao invés de baixar direto"""
        try:
            # Pega o valor da parcela no BD
            self.db.cursor.execute("SELECT valor_previsto FROM db_fin.contas_receber WHERE id = ?", (parcela_id,))
            resultado = self.db.cursor.fetchone()
            
            if resultado:
                valor_parcela = resultado[0]
                # Abre a janela que criamos
                dialog = DialogoReceberParcela(self.db, parcela_id, valor_parcela, self)
                if dialog.exec():
                    # Se o usuário confirmou e deu tudo certo, recarregamos a tabela
                    self.carregar_dados() # Ou o nome do seu método que atualiza a tabela da tela
                    
        except Exception as e:
            mostrar_mensagem(self, "erro", "Erro", f"Erro ao preparar recebimento: {e}")

class BaixaContaDialog(QDialog):

    def __init__(self, db_context, conta_id, tipo="Receber", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"💰 Baixa de {tipo}")
        self.setFixedWidth(480)
        self.db = db_context
        self.conta_id = conta_id
        self.tipo = tipo
        self.comprovante_path = ""
        
        # --- ESTILO UNIFORME ---
        self.setStyleSheet("""
            QDialog { background-color: #f0f2f5; }
            QLabel { color: #2c3e50; font-weight: bold; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { 
                padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px; 
                background-color: white; color: #2c3e50; min-height: 25px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border: 2px solid #00aff0; }
            QPushButton { border-radius: 4px; padding: 10px; font-weight: bold; border: none; }
        """)
        
        # --- BUSCAR DADOS DA CONTA ---
        tabela = "db_fin.contas_receber" if tipo == "Receber" else "db_fin.contas_pagar"
        col_val_banco = "valor_previsto" if tipo == "Receber" else "valor"
        
        try:
            self.db.cursor.execute(f"SELECT descricao, {col_val_banco}, data_vencimento FROM {tabela} WHERE id=?", (conta_id,))
            row = self.db.cursor.fetchone()
        except Exception as e:
            print(f"Erro ao buscar conta: {e}")
            row = None
        
        if not row:
            QMessageBox.critical(self, "Erro", "Conta não encontrada!")
            self.reject()
            return
            
        desc, valor_orig, vencto = row
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- CARD INFORMATIVO ---
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #d1d5db; padding: 15px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)
        
        l_desc = QLabel(desc)
        l_desc.setStyleSheet("font-size: 16px; font-weight: 800; color: #1e293b;")
        
        l_val = QLabel(f"💵 Valor Original: R$ {valor_orig:,.2f}")
        l_val.setStyleSheet("font-size: 13px; color: #7f8c8d;")
        
        str_venc = "Sem data"
        if vencto:
            try:
                str_venc = datetime.strptime(vencto, '%Y-%m-%d').strftime('%d/%m/%Y')
            except: pass
            
        l_venc = QLabel(f"📅 Vencimento: {str_venc}")
        l_venc.setStyleSheet("font-size: 13px; color: #e74c3c; font-weight: 600;")
        
        info_layout.addWidget(l_desc)
        info_layout.addWidget(l_val)
        info_layout.addWidget(l_venc)
        layout.addWidget(info_frame)
        
        # --- FORMULÁRIO ---
        form = QFormLayout()
        form.setSpacing(12)
        
        self.dt_baixa = QDateEdit(QDate.currentDate())
        self.dt_baixa.setCalendarPopup(True)
        self.dt_baixa.setDisplayFormat("dd/MM/yyyy")
        
        self.spin_val_final = QDoubleSpinBox()
        self.spin_val_final.setMaximum(9999999)
        self.spin_val_final.setValue(valor_orig)
        self.spin_val_final.setPrefix("R$ ")
        self.spin_val_final.setDecimals(2)
        
        # --- CARREGA CONTAS BANCÁRIAS REAIS DO BANCO DE DADOS ---
        self.cb_conta = QComboBox()
        contas_bancarias = self.db.obter_contas_bancarias(apenas_ativas=True)
        
        if contas_bancarias:
            for conta in contas_bancarias:
                conta_id_db, banco, agencia, numero_conta, tipo_conta, saldo_atual, ativa = conta
                display_text = f"🏦 {banco} - {tipo_conta} (Ag: {agencia} | Conta: {numero_conta})"
                self.cb_conta.addItem(display_text, conta_id_db)
        else:
            self.cb_conta.addItem("❌ Nenhuma conta cadastrada", None)
            self.cb_conta.setEnabled(False)
        
        form.addRow("Data da Baixa:", self.dt_baixa)
        form.addRow("Valor Recebido/Pago:", self.spin_val_final)
        form.addRow("💳 Conta Destino:", self.cb_conta)
        layout.addLayout(form)
        
        # --- ANEXO ---
        self.btn_anexo = QPushButton("📎 Anexar Comprovante")
        self.btn_anexo.setStyleSheet("background-color: #3498db; color: white;")
        self.btn_anexo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_anexo.clicked.connect(self.selecionar_anexo)
        layout.addWidget(self.btn_anexo)
        
        # --- BOTÕES AÇÃO ---
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("❌ Cancelar")
        btn_confirm = QPushButton("✅ CONFIRMAR BAIXA")
        
        btn_cancel.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_confirm.setStyleSheet("background-color: #27ae60; color: white;")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_cancel.clicked.connect(self.reject)
        btn_confirm.clicked.connect(self.confirmar)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def selecionar_anexo(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Selecionar Comprovante", "", "Arquivos (*.pdf *.jpg *.png *.jpeg)")
        if fname:
            self.comprovante_path = fname
            self.btn_anexo.setText(f"📎 {os.path.basename(fname)}")
            self.btn_anexo.setStyleSheet("background-color: #2ecc71; color: white;")

    def confirmar(self):
        val_final = self.spin_val_final.value()
        dt_baixa = self.dt_baixa.date().toString("yyyy-MM-dd")
        conta_id_selected = self.cb_conta.currentData()
        
        # Validação
        if conta_id_selected is None:
            QMessageBox.warning(self, "Atenção", "Selecione uma conta bancária válida!")
            return
        
        try:
            if self.tipo == "Receber":
                self.db.cursor.execute('''
                    UPDATE db_fin.contas_receber 
                    SET status=?, data_recebimento=?, valor_recebido=?, conta_destino=?, comprovante_path=?
                    WHERE id=?
                ''', ("Recebido", dt_baixa, val_final, conta_id_selected, self.comprovante_path, self.conta_id))
            else:
                self.db.cursor.execute('''
                    UPDATE db_fin.contas_pagar 
                    SET status=?, data_pagamento=?, valor=?, conta_destino=?
                    WHERE id=?
                ''', ("Pago", dt_baixa, val_final, conta_id_selected, self.conta_id))
                
            self.db.conn.commit()
            mostrar_mensagem(self, 'sucesso', "Sucesso", "Baixa realizada com sucesso!")
            self.accept()
            
        except Exception as e:
            mostrar_mensagem(self, 'erro', "Erro na Baixa", f"Não foi possível processar a baixa.\n\nDetalhes: {str(e)}")

class PedidosForm(QWidget):

    editar_pedido_signal = pyqtSignal(int)

    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.pagina_atual = 0
        self.itens_por_pagina = 50 # Carrega apenas 50 por vez
        
        # Estilo
        self.setStyleSheet("""
            QWidget { background-color: #f0f2f5; color: #2c3e50; font-family: 'Segoe UI'; }
            QTableWidget { background-color: white; border: 1px solid #bdc3c7; gridline-color: #ecf0f1; }
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 6px; border: none; }
            QPushButton { border-radius: 4px; padding: 6px; font-weight: bold; border: none; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- TOPO (Filtros e Paginação) ---
        top_layout = QHBoxLayout()
        lbl_titulo = QLabel("📑 Histórico de Pedidos")
        lbl_titulo.setStyleSheet("font-size: 20px; font-weight: 800; color: #2c3e50;")
        
        # Filtro de Texto
        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar por Cliente ou ID...")
        self.txt_busca.setFixedWidth(250)
        self.txt_busca.returnPressed.connect(self.resetar_e_buscar)

        btn_buscar = QPushButton("🔍")
        btn_buscar.setFixedWidth(40)
        btn_buscar.setStyleSheet("background-color: #3498db; color: white;")
        btn_buscar.clicked.connect(self.resetar_e_buscar)

        # Botões de Paginação
        self.btn_ant = QPushButton("⬅️ Anterior")
        self.btn_ant.setStyleSheet("background-color: #95a5a6; color: white;")
        self.btn_ant.clicked.connect(self.pagina_anterior)
        
        self.lbl_pag = QLabel("Página 1")
        
        self.btn_prox = QPushButton("Próxima ➡️")
        self.btn_prox.setStyleSheet("background-color: #95a5a6; color: white;")
        self.btn_prox.clicked.connect(self.proxima_pagina)

        btn_refresh = QPushButton("🔄 Atualizar")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("background-color: #2c3e50; color: white;")
        btn_refresh.clicked.connect(self.carregar_dados)
        
        top_layout.addWidget(lbl_titulo)
        top_layout.addStretch()
        top_layout.addWidget(self.txt_busca)
        top_layout.addWidget(btn_buscar)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.btn_ant)
        top_layout.addWidget(self.lbl_pag)
        top_layout.addWidget(self.btn_prox)
        top_layout.addSpacing(10)
        top_layout.addWidget(btn_refresh)
        layout.addLayout(top_layout)

        # --- TABELA ---
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(8)
        self.tabela.setHorizontalHeaderLabels(["ID", "Data", "Cliente", "Descrição", "Produtos", "Total (R$)", "Status Fin.", "Ações"])
        
        # Ajustes de Coluna
        self.tabela.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Produtos estica
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Cliente ajusta
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.tabela)
        
        self.carregar_dados()

    def showEvent(self, event):
        self.carregar_dados()
        super().showEvent(event)

    def resetar_e_buscar(self):
        self.pagina_atual = 0
        self.carregar_dados()

    def pagina_anterior(self):
        if self.pagina_atual > 0:
            self.pagina_atual -= 1
            self.carregar_dados()

    def proxima_pagina(self):
        self.pagina_atual += 1
        self.carregar_dados()

    def carregar_dados(self):
        self.tabela.setRowCount(0)
        offset = self.pagina_atual * self.itens_por_pagina
        termo = self.txt_busca.text().strip()
        
        # Filtro WHERE dinâmico
        where_clause = ""
        params = []
        if termo:
            # Tenta buscar por ID se for número, senão busca por nome
            if termo.isdigit():
                where_clause = "WHERE v.id = ?"
                params.append(termo)
            else:
                where_clause = "WHERE c.nome_razao LIKE ?"
                params.append(f"%{termo}%")

        # Query Otimizada com LIMIT e OFFSET
        query = f"""
            SELECT 
                v.id, 
                v.data_venda,
                COALESCE(c.nome_razao, 'Consumidor Final') as cliente,
                v.descricao_pedido,
                GROUP_CONCAT(p.nome, ' | ') as produtos,
                v.valor_liquido,
                (SELECT COUNT(*) FROM db_fin.contas_receber WHERE venda_id = v.id AND status != 'Recebido') as parcelas_pendentes
            FROM main.vendas v
            LEFT JOIN db_cli.entidades c ON v.cliente_id = c.id
            LEFT JOIN main.itens_venda iv ON v.id = iv.venda_id
            LEFT JOIN db_prod.produtos p ON iv.produto_id = p.id
            {where_clause}
            GROUP BY v.id
            ORDER BY v.id DESC
            LIMIT ? OFFSET ?
        """
        
        # Adiciona LIMIT e OFFSET aos parametros
        params.extend([self.itens_por_pagina, offset])
        
        try:
            self.db.cursor.execute(query, tuple(params))
            rows = self.db.cursor.fetchall()
            
            # Controle dos botões de paginação
            self.lbl_pag.setText(f"Página {self.pagina_atual + 1}")
            self.btn_ant.setEnabled(self.pagina_atual > 0)
            # Se vier menos itens que o limite, estamos na última página
            self.btn_prox.setEnabled(len(rows) == self.itens_por_pagina)
            
            for i, row in enumerate(rows):
                self.tabela.insertRow(i)
                
                vid, dt, cli, desc, prods, val, pendentes = row
                
                try: dt_fmt = datetime.strptime(dt, "%Y-%m-%d").strftime("%d/%m/%Y")
                except: dt_fmt = dt

                self.tabela.setItem(i, 0, QTableWidgetItem(str(vid)))
                self.tabela.setItem(i, 1, QTableWidgetItem(dt_fmt))
                self.tabela.setItem(i, 2, QTableWidgetItem(cli))
                self.tabela.setItem(i, 3, QTableWidgetItem(desc if desc else "-"))
                
                # Produtos (Limita tamanho do texto para não travar renderização)
                prod_txt = prods if prods else "Sem itens"
                if len(prod_txt) > 100: prod_txt = prod_txt[:100] + "..."
                item_prod = QTableWidgetItem(prod_txt)
                item_prod.setToolTip(prods if prods else "")
                self.tabela.setItem(i, 4, item_prod)
                
                self.tabela.setItem(i, 5, QTableWidgetItem(f"R$ {val:,.2f}"))
                
                # Status Financeiro
                if pendentes == 0:
                    st_text = "✅ PAGO"
                    st_color = Qt.GlobalColor.darkGreen
                else:
                    st_text = "⚠️ PENDENTE"
                    st_color = Qt.GlobalColor.darkRed 

                item_st = QTableWidgetItem(st_text)
                item_st.setForeground(st_color)
                item_st.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                self.tabela.setItem(i, 6, item_st)
                
                # --- BOTÕES DE AÇÃO ---
                widget_btn = QWidget()
                layout_btn = QHBoxLayout(widget_btn)
                layout_btn.setContentsMargins(2, 2, 2, 2)
                layout_btn.setSpacing(4)
                
                btn_parcelas = QPushButton("💲")
                btn_parcelas.setFixedSize(30, 30)
                btn_parcelas.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_parcelas.setToolTip("Financeiro")
                btn_parcelas.setStyleSheet("background-color: #3498db; color: white; border-radius: 4px;")
                btn_parcelas.clicked.connect(lambda ch, id_v=vid: self.abrir_detalhes(id_v))
                
                btn_edit = QPushButton("✏️")
                btn_edit.setFixedSize(30, 30)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setToolTip("Editar Pedido")
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius: 4px;")
                btn_edit.clicked.connect(lambda ch, id_v=vid: self.emitir_edicao(id_v))

                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(30, 30)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setToolTip("Excluir")
                btn_del.setStyleSheet("background-color: #c0392b; color: white; border-radius: 4px;")
                btn_del.clicked.connect(lambda ch, id_v=vid: self.acao_excluir(id_v))
                
                layout_btn.addWidget(btn_parcelas)
                layout_btn.addWidget(btn_edit)
                layout_btn.addWidget(btn_del)
                
                self.tabela.setCellWidget(i, 7, widget_btn)
                
        except Exception as e:
            mostrar_mensagem(self, 'erro', 'Erro BD', str(e))

    def emitir_edicao(self, venda_id):
        self.editar_pedido_signal.emit(venda_id)

    def abrir_detalhes(self, venda_id):
        dlg = DialogoDetalhesParcelas(self.db, venda_id, self)
        dlg.exec()
        self.carregar_dados() 
        
    def acao_excluir(self, venda_id):
        if mostrar_mensagem(self, 'confirma_exclusao', 'Excluir Venda', 
                            "Tem certeza? Isso excluirá o financeiro e devolverá o estoque."):
            try:
                self.db.cursor.execute("SELECT produto_id, quantidade FROM main.itens_venda WHERE venda_id = ?", (venda_id,))
                itens = self.db.cursor.fetchall()
                for pid, qtd in itens:
                    self.db.cursor.execute("UPDATE db_prod.produtos SET estoque_atual = estoque_atual + ? WHERE id=?", (qtd, pid))

                self.db.cursor.execute("DELETE FROM db_fin.contas_receber WHERE venda_id = ?", (venda_id,))
                self.db.cursor.execute("DELETE FROM main.itens_venda WHERE venda_id = ?", (venda_id,))
                self.db.cursor.execute("DELETE FROM main.vendas WHERE id = ?", (venda_id,))
                
                self.db.conn.commit()
                self.carregar_dados()
                
            except Exception as e:
                self.db.conn.rollback()
                mostrar_mensagem(self, 'erro', 'Erro', str(e))