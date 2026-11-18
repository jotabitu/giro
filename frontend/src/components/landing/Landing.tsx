import { ChamadaFinal } from "./ChamadaFinal";
import { ComoFunciona } from "./ComoFunciona";
import { Hero } from "./Hero";
import { Modulos } from "./Modulos";
import { Nav } from "./Nav";
import { Perguntas } from "./Perguntas";
import { Planos } from "./Planos";
import { Problema } from "./Problema";
import { QuemUsa } from "./QuemUsa";
import { WhiteLabel } from "./WhiteLabel";
import "./landing.css";

/** Landing pública do Giro (T-489), porta de giro-landing/index.html: 10 seções nesta ordem. */
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
        <QuemUsa />
        <Planos />
        <Perguntas />
      </main>
      <ChamadaFinal />
    </div>
  );
}
