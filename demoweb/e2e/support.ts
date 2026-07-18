import { expect, type APIRequestContext, type Locator, type Page } from "@playwright/test";

export const apiBaseUrl = `http://127.0.0.1:${process.env.VNEGUIDE_E2E_API_PORT ?? "38100"}`;

export const procedures = [
  {
    code: "2.000635",
    slug: "cap-ban-sao-giay-khai-sinh",
    title: "Cấp bản sao Trích lục hộ tịch (bản sao Giấy khai sinh)",
    contextTitle: "Cấp bản sao Giấy khai sinh",
  },
  {
    code: "1.013314",
    slug: "xac-nhan-dieu-kien-nha-o",
    title: "Xác nhận điều kiện diện tích bình quân nhà ở",
    contextTitle: "Xác nhận điều kiện diện tích bình quân nhà ở",
  },
  {
    code: "1.004194",
    slug: "dang-ky-tam-tru",
    title: "Đăng ký tạm trú",
    contextTitle: "Đăng ký tạm trú",
  },
] as const;

const heroQuery = new URLSearchParams({
  service: "temporary-residence-guidance",
  receptionUnit: "Trung tâm phục vụ hành chính công, Thành phố Hà Nội",
});

export const temporaryResidenceFormPath =
  `/hon-nhan-va-gia-dinh/dang-ky-tam-tru/to-khai?${heroQuery.toString()}`;

export const heroFields = [
  { id: "registration_mode", kind: "select", value: "individual_or_household" },
  { id: "applicant_full_name", kind: "input", value: "Người Dùng E2E Tổng Hợp" },
  { id: "applicant_date_of_birth", kind: "input", value: "1990-01-01" },
  { id: "applicant_personal_id", kind: "input", value: "0".repeat(12) },
  { id: "applicant_is_minor", kind: "select", value: "false" },
  { id: "temporary_address", kind: "input", value: "Số 10 phố Kiểm Thử, Hà Nội" },
  { id: "temporary_start_date", kind: "input", value: "2026-08-01" },
  { id: "temporary_end_date", kind: "input", value: "2027-08-01" },
  { id: "dwelling_basis", kind: "select", value: "rented" },
  { id: "owner_or_householder_consent", kind: "select", value: "true" },
  { id: "legal_dwelling_data_retrievable", kind: "select", value: "true" },
  { id: "submission_channel", kind: "select", value: "online" },
  { id: "fee_exemption_claimed", kind: "select", value: "false" },
] as const;

export function fieldContainer(page: Page, fieldId: string) {
  return page.locator(`[data-field-id="${fieldId}"]`);
}
export async function setControlValue(control: Locator, kind: "input" | "select", value: string) {
  await control.focus();
  if (kind === "select") await control.selectOption(value);
  else await control.fill(value);
  await expect(control).toHaveValue(value);
}

export async function setAndSyncField(
  page: Page,
  fieldId: string,
  kind: "input" | "select",
  value: string,
) {
  const control = page.locator(`#${fieldId}`);
  await setControlValue(control, kind, value);
  const [response] = await Promise.all([
    page.waitForResponse(
      (candidate) =>
        candidate.url().endsWith("/api/chat/field") &&
        candidate.request().method() === "POST",
    ),
    control.blur(),
  ]);
  expect(response.status()).toBe(200);
  await expect(fieldContainer(page, fieldId)).toContainText("Đã đồng bộ với trợ lý");
  return response;
}

export async function fillHeroForm(page: Page, runNumber = 1) {
  for (const field of heroFields) {
    const value =
      field.id === "applicant_full_name" || field.id === "temporary_address"
        ? `${field.value} ${runNumber}`
        : field.value;
    await setAndSyncField(page, field.id, field.kind, value);
  }
}

export async function currentSessionId(page: Page) {
  const cookie = (await page.context().cookies()).find(
    (candidate) => candidate.name === "vneguide_chat_session",
  );
  expect(cookie, "BFF phải tạo cookie session HttpOnly").toBeDefined();
  return cookie!.value;
}

export async function getBackendSession(request: APIRequestContext, sessionId: string) {
  const response = await request.get(`${apiBaseUrl}/v1/chat/sessions/${sessionId}`);
  expect(response.status()).toBe(200);
  return response.json();
}
