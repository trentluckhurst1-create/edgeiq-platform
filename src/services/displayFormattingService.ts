import type { CSSProperties } from "react";
import type { CsvRow } from "../utils/edgeiqCsv";
import { firstText } from "../utils/raceRowHelpers";
import { edgePct, fairPrice, livePrice } from "./marketPricingService";

type Row = CsvRow;

export function cellTone(label: string): string {
 const value = label.toUpperCase();
 if (value === "BET") return "#3ee68f";
 if (value === "VERY HIGH" || value === "HIGH") return "#3ee68f";
 if (value === "WATCH" || value === "LEN" || value === "MEDIUM") return "#ffffff";
 if (value === "MODEL" || value === "MODEL EDGE") return "#ffffff";
 if (value === "LOW DT") return "#94a3b8";
 if (value === "SCRATCHED") return "#9ca3af";
 if (value === "WIT") return "#94a3b8";
 if (value === "PSS" || value === "MRKET COMPRESSION" || value === "LOW" || value === "VERY LOW") return "#f87171";
 return "#eaf2ff";
}

export function connectionTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("ELITE") || value.includes("STRONG") || value.includes("POSITIVE") || value.includes("OUTPERFORMS")) return "#34d399";
 if (value.includes("NEUTRAL")) return "#ffffff";
 if (value.includes("NEGATIVE") || value.includes("POOR") || value.includes("UNDERPERFORMS")) return "#f87171";
 if (value.includes("INSUFFICIENT")) return "#94a3b8";
 return "#ffffff";
}

export function campaignEvidenceTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("STRONG") || value === "LOW") return "#34d399";
 if (value.includes("DEVELOPING")) return "#ffffff";
 if (value.includes("LIMITED") || value === "MODERATE") return "#ffffff";
 if (value === "HIGH") return "#f87171";
 if (value.includes("NO HISTORY") || value.includes("UNPROVEN") || value.includes("-") || value.includes("UNRTED")) return "#94a3b8";
 return "#eaf2ff";
}

export function hiddenGemTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("STRONG CSE")) return "#ffffff";
 if (value.includes("IMPROVING")) return "#34d399";
 if (value.includes("BELOW EXPECTTIONS")) return "#f87171";
 if (value.includes("NEUTRAL") || value.includes("NO SIGNAL") || value.includes("NONE")) return "#94a3b8";
 return "#cbd5e1";
}

export function performanceIntelligenceLabel(label: string, actionable = false, historical = false): string {
 const value = label.toUpperCase();
 if (value.includes("STRONG CSE") || value.includes("EDGE DETECTED")) return "STRONG CSE";
 if (value.includes("IMPROVING") || value.includes("PROFILE EVIDENCE") || value.includes("HISTORICAL")) return "IMPROVING";
 if (value.includes("BELOW") || value.includes("NEGATIVE")) return "BELOW EXPECTTIONS";
 if (value.includes("NEUTRAL")) return "NEUTRAL";
 if (actionable && (value.includes("HIGH") || value.includes("STRONG"))) return "STRONG CSE";
 if (actionable) return "STRONG CSE";
 if (historical || value.includes("HISTORICAL")) return "IMPROVING";
 return "NEUTRAL";
}

export function customerPerformanceNarrative(value: string): string {
 return value
 .replace(/hidden-gem/gi, "performance intelligence")
 .replace(/hidden gem/gi, "performance intelligence")
 .replace(/edge detected/gi, "strong case")
 .replace(/profile evidence/gi, "improving")
 .replace(/no evidence/gi, "neutral");
}

export function formatCampaignStage(stage: number | null, label: string): string {
 const normalized = label.replace(/_/g, " ").trim().toUpperCase();
 if (normalized && normalized !== "-" && normalized !== "-") {
 return stage !== null ? `${normalized} (${Math.round(stage)})` : normalized;
 }
 return stage !== null ? `STGE ${Math.round(stage)}` : "-";
}

export function formatCampaignWindow(start: number | null, end: number | null): string {
 if (start === null || end === null) return "-";
 if (start === end) return `STGE ${Math.round(start)}`;
 return `STGES ${Math.round(start)}-${Math.round(end)}`;
}

export function coverageStatus(count: number, total: number): string {
 if (total <= 0 || count <= 0) return "NOT LOADED";
 if (count / total >= 0.8) return "LODED";
 return "PARTIAL";
}

export function coverageStatusTone(status: string): string {
 const normalized = status.toUpperCase();
 if (normalized === "LODED") return "#34d399";
 if (normalized === "PARTIAL") return "#ffffff";
 return "#94a3b8";
}

export function trajectoryTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("STRONG UP") || value === "UP" || value === "SCENDING" || value === "PEK") return "#34d399";
 if (value === "EMERGING") return "#ffffff";
 if (value === "STBLE" || value === "PLTEU") return "#ffffff";
 if (value.includes("DOWN") || value === "DECLINING") return "#f87171";
 return "#eaf2ff";
}

