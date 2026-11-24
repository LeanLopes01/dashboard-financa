from classes.funcoesAuxiliares import COLORS
from classes.cadastros import *
from classes.contas_bancos import *
from classes.funcoesAuxiliares import *
from classes.imports import *
from classes.pedidos import *
from classes.vizualizacao import *

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
            status TEXT, 
            nota_fiscal TEXT,
            forma_pagamento_prevista TEXT,
            descricao_pedido TEXT, -- <--- CAMPO NOVO
            obs TEXT
        )''')

        # 3.1 Itens da Venda (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER, -- <--- MUDADO DE REAL PARA INTEGER
            preco_unitario REAL,
            subtotal REAL,
            detalhes TEXT,      -- <--- NOVO
            variacao TEXT,      -- <--- NOVO
            preco_custo REAL,   -- <--- NOVO
            ipi REAL,           -- <--- NOVO
            icms REAL,          -- <--- NOVO
            anexo_path TEXT,    -- <--- NOVO
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
        
        # 6. Comissões de Vendedores (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.comissoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            vendedor TEXT NOT NULL,
            valor_venda REAL NOT NULL,
            percentual_comissao REAL NOT NULL,
            valor_comissao REAL NOT NULL,
            data_venda DATE NOT NULL,
            data_pagamento DATE,
            status TEXT DEFAULT 'Pendente',
            observacoes TEXT,
            FOREIGN KEY(venda_id) REFERENCES vendas(id)
        )''')
        
        # 7. Movimentações de Estoque (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_prod.movimentacoes_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            tipo TEXT CHECK(tipo IN ('Entrada', 'Saída', 'Ajuste')),
            quantidade REAL NOT NULL,
            custo_unitario REAL,
            data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            motivo TEXT,
            usuario TEXT,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )''')
        
        # 8. Configurações do Sistema (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            descricao TEXT,
            tipo TEXT DEFAULT 'texto'
        )''')
        
        # 9. Log de Backups (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.log_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_backup TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            arquivo TEXT,
            tamanho_bytes INTEGER,
            status TEXT,
            mensagem TEXT
        )''')

        # 10. Vendedores (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.vendedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            comissao REAL DEFAULT 0.0,
            data_registro DATE
        )''')

        # Adiciona campos extras em tabelas existentes se não existirem
        try:
            # Margem de lucro em produtos
            self.cursor.execute("ALTER TABLE db_prod.produtos ADD COLUMN margem_lucro REAL DEFAULT 0")
        except:
            pass  # Coluna já existe
        
        try:
            # Estoque mínimo em produtos
            self.cursor.execute("ALTER TABLE db_prod.produtos ADD COLUMN estoque_minimo REAL DEFAULT 0")
        except:
            pass
        
        try:
            # Valor pendente em contas a receber
            self.cursor.execute("ALTER TABLE db_fin.contas_receber ADD COLUMN valor_pendente REAL")
        except:
            pass
        
        try:
            # Dias de atraso em contas a receber
            self.cursor.execute("ALTER TABLE db_fin.contas_receber ADD COLUMN dias_atraso INTEGER DEFAULT 0")
        except:
            pass
        
        # Insere configurações padrão
        configuracoes_padrao = [
            ('empresa_nome', 'Minha Empresa', 'Nome da empresa'),
            ('empresa_cnpj', '', 'CNPJ da empresa'),
            ('pix_chave', '', 'Chave PIX para recebimentos'),
            ('banco_codigo', '', 'Código do banco para boletos'),
            ('banco_agencia', '', 'Agência bancária'),
            ('banco_conta', '', 'Conta corrente'),
            ('backup_automatico', '1', 'Ativar backup automático (0=não, 1=sim)'),
            ('comissao_padrao', '5', 'Percentual padrão de comissão'),

            ('regime_tributario', 'simples', 'Regime tributário (simples, lucro_presumido, lucro_real)'),
        ]
        
        for chave, valor, descricao in configuracoes_padrao:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO main.configuracoes (chave, valor, descricao) VALUES (?, ?, ?)",
                    (chave, valor, descricao)
                )
            except:
                pass


        # 11. Contas Bancárias (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_bancarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            banco TEXT NOT NULL,
            agencia TEXT NOT NULL,
            numero_conta TEXT NOT NULL,
            tipo_conta TEXT CHECK(tipo_conta IN ('Corrente', 'Poupança', 'Caixa Interno', 'Maquininha')),
            saldo_inicial REAL DEFAULT 0,
            saldo_atual REAL DEFAULT 0,
            ativa INTEGER DEFAULT 1,
            taxa_debito REAL DEFAULT 1.99,
            taxa_credito_vista REAL DEFAULT 2.99,
            taxa_credito_parcelado REAL DEFAULT 3.99,
            observacoes TEXT,
            data_cadastro DATE DEFAULT CURRENT_DATE
        )''')
        
        # 12. Movimentações Bancárias (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.movimentacoes_bancarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_id INTEGER NOT NULL,
            tipo_movimentacao TEXT CHECK(tipo_movimentacao IN ('Entrada', 'Saída', 'Transferência')),
            data_movimentacao DATE NOT NULL,
            valor_bruto REAL NOT NULL,
            taxa REAL DEFAULT 0,
            valor_liquido REAL NOT NULL,
            forma_pagamento TEXT,
            origem TEXT,
            origem_id INTEGER,
            descricao TEXT,
            comprovante_path TEXT,
            conciliado INTEGER DEFAULT 0,
            data_conciliacao DATE,
            FOREIGN KEY(conta_id) REFERENCES contas_bancarias(id)
        )''')
        
        # 13. Taxas de Cartão (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.taxas_cartao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_id INTEGER NOT NULL,
            bandeira TEXT,
            tipo_transacao TEXT CHECK(tipo_transacao IN ('Débito', 'Crédito Vista', 'Crédito Parcelado')),
            taxa_percentual REAL NOT NULL,
            prazo_recebimento INTEGER,
            ativa INTEGER DEFAULT 1,
            FOREIGN KEY(conta_id) REFERENCES contas_bancarias(id)
        )''')

        # 13. Bancos (NOVO)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.bancos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_banco TEXT NOT NULL,       -- Ex: 237 (Bradesco)
            nome_banco TEXT NOT NULL,         -- Ex: Banco Bradesco
            agencia TEXT,                     -- Ex: 0001
            conta TEXT,                       -- Ex: 12345-6
            tipo_conta TEXT,                  -- Corrente, Poupança, Caixa, Digital
            saldo_inicial REAL DEFAULT 0,     -- Saldo ao criar
            saldo_atual REAL DEFAULT 0,       -- Atualizado automaticamente
            ativo INTEGER DEFAULT 1,          -- 1=Ativo, 0=Inativo
            observacoes TEXT,
            data_abertura DATE
        )''')
        
        # 14. Taxas maquininha
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.taxas_maquininha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operadora TEXT NOT NULL,              -- Rede, Stone, PagSeguro, Cielo, GetNet
            tipo_cartao TEXT,                     -- 'Débito' ou 'Crédito'
            parcelas INTEGER DEFAULT 1,           -- 1 a 12
            taxa_percentual REAL NOT NULL,        -- Ex: 1.50, 2.99, 3.80
            prazo_recebimento INTEGER DEFAULT 1,  -- Dias até receber
            ativo INTEGER DEFAULT 1               -- 1=Ativa, 0=Inativa
        )''')

        # Insere contas padrão se não existirem
        try:
            self.cursor.execute("SELECT COUNT(*) FROM db_fin.contas_bancarias")
            if self.cursor.fetchone()[0] == 0:
                contas_padrao = [
                    ('Caixa Interno', '0000', '00001', 'Caixa Interno', 0),
                    ('Banco Itaú', '0000', '00000-0', 'Corrente', 0),
                    ('Maquininha Stone', '0000', 'STONE', 'Maquininha', 0)
                ]
                for banco, agencia, conta, tipo, saldo in contas_padrao:
                    self.cursor.execute("""
                        INSERT INTO db_fin.contas_bancarias 
                        (banco, agencia, numero_conta, tipo_conta, saldo_inicial, saldo_atual)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (banco, agencia, conta, tipo, saldo, saldo))
        except:
            pass
        
        for chave, valor, descricao in configuracoes_padrao:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO main.configuracoes (chave, valor, descricao) VALUES (?, ?, ?)",
                    (chave, valor, descricao)
                )
            except:
                pass

        self.conn.commit()
    
    def get_sales_chart_data(self):
        query = "SELECT strftime('%Y-%m', data_venda) as mes, SUM(valor_liquido) FROM main.vendas WHERE status = 'Concluido' GROUP BY mes ORDER BY mes"
        return pd.read_sql_query(query, self.conn)
    
    def get_fluxo_caixa(self, data_inicio, data_fim):
        # Mudei para pegar o NOME direto no SQL usando LEFT JOIN
        query = f"""
            SELECT 
                cr.id, 
                cr.data_vencimento as data, 
                cr.descricao, 
                cr.valor_previsto as valor, 
                'receber' as origem, 
                cr.id as origem_id,
                'Receita' as tipo,
                COALESCE(cli.nome_razao, 'Consumidor Final') as entidade_nome, -- <--- PEGA O NOME AQUI
                cr.venda_id,
                cr.num_parcela
            FROM db_fin.contas_receber cr
            LEFT JOIN db_cli.entidades cli ON cr.cliente_id = cli.id
            WHERE cr.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            
            UNION ALL
            
            SELECT 
                cp.id, 
                cp.data_vencimento as data, 
                cp.descricao, 
                cp.valor * -1 as valor, 
                'pagar' as origem, 
                cp.id as origem_id,
                'Despesa' as tipo,
                'Fornecedor / Despesa' as entidade_nome, -- Texto padrão para pagar (ou faça join com fornecedores se tiver)
                NULL as venda_id,
                NULL as num_parcela
            FROM db_fin.contas_pagar cp
            WHERE cp.data_vencimento BETWEEN '{data_inicio}' AND '{data_fim}'
            
            ORDER BY data ASC
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except Exception as e:
            print(f"Erro fluxo SQL: {e}")
            return pd.DataFrame()
    
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


    def obter_configuracao(self, chave, padrao=""):
        """Obtém valor de configuração"""
        try:
            self.cursor.execute("SELECT valor FROM main.configuracoes WHERE chave = ?", (chave,))
            result = self.cursor.fetchone()
            return result[0] if result else padrao
        except:
            return padrao
    
    def salvar_configuracao(self, chave, valor):
        """Salva configuração"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO main.configuracoes (chave, valor)
                VALUES (?, ?)
            """, (chave, valor))
            self.conn.commit()
            return True
        except:
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

    def get_lista_vendedores(self):
        """Retorna lista de nomes de vendedores para ComboBox"""
        try:
            self.cursor.execute("SELECT nome FROM main.vendedores ORDER BY nome")
            # Retorna uma lista simples de strings: ['João', 'Maria', ...]
            return [row[0] for row in self.cursor.fetchall()]
        except:
            return []

    def get_dados_vendedor(self, nome_vendedor):
        """Retorna dados do vendedor pelo nome (usado na venda para pegar comissão)"""
        try:
            self.cursor.execute("SELECT id, comissao FROM main.vendedores WHERE nome = ?", (nome_vendedor,))
            return self.cursor.fetchone() # Retorna (id, comissao)
        except:
            return None

    def salvar_vendedor(self, dados, id_editar=None):
        """
        Salva ou atualiza um vendedor.
        dados = (nome, cpf, telefone, email, endereco, comissao, data)
        """
        try:
            if id_editar:
                self.cursor.execute("""
                    UPDATE main.vendedores SET 
                        nome=?, cpf=?, telefone=?, email=?, endereco=?, comissao=?, data_registro=?
                    WHERE id=?
                """, dados + (id_editar,))
            else:
                self.cursor.execute("""
                    INSERT INTO main.vendedores (nome, cpf, telefone, email, endereco, comissao, data_registro) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, dados)
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao salvar vendedor: {e}")
            return False

    def excluir_vendedor(self, id_vendedor):
        """Exclui um vendedor"""
        try:
            self.cursor.execute("DELETE FROM main.vendedores WHERE id=?", (id_vendedor,))
            self.conn.commit()
            return True
        except:
            return False
        
# --- 2. COMPONENTES DE UI -


    
    # ==================== NOVOS MÉTODOS PARA FUNCIONALIDADES AVANÇADAS ====================
    
    def calcular_faturamento_periodo(self, data_inicio, data_fim):
        """Calcula faturamento do período"""
        try:
            self.cursor.execute("""
                SELECT COALESCE(SUM(valor_liquido), 0)
                FROM main.vendas
                WHERE data_venda BETWEEN ? AND ?
                AND status NOT IN ('Cancelado', 'Orçamento')
            """, (data_inicio, data_fim))
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def calcular_despesas_periodo(self, data_inicio, data_fim):
        """Calcula despesas do período"""
        try:
            self.cursor.execute("""
                SELECT COALESCE(SUM(valor), 0)
                FROM db_fin.contas_pagar
                WHERE data_vencimento BETWEEN ? AND ?
                AND status != 'Cancelado'
            """, (data_inicio, data_fim))
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def obter_inadimplencia_total(self):
        """Retorna valor total de inadimplência"""
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("""
                SELECT COALESCE(SUM(valor_pendente), 0), COUNT(*)
                FROM db_fin.contas_receber
                WHERE data_vencimento < ? AND status = 'Pendente'
            """, (hoje,))
            valor, qtd = self.cursor.fetchone()
            return {"valor": valor, "quantidade": qtd}
        except:
            return {"valor": 0, "quantidade": 0}
    
    def obter_produtos_estoque_baixo(self):
        """Retorna produtos com estoque abaixo do mínimo"""
        try:
            self.cursor.execute("""
                SELECT id, nome, sku, estoque_atual, unidade_medida
                FROM db_prod.produtos
                WHERE estoque_atual < 10
                ORDER BY estoque_atual ASC
                LIMIT 20
            """)
            return self.cursor.fetchall()
        except:
            return []
    
    def salvar_comissao(self, venda_id, vendedor, valor_venda, percentual):
        """Registra comissão de venda"""
        try:
            valor_comissao = valor_venda * (percentual / 100)
            data_venda = datetime.now().strftime("%Y-%m-%d")
            
            self.cursor.execute("""
                INSERT INTO db_fin.comissoes 
                (venda_id, vendedor, valor_venda, percentual_comissao, 
                 valor_comissao, data_venda, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pendente')
            """, (venda_id, vendedor, valor_venda, percentual, valor_comissao, data_venda))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao salvar comissão: {e}")
            return False
    
    def obter_comissoes_pendentes(self, vendedor=None):
        """Retorna comissões pendentes"""
        try:
            if vendedor:
                self.cursor.execute("""
                    SELECT * FROM db_fin.comissoes
                    WHERE status = 'Pendente' AND vendedor = ?
                    ORDER BY data_venda DESC
                """, (vendedor,))
            else:
                self.cursor.execute("""
                    SELECT * FROM db_fin.comissoes
                    WHERE status = 'Pendente'
                    ORDER BY data_venda DESC
                """)
            return self.cursor.fetchall()
        except:
            return []
    
    def pagar_comissao(self, comissao_id):
        """Marca comissão como paga"""
        try:
            data_pagamento = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("""
                UPDATE db_fin.comissoes
                SET status = 'Pago', data_pagamento = ?
                WHERE id = ?
            """, (data_pagamento, comissao_id))
            self.conn.commit()
            return True
        except:
            return False
    
    def projecao_fluxo_caixa(self, dias=30):
        """Projeta fluxo de caixa para os próximos X dias"""
        try:
            hoje = datetime.now().date()
            data_fim = hoje + timedelta(days=dias)
            
            # Contas a receber
            self.cursor.execute("""
                SELECT data_vencimento, COALESCE(SUM(valor_pendente), 0) as total
                FROM db_fin.contas_receber
                WHERE data_vencimento BETWEEN ? AND ?
                AND status = 'Pendente'
                GROUP BY data_vencimento
                ORDER BY data_vencimento
            """, (hoje.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")))
            
            receber = {r[0]: r[1] for r in self.cursor.fetchall()}
            
            # Contas a pagar
            self.cursor.execute("""
                SELECT data_vencimento, COALESCE(SUM(valor), 0) as total
                FROM db_fin.contas_pagar
                WHERE data_vencimento BETWEEN ? AND ?
                AND status = 'Pendente'
                GROUP BY data_vencimento
                ORDER BY data_vencimento
            """, (hoje.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")))
            
            pagar = {r[0]: r[1] for r in self.cursor.fetchall()}
            
            # Monta projeção dia a dia
            projecao = []
            saldo_acumulado = 0
            
            for dia in range(dias + 1):
                data = (hoje + timedelta(days=dia)).strftime("%Y-%m-%d")
                entrada = receber.get(data, 0)
                saida = pagar.get(data, 0)
                saldo_dia = entrada - saida
                saldo_acumulado += saldo_dia
                
                projecao.append({
                    "data": data,
                    "entrada": entrada,
                    "saida": saida,
                    "saldo_dia": saldo_dia,
                    "saldo_acumulado": saldo_acumulado
                })
            
            return projecao
        except Exception as e:
            print(f"Erro na projeção: {e}")
            return []
    
    def gerar_dre(self, data_inicio, data_fim):
        """Gera Demonstração do Resultado do Exercício"""
        try:
            # Receita Bruta
            receita_bruta = self.calcular_faturamento_periodo(data_inicio, data_fim)
            
            # Impostos (estimativa 8% Simples Nacional)
            impostos = receita_bruta * 0.08
            receita_liquida = receita_bruta - impostos
            
            # CPV (Custo Produtos Vendidos)
            self.cursor.execute("""
                SELECT COALESCE(SUM(iv.quantidade * iv.preco_custo), 0)
                FROM main.itens_venda iv
                JOIN main.vendas v ON iv.venda_id = v.id
                WHERE v.data_venda BETWEEN ? AND ?
                AND v.status != 'Cancelado'
            """, (data_inicio, data_fim))
            cpv = self.cursor.fetchone()[0] or 0
            
            # Lucro Bruto
            lucro_bruto = receita_liquida - cpv
            margem_bruta = (lucro_bruto / receita_bruta * 100) if receita_bruta > 0 else 0
            
            # Despesas Operacionais
            despesas = self.calcular_despesas_periodo(data_inicio, data_fim)
            
            # Lucro Líquido
            lucro_liquido = lucro_bruto - despesas
            margem_liquida = (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0
            
            return {
                "receita_bruta": receita_bruta,
                "impostos": impostos,
                "receita_liquida": receita_liquida,
                "cpv": cpv,
                "lucro_bruto": lucro_bruto,
                "margem_bruta": margem_bruta,
                "despesas_operacionais": despesas,
                "lucro_liquido": lucro_liquido,
                "margem_liquida": margem_liquida
            }
        except Exception as e:
            print(f"Erro ao gerar DRE: {e}")
            return None
    
    def exportar_clientes_excel(self, filepath=None):
        """Exporta clientes para Excel"""
        try:
            if not filepath:
                filepath = f"clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            self.cursor.execute("""
                SELECT id, tipo_pessoa, categoria, nome_razao, cpf_cnpj,
                       telefone, email, cidade, uf, data_registro
                FROM db_cli.entidades
                ORDER BY nome_razao
            """)
            
            dados = self.cursor.fetchall()
            colunas = ["ID", "Tipo", "Categoria", "Nome/Razão", "CPF/CNPJ",
                      "Telefone", "Email", "Cidade", "UF", "Data Cadastro"]
            
            return exportar_excel_generico(dados, colunas, "Relatório de Clientes", filepath)
        except Exception as e:
            return False, str(e)
    
    def exportar_produtos_excel(self, filepath=None):
        """Exporta produtos para Excel"""
        try:
            if not filepath:
                filepath = f"produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            self.cursor.execute("""
                SELECT sku, nome, categoria, preco_custo, preco_venda,
                       estoque_atual, unidade_medida, data_cadastro
                FROM db_prod.produtos
                ORDER BY nome
            """)
            
            dados = self.cursor.fetchall()
            colunas = ["SKU", "Nome", "Categoria", "Preço Custo", "Preço Venda",
                      "Estoque", "Unidade", "Data Cadastro"]
            
            return exportar_excel_generico(dados, colunas, "Relatório de Produtos", filepath)
        except Exception as e:
            return False, str(e)
    
    def atualizar_margem_lucro_produto(self, produto_id):
        """Atualiza margem de lucro calculada do produto"""
        try:
            self.cursor.execute("""
                SELECT preco_custo, preco_venda FROM db_prod.produtos WHERE id = ?
            """, (produto_id,))
            
            resultado = self.cursor.fetchone()
            if resultado:
                custo, venda = resultado
                margem = calcular_margem_lucro(venda, custo)
                
                self.cursor.execute("""
                    UPDATE db_prod.produtos SET margem_lucro = ? WHERE id = ?
                """, (margem, produto_id))
                
                self.conn.commit()
                return True
        except:
            return False
    
    def atualizar_dias_atraso_inadimplencia(self):
        """Atualiza dias de atraso nas contas a receber"""
        try:
            hoje = datetime.now().date()
            
            self.cursor.execute("""
                SELECT id, data_vencimento FROM db_fin.contas_receber
                WHERE status = 'Pendente'
            """)
            
            for conta_id, vencimento in self.cursor.fetchall():
                data_venc = datetime.strptime(vencimento, "%Y-%m-%d").date()
                dias_atraso = max(0, (hoje - data_venc).days)
                
                # Atualiza status para "Vencido" se necessário
                status = "Vencido" if dias_atraso > 0 else "Pendente"
                
                self.cursor.execute("""
                    UPDATE db_fin.contas_receber
                    SET dias_atraso = ?, status = ?
                    WHERE id = ?
                """, (dias_atraso, status, conta_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar atrasos: {e}")
            return False
    # ==================== MÉTODOS BANCÁRIOS ====================
    
    def listar_bancos_ativos(self):
        """Lista bancos ativos"""
        try:
            self.cursor.execute("""
                SELECT id, codigo_banco, nome_banco, agencia, conta, tipo_conta, saldo_atual
                FROM db_fin.bancos
                WHERE ativo = 1
                ORDER BY nome_banco
            """)
            return self.cursor.fetchall()
        except:
            return []
    
    def obter_saldo_banco(self, banco_id):
        """Obtém saldo atual do banco"""
        try:
            self.cursor.execute("SELECT saldo_atual FROM db_fin.contas_bancarias WHERE id = ?", (banco_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except:
            return 0
    
    def atualizar_saldo_banco(self, banco_id):
        """Recalcula e atualiza saldo do banco"""
        try:
            # Pega saldo inicial
            self.cursor.execute("SELECT saldo_inicial FROM db_fin.contas_bancarias WHERE id = ?", (banco_id,))
            resultado = self.cursor.fetchone()
            if not resultado:
                return 0
            saldo_inicial = resultado[0] or 0
            
            # Soma entradas (valores positivos)
            self.cursor.execute("""
                SELECT COALESCE(SUM(valor_liquido), 0)
                FROM db_fin.movimentacoes_bancarias
                WHERE conta_id = ? AND tipo_movimentacao = 'Entrada'
            """, (banco_id,))
            entradas = self.cursor.fetchone()[0] or 0
            
            # Soma saídas (valores negativos)
            self.cursor.execute("""
                SELECT COALESCE(SUM(valor_liquido), 0)
                FROM db_fin.movimentacoes_bancarias
                WHERE conta_id = ? AND tipo_movimentacao = 'Saída'
            """, (banco_id,))
            saidas = self.cursor.fetchone()[0] or 0
            
            # Calcula saldo atual: saldo_inicial + entradas - saídas
            saldo_atual = saldo_inicial + entradas - saidas
            
            # Atualiza na tabela contas_bancarias
            self.cursor.execute("""
                UPDATE db_fin.contas_bancarias SET saldo_atual = ? WHERE id = ?
            """, (saldo_atual, banco_id))
            
            self.conn.commit()
            return saldo_atual
        except Exception as e:
            print(f"Erro ao atualizar saldo: {e}")
            return 0
    
    def lancar_recebimento_bancario(self, dados):
        """Lança recebimento bancário"""
        try:
            valor_liquido = dados['valor'] - dados.get('taxa', 0)
            
            # Insere na tabela de movimentações com os campos corretos
            self.cursor.execute("""
                INSERT INTO db_fin.movimentacoes_bancarias
                (conta_id, tipo_movimentacao, data_movimentacao, valor_bruto, taxa, 
                 valor_liquido, forma_pagamento, origem, origem_id, descricao, comprovante_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados['conta_id'],                              # conta_id (não banco_id)
                'Entrada',                                      # tipo_movimentacao
                dados['data_movimentacao'],                     # data_movimentacao
                dados['valor'],                                 # valor_bruto
                dados.get('taxa', 0),                          # taxa
                valor_liquido,                                  # valor_liquido
                dados.get('forma_pagamento', 'Dinheiro'),      # forma_pagamento
                dados.get('origem', 'Venda'),                  # origem
                dados.get('origem_id'),                         # origem_id (venda_id)
                dados['descricao'],                             # descricao
                dados.get('comprovante_path', '')              # comprovante_path
            ))
            
            self.conn.commit()
            
            # Atualiza saldo
            self.atualizar_saldo_banco(dados['conta_id'])
            
            # Se tem origem_id (venda_id), marca contas_receber como recebida
            if dados.get('origem_id'):
                self.cursor.execute("""
                    UPDATE db_fin.contas_receber
                    SET status = 'Recebido', data_recebimento = ?
                    WHERE venda_id = ?
                """, (dados['data_movimentacao'], dados['origem_id']))
                self.conn.commit()
            
            return True, "Recebimento lançado com sucesso!"
        except Exception as e:
            return False, str(e)
    
    def calcular_taxa_maquininha(self, valor, operadora, tipo_cartao, parcelas=1):
        """Calcula taxa da maquininha"""
        try:
            self.cursor.execute("""
                SELECT taxa_percentual, prazo_recebimento
                FROM db_fin.taxas_maquininha
                WHERE operadora = ? AND tipo_cartao = ? AND parcelas = ? AND ativo = 1
            """, (operadora, tipo_cartao, parcelas))
            
            result = self.cursor.fetchone()
            if result:
                taxa_percentual, prazo = result
                valor_taxa = valor * (taxa_percentual / 100)
                valor_liquido = valor - valor_taxa
                return {
                    'taxa_percentual': taxa_percentual,
                    'valor_taxa': valor_taxa,
                    'valor_liquido': valor_liquido,
                    'prazo_recebimento': prazo
                }
            return None
        except:
            return None
    
    def buscar_impostos_bcb(self):
        """Busca impostos atuais do Banco Central"""
        try:
            # SGS 4390 = Taxa Selic
            selic = sgs.get({'selic': 4390}, start='2024-01-01')
            if not selic.empty:
                taxa_selic = selic['selic'].iloc[-1]
                return {'selic': taxa_selic}
            return None
        except Exception as e:
            print(f"Erro ao buscar impostos BCB: {e}")
            return None
    
    def obter_contas_bancarias(self, apenas_ativas=True):
        """Obtém lista de contas bancárias"""
        try:
            if apenas_ativas:
                self.cursor.execute("""
                    SELECT id, banco, agencia, numero_conta, tipo_conta, saldo_atual, ativa
                    FROM db_fin.contas_bancarias
                    WHERE ativa = 1
                    ORDER BY banco
                """)
            else:
                self.cursor.execute("""
                    SELECT id, banco, agencia, numero_conta, tipo_conta, saldo_atual, ativa
                    FROM db_fin.contas_bancarias
                    ORDER BY banco
                """)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erro ao obter contas bancárias: {e}")
            return []
    
    def obter_saldo_total_contas(self):
        """Obtém saldo total de todas as contas ativas"""
        try:
            self.cursor.execute("""
                SELECT COALESCE(SUM(saldo_atual), 0)
                FROM db_fin.contas_bancarias
                WHERE ativa = 1
            """)
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"Erro ao obter saldo total: {e}")
            return 0

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

# --- TELA DE LOGIN KEYAUTH ---

SESSION_FILE = "session.json"

# def save_session(user_data):
#     """Salva o status de login em um arquivo JSON."""
#     try:
#         with open(SESSION_FILE, 'w') as f:
#             json.dump(user_data, f)
#     except Exception as e:
#         print(f"Erro ao salvar sessão: {e}")

def load_session():
    """Verifica se existe uma sessão salva válida."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def clear_session():
    """Apaga o arquivo de sessão (para Logout)."""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

KEY_LOCAL = b'gQjXw8kZ4q5yJ2n0oP1r3sT6uV9wX8yZ7aB6cD5eF4g=' 
cipher = Fernet(KEY_LOCAL)

CONFIG_FILE = "user_config.dat"

def save_session(username, password):
    """Salva usuário e senha criptografados no disco"""
    try:
        # Criptografa os dados
        enc_user = cipher.encrypt(username.encode()).decode()
        enc_pass = cipher.encrypt(password.encode()).decode()
        
        data = {"u": enc_user, "p": enc_pass}
        
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Erro ao salvar sessão: {e}")

def load_session():
    """Tenta ler e descriptografar a sessão salva"""
    if not os.path.exists(SESSION_FILE):
        return None, None
    try:
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
            
        # Descriptografa
        user = cipher.decrypt(data["u"].encode()).decode()
        password = cipher.decrypt(data["p"].encode()).decode()
        return user, password
    except:
        return None, None # Se o arquivo estiver corrompido ou chave errada

def clear_session():
    """Apaga o arquivo de sessão (Logout)"""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

class LoginDialog(QDialog):
    def __init__(self, api_instance):
        super().__init__()
        self.api = api_instance
        self.setWindowTitle("Autenticação")
        self.setFixedSize(400, 300)
        self.setStyleSheet(f"background-color: {COLORS['light_bg']};")
        
        # Remove botão de ajuda/fechar para forçar login ou sair
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Título
        lbl_title = QLabel("Login do Usuário")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['primary']}; margin-bottom: 10px;")
        layout.addWidget(lbl_title)

        # Campos
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Usuário")
        self.user_input.setStyleSheet(FOCUS_STYLE)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Senha")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet(FOCUS_STYLE)

        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)

        # Checkbox "Lembrar de mim" (Visualmente agradável)
        self.chk_save = QCheckBox("Manter conectado")
        self.chk_save.setChecked(True) # Padrão marcado
        self.chk_save.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self.chk_save)

        # Botão Entrar
        self.btn_login = QPushButton("ENTRAR NO SISTEMA")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white; font-weight: bold; padding: 12px; border-radius: 6px; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS['primary_hover']}; }}
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
        QApplication.processEvents()

        # Tenta Logar no KeyAuth
        self.api.login(username, password)
        
        if self.api.check():
            # LOGIN SUCESSO!
            
            # Se a opção "Manter conectado" estiver marcada, salva criptografado
            if self.chk_save.isChecked():
                save_session(username, password)
            else:
                clear_session()
            
            self.accept()
        else:
            # Pega mensagem de erro
            msg = "Login falhou."
            if hasattr(self.api, 'json') and self.api.json:
                 msg = self.api.json.get("message", msg)
            
            self.lbl_status.setText(msg)
            self.btn_login.setText("ENTRAR NO SISTEMA")
            self.btn_login.setEnabled(True)

# class ChangePasswordDialog(QDialog):
#     def __init__(self, api_instance, username, old_password):
#         super().__init__()
#         self.api = api_instance
#         self.username = username
#         self.old_password = old_password # Recebe a senha provisória (123456)
        
#         self.setWindowTitle("Definir Senha Pessoal")
#         self.setFixedSize(400, 320)
#         self.setStyleSheet(f"background-color: {COLORS['light_bg']};")
        
#         # Remove o botão de fechar (X) para obrigar a ação
#         self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

#         layout = QVBoxLayout()
#         layout.setSpacing(15)
#         layout.setContentsMargins(30, 30, 30, 30)

#         lbl_info = QLabel(f"Olá, <b>{username}</b>.<br>Primeiro acesso detectado.<br>Defina sua nova senha pessoal.")
#         lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         lbl_info.setStyleSheet("color: #2c3e50; font-size: 14px;")
#         layout.addWidget(lbl_info)

#         self.new_pass = QLineEdit()
#         self.new_pass.setPlaceholderText("Nova Senha")
#         self.new_pass.setEchoMode(QLineEdit.EchoMode.Password)
#         self.new_pass.setStyleSheet(FOCUS_STYLE)

#         self.confirm_pass = QLineEdit()
#         self.confirm_pass.setPlaceholderText("Confirmar Nova Senha")
#         self.confirm_pass.setEchoMode(QLineEdit.EchoMode.Password)
#         self.confirm_pass.setStyleSheet(FOCUS_STYLE)

#         layout.addWidget(self.new_pass)
#         layout.addWidget(self.confirm_pass)

#         # Botão Salvar
#         self.btn_save = QPushButton("SALVAR NOVA SENHA")
#         self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.btn_save.setStyleSheet(f"""
#             QPushButton {{ background-color: {COLORS['success']}; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }}
#             QPushButton:hover {{ background-color: #219150; }}
#         """)
#         self.btn_save.clicked.connect(self.save_password)
#         layout.addWidget(self.btn_save)
        
#         # Botão Cancelar (volta para tela de login)
#         self.btn_cancel = QPushButton("Cancelar / Sair")
#         self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.btn_cancel.setStyleSheet("background: transparent; color: #7f8c8d; border: none; margin-top: 5px;")
#         self.btn_cancel.clicked.connect(self.reject)
#         layout.addWidget(self.btn_cancel)

#         self.lbl_status = QLabel("")
#         self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 12px;")
#         layout.addWidget(self.lbl_status)

#         self.setLayout(layout)

#     def save_password(self):
#         new_pw = self.new_pass.text()
#         conf_pw = self.confirm_pass.text()

#         if len(new_pw) < 4:
#             self.lbl_status.setText("Mínimo 4 caracteres.")
#             return
#         if new_pw != conf_pw:
#             self.lbl_status.setText("Senhas não conferem.")
#             return

#         # AQUI ESTÁ O TRUQUE:
#         # Não chamamos a API. Apenas salvamos localmente.
#         save_local_password(self.username, new_pw)
        
#         QMessageBox.information(self, "Sucesso", "Senha definida neste computador!\nUse-a nos próximos acessos.")
#         self.accept()

class MainWindow(QMainWindow):
    def __init__(self, api_instance):
        super().__init__()
        self.api = api_instance
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

        # --- BOTÃO SAIR ---
        btn_sair = QPushButton("🚪 Sair")
        btn_sair.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sair.setStyleSheet("""
            QPushButton { 
                background-color: #ef4444; color: white; font-weight: bold;
                padding: 12px; border: none; border-radius: 6px; margin: 10px; margin-top: 0px; font-size: 14px;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        btn_sair.clicked.connect(self.logout)
        sidebar_layout.addWidget(btn_sair)
        
        # --- ÁREA DE CONTEÚDO (STACK) ---
        # ATENÇÃO: Criamos a área de conteúdo ANTES de adicionar os widgets
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("background-color: #f1f2f6;")
        main_layout.addWidget(self.content_area)

        # --- INICIALIZAÇÃO DAS TELAS ---
        self.tab_nova_venda = LancarPedido(self.db_context)
        self.tab_pedidos = PedidosForm(self.db_context)
        self.tab_cadastro_prod = CadastroProdutoForm(self.db_context)
        # Conecta sinal de produto salvo para atualizar a venda
        self.tab_cadastro_prod.produto_salvo_signal.connect(self.tab_nova_venda.load_produtos)

        # Instancia as telas de Clientes e Fornecedores (Nova Classe Unificada)
        self.page_clientes = GerenciamentoEntidades(self.db_context, "Cliente")
        self.page_fornecedores = GerenciamentoEntidades(self.db_context, "Fornecedor")
        self.tab_nova_venda.pedido_salvo_signal.connect(self.ao_salvar_pedido)
        
        # 2. Quando clica em editar na lista "PedidosForm", vai para o formulário
        self.tab_pedidos.editar_pedido_signal.connect(self.ao_editar_pedido)
        
        # 3. Quando cadastra produto novo, atualiza a lista de produtos na venda
        self.tab_cadastro_prod.produto_salvo_signal.connect(self.tab_nova_venda.load_produtos)

        # --- Instancia componentes com referências para conexões de sinais ---
        tab_fluxo_caixa = FluxoCaixaForm(self.db_context)
        tab_gestao_bancaria = GestaoBancaria(self.db_context)

        # --- MAPEAMENTO DO MENU ---
        self.items_map = [
            ("📊 Dashboard Gerencial", DashboardTab(self.db_context)),
            ("👥 Cadastro de Clientes", self.page_clientes), 
            ("🏢 Cadastro de Fornecedores", self.page_fornecedores),
            ("📦 Cadastro de Produtos", self.tab_cadastro_prod), 
            ("💳 Contas a Pagar", ContasPagarForm(self.db_context)),
            ("🛒 Novo Pedido", self.tab_nova_venda), 
            ("📋 Pedidos", self.tab_pedidos),
            ("💵 Fluxo de Caixa", tab_fluxo_caixa),
            ("📈 Relatório DRE", RelatorioDREForm(self.db_context)),
            ("💼 Comissões", GestaoComissoes(self.db_context)),
            ("🏦 Gestão Bancária", tab_gestao_bancaria)
        ]
        
        # Popula o menu e a Stack ao mesmo tempo
        for nome, widget in self.items_map:
            self.menu_list.addItem(QListWidgetItem(nome))
            self.content_area.addWidget(widget)
        
        # --- Conectar sinais de integração ---
        # Quando recebimentos são adicionados em GestaoBancaria, atualiza FluxoCaixa
        tab_gestao_bancaria.recebimento_adicionado_signal.connect(tab_fluxo_caixa.load)
            
        self.menu_list.currentRowChanged.connect(self.switch_tab)

        # --- VERIFICAÇÃO AUTOMÁTICA DE PARCELAS ---
        # Usa QTimer para rodar logo após a janela aparecer, evitando travamentos visuais na inicialização
        QTimer.singleShot(500, self.verificar_parcelas_do_dia)

    def switch_tab(self, index):
        self.content_area.setCurrentIndex(index)

    def verificar_parcelas_do_dia(self):
        """Verifica se há contas a receber hoje e abre o diálogo"""
        hoje = QDate.currentDate().toString("yyyy-MM-dd")
        
        # Consulta rápida pra ver se tem algo antes de abrir o dialog
        try:
            self.db_context.cursor.execute("SELECT COUNT(*) FROM db_fin.contas_receber WHERE data_vencimento = ? AND status != 'Recebido'", (hoje,))
            count = self.db_context.cursor.fetchone()[0]
            
            if count > 0:
                dlg = DialogoParcelasHoje(self.db_context, self)
                dlg.exec() # Abre modal
        except Exception as e:
            print(f"Erro ao verificar parcelas: {e}")
            
    def ao_editar_pedido(self, venda_id):
        """Chamado quando clica no lápis na lista de 'Pedidos'"""
        # Queremos ir para a aba "Novo Pedido" (Index 5 na lista self.items_map)
        self.menu_list.setCurrentRow(5)
        
        # Carrega os dados na tela de lançamento
        self.tab_nova_venda.carregar_pedido_para_edicao(venda_id)

    def ao_salvar_pedido(self):
        """Chamado quando um pedido é salvo com sucesso em 'Novo Pedido'"""
        # Queremos ir para a aba "Pedidos" (Index 6 na lista self.items_map)
        # Atualizamos visualmente o menu lateral e a tela
        self.menu_list.setCurrentRow(6) 
        self.tab_pedidos.carregar_dados() # Recarrega a lista


    def fazer_backup_automatico(self):
        """Inicia backup automático em background"""
        pasta = QFileDialog.getExistingDirectory(self, "Pasta para Backup", os.path.expanduser("~"))
        if not pasta:
            return
        
        # Cria dialog de progresso
        self.dialog_backup = QDialog(self)
        self.dialog_backup.setWindowTitle("Backup em Andamento")
        self.dialog_backup.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        self.lbl_backup_status = QLabel("Iniciando backup...")
        self.lbl_backup_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_backup_status)
        
        self.progress_backup = QProgressBar()
        layout.addWidget(self.progress_backup)
        
        self.dialog_backup.setLayout(layout)
        
        # Thread de backup
        self.thread_backup = BackupAutomaticoThread(self.db_context)
        self.thread_backup.progresso.connect(self.atualizar_progresso_backup)
        self.thread_backup.concluido.connect(self.backup_concluido)
        
        # Sobrescreve o diretório
        self.thread_backup.pasta_destino = pasta
        self.thread_backup.start()
        
        self.dialog_backup.exec()
    
    def atualizar_progresso_backup(self, valor, mensagem):
        """Atualiza barra de progresso do backup"""
        self.progress_backup.setValue(valor)
        self.lbl_backup_status.setText(mensagem)
    
    def backup_concluido(self, sucesso, resultado):
        """Callback quando backup termina"""
        self.dialog_backup.close()
        
        if sucesso:
            resp = QMessageBox.question(self, "Backup Concluído",
                f"✅ Backup salvo com sucesso!\n\n{resultado}\n\nAbrir pasta?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.Yes:
                import os
                os.startfile(os.path.dirname(resultado))
        else:
            QMessageBox.critical(self, "Erro", f"❌ Erro no backup:\n\n{resultado}")


    def logout(self):
        reply = QMessageBox.question(self, 'Sair', 
                                     "Deseja fazer logout e trocar de usuário?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            clear_session() # Apaga o arquivo json
            self.close()    # Fecha o painel atual
            
            # Reinicia a aplicação para pedir login novamente
            # Isso é um truque para reabrir o app do zero
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)

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
    # Define ID para o Windows agrupar ícones corretamente
    myappid = 'minhaempresa.meusistema.financeiro.2.0' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
        
    # Estilo Global
    app.setStyleSheet("""
        QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox { 
            padding: 8px; border: 1px solid #ccc; border-radius: 4px; 
            background: white; color: black; 
        } 
        QComboBox QAbstractItemView { 
            color: black; background-color: white; 
            selection-background-color: #3c40c6; selection-color: white; 
        } 
        QLabel { color: #333; }
        QCalendarWidget QWidget { background-color: white; color: black; }
        QCalendarWidget QToolButton { color: black; icon-size: 20px; }
        QCalendarWidget QMenu { background-color: white; color: black; }
        QCalendarWidget QSpinBox { background-color: white; color: black; }
        QCalendarWidget QAbstractItemView:enabled {
            color: black; background-color: white;
            selection-background-color: #3498db; selection-color: white;
        }
    """)
    
    # --- 1. CONFIGURAÇÃO KEYAUTH ---
    print(" Configurando API...")
    keyauthapp = api(
        name = "dashpoin.auth",
        ownerid = os.getenv("KEYAUTH_OWNER_ID", "your-keyauth-owner-id"),
        version = "1.0",
        hash_to_check = get_checksum()
    )

    # CORREÇÃO: Verificamos se já está inicializado para evitar o erro duplo
    # A maioria dos wrappers KeyAuth define 'self.sessionid' quando inicializado
    if not hasattr(keyauthapp, 'sessionid') or not keyauthapp.sessionid:
        print(" Inicializando conexão com KeyAuth...")
        keyauthapp.init() 

    # 2. TENTATIVA DE LOGIN AUTOMÁTICO
    login_sucesso = False
    
    # Carrega dados criptografados do disco
    saved_user, saved_pass = load_session()
    
    if saved_user and saved_pass:
        print(f" Credenciais encontradas. Tentando login automático para: {saved_user}")
        
        # Tenta logar direto sem abrir janela
        keyauthapp.login(saved_user, saved_pass)
        
        if keyauthapp.check():
            print(" Login automático realizado com sucesso!")
            login_sucesso = True
        else:
            print(" Credenciais salvas inválidas ou expiradas.")
            clear_session() # Limpa para não tentar de novo errado

    # 3. SE NÃO LOGOU AUTOMÁTICO, ABRE TELA DE LOGIN
    if not login_sucesso:
        login_screen = LoginDialog(keyauthapp)
        if login_screen.exec() == QDialog.DialogCode.Accepted:
            login_sucesso = True
        else:
            sys.exit() # Usuário fechou a janela

    # 4. INICIA O SISTEMA
    if login_sucesso:
        try:
            # Splash Screen
            splash = LoadingScreen()
            splash.show()
            
            # Centraliza
            ag = splash.frameGeometry()
            cp = app.primaryScreen().availableGeometry().center()
            ag.moveCenter(cp)
            splash.move(ag.topLeft())

            splash.update_progress(10, "Autenticado. Iniciando sistema...")
            app.processEvents()
            
            # Instancia MainWindow passando a API (IMPORTANTE)
            # Certifique-se que alterou o __init__ da MainWindow como no passo 3
            window = MainWindow(keyauthapp) 
            
            splash.update_progress(50, "Carregando banco de dados...")
            app.processEvents()
            time.sleep(0.5)
            
            splash.update_progress(100, "Pronto!")
            app.processEvents()
            
            splash.close()
            window.show()
            
            sys.exit(app.exec())
            
        except Exception as e:
            print("-" * 50)
            print("ERRO CRÍTICO:")
            print(str(e))
            import traceback
            traceback.print_exc()
            input("Erro fatal. Pressione ENTER...")