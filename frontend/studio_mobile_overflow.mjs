import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
await page.goto("https://app.stlmaster.online/app", { waitUntil: "networkidle" });
const data = await page.evaluate(() => {
  const width = window.innerWidth;
  const offenders = [...document.querySelectorAll("body *")]
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        tag: element.tagName.toLowerCase(),
        className: typeof element.className === "string" ? element.className : "",
        text: element.textContent?.trim().slice(0, 80) || "",
        x: Math.round(rect.x),
        width: Math.round(rect.width),
        right: Math.round(rect.right),
      };
    })
    .filter((item) => item.right > width + 2 || item.x < -2)
    .sort((a, b) => b.right - a.right)
    .slice(0, 30);
  return { innerWidth: width, scrollWidth: document.documentElement.scrollWidth, offenders };
});
await browser.close();
console.log(JSON.stringify(data, null, 2));
