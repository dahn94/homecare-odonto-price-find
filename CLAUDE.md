# CLAUDE.md — Basis Odontologia Domiciliar · Precificação v3

## Visão Geral

Aplicação desktop em **Python + CustomTkinter** para precificação profissional de atendimentos odontológicos domiciliares na região de Blumenau/SC (Blumenau, Gaspar, Pomerode, Indaial, Timbó).

### Filosofia: "Precificador de 10 segundos"

A tela principal é **ÚNICA e minimalista**: a usuária escolhe um (ou mais) procedimento, digita a distância em km até o paciente, opcionalmente ajusta o regime tributário, clica em **Calcular**, e o app mostra os 4 valores finais (Pix, 7x, 10x, 12x) prontos pra cobrar. Em seguida, gera um PDF com esses cenários para enviar ao paciente.

Toda a complexidade de cálculo (materiais, hora clínica, deslocamento, custos fixos, retrabalho, impostos, maquineta) **acontece nos bastidores** usando os parâmetros do `basis.db`. A usuária não vê camada DEFAULTa no dia a dia — só o resultado.

A única outra tela do app é **⚙️ Configurações**, escondida atrás de um ícone discreto, usada esporadicamente pra ajustar parâmetros (combustível subiu, novo procedimento, reajuste anual). Sem sidebar de 6 abas, sem painel financeiro, sem orçamento por paciente, sem histórico complexo.

A composição interna do preço (não exibida ao usuário, mas presente no cálculo) é:
**Preço Domiciliar + Hora Clínica + Deslocamento + Custos Fixos + Retrabalho + Impostos + Maquineta = TOTAL**

---

## Stack Técnica

- **Linguagem**: Python 3.10+
- **UI**: `customtkinter` (visual moderno sobre Tkinter)
- **Persistência**: SQLite local (`basis.db`) — único arquivo com tabelas para configurações, procedimentos, referência CBHPO oficial e histórico
- **PDF**: `reportlab` para geração de orçamentos em PDF
- **Busca**: fuzzy search nos procedimentos com `thefuzz`
- **Logo**: arquivo `assets/logo_basis.png` exibido no header e nos PDFs
- **Empacotamento**: PyInstaller para gerar `.exe` distribuível

---

## Identidade Visual

### Paleta de Cores

```python
COLORS = {
    "bg_primary":     "#0F1B2D",   # Azul escuro profundo — fundo principal
    "bg_secondary":   "#1A2B45",   # Azul escuro — cards e painéis
    "bg_card":        "#223553",   # Azul médio — cards internos
    "accent":         "#00BFA6",   # Verde-turquesa — botões primários, destaques, totais
    "accent_hover":   "#00A68E",   # Verde-turquesa escuro — hover
    "accent_warm":    "#FF6B6B",   # Coral — alertas, valores negativos, urgências
    "gold":           "#FFD700",   # Dourado — campos editáveis (ref. amarelo planilha)
    "text_primary":   "#FFFFFF",   # Branco — texto principal
    "text_secondary": "#A0B4C8",   # Azul-cinza claro — labels
    "text_muted":     "#5A7A96",   # Azul-cinza — texto desabilitado
    "border":         "#2A4060",   # Borda sutil dos cards
    "success":        "#4CAF50",   # Verde — valores calculados (ref. verde planilha)
    "purple":         "#B388FF",   # Roxo claro — preços NEE (ref. roxo planilha)
    "input_bg":       "#2A3F5F",   # Fundo dos inputs
    "warning":        "#FFA726",   # Laranja — avisos de reajuste, validade
    "error":          "#EF5350",   # Vermelho — cálculo errado, perda
}
```

### Tipografia

```python
FONTS = {
    "title":     ("Segoe UI", 22, "bold"),
    "subtitle":  ("Segoe UI", 16, "bold"),
    "heading":   ("Segoe UI", 13, "bold"),
    "body":      ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "small":     ("Segoe UI", 10),
    "mono":      ("Consolas", 13),        # valores monetários
    "mono_lg":   ("Consolas", 18, "bold"), # total final
}
```

### Regras Visuais

1. **Logo Basis** no topo esquerdo de todas as telas (~120×40px), carregada de `assets/logo_basis.png`.
2. **Campos editáveis** têm borda dourada (`gold`).
3. **Valores calculados** aparecem em verde (`success`).
4. **Valores NEE** aparecem em roxo (`purple`).
5. **Total final** usa `accent` (verde-turquesa) em fonte `mono_lg`.
6. **Cálculo errado / perda** usa `error` (vermelho) — ex: comparativo de fórmula errada da maquineta.
7. **Avisos de reajuste/validade** usam `warning` (laranja).
8. **Cards** com cantos arredondados (corner_radius=12).
9. **Sidebar** esquerda: ⚙️ Configurações, 📋 Precificação, 🧾 Orçamento, 💳 Maquineta, 📊 Painel, 📄 Histórico.
10. **Scrollable frames** para lista de procedimentos.
11. **Tooltips** nos campos explicando cada variável.

---

## Estrutura do Projeto

```
basis-precificacao/
├── main.py
├── basis.db                 # SQLite: config, procedimentos, cbhpo_referencia, historico
├── seeds/
│   └── cbhpo_2024.sql       # Seed inicial da tabela cbhpo_referencia (atualizável)
├── assets/
│   └── logo_basis.png
├── src/
│   ├── app.py               # Classe principal CTk — orquestra a tela única + config
│   ├── theme.py             # COLORS, FONTS, helpers de estilo
│   ├── views/
│   │   ├── precificador_view.py  # ÚNICA tela principal: procedimento + km → preço final
│   │   └── config_view.py        # Tela de configurações (acessada por ícone ⚙️)
│   ├── widgets/
│   │   ├── procedimento_picker.py  # Busca/seleção fuzzy de procedimentos
│   │   ├── input_field.py
│   │   └── currency_label.py
│   ├── db/
│   │   ├── schema.sql            # DDL das tabelas SQLite
│   │   ├── connection.py         # Singleton de conexão sqlite3
│   │   ├── migrations.py         # Aplicação de seeds e atualização da CBHPO
│   │   └── repositories.py       # CRUD: procedimentos, config, cbhpo, historico
│   ├── models/
│   │   ├── procedimento.py
│   │   ├── orcamento.py
│   │   └── config.py
│   ├── calc/
│   │   ├── deslocamento.py       # custo por km a partir de config.veiculo + tempo
│   │   ├── maquineta.py          # fórmula inversa valor/(1-taxa)
│   │   ├── impostos.py           # alíquota efetiva por regime (PF/MEI/Simples/custom)
│   │   ├── custos_fixos.py       # rateio por atendimento
│   │   └── precificador.py       # ORQUESTRADOR: junta tudo e devolve cenários (Pix, 7x, 10x, 12x)
│   └── export/
│       └── pdf_generator.py      # PDF minimalista: cenários de pagamento
```

---

## Modelo de Dados

### Persistência: SQLite (`basis.db`)

Toda a aplicação usa um único arquivo SQLite. O schema completo fica em `src/db/schema.sql` e é aplicado na primeira execução. Nada é hardcoded em código — todos os valores vêm do banco e podem ser editados pela usuária.

