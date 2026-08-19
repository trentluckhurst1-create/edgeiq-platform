from pathlib import Path
from datetime import datetime

app = Path("src/App.tsx")
checkpoint = Path("src/App_CHECKPOINT_BEFORE_EDGEIQ_OS_V2_MOUNT_20260707.tsx")

checkpoint.write_text(app.read_text(encoding="utf-8"), encoding="utf-8")

app.write_text(r'''
import { EdgeiqOsV2 } from "./edgeiq-os/EdgeiqOsV2";

export default function App() {
  return <EdgeiqOsV2 />;
}
''', encoding="utf-8")

print("[EDGEIQ_OS_V2_MOUNT] App.tsx now mounts EdgeiqOsV2")
print("checkpoint=", checkpoint)
