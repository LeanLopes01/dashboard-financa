# 🚀 GUIA RÁPIDO - NOVAS FUNCIONALIDADES

## ⚡ Como Usar as Melhorias Implementadas

Este guia mostra como usar as novas funcionalidades adicionadas ao `main.py`.

---

## 1. 📱 Validação de CPF/CNPJ

### Usar o campo com validação visual

```python
# Ao criar um formulário de cadastro:
campo_cpf_cnpj = CPFCNPJLineEdit()
form.addRow("CPF/CNPJ:", campo_cpf_cnpj)

# Ao salvar:
if not campo_cpf_cnpj.is_valid():
    QMessageBox.warning(self, "Atenção", "CPF/CNPJ inválido!")
    return

# Pega o valor sem formatação:
doc = re.sub(r'[^0-9]', '', campo_cpf_cnpj.text())
```

**O que acontece:**
- Usuário digita: `12345678910`
- Campo formata automaticamente: `123.456.789-10`
- Se válido → fica verde ✅
- Se inválido → fica vermelho ❌

---

## 2. 💰 Cálculo de Impostos

### Calcular Simples Nacional

```python
# Ao calcular impostos da empresa:
faturamento_anual = 250000.00  # R$ 250 mil/ano

imposto_anual = calcular_imposto_simples(faturamento_anual)
imposto_mensal = imposto_anual / 12

print(f"Imposto mensal: {formatar_moeda_br(imposto_mensal)}")
# Saída: Imposto mensal: R$ 1.553,33
```

### Calcular margem de lucro

```python
# Ao cadastrar/editar produto:
preco_custo = 50.00
preco_venda = 100.00

margem = calcular_margem_lucro(preco_venda, preco_custo)
print(f"Margem de lucro: {margem}%")
# Saída: Margem de lucro: 50.0%

# Atualizar no banco:
db_context.atualizar_margem_lucro_produto(produto_id)
```

---

## 3. 📱 Geração de PIX

### Gerar QR Code PIX

```python
# Ao finalizar uma venda:
payload = gerar_pix_payload(
    chave="contato@minhaempresa.com",
    valor=150.50,
    nome_beneficiario="Minha Empresa LTDA",
    cidade="Sao Paulo",
    descricao="Pedido #12345"
)

# Gera QR Code
qr_code_base64 = gerar_qr_code_pix(payload)

# Exibir na tela:
dialog = QDialog(self)
dialog.setWindowTitle("PIX - Pagamento")

layout = QVBoxLayout()

# QR Code
label_qr = QLabel()
pixmap = QPixmap()
img_data = base64.b64decode(qr_code_base64.split(',')[1])
pixmap.loadFromData(img_data)
label_qr.setPixmap(pixmap)
layout.addWidget(label_qr)

# Código para copiar
label_codigo = QLabel("Código PIX (Copia e Cola):")
layout.addWidget(label_codigo)

text_codigo = QLineEdit(payload)
text_codigo.setReadOnly(True)
layout.addWidget(text_codigo)

btn_copiar = QPushButton("📋 Copiar Código")
btn_copiar.clicked.connect(lambda: QApplication.clipboard().setText(payload))
layout.addWidget(btn_copiar)

dialog.setLayout(layout)
dialog.exec()
```

**Resultado:**
- Janela com QR Code
- Cliente escaneia e paga
- Ou copia o código PIX

---

## 4. 📄 Geração de Boletos

### Gerar boleto bancário

