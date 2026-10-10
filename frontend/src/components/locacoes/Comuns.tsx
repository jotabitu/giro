import Link from "next/link";
import { mensagemDoErro } from "@/lib/erros";

/** Erro de uma página inteira (404, 403, falha de rede): a mensagem da API e o caminho de volta. */
export function TelaDeErro({ erro, voltar }: { erro: unknown; voltar: { href: string; rotulo: string } }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-4">
      <p className="text-body">{mensagemDoErro(erro)}</p>
      <Link href={voltar.href} className="wl-btn">
        {voltar.rotulo}
      </Link>
    </div>
  );
}
