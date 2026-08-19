from pathlib import Path
root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

def read(rel):
    return (root / rel).read_text(encoding="utf-8")

def write(rel, text):
    (root / rel).write_text(text, encoding="utf-8", newline="\n")

rel = "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
text = read(rel)
text = text.replace("  profileSummary,\n", "")
marker = "function KeyInsights({ runner }: { runner: FormGuideRunnerDisplay }) {"
helpers = r'''
function humanProfileLabel(value: string): string {
  const text = String(value || "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
  if (!text) return "Profile";
  return text.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function readableStarts(value: string): string {
  const text = String(value || "").trim();
  if (!text) return "";
  const parsed = Number(text.replace(/[^\d.-]/g, ""));
  if (Number.isFinite(parsed)) return `${parsed} ${parsed === 1 ? "start" : "starts"}`;
  return text;
}

function profileRows(profile: string): Array<{ label: string; value: string }> {
  const text = String(profile || "").trim();
  if (!text) return [];
  return text
    .split(/[;|]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const parts = item.split(":");
      if (parts.length >= 2) {
        return { label: humanProfileLabel(parts.slice(0, -1).join(":")), value: readableStarts(parts[parts.length - 1]) };
      }
      return { label: humanProfileLabel(item), value: "Available" };
    })
    .filter((row) => row.label || row.value);
}

function ProfileRows({ profile }: { profile: string }) {
  const rows = profileRows(profile).slice(0, 5);
  if (!rows.length) return <span>{displayOrDash("")}</span>;
  return (
    <ul className="eiq-performance-profile-list">
      {rows.map((row) => (
        <li key={`${row.label}-${row.value}`}>
          <span>{row.label}</span>
          <b>{row.value}</b>
        </li>
      ))}
    </ul>
  );
}

function friendlyState(value: string): string {
  const text = String(value || "").replace(/_/g, " ").trim().toLowerCase();
  if (!text) return "Unavailable";
  return text.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

'''
if "function humanProfileLabel" not in text:
    text = text.replace(marker, helpers + marker)
text = text.replace("function CertifiedPerformanceIntelligence", "function PerformanceHistory")
text = text.replace("<h3>Certified Performance Intelligence</h3>", "<h3>Performance History</h3>")
text = text.replace("<tr><th>Profile</th><td>{displayOrDash(horseProfile.profile_quality_state)}</td></tr>", "<tr><th>Profile</th><td>{friendlyState(horseProfile.profile_quality_state)}</td></tr>")
text = text.replace("<h3>Observed Profile</h3>", "<h3>Current Profile</h3>")
text = text.replace('''<tr><th>Track</th><td>{displayOrDash(profileSummary(horseProfile.track_profile))}</td></tr>
                <tr><th>Distance</th><td>{displayOrDash(profileSummary(horseProfile.distance_profile))}</td></tr>
                <tr><th>Going</th><td>{displayOrDash(profileSummary(horseProfile.going_profile))}</td></tr>
                <tr><th>Class</th><td>{displayOrDash(profileSummary(horseProfile.class_profile))}</td></tr>''', '''<tr><th>Track</th><td><ProfileRows profile={horseProfile.track_profile} /></td></tr>
                <tr><th>Distance</th><td><ProfileRows profile={horseProfile.distance_profile} /></td></tr>
                <tr><th>Going</th><td><ProfileRows profile={horseProfile.going_profile} /></td></tr>
                <tr><th>Class</th><td><ProfileRows profile={horseProfile.class_profile} /></td></tr>''')
text = text.replace("<h3>Recent Benchmark Context</h3>", "<h3>Recent Race Context</h3>")
text = text.replace("<th>Benchmark</th>\n                  <th>Confidence</th>", "<th>Distance</th>\n                  <th>Class</th>\n                  <th>Benchmark</th>\n                  <th>Confidence</th>")
text = text.replace("<td>{formatBenchmarkLevel(row.benchmark_level)}</td>\n                    <td>{formatBenchmarkConfidence(row.benchmark_confidence)}</td>", "<td>{displayOrDash(row.distance_metres ? `${row.distance_metres}m` : '')}</td>\n                    <td>{displayOrDash(row.race_class)}</td>\n                    <td>{formatBenchmarkLevel(row.benchmark_level)}</td>\n                    <td>{formatBenchmarkConfidence(row.benchmark_confidence)}</td>")
text = text.replace("Certified horse profile is not available for this runner.", "Performance history is not available for this runner.")
text = text.replace("Observed profile counts are not available.", "Current profile counts are not available.")
text = text.replace("Recent certified benchmark context is not available.", "Recent race context is not available.")
text = text.replace("<CertifiedPerformanceIntelligence horseProfile={horseProfile} historicalRows={historicalRows} />", "<PerformanceHistory horseProfile={horseProfile} historicalRows={historicalRows} />")
write(rel, text)
print("patched RaceFormGuideWorkspace")
