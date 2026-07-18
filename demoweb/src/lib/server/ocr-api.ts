import "server-only";

const OCR_TIMEOUT_MS = 65_000;

function configuration() {
  const baseUrl = process.env.VNEGUIDE_OCR_BASE_URL?.trim() || "http://127.0.0.1:8010";
  const token = process.env.VNEGUIDE_OCR_WORKER_TOKEN?.trim();
  const url = new URL(baseUrl);
  if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) {
    throw new Error("VNEGUIDE_OCR_BASE_URL must be an HTTP(S) URL without credentials");
  }
  if (!token) throw new Error("VNEGUIDE_OCR_WORKER_TOKEN is not configured");
  return { url, token };
}

export async function callOcrWorker(path: string, init: RequestInit = {}) {
  const { url, token } = configuration();
  return fetch(new URL(path, url), {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
    signal: AbortSignal.timeout(OCR_TIMEOUT_MS),
  });
}

export async function safeOcrBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return {
      error: {
        code: "invalid_ocr_response",
        message: "Dịch vụ kiểm tra tài liệu trả dữ liệu không hợp lệ.",
        retryable: true,
      },
    };
  }
}

export function ocrUnavailable(error: unknown) {
  const timeout = error instanceof DOMException && error.name === "TimeoutError";
  return Response.json(
    {
      error: {
        code: timeout ? "ocr_timeout" : "ocr_unavailable",
        message: timeout
          ? "Kiểm tra tài liệu quá thời gian; hồ sơ có thể chuyển sang kiểm tra chính thức."
          : "Chưa thể kết nối dịch vụ kiểm tra tài liệu.",
        retryable: true,
      },
    },
    { status: 503 },
  );
}
