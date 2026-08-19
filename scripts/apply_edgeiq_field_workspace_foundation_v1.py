from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FIELD_COMPONENT = '''type FieldWorkspaceProps = {
  field: any[];
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  onOpenRunner: (index: number) => void;
};

function firstValue(row: any, keys: string[]): any {
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], row);
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return undefined;
}

function statusForRunner(row: any, clean: (value: any) => string): string {
  const raw = clean(firstValue(row, ["status", "official.status", "scratchingStatus", "official.scratchingStatus"]));
  if (raw && raw !== "-") return raw;
  const scratched = firstValue(row, ["scratched", "official.scratched", "isScratched"]);
  return scratched === true || String(scratched).toUpperCase() === "TRUE" ? "Scratched" : "Active";
}

export function FieldWorkspace({ field, clean, weight, market, onOpenRunner }: FieldWorkspaceProps) {
  const rows = Array.isArray(field) ? field : [];

  return (
    <section className="eiq-workspace-panel eiq-field-workspace-v1">
      <div className="eiq-workspace-panel__title">
        <span>FIELD</span>
        <strong>Race field</strong>
        <p>Official runners with governed EDGEiQ fields where available.</p>
      </div>

      <div className="eiq-table-wrap">
        <table className="eiq-field-table-v1">
          <thead>
            <tr>
              <th>No.</th>
              <th>Silk</th>
              <th className="is-left">Runner</th>
              <th>Barrier</th>
              <th>Weight</th>
              <th className="is-left">Jockey</th>
              <th className="is-left">Trainer</th>
              <th>EPI</th>
              <th>Market</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((runner, index) => {
              const no = clean(firstValue(runner, ["official.number", "number", "runnerNumber", "saddlecloth", "no"]));
              const silk = firstValue(runner, ["official.silkUrl", "silkUrl", "silksUrl", "silk"]);
              const name = clean(firstValue(runner, ["official.runner", "runner", "runnerName", "horse", "name"]));
              const barrier = clean(firstValue(runner, ["official.barrier", "barrier", "bar", "draw"]));
              const runnerWeight = weight(firstValue(runner, ["official.weight", "weight", "wt"]));
              const jockey = clean(firstValue(runner, ["official.jockey", "jockey"]));
              const trainer = clean(firstValue(runner, ["official.trainer", "trainer"]));
              const epi = clean(firstValue(runner, ["metrics.epi", "epi", "currentEpi", "rating", "official.epi"]));
              const price = market(firstValue(runner, ["official.market", "market", "live", "price"]));
              const status = statusForRunner(runner, clean);

              return (
                <tr
                  key={`${no}-${name}-${index}`}
                  className={status.toLowerCase().includes("scratch") ? "is-scratched" : ""}
                  role="button"
                  tabIndex={0}
                  onClick={() => onOpenRunner(index)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onOpenRunner(index);
                    }
                  }}
                >
                  <td>{no}</td>
                  <td>
                    {typeof silk === "string" && silk.startsWith("http") ? (
                      <img className="eiq-field-table-v1__silk" src={silk} alt="" loading="lazy" />
                    ) : (
                      clean(silk)
                    )}
                  </td>
                  <td className="is-left"><strong>{name}</strong></td>
                  <td>{barrier}</td>
                  <td>{runnerWeight}</td>
                  <td className="is-left">{jockey}</td>
                  <td className="is-left">{trainer}</td>
                  <td>{epi}</td>
                  <td>{price}</td>
                  <td>{status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if old not in text:
        raise RuntimeError(f"Expected block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_component() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx"
    if path.exists():
      checkpoint = path.with_name(path.stem + "_CHECKPOINT_BEFORE_FIELD_WORKSPACE_FOUNDATION_V1" + path.suffix)
      checkpoint.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8")
    path.write_text(FIELD_COMPONENT, encoding="utf-8")


def patch_race_workspace() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
    replace_once(path, 'import { MapWorkspace } from "./MapWorkspace";', 'import { FieldWorkspace } from "./FieldWorkspace";\nimport { MapWorkspace } from "./MapWorkspace";')
    replace_once(
        path,
        'const tabs = ["FORM GUIDE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"] as const;',
        'const tabs = ["FIELD", "FORM GUIDE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "REVIEW"] as const;',
    )
    replace_once(
        path,
        '''      {tab === "FORM GUIDE" ? (
        <RaceFormGuideWorkspace''',
        '''      {tab === "FIELD" ? (
        <FieldWorkspace
          field={field}
          clean={clean}
          weight={market}
          market={market}
          onOpenRunner={onOpenRunner}
        />
      ) : tab === "FORM GUIDE" ? (
        <RaceFormGuideWorkspace''',
    )
    # Correct the deliberately direct replacement above so TypeScript receives the real weight formatter.
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("          weight={market}\n          market={market}", "          weight={weight}\n          market={market}", 1)
    path.write_text(text, encoding="utf-8")


def patch_race_file() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
    replace_once(path, '  field: "FORM GUIDE",', '  field: "FIELD",')


def main() -> int:
    write_component()
    patch_race_workspace()
    patch_race_file()
    print("Applied EDGEiQ Field workspace foundation v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
