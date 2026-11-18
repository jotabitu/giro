import { ChamadaFinal } from "./ChamadaFinal";
import { ComoFunciona } from "./ComoFunciona";
import { Hero } from "./Hero";
import { Modulos } from "./Modulos";
import { Nav } from "./Nav";
import { Perguntas } from "./Perguntas";
import { Planos } from "./Planos";
import { Problema } from "./Problema";
import { WhiteLabel } from "./WhiteLabel";
import "./landing.css";

/** Landing pública do Giro (T-489), porta de giro-landing/index.html: 9 seções nesta ordem ("Quem usa" oculta, T-490). */
export function Landing() {
  return (
    <div className="lp">
      <a className="skip" href="#conteudo">Pular para o conteúdo</a>
      <Nav />
      <main id="conteudo">
        <Hero />
        <Problema />
        <ComoFunciona />
        <Modulos />
        <WhiteLabel />
        {/* TODO(landing): "Quem usa" oculta por decisão do dono (T-490) até haver depoimentos reais. Para voltar,
            renderize <QuemUsa /> aqui, entre WhiteLabel e Planos. */}
        <Planos />
        <Perguntas />
      </main>
      <ChamadaFinal />
    </div>
  );
}
