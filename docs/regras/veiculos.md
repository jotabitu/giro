# Veículos

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

O veículo tem 9 estados e só muda de estado por um evento de outro módulo (locação, vistoria, manutenção, venda, movimentação) ou por ação explícita do gerente. Telas: `Frota`, `Veiculo`, `Manutencao`, `Vendas`.

| Estado | Significa | Pode ser alugado? | Aparece em |
| --- | --- | --- | --- |
| `disponivel` | na filial, pronto | sim | Frota (filtro Disponíveis), Nova locação |
| `reservado` | separado para uma locação confirmada que ainda não saiu (`aguardando_retirada`), com qualquer data de início, ou para uma troca de veículo pedida | só por quem reservou | Frota ("Reservado na LOC-2856"), ficha do veículo, agenda do vistoriador |
| `alugado` | com uma locação ativa | não | Frota, Locações |
| `em_manutencao` | com uma ordem de serviço aberta | não | Frota, Manutenções |
| `indisponivel` | parado por documento vencido, sinistro ou decisão do gerente | não | Frota |
| `a_venda` | saiu da frota de locação e está à venda | não | Vendas, Veículos à venda |
| `vendido` | venda concluída | não | histórico |
| `baixado` | perda total, roubo, sucata | não | histórico |
| `em_movimentacao` | saiu da filial numa movimentação (em trânsito ou num local de apoio, `MOV-03`) | não | Frota, Movimentações |

**Transições permitidas**

| De | Para | Evento que dispara | Quem |
| --- | --- | --- | --- |
| `disponivel` | `reservado` | locação confirmada (sai de `rascunho` para `aguardando_retirada`), com início futuro, hoje ou passado, ou troca de veículo pedida (`LOC-09`, veículo novo) | vendedor, gerente |
| `disponivel` ou `reservado` | `alugado` | vistoria de saída concluída e contrato assinado | sistema |
| `reservado` | `disponivel` | locação cancelada antes da retirada, pedida ou automática por não retirada em 3 dias (`LOC-12`), ou troca de veículo cancelada (`LOC-09`, veículo novo) | sistema |
| `alugado` | `disponivel` | devolução encerrada sem avaria, ou troca de veículo concluída (`LOC-09`, veículo antigo) | sistema |
| `alugado` | `em_manutencao` | devolução encerrada, ou troca de veículo concluída (`LOC-09`, veículo antigo), com avaria marcada "vai para oficina" | sistema |
| `disponivel` | `em_manutencao` | OS aberta (manual ou preventiva) | gerente, vistoriador |
| `em_manutencao` | `disponivel` | OS concluída e veículo liberado | gerente |
| `em_manutencao` | `indisponivel` | OS concluída com CRLV ou seguro vencido (`MAN-05`, `VEI-03`) | sistema |
| `disponivel` | `indisponivel` | documento vence (automático) ou bloqueio manual | sistema, gerente |
| `indisponivel` | `disponivel` | documento renovado ou desbloqueio | gerente |
| `disponivel` | `a_venda` | "Colocar à venda" na ficha | gerente, administrador |
| `a_venda` | `disponivel` | "Voltar para a frota" | gerente, administrador |
| `a_venda` | `vendido` | venda concluída (pagamento ou contrato) | sistema |
| `alugado` | `vendido` | quitação da locação com intenção de compra (`LOC-16`, `VEN-11`) | sistema |
| `vendido` | `a_venda` | venda cancelada (`VEN-07`) | sistema |
| `vendido` | `indisponivel` | veículo recomprado numa troca (`VEN-05`, `VEI-07`) | sistema |
| qualquer, exceto `alugado` | `baixado` | baixa com motivo; com movimentação aberta, ela vira `cancelada` (`MOV-03`) | administrador |
| `disponivel` | `em_movimentacao` | movimentação iniciada (`MOV-03`) | sistema |
| `em_movimentacao` | `disponivel` | chegada registrada no destino, com CRLV e seguro em dia (`MOV-05`) | sistema |
| `em_movimentacao` | `indisponivel` | chegada registrada com CRLV ou seguro vencido (`MOV-05`, `VEI-03`) | sistema |

Qualquer outra transição é recusada pelo backend com erro de regra (HTTP 409).

**Regras**

