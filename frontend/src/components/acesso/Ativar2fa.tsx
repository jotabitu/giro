"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";
import { Button, CodigoVerificacao, Icone } from "@/design-system";
import { contas, type Eu } from "@/lib/api";
import { mensagemDoErro } from "@/lib/erros";
import { Aviso } from "./Aviso";
import { PaginaAcesso, Passo } from "./PaginaAcesso";

/**
 * Ativar verificação em 2 etapas (Ativar-2FA). Quem chega por `etapa: configurar_2fa` usa o token_pre_2fa.
 * A API decide se o perfil exige (`exige`); a tela só mostra o aviso.
 */
export function Ativar2fa({ tokenPre, exige, aoConcluir }: { tokenPre: string; exige: boolean; aoConcluir: (usuario: Eu) => void }) {
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [concluido, setConcluido] = useState<{ usuario: Eu; codigos: string[] } | null>(null);
  const [guardei, setGuardei] = useState(false);

  const segredo = useQuery({ queryKey: ["2fa-configurar", tokenPre], queryFn: () => contas.configurar2fa(tokenPre), staleTime: Infinity });

  async function ativar() {
    setErro(null);
    setEnviando(true);
    try {
      const r = await contas.verificar2fa(tokenPre, { codigo });
      if (r.etapa !== "pronto") throw new Error("etapa inesperada");
      if (r.codigos_recuperacao?.length) setConcluido({ usuario: r.usuario, codigos: r.codigos_recuperacao });
      else aoConcluir(r.usuario);
    } catch (e) {
      setErro(mensagemDoErro(e));
      setCodigo("");
    } finally {
      setEnviando(false);
    }
  }

  function baixar(codigos: string[]) {
    const url = URL.createObjectURL(new Blob([codigos.join("\n") + "\n"], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "codigos-de-recuperacao.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <PaginaAcesso
      titulo="Ativar verificação em 2 etapas"
      descricao="Além da senha, você passa a digitar um código de 6 números do celular. Assim ninguém entra na sua conta só com a senha."
    >
      {exige && !concluido && <Aviso>Seu perfil exige a verificação em 2 etapas. Termine este passo para entrar no sistema.</Aviso>}

      {!concluido ? (
        <>
          <Passo numero={1} titulo="Adicione a conta ao aplicativo">
            {segredo.isError ? (
              <Aviso tipo="erro">{mensagemDoErro(segredo.error)}</Aviso>
            ) : (
              <>
                <div className="flex flex-col gap-4 md:flex-row md:items-center">
                  <div className="w-fit rounded-lg border border-line p-3" role="img" aria-label="QR code para o aplicativo autenticador">
                    {/* O QR precisa de fundo branco e traço escuro para ser lido; não segue o tema. */}
                    {segredo.data ? (
                      <QRCodeSVG value={segredo.data.otpauth_uri} size={150} bgColor="#ffffff" fgColor="#111114" />
                    ) : (
                      <div className="size-[150px]" aria-hidden="true" />
                    )}
                  </div>
                  <ol className="list-decimal pl-5 text-body text-ink-muted">
                    <li>Instale um aplicativo autenticador no celular (Google Authenticator ou Microsoft Authenticator).</li>
                    <li>Aponte a câmera para o código ao lado.</li>
                    <li>Digite os 6 números que aparecem no aplicativo.</li>
                  </ol>
                </div>
                <p className="text-caption text-ink-muted">
                  Sem câmera? Digite a chave <span className="wl-mono text-ink">{segredo.data?.chave ?? "…"}</span>
                </p>
              </>
            )}
          </Passo>
          <Passo numero={2} titulo="Digite o código">
            <CodigoVerificacao rotulo="Código do aplicativo" valor={codigo} aoMudar={setCodigo} erro={erro ?? undefined} />
            <div className="grid md:flex">
              <Button variante="solido" disabled={codigo.length < 6 || enviando || !segredo.data} onClick={ativar}>
                {enviando ? "Verificando…" : "Ativar verificação"}
              </Button>
            </div>
          </Passo>
        </>
      ) : (
        <Passo numero={3} titulo="Guarde os códigos de recuperação">
          <p className="text-body text-ink-muted">Se você perder o celular, cada código abaixo vale para um acesso. Eles não aparecem de novo.</p>
          <ul className="grid grid-cols-2 gap-3 md:grid-cols-4" aria-label="Códigos de recuperação">
            {concluido.codigos.map((c) => (
              <li key={c} className="wl-mono rounded-md bg-surface-sunken px-3 py-2 text-center">
                {c}
              </li>
            ))}
          </ul>
          <div>
            <Button variante="quieto" compacto icone={<Icone de={Download} />} onClick={() => baixar(concluido.codigos)}>
              Baixar arquivo
            </Button>
          </div>
          <label className="flex items-center gap-2 text-body">
            <input type="checkbox" checked={guardei} onChange={(e) => setGuardei(e.target.checked)} className="size-5 accent-[var(--solid)]" />
            Guardei os códigos em um lugar seguro
          </label>
          <div className="grid md:flex">
            <Button variante="solido" disabled={!guardei} onClick={() => aoConcluir(concluido.usuario)}>
              Concluir
            </Button>
          </div>
        </Passo>
      )}
    </PaginaAcesso>
  );
}
