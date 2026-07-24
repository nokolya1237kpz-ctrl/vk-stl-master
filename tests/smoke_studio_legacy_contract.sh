#!/usr/bin/env bash
set -euo pipefail

APP_URL="${APP_URL:-https://app.stlmaster.online/app}"

if ! command -v node >/dev/null 2>&1; then
  echo "node is required"
  exit 1
fi

cd /home/codex/projects/vk-stl-master/frontend

node <<'NODE'
const { chromium } = require("playwright");

const appUrl = process.env.APP_URL || "https://app.stlmaster.online/app";
const bannedTexts = [
  "Пять шагов проверки",
  "Новая обработка",
  "Модель появится здесь",
  "Код доступа",
  "Подготовка 3D-моделей к печати",
];
const bannedSelectors = [
  ".appIntro",
  ".uploadPanel",
  ".dropZone",
  ".betaAccessPanel",
  ".operationsPanel",
  ".presetGrid",
  ".actionCard",
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1536, height: 1024 } });
  await page.goto(appUrl, { waitUntil: "load" });
  await page.waitForSelector(".studioShell", { timeout: 15000 });

  const report = await page.evaluate(({ bannedTexts, bannedSelectors }) => {
    const bodyText = document.body.textContent || "";
    return {
      oldTexts: bannedTexts.filter((text) => bodyText.includes(text)),
      oldSelectors: bannedSelectors.filter((selector) => document.querySelector(selector)),
      studioShell: Boolean(document.querySelector(".studioShell")),
      studioHeader: Boolean(document.querySelector(".studioHeader")),
      studioViewer: Boolean(document.querySelector(".studioViewerWorkspace")),
      studioInspector: Boolean(document.querySelector(".studioInspector")),
      studioWorkflow: Boolean(document.querySelector(".studioWorkflowBar")),
      fileInputs: document.querySelectorAll("input[type=file]").length,
      fileAccepts: Array.from(document.querySelectorAll("input[type=file]")).map((input) => input.getAttribute("accept")),
    };
  }, { bannedTexts, bannedSelectors });

  await browser.close();

  if (!report.studioShell || !report.studioHeader || !report.studioViewer || !report.studioInspector || !report.studioWorkflow) {
    console.error("Studio shell contract failed", report);
    process.exit(1);
  }
  if (report.oldTexts.length || report.oldSelectors.length) {
    console.error("Legacy editor contract failed", report);
    process.exit(1);
  }
  if (report.fileInputs !== 1 || report.fileAccepts[0] !== ".stl") {
    console.error("STL input contract failed", report);
    process.exit(1);
  }

  console.log("Studio legacy contract OK", report);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
NODE
