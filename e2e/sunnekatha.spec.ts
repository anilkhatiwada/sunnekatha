import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await page.waitForFunction(() =>
    window.localStorage.getItem("sunnekatha-player"),
  );
});

test("homepage loads its primary content", async ({ page }) => {
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Nepali literature, now in audio",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Featured playlists" }),
  ).toBeVisible();
});

test("user opens a playlist", async ({ page }) => {
  await page
    .locator('a[href="/playlist/sunnai-parne-nepali-kavita"]')
    .first()
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
    .getByRole("region", { name: "Popular this week" })
    .getByRole("button", { name: "प्रेमका कविता — play" })
    .click();

  const player = page.getByRole("region", { name: "Audio player" });
  await expect(player).toContainText("प्रेमका कविता");
  await expect(player.getByRole("button", { name: "Pause" })).toBeVisible();

  await page.getByRole("link", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/\/search$/);
  await expect(player).toContainText("प्रेमका कविता");
  await expect(player.getByRole("button", { name: "Pause" })).toBeVisible();

  await player.getByRole("button", { name: "Open queue" }).click();
  await expect(page.getByRole("dialog", { name: "Queue" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Now playing" }),
  ).toBeVisible();
});

test("search returns matching Nepali literature", async ({ page }) => {
  await page.goto("/search");
  const searchbox = page.getByRole("combobox", {
    name: "Search SunneKatha",
  });
  await searchbox.fill("वर्षाको साँझ");

  await expect(page).toHaveURL(/q=/);
  await expect(page.locator('a[href="/track/barshako-saanjh"]')).toBeVisible();
});

test("favoriting requires authentication", async ({ page }) => {
  await page.goto("/track/seto-gurans");
  await page
    .getByRole("main")
    .getByRole("button", { name: "Add to favorites", exact: true })
    .click();
  await expect(
    page.getByText("Sign in to add this track to your favorites.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/track\/seto-gurans$/);
});