### 1. Tabela `config` — chave/valor tipado

Em vez de uma tabela rígida com 30 colunas, configurações ficam em chave/valor — assim adicionar um parâmetro novo não exige migração.

```sql
CREATE TABLE config (
  chave         TEXT PRIMARY KEY,
  valor         TEXT NOT NULL,            -- serializado (número, bool ou JSON)
  tipo          TEXT NOT NULL,            -- 'float' | 'int' | 'bool' | 'string' | 'json'
  grupo         TEXT NOT NULL,            -- 'veiculo' | 'tempo' | 'maquineta' | 'impostos' | ...
  descricao     TEXT,                     -- texto exibido como tooltip na UI
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Seed inicial** (mesmos defaults da v anterior em JSON, agora linhas):

| chave | valor | tipo | grupo |
|---|---|---|---|
| `veiculo.consumo_km_l` | `12.0` | float | veiculo |
| `veiculo.preco_combustivel_litro` | `6.10` | float | veiculo |
| `veiculo.custo_manutencao_km` | `0.15` | float | veiculo |
| `tempo.valor_hora_clinica` | `150.00` | float | tempo |
| `tempo.velocidade_media_km_h` | `40` | int | tempo |
| `deslocamento.margem_lucro` | `0.30` | float | deslocamento |
| `maquineta.nome` | `modoPAG` | string | maquineta |
| `maquineta.taxas` | `{"pix":0,"7x":0.08,"8x":0.088,"10x":0.10,"12x":0.1151}` | json | maquineta |
| `impostos.regime` | `PF` | string | impostos |
| `impostos.aliquota_ir_percent` | `0.275` | float | impostos |
| `impostos.iss_percent` | `0.05` | float | impostos |
| `impostos.inss_percent` | `0.11` | float | impostos |
| `impostos.aplicar` | `false` | bool | impostos |
| `domiciliar.acrescimo_padrao` | `1.00` | float | domiciliar |
| `domiciliar.acrescimo_nee` | `0.25` | float | domiciliar |
| `meta.atendimentos_estimados_mes` | `40` | int | meta |
| `meta.faturamento_liquido_desejado_mes` | `10000.00` | float | meta |
| `reajuste.indice_anual_percent` | `0.045` | float | reajuste |
| `reajuste.ultimo` | `2024-01-01` | string | reajuste |
| `reajuste.alerta_meses` | `6` | int | reajuste |
| `descontos.segundo` | `0.10` | float | descontos |
| `descontos.terceiro` | `0.15` | float | descontos |
| `descontos.quarto_mais` | `0.20` | float | descontos |
| `retrabalho.margem_percent` | `0.05` | float | retrabalho |

### 2. Tabela `custos_fixos` — uma linha por item rateado

```sql
CREATE TABLE custos_fixos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  nome          TEXT NOT NULL,
  valor_mensal  REAL NOT NULL,
  ativo         INTEGER NOT NULL DEFAULT 1
);
```

Seed: CRO rateado (50), seguro RC (80), contabilidade (150), depreciação equipamento (200), cursos (100), manutenção autoclave (50).

### 3. Tabela `zonas` — atendimento por região

```sql
CREATE TABLE zonas (
  id                       INTEGER PRIMARY KEY AUTOINCREMENT,
  nome                     TEXT NOT NULL,
  distancia_ida_volta_km   REAL NOT NULL,
  referencia               TEXT,
  ativo                    INTEGER NOT NULL DEFAULT 1
);
```

Seed: Blumenau centrais (10), Blumenau afastados (20), Gaspar (30), Indaial (36), Pomerode (44), Timbó (50).

### 4. Tabela `cbhpo_referencia` — valores oficiais (atualizável)

Esta tabela é a **fonte da verdade da CBHPO oficial**, separada dos valores praticados pela Basis. Atualizada manualmente hoje (via importação do `seeds/cbhpo_AAAA.sql`); no futuro, uma API do CFO/CNCC pode rodar um upsert aqui sem afetar a tabela `procedimentos`.

```sql
CREATE TABLE cbhpo_referencia (
  codigo_cbhpo  TEXT PRIMARY KEY,         -- ex: '81000030'
  nome_oficial  TEXT NOT NULL,
  categoria     TEXT,
  valor_oficial REAL NOT NULL,
  versao        TEXT NOT NULL,            -- ex: '2024' — permite ter múltiplas versões coexistindo
  fonte         TEXT,                     -- ex: 'CFO/CNCC 2024'
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_cbhpo_versao ON cbhpo_referencia(versao);
```

### 5. Tabela `procedimentos` — valores praticados pela Basis

```sql
CREATE TABLE procedimentos (
  id                          INTEGER PRIMARY KEY AUTOINCREMENT,
  nome                        TEXT NOT NULL,
  categoria                   TEXT NOT NULL,
  codigo_cbhpo                TEXT,                          -- NULL se não existe na CBHPO
  valor_atual                 REAL NOT NULL,                 -- valor praticado pela Basis (editável)
  tempo_estimado_min          INTEGER NOT NULL,
  valor_hora_clinica_override REAL,                          -- NULL = usa global
  custo_material              REAL NOT NULL DEFAULT 0,
  custo_laboratorio           REAL NOT NULL DEFAULT 0,
  fator_complexidade_min      REAL NOT NULL DEFAULT 1.0,
  fator_complexidade_max      REAL NOT NULL DEFAULT 1.0,
  ativo                       INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY (codigo_cbhpo) REFERENCES cbhpo_referencia(codigo_cbhpo)
);

CREATE INDEX idx_proc_categoria ON procedimentos(categoria);
CREATE INDEX idx_proc_codigo ON procedimentos(codigo_cbhpo);
```

**Cálculo do delta vs CBHPO (view, não armazenado):**

```sql
CREATE VIEW v_procedimentos_com_delta AS
SELECT
  p.*,
  c.valor_oficial         AS valor_cbhpo_oficial,
  c.versao                AS cbhpo_versao,
  CASE
    WHEN c.valor_oficial IS NULL OR c.valor_oficial = 0 THEN NULL
    ELSE (p.valor_atual - c.valor_oficial) / c.valor_oficial
  END                     AS delta_percent
FROM procedimentos p
LEFT JOIN cbhpo_referencia c ON c.codigo_cbhpo = p.codigo_cbhpo;
```

Procedimentos sem `codigo_cbhpo` (ou cujo código não exista na referência) retornam `valor_cbhpo_oficial = NULL` e `delta_percent = NULL` — a UI omite a comparação nesses casos.

### 6. Tabela `historico` — toda precificação realizada

**Todo cálculo gera um registro em `historico`** — não só os exportados em PDF. O objetivo é ter rastreio completo: quem foi o cliente, quando, qual o resultado.

```sql
CREATE TABLE historico (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  data_hora           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),  -- ISO 8601 local
  cliente_nome        TEXT NOT NULL,           -- obrigatório: prompt na hora de calcular
  cliente_observacao  TEXT,                    -- opcional: telefone, endereço, anotação
  distancia_km        REAL NOT NULL,
  is_nee              INTEGER NOT NULL DEFAULT 0,
  regime_aplicado     TEXT NOT NULL,           -- 'PF' | 'MEI' | 'SIMPLES' | 'DEFAULT' | 'CUSTOM'
  aliquota_aplicada   REAL NOT NULL,           -- alíquota efetiva no momento
  total_a_vista       REAL NOT NULL,
  total_cartao_7x     REAL NOT NULL,
  total_cartao_10x    REAL NOT NULL,
  total_cartao_12x    REAL NOT NULL,
  pdf_gerado          INTEGER NOT NULL DEFAULT 0,  -- 1 se exportou PDF, 0 se só calculou
  payload_json        TEXT NOT NULL            -- snapshot: procedimentos, decomposição interna, config
);

