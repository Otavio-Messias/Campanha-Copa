# 🏆 Campanha Copa — Dashboard Executivo

Sistema web local para automação de campanhas comerciais de **Pneus** e **Peças & Serviços**.

---

## 📁 Estrutura do Projeto

```
/Campanha Copa
│
├── Dados/
│   ├── Semana 1 Pneus.xlsx
│   ├── Semana 2 Pneus.xlsx
│   ├── Semana 1 Peças e Serviços.xlsx
│   └── ...
│
├── Auxiliares/
│   ├── Vendedores.xlsx
│   ├── Empresas Pneus.xlsx
│   └── Empresas Peças e Serviços.xlsx
│
├── app.py
├── processor.py
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/dashboard.js
├── relatorios/
├── requirements.txt
└── README.md
```

---

## ⚙️ Instalação e Execução

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Iniciar o servidor

```bash
python app.py
```

### 3. Acessar o dashboard

Abra o navegador em:
```
http://localhost:5000
```

---

## 📊 Arquivos Auxiliares

Coloque na pasta `Auxiliares/`:

### `Vendedores.xlsx`
| Código | Nome |
|--------|------|
| 1 | João Silva |
| 2 | Maria Souza |

### `Empresas Pneus.xlsx`
| Cód. Empresa | Nome Empresa |
|---|---|
| 101 | Auto Peças Norte |

### `Empresas Peças e Serviços.xlsx`
| Cód. Empresa | Nome Empresa |
|---|---|
| 201 | Mecânica Rápida |

---

## 📁 Arquivos de Dados (ERP)

Coloque na pasta `Dados/` arquivos exportados do ERP com os seguintes nomes:

- `Semana 1 Pneus.xlsx`
- `Semana 2 Pneus.xlsx`
- `Semana 1 Peças e Serviços.xlsx`
- `Semana 2 Peças e Serviços.xlsx`
- etc.

### Colunas esperadas (por posição de letra):

| Coluna | Campo |
|--------|-------|
| A | Cód. Empresa |
| K | Preço Final |
| M | Data da Venda |
| N | Nota |
| O | Código do Vendedor |
| R | Nome do Cliente |

---

## 🔄 Como adicionar uma nova semana

1. Exporte o arquivo do ERP normalmente.
2. Salve na pasta `Dados/` com o nome correspondente (ex: `Semana 3 Pneus.xlsx`).
3. No dashboard, clique em **[ Atualizar Dados ]**.

O sistema reconhece automaticamente o novo arquivo.

---

## 🚫 Clientes Filtrados Automaticamente

Os seguintes clientes são excluídos automaticamente (correspondência parcial, sem distinção de maiúsculas):

- PRODOESTE
- MERCEDES BENZ
- UBERDIESEL

---

## 📌 Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| 🔄 Atualizar Dados | Reprocessa todos os Excel da pasta Dados |
| 📊 Exportar Excel | Exporta dados tratados + KPIs + comparativo |
| 📄 Exportar PDF | Gera PDF do dashboard atual |
| 🖼️ Baixar PNG | Captura screenshot do dashboard |
| 🔍 Filtro por Tipo | Pneus / Peças e Serviços |
| 📅 Filtro por Semana | Todas / Semana 1 a 6 |
| 📈 Comparativo | Evolução semana a semana |

---

## 🏗️ Tecnologias

- **Backend**: Python + Flask + Pandas
- **Frontend**: HTML5 + CSS3 + JavaScript
- **Gráficos**: Chart.js
- **Tabelas**: DataTables
- **Export**: html2canvas + jsPDF