export function runnerTrendSummary(direction: string, delta: number | null, historyCount = 0): string {
 const value = direction.toUpperCase();
 if (value.includes("STRONG UP") || value === "UP" || value === "SCENDING" || value === "EMERGING") return "IMPROVING";
 if (value.includes("DOWN") || value === "DECLINING") return "REGRESSING";
 if (value === "STBLE" || value === "PLTEU" || value === "PEK") return "STBLE";
 if (delta !== null) {
 if (delta >= 1.5) return "IMPROVING";
 if (delta <= -1.5) return "REGRESSING";
 return "STBLE";
 }
 return historyCount >= 2 ? "STBLE" : "LIMITED";
}

export function runnerTrendTone(label: string): string {
 const value = label.toUpperCase();
 if (value === "IMPROVING") return "#34d399";
 if (value === "STBLE") return "#ffffff";
 if (value === "REGRESSING") return "#f87171";
 return "#94a3b8";
}

export function historyReadLabel(count: number): string {
 if (count >= 5) return "HISTORY STRONG";
 if (count >= 3) return "HISTORY BUILDING";
 if (count >= 1) return "HISTORY LIMITED";
 return "NO HISTORY";
}

export function fitReadLabel(label: string, fallback = "Neutral"): string {
 const value = label.toUpperCase();
 if (!value || value === "-") return fallback;
 if (value.includes("POSITIVE") || value.includes("STRONG") || value.includes("ELITE")) return "Positive";
 if (value.includes("NEGATIVE") || value.includes("POOR")) return "Negative";
 if (value.includes("NEUTRAL")) return "Neutral";
 return value.replace(/_/g, " ");
}

export function evidenceQualityTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("LODED")) return "#34d399";
 if (value.includes("LIMITED") || value.includes("PARTIAL")) return "#ffffff";
 if (value.includes("NOT")) return "#94a3b8";
 return "#ffffff";
}

export function opportunityTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("VERY HIGH") || value === "HIGH") return "#34d399";
 if (value === "MEDIUM") return "#ffffff";
 if (value === "LOW") return "#94a3b8";
 return "#eaf2ff";
}

export function riskTone(label: string): string {
 const value = label.toUpperCase();
 if (value.includes("VERY HIGH") || value === "HIGH") return "#f87171";
 if (value === "MEDIUM") return "#ffffff";
 if (value === "LOW") return "#34d399";
 return "#eaf2ff";
}

export function valueccent(label: string): CSSProperties {
 return { color: cellTone(label), fontWeight: 900 };
}

export function sourceLabel(row: Row, bet?: Row): string {
 const display = firstText(row, ["display_source"], "");
 if (display && display !== "-") {
 return display
 .replace("LIMITED_DT_MRKET_DJUSTED_V1", "MRKET DJ")
 .replace(/^MODEL$/i, "EDGEIQ")
 .toUpperCase();
 }

 const live = livePrice(row, bet);
 const explicit = firstText(row, ["live_price_source", "tab_live_price_source", "edgeiq_price_source_v1", "bookmaker"], "");
 if (explicit && explicit !== "-") {
 return explicit
 .replace("LIMITED_DT_MRKET_DJUSTED_V1", "MRKET DJ")
 .replace(/^MODEL$/i, "EDGEIQ")
 .toUpperCase();
 }

 return live && live > 0 ? "TB" : "EDGEIQ";
}

export function decision(row: Row, bet?: Row): string {
 const display = firstText(row, ["display_decision"], "");
 if (display && display !== "-") return display.toUpperCase();

 const explicit = firstText(row, ["execution_action", "decision"], "");
 if (explicit && explicit !== "-" && !["WITING FEED", "NO_MRKET"].includes(explicit.toUpperCase())) {
 return explicit.toUpperCase();
 }

 const live = livePrice(row, bet);
 const fair = fairPrice(row, bet);
 const edge = edgePct(row, bet);

 if (!live || live <= 0) return "MRKET SOURCE UNVILBLE";
 if (!fair || fair <= 0) return "PSS";
 if (edge !== null && edge >= 18) return "WATCH";
 if (edge !== null && edge >= 10) return "LEN";
 if (edge !== null && edge > 0) return "PSS";
 if (edge !== null) return "MRKET COMPRESSION";
 return "PSS";
}


export function ordinal(value: number | null): string {
 if (value === null || !Number.isFinite(value)) return "N/";
 const rounded = Math.trunc(value);
 const mod100 = rounded % 100;
 if (mod100 >= 11 && mod100 <= 13) return `${rounded}th`;
 const mod10 = rounded % 10;
 if (mod10 === 1) return `${rounded}st`;
 if (mod10 === 2) return `${rounded}nd`;
 if (mod10 === 3) return `${rounded}rd`;
 return `${rounded}th`;
}

export function drawerValue(value: string): string {
 return value && value !== "-" ? value : "N/";
}
