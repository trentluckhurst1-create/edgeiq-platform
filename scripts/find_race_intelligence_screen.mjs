import fs from "fs";
import path from "path";

const root = process.cwd();

const candidates = [
  "src/RaceIntelligenceScreen.tsx",
  "src/components/RaceIntelligenceScreen.tsx",
  "src/screens/RaceIntelligenceScreen.tsx",
  "src/pages/RaceIntelligenceScreen.tsx",
];

for (const rel of candidates) {
  const p = path.join(root, rel);
  if (fs.existsSync(p)) {
    console.log(rel);
  }
}
