const { chromium } = require("playwright");
const { AxeBuilder } = require("@axe-core/playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = "http://localhost:8501";
const REPORT_DIR = path.join(__dirname, "reports");

// Streamlit 페이지 목록
const PAGES = [
  { name: "메인 페이지", path: "/" },
  { name: "냉장고 스캔", path: "/fridge_scan" },
  { name: "재료 관리", path: "/ingredients" },
  { name: "레시피 추천", path: "/recipes" },
  { name: "프로필 설정", path: "/profile" },
  { name: "저장된 레시피", path: "/saved_recipes" },
  { name: "장보기 목록", path: "/shopping" },
];

async function waitForStreamlit(page) {
  // Streamlit이 로드될 때까지 대기
  await page.waitForLoadState("networkidle");
  // Streamlit 특유의 로딩 완료 대기
  await page
    .waitForSelector('[data-testid="stAppViewContainer"]', { timeout: 15000 })
    .catch(() => {});
  // 추가 렌더링 대기
  await page.waitForTimeout(2000);
}

async function runAxeOnPage(page, pageName) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
    .analyze();

  return {
    page: pageName,
    url: page.url(),
    timestamp: new Date().toISOString(),
    violations: results.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      help: v.help,
      helpUrl: v.helpUrl,
      nodes: v.nodes.length,
      targets: v.nodes.slice(0, 3).map((n) => n.target.join(" > ")),
    })),
    passes: results.passes.length,
    incomplete: results.incomplete.length,
    inapplicable: results.inapplicable.length,
  };
}

function generateMarkdownReport(allResults) {
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");

  let md = `# 접근성(AX) 테스트 리포트\n\n`;
  md += `**테스트 일시:** ${now}\n`;
  md += `**테스트 도구:** axe-core + Playwright\n`;
  md += `**기준:** WCAG 2.1 AA + Best Practice\n\n`;
  md += `---\n\n`;

  // 요약
  let totalViolations = 0;
  let totalPasses = 0;

  for (const result of allResults) {
    totalViolations += result.violations.length;
    totalPasses += result.passes;
  }

  md += `## 요약\n\n`;
  md += `| 페이지 | 위반 | 통과 | 미완료 |\n`;
  md += `|--------|------|------|--------|\n`;

  for (const result of allResults) {
    const violationIcon =
      result.violations.length === 0
        ? "✅"
        : result.violations.some((v) => v.impact === "critical")
          ? "🔴"
          : "🟡";
    md += `| ${violationIcon} ${result.page} | ${result.violations.length} | ${result.passes} | ${result.incomplete} |\n`;
  }

  md += `\n**총 위반:** ${totalViolations}건 | **총 통과:** ${totalPasses}건\n\n`;
  md += `---\n\n`;

  // 페이지별 상세
  for (const result of allResults) {
    md += `## ${result.page}\n\n`;

    if (result.violations.length === 0) {
      md += `✅ 접근성 위반 사항이 발견되지 않았습니다.\n\n`;
    } else {
      md += `| 심각도 | 규칙 | 설명 | 영향 요소 |\n`;
      md += `|--------|------|------|-----------|\n`;

      for (const v of result.violations) {
        const impactIcon =
          v.impact === "critical"
            ? "🔴"
            : v.impact === "serious"
              ? "🟠"
              : v.impact === "moderate"
                ? "🟡"
                : "🔵";
        md += `| ${impactIcon} ${v.impact} | ${v.id} | ${v.help} | ${v.nodes}개 |\n`;
      }

      md += `\n`;

      // 상세 위반 내용
      md += `<details>\n<summary>상세 위반 내용 보기</summary>\n\n`;
      for (const v of result.violations) {
        md += `### ${v.id} (${v.impact})\n`;
        md += `- **설명:** ${v.description}\n`;
        md += `- **도움말:** ${v.help}\n`;
        md += `- **참고:** ${v.helpUrl}\n`;
        md += `- **영향 요소 (최대 3개):**\n`;
        for (const t of v.targets) {
          md += `  - \`${t}\`\n`;
        }
        md += `\n`;
      }
      md += `</details>\n\n`;
    }

    md += `---\n\n`;
  }

  return md;
}

async function main() {
  const generateReport = process.argv.includes("--report");

  console.log("🔍 컬리너리 에이전트 접근성(AX) 자동화 테스트 시작\n");
  console.log(`📋 테스트 대상: ${PAGES.length}개 페이지`);
  console.log(`🌐 서버: ${BASE_URL}\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    locale: "ko-KR",
  });

  const allResults = [];

  for (const pageInfo of PAGES) {
    const page = await context.newPage();
    const url = `${BASE_URL}${pageInfo.path}`;

    console.log(`🧪 테스트 중: ${pageInfo.name} (${url})`);

    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
      await waitForStreamlit(page);

      const result = await runAxeOnPage(page, pageInfo.name);
      allResults.push(result);

      if (result.violations.length === 0) {
        console.log(`   ✅ 위반 없음 (통과: ${result.passes})\n`);
      } else {
        console.log(
          `   ⚠️  위반 ${result.violations.length}건 발견 (통과: ${result.passes})`
        );
        for (const v of result.violations) {
          console.log(`      - [${v.impact}] ${v.id}: ${v.help} (${v.nodes}개 요소)`);
        }
        console.log();
      }
    } catch (err) {
      console.log(`   ❌ 오류: ${err.message}\n`);
      allResults.push({
        page: pageInfo.name,
        url,
        timestamp: new Date().toISOString(),
        violations: [{ id: "error", impact: "critical", description: err.message, help: "페이지 로드 실패", helpUrl: "", nodes: 0, targets: [] }],
        passes: 0,
        incomplete: 0,
        inapplicable: 0,
      });
    }

    await page.close();
  }

  await browser.close();

  // 결과 요약
  const totalViolations = allResults.reduce(
    (sum, r) => sum + r.violations.length,
    0
  );
  const totalPasses = allResults.reduce((sum, r) => sum + r.passes, 0);

  console.log("━".repeat(50));
  console.log(`\n📊 최종 결과: 위반 ${totalViolations}건 / 통과 ${totalPasses}건\n`);

  // 리포트 저장
  if (!fs.existsSync(REPORT_DIR)) {
    fs.mkdirSync(REPORT_DIR, { recursive: true });
  }

  // JSON 리포트
  const jsonPath = path.join(REPORT_DIR, "ax-results.json");
  fs.writeFileSync(jsonPath, JSON.stringify(allResults, null, 2), "utf-8");
  console.log(`📄 JSON 리포트: ${jsonPath}`);

  // Markdown 리포트
  const mdReport = generateMarkdownReport(allResults);
  const mdPath = path.join(REPORT_DIR, "ax-report.md");
  fs.writeFileSync(mdPath, mdReport, "utf-8");
  console.log(`📄 MD 리포트: ${mdPath}`);

  // 종료 코드 (위반이 있으면 1)
  process.exit(totalViolations > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error("❌ 테스트 실행 실패:", err);
  process.exit(2);
});
