const { test, expect } = require("@playwright/test");

const API_BASE = process.env.E2E_API_BASE || "http://127.0.0.1:8001/api";

function uniqueEmail(prefix) {
  return `futureflex.${prefix}.${Date.now()}.${Math.random().toString(16).slice(2)}@gmail.com`;
}

function dateInMonths(months, day = 15) {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + months, day))
    .toISOString().slice(0, 10);
}

async function apiJson(page, path) {
  const response = await page.request.get(`${API_BASE}${path}`);
  expect(response.ok(), `${path} should return 2xx`).toBeTruthy();
  return response.json();
}

async function registerAndOnboard(page, balance = 2500) {
  await page.goto("/login");
  await page.getByTestId("auth-toggle-mode").click();
  await page.getByTestId("register-name").fill("QA Flexibilidade");
  await page.getByTestId("auth-email").fill(uniqueEmail("flex"));
  await page.getByTestId("auth-password").fill("Release Future Flex 2026");
  await page.getByTestId("auth-submit").click();
  await expect(page.getByTestId("onboarding-page")).toBeVisible();
  await page.getByTestId("onboarding-start").click();
  await page.getByTestId("onboarding-account-name").fill("Conta QA");
  await page.getByTestId("onboarding-account-balance").fill(String(balance));
  await page.getByTestId("onboarding-account-submit").click();
  await page.getByTestId("onboarding-income-skip").click();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
}

async function go(page, desktopId, mobileId, moreId, pageId) {
  if (await page.getByTestId(desktopId).isVisible().catch(() => false)) {
    await page.getByTestId(desktopId).click();
  } else if (mobileId && await page.getByTestId(mobileId).isVisible().catch(() => false)) {
    await page.getByTestId(mobileId).click();
  } else {
    await page.getByTestId("mobile-more-btn").click();
    await expect(page.getByTestId("mobile-more-sheet")).toBeVisible();
    await page.getByTestId(moreId).click();
  }
  await expect(page.getByTestId(pageId)).toBeVisible();
}

async function goAccounts(page) {
  return go(page, "nav-accounts-desktop", "nav-accounts-mobile", null, "accounts-page");
}
async function goThirdParties(page) {
  return go(page, "nav-third-parties-desktop", null, "nav-third-parties-more", "third-parties-page");
}
async function goCards(page) {
  return go(page, "nav-cards-desktop", null, "nav-cards-more", "cards-page");
}
async function goCommitments(page) {
  return go(page, "nav-commitments-desktop", "nav-commitments-mobile", null, "commitments-page");
}

async function openQuickAdd(page) {
  if (await page.getByTestId("sidebar-quick-add").isVisible().catch(() => false)) {
    await page.getByTestId("sidebar-quick-add").click();
  } else {
    await page.getByTestId("mobile-more-btn").click();
    await page.getByTestId("mobile-more-quick-add").click();
  }
  await expect(page.getByTestId("quick-add-drawer")).toBeVisible();
}

async function selectContaining(select, text) {
  const value = await select.locator("option").filter({ hasText: text }).first().getAttribute("value");
  expect(value).toBeTruthy();
  await select.selectOption(value);
}

test("accounts cannot be created blank and unused accounts can be edited/deleted", async ({ page }) => {
  await registerAndOnboard(page);
  await goAccounts(page);

  await page.getByTestId("new-account-btn").click();
  await page.getByTestId("account-name").press("Enter");
  await expect(page.getByText("Informe o nome da conta")).toBeVisible();
  expect(await apiJson(page, "/accounts")).toHaveLength(1);

  await page.getByTestId("account-name").fill("Conta temporária");
  await page.getByTestId("account-balance-input").fill("10,25");
  await page.getByTestId("account-save").click();
  await expect(page.getByText("Conta temporária", { exact: true })).toBeVisible();

  let accounts = await apiJson(page, "/accounts");
  const temporary = accounts.find((item) => item.name === "Conta temporária");
  expect(temporary).toBeTruthy();

  await page.getByTestId(`account-edit-${temporary.id}`).click();
  await page.getByTestId("account-name").fill("Conta corrigida");
  await page.getByTestId("account-save").click();
  await expect(page.getByText("Conta corrigida", { exact: true })).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId(`account-delete-${temporary.id}`).click();
  await expect(page.getByText("Conta corrigida", { exact: true })).toHaveCount(0);
  accounts = await apiJson(page, "/accounts");
  expect(accounts.some((item) => item.id === temporary.id)).toBeFalsy();
});

