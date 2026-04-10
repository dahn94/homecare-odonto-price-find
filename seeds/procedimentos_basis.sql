-- Seed inicial do catálogo Basis (procedimentos praticados).
-- Cada linha = um INSERT em procedimentos. valor_atual é editável pela usuária na UI.
-- codigo_cbhpo NULL quando o procedimento não existe na CBHPO oficial.

INSERT OR IGNORE INTO procedimentos (nome, categoria, codigo_cbhpo, valor_atual, tempo_estimado_min, custo_material, custo_laboratorio) VALUES
  -- Consulta e Diagnóstico
  ('Consulta odontológica',                          'Consulta e Diagnóstico', '81000030', 133.00,  30,  5.00,   0),
  ('Consulta odontológica inicial',                  'Consulta e Diagnóstico', '81000065', 133.00,  45,  5.00,   0),
  ('Consulta inicial e Orientações de higiene',      'Consulta e Diagnóstico', NULL,       250.00,  45,  5.00,   0),
  ('Diagnóstico e planejamento de tratamento',       'Consulta e Diagnóstico', '81000189', 266.00,  60,  5.00,   0),
  ('Condicionamento em odontologia',                 'Consulta e Diagnóstico', '81000014', 107.60,  30,  5.00,   0),
  ('Urgências Odontológicas',                        'Consulta e Diagnóstico', NULL,       300.00,  30, 10.00,   0),
  ('Urgência (horário comercial)',                   'Consulta e Diagnóstico', '81000065', 133.00,  30, 10.00,   0),
  ('Urgência (noturno / fds / feriado)',             'Consulta e Diagnóstico', '81000065', 200.00,  30, 10.00,   0),
  ('Radiografia periapical',                         'Diagnóstico por imagem', '81000421',  23.32,  10,  8.00,   0),
  ('Radiografia panorâmica',                         'Diagnóstico por imagem', '81000405',  88.80,  15,  8.00,   0),
  ('Radiografia oclusal',                            'Diagnóstico por imagem', '81000383',  57.40,  10,  8.00,   0),
  ('Tomografia cone beam (CBCT)',                    'Diagnóstico por imagem', '81000510', 587.40,  20,  0.00, 300),

  -- Prevenção e Periodontia
  ('Profilaxia e raspagem',                          'Prevenção e Periodontia', NULL,       400.00,  50, 15.00,   0),
  ('Profilaxia / raspagem supragengival (arcada)',   'Prevenção e Periodontia', '85300047', 180.10,  40, 15.00,   0),
  ('Remoção de fatores de retenção',                 'Prevenção e Periodontia', '85300055', 136.00,  30, 10.00,   0),
  ('Raspagem subgengival — por segmento',            'Prevenção e Periodontia', '85300071', 180.10,  45, 15.00,   0),
  ('Aplicação tópica de flúor',                      'Prevenção e Periodontia', NULL,        70.00,  15, 12.00,   0),
  ('Aplicação de verniz fluoretado',                 'Prevenção e Periodontia', NULL,        80.00,  20, 15.00,   0),
  ('Tratamento de manutenção periodontal',           'Prevenção e Periodontia', '85300071', 180.10,  45, 15.00,   0),

  -- Restaurações / Dentística
  ('ART (Tratamento Restaurador Atraumático)',       'Restaurações / Dentística', NULL,       120.00,  30, 18.00,   0),
  ('Restauração de dente decíduo',                   'Restaurações / Dentística', NULL,       150.00,  30, 20.00,   0),
  ('Restaurações simples',                           'Restaurações / Dentística', NULL,       200.00,  40, 30.00,   0),
  ('Restaurações complexas',                         'Restaurações / Dentística', NULL,       350.00,  60, 50.00,   0),
  ('Restaurações estéticas',                         'Restaurações / Dentística', NULL,       400.00,  60, 55.00,   0),
  ('Restauração resina — Classe I (1 face)',         'Restaurações / Dentística', '85100196', 202.50,  40, 35.00,   0),
  ('Restauração resina — Classe II (2 faces)',       'Restaurações / Dentística', '85100200', 266.00,  50, 45.00,   0),
  ('Restauração resina — Classe II (3 faces)',       'Restaurações / Dentística', '85100218', 329.50,  60, 55.00,   0),
  ('Restauração resina — Classe II (4 faces)',       'Restaurações / Dentística', '85100226', 367.60,  70, 60.00,   0),
  ('Restauração resina — Classe III',                'Restaurações / Dentística', '85100218', 329.50,  50, 45.00,   0),
  ('Restauração resina — Classe IV',                 'Restaurações / Dentística', '85100226', 367.60,  60, 55.00,   0),
  ('Restauração resina — Classe V',                  'Restaurações / Dentística', '85100196', 202.50,  30, 30.00,   0),
  ('Restauração amálgama — Classe I (1 face)',       'Restaurações / Dentística', '85100099', 177.10,  35, 20.00,   0),
  ('Restauração amálgama — Classe II (2 faces)',     'Restaurações / Dentística', '85100102', 205.50,  45, 25.00,   0),
  ('Restauração amálgama — Classe II (3 faces)',     'Restaurações / Dentística', '85100110', 243.60,  55, 30.00,   0),
  ('Restauração amálgama — Classe II (4 faces)',     'Restaurações / Dentística', '85100129', 284.70,  65, 35.00,   0),
  ('Restauração ionômero — Classe I (1 face)',       'Restaurações / Dentística', '85100137', 139.00,  30, 18.00,   0),
  ('Restauração ionômero — Classe II (2 faces)',     'Restaurações / Dentística', '85100145', 170.40,  40, 22.00,   0),
  ('Restauração temporária / expectante',            'Restaurações / Dentística', '85200085', 100.90,  20, 12.00,   0),

  -- Endodontia
  ('Abertura e curativo endodôntico',                'Endodontia', NULL,       180.00,  40, 30.00,   0),
  ('Canal — incisivo / canino (unirradicular)',      'Endodontia', '85200115', 359.50,  90, 60.00,   0),
  ('Endodontia de anterior',                         'Endodontia', NULL,       400.00,  90, 60.00,   0),
  ('Canal — canino / pré-molar (birradicular)',      'Endodontia', '85200093', 486.50, 120, 75.00,   0),
  ('Canal — molar',                                  'Endodontia', '85200107', 613.50, 180, 95.00,   0),
  ('Retratamento — incisivo / canino',               'Endodontia', '85200115', 359.50, 120, 65.00,   0),
  ('Retratamento — canino / pré-molar',              'Endodontia', '85200093', 486.50, 150, 80.00,   0),
  ('Retratamento — molar',                           'Endodontia', '85200107', 613.50, 210,100.00,   0),
  ('Pulpectomia de urgência',                        'Endodontia', '85200034', 142.00,  45, 30.00,   0),
  ('Pulpotomia',                                     'Endodontia', '85200042', 142.00,  40, 25.00,   0),
  ('Capeamento pulpar direto e indireto',            'Endodontia', NULL,       150.00,  30, 20.00,   0),
  ('Remoção de material obturador (retratamento)',   'Endodontia', '85200069', 275.00,  60, 40.00,   0),
  ('Remoção de núcleo intra-radicular',              'Endodontia', '85200077', 281.00,  60, 35.00,   0),

  -- Cirurgia / Extrações
  ('Exodontia de baixa complexidade',                'Cirurgia / Extrações', NULL,       250.00,  40, 25.00,   0),
  ('Exodontia de RR (raiz residual)',                'Cirurgia / Extrações', NULL,       250.00,  45, 25.00,   0),
  ('Exodontia — dente permanente',                   'Cirurgia / Extrações', '82000875', 208.50,  45, 25.00,   0),
  ('Exodontia — raiz residual',                      'Cirurgia / Extrações', '82000859', 208.50,  45, 25.00,   0),
  ('Exodontia a retalho',                            'Cirurgia / Extrações', '82000816', 249.60,  60, 40.00,   0),
  ('Exodontia — dente incluso / impactado',          'Cirurgia / Extrações', '82001286', 515.60,  90, 55.00,   0),
  ('Exodontia — dente semi-incluso',                 'Cirurgia / Extrações', '82001294', 515.60,  75, 50.00,   0),
  ('Tratamento de alveolite',                        'Cirurgia / Extrações', '82001650', 143.80,  30, 20.00,   0),
  ('Drenagem de abscesso — intra-oral',              'Cirurgia / Extrações', '82001030', 205.50,  30, 25.00,   0),
  ('Drenagem de abscesso — extra-oral',              'Cirurgia / Extrações', '82001022', 205.50,  30, 25.00,   0),
  ('Controle pós-operatório (por sessão)',           'Cirurgia / Extrações', '82000506', 133.00,  20, 10.00,   0),

  -- Prótese
  ('Prótese total acrílica — por arcada',            'Prótese', NULL,       800.00, 120, 30.00, 350),
  ('Prótese parcial removível c/ grampos (PPR)',     'Prótese', NULL,       700.00,  90, 25.00, 300),
  ('Prótese fixa metalo-cerâmica — por elemento',    'Prótese', NULL,       600.00,  90, 30.00, 400),
  ('Coroa de porcelana pura — por elemento',         'Prótese', NULL,       800.00,  90, 35.00, 500),
  ('Reembasamento de prótese (imediato)',            'Prótese', '85400483', 202.50,  45, 25.00,   0),
  ('Reembasamento de prótese (definitivo)',          'Prótese', NULL,       259.30,  60, 30.00,  80),
  ('Recimentação de trabalho protético',             'Prótese', '85400467', 136.00,  20, 15.00,   0),
  ('Remoção de trabalho protético — por elemento',   'Prótese', '85400505', 136.00,  30, 10.00,   0),
  ('Restauração cerâmica inlay / onlay',             'Prótese', '85400513', 734.50,  90, 40.00, 450),

  -- Urgências / Dor
  ('Curativo de demora endodôntico',                 'Urgências / Dor', '85200085', 100.90,  25, 15.00,   0),
  ('Abertura coronária / pulpectomia urgência',      'Urgências / Dor', '85200034', 142.00,  45, 30.00,   0),
  ('Drenagem de abscesso intra-oral (urgência)',     'Urgências / Dor', '82001030', 205.50,  30, 25.00,   0),
  ('Tratamento conservador luxação ATM',             'Urgências / Dor', '82001642', 142.00,  30, 10.00,   0),
  ('Redução simples de luxação da ATM',              'Urgências / Dor', '82001197', 127.80,  20,  5.00,   0);