CREATE INDEX idx_historico_data ON historico(data_hora DESC);
CREATE INDEX idx_historico_cliente ON historico(cliente_nome);
```

**Fluxo de gravação na tela principal:**

1. Usuária preenche procedimento(s) + km + clica **Calcular**
2. Antes de mostrar o resultado, app pede **"Cliente: ____"** (campo obrigatório, modal pequeno ou inline)
3. Salva imediatamente em `historico` com `pdf_gerado = 0`
4. Mostra os 4 cenários
5. Se ela clicar em **Gerar PDF**, atualiza o registro pra `pdf_gerado = 1`

**Por que pedir o nome antes do resultado**, e não depois: garante que **todo cálculo é rastreável**, mesmo que ela não emita PDF. Sem isso, ela poderia calcular dezenas de "experimentos" e perder histórico de cobrança real. O nome pode ser livre — "João da Silva", "Família Klein", "Sr. Curt - Pomerode" — não precisa cadastro prévio.

### 7. Modelo Python (`Procedimento`)

```python
@dataclass
class Procedimento:
    id: int
    nome: str
    categoria: str
    codigo_cbhpo: str | None              # None se procedimento não existe na CBHPO
    valor_atual: float                    # valor praticado pela Basis
    tempo_estimado_min: int
    valor_hora_clinica_override: float | None
    custo_material: float
    custo_laboratorio: float
    fator_complexidade_min: float
    fator_complexidade_max: float

    # Carregado via JOIN com cbhpo_referencia (None se sem código):
    valor_cbhpo_oficial: float | None
    cbhpo_versao: str | None
    delta_percent: float | None           # (valor_atual - oficial) / oficial
```

### 8. UI: indicador de delta vs CBHPO

Quando a usuária edita `valor_atual` na tela de configurações de procedimentos, o app mostra ao lado:

```
Restauração resina Classe I       Código CBHPO: 85100196
CBHPO 2024 oficial: R$ 202,50
Seu valor:          [R$ 280,00]   ▲ +38,3%
```

- ▲ verde (`success`) se acima do oficial
- ▼ vermelho (`error`) se abaixo (sinal de prejuízo)
- = cinza se igual
- Sem indicador se `codigo_cbhpo` for NULL

E um indicador agregado no topo: *"Sua tabela está em média +X% acima da CBHPO 2024 (Y de Z procedimentos comparáveis)."*

### 9. Atualização da referência CBHPO

- **Hoje (manual)**: nas configurações há um botão *"Atualizar referência CBHPO"* que executa `seeds/cbhpo_AAAA.sql` (UPSERT em `cbhpo_referencia`). Os valores em `procedimentos.valor_atual` **não são tocados** — a usuária decide se quer reajustar.
- **Futuro (API)**: módulo `src/db/cbhpo_sync.py` busca CBHPO atualizada do CFO/CNCC e roda o mesmo UPSERT. Mesmo princípio: nunca sobrescreve `valor_atual`.

### 10. Modelo Python (`Zona`)

```python
@dataclass
class Zona:
    id: int
    nome: str                        # ex: "Blumenau — bairros centrais"
    distancia_ida_volta_km: float    # ex: 10
    referencia: str                  # ex: "Até 5 km do ponto base"
    # Calculados em runtime:
    custo_veiculo: float
    custo_tempo: float
    custo_total_real: float
    taxa_ao_paciente: float          # com margem aplicada
```

### 11. Modelo do orçamento simplificado

A tela única recebe a entrada mínima e devolve os 4 cenários de pagamento. Não há "item de orçamento" com 6 colunas visíveis — tudo é interno.

```python
@dataclass
class EntradaPrecificacao:
    procedimentos: list[tuple[int, int]]   # [(procedimento_id, quantidade), ...]
    distancia_km: float                    # ida + volta — usuária digita direto
    is_nee: bool                           # checkbox
    regime_override: str | None            # 'PF' | 'MEI' | 'SIMPLES' | 'DEFAULT' | 'CUSTOM' | None
    aliquota_override: float | None        # só se regime_override == 'CUSTOM'

@dataclass
class CenarioPagamento:
    forma: str           # 'Pix' | 'Cartão 7x' | 'Cartão 10x' | 'Cartão 12x'
    total: float         # valor final cobrado do paciente
    parcela: float | None  # None se à vista

@dataclass
class ResultadoPrecificacao:
    entrada: EntradaPrecificacao

    # Decomposição interna (não exibida ao usuário, mas guardada no histórico):
    custo_procedimentos: float    # Σ valor_atual × acréscimo domiciliar (× NEE se aplicável)
    custo_hora_clinica: float     # Σ hora_clinica × tempo
    custo_materiais_lab: float    # Σ material + lab
    custo_deslocamento: float     # cobrado 1x pela visita
    custo_fixos_rateado: float    # parcela do mês / atendimentos estimados
    margem_retrabalho: float      # 5% do subtotal
    valor_impostos: float         # alíquota efetiva sobre o subtotal
    subtotal_a_vista: float       # base antes da maquineta

    cenarios: list[CenarioPagamento]   # Pix, 7x, 10x, 12x
