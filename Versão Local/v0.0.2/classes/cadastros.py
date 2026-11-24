from .imports import *
from classes.funcoesAuxiliares import COLORS, CPFCNPJLineEdit, calcular_margem_lucro, exportar_excel_generico, formatar_cnpj, formatar_cpf, mostrar_mensagem, validar_cpf

class GerenciamentoEntidades(QWidget):
    def __init__(self, db_context, tipo_entidade="Cliente"):
        super().__init__()
        self.db = db_context
        self.tipo = tipo_entidade 
        self.id_em_edicao = None 
        
        # Layout Principal
        self.layout = QVBoxLayout(self)
        
        # Área de Rolagem
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
        self.cb_tipo_pessoa.addItems(["Pessoa Física", "Pessoa Jurídica"]) # Inverti para PF ser o padrão se quiser
        # Conecta a mudança do combo à função de esconder campos
        self.cb_tipo_pessoa.currentTextChanged.connect(self.atualizar_interface)
        
        # Doc (CPF/CNPJ)
        self.lbl_doc = QLabel("CPF:") # Guardamos o label para mudar o texto
        self.txt_doc = CPFCNPJLineEdit()  # ✨ Campo com validação visual automática
        self.txt_doc.setPlaceholderText("Digite CPF ou CNPJ")
        
        # Inscrição Estadual (Apenas PJ)
        self.lbl_ie = QLabel("Inscrição Estadual:")
        self.txt_ie = QLineEdit()
        self.txt_ie.setPlaceholderText("IE")

        # Nome / Razão
        self.lbl_nome = QLabel("Nome Completo:")
        self.txt_nome = QLineEdit()
        self.txt_nome.setPlaceholderText("Obrigatório")
        
        # Fantasia (Apenas PJ)
        self.lbl_fantasia = QLabel("Nome Fantasia:")
        self.txt_fantasia = QLineEdit()
        self.txt_fantasia.setPlaceholderText("Nome Fantasia")
        
        # Adiciona ao Form (Usando as variáveis de Label criadas acima)
        form_layout.addRow("Tipo:", self.cb_tipo_pessoa)
        form_layout.addRow(self.lbl_doc, self.txt_doc)
        form_layout.addRow(self.lbl_ie, self.txt_ie)
        form_layout.addRow(self.lbl_nome, self.txt_nome)
        form_layout.addRow(self.lbl_fantasia, self.txt_fantasia)
        
        # Grupo de Endereço
        lbl_end = QLabel("Endereço e Contato")
        lbl_end.setStyleSheet("font-weight: bold; margin-top: 10px; color: #2c3e50;")
        form_layout.addRow(lbl_end)

        hbox_cep = QHBoxLayout()
        self.txt_cep = QLineEdit(); self.txt_cep.setPlaceholderText("CEP")
        self.txt_endereco = QLineEdit(); self.txt_endereco.setPlaceholderText("Rua, Número")
        hbox_cep.addWidget(self.txt_cep)
        hbox_cep.addWidget(self.txt_endereco)
        form_layout.addRow("CEP / Rua:", hbox_cep)

        hbox_loc = QHBoxLayout()
        self.txt_bairro = QLineEdit(); self.txt_bairro.setPlaceholderText("Bairro")
        self.txt_cidade = QLineEdit(); self.txt_cidade.setPlaceholderText("Cidade")
        self.txt_uf = QLineEdit(); self.txt_uf.setPlaceholderText("UF"); self.txt_uf.setFixedWidth(50)
        
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


        # Botões de ação
        btn_actions = QHBoxLayout()
        btn_exportar = QPushButton("📥 Exportar Excel")
        btn_exportar.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 15px; font-weight: bold; border-radius: 5px;")
        btn_exportar.clicked.connect(self.exportar_para_excel)
        btn_actions.addWidget(btn_exportar)
        btn_actions.addStretch()
        layout_content.addLayout(btn_actions)
        
        # --- 2. TABELA DE LISTAGEM ---
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome/Razão", "CPF/CNPJ", "Cidade/UF", "Telefone", "Ações"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setMinimumHeight(300)
        self.tabela.setStyleSheet("QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; }")
        
        layout_content.addWidget(self.tabela)
        
        # Inicialização
        self.atualizar_interface() # Ajusta campos iniciais
        self.carregar_tabela()

    def atualizar_interface(self):
        """Esconde/Mostra campos dependendo se é PF ou PJ"""
        tipo = self.cb_tipo_pessoa.currentText()
        
        if tipo == "Pessoa Física":
            # Esconde campos de PJ
            self.lbl_fantasia.hide()
            self.txt_fantasia.hide()
            self.lbl_ie.hide()
            self.txt_ie.hide()
            
            # Ajusta Labels e Placeholders para PF
            self.lbl_nome.setText("Nome Completo:")
            self.lbl_doc.setText("CPF:")
            self.txt_doc.setPlaceholderText("Opcional para PF")
            
        else: # Pessoa Jurídica
            # Mostra campos de PJ
            self.lbl_fantasia.show()
            self.txt_fantasia.show()
            self.lbl_ie.show()
            self.txt_ie.show()
            
            # Ajusta Labels e Placeholders para PJ
            self.lbl_nome.setText("Razão Social:")
            self.lbl_doc.setText("CNPJ:")
            self.txt_doc.setPlaceholderText("Obrigatório")

    def salvar(self):
        # Coleta dados brutos
        nome = self.txt_nome.text().strip()
        doc = self.txt_doc.text().strip()
        tipo_pessoa = self.cb_tipo_pessoa.currentText()

        # --- VALIDAÇÃO ---
        # Regra 1: Nome é sempre obrigatório
        if not nome:
            mostrar_mensagem(self, 'aviso', 'Atenção', f"O campo {self.lbl_nome.text().replace(':','')} é obrigatório.")
            self.txt_nome.setFocus()
            return

        # Regra 2: Documento só é obrigatório para PJ (conforme seu pedido)
        if tipo_pessoa == "Pessoa Jurídica" and not doc:
            mostrar_mensagem(self, 'aviso', 'Atenção', "Para Pessoa Jurídica, o CNPJ é obrigatório.")
            self.txt_doc.setFocus()
            return
        
        # Limpa campos ocultos para não salvar lixo no banco
        fantasia = self.txt_fantasia.text().strip() if tipo_pessoa == "Pessoa Jurídica" else ""
        ie = self.txt_ie.text().strip() if tipo_pessoa == "Pessoa Jurídica" else ""

        # Coleta restante dos dados
        dados = (
            tipo_pessoa,
            self.tipo, # Categoria
            nome,
            fantasia,
            doc,
            ie,
            self.txt_endereco.text().strip(),
            self.txt_bairro.text().strip(),
            self.txt_cidade.text().strip(),
            self.txt_uf.text().strip(),
            self.txt_cep.text().strip(),
            self.txt_telefone.text().strip(),
            self.txt_email.text().strip(),
            datetime.now().strftime("%Y-%m-%d")
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
            mostrar_mensagem(self, 'erro', 'Erro Crítico', f"Erro ao salvar: {str(e)}")

    def carregar_tabela(self):
        self.tabela.setRowCount(0)
        query = f"SELECT id, nome_razao, cpf_cnpj, cidade, uf, telefone FROM db_cli.entidades WHERE categoria = '{self.tipo}' ORDER BY id DESC"
        
        self.tabela.setStyleSheet("""
            QTableWidget {
                color: black;            /* Cor do texto das células */
                background-color: white; /* Cor do fundo das células */
            }
            QHeaderView::section { 
                background-color: #f1f1f1; 
                color: black;            /* Cor do texto do cabeçalho */
                font-weight: bold; 
            }
        """)

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
        
        self.id_em_edicao = row[0]
        
        # Define o tipo primeiro para acionar o atualizar_interface()
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
        
        # Garante que a interface volta ao estado do combo atual
        self.atualizar_interface()


    def exportar_para_excel(self):
        """Exporta lista de entidades para Excel"""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Salvar Excel",
                f"{self.tipo.lower()}s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel (*.xlsx)"
            )
            if not filepath:
                return
            
            progress = QProgressDialog("Exportando...", None, 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setValue(20)
            
            query = f"""
                SELECT id, tipo_pessoa, nome_razao, cpf_cnpj, telefone, email, 
                       endereco, cidade, uf, data_registro
                FROM db_cli.entidades
                WHERE categoria = '{self.tipo}' OR categoria = 'Ambos'
                ORDER BY nome_razao
            """
            self.db.cursor.execute(query)
            dados = self.db.cursor.fetchall()
            
            progress.setValue(50)
            
            # Formata CPF/CNPJ
            dados_fmt = []
            for row in dados:
                r = list(row)
                if r[3]:
                    doc = str(r[3])
                    if len(doc) == 11:
                        r[3] = formatar_cpf(doc)
                    elif len(doc) == 14:
                        r[3] = formatar_cnpj(doc)
                dados_fmt.append(r)
            
            colunas = ["ID", "Tipo", "Nome", "CPF/CNPJ", "Telefone", "Email",
                      "Endereço", "Cidade", "UF", "Data Cadastro"]
            
            sucesso, msg = exportar_excel_generico(dados_fmt, colunas, 
                f"Relatório de {self.tipo}s", filepath)
            
            progress.setValue(100)
            progress.close()
            
            if sucesso:
                resp = QMessageBox.question(self, "Sucesso",
                    f"✅ Exportado com sucesso!\n\n{filepath}\n\nAbrir arquivo?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if resp == QMessageBox.StandardButton.Yes:
                    import os
                    os.startfile(filepath)
            else:
                QMessageBox.critical(self, "Erro", f"❌ Erro: {msg}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

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
        
        # Margem de Lucro Automática
        self.lbl_margem = QLabel("💰 Margem: 0.00%")
        self.lbl_margem.setStyleSheet("font-size: 18px; font-weight: bold; color: #27ae60; padding: 8px;")
        form_layout.addRow("", self.lbl_margem)
        
        # Conecta sinais para cálculo automático
        self.spin_custo.valueChanged.connect(self.calcular_margem_auto)
        self.spin_venda.valueChanged.connect(self.calcular_margem_auto)
        
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
        # Aumentado para 7 colunas para incluir o Excluir
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "SKU", "Produto", "Categoria", "Preço Venda", "Editar", "Excluir"])
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
                btn_edit = QPushButton("✏️")
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius: 4px; font-weight: bold; border: none; padding: 4px;")
                btn_edit.clicked.connect(lambda checked, id_p=pid: self.abrir_editor(id_p))
                self.table.setCellWidget(i, 5, btn_edit)

                # Botão Excluir
                btn_del = QPushButton("🗑️")
                btn_del.setStyleSheet("background-color: #c0392b; color: white; border-radius: 4px; font-weight: bold; border: none; padding: 4px;")
                btn_del.clicked.connect(lambda checked, id_p=pid: self.excluir_produto(id_p))
                self.table.setCellWidget(i, 6, btn_del)
                
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
            
            # Mensagem segura
            mostrar_mensagem(self, 'sucesso', 'Sucesso', 'Produto cadastrado com sucesso!')
            
        except Exception as e: 
            mostrar_mensagem(self, 'erro', 'Erro', str(e))

    def excluir_produto(self, id_produto):
        if mostrar_mensagem(self, 'confirma', 'Excluir Produto', "Tem certeza que deseja excluir? Isso pode afetar relatórios."):
            try:
                self.db.cursor.execute("DELETE FROM db_prod.produtos WHERE id=?", (id_produto,))
                self.db.conn.commit()
                self.carregar_tabela()
                # Importante: Atualiza a tela de vendas removendo o produto do combo
                self.produto_salvo_signal.emit()
            except Exception as e:
                mostrar_mensagem(self, 'erro', 'Erro', str(e))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.focusNextChild()
        else:
            super().keyPressEvent(event)


    def calcular_margem_auto(self):
        """Calcula margem de lucro em tempo real"""
        try:
            custo = self.spin_custo.value()
            venda = self.spin_venda.value()
            if venda > 0:
                margem = calcular_margem_lucro(venda, custo)
                if margem < 10:
                    emoji, cor = "⚠️", "#e74c3c"
                elif margem < 20:
                    emoji, cor = "⚡", "#f39c12"
                elif margem < 30:
                    emoji, cor = "💰", "#3498db"
                else:
                    emoji, cor = "🎯", "#27ae60"
                self.lbl_margem.setText(f"{emoji} Margem: {margem:.2f}%")
                self.lbl_margem.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {cor}; padding: 8px;")
            else:
                self.lbl_margem.setText("💰 Margem: 0.00%")
        except:
            pass

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
    def __init__(self, db, origem, item_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.origem = origem # 'pagar', 'receber'
        self.item_id = item_id
        self.setWindowTitle(f"Editar {origem.capitalize()}")
        self.setFixedWidth(400)
        
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { color: #2c3e50; font-weight: bold; }
            QLineEdit, QDateEdit, QDoubleSpinBox { 
                background-color: white; color: #2c3e50; border: 1px solid #bdc3c7; padding: 6px; border-radius: 4px; 
            }
            QPushButton { padding: 8px; border-radius: 4px; font-weight: bold; }
        """)

        # Configurações de campos baseadas na origem
        if self.origem == 'receber':
            self.table_name = "db_fin.contas_receber"
            self.col_valor = "valor_previsto"
        else:
            self.table_name = "db_fin.contas_pagar"
            self.col_valor = "valor"

        layout = QVBoxLayout(self)
        self.form = QFormLayout()

        # Carrega dados
        try:
            self.db.cursor.execute(f"SELECT descricao, {self.col_valor}, data_vencimento FROM {self.table_name} WHERE id=?", (item_id,))
            row = self.db.cursor.fetchone()
            
            if not row:
                mostrar_mensagem(self, 'erro', 'Erro', 'Registro não encontrado.')
                self.reject()
                return

            desc_atual, val_atual, data_atual = row
        except Exception as e:
            mostrar_mensagem(self, 'erro', 'Erro BD', str(e))
            self.reject()
            return

        # Inputs
        self.txt_desc = QLineEdit(desc_atual)
        self.spin_val = QDoubleSpinBox()
        self.spin_val.setMaximum(99999999)
        self.spin_val.setPrefix("R$ ")
        self.spin_val.setValue(float(val_atual) if val_atual else 0.0)
        
        self.dt_venc = QDateEdit()
        self.dt_venc.setCalendarPopup(True)
        self.dt_venc.setDisplayFormat("dd/MM/yyyy")
        
        try:
            if data_atual:
                # Tenta converter string YYYY-MM-DD para QDate
                d = datetime.strptime(data_atual, "%Y-%m-%d")
                self.dt_venc.setDate(d)
            else:
                self.dt_venc.setDate(QDate.currentDate())
        except:
            self.dt_venc.setDate(QDate.currentDate())

        self.form.addRow("Descrição:", self.txt_desc)
        self.form.addRow("Valor:", self.spin_val)
        self.form.addRow("Vencimento:", self.dt_venc)
        layout.addLayout(self.form)

        # --- BOTÕES (Excluir e Salvar) ---
        hbox_btn = QHBoxLayout()
        
        btn_excluir = QPushButton("🗑️ Excluir")
        btn_excluir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_excluir.setStyleSheet("background-color: #c0392b; color: white; border: none;")
        btn_excluir.clicked.connect(self.excluir)
        
        btn_save = QPushButton("💾 Salvar Alterações")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #27ae60; color: white; border: none;")
        btn_save.clicked.connect(self.salvar)
        
        hbox_btn.addWidget(btn_excluir)
        hbox_btn.addStretch()
        hbox_btn.addWidget(btn_save)
        
        layout.addLayout(hbox_btn)

    def salvar(self):
        novo_desc = self.txt_desc.text()
        novo_val = self.spin_val.value()
        nova_data = self.dt_venc.date().toString("yyyy-MM-dd")

        try:
            self.db.cursor.execute(f"""
                UPDATE {self.table_name} 
                SET descricao=?, {self.col_valor}=?, data_vencimento=? 
                WHERE id=?
            """, (novo_desc, novo_val, nova_data, self.item_id))
            self.db.conn.commit()
            mostrar_mensagem(self, 'sucesso', 'Sucesso', "Registro atualizado!")
            self.accept()
        except Exception as e:
            mostrar_mensagem(self, 'erro', 'Erro', f"Falha ao salvar: {e}")

    def excluir(self):
        if mostrar_mensagem(self, 'confirma', 'Excluir', "Tem certeza que deseja excluir este lançamento? Esta ação não pode ser desfeita."):
            try:
                self.db.cursor.execute(f"DELETE FROM {self.table_name} WHERE id=?", (self.item_id,))
                self.db.conn.commit()
                mostrar_mensagem(self, 'sucesso', 'Sucesso', "Registro excluído!")
                self.accept()
            except Exception as e:
                self.db.conn.rollback()
                mostrar_mensagem(self, 'erro', 'Erro', f"Falha ao excluir: {e}")

class GerenciamentoVendedores(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        self.id_em_edicao = None 
        
        # --- CRIAÇÃO AUTOMÁTICA DA TABELA ---
        self.criar_tabela_vendedores()

        # Layout Principal
        self.layout = QVBoxLayout(self)
        
        # Área de Rolagem
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        self.layout.addWidget(scroll)

        layout_content = QVBoxLayout(content)

        # --- 1. FORMULÁRIO ---
        self.frame_form = QFrame()
        self.frame_form.setStyleSheet("background-color: #f7f9f9; border-radius: 8px; border: 1px solid #bdc3c7;")
        form_layout = QFormLayout(self.frame_form)
        form_layout.setSpacing(10)
        
        # Título
        lbl_titulo = QLabel("👔 Cadastro de Vendedores")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        form_layout.addRow(lbl_titulo)

        # Nome (Obrigatório)
        self.lbl_nome = QLabel("Nome Completo:")
        self.txt_nome = QLineEdit()
        self.txt_nome.setPlaceholderText("Obrigatório")
        form_layout.addRow(self.lbl_nome, self.txt_nome)

        # CPF (Opcional)
        self.txt_cpf = QLineEdit()
        self.txt_cpf.setPlaceholderText("CPF (Apenas números)")
        form_layout.addRow("CPF:", self.txt_cpf)

        # Contato
        hbox_contato = QHBoxLayout()
        self.txt_telefone = QLineEdit(); self.txt_telefone.setPlaceholderText("Telefone / WhatsApp")
        self.txt_email = QLineEdit(); self.txt_email.setPlaceholderText("Email")
        hbox_contato.addWidget(self.txt_telefone)
        hbox_contato.addWidget(QLabel("Email:"))
        hbox_contato.addWidget(self.txt_email)
        form_layout.addRow("Contatos:", hbox_contato)

        # Endereço Simples
        self.txt_endereco = QLineEdit()
        self.txt_endereco.setPlaceholderText("Cidade - UF (Opcional)")
        form_layout.addRow("Localização:", self.txt_endereco)

        # --- COMISSÃO ---
        self.spin_comissao = QDoubleSpinBox()
        self.spin_comissao.setRange(0, 100)
        self.spin_comissao.setSuffix(" %")
        self.spin_comissao.setDecimals(2)
        self.spin_comissao.setSingleStep(0.5)
        self.spin_comissao.setValue(0.0) 
        self.spin_comissao.setStyleSheet("padding: 8px; background-color: white; color: black;")
        self.spin_comissao.setFixedWidth(120)
        
        lbl_comissao = QLabel("Comissão (%):")
        lbl_comissao.setStyleSheet("font-weight: bold; color: #27ae60;")
        
        form_layout.addRow(lbl_comissao, self.spin_comissao)

        # Botões
        hbox_btn = QHBoxLayout()
        self.btn_salvar = QPushButton("✅ Salvar Vendedor")
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

        # --- 2. TABELA DE LISTAGEM ---
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome", "Comissão", "Contato", "Ações"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setMinimumHeight(300)
        
        # --- CORREÇÃO DE COR DO TEXTO AQUI ---
        self.tabela.setStyleSheet("""
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 6px; }
            QTableWidget { 
                background-color: white; 
                alternate-background-color: #f9f9f9; 
                color: #2c3e50; /* Cor do texto PRETO/Cinza Escuro */
                selection-background-color: #3498db;
                selection-color: white;
            }
        """)
        self.tabela.setAlternatingRowColors(True)
        
        layout_content.addWidget(self.tabela)
        
        self.carregar_tabela()

    def criar_tabela_vendedores(self):
        try:
            self.db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendedores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT,
                    telefone TEXT,
                    email TEXT,
                    endereco TEXT,
                    comissao REAL DEFAULT 0.0,
                    data_registro TEXT
                )
            """)
            self.db.conn.commit()
        except Exception as e:
            print(f"Erro ao criar tabela vendedores: {e}")

    def salvar(self):
        nome = self.txt_nome.text().strip()
        cpf = self.txt_cpf.text().strip()
        
        # Validação 1: Nome obrigatório
        if not nome:
            QMessageBox.warning(self, 'Atenção', "O Nome do vendedor é obrigatório.")
            self.txt_nome.setFocus()
            return

        # Validação 2: CPF (Se preenchido)
        if cpf:
            # Remove caracteres não numéricos para validação, se necessário, 
            # mas geralmente a função validar_cpf espera a string como está ou limpa dentro dela.
            # Vamos assumir que a função lida com pontuação ou string pura.
            if not validar_cpf(cpf):
                QMessageBox.warning(self, 'CPF Inválido', "O CPF informado é inválido.\nVerifique os dígitos.")
                self.txt_cpf.setFocus()
                return

        dados = (
            nome,
            cpf,
            self.txt_telefone.text().strip(),
            self.txt_email.text().strip(),
            self.txt_endereco.text().strip(),
            self.spin_comissao.value(),
            datetime.now().strftime("%Y-%m-%d")
        )

        try:
            if self.id_em_edicao:
                # UPDATE
                self.db.cursor.execute("""
                    UPDATE vendedores SET 
                        nome=?, cpf=?, telefone=?, email=?, endereco=?, comissao=?, data_registro=?
                    WHERE id=?
                """, dados + (self.id_em_edicao,))
                msg = "Vendedor atualizado com sucesso!"
            else:
                # INSERT
                self.db.cursor.execute("""
                    INSERT INTO vendedores (nome, cpf, telefone, email, endereco, comissao, data_registro) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, dados)
                msg = "Vendedor cadastrado com sucesso!"
            
            self.db.conn.commit()
            QMessageBox.information(self, 'Sucesso', msg)
            self.limpar_form()
            self.carregar_tabela()
            
        except Exception as e:
            self.db.conn.rollback()
            QMessageBox.critical(self, 'Erro', f"Erro ao salvar: {str(e)}")

    def carregar_tabela(self):
        self.tabela.setRowCount(0)
        try:
            self.db.cursor.execute("SELECT id, nome, comissao, telefone, email FROM vendedores ORDER BY nome")
            rows = self.db.cursor.fetchall()
            
            for i, row in enumerate(rows):
                self.tabela.insertRow(i)
                vid, nome, comissao, tel, email = row
                
                self.tabela.setItem(i, 0, QTableWidgetItem(str(vid)))
                self.tabela.setItem(i, 1, QTableWidgetItem(nome))
                
                # Comissão em Negrito/Verde
                item_com = QTableWidgetItem(f"{comissao:.1f}%")
                item_com.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                item_com.setForeground(QColor("#27ae60"))
                item_com.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabela.setItem(i, 2, item_com)
                
                contato = f"{tel} | {email}" if email else tel
                self.tabela.setItem(i, 3, QTableWidgetItem(contato))
                
                # Botões de Ação
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(4, 2, 4, 2)
                layout.setSpacing(5)
                
                btn_edit = QPushButton("✏️")
                btn_edit.setFixedSize(28, 24)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border: none; border-radius: 3px;")
                btn_edit.clicked.connect(lambda ch, id_v=vid: self.carregar_para_edicao(id_v))
                
                btn_del = QPushButton("🗑️")
                btn_del.setFixedSize(28, 24)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet("background-color: #c0392b; color: white; border: none; border-radius: 3px;")
                btn_del.clicked.connect(lambda ch, id_v=vid: self.excluir(id_v))
                
                layout.addWidget(btn_edit)
                layout.addWidget(btn_del)
                layout.addStretch()
                self.tabela.setCellWidget(i, 4, widget)

        except Exception as e:
             print(f"Erro ao carregar vendedores: {e}")

    def carregar_para_edicao(self, id_vendedor):
        try:
            self.db.cursor.execute("SELECT * FROM vendedores WHERE id=?", (id_vendedor,))
            row = self.db.cursor.fetchone()
            if not row: return
            
            self.id_em_edicao = row[0]
            
            self.txt_nome.setText(row[1])
            self.txt_cpf.setText(row[2])
            self.txt_telefone.setText(row[3])
            self.txt_email.setText(row[4])
            self.txt_endereco.setText(row[5])
            self.spin_comissao.setValue(float(row[6]))
            
            self.btn_salvar.setText("💾 Salvar Alterações")
            self.btn_cancelar.show()
            self.txt_nome.setFocus()
            
        except Exception as e:
            print(f"Erro ao editar: {e}")

    def excluir(self, id_vendedor):
        reply = QMessageBox.question(self, 'Excluir', "Deseja realmente excluir este vendedor?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.cursor.execute("DELETE FROM vendedores WHERE id=?", (id_vendedor,))
                self.db.conn.commit()
                self.carregar_tabela()
                self.limpar_form()
            except Exception as e:
                QMessageBox.critical(self, 'Erro', str(e))

    def limpar_form(self):
        self.id_em_edicao = None
        self.txt_nome.clear()
        self.txt_cpf.clear()
        self.txt_telefone.clear()
        self.txt_email.clear()
        self.txt_endereco.clear()
        self.spin_comissao.setValue(0.0)
        
        self.btn_salvar.setText("✅ Salvar Vendedor")
        self.btn_cancelar.hide()