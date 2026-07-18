import { NextRequest, NextResponse } from "next/server";

import {
  MAX_PORTAL_OPTIONS,
  type PortalOption,
} from "@/data/portal-authorities";

const PORTAL_API_URL = "https://vpcp.dichvucong.gov.vn/jsp/rest.jsp";
const PORTAL_API_TIMEOUT_MS = 8_000;

const optionServices = {
  ward: "dvcqg_get_quan_huyen_by_selected_v2",
  department: "dvcqg_get_so_by_selected_v2",
} as const;

interface PortalApiRecord {
  ID?: unknown;
  NAME?: unknown;
}

function jsonResponse(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store, max-age=0",
    },
  });
}

function normalizePortalRecords(value: unknown): PortalOption[] | null {
  if (!Array.isArray(value)) {
    return null;
  }

  const options: PortalOption[] = [];
  const seenIds = new Set<string>();

  for (const valueRecord of value) {
    if (
      typeof valueRecord !== "object" ||
      valueRecord === null ||
      !("ID" in valueRecord) ||
      !("NAME" in valueRecord)
    ) {
      continue;
    }

    const record = valueRecord as PortalApiRecord;
    const id =
      typeof record.ID === "string" || typeof record.ID === "number"
        ? String(record.ID).trim()
        : "";
    const label =
      typeof record.NAME === "string"
        ? record.NAME.replace(/\s+/g, " ").trim()
        : "";

    if (
      id.length === 0 ||
      id === "-1" ||
      id.length > 64 ||
      !/^\d+$/.test(id) ||
      label.length === 0 ||
      label.length > 200 ||
      seenIds.has(id)
    ) {
      continue;
    }

    seenIds.add(id);
    options.push({ id, label });

    if (options.length === MAX_PORTAL_OPTIONS) {
      break;
    }
  }

  return options;
}

function isTimeoutError(error: unknown) {
  return (
    error instanceof DOMException &&
    (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

export async function GET(request: NextRequest) {
  const kind = request.nextUrl.searchParams.get("kind");
  const provinceId = request.nextUrl.searchParams.get("provinceId");

  if (
    (kind !== "ward" && kind !== "department") ||
    !provinceId ||
    !/^\d+$/.test(provinceId)
  ) {
    return jsonResponse(
      {
        error: "Yêu cầu danh sách cơ quan không hợp lệ.",
        retryable: false,
      },
      400,
    );
  }

  const params = JSON.stringify({
    service: optionServices[kind],
    type: "qry",
    provider: "dvcquocgiaRead",
    tinh_id: provinceId,
  });

  try {
    const portalResponse = await fetch(PORTAL_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      },
      body: new URLSearchParams({ params }),
      cache: "no-store",
      signal: AbortSignal.timeout(PORTAL_API_TIMEOUT_MS),
    });

    if (!portalResponse.ok) {
      return jsonResponse(
        {
          error: "Cổng dữ liệu cơ quan tạm thời không phản hồi.",
          retryable: true,
        },
        502,
      );
    }

    const records: unknown = await portalResponse.json();
    const options = normalizePortalRecords(records);
    if (options === null) {
      return jsonResponse(
        {
          error: "Cổng dữ liệu cơ quan trả về dữ liệu không hợp lệ.",
          retryable: true,
        },
        502,
      );
    }

    return jsonResponse({ options });
  } catch (error) {
    return jsonResponse(
      {
        error: isTimeoutError(error)
          ? "Cổng dữ liệu cơ quan phản hồi quá thời gian chờ."
          : "Không thể tải danh sách cơ quan lúc này.",
        retryable: true,
      },
      isTimeoutError(error) ? 504 : 502,
    );
  }
}
