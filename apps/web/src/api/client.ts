const API = "/api/v1";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function login(username: string, password: string) {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  return json<{ status: string; user?: string }>(res);
}

export async function logout() {
  const res = await fetch(`${API}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  return json<{ status: string }>(res);
}

export async function createPackage() {
  const res = await fetch(`${API}/packages`, {
    method: "POST",
    credentials: "include",
  });
  return json<{ packageId: string; state: string }>(res);
}

export async function uploadPackage(
  packageId: string,
  formData: FormData
) {
  const res = await fetch(`${API}/packages/${packageId}/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  return json<{ packageId: string; state: string }>(res);
}

export async function startExtract(
  packageId: string,
  /** Снимок первичных данных (FullSpecification §3.1); при отказе бэкенда тело повторяется без JSON */
  primarySnapshot?: Record<string, unknown>
) {
  const post = async (withJson: boolean) => {
    const init: RequestInit = {
      method: "POST",
      credentials: "include",
    };
    if (withJson && primarySnapshot !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(primarySnapshot);
    }
    return fetch(`${API}/packages/${packageId}/extract`, init);
  };

  let res = await post(primarySnapshot !== undefined);
  if (
    !res.ok &&
    primarySnapshot !== undefined &&
    (res.status === 415 || res.status === 422)
  ) {
    res = await post(false);
  }
  return json<{ packageId?: string; state: string }>(res);
}

export async function getExtraction(packageId: string) {
  const res = await fetch(`${API}/packages/${packageId}/extraction`, {
    credentials: "include",
  });
  return json<{
    packageId: string;
    state: string;
    progress?: Record<string, unknown>;
    error?: string | null;
  }>(res);
}

export async function getForm(packageId: string) {
  const res = await fetch(`${API}/packages/${packageId}/form`, {
    credentials: "include",
  });
  return json<{
    packageId: string;
    form: Record<string, unknown>;
    parseResult: Record<string, unknown>;
    calculation: unknown;
  }>(res);
}

export async function putForm(packageId: string, form: Record<string, unknown>) {
  const res = await fetch(`${API}/packages/${packageId}/form`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ form }),
  });
  return json<{ form: Record<string, unknown> }>(res);
}

export async function calculate(packageId: string) {
  const res = await fetch(`${API}/packages/${packageId}/calculate`, {
    method: "POST",
    credentials: "include",
  });
  return json<Record<string, unknown>>(res);
}

export async function generateDocs(packageId: string) {
  const res = await fetch(`${API}/packages/${packageId}/documents/generate`, {
    method: "POST",
    credentials: "include",
  });
  return json<{ isk: string; calculation: string; state?: string }>(res);
}

export function downloadUrl(packageId: string, kind: "isk" | "calculation") {
  return `${API}/packages/${packageId}/documents/${kind}`;
}

export async function downloadDocumentBlob(
  packageId: string,
  kind: "isk" | "calculation"
): Promise<Blob> {
  const res = await fetch(downloadUrl(packageId, kind), { credentials: "include" });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.blob();
}
