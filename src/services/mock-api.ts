const DEFAULT_MOCK_DELAY_MS = 350;
const LOADING_MOCK_DELAY_MS = 30_000;
const MOCK_SCENARIO_STORAGE_KEY = "sunnekatha:mock-scenario";

export type MockScenario = "loading" | "success" | "empty" | "error";

export class MockApiError extends Error {
  constructor() {
    super("Mock service request failed.");
    this.name = "MockApiError";
  }
}

function getMockScenario(): MockScenario {
  if (typeof window === "undefined") return "success";

  const queryScenario = new URLSearchParams(window.location.search).get(
    "mock",
  );
  if (isMockScenario(queryScenario)) return queryScenario;

  const storedScenario = window.localStorage.getItem(
    MOCK_SCENARIO_STORAGE_KEY,
  );
  return isMockScenario(storedScenario) ? storedScenario : "success";
}

function isMockScenario(value: string | null): value is MockScenario {
  return ["loading", "success", "empty", "error"].includes(value ?? "");
}

function emptyCollections<T>(value: T): T {
  if (Array.isArray(value)) return [] as T;
  if (!value || typeof value !== "object") return value;

  return Object.fromEntries(
    Object.entries(value).map(([key, nestedValue]) => [
      key,
      Array.isArray(nestedValue)
        ? []
        : nestedValue && typeof nestedValue === "object"
          ? emptyCollections(nestedValue)
          : nestedValue,
    ]),
  ) as T;
}

export async function mockApiResponse<T>(
  value: T,
  delayMs = DEFAULT_MOCK_DELAY_MS,
  emptyValue?: T,
): Promise<T> {
  const scenario = getMockScenario();
  const responseDelay =
    scenario === "loading" ? LOADING_MOCK_DELAY_MS : delayMs;

  await new Promise<void>((resolve) => {
    setTimeout(resolve, responseDelay);
  });

  if (scenario === "error") throw new MockApiError();

  return structuredClone(
    scenario === "empty"
      ? arguments.length >= 3
        ? (emptyValue as T)
        : emptyCollections(value)
      : value,
  );
}
