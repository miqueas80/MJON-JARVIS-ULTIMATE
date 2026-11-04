import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  checkWindowsStorage,
  fetchWindowsModels,
  fetchWindowsOverview,
  openWindowsSettings,
  testWindowsModel,
} from "./mjonWindowsBridge";

function reply(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response;
}

describe("MJON Windows backend bridge", () => {
  const fetcher = vi.fn();

  beforeEach(() => {
    fetcher.mockReset();
    vi.stubGlobal("fetch", fetcher);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("queries the actual MJON Windows status without changing visual settings", async () => {
    const source = {
      product: "MJON AI OS",
      diagnostics: { platform: "Windows", model_tested: false },
      modules: [{ id: "ollama", status: "installed_unverified" }],
      automatic_installation: false,
      automatic_cloud_fallback: false,
    };
    fetcher.mockResolvedValue(reply(source));
    expect(await fetchWindowsOverview()).toEqual(source);
    expect(fetcher).toHaveBeenCalledWith("/api/mjon/windows/overview", {
      cache: "no-store",
    });
  });

  it("does not claim a downloaded model is ready before real generation", async () => {
    fetcher.mockResolvedValue(reply({
      server_reachable: true,
      models_available: true,
      ready: false,
      generation_tested: false,
      models: ["tiny:latest"],
      reason: "Aún no probado",
    }));
    const result = await fetchWindowsModels();
    expect(result.ready).toBe(false);
    expect(result.generation_tested).toBe(false);
    expect(result.models).toEqual(["tiny:latest"]);
  });

  it("tests only a named Ollama model through an explicit POST", async () => {
    fetcher.mockResolvedValue(reply({
      ok: true, provider: "ollama_local", model: "tiny:latest",
      answer: "Hola", generation_tested: true,
    }));
    const result = await testWindowsModel("tiny:latest", "Hola");
    expect(result.generation_tested).toBe(true);
    expect(fetcher).toHaveBeenCalledWith("/api/mjon/windows/models/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: "tiny:latest", prompt: "Hola" }),
    });
  });

  it("refuses a blank model locally instead of invoking any provider", async () => {
    await expect(testWindowsModel("", "Hola")).rejects.toThrow();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("opens the native Windows Settings section only from a deliberate call", async () => {
    fetcher.mockResolvedValue(reply({ opened: "ms-settings:network-wifi" }));
    await openWindowsSettings("wifi");
    expect(fetcher).toHaveBeenCalledWith("/api/mjon/windows/settings/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ section: "wifi" }),
    });
  });

  it("checks the server-side volume without trusting fake browser free space", async () => {
    fetcher.mockResolvedValue(reply({
      allowed: false, free_bytes: 1024, required_bytes: 4096,
      reserve_bytes: 2048, reason: "Espacio insuficiente",
      started_download: false,
    }));
    const result = await checkWindowsStorage(512);
    expect(result.allowed).toBe(false);
    expect(fetcher).toHaveBeenCalledWith("/api/mjon/windows/storage/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_bytes: 512 }),
    });
  });

  it("exposes local errors and never retries a provider in the cloud", async () => {
    fetcher.mockResolvedValue(reply({ detail: "Sin modelo local" }, 503));
    await expect(testWindowsModel("tiny:latest", "Hola")).rejects.toThrow("Sin modelo local");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
