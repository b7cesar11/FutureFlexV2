const { test, expect } = require("@playwright/test");

function uniqueEmail() {
  return `futureflex.release.${Date.now()}.${Math.random().toString(16).slice(2)}@gmail.com`;
}

test("new user can register, onboard, reload and reach commitments", async ({ page }) => {
  const serverErrors = [];
  page.on("response", (response) => {
    if (response.status() >= 500) {
      serverErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto("/login");
  await expect(page.getByTestId("auth-email")).toBeVisible();

  await page.getByTestId("auth-toggle-mode").click();
  await page.getByTestId("register-name").fill("QA Release");
  await page.getByTestId("auth-email").fill(uniqueEmail());
  await page.getByTestId("auth-password").fill("Release@2026");
  await page.getByTestId("auth-submit").click();

  await expect(page.getByTestId("onboarding-page")).toBeVisible();
  await page.getByTestId("onboarding-start").click();
  await page.getByTestId("onboarding-account-name").fill("Conta QA");
  await page.getByTestId("onboarding-account-balance").fill("2500");
  await page.getByTestId("onboarding-account-submit").click();

  await expect(page.getByTestId("onboarding-income-ask")).toBeVisible();
  await page.getByTestId("onboarding-income-skip").click();

  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByTestId("metric-balance")).toContainText("2.500");
  await expect(page.getByTestId("free-money-card")).toBeVisible();

  // Onboarding must be idempotent after the first account exists.
  await page.reload();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByTestId("onboarding-page")).toHaveCount(0);

  await page.getByTestId("dashboard-to-commitments").click();
  await expect(page).toHaveURL(/\/compromissos$/);
  await expect(page.getByTestId("commitments-page")).toBeVisible();
  await expect(page.getByTestId("month-committed")).toBeVisible();

  expect(serverErrors).toEqual([]);
});
