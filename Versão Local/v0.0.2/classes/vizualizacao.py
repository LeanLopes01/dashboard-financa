from classes.cadastros import EntryEditorDialog
from classes.funcoesAuxiliares import exportar_excel_generico, formatar_moeda_br, mostrar_mensagem
from .imports import *

class DashboardCard(QFrame):
    """Card visual para KPIs do dashboard"""
    def __init__(self, titulo, valor, icone="", cor="#3498db", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {cor};
                border-radius: 10px;
                padding: 15px;
                min-width: 200px;
                min-height: 120px;
            }}
            QFrame:hover {{
                background-color: #f8f9fa;
                border: 2px solid {cor};
            }}
        """)
        
        layout = QVBoxLayout()
        
        # Título
        lbl_titulo = QLabel(f"{icone} {titulo}")
        lbl_titulo.setStyleSheet(f"color: {cor}; font-weight: bold; font-size: 14px; border: none;")
        
        # Valor
        self.lbl_valor = QLabel(valor)
        self.lbl_valor.setStyleSheet(f"color: {cor}; font-size: 24px; font-weight: bold; border: none;")
        self.lbl_valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(lbl_titulo)
        layout.addWidget(self.lbl_valor)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def atualizar_valor(self, novo_valor):
        """Atualiza o valor exibido"""
        self.lbl_valor.setText(novo_valor)

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

class BackupAutomaticoThread(QThread):
    """Thread para backup automático em background"""
    progresso = pyqtSignal(int, str)
    concluido = pyqtSignal(bool, str)
    
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
    
    def run(self):
        """Executa backup em background"""
        try:
            self.progresso.emit(10, "Iniciando backup...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Usa pasta destino se definida, senão usa backups
            backup_dir = getattr(self, 'pasta_destino', "backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            self.progresso.emit(30, "Copiando banco de dados...")
            
            # Copia cada banco
            arquivos = [
                (self.db.db_vendas, f"{backup_dir}/vendas_{timestamp}.db"),
                (self.db.db_clientes, f"{backup_dir}/clientes_{timestamp}.db"),
                (self.db.db_produtos, f"{backup_dir}/produtos_{timestamp}.db"),
                (self.db.db_financeiro, f"{backup_dir}/financeiro_{timestamp}.db")
            ]
            
            for i, (origem, destino) in enumerate(arquivos):
                if os.path.exists(origem):
                    shutil.copy2(origem, destino)
                progresso_atual = 30 + (i + 1) * 15
                self.progresso.emit(progresso_atual, f"Copiando {os.path.basename(origem)}...")
            
            self.progresso.emit(90, "Compactando backup...")
            
            # Compacta em arquivo zip
            import zipfile
            zip_path = f"{backup_dir}/backup_completo_{timestamp}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for _, destino in arquivos:
                    if os.path.exists(destino):
                        zipf.write(destino, os.path.basename(destino))
                        os.remove(destino)  # Remove arquivos individuais
            
            self.progresso.emit(100, "Backup concluído!")
            self.concluido.emit(True, zip_path)
            
        except Exception as e:
            self.concluido.emit(False, str(e))

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
        self.tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Grupo
        self.tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Detalhe (Estica)
        self.tb.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed) # Valor (Fixo)
        self.tb.setColumnWidth(2, 180)
        self.tb.setStyleSheet("""
            QTableWidget { 
                background-color: white; 
                color: black; 
                font-size: 14px; 
                border: 1px solid #bdc3c7; 
            } 
            QHeaderView::section { 
                background-color: #34495e; 
                color: white; 
                font-weight: bold; 
                padding: 6px; 
            }
            /* AQUI ESTÁ A MUDANÇA PRINCIPAL */
            QTableWidget::item {
                padding-right: 20px; /* Espaço na direita para não colar na borda */
                padding-left: 5px;
            }
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


    def exportar_dre(self):
        """Exporta DRE para Excel"""
        if not hasattr(self, 'ultimo_dre') or not self.ultimo_dre:
            QMessageBox.warning(self, "Atenção", "Gere o DRE primeiro antes de exportar!")
            return
        
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Salvar DRE Excel",
                f"DRE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel (*.xlsx)"
            )
            if not filepath:
                return
            
            dre = self.ultimo_dre
            dados = [
                ["(+) Receita Bruta", formatar_moeda_br(dre['receita_bruta'])],
                ["(-) Impostos", formatar_moeda_br(dre['impostos'])],
                ["(=) Receita Líquida", formatar_moeda_br(dre['receita_liquida'])],
                ["", ""],
                ["(-) CPV", formatar_moeda_br(dre['cpv'])],
                ["(=) Lucro Bruto", formatar_moeda_br(dre['lucro_bruto'])],
                [f"    Margem Bruta", f"{dre['margem_bruta']:.2f}%"],
                ["", ""],
                ["(-) Despesas Operacionais", formatar_moeda_br(dre['despesas_operacionais'])],
                ["", ""],
                ["(=) LUCRO LÍQUIDO", formatar_moeda_br(dre['lucro_liquido'])],
                [f"    Margem Líquida", f"{dre['margem_liquida']:.2f}%"],
            ]
            
            colunas = ["Descrição", "Valor"]
            periodo = f"{self.dt_inicio.date().toString('dd/MM/yyyy')} a {self.dt_fim.date().toString('dd/MM/yyyy')}"
            
            sucesso, msg = exportar_excel_generico(dados, colunas, 
                f"DRE - {periodo}", filepath)
            
            if sucesso:
                QMessageBox.information(self, "Sucesso", f"✅ DRE exportado!\n\n{filepath}")
            else:
                QMessageBox.critical(self, "Erro", f"❌ {msg}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

class FluxoCaixaForm(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        # Removemos self.cache_nomes pois o SQL já resolve isso
        
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
        
        # Botões
        btn_filter = QPushButton("🔍 Filtrar")
        btn_filter.clicked.connect(self.load)
        btn_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_filter.setStyleSheet("""
            QPushButton { background-color: #2c3e50; color: white; font-weight: bold; padding: 8px 16px; border: none; border-radius: 5px; }
            QPushButton:hover { background-color: #3498db; }
        """)

        btn_refresh = QPushButton("🔄 Atualizar")
        btn_refresh.clicked.connect(self.load)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; font-weight: bold; padding: 8px 16px; border: none; border-radius: 5px; }
            QPushButton:hover { background-color: #3498db; }
        """)

        btn_delete_mass = QPushButton("🗑️ Excluir Selecionados")
        btn_delete_mass.clicked.connect(self.excluir_em_massa)
        btn_delete_mass.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete_mass.setStyleSheet("""
            QPushButton { background-color: #c0392b; color: white; font-weight: bold; padding: 8px 16px; border: none; border-radius: 5px; }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        
        hf.addWidget(QLabel("Período:", styleSheet="color: #2c3e50; font-weight: bold;"))
        hf.addWidget(self.cb_periodo)
        hf.addWidget(QLabel(" De:", styleSheet="color: #2c3e50; font-weight: bold;"))
        hf.addWidget(self.di)
        hf.addWidget(QLabel("Até:", styleSheet="color: #2c3e50; font-weight: bold;"))
        hf.addWidget(self.df)
        hf.addWidget(btn_filter)
        hf.addWidget(btn_refresh)
        hf.addWidget(btn_delete_mass) 
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
        self.tb.setColumnCount(8)
        self.tb.setHorizontalHeaderLabels(["", "Data", "Entidade", "Descrição", "Ref/Parc.", "Tipo", "Valor", "Editar"])
        
        self.tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Checkbox
        self.tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Data
        self.tb.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Entidade
        self.tb.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Descrição estica
        self.tb.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Ref
        
        self.tb.setStyleSheet("""
            QTableWidget { background-color: white; color: black; border: 1px solid #bdc3c7; } 
            QHeaderView::section { background-color: #34495e; color: white; font-weight: bold; padding: 8px; }
        """)
        main.addWidget(self.tb)
        
        self.atualizar_datas_pelo_combo()
        self.load()

    def showEvent(self, event):
        self.load()
        super().showEvent(event)

    def carregar_periodos(self):
        self.cb_periodo.clear()
        self.cb_periodo.addItem("Todo o Período", userData="ALL")
        try:
            self.db.cursor.execute("SELECT strftime('%Y', data_vencimento) as ano, strftime('%m', data_vencimento) as mes FROM db_fin.contas_receber UNION SELECT strftime('%Y', data_vencimento), strftime('%m', data_vencimento) FROM db_fin.contas_pagar ORDER BY 1 DESC, 2 DESC")
            # Ajustei a query acima para ser mais genérica caso get_meses falhe
            meses = self.db.cursor.fetchall()
            
            nomes_meses = {'01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril', '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
            for ano, mes in meses:
                if ano and mes:
                    self.cb_periodo.addItem(f"{nomes_meses.get(mes, mes)} {ano}", userData=(ano, mes))
        except: pass

    def atualizar_datas_pelo_combo(self):
        data = self.cb_periodo.currentData()
        if data == "ALL" or data is None:
            self.di.setDate(QDate(2000, 1, 1))
            self.df.setDate(QDate(2100, 12, 31))
        else:
            ano, mes = int(data[0]), int(data[1])
            try:
                import calendar
                ultimo_dia = calendar.monthrange(ano, mes)[1]
            except:
                ultimo_dia = 30
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

    def buscar_nome_entidade(self, id_ent):
        if not id_ent: return "-"
        if id_ent in self.cache_nomes: return self.cache_nomes[id_ent]
        
        try:
            self.db.cursor.execute("SELECT nome_razao FROM db_cli.entidades WHERE id = ?", (id_ent,))
            res = self.db.cursor.fetchone()
            nome = res[0] if res else "Desconhecido"
            self.cache_nomes[id_ent] = nome
            return nome
        except: return "-"

    def load(self):
        di = self.di.date().toString("yyyy-MM-dd")
        df_end = self.df.date().toString("yyyy-MM-dd")
        
        try:
            df = self.db.get_fluxo_caixa(di, df_end)
        except Exception as e:
            print(f"Erro ao carregar fluxo: {e}")
            self.tb.setRowCount(0)
            return
        
        self.tb.setRowCount(len(df))
        te, ts = 0.0, 0.0
        
        if df.empty: return

        for i, r in df.iterrows():
            raw_val = r['valor']
            v = float(raw_val) if raw_val is not None else 0.0
            
            # 0. CHECKBOX
            origem = r.get('origem', None)
            try: origem_id = int(r.get('origem_id')) if pd.notnull(r.get('origem_id')) else None
            except: origem_id = None

            chk_item = QTableWidgetItem()
            if origem in ['pagar', 'receber'] and origem_id:
                chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                chk_item.setCheckState(Qt.CheckState.Unchecked)
                chk_item.setData(Qt.ItemDataRole.UserRole, {'origem': origem, 'id': origem_id})
            else:
                chk_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tb.setItem(i, 0, chk_item)

            # 1. DATA
            dt_str = r['data']
            try: dt = datetime.strptime(dt_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            except: dt = str(dt_str)
            self.tb.setItem(i, 1, QTableWidgetItem(dt))

            # 2. ENTIDADE (AGORA PEGA DIRETO DO SQL)
            # Não precisamos mais de lógica complexa aqui
            ent_nome = str(r['entidade_nome']) if pd.notnull(r.get('entidade_nome')) else "-"
            self.tb.setItem(i, 2, QTableWidgetItem(ent_nome))

            # 3. DESCRIÇÃO
            self.tb.setItem(i, 3, QTableWidgetItem(str(r['descricao'])))

            # 4. REF/PARCELA
            ref_str = ""
            venda_id = r.get('venda_id')
            if pd.notnull(venda_id):
                try: ref_str += f"Venda #{int(float(venda_id))}"
                except: pass
            
            num_parc = r.get('num_parcela')
            if pd.notnull(num_parc) and str(num_parc) != "":
                ref_str += f" ({str(num_parc)})"
            
            if ref_str == "": ref_str = "-"
            self.tb.setItem(i, 4, QTableWidgetItem(ref_str))

            # 5. TIPO
            self.tb.setItem(i, 5, QTableWidgetItem(str(r['tipo'])))
            
            # 6. VALOR
            it = QTableWidgetItem(f"R$ {v:,.2f}")
            if v < 0: 
                it.setForeground(Qt.GlobalColor.red)
                ts += v
            else: 
                it.setForeground(Qt.GlobalColor.darkGreen)
                te += v
            self.tb.setItem(i, 6, it)

            # 7. EDITAR
            if origem in ['pagar', 'receber'] and origem_id:
                btn_edit = QPushButton("✏️")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setFixedSize(30, 30)
                btn_edit.setStyleSheet("background-color: #f39c12; color: white; border-radius:4px; font-weight:bold;")
                btn_edit.clicked.connect(lambda checked, o=origem, oid=origem_id: self.edit_entry(o, oid))
                self.tb.setCellWidget(i, 7, btn_edit)
            else:
                self.tb.setItem(i, 7, QTableWidgetItem("-"))
        
        self.k_ent.val.setText(f"R$ {te:,.2f}")
        self.k_sai.val.setText(f"R$ {ts:,.2f}")
        self.k_sal.val.setText(f"R$ {te+ts:,.2f}")

    def edit_entry(self, origem, origem_id):
        if not origem or not origem_id: return
        dlg = EntryEditorDialog(self.db, origem, origem_id, self)
        if dlg.exec(): 
            self.load()

    def excluir_em_massa(self):
        itens_para_excluir = []
        for i in range(self.tb.rowCount()):
            item = self.tb.item(i, 0)
            if item.checkState() == Qt.CheckState.Checked:
                dados = item.data(Qt.ItemDataRole.UserRole)
                if dados:
                    itens_para_excluir.append(dados)
        
        if not itens_para_excluir:
            mostrar_mensagem(self, 'aviso', 'Atenção', 'Selecione pelo menos um item para excluir.')
            return

        if not mostrar_mensagem(self, 'confirma_exclusao', 'Excluir Selecionados', f"Tem certeza que deseja excluir {len(itens_para_excluir)} itens selecionados?\nEssa ação não tem volta."):
            return

        try:
            for dados in itens_para_excluir:
                tabela = "db_fin.contas_receber" if dados['origem'] == 'receber' else "db_fin.contas_pagar"
                self.db.cursor.execute(f"DELETE FROM {tabela} WHERE id=?", (dados['id'],))
            
            self.db.conn.commit()
            mostrar_mensagem(self, 'sucesso', 'Sucesso', 'Itens excluídos com sucesso!')
            self.load()
            
        except Exception as e:
            self.db.conn.rollback()
            mostrar_mensagem(self, 'erro', 'Erro', f"Erro ao excluir: {str(e)}")

# ==================== TELA DE DASHBOARD COMPLETA ====================
class DashboardAvancado(QWidget):
    """Dashboard gerencial com KPIs e gráficos"""
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Título
        titulo = QLabel("📊 Dashboard Gerencial")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(titulo)
        
        # Grid de KPIs
        grid_kpis = QGridLayout()
        grid_kpis.setSpacing(15)
        
        # Calcula métricas
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
        hoje_str = hoje.strftime("%Y-%m-%d")
        
        faturamento = self.db.calcular_faturamento_periodo(inicio_mes, hoje_str)
        despesas = self.db.calcular_despesas_periodo(inicio_mes, hoje_str)
        lucro = faturamento - despesas
        inadimplencia = self.db.obter_inadimplencia_total()
        
        # Contas a receber hoje
        self.db.cursor.execute("""
            SELECT COALESCE(SUM(valor_pendente), 0)
            FROM db_fin.contas_receber
            WHERE data_vencimento <= ? AND status = 'Pendente'
        """, (hoje_str,))
        receber_hoje = self.db.cursor.fetchone()[0]
        
        # Produtos com estoque baixo
        produtos_baixos = self.db.obter_produtos_estoque_baixo()
        
        # Cria cards
        self.card_faturamento = DashboardCard("Faturamento Mês", formatar_moeda_br(faturamento), "💰", "#27ae60")
        self.card_despesas = DashboardCard("Despesas Mês", formatar_moeda_br(despesas), "💳", "#e74c3c")
        self.card_lucro = DashboardCard("Lucro Mês", formatar_moeda_br(lucro), "📈", "#3498db")
        self.card_inadimplencia = DashboardCard("Inadimplência", formatar_moeda_br(inadimplencia['valor']), "⚠️", "#f39c12")
        self.card_receber = DashboardCard("A Receber Hoje", formatar_moeda_br(receber_hoje), "💵", "#9b59b6")
        self.card_estoque = DashboardCard("Estoque Baixo", f"{len(produtos_baixos)} itens", "📦", "#e67e22")
        
        grid_kpis.addWidget(self.card_faturamento, 0, 0)
        grid_kpis.addWidget(self.card_despesas, 0, 1)
        grid_kpis.addWidget(self.card_lucro, 0, 2)
        grid_kpis.addWidget(self.card_inadimplencia, 1, 0)
        grid_kpis.addWidget(self.card_receber, 1, 1)
        grid_kpis.addWidget(self.card_estoque, 1, 2)
        
        layout.addLayout(grid_kpis)
        
        # Botão atualizar
        btn_atualizar = QPushButton("🔄 Atualizar Dashboard")
        btn_atualizar.setStyleSheet("background-color: #3498db; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_atualizar.clicked.connect(self.atualizar)
        layout.addWidget(btn_atualizar)
        
        # Gráfico (placeholder)
        info = QLabel("💡 Dica: Use os relatórios DRE e Fluxo de Caixa para análises detalhadas")
        info.setStyleSheet("background-color: #ecf0f1; padding: 15px; border-radius: 5px; color: #2c3e50;")
        layout.addWidget(info)
        
        layout.addStretch()
    
    def atualizar(self):
        """Atualiza os KPIs"""
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
        hoje_str = hoje.strftime("%Y-%m-%d")
        
        faturamento = self.db.calcular_faturamento_periodo(inicio_mes, hoje_str)
        despesas = self.db.calcular_despesas_periodo(inicio_mes, hoje_str)
        lucro = faturamento - despesas
        inadimplencia = self.db.obter_inadimplencia_total()
        
        self.db.cursor.execute("""
            SELECT COALESCE(SUM(valor_pendente), 0)
            FROM db_fin.contas_receber
            WHERE data_vencimento <= ? AND status = 'Pendente'
        """, (hoje_str,))
        receber_hoje = self.db.cursor.fetchone()[0]
        
        produtos_baixos = self.db.obter_produtos_estoque_baixo()
        
        self.card_faturamento.atualizar_valor(formatar_moeda_br(faturamento))
        self.card_despesas.atualizar_valor(formatar_moeda_br(despesas))
        self.card_lucro.atualizar_valor(formatar_moeda_br(lucro))
        self.card_inadimplencia.atualizar_valor(formatar_moeda_br(inadimplencia['valor']))
        self.card_receber.atualizar_valor(formatar_moeda_br(receber_hoje))
        self.card_estoque.atualizar_valor(f"{len(produtos_baixos)} itens")
        
        QMessageBox.information(self, "Atualizado", "✅ Dashboard atualizado com sucesso!")

# ==================== TELA DE COMISSÕES ====================
class GestaoComissoes(QWidget):
    """Tela para gerenciar comissões de vendedores"""
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel("💼 Gestão de Comissões")
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(titulo)
        
        # Filtros
        filtros_layout = QHBoxLayout()
        
        filtros_layout.addWidget(QLabel("Vendedor:"))
        self.cb_vendedor = QComboBox()
        self.cb_vendedor.addItem("Todos")
        # O estilo do ComboBox para ficar legível
        self.cb_vendedor.setStyleSheet("color: black; background-color: white; padding: 5px;")
        filtros_layout.addWidget(self.cb_vendedor)
        
        filtros_layout.addWidget(QLabel("Status:"))
        self.cb_status = QComboBox()
        self.cb_status.addItems(["Todos", "Pendente", "Pago"])
        self.cb_status.setStyleSheet("color: black; background-color: white; padding: 5px;")
        filtros_layout.addWidget(self.cb_status)
        
        btn_filtrar = QPushButton("🔍 Filtrar")
        btn_filtrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_filtrar.setStyleSheet("background-color: #3498db; color: white; padding: 8px; border-radius: 5px; font-weight: bold;")
        btn_filtrar.clicked.connect(self.carregar_comissoes)
        filtros_layout.addWidget(btn_filtrar)
        
        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)
        
        # Tabela
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(7)
        self.tabela.setHorizontalHeaderLabels([
            "ID", "Vendedor", "Data Venda", "Valor Venda", 
            "% Comissão", "Valor Comissão", "Status"
        ])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # --- CORREÇÃO DE CORES DA TABELA ---
        self.tabela.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #2c3e50;  /* Texto Escuro */
                gridline-color: #ecf0f1;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        layout.addWidget(self.tabela)
        
        # Resumo
        self.lbl_resumo = QLabel()
        self.lbl_resumo.setStyleSheet("background-color: #ecf0f1; color: #2c3e50; padding: 15px; border-radius: 5px; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_resumo)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        btn_pagar = QPushButton("💰 Pagar Selecionadas")
        btn_pagar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pagar.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_pagar.clicked.connect(self.pagar_selecionadas)
        btn_layout.addWidget(btn_pagar)
        
        btn_exportar = QPushButton("📥 Exportar")
        btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exportar.setStyleSheet("background-color: #3498db; color: white; padding: 10px; border-radius: 5px;")
        btn_exportar.clicked.connect(self.exportar)
        btn_layout.addWidget(btn_exportar)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Inicialização inicial
        self.carregar_vendedores()
        self.carregar_comissoes()

    def showEvent(self, event):
        """
        MÁGICA: Este método é chamado automaticamente pelo PyQt 
        sempre que esta aba/janela se torna visível.
        """
        self.carregar_vendedores() # Atualiza o Combo se cadastrou vendedor novo
        self.carregar_comissoes()  # Atualiza a tabela se fez venda nova
        super().showEvent(event)
    
    def carregar_vendedores(self):
        """Carrega lista de vendedores mantendo a seleção atual se possível"""
        selecao_atual = self.cb_vendedor.currentText()
        
        self.cb_vendedor.blockSignals(True) # Evita recarregar a tabela enquanto limpa
        self.cb_vendedor.clear()
        self.cb_vendedor.addItem("Todos")
        
        try:
            # Pega da tabela VENDEDORES (não de vendas, para pegar até quem não vendeu nada ainda)
            lista = self.db.get_lista_vendedores() 
            self.cb_vendedor.addItems(lista)
        except:
            pass
        
        # Tenta restaurar a seleção
        index = self.cb_vendedor.findText(selecao_atual)
        if index >= 0:
            self.cb_vendedor.setCurrentIndex(index)
        
        self.cb_vendedor.blockSignals(False)
    
    def carregar_comissoes(self):
        """Carrega comissões na tabela"""
        try:
            vendedor = self.cb_vendedor.currentText()
            status = self.cb_status.currentText()
            
            query = "SELECT * FROM db_fin.comissoes WHERE 1=1"
            params = []
            
            if vendedor != "Todos":
                query += " AND vendedor = ?"
                params.append(vendedor)
            
            if status != "Todos":
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY data_venda DESC"
            
            self.db.cursor.execute(query, params)
            dados = self.db.cursor.fetchall()
            
            self.tabela.setRowCount(len(dados))
            
            total_pendente = 0
            total_pago = 0
            
            for i, row in enumerate(dados):
                # row structure: 0:id, 1:venda_id, 2:vendedor, 3:valor_venda, 4:%, 5:valor_comissao, 6:data, 7:data_pag, 8:status, ...
                
                # ID
                self.tabela.setItem(i, 0, QTableWidgetItem(str(row[0])))
                
                # Vendedor
                self.tabela.setItem(i, 1, QTableWidgetItem(row[2]))
                
                # Data (Formatar para BR)
                try:
                    dt = datetime.strptime(row[6], "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    dt = row[6]
                self.tabela.setItem(i, 2, QTableWidgetItem(dt))
                
                # Valor Venda
                self.tabela.setItem(i, 3, QTableWidgetItem(formatar_moeda_br(row[3])))
                
                # % Comissão
                self.tabela.setItem(i, 4, QTableWidgetItem(f"{row[4]:.1f}%"))
                
                # Valor Comissão
                val_comissao = row[5]
                self.tabela.setItem(i, 5, QTableWidgetItem(formatar_moeda_br(val_comissao)))
                
                # Status com cor
                status_txt = row[8]
                status_item = QTableWidgetItem(status_txt)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                
                if status_txt == "Pendente":
                    status_item.setBackground(QColor("#f39c12")) # Laranja
                    total_pendente += val_comissao
                else:
                    status_item.setBackground(QColor("#27ae60")) # Verde
                    total_pago += val_comissao
                
                status_item.setForeground(QColor("white"))
                self.tabela.setItem(i, 6, status_item)
            
            # Atualiza resumo
            self.lbl_resumo.setText(
                f"💰 A Pagar: {formatar_moeda_br(total_pendente)}   |   "
                f"✅ Já Pago: {formatar_moeda_br(total_pago)}   |   "
                f"📊 Total: {formatar_moeda_br(total_pendente + total_pago)}"
            )
            
        except Exception as e:
            # Evita spam de erro na inicialização se a tabela não existir ainda
            print(f"Erro ao carregar comissões: {e}")
    
    def pagar_selecionadas(self):
        """Marca comissões selecionadas como pagas"""
        try:
            # Pega as linhas únicas selecionadas
            linhas = set(item.row() for item in self.tabela.selectedItems())
            
            if not linhas:
                QMessageBox.warning(self, "Atenção", "Selecione pelo menos uma comissão na tabela!")
                return
            
            # Verifica se alguma já está paga
            for linha in linhas:
                status = self.tabela.item(linha, 6).text()
                if status == "Pago":
                    QMessageBox.warning(self, "Aviso", "Algumas comissões selecionadas já estão pagas.")
                    return

            resp = QMessageBox.question(self, "Confirmar Pagamento",
                f"Confirma o pagamento de {len(linhas)} comissão(ões)?\nIsso mudará o status para 'Pago'.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if resp == QMessageBox.StandardButton.Yes:
                for linha in linhas:
                    comissao_id = int(self.tabela.item(linha, 0).text())
                    self.db.pagar_comissao(comissao_id)
                
                QMessageBox.information(self, "Sucesso", f"✅ {len(linhas)} comissão(ões) atualizada(s)!")
                self.carregar_comissoes()
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
    
    def exportar(self):
        """Exporta comissões para Excel"""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Salvar Excel",
                f"comissoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel (*.xlsx)"
            )
            if not filepath:
                return
            
            # Busca dados
            vendedor = self.cb_vendedor.currentText()
            status = self.cb_status.currentText()
            
            query = "SELECT vendedor, data_venda, valor_venda, percentual_comissao, valor_comissao, status FROM db_fin.comissoes WHERE 1=1"
            params = []
            
            if vendedor != "Todos":
                query += " AND vendedor = ?"
                params.append(vendedor)
            
            if status != "Todos":
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY data_venda DESC"
            
            self.db.cursor.execute(query, params)
            dados = self.db.cursor.fetchall()
            
            # Formata dados
            dados_fmt = []
            for row in dados:
                dados_fmt.append([
                    row[0],  # Vendedor
                    row[1],  # Data
                    formatar_moeda_br(row[2]),  # Valor venda
                    f"{row[3]:.1f}%",  # Percentual
                    formatar_moeda_br(row[4]),  # Valor comissão
                    row[5]  # Status
                ])
            
            colunas = ["Vendedor", "Data Venda", "Valor Venda", "% Comissão", "Valor Comissão", "Status"]
            
            sucesso, msg = exportar_excel_generico(dados_fmt, colunas, "Relatório de Comissões", filepath)
            
            if sucesso:
                QMessageBox.information(self, "Sucesso", f"✅ Exportado!\n\n{filepath}")
            else:
                QMessageBox.critical(self, "Erro", msg)
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