```

O `precificador.py` é o **único orquestrador**: recebe `EntradaPrecificacao`, lê tudo do banco, e devolve `ResultadoPrecificacao`. Toda a lógica das demais camadas (`deslocamento.py`, `maquineta.py`, etc.) é chamada por ele.

---

## Tabela de Procedimentos

Existem **dois seeds independentes** que populam o SQLite na primeira execução. Os arquivos vivem em `seeds/` e são versionados:

1. **`seeds/cbhpo_2024.sql`** — popula `cbhpo_referencia` com os valores oficiais do CFO/CNCC. **Imutável** durante o uso normal. Atualizado manualmente quando sair uma nova versão (CBHPO 2025, etc.) e re-aplicado via UPSERT.
2. **`seeds/procedimentos_basis.sql`** — popula `procedimentos` com o catálogo da Basis. Cada linha tem `valor_atual` (preço praticado) + FK opcional para `cbhpo_referencia.codigo_cbhpo`. A usuária edita `valor_atual` na UI e o app calcula o delta vs CBHPO em tempo real.

Procedimentos criados pela Basis que não existem na CBHPO oficial (ex: "Profilaxia e raspagem premium", "Restaurações estéticas") ficam com `codigo_cbhpo = NULL` — a comparação simplesmente não aparece.

Convenções dos seeds abaixo:
- Acréscimo domiciliar padrão 100%, NEE +25% (vêm da tabela `config`).
- `tempo_min`, `material`, `lab` e `hora_clinica_override` são **defaults editáveis** no banco — a usuária pode ajustar a qualquer momento.
- `hora_clinica_override` em branco = usa o global de `config.tempo.valor_hora_clinica`.

---

### Seed 1 — `cbhpo_referencia` (versão `2024`, fonte: CFO/CNCC)

Tabela deduplicada por código (cada `codigo_cbhpo` aparece **uma única vez**, mesmo que vários procedimentos da Basis o reutilizem).

| Código | Nome Oficial CBHPO | Categoria | Valor Oficial (R$) |
|---|---|---|---|
| 81000014 | Condicionamento em odontologia | Consulta e Diagnóstico | 107,60 |
| 81000030 | Consulta odontológica | Consulta e Diagnóstico | 133,00 |
| 81000065 | Consulta odontológica inicial | Consulta e Diagnóstico | 133,00 |
| 81000189 | Diagnóstico e planejamento de tratamento | Consulta e Diagnóstico | 266,00 |
| 81000383 | Radiografia oclusal | Diagnóstico por imagem | 57,40 |
| 81000405 | Radiografia panorâmica | Diagnóstico por imagem | 88,80 |
| 81000421 | Radiografia periapical | Diagnóstico por imagem | 23,32 |
| 81000510 | Tomografia cone beam (CBCT) | Diagnóstico por imagem | 587,40 |
| 82000506 | Controle pós-operatório | Cirurgia | 133,00 |
| 82000816 | Exodontia a retalho | Cirurgia | 249,60 |
| 82000859 | Exodontia — raiz residual | Cirurgia | 208,50 |
| 82000875 | Exodontia — dente permanente | Cirurgia | 208,50 |
| 82001022 | Drenagem de abscesso — extra-oral | Cirurgia | 205,50 |
| 82001030 | Drenagem de abscesso — intra-oral | Cirurgia | 205,50 |
| 82001197 | Redução simples de luxação da ATM | ATM / Urgência | 127,80 |
| 82001286 | Exodontia — dente incluso / impactado | Cirurgia | 515,60 |
| 82001294 | Exodontia — dente semi-incluso | Cirurgia | 515,60 |
| 82001642 | Tratamento conservador de luxação da ATM | ATM / Urgência | 142,00 |
| 82001650 | Tratamento de alveolite | Cirurgia | 143,80 |
| 85100099 | Restauração amálgama — Classe I (1 face) | Dentística | 177,10 |
| 85100102 | Restauração amálgama — Classe II (2 faces) | Dentística | 205,50 |
| 85100110 | Restauração amálgama — Classe II (3 faces) | Dentística | 243,60 |
| 85100129 | Restauração amálgama — Classe II (4 faces) | Dentística | 284,70 |
| 85100137 | Restauração ionômero — Classe I (1 face) | Dentística | 139,00 |
| 85100145 | Restauração ionômero — Classe II (2 faces) | Dentística | 170,40 |
| 85100196 | Restauração resina — Classe I (1 face) | Dentística | 202,50 |
| 85100200 | Restauração resina — Classe II (2 faces) | Dentística | 266,00 |
| 85100218 | Restauração resina — Classe II/III (3 faces) | Dentística | 329,50 |
| 85100226 | Restauração resina — Classe II/IV (4 faces) | Dentística | 367,60 |
| 85200034 | Pulpectomia de urgência | Endodontia | 142,00 |
| 85200042 | Pulpotomia | Endodontia | 142,00 |
| 85200069 | Remoção de material obturador (retratamento) | Endodontia | 275,00 |
| 85200077 | Remoção de núcleo intra-radicular | Endodontia | 281,00 |
| 85200085 | Restauração temporária / curativo de demora | Endodontia | 100,90 |
| 85200093 | Tratamento endodôntico — birradicular | Endodontia | 486,50 |
| 85200107 | Tratamento endodôntico — molar | Endodontia | 613,50 |
| 85200115 | Tratamento endodôntico — unirradicular | Endodontia | 359,50 |
| 85300047 | Profilaxia / raspagem supragengival (por arcada) | Periodontia | 180,10 |
| 85300055 | Remoção de fatores de retenção | Periodontia | 136,00 |
| 85300071 | Raspagem subgengival / manutenção periodontal | Periodontia | 180,10 |
| 85400467 | Recimentação de trabalho protético | Prótese | 136,00 |
| 85400483 | Reembasamento de prótese (imediato) | Prótese | 202,50 |
| 85400505 | Remoção de trabalho protético — por elemento | Prótese | 136,00 |
| 85400513 | Restauração cerâmica inlay / onlay | Prótese | 734,50 |

> **Observação**: a Basis pratica preços frequentemente acima desses valores (a CBHPO está defasada). O delta é **esperado** e calculado pelo app pra mostrar a margem.

---

### Seed 2 — `procedimentos` (catálogo Basis)

Cada linha vira um INSERT em `procedimentos`. O `valor_atual` é o preço praticado pela Basis hoje; quando há um `codigo_cbhpo` preenchido, o app calcula automaticamente o delta vs `cbhpo_referencia.valor_oficial` e mostra na UI.

#### 🔍 Consulta e Diagnóstico

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| Consulta odontológica | 81000030 | 133,00 | 30 | — | 5,00 | 0 |
| Consulta odontológica inicial | 81000065 | 133,00 | 45 | — | 5,00 | 0 |
| Consulta inicial e Orientações de higiene | NULL | 250,00 | 45 | — | 5,00 | 0 |
| Diagnóstico e planejamento de tratamento | 81000189 | 266,00 | 60 | — | 5,00 | 0 |
| Condicionamento em odontologia | 81000014 | 107,60 | 30 | — | 5,00 | 0 |
| Urgências Odontológicas | NULL | 300,00 | 30 | — | 10,00 | 0 |
| Urgência (horário comercial) | 81000065 | 133,00 | 30 | — | 10,00 | 0 |
| Urgência (noturno / fds / feriado) | 81000065 | 200,00 | 30 | — | 10,00 | 0 |
| Radiografia periapical | 81000421 | 23,32 | 10 | — | 8,00 | 0 |
| Radiografia panorâmica | 81000405 | 88,80 | 15 | — | 8,00 | 0 |
| Radiografia oclusal | 81000383 | 57,40 | 10 | — | 8,00 | 0 |
| Tomografia cone beam (CBCT) | 81000510 | 587,40 | 20 | — | 0,00 | 300,00 |

#### 🧹 Prevenção e Periodontia

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| Profilaxia e raspagem | NULL | 400,00 | 50 | 200 | 15,00 | 0 |
| Profilaxia / raspagem supragengival (por arcada) | 85300047 | 180,10 | 40 | — | 15,00 | 0 |
| Remoção de fatores de retenção | 85300055 | 136,00 | 30 | — | 10,00 | 0 |
| Raspagem subgengival — por segmento | 85300071 | 180,10 | 45 | — | 15,00 | 0 |
| Aplicação tópica de flúor | NULL | 70,00 | 15 | — | 12,00 | 0 |
| Aplicação de verniz fluoretado (por sessão) | NULL | 80,00 | 20 | — | 15,00 | 0 |
| Tratamento de manutenção periodontal | 85300071 | 180,10 | 45 | — | 15,00 | 0 |

#### 🔧 Restaurações / Dentística

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| ART (Tratamento Restaurador Atraumático) | NULL | 120,00 | 30 | 200 | 18,00 | 0 |
| Restauração de dente decíduo | NULL | 150,00 | 30 | — | 20,00 | 0 |
| Restaurações simples | NULL | 200,00 | 40 | — | 30,00 | 0 |
| Restaurações complexas | NULL | 350,00 | 60 | — | 50,00 | 0 |
| Restaurações estéticas | NULL | 400,00 | 60 | — | 55,00 | 0 |
| Restauração resina — Classe I (1 face) | 85100196 | 202,50 | 40 | — | 35,00 | 0 |
| Restauração resina — Classe II (2 faces) | 85100200 | 266,00 | 50 | — | 45,00 | 0 |
| Restauração resina — Classe II (3 faces) | 85100218 | 329,50 | 60 | — | 55,00 | 0 |
| Restauração resina — Classe II (4 faces) | 85100226 | 367,60 | 70 | — | 60,00 | 0 |
| Restauração resina — Classe III | 85100218 | 329,50 | 50 | — | 45,00 | 0 |
| Restauração resina — Classe IV | 85100226 | 367,60 | 60 | — | 55,00 | 0 |
| Restauração resina — Classe V | 85100196 | 202,50 | 30 | — | 30,00 | 0 |
| Restauração amálgama — Classe I (1 face) | 85100099 | 177,10 | 35 | — | 20,00 | 0 |
| Restauração amálgama — Classe II (2 faces) | 85100102 | 205,50 | 45 | — | 25,00 | 0 |
| Restauração amálgama — Classe II (3 faces) | 85100110 | 243,60 | 55 | — | 30,00 | 0 |
| Restauração amálgama — Classe II (4 faces) | 85100129 | 284,70 | 65 | — | 35,00 | 0 |
| Restauração ionômero — Classe I (1 face) | 85100137 | 139,00 | 30 | — | 18,00 | 0 |
| Restauração ionômero — Classe II (2 faces) | 85100145 | 170,40 | 40 | — | 22,00 | 0 |
| Restauração temporária / expectante | 85200085 | 100,90 | 20 | — | 12,00 | 0 |

#### ⚗️ Endodontia (Canal)

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| Abertura e curativo endodôntico | NULL | 180,00 | 40 | — | 30,00 | 0 |
| Canal — incisivo / canino (unirradicular) | 85200115 | 359,50 | 90 | — | 60,00 | 0 |
| Endodontia de anterior | NULL | 400,00 | 90 | — | 60,00 | 0 |
| Canal — canino / pré-molar (birradicular) | 85200093 | 486,50 | 120 | — | 75,00 | 0 |
| Canal — molar | 85200107 | 613,50 | 180 | — | 95,00 | 0 |
| Retratamento — incisivo / canino | 85200115 | 359,50 | 120 | — | 65,00 | 0 |
| Retratamento — canino / pré-molar | 85200093 | 486,50 | 150 | — | 80,00 | 0 |
| Retratamento — molar | 85200107 | 613,50 | 210 | — | 100,00 | 0 |
| Pulpectomia de urgência | 85200034 | 142,00 | 45 | — | 30,00 | 0 |
| Pulpotomia | 85200042 | 142,00 | 40 | — | 25,00 | 0 |
| Capeamento pulpar direto e indireto | NULL | 150,00 | 30 | — | 20,00 | 0 |
| Remoção de material obturador (retratamento) | 85200069 | 275,00 | 60 | — | 40,00 | 0 |
| Remoção de núcleo intra-radicular | 85200077 | 281,00 | 60 | — | 35,00 | 0 |

#### ✂️ Cirurgia / Extrações

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| Exodontia de baixa complexidade | NULL | 250,00 | 40 | — | 25,00 | 0 |
| Exodontia de RR (raiz residual) | NULL | 250,00 | 45 | — | 25,00 | 0 |
| Exodontia — dente permanente | 82000875 | 208,50 | 45 | — | 25,00 | 0 |
| Exodontia — raiz residual | 82000859 | 208,50 | 45 | — | 25,00 | 0 |
| Exodontia a retalho | 82000816 | 249,60 | 60 | — | 40,00 | 0 |
| Exodontia — dente incluso / impactado | 82001286 | 515,60 | 90 | — | 55,00 | 0 |
| Exodontia — dente semi-incluso | 82001294 | 515,60 | 75 | — | 50,00 | 0 |
| Tratamento de alveolite | 82001650 | 143,80 | 30 | — | 20,00 | 0 |
| Drenagem de abscesso — intra-oral | 82001030 | 205,50 | 30 | — | 25,00 | 0 |
| Drenagem de abscesso — extra-oral | 82001022 | 205,50 | 30 | — | 25,00 | 0 |
| Controle pós-operatório (por sessão) | 82000506 | 133,00 | 20 | — | 10,00 | 0 |

#### 🦷 Prótese

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| Prótese total acrílica — por arcada | NULL | 800,00 | 120 | — | 30,00 | 350,00 |
| Prótese parcial removível c/ grampos (PPR) | NULL | 700,00 | 90 | — | 25,00 | 300,00 |
| Prótese fixa metalo-cerâmica — por elemento | NULL | 600,00 | 90 | — | 30,00 | 400,00 |
| Coroa de porcelana pura — por elemento | NULL | 800,00 | 90 | — | 35,00 | 500,00 |
| Reembasamento de prótese (imediato) | 85400483 | 202,50 | 45 | — | 25,00 | 0 |
| Reembasamento de prótese (definitivo) | NULL | 259,30 | 60 | — | 30,00 | 80,00 |
| Recimentação de trabalho protético | 85400467 | 136,00 | 20 | — | 15,00 | 0 |
| Remoção de trabalho protético — por elemento | 85400505 | 136,00 | 30 | — | 10,00 | 0 |
| Restauração cerâmica inlay / onlay | 85400513 | 734,50 | 90 | — | 40,00 | 450,00 |

#### 🚨 Urgências / Dor

| Procedimento | Código CBHPO | Valor Atual (R$) | Tempo (min) | Hora Clín. (R$) | Material (R$) | Lab (R$) |
|---|---|---|---|---|---|---|
| Curativo de demora endodôntico | 85200085 | 100,90 | 25 | — | 15,00 | 0 |
| Abertura coronária / pulpectomia urgência | 85200034 | 142,00 | 45 | — | 30,00 | 0 |
| Drenagem de abscesso intra-oral (urgência) | 82001030 | 205,50 | 30 | — | 25,00 | 0 |
| Tratamento conservador luxação ATM | 82001642 | 142,00 | 30 | — | 10,00 | 0 |
| Redução simples de luxação da ATM | 82001197 | 127,80 | 20 | — | 5,00 | 0 |

---

## Tabela de Distâncias por Zona (Deslocamento)

Base: Blumenau centro. Custos calculados automaticamente a partir dos parâmetros do veículo e tempo.

| Zona | Distância ida+volta (km) | Referência |
|---|---|---|
| Blumenau — bairros centrais | 10 | Até 5 km do ponto base |
| Blumenau — bairros afastados | 20 | Itoupava, Velha, Fortaleza, Badenfurt |
| Gaspar | 30 | Aprox. 15 km de Blumenau |
| Indaial | 36 | Aprox. 18 km de Blumenau |
| Pomerode | 44 | Aprox. 22 km de Blumenau |
| Timbó | 50 | Aprox. 25 km de Blumenau |

Na interface, o usuário seleciona a zona no dropdown OU digita distância customizada. O app calcula automaticamente:

```
custo_veiculo     = custo_total_km × distancia
custo_tempo       = custo_tempo_km × distancia
custo_real        = custo_veiculo + custo_tempo
taxa_ao_paciente  = custo_real × (1 + margem)
```

A tabela de zonas é editável — o usuário pode adicionar/remover zonas nas configurações.

---

## Fórmulas de Cálculo

### A) Valor Base do Procedimento Domiciliar

```
valor_com_reajuste   = valor_cbhpo × (1 + reajuste_acumulado)
preco_domiciliar     = valor_com_reajuste × (1 + acrescimo_domiciliar)
preco_nee            = preco_domiciliar × (1 + acrescimo_nee)
preco_com_complexidade = preco × fator_complexidade
```

### B) Custo de Materiais e Laboratório

```
custo_direto = custo_material + custo_laboratorio
```

Repassado ao paciente sem acréscimo domiciliar (é custo real).

### C) Hora Clínica (por procedimento — NOVA coluna)

Cada procedimento pode ter um valor de hora clínica próprio (ex: profilaxia usa R$ 200/h, consulta usa R$ 150/h). Se não definido, usa o global.

```
valor_hora_proc = valor_hora_clinica_override OU config.valor_hora_clinica
custo_hora      = valor_hora_proc × (tempo_estimado_min / 60)
```

**Na planilha da Gabrielle, a hora clínica é uma coluna separada somada ao preço unitário** — o app deve refletir isso:
```
subtotal = (preco_unitario × qtd) + valor_hora_clinica
```

### D) Deslocamento (por zona)

```
custo_combustivel_km  = preco_combustivel_litro / consumo_km_l
custo_total_km        = custo_combustivel_km + custo_manutencao_km
custo_tempo_km        = valor_hora_clinica / velocidade_media_km_h