```python
# Ao criar uma cobrança:
data_vencimento = "2024-03-15"

codigo_barras = gerar_codigo_barras_boleto(
    banco="237",  # Bradesco
    valor=150.50,
    data_vencimento=data_vencimento,
    nosso_numero="12345",
    agencia="1234",
    conta="12345678"
)

linha_digitavel = gerar_linha_digitavel_boleto(codigo_barras)

# Exibir boleto:
dialog = QDialog(self)
dialog.setWindowTitle("Boleto Bancário")

layout = QVBoxLayout()

# Linha digitável
label = QLabel("Linha Digitável:")
layout.addWidget(label)

text = QLineEdit(linha_digitavel)
text.setReadOnly(True)
text.setStyleSheet("font-family: monospace; font-size: 14px;")
layout.addWidget(text)

# Botão copiar
btn = QPushButton("📋 Copiar Linha Digitável")
btn.clicked.connect(lambda: QApplication.clipboard().setText(linha_digitavel))
layout.addWidget(btn)

# Código de barras
label2 = QLabel(f"Código de Barras: {codigo_barras}")
layout.addWidget(label2)

dialog.setLayout(layout)
dialog.exec()
```

---

## 5. 📊 Dashboard com KPIs

### Criar dashboard

```python
class MinhaTelaInicial(QWidget):
    def __init__(self, db_context):
        super().__init__()
        self.db = db_context
        
        layout = QVBoxLayout()
        
        # Título
        titulo = QLabel("📊 Dashboard Gerencial")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(titulo)
        
        # Grid de cards
        grid = QGridLayout()
        
        # Calcula valores
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
        hoje_str = hoje.strftime("%Y-%m-%d")
        
        faturamento = self.db.calcular_faturamento_periodo(inicio_mes, hoje_str)
        despesas = self.db.calcular_despesas_periodo(inicio_mes, hoje_str)
        lucro = faturamento - despesas
        inadimplencia = self.db.obter_inadimplencia_total()
        
        # Cria cards
        card_fat = DashboardCard(
            titulo="Faturamento Mês",
            valor=formatar_moeda_br(faturamento),
            icone="💰",
            cor="#27ae60"
        )
        
        card_desp = DashboardCard(
            titulo="Despesas Mês",
            valor=formatar_moeda_br(despesas),
            icone="💳",
            cor="#e74c3c"
        )
        
        card_lucro = DashboardCard(
            titulo="Lucro Mês",
            valor=formatar_moeda_br(lucro),
            icone="📈",
            cor="#3498db"
        )
        
        card_inad = DashboardCard(
            titulo="Inadimplência",
            valor=formatar_moeda_br(inadimplencia['valor']),
            icone="⚠️",
            cor="#f39c12"
        )
        
        # Adiciona ao grid
        grid.addWidget(card_fat, 0, 0)
        grid.addWidget(card_desp, 0, 1)
        grid.addWidget(card_lucro, 1, 0)
        grid.addWidget(card_inad, 1, 1)
        
        layout.addLayout(grid)
        
        # Botão atualizar
        btn_atualizar = QPushButton("🔄 Atualizar")
        btn_atualizar.clicked.connect(self.atualizar_dashboard)
        layout.addWidget(btn_atualizar)
        
        self.setLayout(layout)
        
        # Guarda referência dos cards para atualizar depois
        self.card_fat = card_fat
        self.card_desp = card_desp
        self.card_lucro = card_lucro
        self.card_inad = card_inad
    
    def atualizar_dashboard(self):
        # Recalcula
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
        hoje_str = hoje.strftime("%Y-%m-%d")
        
        faturamento = self.db.calcular_faturamento_periodo(inicio_mes, hoje_str)
        despesas = self.db.calcular_despesas_periodo(inicio_mes, hoje_str)
        lucro = faturamento - despesas
        inadimplencia = self.db.obter_inadimplencia_total()
        
        # Atualiza cards
        self.card_fat.atualizar_valor(formatar_moeda_br(faturamento))
        self.card_desp.atualizar_valor(formatar_moeda_br(despesas))
        self.card_lucro.atualizar_valor(formatar_moeda_br(lucro))
        self.card_inad.atualizar_valor(formatar_moeda_br(inadimplencia['valor']))
```

---

## 6. 💸 Controle de Inadimplência

### Ver contas vencidas

