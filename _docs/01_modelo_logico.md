# Modelo Lógico Relacional — OTO (Base de Dados Principal)

Notação: <u>sublinhado</u> = PK; * = NOT NULL; (azul) = FK.

## Inventário Turístico
- **Segmento** = {id_segmento(PK), nome, descricao}
- **Item_Inventario** = {id_item(PK), nome, razao_social, tipo_documento, documento, endereco, bairro, latitude, longitude, status}
- **Campo_Segmento** = {id_campo(PK), id_segmento*(FK→Segmento), nome, tipo_dado, obrigatorio}
- **Preenchimento** = {id_item(PK,FK→Item_Inventario), id_campo(PK,FK→Campo_Segmento), valor}  (PK composta)
- **Participa** = {id_item(PK,FK→Item_Inventario), id_segmento(PK,FK→Segmento), classificacao}
- **Profissional_Turismo** = {id_profissional(PK), nome, cpf, endereco, classificacao}
- **Categoria_Atuacao_Profissional** = {id_profissional(PK,FK→Profissional_Turismo), categoria_atuacao(PK)}
- **Contato** = {id_contato(PK), id_item(FK→Item_Inventario), id_profissional(FK→Profissional_Turismo), tipo, valor, finalidade}
- **Cadastur** = {id_cadastur(PK), id_item(FK→Item_Inventario), id_profissional(FK→Profissional_Turismo), numero, tipo, situacao, vencimento}
- **Cnae** = {codigo(PK), descricao}
- **Possui_Atividade** = {id_item(PK,FK→Item_Inventario), codigo(PK,FK→Cnae)}
- **Vinculo_Profissional_Item** = {id_profissional(PK,FK→Profissional_Turismo), id_item(PK,FK→Item_Inventario)}

## Módulo ODS (complementar)
- **ODS** = {id_ods(PK), nome}
- **Indicador_ODS** = {id_indicador(PK), nome, descricao, meta}
- **ODS_Indicador** = {id_ods(PK,FK→ODS), id_indicador(PK,FK→Indicador_ODS)}
- **Campo_Indicador** = {id_campo(PK,FK→Campo_Segmento), id_indicador(PK,FK→Indicador_ODS)}
- **Dado_Pesquisa_ODS** = {id_dado(PK), id_indicador*(FK→Indicador_ODS), origem_pesquisa, data_referencia, valor, observacao}
- **Medicao_Indicador** = {id_medicao(PK), id_indicador*(FK→Indicador_ODS), periodo, valor_calculado, data_calculo}

## Auditoria e Importação
- **Usuario** = {id_usuario(PK), nome, email, perfil, ativo}
- **Alteracao_Inventario** = {id_alteracao(PK), id_usuario*(FK→Usuario), id_item*(FK→Item_Inventario), data_hora, acao, campo_alterado, valor_anterior, valor_novo}
- **Fonte_Dados** = {id_fonte(PK), nome, tipo, formato}
- **Importacao** = {id_importacao(PK), id_usuario*(FK→Usuario), id_fonte*(FK→Fonte_Dados), data_hora, arquivo_origem, status, qtd_registros}
- **Inconsistencia_Importacao** = {id_inconsistencia(PK), id_importacao*(FK→Importacao), referencia_origem, tipo, descricao, status}
- **Gerencia** = {id_usuario(PK,FK→Usuario), id_item(PK,FK→Item_Inventario)}

## Integridade referencial (todas as FKs)
Participa[id_item]→Item_Inventario; Participa[id_segmento]→Segmento;
Campo_Segmento[id_segmento]→Segmento; Preenchimento[id_item]→Item_Inventario;
Preenchimento[id_campo]→Campo_Segmento; Categoria_Atuacao_Profissional[id_profissional]→Profissional_Turismo;
Contato[id_item]→Item_Inventario; Contato[id_profissional]→Profissional_Turismo;
Cadastur[id_item]→Item_Inventario; Cadastur[id_profissional]→Profissional_Turismo;
Possui_Atividade[id_item]→Item_Inventario; Possui_Atividade[codigo]→Cnae;
Vinculo_Profissional_Item[*]→Profissional_Turismo/Item_Inventario;
ODS_Indicador[id_ods]→ODS; ODS_Indicador[id_indicador]→Indicador_ODS;
Campo_Indicador[id_campo]→Campo_Segmento; Campo_Indicador[id_indicador]→Indicador_ODS;
Dado_Pesquisa_ODS[id_indicador]→Indicador_ODS; Medicao_Indicador[id_indicador]→Indicador_ODS;
Alteracao_Inventario[id_usuario]→Usuario; Alteracao_Inventario[id_item]→Item_Inventario;
Importacao[id_usuario]→Usuario; Importacao[id_fonte]→Fonte_Dados;
Inconsistencia_Importacao[id_importacao]→Importacao;
Gerencia[id_item]→Item_Inventario; Gerencia[id_usuario]→Usuario.
