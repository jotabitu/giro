# T-100 · Frota com um botão só de cadastrar veículo · frontend → orquestrador

**O que foi feito:** a Frota (`/veiculos`) mostra um único botão preto (`wl-btn wl-btn--solid`) com ícone Plus e o texto "Cadastrar veículo", no desktop e no celular, para quem tem `pode.veiculos === "editar"`. O botão de ícone (`wl-icon-btn md:hidden`) saiu.
**Onde:** frontend/src/components/frota/ListaVeiculos.tsx, frontend/src/components/frota/NovoVeiculo.test.tsx
**Regras cobertas:** VEI-01, VEI-02 (sem mudança de comportamento; só a apresentação do botão). Teste: o link para `/veiculos/novo` aparece uma vez, com `wl-btn--solid`, sem `wl-icon-btn` e sem `aria-label`; quem não edita não vê o botão.
**Check:** lint, typecheck, Vitest (158 testes, 20 arquivos) e build passaram.
**Mesmo padrão em outras telas (nada alterado):** em `NovoVeiculoForm.tsx`, linha 151 (`wl-icon-btn md:hidden`, voltar para a Frota) e linha 164 (`wl-btn hidden md:inline-flex`, botão desabilitado "Em breve"). Pelo mesmo motivo, as duas classes `wl-` devem anular o `hidden`/`md:hidden`, então esses elementos provavelmente aparecem nos dois tamanhos. Não conferi no navegador. Fora isso, o grep em `frontend/src` não achou outro caso.
**Próximo passo para quem recebe:** abrir o PR; decidir se vira tarefa a correção dos dois casos acima (a causa é o design system: a classe `wl-` define `display` e vence o utilitário).
