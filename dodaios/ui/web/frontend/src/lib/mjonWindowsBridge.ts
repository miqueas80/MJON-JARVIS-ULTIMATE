/**
 * Typed transport for the independently branded MJON AI OS Windows edition.
 *
 * NO visual/layout code lives here. The approved user interface will call
 * these functions from its existing controls when implemented.
 *
 * These functions only address same-origin /api/mjon/windows routes on the
 * local JARVIS server. They never silently fall back to a cloud provider,
 * install a model, change Windows policy, or initiate network calls on import.
 */
const ROOT = "/api/mjon/windows";

export type WindowsModuleState = "not_installed" | "installed_unverified" | "remote_opt_in";

export interface WindowsModule {
  id: string;
  name: string;
  domain: string;
  status: WindowsModuleState;
  offline: boolean;
  launch: "manual_only";
  workstation_only: boolean;
}

export interface WindowsDiagnostics {
  product: string;
  platform: "Windows";
  release: string;
  architecture: string;
  memory_total_bytes: number | null;
  disk_free_bytes: number | null;
  ollama: "installed_unverified" | "not_installed";
  model_tested: boolean;
  remote_provider_auto_enabled: false;
  linux_desktop_services: "not_applicable";
}

export interface WindowsOverview {
  product: string;
  platform: "Windows";
  diagnostics: WindowsDiagnostics;
  modules: WindowsModule[];
  automatic_installation: false;
  automatic_cloud_fallback: false;
}

export interface WindowsModelInventory {
  /** Explicitly false until an actual generation test has been completed. */
  ready: boolean;
  server_reachable: boolean;
  models_available: boolean;
  generation_tested: boolean;
  models: string[];
  reason: string;
}

export interface WindowsModelTestResult {
  ok: true;
  provider: "ollama_local";
  model: string;
  answer: string;
  generation_tested: true;
}

export interface WindowsStorageDecision {
  allowed: boolean;
  free_bytes: number;
  required_bytes: number;
  reserve_bytes: number;
  reason: string;
  started_download: false;
}

export type WindowsSettingsSection =
  | "wifi" | "bluetooth" | "ethernet" | "sound"
  | "display" | "power" | "storage" | "apps"
  | "privacy" | "updates";

async function read<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const failure: unknown = await response.json().catch(() => null);
    const detail = (
      failure && typeof failure === "object" && "detail" in failure
      && typeof failure.detail === "string"
    ) ? failure.detail : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

function post<T>(suffix: string, payload: object): Promise<T> {
  return read<T>(ROOT + suffix, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchWindowsOverview(): Promise<WindowsOverview> {
  return read<WindowsOverview>(ROOT + "/overview", { cache: "no-store" });
}

export function fetchWindowsModels(): Promise<WindowsModelInventory> {
  return read<WindowsModelInventory>(ROOT + "/models", { cache: "no-store" });
}

/** Only an explicit interaction tests generation with a chosen downloaded model. */
export function testWindowsModel(model: string, prompt: string): Promise<WindowsModelTestResult> {
  if (!model?.trim() || model.length > 200 || !prompt?.trim() || prompt.length > 1024) {
    return Promise.reject(new Error("Indicá un modelo y una consulta válida."));
  }
  return post<WindowsModelTestResult>("/models/test", { model, prompt });
}

export function openWindowsSettings(
  section: WindowsSettingsSection,
): Promise<{ opened: string }> {
  return post<{ opened: string }>("/settings/open", { section });
}

/** Storage numbers come from the server's actual chosen model volume. */
export function checkWindowsStorage(modelBytes: number): Promise<WindowsStorageDecision> {
  if (!Number.isSafeInteger(modelBytes) || modelBytes < 0 || modelBytes > 1_000_000_000_000) {
    return Promise.reject(new Error("El tamaño del modelo es inválido."));
  }
  return post<WindowsStorageDecision>("/storage/check", { model_bytes: modelBytes });
}
