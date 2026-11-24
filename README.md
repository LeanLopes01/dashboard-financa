# Dashboard de Gestão Financeira Desktop

Aplicativo desktop moderno e intuitivo desenvolvido em **Python** e **PyQt6** para gestão financeira pessoal e empresarial, com suporte a relatórios visuais dinâmicos, controle de fluxo de caixa e autenticação segura com **KeyAuth**.

---

## 📸 Demonstração Visual

O projeto inclui telas de demonstração completas na pasta [`screenshots/`](screenshots/):

| Visão Geral | Gráficos Analíticos | Gestão de Categorias |
| :---: | :---: | :---: |
| Painel com saldo, receitas e despesas | Distribuição por categoria e linha do tempo | Cadastro ágil de entradas e saídas |

---

## 🛠️ Tecnologias Utilizadas

- **Interface Gráfica:** PyQt6 (Design moderno em Dark Mode com widgets personalizados)
- **Linguagem:** Python 3.10+
- **Autenticação & Licenciamento:** [KeyAuth](https://keyauth.cc/) API Client (validação de licença, login de usuário e integridade de checksum)
- **Criptografia:** `cryptography.fernet` (para salvar credenciais de sessão local de forma segura)
- **Requisições & Rede:** `requests`, `urllib3`

---

## 📂 Estrutura do Projeto

```text
dashboard-financa/
├── screenshots/                # Capturas de tela do sistema em execução
├── Versão Local/
│   ├── v0.0.2/                 # Versão mais recente e estável do sistema
│   │   ├── classes/            # Componentes visuais e modelos de dados
│   │   ├── data/               # Estruturas e persistência local
│   │   ├── images/             # Ícones e elementos visuais da interface
│   │   ├── input.py            # Validação e processamento de entradas
│   │   ├── keyauth.py          # Wrapper de integração com a API do KeyAuth
│   │   └── main.py             # Ponto de entrada da aplicação PyQt6
│   ├── v0.0.1/                 # Versão legada inicial
│   └── outra/                  # Protótipos alternativos
├── .env.example                # Configurações de autenticação e API
├── .gitignore                  # Arquivos de sessão, caches e venvs ignorados
└── README.md                   # Documentação do projeto
```

---

## 🚀 Como Executar

### 1. Pré-requisitos

Instale as dependências necessárias:
```bash
pip install PyQt6 requests cryptography
```

*(No Windows, também é recomendável `pywin32` para obtenção do identificador de máquina).*

### 2. Configurar Autenticação (Opcional/KeyAuth)

Copie o `.env.example` e configure as credenciais da sua aplicação KeyAuth:
```bash
cp .env.example .env
```
Ou defina a variável no ambiente:
```bash
export KEYAUTH_OWNER_ID="seu-owner-id"
```

### 3. Iniciar o Aplicativo

Navegue até a versão mais recente (`v0.0.2`) e execute:
```bash
cd "Versão Local/v0.0.2"
python main.py
```

- Será exibida a tela de login integrada ao KeyAuth (ou login direto se a sessão estiver salva).
- Após autenticado, o painel financeiro principal será carregado com dashboards e formulários de lançamentos.
