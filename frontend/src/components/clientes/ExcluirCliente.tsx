"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Button, Icone, LinhaDeAcao } from "@/design-system";
import { ExcluirCadastro } from "@/components/comum/ExcluirCadastro";
import { clientes, type ClienteCompleto } from "@/lib/api";
import { DialogoDaAcao } from "./AcoesDoCliente";

/**
 * CLI-13: "Excluir" para quem `acoes.excluir` vem (gerente e administrador; `null` para o vendedor). Sem histórico, a confirmação;
 * com histórico, o aviso com o motivo e o caminho da API, e "Inativar cliente" quando `inativar` vem, que abre a inativação da CLI-09.
 */
export function ExcluirCliente({ c, celular, aoAvisar, abertoDeInicio, noPainel }: { c: ClienteCompleto; celular?: boolean; aoAvisar: (aviso: string) => void; abertoDeInicio?: boolean; noPainel?: boolean }) {
  const [inativando, setInativando] = useState(false);
  const acao = c.acoes?.excluir;
  if (!acao) return null;
  return (
    <>
      <ExcluirCadastro
        acao={acao}
        celular={celular}
        rotulo={celular ? "Excluir cliente" : "Excluir"}
        botao={noPainel ? (abrir) => <LinhaDeAcao perigo rotulo="Excluir" detalhe="Só para cadastro feito por engano" icone={<Icone de={Trash2} />} onClick={abrir} /> : undefined}
        coisa="cliente"
        executar={() => clientes.excluir(c.id)}
        chaveDaFicha={["cliente", c.id]}
        chavesDasListas={[["clientes"], ["contadores"]]}
        lista="/clientes"
        caminho={
          acao.inativar
            ? (fechar) => (
                <Button
                  variante="solido"
                  onClick={() => {
                    fechar();
                    setInativando(true);
                  }}
                >
                  Inativar cliente
                </Button>
              )
            : undefined
        }
        estiloDoBotao={celular ? { height: 48 } : { height: 56 }}
        abertoDeInicio={abertoDeInicio}
      />
      {inativando && (
        <DialogoDaAcao
          acao="inativar"
          cliente={c}
          aoFechar={() => setInativando(false)}
          aoConcluir={(aviso) => {
            setInativando(false);
            aoAvisar(aviso);
          }}
        />
      )}
    </>
  );
}
