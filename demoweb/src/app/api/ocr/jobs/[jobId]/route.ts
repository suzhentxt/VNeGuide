import { NextRequest, NextResponse } from "next/server";

import { callOcrWorker, ocrUnavailable, safeOcrBody } from "@/lib/server/ocr-api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  if (!/^[A-Za-z0-9_-]{16,100}$/.test(jobId)) {
    return NextResponse.json(
      { error: { code: "invalid_ocr_job", message: "Mã kiểm tra tài liệu không hợp lệ.", retryable: false } },
      { status: 400 },
    );
  }
  try {
    const worker = await callOcrWorker(`/v1/ocr/jobs/${encodeURIComponent(jobId)}`);
    return NextResponse.json(await safeOcrBody(worker), { status: worker.status });
  } catch (error) {
    return ocrUnavailable(error);
  }
}
