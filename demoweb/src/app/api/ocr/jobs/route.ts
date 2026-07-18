import { NextRequest, NextResponse } from "next/server";

import { callOcrWorker, ocrUnavailable, safeOcrBody } from "@/lib/server/ocr-api";

const MAX_FILE_BYTES = 8 * 1024 * 1024;
const DOCUMENT_KINDS = new Set(["legal_dwelling", "minor_consent"]);
const MIME_TYPES = new Set(["image/jpeg", "image/png", "application/pdf"]);

export async function POST(request: NextRequest) {
  const documentKind = request.headers.get("x-document-kind") ?? "";
  const contentType = (request.headers.get("content-type") ?? "").split(";", 1)[0].trim();
  if (!DOCUMENT_KINDS.has(documentKind) || !MIME_TYPES.has(contentType)) {
    return NextResponse.json(
      { error: { code: "invalid_ocr_upload", message: "Loại tài liệu hoặc định dạng tệp không được hỗ trợ.", retryable: false } },
      { status: 422 },
    );
  }
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (declaredLength > MAX_FILE_BYTES) {
    return NextResponse.json(
      { error: { code: "file_too_large", message: "Tệp vượt quá giới hạn 8 MiB.", retryable: false } },
      { status: 413 },
    );
  }
  try {
    const content = await request.arrayBuffer();
    if (!content.byteLength || content.byteLength > MAX_FILE_BYTES) {
      return NextResponse.json(
        { error: { code: "invalid_ocr_upload", message: "Tệp rỗng hoặc vượt quá giới hạn 8 MiB.", retryable: false } },
        { status: content.byteLength > MAX_FILE_BYTES ? 413 : 422 },
      );
    }
    const worker = await callOcrWorker("/v1/ocr/jobs", {
      method: "POST",
      body: content,
      headers: {
        "Content-Type": contentType,
        "X-Procedure-Code": "1.004194",
        "X-Document-Kind": documentKind,
      },
    });
    return NextResponse.json(await safeOcrBody(worker), { status: worker.status });
  } catch (error) {
    return ocrUnavailable(error);
  }
}
