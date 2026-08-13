/** Download a file from the API with session cookie. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(path, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** POST JSON and download the response as a file (PDF, XLSX, etc.). */
export async function downloadBlobPost(
  path: string,
  body: unknown,
  filename: string,
): Promise<void> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** POST JSON and download PDF response. */
export async function downloadPdfPost(
  path: string,
  body: unknown,
  filename: string,
): Promise<void> {
  await downloadBlobPost(path, body, filename);
}

/** Sanitize a billing reference for use in download filenames. */
export function safeDownloadStem(value: string, fallback = "batch"): string {
  const cleaned = (value || "").trim().replace(/[^\w.\-]+/g, "_").replace(/^[._]+|[._]+$/g, "");
  return cleaned || fallback;
}

/** Trigger a browser download from in-memory text (e.g. CSV). */
export function downloadTextFile(
  content: string,
  filename: string,
  mimeType = "text/csv;charset=utf-8",
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