custo_veiculo         = custo_total_km × distancia_ida_volta_km
custo_tempo           = custo_tempo_km × distancia_ida_volta_km
custo_real            = custo_veiculo + custo_tempo

taxa_deslocamento     = custo_real × (1 + margem_lucro)
```

**Cobrado 1x por visita**, independente de quantos procedimentos.

### E) Desconto por Múltiplos Procedimentos

```
1º procedimento: preço cheio
2º: preço × (1 - 0.10)    # -10%
3º: preço × (1 - 0.15)    # -15%
4º+: preço × (1 - 0.20)   # -20%
```

Ordenado do mais caro ao mais barato. Configurável.

### F) Custos Fixos Rateados

```
total_custos_fixos_mes = Σ custos_fixos_mensais
custo_fixo_por_visita  = total_custos_fixos_mes / atendimentos_estimados_mes
```

### G) Margem de Retrabalho

```
margem_retrabalho = subtotal_procedimentos × 0.05
```

### H) Impostos — Calculadora Guiada

A Gabrielle não sabe calcular impostos (na planilha: "Não sei fazer kkk socorro"). O app deve **guiar** ela com um assistente passo a passo:

**Cenário PF (Pessoa Física — carnê-leão):**
```
base_calculo = faturamento_bruto_mes - deduções (INSS, dependentes, livro-caixa)
ir = base_calculo × aliquota_progressiva - parcela_dedutivel
iss = faturamento_bruto × 0.02 a 0.05 (varia por município)
inss = limitado ao teto (20% como contribuinte individual)
```

Tabela IR progressiva 2024/2025:
| Faixa | Alíquota | Dedução |
|---|---|---|
| Até R$ 2.259,20 | Isento | — |
| R$ 2.259,21 a R$ 2.826,65 | 7,5% | R$ 169,44 |
| R$ 2.826,66 a R$ 3.751,05 | 15% | R$ 381,44 |
| R$ 3.751,06 a R$ 4.664,68 | 22,5% | R$ 662,77 |
| Acima de R$ 4.664,68 | 27,5% | R$ 896,00 |

**Cenário MEI:**
```
das_fixo = ~R$ 75,60/mês (saúde)
sem IR separado
limite faturamento = R$ 81.000/ano
```

**Cenário Simples Nacional (ME):**
```
aliquota_efetiva = depende da faixa de faturamento (Anexo III ou V)
```

O app deve:
1. Perguntar o regime tributário (PF / MEI / Simples) **uma vez** nas configurações — fica como default global
2. Calcular automaticamente a alíquota efetiva a partir do regime + faturamento estimado
3. Aplicar sobre cada orçamento usando o default — **mas permitir override por orçamento**
4. Mostrar sugestão: "Para seu faturamento estimado de R$ X/mês, considere migrar para [regime]"

**Por que o override por orçamento é obrigatório**: a Gabrielle pode atender uma família como **PF** (recibo simples / carnê-leão) e logo depois atender um plano corporativo como **PJ** (nota fiscal pelo Simples Nacional). Os dois orçamentos no mesmo dia têm alíquotas diferentes — o app precisa refletir isso sem forçá-la a abrir as configurações no meio do atendimento.

**Mecanismo de override (na tela de orçamento / precificação):**

```
┌──────────────────────────────────────────────┐
│ Regime tributário deste orçamento            │
│  ⦿ PF (carnê-leão)        ~27,5% efetivo     │
│  ○ MEI                    ~6,0% efetivo      │
│  ○ Simples (Anexo III)    ~13,5% efetivo     │
│  ○ Não aplicar imposto                       │
│  ○ Customizado: [____]%                      │
│                                              │
│  Padrão (config): PF                         │
└──────────────────────────────────────────────┘
```

- O dropdown **inicia no regime default** (lido de `config.impostos.regime`)
- A Gabrielle pode trocar pra qualquer outro **só pra esse orçamento**
- O default global **não é alterado** — fica intacto pra próximo atendimento
- Cada item em `historico` salva o `regime_aplicado` + `aliquota_aplicada` no `payload_json` (imutável após salvo)

**Na composição do orçamento**, impostos são uma coluna separada por item:
```
aliquota_efetiva = override_orcamento OU config.impostos.aliquota_efetiva_total
valor_impostos_item = subtotal_item × aliquota_efetiva
```

**Modelo Python (override no orçamento):**

```python
@dataclass
class Orcamento:
    ...
    regime_override: str | None       # 'PF' | 'MEI' | 'SIMPLES' | 'DEFAULT' | 'CUSTOM' | None (= default)
    aliquota_override: float | None   # só usado se regime_override == 'CUSTOM'
