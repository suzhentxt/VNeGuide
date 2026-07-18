import { expect, test } from "@playwright/test";

import {
  currentSessionId,
  fillHeroForm,
  getBackendSession,
  heroFields,
  temporaryResidenceFormPath,
} from "./support";

for (let runNumber = 1; runNumber <= 5; runNumber += 1) {
  test(`hero đăng ký tạm trú hoàn tất với dữ liệu giả — lượt ${runNumber}/5`, async ({ page, request }) => {
    await page.goto(temporaryResidenceFormPath);
    await expect(
      page.getByRole("heading", { level: 1, name: "Chuẩn bị đăng ký tạm trú" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Kiểm tra và lưu bản nháp" }).click();
    await expect(
      page.getByRole("alert", { name: "Cần sửa 11 thông tin" }),
    ).toBeVisible();
    await expect(page.locator("#registration_mode")).toBeFocused();

    await fillHeroForm(page, runNumber);
    await expect(page.getByTestId("workspace-revision")).toHaveText(String(heroFields.length));

    await page.getByRole("button", { name: "Kiểm tra và lưu bản nháp" }).click();
    await expect(page.getByRole("status")).toContainText(
      "Bản nháp đã đủ thông tin kiểm tra tại UI.",
    );
    await expect(page.getByRole("region", { name: "Thông tin tham khảo" })).toContainText(
      "Lệ phí dự kiến 7.000 đồng/lần đăng ký.",
    );

    const session = await getBackendSession(request, await currentSessionId(page));
    expect(session.draft.revision).toBe(heroFields.length);
    expect(Object.keys(session.draft.values)).toHaveLength(heroFields.length);
    expect(session.draft.values).toMatchObject({
      applicant_full_name: `Người Dùng E2E Tổng Hợp ${runNumber}`,
      temporary_address: `Số 10 phố Kiểm Thử, Hà Nội ${runNumber}`,
      applicant_is_minor: false,
      submission_channel: "online",
      fee_exemption_claimed: false,
    });
  });
}
