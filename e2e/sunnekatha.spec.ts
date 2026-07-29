import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
});

test("homepage loads its primary content", async ({ page }) => {
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "नेपाली साहित्य अब कानसम्म",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "विशेष प्लेलिस्टहरू" }),
  ).toBeVisible();
});

test("user opens a playlist", async ({ page }) => {
  await page
    .getByRole("region", { name: "विशेष प्रस्तुति" })
    .getByRole("link", { name: "सुन्नैपर्ने नेपाली कविता", exact: true })
    .click();

  await expect(page).toHaveURL(/\/playlist\/sunnai-parne-nepali-kavita$/);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "सुन्नैपर्ने नेपाली कविता",
    }),
  ).toBeVisible();
});

test("playing survives navigation and the queue opens", async ({ page }) => {
  await page
    .getByRole("region", { name: "यो हप्ता लोकप्रिय" })
    .getByRole("button", { name: "प्रेमका कविता बजाउनुहोस्" })
    .click();

  const player = page.getByRole("region", { name: "अडियो प्लेयर" });
  await expect(player).toContainText("प्रेमका कविता");
  await expect(player.getByRole("button", { name: "पज गर्नुहोस्" })).toBeVisible();

  await page.getByRole("link", { name: "खोज्नुहोस्", exact: true }).click();
  await expect(page).toHaveURL(/\/search$/);
  await expect(player).toContainText("प्रेमका कविता");
  await expect(player.getByRole("button", { name: "पज गर्नुहोस्" })).toBeVisible();

  await player.getByRole("button", { name: "प्ले सूची खोल्नुहोस्" }).click();
  await expect(
    page.getByRole("dialog", { name: "प्ले सूची" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "अहिले बज्दैछ" }),
  ).toBeVisible();
});

test("search returns matching Nepali literature", async ({ page }) => {
  await page.goto("/search");
  const searchbox = page.getByRole("searchbox", {
    name: "SunneKatha मा खोज्नुहोस्",
  });
  await searchbox.fill("वर्षाको साँझ");

  await expect(page).toHaveURL(/q=/);
  await expect(page.locator('a[href="/track/barshako-saanjh"]')).toBeVisible();
});

test("favoriting a track adds it to the library", async ({ page }) => {
  await page.goto("/track/seto-gurans");
  await page
    .getByRole("main")
    .getByRole("button", { name: "मनपर्नेमा", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "मनपर्ने", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("link", { name: "लाइब्रेरी", exact: true }).click();
  await expect(page).toHaveURL(/\/library$/);
  await expect(
    page.getByRole("link", { name: "सेतो गुराँस", exact: true }),
  ).toBeVisible();
});