```

### I) Taxa da Maquineta (fórmula correta)

```
preco_a_cobrar = valor_liquido / (1 - taxa)
taxa_paga      = preco_a_cobrar × taxa
confirmacao    = preco_a_cobrar - taxa_paga  (deve = valor_liquido)
parcela        = preco_a_cobrar / num_parcelas
```

**Comparativo com fórmula errada (para educação):**
```
errado         = valor_liquido × (1 + taxa)
perda          = preco_a_cobrar - errado     # quanto perderia
```

### J) Composição Final — 6 Colunas por Item

Reflete a estrutura da planilha:

```
┌──────────────┬──────┬────────────┬────────────┬──────────┬──────────────┬──────────┬──────────┬──────────┐
│ Procedimento │ Qtd. │ Preço Unit.│ Hora Clín. │ Subtotal │ Deslocamento │ Maquineta│ Impostos │ TOTAL    │
│              │      │ Domic.(R$) │    (R$)    │   (R$)   │     (R$)     │   (R$)   │   (R$)   │   (R$)   │
├──────────────┼──────┼────────────┼────────────┼──────────┼──────────────┼──────────┼──────────┼──────────┤
│ Urgência     │  1   │   300,00   │   150,00   │  450,00  │    57,31     │  64,34   │    —     │  571,65  │
│ Consulta ini.│  1   │   250,00   │   150,00   │  400,00  │    57,31     │    —     │    —     │  457,31  │
│ Profilaxia   │  1   │   400,00   │   200,00   │  600,00  │      —       │    —     │    —     │  600,00  │
├──────────────┴──────┴────────────┴────────────┼──────────┤──────────────┤──────────┤──────────┤──────────┤
│                                    TOTAIS:     │ 1.450,00 │   114,62    │  64,34   │    —     │1.628,96  │
│                                    NEE (+25%): │          │             │          │          │2.036,20  │
└────────────────────────────────────────────────┴──────────┴─────────────┴──────────┴──────────┴──────────┘
```

**Regras da composição:**
- Deslocamento: cobrado 1x por visita. Se múltiplos procedimentos, rateado ou alocado no primeiro item.
- Maquineta: aplicada apenas se pagamento no cartão. Pode ser por item ou sobre o total.
- Impostos: aplicados por item ou sobre o total (configurável).
- NEE: +25% sobre o total dos procedimentos (não sobre deslocamento).

### K) Reajuste Automático

```
meses_desde = diferença(hoje, ultimo_reajuste)
reajuste_acumulado = (1 + indice_anual) ^ (meses_desde / 12) - 1

