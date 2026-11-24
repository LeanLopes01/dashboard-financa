import sqlite3
import os
import random
import shutil
from datetime import datetime, timedelta
from faker import Faker

# Configuração de caminhos
DATA_DIR = "data"
DB_VENDAS = os.path.join(DATA_DIR, "vendas.db")
DB_CLIENTES = os.path.join(DATA_DIR, "clientes.db")
DB_PRODUTOS = os.path.join(DATA_DIR, "produtos.db")
DB_FINANCEIRO = os.path.join(DATA_DIR, "financeiro.db")

fake = Faker('pt_BR')

class DataSeeder:
    def __init__(self):
        self.ensure_directory()
        # Conecta ao banco principal (vendas)
        self.conn = sqlite3.connect(DB_VENDAS)
        self.cursor = self.conn.cursor()
        
        self.attach_databases()
        self.create_tables()  # CRUCIAL: Cria as tabelas antes de limpar/popular
        self.clean_database()

    def ensure_directory(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def attach_databases(self):
        # Garante que os arquivos existam para o ATTACH
        for db in [DB_CLIENTES, DB_PRODUTOS, DB_FINANCEIRO]:
            sqlite3.connect(db).close()
            
        self.cursor.execute(f"ATTACH DATABASE '{DB_CLIENTES}' AS db_cli")
        self.cursor.execute(f"ATTACH DATABASE '{DB_PRODUTOS}' AS db_prod")
        self.cursor.execute(f"ATTACH DATABASE '{DB_FINANCEIRO}' AS db_fin")

    def create_tables(self):
        print("🛠️ Verificando/Criando estrutura de tabelas...")
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

        # 3. Vendas
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, data_venda DATE NOT NULL, cliente_id INTEGER, 
            vendedor TEXT, valor_bruto REAL, desconto_geral REAL, valor_liquido REAL,
            status TEXT, nota_fiscal TEXT, forma_pagamento_prevista TEXT, obs TEXT)''')

        # 3.1 Itens da Venda
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS main.itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, venda_id INTEGER, produto_id INTEGER,
            quantidade REAL, preco_unitario REAL, subtotal REAL,
            FOREIGN KEY(venda_id) REFERENCES vendas(id))''')

        # 4. Contas a Pagar
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL, fornecedor_id INTEGER,
            categoria TEXT, valor REAL NOT NULL, data_vencimento DATE, data_pagamento DATE,
            status TEXT, forma_pagamento TEXT, obs TEXT)''')

        # 5. Contas a Receber
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS db_fin.contas_receber (
            id INTEGER PRIMARY KEY AUTOINCREMENT, venda_id INTEGER, descricao TEXT NOT NULL,
            cliente_id INTEGER, num_parcela TEXT, valor_previsto REAL NOT NULL,
            valor_recebido REAL, data_vencimento DATE, data_recebimento DATE,
            status TEXT, forma_pagamento TEXT, conta_destino TEXT, comprovante_path TEXT, obs TEXT)''')
        self.conn.commit()

    def clean_database(self):
        print("🧹 Limpando dados antigos...")
        tab_list = [
            "main.itens_venda", "main.vendas", 
            "db_fin.contas_receber", "db_fin.contas_pagar",
            "db_cli.entidades", "db_prod.produtos"
        ]
        for table in tab_list:
            self.cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()

    def seed_clientes(self, qtd=50):
        print(f"👥 Gerando {qtd} clientes...")
        for _ in range(qtd):
            tipo = random.choice(['Física', 'Jurídica'])
            nome = fake.name() if tipo == 'Física' else fake.company()
            self.cursor.execute("""
                INSERT INTO db_cli.entidades (tipo_pessoa, nome_razao, cpf_cnpj, cidade, uf, data_registro)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tipo, nome, fake.cpf() if tipo == 'Física' else fake.cnpj(), fake.city(), fake.state_abbr(), fake.date_this_year()))
        self.conn.commit()

    def seed_produtos(self):
        print("📦 Gerando catálogo de produtos...")
        produtos = [
            ("NOTE001", "Notebook Dell", "Eletrônicos", 2500, 3800),
            ("MOUSE01", "Mouse Logi", "Acessórios", 45, 95),
            ("TECL002", "Teclado Mecânico", "Acessórios", 150, 320),
            ("MONIT03", "Monitor 24", "Eletrônicos", 600, 890),
            ("SSD006",  "SSD 480GB", "Hardware", 180, 350),
        ]
        for sku, nome, cat, custo, venda in produtos:
            self.cursor.execute("""
                INSERT INTO db_prod.produtos (sku, nome, categoria, preco_custo, preco_venda, estoque_atual, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sku, nome, cat, custo, venda, random.randint(10, 50), fake.date_this_year()))
        self.conn.commit()

    def seed_movimentacao_anual(self):
        print("📅 Simulando 1 ano de operações...")
        self.cursor.execute("SELECT id FROM db_cli.entidades")
        clientes = [r[0] for r in self.cursor.fetchall()]
        self.cursor.execute("SELECT id, preco_venda FROM db_prod.produtos")
        produtos = self.cursor.fetchall()

        data_ini = datetime.now() - timedelta(days=365)
        for d in range(365):
            atual = data_ini + timedelta(days=d)
            str_d = atual.strftime("%Y-%m-%d")

            # Vendas (2 por dia em média)
            for _ in range(random.randint(1, 3)):
                c_id = random.choice(clientes)
                p_id, preco = random.choice(produtos)
                qtd = random.randint(1, 2)
                total = preco * qtd
                
                self.cursor.execute("INSERT INTO main.vendas (data_venda, cliente_id, status, valor_liquido) VALUES (?, ?, 'Concluido', ?)", (str_d, c_id, total))
                v_id = self.cursor.lastrowid
                self.cursor.execute("INSERT INTO main.itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?)", (v_id, p_id, qtd, preco, total))
                self.cursor.execute("INSERT INTO db_fin.contas_receber (venda_id, descricao, valor_previsto, valor_recebido, data_recebimento, status) VALUES (?, 'Venda', ?, ?, ?, 'Recebido')", (v_id, total, total, str_d))

            # Despesa Mensal (Aluguel no dia 10)
            if atual.day == 10:
                self.cursor.execute("INSERT INTO db_fin.contas_pagar (descricao, categoria, valor, data_pagamento, status) VALUES ('Aluguel', 'Operacional', 2000, ?, 'Pago')", (str_d,))

        self.conn.commit()

if __name__ == "__main__":
    seeder = DataSeeder()
    seeder.seed_clientes()
    seeder.seed_produtos()
    seeder.seed_movimentacao_anual()
    seeder.conn.close()
    print("\n✅ Sucesso! Tabelas criadas e dados inseridos.")