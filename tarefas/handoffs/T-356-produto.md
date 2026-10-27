# T-356 · Regras das decisões de 25 out · produto → orquestrador, arquiteto (T-358), backend, qa

**O que foi feito:**
- `docs/regras-de-negocio.md`:
  - **Fase 2:** comissões (`FIN-09`, `FIN-10`, `AUT-10`), relatórios e DRE (`FIN-13`, `FIN-14`), a tela Minha conta (`USR-02`), o expurgo da auditoria (`AUT-16`) e a implantação parada (`AUT-14`, `IMP-06`).
  - **Catálogo da fase 1** (`PLT-11`, `PLT-12`): só o Essencial e o Profissional são vendidos, e a API recusa a mudança para o Completo ("O plano Completo ainda não está à venda.").
  - **Suporte no MVP** (`PLT-07`): a equipe abre o acesso pelo Django Admin. O administrador bloqueia no cartão "Acesso do suporte Giro" em Configurações.
  - **NFS-e** (`PLT-15`): sai à mão até a T-197.
  - **Regra nova `IMP-07`:** o que marca cada passo do assistente. Preços: a primeira categoria com preço vigente. Equipe: o primeiro convite enviado. Filial: a matriz criada. Contrato: o primeiro modelo publicado. Recebimentos: a subconta aprovada. Pular não marca.
  - Seção "Decisões de 25 out 2026" e um item novo em "Pontos em aberto".
- `docs/qa/criterios/assinatura.md`:
  - CA-ASS-70 novo: o Completo fora da venda;
  - CA-ASS-20, 22, 24 e 29 ajustados;
  - os critérios que dependem do Completo, de vendas ou de comissão ficaram marcados como fase 2.

**O dono precisa responder** (item "Preço do Profissional na fase 1" em "Pontos em aberto"):
1. **Preço:** mantém R$ 449,00 (R$ 4.490,00 no anual) ou passa a outro.
2. **Limites:** mantém 150 veículos, 3 filiais e 10 usuários ou muda.
3. **Texto:** aprova "Tudo do Essencial, mais despesas; Pix e boleto automáticos e cobrança pelo WhatsApp" ou pede outro.

Se o preço mudar, mudam também o seed (FAT-0001 de R$ 449,00) e os critérios que usam esse valor.

**Tarefas que decorrem** (para o orquestrador numerar):
- **backend:**
  - parar de lançar a comissão de locação, que hoje nasce pela `test_fin_09_ca_015_25_*`, e passar esses testes para a fase 2;
  - recusar a mudança para o Completo e tirá-lo do catálogo e do cartão (`test_plt_11_completo_fora_da_venda`);
  - texto do Profissional em `plataforma/catalogo.py` e na migração dos planos.
- **frontend:** cartão "Acesso do suporte Giro" em Configurações (`POST /api/suporte/bloquear/` e `/liberar/`).
- **arquiteto (T-358):** usar a `IMP-07` no contrato dos passos.

**Ficou de fora:** não mexi nas telas de Veículos nem no `plano.md`.