Se meses_desde >= alerta_meses:
  ⚠️ "Tabela sem reajuste há X meses. Sugerido: +Y%"
```

### L) Validação contra Meta

```
projecao = ticket_medio × atendimentos_estimados
gap = meta - projecao

Se gap > 0: ⚠️ "Faltam R$ X/mês. Aumente preços em Y% ou atenda Z visitas a mais."
```

---

## Fluxo das Telas

O app tem **2 telas só**: a principal (Precificador) e a de Configurações (escondida atrás do ícone ⚙️ no canto).

### Tela Principal — 🧮 Precificador

```
┌──────────────────────────────────────────────────┐
│  [Logo Basis]   BASIS Precificador          ⚙️   │
├──────────────────────────────────────────────────┤
│                                                  │
│  Procedimento(s):                                │
│  ┌────────────────────────────────────────────┐  │
│  │ 🔍 buscar procedimento...              [+] │  │
│  └────────────────────────────────────────────┘  │
│  • Consulta odontológica            [1] [×]      │
│  • Restauração resina Classe I      [2] [×]      │
│                                                  │
│  Distância (ida + volta): [____] km              │
│                                                  │
│  □ NEE (+25%)                                    │
│                                                  │
│  Regime tributário: [PF (padrão)         ▾]      │
│                                                  │
│            ┌──────────────────┐                  │
│            │    CALCULAR      │                  │
│            └──────────────────┘                  │
│                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                                  │
│  💰 À vista (Pix):       R$    850,00            │
│  💳 Cartão 7x:           R$    924,15            │
│         (7× de R$ 132,02)                        │
│  💳 Cartão 10x:          R$    944,44            │
│         (10× de R$ 94,44)                        │
│  💳 Cartão 12x:          R$    960,55            │
│         (12× de R$ 80,05)                        │
│                                                  │
│            ┌──────────────────┐                  │
│            │  📄 GERAR PDF    │                  │
│            └──────────────────┘                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Comportamento:**

1. **Busca de procedimentos** com fuzzy search (`thefuzz`). Múltiplos podem ser adicionados, cada um com quantidade.
2. **Distância em km**: input livre. Se a usuária quiser, há um botão pequeno "📍 zonas pré-cadastradas" que abre um popover com as zonas comuns (Blumenau centro = 10 km, Gaspar = 30 km, etc.) — só atalho, não obrigatório.
3. **Checkbox NEE** aplica +25% sobre o subtotal de procedimentos (não sobre deslocamento).
4. **Regime tributário** começa selecionado no default global. Trocar aqui afeta **só este cálculo**, não o config.
5. **Botão Calcular** chama `precificador.precificar(entrada)` e popula os 4 cenários abaixo.
6. **Botão Gerar PDF** salva o orçamento em `historico` e abre o PDF.

**O que NÃO está na tela principal** (intencionalmente):
- ❌ Decomposição em 6 colunas (preço unit / hora clín / desloc / etc.) — fica oculto
- ❌ Dados do paciente (nome, endereço) — não obrigatório, opcional só na hora de gerar PDF
- ❌ Materiais, laboratório, custos fixos, retrabalho — tudo nos bastidores
- ❌ Lucro líquido, custo real — irrelevante na hora de cobrar
- ❌ Sidebar de navegação — não há outras telas pra navegar

### Tela ⚙️ Configurações (esporádica)

Acessada pelo ícone discreto no canto da tela principal. Cards agrupados, inputs com borda dourada, **salvam automaticamente** ao alterar (sem botão "Salvar"). A usuária só vem aqui de tempos em tempos:

- **Veículo**: consumo (km/L), preço combustível (R$/L), manutenção (R$/km)
- **Tempo**: valor hora clínica global (R$/h), velocidade média (km/h)
- **Deslocamento**: margem de lucro (%)
- **Zonas pré-cadastradas**: lista editável (nome, distância) — só atalho da tela principal
- **Maquineta**: dropdown da maquineta usada + taxas editáveis (Pix, 7x, 10x, 12x)
- **Impostos**: regime tributário default (PF/MEI/Simples) + assistente guiado pra calcular alíquota
- **Domiciliar**: acréscimo padrão (100%), acréscimo NEE (25%)
- **Custos Fixos Mensais**: CRO, seguro, contabilidade, depreciação, cursos, autoclave, outros
- **Retrabalho**: margem (%)
- **Meta Mensal**: nº de atendimentos estimados (usado pro rateio dos custos fixos)
- **Referência CBHPO**: botão "Atualizar referência" + exibição da versão atual

#### Sub-tela: Editor de Procedimentos (foco visual moderno)

