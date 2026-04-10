-- Configurações default. Re-aplicado com INSERT OR IGNORE — não sobrescreve mudanças do usuário.

INSERT OR IGNORE INTO config (chave, valor, tipo, grupo, descricao) VALUES
  -- Veículo
  ('veiculo.consumo_km_l',             '12.0',  'float', 'veiculo',     'Consumo médio do veículo (km por litro)'),
  ('veiculo.preco_combustivel_litro',  '6.10',  'float', 'veiculo',     'Preço do combustível (R$/litro)'),
  ('veiculo.custo_manutencao_km',      '0.15',  'float', 'veiculo',     'Custo de manutenção rateado (R$/km)'),

  -- Tempo
  ('tempo.valor_hora_clinica',         '150.00','float', 'tempo',       'Valor padrão da hora clínica (R$/h)'),
  ('tempo.velocidade_media_km_h',      '40',    'int',   'tempo',       'Velocidade média de deslocamento (km/h)'),

  -- Deslocamento
  ('deslocamento.margem_lucro',        '0.30',  'float', 'deslocamento','Margem aplicada ao custo real do deslocamento'),

  -- Maquineta
  ('maquineta.nome',                   'modoPAG','string','maquineta',  'Nome da maquineta usada'),
  ('maquineta.taxa_pix',               '0.00',  'float', 'maquineta',   'Taxa Pix'),
  ('maquineta.taxa_7x',                '0.08',  'float', 'maquineta',   'Taxa cartão 7x'),
  ('maquineta.taxa_10x',               '0.10',  'float', 'maquineta',   'Taxa cartão 10x'),
  ('maquineta.taxa_12x',               '0.1151','float', 'maquineta',   'Taxa cartão 12x'),

  -- Impostos (default global; pode ser sobrescrito por orçamento)
  ('impostos.regime_default',          'PF',    'string','impostos',    'Regime tributário padrão (PF/MEI/SIMPLES/DEFAULT)'),
  ('impostos.aliquota_pf',             '0.275', 'float', 'impostos',    'Alíquota efetiva PF (carnê-leão)'),
  ('impostos.aliquota_mei',            '0.06',  'float', 'impostos',    'Alíquota efetiva MEI'),
  ('impostos.aliquota_simples',        '0.135', 'float', 'impostos',    'Alíquota efetiva Simples Nacional (Anexo III)'),

  -- Domiciliar
  ('domiciliar.acrescimo_padrao',      '1.00',  'float', 'domiciliar',  'Acréscimo domiciliar (100% sobre o valor de consultório)'),
  ('domiciliar.acrescimo_nee',         '0.25',  'float', 'domiciliar',  'Acréscimo NEE (25% adicional)'),

  -- Retrabalho
  ('retrabalho.margem_percent',        '0.05',  'float', 'retrabalho',  'Margem de retrabalho (5%)'),

  -- Meta (rateio dos custos fixos)
  ('meta.atendimentos_estimados_mes',  '40',    'int',   'meta',        'Atendimentos estimados por mês (rateio de custos fixos)'),
  ('meta.faturamento_desejado_mes',    '10000', 'float', 'meta',        'Faturamento líquido desejado mensalmente'),

  -- CBHPO referência
  ('cbhpo.versao_atual',               '2024',  'string','cbhpo',       'Versão da CBHPO carregada na referência');

-- Custos fixos mensais (rateados pelo nº de atendimentos)
INSERT OR IGNORE INTO custos_fixos (id, nome, valor_mensal) VALUES
  (1, 'CRO anual rateado',                  50.00),
  (2, 'Seguro responsabilidade civil',      80.00),
  (3, 'Contabilidade',                     150.00),
  (4, 'Depreciação equipamento portátil',  200.00),
  (5, 'Cursos de especialização',          100.00),
  (6, 'Manutenção autoclave',               50.00);

-- Zonas de atalho
INSERT OR IGNORE INTO zonas (id, nome, distancia_ida_volta_km, referencia) VALUES
  (1, 'Blumenau — bairros centrais',  10, 'Até 5 km do ponto base'),
  (2, 'Blumenau — bairros afastados', 20, 'Itoupava, Velha, Fortaleza, Badenfurt'),
  (3, 'Gaspar',                       30, 'Aprox. 15 km de Blumenau'),
  (4, 'Indaial',                      36, 'Aprox. 18 km de Blumenau'),
  (5, 'Pomerode',                     44, 'Aprox. 22 km de Blumenau'),
  (6, 'Timbó',                        50, 'Aprox. 25 km de Blumenau');