```python
# Atualiza dias de atraso:
db_context.atualizar_dias_atraso_inadimplencia()

# Pega inadimplência:
inadimplencia = db_context.obter_inadimplencia_total()

print(f"Total inadimplente: {formatar_moeda_br(inadimplencia['valor'])}")
print(f"Quantidade de contas: {inadimplencia['quantidade']}")

# Lista produtos com estoque baixo:
produtos_baixos = db_context.obter_produtos_estoque_baixo()
for produto in produtos_baixos:
    print(f"⚠️ {produto[1]} - Estoque: {produto[3]} {produto[4]}")
```

---

## 7. 📑 Exportação para Excel

### Exportar clientes

```python
# Exportar para Excel:
sucesso, arquivo = db_context.exportar_clientes_excel()

if sucesso:
    QMessageBox.information(
        self,
        "Sucesso",
        f"Clientes exportados com sucesso!\n\nArquivo: {arquivo}"
    )
    
    # Abrir arquivo (opcional):
    import subprocess
    subprocess.Popen(['start', arquivo], shell=True)
else:
    QMessageBox.critical(self, "Erro", f"Erro ao exportar: {arquivo}")
```

### Exportar produtos

```python
sucesso, arquivo = db_context.exportar_produtos_excel()

if sucesso:
    QMessageBox.information(self, "Sucesso", f"Exportado: {arquivo}")
```

---

## 8. 💾 Backup Automático

### Fazer backup em background

```python
class MinhaJanela(QMainWindow):
    def fazer_backup(self):
        # Cria thread de backup
        self.thread_backup = BackupAutomaticoThread(self.db_context)
        
        # Conecta sinais
        self.thread_backup.progresso.connect(self.atualizar_progresso)
        self.thread_backup.concluido.connect(self.backup_concluido)
        
        # Inicia
        self.thread_backup.start()
        
        # Mostra dialog de progresso
        self.dialog_progresso = QDialog(self)
        self.dialog_progresso.setWindowTitle("Backup em andamento...")
        
        layout = QVBoxLayout()
        
        self.label_status = QLabel("Iniciando backup...")
        layout.addWidget(self.label_status)
        
        self.barra_progresso = QProgressBar()
        layout.addWidget(self.barra_progresso)
        
        self.dialog_progresso.setLayout(layout)
        self.dialog_progresso.show()
    
    def atualizar_progresso(self, valor, mensagem):
        self.barra_progresso.setValue(valor)
        self.label_status.setText(mensagem)
    
    def backup_concluido(self, sucesso, resultado):
        self.dialog_progresso.close()
        
        if sucesso:
            QMessageBox.information(
                self,
                "Backup Concluído",
                f"Backup salvo com sucesso!\n\nArquivo: {resultado}"
            )
        else:
            QMessageBox.critical(
                self,
                "Erro no Backup",
                f"Erro ao fazer backup:\n\n{resultado}"
            )
```

---

## 9. 💼 Controle de Comissões

### Registrar comissão de venda

```python
# Ao finalizar uma venda:
venda_id = 123
vendedor = "João Silva"
valor_venda = 1500.00
percentual_comissao = 5.0  # 5%

sucesso = db_context.salvar_comissao(
    venda_id,
    vendedor,
    valor_venda,
    percentual_comissao
)

if sucesso:
    valor_comissao = valor_venda * (percentual_comissao / 100)
    print(f"Comissão registrada: {formatar_moeda_br(valor_comissao)}")
```

### Ver comissões pendentes

```python
# Listar comissões não pagas:
comissoes = db_context.obter_comissoes_pendentes()

for comissao in comissoes:
    print(f"Vendedor: {comissao[2]}")
    print(f"Valor: {formatar_moeda_br(comissao[5])}")
    print(f"Data: {comissao[6]}")
    print("---")

# Pagar comissão:
comissao_id = 1
db_context.pagar_comissao(comissao_id)
```

---

## 10. 📈 Projeção de Fluxo de Caixa

### Projetar próximos 30 dias