Esta sub-tela merece destaque — é onde a Gabrielle vai passar mais tempo nas configurações. **A intenção é parecer um app moderno tipo Notion / Linear / Airtable**, não um Excel velho.

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Voltar          Procedimentos              [+ Novo]   [⬇ CSV]│
├─────────────────────────────────────────────────────────────────┤
│  🔍 [Buscar...                          ]   Categoria: [Todas▾] │
│                                                                 │
│  📊 87 procedimentos · em média +32% acima da CBHPO 2024        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 🔧 Restaurações / Dentística                          ▾  │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │  Restauração resina Classe I (1 face)                    │  │
│  │  85100196 · 40 min · Material R$ 35                      │  │
│  │  ┌─────────────┐  CBHPO 2024: R$ 202,50                  │  │
│  │  │ R$  280,00  │  ▲ +38,3% acima                    [✏️] │  │
│  │  └─────────────┘                                          │  │
│  │  ───────────────────────────────────────────────────      │  │
│  │  Restauração resina Classe II (2 faces)                  │  │
│  │  85100200 · 50 min · Material R$ 45                      │  │
│  │  ┌─────────────┐  CBHPO 2024: R$ 266,00                  │  │
│  │  │ R$  350,00  │  ▲ +31,6% acima                    [✏️] │  │
│  │  └─────────────┘                                          │  │
│  │  ───────────────────────────────────────────────────      │  │
│  │  Restaurações estéticas                                  │  │
│  │  Sem código CBHPO · 60 min · Material R$ 55              │  │
│  │  ┌─────────────┐                                         │  │
│  │  │ R$  400,00  │  Sem referência                    [✏️] │  │
│  │  └─────────────┘                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ⚗️ Endodontia                                          ▸  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Especificação visual e de comportamento:**

1. **Categorias agrupadas em cards colapsáveis** (`CTkFrame` com header clicável). Padrão: todas expandidas. O usuário colapsa as que não interessam.
2. **Busca fuzzy ao vivo** no topo (`thefuzz`) — filtra entre todas as categorias enquanto digita. Filtros adicionais por categoria via dropdown.
3. **Indicador agregado no topo**: *"87 procedimentos · em média +32% acima da CBHPO 2024"* — calculado em tempo real via `v_procedimentos_com_delta`.
4. **Edição inline do `valor_atual`**: input destacado com borda dourada (`gold`). Salva no banco em `on_focus_out` (sem botão "Salvar"). Loading animado discreto durante o save.
5. **Delta vs CBHPO ao lado do input**, atualizado em tempo real enquanto a usuária digita:
   - ▲ verde (`success`) se acima do oficial
   - ▼ vermelho (`error`) se abaixo (alerta de prejuízo)
   - = cinza se igual
   - "Sem referência" em `text_muted` se `codigo_cbhpo IS NULL`
6. **Botão `[✏️]`** abre um **drawer lateral** (não modal bloqueante) com os campos avançados: tempo, hora clínica override, custo de material, custo de lab, código CBHPO, fator de complexidade. Salva ao fechar.
7. **Botão `[+ Novo]`** abre o mesmo drawer, vazio, pra criar do zero.
8. **`[⬇ CSV]`** exporta a tabela atual pra Excel/CSV — bônus pra Gabrielle ter uma cópia offline.
9. **Animações sutis**: fade-in ao filtrar, highlight verde rápido (~300ms) ao salvar com sucesso, shake vermelho se o valor for inválido.
10. **Atalhos de teclado**: `↑↓` navega entre procedimentos, `Enter` abre o drawer, `Esc` fecha, `Ctrl+F` foca na busca, `Ctrl+N` cria novo.
11. **Estado vazio bonito** quando o filtro não retorna nada: ícone + texto *"DEFAULT procedimento encontrado para 'X'"* + botão "Criar 'X' como novo procedimento".

**Feel-good details:**
- Cards com `corner_radius=12`, sombras sutis, hover com leve scale
- Tipografia: nome do procedimento em `heading`, código + tempo + material em `small text_secondary`, valor em `mono` grande
- Cor de fundo do card muda sutilmente quando hover (`bg_secondary` → `bg_card`)

> **Nota**: a calculadora completa de maquineta, painel financeiro, histórico detalhado e simulador de meta — tudo que existia nas telas antigas — **foi removido**. Se a usuária precisar dessas análises mais tarde, voltam como features avançadas; por ora a meta é zero ruído na tela principal.

---

## Geração de PDF (reportlab)

PDF minimalista — pensado pro paciente, não pra Gabrielle. **Não mostra decomposição interna** de custos.

1. **Header**: logo Basis + "Orçamento Odontológico Domiciliar" + data + nº sequencial
2. **Procedimento(s)**: lista simples com nome + quantidade. Sem códigos CBHPO, sem valores unitários.
3. **Atendimento domiciliar**: indicação genérica ("Inclui deslocamento até o endereço do paciente").
4. **Cenários de pagamento** (a estrela do PDF):

   ```
   ┌─────────────────────────────────────────────┐
   │  💰 À vista (Pix/Dinheiro):     R$ 850,00   │
   │                                             │
   │  💳 Cartão de crédito                       │
   │     7x sem juros:    R$ 924,15              │
   │                      (7 parcelas R$ 132,02) │
   │     10x sem juros:   R$ 944,44              │
   │                      (10 parcelas R$ 94,44) │
   │     12x sem juros:   R$ 960,55              │
   │                      (12 parcelas R$ 80,05) │
   └─────────────────────────────────────────────┘
   ```

5. **Validade**: 30 dias a partir da emissão
6. **Dados do paciente**: opcionais — só preenchidos se a Gabrielle informar antes de gerar
7. **Rodapé**: contato da Basis, CRO da profissional, observações

---

## Regras de Negócio

1. **Filosofia "10 segundos"**: o uso diário cabe em uma única tela — procedimento + km → preço final. Toda complexidade fica nos bastidores.
2. **Tudo é variável** — qualquer parâmetro é editável via configurações. Nada hardcoded.
3. **Acréscimo domiciliar padrão 100%** (CNCC/CRO), editável.
4. **NEE +25%** sobre valor domiciliar (não sobre deslocamento).
5. **Hora clínica somada ao valor do procedimento** internamente. Pode variar por procedimento via `valor_hora_clinica_override`.
6. **Maquineta fórmula inversa**: `valor / (1 - taxa)`.
7. **Deslocamento em km direto** — input livre. Há atalho opcional para zonas pré-cadastradas.
8. **Deslocamento cobrado 1x por visita**, independente de quantos procedimentos.
9. **Materiais e lab são custo real** — repassados sem acréscimo domiciliar.
10. **Custos fixos rateados** pelo nº de atendimentos/mês estimados.
11. **Margem de retrabalho (5%)** cobre refações.
12. **Comparativo de pagamento sempre visível**: Pix, 7x, 10x, 12x.
13. **Impostos editáveis por orçamento** — default global vem do regime configurado, mas pode ser sobrescrito a cada cálculo (PF num atendimento, PJ no próximo).
14. **CBHPO como referência editável** — `cbhpo_referencia` é fonte da verdade, `procedimentos.valor_atual` é o preço praticado, app mostra delta automaticamente.
15. **Atualização de CBHPO nunca toca em `valor_atual`** — só atualiza a referência; a usuária decide se reajusta.
16. **Região**: Blumenau, Gaspar, Pomerode, Indaial, Timbó — SC.

---

## Dependências (requirements.txt)

```
customtkinter>=5.2.0
Pillow>=10.0.0
reportlab>=4.0
thefuzz>=0.20.0
```

## Como rodar

```bash
pip install -r requirements.txt
python main.py
```

## Empacotar como .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/logo_basis.ico \
  --add-data "assets;assets" \
  --add-data "seeds;seeds" \
  main.py
```