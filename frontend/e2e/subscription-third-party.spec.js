const { test, expect } = require("@playwright/test");

function uniqueEmail() {
  return `futureflex.subscription.tp.${Date.now()}.${Math.random().toString(16).slice(2)}@gmail.com`;
}

async function registerAndOnboard(page) {
  await page.goto("/login");
  await page.getByTestId("auth-toggle-mode").click();
  await page.getByTestId("register-name").fill("QA Assinatura Terceiro");
  await page.getByTestId("auth-email").fill(uniqueEmail());
  await page.getByTestId("auth-password").fill("Release Future Flex 2026");
  await page.getByTestId("auth-submit").click();
  await expect(page.getByTestId("onboarding-page")).toBeVisible();
  await page.getByTestId("onboarding-start").click();
  await page.getByTestId("onboarding-account-name").fill("Conta QA");
  await page.getByTestId("onboarding-account-balance").fill("2500,00");
  await page.getByTestId("onboarding-account-submit").click();
  await page.getByTestId("onboarding-income-skip").click();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
}

async function selectContaining(select, text) {
  const option = select.locator("option").filter({ hasText: text }).first();
  const value = await option.getAttribute("value");
  expect(value).toBeTruthy();
  await select.selectOption(value);
}

test("subscription charged on my card can be reimbursed by a third party without duplicate expense", async ({ page }) => {
  const serverErrors = [];
  page.on("response", (response) => {
    if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`);
  });

  await registerAndOnboard(page);

  await page.goto("/cartoes");
  await expect(page.getByTestId("cards-page")).toBeVisible();
  await page.getByTestId("new-card-btn").click();
  await page.getByTestId("card-name").fill("Nubank QA");
  await page.getByTestId("card-limit").fill("5000,00");
  await page.getByTestId("card-closing-day").fill("28");
  await page.getByTestId("card-due-day").fill("5");
  await page.getByTestId("card-save").click();
  await expect(page.getByText("Nubank QA", { exact: true })).toBeVisible();

  await page.goto("/terceiros");
  await expect(page.getByTestId("third-parties-page")).toBeVisible();
  await page.getByTestId("person-name").fill("Pai QA");
  await page.getByTestId("person-save").click();
  await expect(page.getByText("Pai QA", { exact: true })).toBeVisible();

  await page.goto("/assinaturas");
  await expect(page.getByTestId("subscriptions-page")).toBeVisible();
  await page.getByTestId("new-subscription-btn").click();
  await page.getByTestId("subscription-name").fill("Netflix Pai QA");
  await page.getByTestId("subscription-amount").fill("55,90");
  await page.getByTestId("subscription-billing-day").fill("10");
  await selectContaining(page.getByTestId("subscription-card"), "Nubank QA");
  await expect(page.getByTestId("subscription-responsible-person")).toBeVisible();
  await selectContaining(page.getByTestId("subscription-responsible-person"), "Pai QA");
  await expect(page.getByTestId("subscription-reimbursement-help")).toBeVisible();
  await page.getByTestId("subscription-save").click();

  const subscription = page.locator("[data-testid^='subscription-']").filter({ hasText: "Netflix Pai QA" }).first();
  await expect(subscription).toBeVisible();
  await expect(subscription).toContainText("Pai QA reembolsa");
  await expect(subscription).toContainText("R$ 55,90 pendente");

  await page.goto("/terceiros");
  const thirdParty = page.locator("[data-testid^='tp-item-']").filter({ hasText: "Netflix Pai QA" }).first();
  await expect(thirdParty).toBeVisible();
  await expect(thirdParty).toContainText("Pai QA");
  await expect(thirdParty).toContainText("assinatura");
  await expect(thirdParty).toContainText("R$ 55,90 pendente");
  await expect(thirdParty.getByTitle("Gerenciado em Assinaturas")).toBeDisabled();

  await page.goto("/cartoes");
  await expect(page.getByTestId("cards-page")).toBeVisible();
  const invoiceButton = page.locator("button[data-testid^='invoice-']").filter({ hasText: "55,90" }).first();
  await expect(invoiceButton).toBeVisible();
  await invoiceButton.click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible();
  await expect(page.getByTestId("invoice-total")).toContainText("55,90");
  await expect(page.getByTestId("invoice-detail")).toContainText("Netflix Pai QA");

  await page.goto("/assinaturas");
  const row = page.locator("[data-testid^='subscription-']").filter({ hasText: "Netflix Pai QA" }).first();
  await row.getByTitle("Editar").click();
  await page.getByTestId("subscription-amount").fill("59,90");
  await page.getByTestId("subscription-save").click();
  await expect(page.locator("[data-testid^='subscription-']").filter({ hasText: "Netflix Pai QA" }).first()).toContainText("R$ 59,90 pendente");

  await page.goto("/terceiros");
  await expect(page.locator("[data-testid^='tp-item-']").filter({ hasText: "Netflix Pai QA" }).first()).toContainText("R$ 59,90 pendente");

  expect(serverErrors).toEqual([]);
});
