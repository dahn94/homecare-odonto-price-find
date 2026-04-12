-- Schema do basis.db (SQLite). Aplicado em runtime por migrations.py.
-- Toda a aplicação Basis Precificador depende destas tabelas.

PRAGMA foreign_keys = ON;

-- ───────────────────────────────────────────────────────────────────
-- 1. config — chave/valor tipado pra parâmetros globais
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS config (
  chave         TEXT PRIMARY KEY,
  valor         TEXT NOT NULL,
  tipo          TEXT NOT NULL,    -- 'float' | 'int' | 'bool' | 'string' | 'json'
  grupo         TEXT NOT NULL,    -- 'veiculo' | 'tempo' | 'maquineta' | ...
  descricao     TEXT,
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ───────────────────────────────────────────────────────────────────
-- 2. custos_fixos — uma linha por item rateado mensal
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS custos_fixos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  nome          TEXT NOT NULL,
  valor_mensal  TEXT NOT NULL,
  ativo         INTEGER NOT NULL DEFAULT 1
);

-- ───────────────────────────────────────────────────────────────────
-- 3. zonas — atalho de distâncias pré-cadastradas
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zonas (
  id                       INTEGER PRIMARY KEY AUTOINCREMENT,
  nome                     TEXT NOT NULL,
  distancia_ida_volta_km   REAL NOT NULL,
  referencia               TEXT,
  ativo                    INTEGER NOT NULL DEFAULT 1
);

-- ───────────────────────────────────────────────────────────────────
-- 4. cbhpo_referencia — fonte da verdade da CBHPO oficial
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cbhpo_referencia (
  codigo_cbhpo  TEXT PRIMARY KEY,
  nome_oficial  TEXT NOT NULL,
  categoria     TEXT,
  valor_oficial TEXT NOT NULL,
  versao        TEXT NOT NULL,
  fonte         TEXT,
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_cbhpo_versao ON cbhpo_referencia(versao);

-- ───────────────────────────────────────────────────────────────────
-- 5. procedimentos — catálogo praticado pela Basis
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS procedimentos (
  id                          INTEGER PRIMARY KEY AUTOINCREMENT,
  nome                        TEXT NOT NULL,
  categoria                   TEXT NOT NULL,
  codigo_cbhpo                TEXT,
  valor_atual                 TEXT NOT NULL,
  tempo_estimado_min          INTEGER NOT NULL,
  valor_hora_clinica_override TEXT,
  custo_material              TEXT NOT NULL DEFAULT 0,
  custo_laboratorio           TEXT NOT NULL DEFAULT 0,
  fator_complexidade_min      TEXT NOT NULL DEFAULT 1.0,
  fator_complexidade_max      TEXT NOT NULL DEFAULT 1.0,
  ativo                       INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY (codigo_cbhpo) REFERENCES cbhpo_referencia(codigo_cbhpo)
);

CREATE INDEX IF NOT EXISTS idx_proc_categoria ON procedimentos(categoria);
CREATE INDEX IF NOT EXISTS idx_proc_codigo ON procedimentos(codigo_cbhpo);

-- ───────────────────────────────────────────────────────────────────
-- View: procedimentos com delta CBHPO calculado
-- ───────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS v_procedimentos_com_delta;
CREATE VIEW v_procedimentos_com_delta AS
SELECT
  p.*,
  c.valor_oficial AS valor_cbhpo_oficial,
  c.versao        AS cbhpo_versao,
  CASE
    WHEN c.valor_oficial IS NULL OR c.valor_oficial = 0 THEN NULL
    ELSE (p.valor_atual - c.valor_oficial) / c.valor_oficial
  END             AS delta_percent
FROM procedimentos p
LEFT JOIN cbhpo_referencia c ON c.codigo_cbhpo = p.codigo_cbhpo;

-- ───────────────────────────────────────────────────────────────────
-- 6. historico — toda precificação realizada
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS historico (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  data_hora           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  cliente_nome        TEXT NOT NULL,
  cliente_observacao  TEXT,
  distancia_km        REAL NOT NULL,
  is_nee              INTEGER NOT NULL DEFAULT 0,
  regime_aplicado     TEXT NOT NULL,
  aliquota_aplicada   TEXT NOT NULL,
  total_a_vista       TEXT NOT NULL,
  total_cartao_7x     TEXT NOT NULL,
  total_cartao_10x    TEXT NOT NULL,
  total_cartao_12x    TEXT NOT NULL,
  pdf_gerado          INTEGER NOT NULL DEFAULT 0,
  payload_json        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_historico_data ON historico(data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_historico_cliente ON historico(cliente_nome);
