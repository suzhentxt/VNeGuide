import { expect, test } from "@playwright/test";

import {
  apiBaseUrl,
  currentSessionId,
  fieldContainer,
  getBackendSession,
  setAndSyncField,
  setControlValue,
  temporaryResidenceFormPath,
} from "./support";

test("manual edit round-trip giữ giá trị cuối trong backend draft", async ({ page, request }) => {
  await page.goto(temporaryResidenceFormPath);
  await setAndSyncField(page, "temporary_address", "input", "Địa chỉ tổng hợp lần một");
  await setAndSyncField(page, "temporary_address", "input", "Địa chỉ tổng hợp đã sửa");

  await expect(page.getByTestId("workspace-revision")).toHaveText("2");
  const session = await getBackendSession(request, await currentSessionId(page));
  expect(session.draft.values.temporary_address).toBe("Địa chỉ tổng hợp đã sửa");
  expect(session.draft.revision).toBe(2);
});
test("stale revision giữ local edit, rebase và cho phép retry", async ({ page, request }) => {
  await page.goto(temporaryResidenceFormPath);
  await setAndSyncField(page, "temporary_address", "input", "Địa chỉ server ban đầu");
  const sessionId = await currentSessionId(page);

  const externalUpdate = await request.patch(
    `${apiBaseUrl}/v1/chat/sessions/${sessionId}/draft/fields/submission_channel`,
    { data: { value: "online", expected_revision: 1 } },
  );
  expect(externalUpdate.status()).toBe(200);
  expect((await externalUpdate.json()).draft.revision).toBe(2);

  const address = page.locator("#temporary_address");
  await setControlValue(address, "input", "Địa chỉ local cần retry");
  const staleResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/chat/field"),
  );
  await address.blur();
  expect((await staleResponsePromise).status()).toBe(409);

  await expect(page.getByTestId("workspace-revision")).toHaveText("2");
  await expect(address).toHaveValue("Địa chỉ local cần retry");
  await expect(fieldContainer(page, "temporary_address")).toContainText(
    "Đã lưu trên form; chờ đồng bộ",
  );
  await expect(page.getByRole("status")).toContainText(/Giá trị bạn vừa sửa vẫn được giữ/);

  const retryResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/chat/field"),
  );
  await address.focus();
  await address.blur();
  expect((await retryResponsePromise).status()).toBe(200);
  await expect(page.getByTestId("workspace-revision")).toHaveText("3");
  await expect(fieldContainer(page, "temporary_address")).toContainText(
    "Đã đồng bộ với trợ lý",
  );

  const recovered = await getBackendSession(request, sessionId);
  expect(recovered.draft.values.temporary_address).toBe("Địa chỉ local cần retry");
  expect(recovered.draft.values.submission_channel).toBe("online");
});

test("reset tạo session mới và xóa workspace cũ", async ({ page }) => {
  await page.goto(temporaryResidenceFormPath);
  await setAndSyncField(page, "applicant_full_name", "input", "Người Dùng Reset Tổng Hợp");
  const previousSessionId = await currentSessionId(page);

  await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
  const dialog = page.getByRole("dialog", { name: "Trợ lý VNeGuide" });
  await expect(dialog.getByRole("textbox", { name: "Nội dung cần trợ lý hỗ trợ" })).toBeEnabled();
  const recreatedSessionResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/chat/session") &&
      response.request().method() === "POST",
  );
  await dialog.getByRole("button", { name: "Bắt đầu lại phiên trò chuyện" }).click();
  expect((await recreatedSessionResponse).status()).toBe(201);

  await expect(dialog.getByRole("textbox", { name: "Nội dung cần trợ lý hỗ trợ" })).toBeEnabled();
  await expect(page.locator("#applicant_full_name")).toHaveValue("");
  await expect(page.getByTestId("workspace-revision")).toHaveText("0");
  await expect.poll(async () => currentSessionId(page)).not.toBe(previousSessionId);
  const deletedSession = await page.request.get(
    `${apiBaseUrl}/v1/chat/sessions/${previousSessionId}`,
  );
  expect(deletedSession.status()).toBe(404);
});

test("session backend bị xóa được tạo lại mà không mất local edit", async ({ page, request }) => {
  await page.goto(temporaryResidenceFormPath);
  await setAndSyncField(page, "temporary_address", "input", "Địa chỉ cần giữ khi tạo lại phiên");
  const expiredSessionId = await currentSessionId(page);

  const expired = await request.delete(
    `${apiBaseUrl}/v1/chat/sessions/${expiredSessionId}`,
  );
  expect(expired.status()).toBe(204);

  const recreated = await setAndSyncField(
    page,
    "applicant_full_name",
    "input",
    "Người Dùng Sau Khi Tạo Lại",
  );
  expect(recreated.headers()["x-vneguide-session-recreated"]).toBe("1");

  const recreatedSessionId = await currentSessionId(page);
  expect(recreatedSessionId).not.toBe(expiredSessionId);
  await expect(page.getByTestId("workspace-revision")).toHaveText("1");
  await expect(page.locator("#temporary_address")).toHaveValue(
    "Địa chỉ cần giữ khi tạo lại phiên",
  );
  await expect(fieldContainer(page, "temporary_address")).toContainText(
    "Đã lưu trên form; chờ đồng bộ",
  );

  await setAndSyncField(
    page,
    "temporary_address",
    "input",
    "Địa chỉ cần giữ khi tạo lại phiên",
  );
  const session = await getBackendSession(request, recreatedSessionId);
  expect(session.draft.revision).toBe(2);
  expect(session.draft.values).toMatchObject({
    applicant_full_name: "Người Dùng Sau Khi Tạo Lại",
    temporary_address: "Địa chỉ cần giữ khi tạo lại phiên",
  });
});

test("field update đổi session khi chuyển sang thủ tục khác", async ({ page, request }) => {
  await page.goto("/hon-nhan-va-gia-dinh/cap-ban-sao-giay-khai-sinh");
  const birthSessionResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/chat/session") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
  expect((await birthSessionResponse).status()).toBe(201);
  const birthSessionId = await currentSessionId(page);

  await page.goto(temporaryResidenceFormPath);
  const switched = await setAndSyncField(
    page,
    "temporary_address",
    "input",
    "Địa chỉ sau khi chuyển thủ tục",
  );
  expect(switched.headers()["x-vneguide-session-recreated"]).toBe("1");

  const temporaryResidenceSessionId = await currentSessionId(page);
  expect(temporaryResidenceSessionId).not.toBe(birthSessionId);
  const session = await getBackendSession(request, temporaryResidenceSessionId);
  expect(session.context.procedure_code).toBe("1.004194");
  expect(session.draft.values.temporary_address).toBe("Địa chỉ sau khi chuyển thủ tục");
});