- `VEI-01` Placa e chassi únicos por empresa, em qualquer estado do veículo; chassi com 17 caracteres; km nunca diminui (vistoria com km menor que o anterior é recusada, salvo correção pelo gerente com motivo). Obrigatórios no cadastro: placa, chassi, marca, modelo, ano de fabricação, ano do modelo, cor, km, categoria de preço e filial. O resto é opcional: Renavam, capacidade do tanque, valor e data de compra e os campos da `VEI-09` (combustível, dados do CRLV-e, rastreador e anotações).
- `VEI-02` O km do veículo é atualizado a cada vistoria e a cada OS. Ele dispara as preventivas (`MAN-03`).
- `VEI-03` Documentos: alerta 30 dias antes do vencimento; no dia do vencimento de CRLV ou seguro, o veículo disponível vai para `indisponivel`. Veículo `alugado`, `reservado` ou `em_manutencao` não muda de status, mas gera tarefa urgente para os gerentes da filial (`FIL-02`). A retirada de veículo com CRLV ou seguro vencido é recusada até o documento ser renovado (vistoria de saída, `VIS-01`). O veículo cujo CRLV ou seguro venceu durante a OS vai para `indisponivel` ao concluir a OS (`MAN-05`).
- `VEI-04` Transferência entre filiais só com o veículo `disponivel`. Grava a filial de origem e destino. É o único jeito de um veículo mudar de filial: a devolução é sempre na filial da locação e a frota não é compartilhada (`FIL-05`). Se a categoria do veículo é só da filial de origem (`FIL-04`), a transferência pede a categoria no destino: uma categoria ativa, do mesmo tipo de veículo, da empresa ou da filial de destino. Sem ela, a transferência é recusada. Categoria da empresa passa direto, e o veículo continua nela. Como só se transfere veículo `disponivel`, nenhuma locação aberta muda de preço: a categoria nova vale a partir da próxima locação (`LOC-01`).
- `VEI-05` "Rendeu no ano" na ficha = receitas de locação recebidas do veículo − custos de manutenção e despesas ligadas a ele, no ano corrente. Ele e o custo de manutenção do ano só aparecem para administrador, gerente e financeiro (`USR-09`). O "Custo de manutenção" do ano soma só as despesas do veículo nas categorias manutenção e peças; o "Rendeu no ano" desconta todas as despesas ligadas ao veículo, de qualquer categoria (IPVA, seguro, multa, combustível também). Nos dois, sem as `recusada`. A lista completa fica em "Despesas do veículo" (`FIN-17`).
- `VEI-06` Ocupação = dias alugado ÷ dias que o veículo esteve na frota no período (exclui `a_venda`, `vendido`, `baixado`). Ocupação da frota = média ponderada pelos dias. Conta o tempo exato entre as mudanças de status, com fração de dia: um veículo alugado às 14:00 conta 0,42 daquele dia (10 h ÷ 24 h).
- `VEI-07` Veículo que volta para a empresa depois de vendido (recompra numa troca, `VEN-05`) reaproveita o cadastro existente, achado pelo chassi, e não ganha outro: vai de `vendido` para `indisponivel` até a vistoria, e o histórico continua no mesmo veículo.
- `VEI-08` **Preencher pelo CRLV-e** (tela `Veiculo-Novo`, "Preencher pelo documento"). Entra no MVP (decisão de 16 out 2026). É opcional: o cadastro manual continua completo sem ele. Quem cadastra veículo (tabela de perfis) envia o PDF do CRLV-e, o arquivo digital emitido pelo Detran ou pela Carteira Digital de Trânsito, e não uma foto do papel.
  - **O que se preenche sozinho (até 18 campos):** placa, chassi, Renavam, marca, modelo, ano de fabricação, ano do modelo, cor e combustível, e os 9 campos do documento da `VEI-09` (potência, cilindrada, espécie, tipo, carroceria, lotação, peso bruto total, número do motor e observações do veículo). A marca e o modelo vêm da lista do cadastro (FIPE): se o texto do documento não achar um modelo da lista, os dois ficam para a pessoa escolher, com o texto lido como dica. A tela diz quantos campos foram preenchidos ("CRLV-e lido · 16 campos preenchidos"), pelo número que a API devolve. Campo que o documento traz vazio, com asterisco ou como "NÃO APLICAVEL" não conta e não muda o que estava na tela.
  - **O que não se preenche:** a validade do CRLV, porque o documento traz o exercício (o ano), e não a data, que depende do calendário de licenciamento do Detran de cada estado; a pessoa informa a validade. Km, categoria de preço, filial, finalidade, valores, seguro, rastreador e anotações também ficam com a pessoa. Nome e CPF ou CNPJ do proprietário não são lidos nem guardados. Também não são lidos a categoria do documento (particular ou aluguel, que não é a categoria de preço), a capacidade de carga, a CMT, os eixos, o número do CRV, o código de segurança do CLA e o bloco do seguro DPVAT.
  - **A pessoa confere antes de salvar.** Nada é gravado na leitura: os campos lidos aparecem marcados como "lido do documento", editáveis, e substituem o que estava neles. Só "Salvar veículo" grava, com as validações de sempre (`VEI-01`: placa e chassi únicos, chassi com 17 caracteres). Ao salvar, o PDF lido fica anexado como o documento CRLV do veículo, com o exercício lido.
  - **Quando não dá para ler** (arquivo que não é CRLV-e, sem texto, protegido por senha ou acima do tamanho; e, se a ADR conferir a assinatura digital, com a assinatura inválida): "Não conseguimos ler este documento. Preencha os campos à mão.", e nenhum campo muda. Leitura parcial preenche só o que leu e diz quantos.
  - O evento de auditoria do cadastro diz que os campos vieram do documento.
