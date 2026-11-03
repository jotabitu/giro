# T-421 · Mais campos do CRLV-e no cadastro e na ficha do veículo · produto → arquiteto, backend, frontend, qa

**O que foi feito:** as decisões do dono de 29 e 30 out 2026 viraram a `VEI-09`, com os rótulos do CRLV-e, o formato e a faixa de cada campo, quais são opcionais e quem vê. A `VEI-01` passou a listar os obrigatórios do cadastro, e a `VEI-08` passou a ler até 18 campos.

1. **`VEI-09` (nova).** Tabela com 13 campos: combustível (visível no cadastro, editar e ficha), potência (cv, 1 a 999; 0 fica vazio), cilindrada (cc, 1 a 9999), espécie (lista fechada do CTB, art. 96), tipo (texto), carroceria ("NÃO APLICAVEL" fica vazio), lotação (pessoas, 1 a 99; "02P" é 2), peso bruto total (o documento traz em toneladas; guarda-se em kg), número do motor, observações do CRLV-e (até 500), rastreador (número ou IMEI e empresa) e anotações da locadora (até 500). **Todos opcionais**, nenhum muda o status.
2. **Quem vê:** número do motor e observações do CRLV-e só para administrador e gerente; para os outros, ausentes na API e sem espaço na ficha (como a `USR-09`). O resto, todos os perfis que abrem a ficha. Quem edita: administrador e gerente.
3. **Alienação ou restrição** nas observações é só informação: não bloqueia nada nem gera alerta.
4. **`VEI-08`:** lê os 9 campos novos do documento (não lê rastreador nem anotações, que nunca são apagados pela leitura). Lista o que não é lido (categoria do documento, capacidade, CMT, eixos, CRV, código de segurança, DPVAT). O "9 campos preenchidos" do CA-247-01 vira 16 com o mesmo documento.
5. **Seed:** linha nova "Dados do CRLV-e do QXA-4B21" (valores fictícios); os outros 85 veículos ficam sem os campos novos.

**Onde:** `docs/regras-de-negocio.md` (Veículos: `VEI-01`, `VEI-08`, `VEI-09` e nota de mudança; Dados de referência; "Decisões de 29 e 30 out 2026"; Pontos em aberto); `docs/qa/criterios/T-421.md` (CA-421-01 a 14).

**Ponto em aberto para o dono** (padrão A, valendo até a resposta): ler o CRLV-e também no editar do veículo. A) sim, com a `VEI-08`, placa e chassi fixos, CRLV-e de outro veículo recusado ("Este CRLV-e é de outro veículo."), sem substituir o documento CRLV; B) os veículos já cadastrados recebem os campos à mão.

**Leituras do produto (não vieram do dono):** formatos e faixas de cada campo; espécie e tipo como dois campos (a ficha mostra "Passageiro · Motocicleta"); peso em kg; rastreador e anotação visíveis a todos os perfis (o dono só restringiu motor e observações).

**Próximo passo para quem recebe:**
- **Arquiteto:** contrato em `docs/api/veiculos.md` (corpo do cadastro e do editar, ficha com os dois campos ausentes para vendedor, vistoriador e financeiro, `lidos` e `rotulo` da leitura com os campos novos, leitura no editar com o 409 ou 400 de "outro veículo", mensagens de formato) e modelo de dados. Combinar a ordem com a T-415, que mexe na mesma leitura.
- **Backend:** migração, `CAMPOS` de `integracoes/leitura_documentos/crlv.py` com os rótulos da tabela (o `CrlvDetran` dos testes já tem POTÊNCIA/CILINDRADA, MOTOR, LOTAÇÃO, CARROCERIA, PESO BRUTO TOTAL, ESPÉCIE / TIPO e OBSERVAÇÕES DO VEÍCULO no leiaute), seed do QXA-4B21, testes `test_vei_09_...`. O teste do "9 campos preenchidos" (T-265) muda.
- **Frontend:** campos no cadastro, no editar e na ficha, a 1440 e a 390; nada de esconder o motor pela tela: a ausência vem da API.
- **QA:** criar os PDFs fictícios da lista dos critérios; CA-247-01 passa a 16 campos.