test("people and unpaid third-party records can be corrected, rescheduled and deleted", async ({ page }) => {
  await registerAndOnboard(page);
  await goThirdParties(page);

  await page.getByTestId("person-name").fill("Ana QA");
  await page.getByTestId("person-save").click();
  await expect(page.getByText("Ana QA", { exact: true }).first()).toBeVisible();

  await page.getByTestId("person-name").fill("Ana duplicada");
  await page.getByTestId("person-save").click();
  let people = await apiJson(page, "/people");
  const duplicate = people.find((item) => item.name === "Ana duplicada");
  expect(duplicate).toBeTruthy();

  await page.getByTestId(`person-edit-${duplicate.id}`).click();
  await page.getByTestId("person-name").fill("Ana corrigida");
  await page.getByTestId("person-save").click();
  people = await apiJson(page, "/people");
  expect(people.find((item) => item.id === duplicate.id)?.name).toBe("Ana corrigida");

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId(`person-delete-${duplicate.id}`).click();
  people = await apiJson(page, "/people");
  expect(people.some((item) => item.id === duplicate.id)).toBeFalsy();

  const ana = people.find((item) => item.name === "Ana QA");
  const firstDue = dateInMonths(1, 15);
  await page.getByTestId("tp-person").selectOption(ana.id);
  await page.getByTestId("tp-direction").selectOption("payable");
  await page.getByTestId("tp-description").fill("Dívida com Ana");
  await page.getByTestId("tp-amount").fill("150,55");
  await page.getByTestId("tp-installments").fill("2");
  await page.getByTestId("tp-start-date").fill(firstDue);
  await page.getByTestId("tp-save").click();
  await expect(page.getByText(/Ana QA · Dívida com Ana/)).toBeVisible();

  let thirdParties = await apiJson(page, "/third-parties");
  const rel = thirdParties.items.find((item) => item.description === "Dívida com Ana");
  expect(rel).toBeTruthy();
  expect(Number(rel.total)).toBeCloseTo(150.55, 2);
  expect(String(rel.first_due_date).slice(0, 10)).toBe(firstDue);

  const correctedDue = dateInMonths(2, 20);
  await page.getByTestId(`tp-edit-${rel.id}`).click();
  await page.getByTestId("tp-description").fill("Dívida corrigida");
  await page.getByTestId("tp-amount").fill("175,75");
  await page.getByTestId("tp-start-date").fill(correctedDue);
  await page.getByTestId("tp-save").click();

  thirdParties = await apiJson(page, "/third-parties");
  const corrected = thirdParties.items.find((item) => item.id === rel.id);
  expect(corrected.description).toBe("Dívida corrigida");
  expect(Number(corrected.total)).toBeCloseTo(175.75, 2);
  expect(String(corrected.first_due_date).slice(0, 10)).toBe(correctedDue);

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId(`tp-delete-${rel.id}`).click();
  thirdParties = await apiJson(page, "/third-parties");
  expect(thirdParties.items.some((item) => item.id === rel.id)).toBeFalsy();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId(`person-delete-${ana.id}`).click();
  people = await apiJson(page, "/people");
  expect(people.some((item) => item.id === ana.id)).toBeFalsy();
});

test("unused cards can be edited/deleted and invoice values are corrected through their items", async ({ page }) => {
  await registerAndOnboard(page, 5000);
  await goCards(page);

  await page.getByTestId("new-card-btn").click();
  await page.getByTestId("card-name").fill("Cartão temporário");
  await page.getByTestId("card-limit").fill("1000,50");
  await page.getByTestId("card-save").click();
  let cards = await apiJson(page, "/credit-cards");
  const temporary = cards.find((item) => item.name === "Cartão temporário");
  expect(temporary).toBeTruthy();

  await page.getByTestId(`card-edit-${temporary.id}`).click();
  await page.getByTestId("card-name").fill("Cartão corrigido");
  await page.getByTestId("card-save").click();
  cards = await apiJson(page, "/credit-cards");
  expect(cards.find((item) => item.id === temporary.id)?.name).toBe("Cartão corrigido");

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByTestId(`card-delete-${temporary.id}`).click();
  cards = await apiJson(page, "/credit-cards");
  expect(cards.some((item) => item.id === temporary.id)).toBeFalsy();

  await page.getByTestId("new-card-btn").click();
  await page.getByTestId("card-name").fill("Cartão Fatura QA");
  await page.getByTestId("card-limit").fill("5000");
  await page.getByTestId("card-closing-day").fill("28");
  await page.getByTestId("card-due-day").fill("5");
  await page.getByTestId("card-save").click();

  await openQuickAdd(page);
  await page.getByTestId("quick-add-type-purchase_installment").click();
  await page.getByTestId("quick-add-description").fill("Compra ajustável QA");
  await page.getByTestId("quick-add-amount").fill("300,10");
  await page.getByTestId("quick-add-installments").fill("1");
  await selectContaining(page.getByTestId("quick-add-card"), "Cartão Fatura QA");
  await page.getByTestId("quick-add-submit").click();

  let invoices = (await apiJson(page, "/invoices")).filter((item) => Number(item.total) > 0);
  expect(invoices.length).toBeGreaterThan(0);
  const invoice = invoices[0];

  await goCards(page);
  await page.getByTestId(`invoice-${invoice.id}`).click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible();
  const editButton = page.locator('button[data-testid^="invoice-item-edit-"]').first();
  await expect(editButton).toBeVisible();
  await editButton.click();
  await page.getByTestId("edit-amount-input").fill("333,33");
  await page.getByTestId("edit-amount-save").click();
  await expect(page.getByTestId("edit-amount-dialog")).toHaveCount(0);
  await expect(page.getByTestId("invoice-total")).toContainText("333,33");

  invoices = await apiJson(page, "/invoices");
  expect(Number(invoices.find((item) => item.id === invoice.id).total)).toBeCloseTo(333.33, 2);

  await goCommitments(page);
  const invoiceRow = page.getByText("Fatura Cartão Fatura QA", { exact: true })
    .locator("xpath=ancestor::div[starts-with(@data-testid, 'occurrence-')][1]");
  await expect(invoiceRow).toContainText("333,33");
  await expect(invoiceRow.locator('button[data-testid^="edit-amount-btn-"]')).toHaveCount(0);
});
