const { test, expect } = require("@playwright/test");

const API_BASE = process.env.E2E_API_BASE || "http://127.0.0.1:8001/api";

function uniqueEmail(prefix = "release") {
  return `futureflex.${prefix}.${Date.now()}.${Math.random().toString(16).slice(2)}@gmail.com`;
}

function watchServerErrors(page) {
  const serverErrors = [];
  page.on("response", (response) => {
    if (response.status() >= 500) {
      serverErrors.push(`${response.status()} ${response.url()}`);
    }
  });
  return serverErrors;
}

async function apiJson(page, path) {
  const response = await page.request.get(`${API_BASE}${path}`);
  expect(response.ok(), `${path} should return 2xx`).toBeTruthy();
  return response.json();
}

async function selectOptionContaining(select, text) {
  const value = await select.locator("option").filter({ hasText: text }).first().getAttribute("value");
  expect(value, `option containing ${text} should exist`).toBeTruthy();
  await select.selectOption(value);
}

async function registerAndOnboard(page, { balance = 2500, accountName = "Conta QA" } = {}) {
  await page.goto("/login");
  await expect(page.getByTestId("auth-email")).toBeVisible();

  await page.getByTestId("auth-toggle-mode").click();
  await page.getByTestId("register-name").fill("QA Release");
  await page.getByTestId("auth-email").fill(uniqueEmail());
  await page.getByTestId("auth-password").fill("Release Future Flex 2026");
  await page.getByTestId("auth-submit").click();

  await expect(page.getByTestId("onboarding-page")).toBeVisible();
  await page.getByTestId("onboarding-start").click();
  await page.getByTestId("onboarding-account-name").fill(accountName);
  await page.getByTestId("onboarding-account-balance").fill(String(balance));
  await page.getByTestId("onboarding-account-submit").click();

  await expect(page.getByTestId("onboarding-income-ask")).toBeVisible();
  await page.getByTestId("onboarding-income-skip").click();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
}

async function openQuickAdd(page) {
  if (await page.getByTestId("sidebar-quick-add").isVisible().catch(() => false)) {
    await page.getByTestId("sidebar-quick-add").click();
  } else {
    await page.getByTestId("mobile-more-btn").click();
    await expect(page.getByTestId("mobile-more-sheet")).toBeVisible();
    await page.getByTestId("mobile-more-quick-add").click();
  }
  await expect(page.getByTestId("quick-add-drawer")).toBeVisible();
}

async function goToCommitments(page) {
  if (await page.getByTestId("nav-commitments-desktop").isVisible().catch(() => false)) {
    await page.getByTestId("nav-commitments-desktop").click();
  } else {
    await page.getByTestId("nav-commitments-mobile").click();
  }
  await expect(page.getByTestId("commitments-page")).toBeVisible();
}

async function goToCards(page) {
  if (await page.getByTestId("nav-cards-desktop").isVisible().catch(() => false)) {
    await page.getByTestId("nav-cards-desktop").click();
  } else {
    await page.getByTestId("mobile-more-btn").click();
    await expect(page.getByTestId("mobile-more-sheet")).toBeVisible();
    await page.getByTestId("nav-cards-more").click();
  }
  await expect(page.getByTestId("cards-page")).toBeVisible();
}

async function currentBalance(page) {
  const accounts = await apiJson(page, "/accounts");
  expect(accounts).toHaveLength(1);
  return Number(accounts[0].current_balance);
}

test("new user can register, onboard, reload and reach commitments", async ({ page }) => {
  const serverErrors = watchServerErrors(page);
  await registerAndOnboard(page, { balance: 2500 });

  await expect(page.getByTestId("metric-balance")).toContainText("2.500");
  await expect(page.getByTestId("free-money-card")).toBeVisible();

  // Ambient auth cookies alone are not enough to mutate financial state.
  const forged = await page.request.post(`${API_BASE}/accounts`, {
    data: { name: "Conta CSRF forjada", type: "checking", opening_balance: 9999 },
  });
  expect(forged.status()).toBe(403);
  expect((await forged.json()).detail).toContain("CSRF");
  expect(await apiJson(page, "/accounts")).toHaveLength(1);

  // Onboarding must be idempotent after the first account exists.
  await page.reload();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByTestId("onboarding-page")).toHaveCount(0);

  // Simulate an expired access token while keeping the refresh credential. The SPA
  // must transparently rotate the session and stay logged in after a full reload.
  const cookies = await page.context().cookies();
  expect(cookies.some((cookie) => cookie.name === "refresh_token")).toBeTruthy();
  await page.context().clearCookies();
  await page.context().addCookies(cookies.filter((cookie) => cookie.name !== "access_token"));
  await page.reload();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByTestId("bootstrap-error")).toHaveCount(0);

  await page.getByTestId("dashboard-to-commitments").click();
  await expect(page).toHaveURL(/\/compromissos$/);
  await expect(page.getByTestId("commitments-page")).toBeVisible();
  await expect(page.getByTestId("month-committed")).toBeVisible();

  expect(serverErrors).toEqual([]);
});

