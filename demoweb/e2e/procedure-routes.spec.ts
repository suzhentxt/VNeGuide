import { expect, test } from "@playwright/test";

import { currentSessionId, getBackendSession, procedures } from "./support";

test.describe("phạm vi đúng ba thủ tục", () => {
  for (const procedure of procedures) {
    test(`${procedure.code} mở đúng route và chat context`, async ({ page, request }) => {
      const response = await page.goto(`/hon-nhan-va-gia-dinh/${procedure.slug}`);
      expect(response?.status()).toBe(200);
      await expect(page.getByRole("heading", { level: 1, name: procedure.title })).toBeVisible();
      await expect(page.getByText(procedure.code, { exact: true }).first()).toBeVisible();

      const createdSessionResponse = page.waitForResponse(
        (candidate) =>
          candidate.url().endsWith("/api/chat/session") &&
          candidate.request().method() === "POST",
      );
      await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
      const dialog = page.getByRole("dialog", { name: "Trợ lý VNeGuide" });
      await expect(dialog).toBeVisible();
      expect((await createdSessionResponse).status()).toBe(201);
      await expect(dialog.getByRole("textbox", { name: "Nội dung cần trợ lý hỗ trợ" })).toBeEnabled();
      await expect(dialog).not.toContainText("chưa có procedure pack");

      const session = await getBackendSession(request, await currentSessionId(page));
      expect(session.context.procedure_code).toBe(procedure.code);
      expect(session.context.procedure_title).toBe(procedure.contextTitle);
    });
  }

  test("route đăng ký kết hôn cũ không còn được hỗ trợ", async ({ page }) => {
    const response = await page.goto("/hon-nhan-va-gia-dinh/dang-ky-ket-hon");
    expect(response?.status()).toBe(404);
  });
});
