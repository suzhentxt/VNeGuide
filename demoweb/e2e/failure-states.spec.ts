import { expect, test } from "@playwright/test";

import { setAndSyncField, temporaryResidenceFormPath } from "./support";

test("typed timeout hiển thị fallback và không làm mất dữ liệu form", async ({ page }) => {
  await page.goto(temporaryResidenceFormPath);
  await setAndSyncField(page, "temporary_address", "input", "Địa chỉ vẫn còn khi timeout");

  await page.route("**/api/chat/message", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "chat_api_timeout",
          message: "Trợ lý phản hồi quá thời gian.",
          retryable: true,
        },
      }),
    });
  });

  await page.getByRole("button", { name: "Mở trợ lý VNeGuide" }).click();
  const dialog = page.getByRole("dialog", { name: "Trợ lý VNeGuide" });
  const input = dialog.getByRole("textbox", { name: "Nội dung cần trợ lý hỗ trợ" });
  await expect(input).toBeEnabled();
  await input.fill("Hãy kiểm tra dữ liệu tổng hợp này");
  await dialog.getByRole("button", { name: "Gửi tin nhắn" }).click();

  await expect(dialog.getByRole("alert")).toContainText(
    "Trợ lý phản hồi quá thời gian. Biểu mẫu vẫn dùng được và dữ liệu không bị mất.",
  );
  await expect(page.locator("#temporary_address")).toHaveValue(
    "Địa chỉ vẫn còn khi timeout",
  );
  await expect(page.getByTestId("workspace-revision")).toHaveText("1");
});

test.fixme(
  "OCR unreadable hiển thị lỗi typed và giữ form",
  async ({ page }) => {
    // Contract cho OCR owner: khi upload/API/UI thật được merge, dùng một file tổng hợp không PII,
    // làm adapter trả ocr_unreadable và xác minh alert mà không ghi đè workspace.
    await page.goto(temporaryResidenceFormPath);
    await page.getByLabel("Tải tài liệu để OCR").setInputFiles({
      name: "ocr-khong-doc-duoc.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("du lieu tong hop khong doc duoc"),
    });
    await expect(page.getByRole("alert")).toContainText("Không đọc được tài liệu");
  },
);