- `VEI-10` **Fotos do veículo** (cadastro `Veiculo-Novo`, editar veículo e ficha `Veiculo`). O veículo tem duas origens de foto, que nunca se misturam: a **galeria do veículo**, com as fotos de cadastro para o catálogo e o anúncio (`VEN`, T-418), e as **fotos da última vistoria** (`VIS-01`), que só servem para conferir o estado.
  - **Galeria: limite e arquivo.** Até 20 fotos por veículo. Cada foto em JPG ou PNG, até 10 MB, como na vistoria; o sistema reprocessa a imagem e tira os metadados de localização. Foto fora disso é recusada no envio, com a mensagem no campo ("Envie uma foto JPG ou PNG de até 10 MB."; "O veículo já tem 20 fotos. Apague uma para enviar outra."), e as outras do mesmo envio seguem. A galeria pode ficar vazia: nenhuma foto é obrigatória para alugar, e o catálogo decide o que pede (T-418).
  - **Galeria: capa e ordem.** Uma foto é a capa, a que aparece primeiro na ficha e no catálogo. A primeira enviada vira capa; a pessoa escolhe outra com "Usar como capa". Apagada a capa, a mais antiga das que ficam vira capa. As outras seguem a ordem de envio.
  - **Galeria: quem mexe.** Enviar, trocar (substituir a foto, mantendo a posição e a capa), apagar e escolher a capa ficam no editar do veículo, para quem cadastra e edita veículo: administrador e gerente (tabela de perfis). Valem em qualquer estado, menos `vendido` e `baixado`, em que a galeria fica só para ver. O suporte Giro, mesmo em "ver e editar", só vê (403 `PLT-07`).
  - **Galeria no cadastro** (decisão do dono de 05 nov 2026, T-437). O cadastro do veículo novo tem o mesmo bloco de fotos, para as mesmas pessoas (administrador e gerente; o suporte Giro não envia, 403 `PLT-07`). As fotos não vão junto com o cadastro: a pessoa as escolhe antes de salvar e, depois de "Salvar veículo" gravar o veículo, a tela as envia logo em seguida, na mesma tela, uma de cada vez, como no editar.
    - **Antes de salvar,** nada é enviado. A pessoa vê as escolhidas em miniatura, pode tirar uma e marcar outra como capa ("Usar como capa"); sem escolha, a capa é a primeira. O limite de 20 vale para as escolhidas: a 21ª não entra na lista ("O veículo pode ter até 20 fotos."). A tela pode recusar já na escolha o arquivo que não é JPG ou PNG ou passa de 10 MB, com "Envie uma foto JPG ou PNG de até 10 MB."; a palavra final é a do envio.
    - **Se o cadastro falha** (placa ou chassi repetidos, campo inválido, limite do plano), nenhuma foto é enviada e o veículo não existe. As fotos escolhidas continuam na tela, e a pessoa corrige o cadastro e salva de novo, sem escolher outra vez.
    - **Depois de salvar,** a capa sobe primeiro e as outras na ordem da escolha. A tela mostra o andamento ("Enviando fotos · 2 de 5") e, no fim, abre a ficha do veículo, como hoje. Foto recusada no envio não impede as outras nem desfaz o veículo, que já está gravado: a tela mostra a recusa no item e fica parada, com "Ir para o veículo" (e "Tentar de novo" quando a falha é de conexão, e não do arquivo), e a foto que ficou de fora se envia depois pelo editar. Se a pessoa sai da tela antes do fim, o veículo fica com as fotos que já subiram.
    - Capa, ordem, limite, formato e auditoria são os da galeria no editar: um evento de cadastro do veículo e um evento de envio por foto.
  - **Galeria: apagar.** A foto apagada sai da galeria, da ficha e do catálogo e não volta pela tela; o arquivo fica guardado, inativo, e o evento de auditoria diz quem apagou e quando. Enviar, trocar, apagar e mudar a capa geram evento de auditoria do veículo, sem a imagem (`AUD-01`).
  - **Ficha: ver, ampliar e baixar.** A ficha mostra a galeria (capa primeiro) e, à parte, as fotos da última vistoria concluída do veículo, com o tipo, a data e a locação ("Vistoria de saída · LOC-2841 · 23 set"), todas as dela, com as de avaria. Tocar numa foto abre o visualizador: ampliada, passa para a anterior e a próxima da mesma origem, e "Baixar" salva a foto como foi guardada (já reprocessada). O arquivo baixado leva a placa no nome: "QXA-4B21-galeria-1.jpg", "QXA-4B21-vistoria-saida-frente.jpg". Cada visualização e cada download usam o link temporário de 15 minutos (`AUD-05`).
  - **Ficha: quem vê.** A galeria, para todos os perfis que consultam o veículo. As fotos da vistoria, para quem faz vistoria (administrador, gerente, vendedor e vistoriador), como o bloco da vistoria na ficha hoje; o financeiro não as recebe. Sem galeria, a ficha diz "Nenhuma foto do veículo." e, para quem edita, "Adicionar fotos" leva ao editar. Sem vistoria concluída, a seção da vistoria não aparece.
  - As fotos da vistoria não entram na galeria nem no catálogo, e a galeria não vale como foto de vistoria (`VIS-01`).
