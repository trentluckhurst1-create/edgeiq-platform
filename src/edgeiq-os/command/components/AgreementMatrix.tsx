
import { CommandService } from "../../services/CommandService";

export function AgreementMatrix() {

  const matrix = CommandService.buildAgreementMatrix();

  return (

    <section className="eiq-agreement">

      <header>

        <span>EDGEIQ Intelligence</span>

        <strong>Agreement Matrix</strong>

      </header>

      <div className="eiq-agreement-score">

        {matrix.agreement}%

      </div>

      <div className="eiq-agreement-grid">

        {matrix.items.map(item=>(

          <article key={item.engine}>

            <strong>{item.engine}</strong>

            <span>{item.status}</span>

          </article>

        ))}

      </div>

    </section>

  );

}
