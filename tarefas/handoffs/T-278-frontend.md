# T-278 · Ficha do veículo: painel de locações do vistoriador · frontend → orquestrador, design-system

**O que foi feito:** o painel Locações da ficha do veículo (desktop) some quando a API recusa a lista com 403, sem olhar o perfil. A consulta não repete a tentativa nesse caso. Outros erros continuam aparecendo no painel.
**Onde:** frontend/src/components/frota/FichaVeiculo.tsx (`semAcesso`), FichaVeiculo.test.tsx
**Regras cobertas:** USR-09 (testes: "T-278" em FichaVeiculo.test.tsx)
**O que ficou de fora:** a branch é empilhada sobre a t-243-editar-veiculo (PR #268); a T-278 está no backlog da t-272 (PR #270), então esse PR remove a linha de lá ao juntar. O celular não tem o painel de locações na ficha. O teste usa marcação estática com o erro no cache.
**Próximo passo para quem recebe:** orquestrador abre o PR depois do #268; conferir o vistoriador no navegador.
