
import type { IntelligenceModule, IntelligenceModuleOutput } from "./IntelligenceRegistryTypes";

const modules: IntelligenceModule[] = [];

export function registerIntelligenceModule(module: IntelligenceModule): void {
  const exists = modules.some((item) => item.key === module.key);
  if (!exists) modules.push(module);
}

export function getRegisteredIntelligenceModules(): IntelligenceModule[] {
  return [...modules];
}

export function buildRegisteredIntelligence(): IntelligenceModuleOutput[] {
  return modules.map((module) => module.build());
}

export function clearIntelligenceRegistry(): void {
  modules.splice(0, modules.length);
}
