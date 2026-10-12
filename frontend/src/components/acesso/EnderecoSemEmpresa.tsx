import { PaginaAcesso } from "./PaginaAcesso";

/** Login aberto fora do endereço de uma locadora (`localhost`, IP, `admin.*`): não há empresa para entrar. */
export function EnderecoSemEmpresa() {
  return (
    <PaginaAcesso titulo="Este endereço não é de uma locadora" descricao="Entre pelo endereço da sua empresa.">
      <p className="text-body text-ink-muted">Se você não sabe o endereço, peça o link ao administrador da sua locadora.</p>
    </PaginaAcesso>
  );
}