- `VEI-09` **Dados do documento, rastreador e anotações** (cadastro `Veiculo-Novo`, editar e ficha `Veiculo`). Além dos campos da `VEI-01`, o veículo guarda os campos abaixo. **Todos são opcionais**: nenhum impede salvar, nenhum muda o status do veículo, e o veículo cadastrado antes fica com eles vazios até alguém preencher. Quem edita é quem cadastra e edita veículo (administrador e gerente, tabela de perfis). Na ficha, campo vazio aparece como "—".

  | Campo na tela | Rótulo no CRLV-e | Como se guarda e se mostra | Quem vê na ficha |
  | --- | --- | --- | --- |
  | Combustível | COMBUSTÍVEL | lista fechada: gasolina, etanol, flex, diesel, elétrico, híbrido (`ALCOOL/GASOLINA` é flex) | todos |
  | Potência | POTÊNCIA/CILINDRADA (antes da barra) | número inteiro em cv, de 1 a 999: "15 cv". Potência 0, que o documento traz em muitas motos, fica vazia | todos |
  | Cilindrada | POTÊNCIA/CILINDRADA (depois da barra) | número inteiro em cc, de 1 a 9999, sem os zeros à esquerda ("0162" é 162): "162 cc". Elétrico fica vazio | todos |
  | Espécie | ESPÉCIE / TIPO (1ª palavra) | lista fechada do Código de Trânsito (art. 96): passageiro, carga, misto, competição, tração, especial, coleção | todos |
  | Tipo | ESPÉCIE / TIPO (o resto) | texto até 30 caracteres, como vem no documento: "Motocicleta", "Motoneta", "Automóvel", "Caminhonete". A ficha mostra os dois juntos: "Passageiro · Motocicleta" | todos |
  | Carroceria | CARROCERIA | texto até 30 caracteres. "NÃO APLICAVEL", comum nas motos, fica vazio | todos |
  | Lotação | LOTAÇÃO | número inteiro de pessoas, de 1 a 99, com o motorista ("02P" é 2): "2 pessoas" | todos |
  | Peso bruto total | PESO BRUTO TOTAL | o documento traz em toneladas ("0,29" ou "0.29"); guarda-se em kg inteiros: "290 kg" | todos |
  | Número do motor | MOTOR | letras e números, até 21 caracteres, em maiúsculas | administrador e gerente |
  | Observações do CRLV-e | OBSERVAÇÕES DO VEÍCULO | texto até 500 caracteres, como vem no documento, com as quebras de linha | administrador e gerente |
  | Rastreador · número ou IMEI | — (fora do documento) | letras e números, até 20 caracteres; o IMEI tem 15 dígitos, mas não é exigido | todos |
  | Rastreador · empresa | — (fora do documento) | texto até 60 caracteres | todos |
  | Anotações | — (da locadora) | texto livre até 500 caracteres, por exemplo "Risco no tanque, lado esquerdo" | todos |

  - **Número do motor e observações do CRLV-e** só para administrador e gerente (decisão do dono em 30 out 2026). Para os outros perfis, a API não manda os dois campos (ausentes, e não vazios), e a ficha não mostra as duas linhas, sem deixar espaço, como na `USR-09`.
  - **Alienação fiduciária ou restrição** (ex.: "ALIENACAO FIDUCIARIA", "RESTRICAO JUDICIAL") nas observações é só informação: não bloqueia locação, venda, movimentação nem transferência, e não gera alerta.
  - **Anotações** são da locadora e nunca vêm do CRLV-e: a leitura não as preenche nem apaga. Servem para o que a equipe precisa saber do veículo e não é avaria de vistoria (a avaria segue na vistoria, `VIS`).
  - **Rastreador:** número e empresa ficam no veículo, em campos simples; o documento "rastreador" (validade e arquivo, `VEI-03`) continua à parte. Quando houver integração com rastreador, ela lê o número daqui (decisão do dono em 30 out 2026).
  - **Valor fora do formato** (potência 1500, lotação 0, peso com letras) é recusado no campo com a mensagem da API ("Informe a potência em cv, de 1 a 999."). Na leitura do CRLV-e, o campo que não passa no formato fica vazio e fora da conta, como os outros da `VEI-08`.
  - **Auditoria:** mudar qualquer campo desta regra no editar gera o evento de edição do veículo, com o antes e o depois, como os outros campos (`AUD-01`).