```python
# Gera projeção:
projecao = db_context.projecao_fluxo_caixa(dias=30)

# Exibe em tabela:
tabela = QTableWidget()
tabela.setColumnCount(5)
tabela.setHorizontalHeaderLabels([
    "Data", "Entrada", "Saída", "Saldo Dia", "Saldo Acumulado"
])

tabela.setRowCount(len(projecao))

for i, dia in enumerate(projecao):
    tabela.setItem(i, 0, QTableWidgetItem(dia['data']))
    tabela.setItem(i, 1, QTableWidgetItem(formatar_moeda_br(dia['entrada'])))
    tabela.setItem(i, 2, QTableWidgetItem(formatar_moeda_br(dia['saida'])))
    tabela.setItem(i, 3, QTableWidgetItem(formatar_moeda_br(dia['saldo_dia'])))
    tabela.setItem(i, 4, QTableWidgetItem(formatar_moeda_br(dia['saldo_acumulado'])))
    
    # Cor no saldo acumulado
    if dia['saldo_acumulado'] < 0:
        tabela.item(i, 4).setBackground(QColor("#fadbd8"))  # Vermelho claro
    else:
        tabela.item(i, 4).setBackground(QColor("#e8f8f5"))  # Verde claro
```

---

## 11. 📋 Geração de DRE

### Gerar DRE do mês

```python
# Define período:
hoje = datetime.now().date()
inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
fim_mes = hoje.strftime("%Y-%m-%d")

# Gera DRE:
dre = db_context.gerar_dre(inicio_mes, fim_mes)

if dre:
    # Exibe relatório:
    relatorio = f"""
    DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO
    Período: {inicio_mes} a {fim_mes}
    
    (+) Receita Bruta:          {formatar_moeda_br(dre['receita_bruta'])}
    (-) Impostos:               {formatar_moeda_br(dre['impostos'])}
    (=) Receita Líquida:        {formatar_moeda_br(dre['receita_liquida'])}
    
    (-) CPV:                    {formatar_moeda_br(dre['cpv'])}
    (=) Lucro Bruto:            {formatar_moeda_br(dre['lucro_bruto'])}
        Margem Bruta:           {dre['margem_bruta']:.2f}%
    
    (-) Despesas Operacionais:  {formatar_moeda_br(dre['despesas_operacionais'])}
    
    (=) LUCRO LÍQUIDO:          {formatar_moeda_br(dre['lucro_liquido'])}
        Margem Líquida:         {dre['margem_liquida']:.2f}%
    """
    
    QMessageBox.information(self, "DRE", relatorio)
```

---

## 🎓 DICAS IMPORTANTES

### 1. Formatar valores brasileiros

```python
# Use sempre:
valor_formatado = formatar_moeda_br(1234.56)
# Retorna: "R$ 1.234,56"
```

### 2. Validar antes de salvar

```python
if campo_cpf_cnpj.is_valid():
    # Salvar
else:
    QMessageBox.warning(self, "Erro", "CPF/CNPJ inválido!")
```

### 3. Atualizar margens automaticamente

```python
# Sempre que alterar preço:
db_context.atualizar_margem_lucro_produto(produto_id)
```

### 4. Atualizar inadimplência diariamente

```python
# No início do dia:
db_context.atualizar_dias_atraso_inadimplencia()
```

---

## 🚨 TROUBLESHOOTING

### Erro ao gerar QR Code

```python
# Instalar biblioteca:
pip install qrcode[pil]
```

### Erro ao exportar Excel

```python
# Instalar biblioteca:
pip install openpyxl
```

### Validação não funciona

```python
# Verificar imports:
import re
from datetime import datetime
```

---

## 📞 SUPORTE

Se encontrar problemas:

1. Verifique os imports no início do arquivo
2. Instale as dependências necessárias
3. Verifique se o banco de dados foi criado corretamente
4. Execute `db_context.create_tables()` novamente se necessário

---

**Pronto para usar! 🎉**

Todas essas funcionalidades estão integradas no `main.py` e prontas para uso imediato.
