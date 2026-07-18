import { expect, test } from "@playwright/test";

import { currentSessionId, getBackendSession } from "./support";

test("quick choice keeps the same conversation when opening the confirmed service", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
  const dialog = page.getByRole("dialog", { name: "Trợ lý VNeGuide" });
  const input = dialog.getByRole("textbox", { name: "Nội dung cần trợ lý hỗ trợ" });

  await input.fill("tui ưng mần giấy khai sinh");
  await dialog.getByRole("button", { name: "Gửi tin nhắn" }).click();
  await expect(
    dialog.getByRole("button", { name: "Tôi muốn xin bản sao Giấy khai sinh" }),
  ).toBeVisible();

  const sessionId = await currentSessionId(page);
  await dialog.getByRole("button", { name: "Tôi muốn xin bản sao Giấy khai sinh" }).click();
  await expect(dialog.getByText("Cần xác nhận trước khi chọn nơi nộp")).toBeVisible();

  await dialog.getByRole("button", { name: "Đúng, chọn nơi nộp hồ sơ" }).click();
  await expect(page).toHaveURL(
    /\/hon-nhan-va-gia-dinh\/cap-ban-sao-giay-khai-sinh\?confirmed=1$/,
  );
  expect(await currentSessionId(page)).toBe(sessionId);

  await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
  await expect(dialog).toContainText("tui ưng mần giấy khai sinh");
  await expect(dialog).toContainText("Tôi muốn xin bản sao Giấy khai sinh");

  const backendSession = await getBackendSession(request, sessionId);
  expect(backendSession.turn.messages).toHaveLength(4);
  expect(backendSession.turn.procedure.code).toBe("2.000635");
});

test("a natural change of mind replaces the service without losing the conversation", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
  const dialog = page.getByRole("dialog", { name: "Trợ lý VNeGuide" });
  const input = dialog.getByRole("textbox", { name: "Nội dung cần trợ lý hỗ trợ" });

  await input.fill("tôi muốn xin bản sao giấy khai sinh cho tôi");
  await dialog.getByRole("button", { name: "Gửi tin nhắn" }).click();
  await expect(dialog.getByText("Cấp bản sao Giấy khai sinh", { exact: true })).toBeVisible();
  const sessionId = await currentSessionId(page);

  await input.fill("à thôi tôi muốn đăng ký tạm trú");
  await dialog.getByRole("button", { name: "Gửi tin nhắn" }).click();
  await expect(dialog.getByRole("heading", { name: "Đăng ký tạm trú" })).toBeVisible();
  await dialog.getByRole("button", { name: "Đúng, chọn nơi nộp hồ sơ" }).click();

  await expect(page).toHaveURL(/\/hon-nhan-va-gia-dinh\/dang-ky-tam-tru\?confirmed=1$/);
  expect(await currentSessionId(page)).toBe(sessionId);
  const backendSession = await getBackendSession(request, sessionId);
  expect(backendSession.turn.procedure.code).toBe("1.004194");
  expect(backendSession.turn.messages).toHaveLength(4);
  expect(backendSession.turn.suggestions).toEqual([]);
});