- `VEI-11` **Tipo do veículo: moto ou carro** (cadastro `Veiculo-Novo` e editar veículo; decisão do dono de 05 nov 2026). O tipo é o `tipo_veiculo` que já filtra a Frota e a Nova locação. Ele é da categoria de preço (`LOC-01`): o veículo é do tipo da categoria em que está, e não há outro campo de tipo no veículo, para os dois nunca discordarem. O tipo decide a CNH exigida (`CLI-02`) e os itens da vistoria (`VIS-01`).
  - **No cadastro e no editar,** o tipo aparece como campo obrigatório, Moto ou Carro, logo antes da categoria de preço. A categoria só lista as categorias ativas do tipo escolhido, da empresa ou da filial do veículo (`FIL-04`). No cadastro, o tipo começa em Moto. No editar, ele começa no tipo da categoria atual e pode ser trocado por quem edita veículo (administrador e gerente, tabela de perfis).
  - **Trocar o tipo troca a categoria.** Ao trocar o tipo na tela, a categoria atual sai do campo, que fica vazio para a pessoa escolher outra do tipo novo, na mesma tela. Voltar ao tipo anterior antes de salvar devolve a categoria que estava. Tipo e categoria se gravam juntos, num só "Salvar": a API recebe só a categoria nova, e o tipo vem dela. Salvar com o campo vazio é recusado no campo: "Escolha a categoria de preço." Sem categoria ativa do tipo na filial, a lista fica vazia com "Nenhuma categoria de carro nesta filial. Cadastre uma em Preços." ("de moto" no outro caso), e não dá para salvar com esse tipo.
  - **Recusada com locação aberta.** Com o veículo `reservado` ou `alugado` (locação em `aguardando_retirada`, `ativa` ou `devolucao_atrasada`, ou troca de veículo pedida, `LOC-09`), a troca de tipo é recusada (HTTP 409 `tipo_com_locacao_aberta`): "Este veículo está na LOC-2841. Troque o tipo depois da devolução." No editar, o campo do tipo aparece travado, com essa frase de dica. Motivo: a CNH do cliente e a vistoria de saída já foram conferidas pelo tipo atual, e o preço contratado é de uma categoria desse tipo (`LOC-15`). Nos outros estados, a troca é livre. Trocar de categoria **sem** mudar o tipo continua livre em qualquer estado em que o veículo se edita, e a locação aberta mantém o preço dela (`LOC-15`).
  - **Auditoria:** a troca gera o evento de edição do veículo, com a categoria e o tipo de antes e de depois (`AUD-01`).
