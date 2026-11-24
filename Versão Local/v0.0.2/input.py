import sqlite3
import os
import random
from datetime import datetime, timedelta
from faker import Faker

# --- Configurações ---
# Ajuste este caminho se seus bancos estiverem em outra pasta
DATA_DIR = "data" 

DB_VENDAS = os.path.join(DATA_DIR, "vendas.db")
DB_CLIENTES = os.path.join(DATA_DIR, "clientes.db")
DB_PRODUTOS = os.path.join(DATA_DIR, "produtos.db")
DB_FINANCEIRO = os.path.join(DATA_DIR, "financeiro.db")

fake = Faker('pt_BR')

class DataSeeder:
    def __init__(self):
        print(f"🚀 Iniciando gerador de dados em: {DATA_DIR}")
        self.ensure_directory()
        
        # Conecta ao banco principal (Vendas)
        self.conn = sqlite3.connect(DB_VENDAS)
        self.cursor = self.conn.cursor()
        
        # Anexa os bancos auxiliares para permitir queries cruzadas (JOINs)
        self.attach_databases()
        
        # Cria as tabelas com a nova estrutura solicitada
        self.create_tables()
        
        # Limpa dados antigos para evitar duplicação
        self.clean_database()

    def ensure_directory(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"📂 Diretório '{DATA_DIR}' criado.")

    def attach_databases(self):
        # Garante que os arquivos existam
        for db in [DB_CLIENTES, DB_PRODUTOS, DB_FINANCEIRO]:
            if not os.path.exists(db):
                sqlite3.connect(db).close()
            
        # Anexa ao contexto atual
        try:
            self.cursor.execute(f"ATTACH DATABASE '{DB_CLIENTES}' AS db_cli")
            self.cursor.execute(f"ATTACH DATABASE '{DB_PRODUTOS}' AS db_prod")
            self.cursor.execute(f"ATTACH DATABASE '{DB_FINANCEIRO}' AS db_fin")
        except sqlite3.OperationalError:
            print("⚠️  Bancos de dados já estavam anexados ou erro de permissão.")

    def create_tables(self):
        print("🛠️  Criando/Atualizando tabelas...")
        
        # --- 1. Clientes ---
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_cli.entidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            tipo_pessoa TEXT, 
            categoria TEXT, 
            nome_razao TEXT NOT NULL, 
            nome_fantasia TEXT, 
            cpf_cnpj TEXT, 
            ie_rg TEXT, 
            endereco TEXT, 
            bairro TEXT, 
            cidade TEXT, 
            uf TEXT, 
            cep TEXT, 
            telefone TEXT, 
            email TEXT, 
            data_registro DATE
        )''')

        # --- 2. Produtos ---
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_prod.produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            sku TEXT UNIQUE NOT NULL, 
            nome TEXT NOT NULL, 
            descricao TEXT, 
            categoria TEXT, 
            preco_custo REAL, 
            preco_venda REAL, 
            estoque_atual REAL, 
            unidade_medida TEXT, 
            data_cadastro DATE
        )''')

        # --- 3. Vendas (Cabeçalho) ---
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
            descricao_pedido TEXT,
            obs TEXT
        )''')

        # --- 3.1 Itens da Venda (NOVO) ---
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER,
            preco_unitario REAL,
            subtotal REAL,
            detalhes TEXT,
            variacao TEXT,
            preco_custo REAL,
            ipi REAL,
            icms REAL,
            anexo_path TEXT,
            FOREIGN KEY(venda_id) REFERENCES vendas(id)
        )''')

        # --- 4. Contas a Pagar ---
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            descricao TEXT NOT NULL, 
            fornecedor_id INTEGER,
            categoria TEXT, 
            valor REAL NOT NULL, 
            data_vencimento DATE, 
            data_pagamento DATE,
            status TEXT, 
            forma_pagamento TEXT, 
            obs TEXT
        )''')

        # --- 5. Contas a Receber (ATUALIZADO) ---
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_receber (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            descricao TEXT NOT NULL,
            cliente_id INTEGER,
            num_parcela TEXT,
            valor_previsto REAL NOT NULL,
            valor_recebido REAL,
            data_vencimento DATE,
            data_recebimento DATE,
            status TEXT,
            forma_pagamento TEXT,
            conta_destino TEXT,
            comprovante_path TEXT,
            obs TEXT
        )''')
        self.conn.commit()

    def clean_database(self):
        print("🧹 Limpando dados antigos...")
        tables = [
            "main.itens_venda", "main.vendas", 
            "db_fin.contas_receber", "db_fin.contas_pagar",
            "db_cli.entidades", "db_prod.produtos"
        ]
        for t in tables:
            try:
                self.cursor.execute(f"DELETE FROM {t}")
            except Exception as e:
                print(f"⚠️  Erro ao limpar {t}: {e}")
                
        self.cursor.execute("DELETE FROM sqlite_sequence") # Reseta os IDs auto increment
        self.conn.commit()

    def seed_entidades(self):
        print("👥 Gerando Clientes e Fornecedores...")
        
        # 1. Gerar Clientes (Pessoa Física)
        for _ in range(30):
            self.cursor.execute("""
                INSERT INTO db_cli.entidades (tipo_pessoa, categoria, nome_razao, cpf_cnpj, cidade, uf, data_registro)
                VALUES ('Física', 'Cliente', ?, ?, ?, ?, ?)
            """, (fake.name(), fake.cpf(), fake.city(), fake.state_abbr(), fake.date_this_year()))
            
        # 2. Gerar Fornecedores (Jurídica)
        for _ in range(10):
            self.cursor.execute("""
                INSERT INTO db_cli.entidades (tipo_pessoa, categoria, nome_razao, nome_fantasia, cpf_cnpj, cidade, uf, data_registro)
                VALUES ('Jurídica', 'Fornecedor', ?, ?, ?, ?, ?, ?)
            """, (fake.company(), fake.company_suffix(), fake.cnpj(), fake.city(), fake.state_abbr(), fake.date_this_year()))
            
        self.conn.commit()

    def seed_produtos(self):
        print("📦 Gerando Produtos...")
        # (SKU, Nome, Categoria, Custo, Venda, Unidade)
        produtos = [
            ("IPHONE13", "iPhone 13 128GB", "Smartphone", 3500, 5200, "UN"),
            ("GALAXYS22", "Samsung S22", "Smartphone", 3000, 4500, "UN"),
            ("NBDELL", "Notebook Dell i7", "Computadores", 4500, 6800, "UN"),
            ("MOUSELOG", "Mouse Logitech MX", "Periféricos", 300, 550, "UN"),
            ("TECLMEC", "Teclado Mecânico", "Periféricos", 200, 450, "UN"),
            ("MONITORLG", "Monitor LG Ultrawide", "Monitores", 900, 1600, "UN"),
            ("HEADSET", "Headset Gamer", "Áudio", 150, 320, "UN"),
            ("CABOHDMI", "Cabo HDMI 2.0", "Cabos", 20, 60, "UN"),
            ("CARREG", "Carregador Rápido", "Acessórios", 50, 120, "UN"),
            ("CAPA", "Capa Protetora", "Acessórios", 10, 45, "UN"),
            ("SERV_INST", "Instalação de Software", "Serviços", 0, 150, "SV")
        ]
        for sku, nome, cat, custo, venda, unid in produtos:
            try:
                self.cursor.execute("""
                    INSERT INTO db_prod.produtos (sku, nome, categoria, preco_custo, preco_venda, estoque_atual, unidade_medida, data_cadastro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (sku, nome, cat, custo, venda, random.randint(5, 100), unid, fake.date_this_year()))
            except sqlite3.IntegrityError:
                pass # SKU já existe
        self.conn.commit()

    def seed_movimentacao(self):
        print("📅 Gerando Movimentação Financeira (365 dias)...")
        
        # Carregar IDs auxiliares
        self.cursor.execute("SELECT id FROM db_cli.entidades WHERE categoria='Cliente'")
        clientes_ids = [r[0] for r in self.cursor.fetchall()]
        
        self.cursor.execute("SELECT id FROM db_cli.entidades WHERE categoria='Fornecedor'")
        fornecedores_ids = [r[0] for r in self.cursor.fetchall()]
        
        # Pegamos ID, Preço Venda e Preço Custo dos produtos
        self.cursor.execute("SELECT id, preco_venda, preco_custo FROM db_prod.produtos")
        produtos = self.cursor.fetchall()
        
        formas_pagamento = ["Pix", "Cartão de Crédito", "Cartão de Débito", "Boleto", "Dinheiro"]
        contas_bancarias = ["Banco Itaú", "Banco Inter", "Caixa Econômica", "Nubank"]

        # Configuração de Despesas Fixas
        despesas_fixas = [
            (5, "Aluguel Loja", "Despesas Operacionais", 2500, 2500),
            (5, "Condomínio", "Despesas Operacionais", 600, 600),
            (10, "Energia Elétrica", "Despesas Operacionais", 350, 600),
            (15, "Internet Fibra", "Despesas Operacionais", 120, 120),
            (20, "DAS/Simples Nacional", "Impostos", 1000, 3500),
            (5, "Salários Funcionários", "Despesas com Pessoal", 6000, 6000)
        ]

        data_ini = datetime.now() - timedelta(days=365)
        
        # Loop dia a dia
        for d in range(366):
            data_atual = data_ini + timedelta(days=d)
            str_data = data_atual.strftime("%Y-%m-%d")
            
            # --- 1. VENDAS (Receita) ---
            # Mais vendas aos sábados (weekday 5) e menos dias de semana
            if data_atual.weekday() < 5: 
                num_vendas = random.randint(1, 4)
            elif data_atual.weekday() == 5: 
                num_vendas = random.randint(2, 6)
            else: 
                num_vendas = 0 # Domingo fechado

            for _ in range(num_vendas):
                if not clientes_ids or not produtos:
                    continue

                cliente = random.choice(clientes_ids)
                forma_pagto = random.choice(formas_pagamento)
                
                # Inserir Cabeçalho da Venda (Valores zerados inicialmente)
                self.cursor.execute("""
                    INSERT INTO main.vendas 
                    (data_venda, cliente_id, vendedor, status, forma_pagamento_prevista, valor_bruto, desconto_geral, valor_liquido, nota_fiscal, descricao_pedido)
                    VALUES (?, ?, ?, 'Concluido', ?, 0, 0, 0, ?, ?)
                """, (str_data, cliente, fake.first_name(), forma_pagto, f"NF-{random.randint(1000, 9999)}", f"Pedido {fake.word()}"))
                
                venda_id = self.cursor.lastrowid
                
                # Inserir Itens da Venda
                total_bruto = 0
                itens_escolhidos = random.sample(produtos, k=random.randint(1, 3))
                
                for pid, pvenda, pcusto in itens_escolhidos:
                    qtd = random.randint(1, 3)
                    subtotal = pvenda * qtd
                    total_bruto += subtotal
                    
                    # Insert detalhado em itens_venda
                    self.cursor.execute("""
                        INSERT INTO main.itens_venda 
                        (venda_id, produto_id, quantidade, preco_unitario, subtotal, detalhes, variacao, preco_custo, ipi, icms) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                    """, (venda_id, pid, qtd, pvenda, subtotal, "Cor padrão", "Unico", pcusto))
                
                # Cálculo final da venda (com desconto se valor alto)
                desconto = 0
                if total_bruto > 5000: 
                    desconto = total_bruto * 0.05
                total_liquido = total_bruto - desconto

                # Atualiza totais na venda
                self.cursor.execute("""
                    UPDATE main.vendas 
                    SET valor_bruto=?, desconto_geral=?, valor_liquido=? 
                    WHERE id=?
                """, (total_bruto, desconto, total_liquido, venda_id))
                
                # Gerar Conta a Receber vinculada à venda
                destino = random.choice(contas_bancarias)
                self.cursor.execute("""
                    INSERT INTO db_fin.contas_receber 
                    (venda_id, descricao, cliente_id, num_parcela, valor_previsto, valor_recebido, data_vencimento, data_recebimento, status, forma_pagamento, conta_destino)
                    VALUES (?, ?, ?, '1/1', ?, ?, ?, ?, 'Recebido', ?, ?)
                """, (venda_id, f"Recebimento Venda #{venda_id}", cliente, total_liquido, total_liquido, str_data, str_data, forma_pagto, destino))

            # --- 2. DESPESAS FIXAS ---
            for dia_pgto, desc, cat, v_min, v_max in despesas_fixas:
                if data_atual.day == dia_pgto:
                    valor = random.uniform(v_min, v_max)
                    self.cursor.execute("""
                        INSERT INTO db_fin.contas_pagar (descricao, categoria, valor, data_vencimento, data_pagamento, status, forma_pagamento)
                        VALUES (?, ?, ?, ?, ?, 'Pago', 'Boleto')
                    """, (desc, cat, valor, str_data, str_data))

            # --- 3. COMPRAS DE FORNECEDORES (Reposição) ---
            if data_atual.day in [10, 25]: 
                fornec = random.choice(fornecedores_ids) if fornecedores_ids else None
                valor_compra = random.uniform(2000, 5000)
                self.cursor.execute("""
                    INSERT INTO db_fin.contas_pagar (descricao, fornecedor_id, categoria, valor, data_vencimento, data_pagamento, status, forma_pagamento)
                    VALUES (?, ?, 'Fornecedores (CMV)', ?, ?, ?, 'Pago', 'Boleto')
                """, (f"Reposição Estoque", fornec, valor_compra, str_data, str_data))

        self.conn.commit()
        print("✅ Transações financeiras geradas com sucesso!")

if __name__ == "__main__":
    try:
        seeder = DataSeeder()
        seeder.seed_entidades()
        seeder.seed_produtos()
        seeder.seed_movimentacao()
        seeder.conn.close()
        print("\n🚀 Pronto! Banco de dados atualizado e populado.")
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")