test("account commitment does not debit until payment and payment updates the month", async ({ page }) => {
  const serverErrors = watchServerErrors(page);
  await registerAndOnboard(page, { balance: 2500 });

  await openQuickAdd(page);
  await page.getByTestId("quick-add-type-fixed_expense").click();
  await page.getByTestId("quick-add-description").fill("Energia QA");
  await page.getByTestId("quick-add-amount").fill("300");
  await page.getByTestId("quick-add-day").fill("28");
  await selectOptionContaining(page.getByTestId("quick-add-account"), "Conta QA");
  await page.getByTestId("quick-add-submit").click();
  await expect(page.getByTestId("quick-add-drawer")).toHaveCount(0);

  // Planning is not a Transaction: creating the commitment must not change cash balance.
  expect(await currentBalance(page)).toBeCloseTo(2500, 2);

  await goToCommitments(page);
  await expect(page.getByTestId("month-committed")).toContainText("300");
  await expect(page.getByTestId("month-pending")).toContainText("300");

  const row = page
    .getByText("Energia QA", { exact: true })
    .locator("xpath=ancestor::div[starts-with(@data-testid, 'occurrence-')][1]");
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Pagar" }).click();

  await expect(page.getByTestId("pay-dialog")).toBeVisible();
  await selectOptionContaining(page.getByTestId("pay-account-select"), "Conta QA");
  await page.getByTestId("pay-confirm-btn").click();
  await expect(page.getByTestId("pay-dialog")).toHaveCount(0);

  await expect(page.getByTestId("month-paid")).toContainText("300");
  await expect(page.getByTestId("month-pending")).toContainText("0,00");
  expect(await currentBalance(page)).toBeCloseTo(2200, 2);
  await expect(row.getByRole("button", { name: "Pagar" })).toHaveCount(0);

  expect(serverErrors).toEqual([]);
});

test("card purchase composes invoice without double counting and only invoice payment debits account", async ({ page }) => {
  const serverErrors = watchServerErrors(page);
  await registerAndOnboard(page, { balance: 5000 });

  await goToCards(page);
  await page.getByTestId("new-card-btn").click();
  await page.getByTestId("card-name").fill("Cartão QA");
  await page.getByTestId("card-limit").fill("10000");
  await page.getByTestId("card-closing-day").fill("28");
  await page.getByTestId("card-due-day").fill("5");
  await page.getByTestId("card-save").click();
  await expect(page.getByText("Cartão QA", { exact: true })).toBeVisible();

  await openQuickAdd(page);
  await page.getByTestId("quick-add-type-purchase_installment").click();
  await page.getByTestId("quick-add-description").fill("Notebook QA");
  await page.getByTestId("quick-add-amount").fill("600");
  await page.getByTestId("quick-add-installments").fill("2");
  await selectOptionContaining(page.getByTestId("quick-add-card"), "Cartão QA");
  await page.getByTestId("quick-add-submit").click();
  await expect(page.getByTestId("quick-add-drawer")).toHaveCount(0);

  // Absolute business rule: card purchase never debits the bank account.
  expect(await currentBalance(page)).toBeCloseTo(5000, 2);

  let invoices = [];
  await expect
    .poll(async () => {
      invoices = (await apiJson(page, "/invoices")).filter((invoice) => Number(invoice.total) > 0);
      return invoices.length;
    })
    .toBeGreaterThan(0);

  invoices.sort((a, b) => a.competence.localeCompare(b.competence));
  const invoice = invoices[0];
  const month = await apiJson(page, `/months/${invoice.competence}`);
  const cardsGroup = month.groups.find((group) => group.key === "cards");
  const installmentsGroup = month.groups.find((group) => group.key === "installments");
  const cardChild = installmentsGroup?.items.find((item) => item.label.includes("Notebook QA"));

  expect(cardsGroup, "card invoice group should exist").toBeTruthy();
  expect(cardChild, "installment occurrence should be present as invoice composition").toBeTruthy();
  expect(cardChild.counts_in_total).toBeFalsy();
  expect(Number(cardsGroup.total)).toBeCloseTo(Number(invoice.total), 2);
  expect(Number(month.committed)).toBeCloseTo(Number(invoice.total), 2);

  await goToCards(page);
  await expect(page.getByTestId(`invoice-${invoice.id}`)).toBeVisible();
  await page.getByTestId(`invoice-${invoice.id}`).click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible();
  await expect(page.getByText(/Notebook QA/).first()).toBeVisible();
  await page.getByTestId("pay-invoice-btn").click();

  await expect(page.getByTestId("pay-dialog")).toBeVisible();
  await selectOptionContaining(page.getByTestId("pay-account-select"), "Conta QA");
  await page.getByTestId("pay-confirm-btn").click();
  await expect(page.getByTestId("pay-dialog")).toHaveCount(0);

  expect(await currentBalance(page)).toBeCloseTo(5000 - Number(invoice.total), 2);

  await expect
    .poll(async () => {
      const refreshed = await apiJson(page, "/invoices");
      return refreshed.find((item) => item.id === invoice.id)?.status;
    })
    .toBe("paid");

  expect(serverErrors).toEqual([]);
});
