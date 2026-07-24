#!/usr/bin/env bash
set -euo pipefail

SMOKE_TEST_NAME="$(basename "$0")"
SMOKE_TEST_RUN_ID="${SMOKE_TEST_RUN_ID:-$(python3 - <<'PY_SMOKE_ID'
import uuid
print(uuid.uuid4())
PY_SMOKE_ID
)}"
SMOKE_UPLOAD_FIELDS=(
  -F "is_test=true"
  -F "source=smoke_test"
  -F "environment=test"
  -F "test_run_id=${SMOKE_TEST_RUN_ID}"
  -F "test_name=${SMOKE_TEST_NAME}"
)
SMOKE_JSON_META="\"is_test\":true,\"source\":\"smoke_test\",\"environment\":\"test\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\",\"test_name\":\"${SMOKE_TEST_NAME}\""

smoke_cleanup_run() {
  local api="${API_BASE:-http://localhost:8000}"
  if [[ "${SMOKE_SKIP_CLEANUP:-0}" == "1" || -z "${ADMIN_TOKEN:-}" ]]; then
    return 0
  fi
  local cleanup_response
  cleanup_response="$(curl --max-time 15 -sS     -H "X-Admin-Token: ${ADMIN_TOKEN}"     -H 'Content-Type: application/json'     -d "{\"confirmation\":\"УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\"}"     "${api}/api/v1/admin/test-data/cleanup" || true)"
  if [[ -z "${cleanup_response}" ]]; then
    return 0
  fi
  python3 - "${cleanup_response}" <<'PY_SMOKE_CLEANUP'
import json
import sys
try:
    payload = json.loads(sys.argv[1])
except Exception:
    raise SystemExit(0)
if payload.get("ok") is not True:
    raise SystemExit("smoke cleanup failed")
remaining = payload.get("remaining_test_counts") or {}
if any(int(value or 0) for value in remaining.values()):
    raise SystemExit(f"smoke cleanup left test records: {remaining}")
print("smoke cleanup OK")
PY_SMOKE_CLEANUP
}
trap smoke_cleanup_run EXIT


PROJECT_DIR="/home/codex/projects/vk-stl-master"
FRONTEND_MAIN="${PROJECT_DIR}/frontend/src/main.jsx"
CSS_FILE="${PROJECT_DIR}/frontend/src/styles.css"
MARKETING_DIR="${PROJECT_DIR}/frontend/public/assets/marketing"

echo "STL Master public pixel-perfect design contract"

test -s "${MARKETING_DIR}/dragon-skull/dragon_skull_demo_poster.png" || { echo "demo skull render missing" >&2; exit 1; }

if grep -R "stl-redesign\|hero-studio-window-reference\|studio-split\|demo-renders-grid\|compare-before\|compare-after\|modal-skull\|hero-skull\|model-check\|export-ready" "${FRONTEND_MAIN}" "${CSS_FILE}" >/tmp/stl_public_reference_png_usage.txt; then
  cat /tmp/stl_public_reference_png_usage.txt >&2
  echo "reference PNGs must not be used as website building blocks" >&2
  exit 1
fi

grep -q "function PublicLanding" "${FRONTEND_MAIN}" || { echo "PublicLanding missing" >&2; exit 1; }
grep -q "function StudioMockup" "${FRONTEND_MAIN}" || { echo "Studio mockup missing" >&2; exit 1; }
grep -q "function PublicModal" "${FRONTEND_MAIN}" || { echo "modal component missing" >&2; exit 1; }
grep -q "function PremiumAccessModal" "${FRONTEND_MAIN}" || { echo "premium access modal missing" >&2; exit 1; }
if grep -RniE "function PremiumPage|premiumPage|Заявка Premium отправлена|Отправить заявку Premium|Официальное сообщество VK|Сервер не ответил за 15 секунд|Не удалось зарегистрировать заявку|Не удалось создать заявку" "${FRONTEND_MAIN}" "${CSS_FILE}" >/tmp/stl_public_premium_legacy.txt; then
  cat /tmp/stl_public_premium_legacy.txt >&2
  echo "legacy premium flow code/text must be removed" >&2
  exit 1
fi
grep -q "function ConnectorsSection" "${FRONTEND_MAIN}" || { echo "connectors section missing" >&2; exit 1; }
grep -q "function StlMarketingViewer" "${FRONTEND_MAIN}" || { echo "STL marketing viewer missing" >&2; exit 1; }
grep -q "function BeforeAfterShowcase" "${FRONTEND_MAIN}" || { echo "before/after showcase missing" >&2; exit 1; }
grep -q "function FeaturesSection" "${FRONTEND_MAIN}" || { echo "features section missing" >&2; exit 1; }
grep -q "function PremiumShowcase" "${FRONTEND_MAIN}" || { echo "premium showcase missing" >&2; exit 1; }
grep -q "function ModalArtScene" "${FRONTEND_MAIN}" || { echo "modal art component missing" >&2; exit 1; }
grep -q "function DemoStudioPreview" "${FRONTEND_MAIN}" || { echo "demo modal component missing" >&2; exit 1; }

for token in \
  "STL Master Studio" \
  "STL Master v2.0" \
  "Возможности" \
  "Соединения" \
  "До / После" \
  "Тарифы" \
  "FAQ" \
  "Открыть приложение" \
  "Подключить Premium"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "header token missing: $token" >&2; exit 1; }
done

if grep -q "reviewItems\|function TestimonialsSection\|id=\"reviews\"\|\[\"reviews\"" "${FRONTEND_MAIN}"; then
  echo "public testimonials/reviews code must be removed" >&2
  exit 1
fi

if grep -q "testimonialRail\|testimonialCard\|testimonialAvatar" "${CSS_FILE}"; then
  echo "testimonial CSS must be removed" >&2
  exit 1
fi

for token in \
  "Исправляйте, режьте" \
  "и готовьте модели" \
  "heroTitleAccent" \
  "Автоматическое исправление сетки, разрез на части" \
  "Загрузить STL" \
  "Смотреть возможности" \
  "Быстро" \
  "Надёжно" \
  "Удобно" \
  ".stl" ".obj" ".3mf" ".ply" ".amf" ".step" "+ ещё"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "hero token missing: $token" >&2; exit 1; }
done

for token in \
  "ИНФОРМАЦИЯ О МОДЕЛИ" \
  "Треугольников" \
  "ПРОВЕРКА МОДЕЛИ" \
  "БЫСТРЫЕ ДЕЙСТВИЯ" \
  "Экспорт" \
  "Запустить проверку" \
  "Авто-исправление"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "studio token missing: $token" >&2; exit 1; }
done

for step in \
  "Загрузите STL" \
  "Проверьте модель" \
  "Исправьте и оптимизируйте" \
  "Разрежьте и соедините" \
  "Проверьте печать" \
  "Экспортируйте"; do
  grep -q "$step" "${FRONTEND_MAIN}" || { echo "workflow step missing: $step" >&2; exit 1; }
done

for connector in \
  "Обычный разрез" \
  "Под склейку" \
  "Штифты" \
  "Магниты" \
  "Профильный замок" \
  "Пазы и направляющие"; do
  grep -q "$connector" "${FRONTEND_MAIN}" || { echo "connector missing: $connector" >&2; exit 1; }
done

for token in \
  "Посмотрите, как меняется модель после обработки" \
  "Проверено и подготовлено к печати" \
  "Открытые края" \
  "Модель снова замкнута" \
  "Треугольников" \
  "Перетащите для сравнения"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "before/after token missing: $token" >&2; exit 1; }
done

for feature in \
  "Анализ модели" \
  "Ремонт сетки" \
  "Очистка артефактов" \
  "Оптимизация" \
  "Экспорт"; do
  grep -q "$feature" "${FRONTEND_MAIN}" || { echo "feature missing: $feature" >&2; exit 1; }
done

for token in \
  "STL Master Premium" \
  "299 ₽ / месяц" \
  "Подключить Premium" \
  "Файлы STL до 300 МБ" \
  "Повышенный приоритет обработки" \
  "Бесплатно" \
  "Premium"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "premium token missing: $token" >&2; exit 1; }
done

for token in \
  "Сообщение подготовлено" \
  "Активировать Premium" \
  "Ожидаем Premium-код" \
  "Открыть профиль администратора" \
  "Ввести Premium-код" \
  "Заявка отклонена" \
  "Premium активирован" \
  "Не удалось активировать Premium" \
  "Скопировать сообщение" \
  "Написать администратору" \
  "Создаём заявку" \
  "Проверяем код" \
  "premium-requests/by-number" \
  "premium/activate"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "modal state missing: $token" >&2; exit 1; }
done

for link in \
  "https://vk.ru/3dmodeliron" \
  "https://vk.ru/pechatdlyadoma" \
  "https://t.me/chat_pechatdlyadoma" \
  "https://pikabu.ru/@PechatDlyaDoma"; do
  grep -q "$link" "${FRONTEND_MAIN}" || { echo "contact link missing: $link" >&2; exit 1; }
done

if grep -q "https://vk.com/3dmodeliron\|https://vk.com/pechatdlyadoma\|mailto:\|#support" "${FRONTEND_MAIN}"; then
  echo "legacy public support links must not remain" >&2
  exit 1
fi

for token in \
  "07 / FAQ" \
  "Ответы на частые вопросы" \
  "Какие файлы поддерживает STL Master?" \
  "Найти ответ" \
  "Поиск по FAQ" \
  "FAQPage" \
  "Не нашли ответ" \
  "Написать в поддержку" \
  "Продукт" \
  "Поддержка" \
  "Инструменты" \
  "currentYear" \
  "соц" \
  "Все права защищены"; do
  grep -q "$token" "${FRONTEND_MAIN}" || { echo "footer/review/faq token missing: $token" >&2; exit 1; }
done

if grep -q "Получить доступ\|Попробовать бесплатно\|Смотреть демо" "${FRONTEND_MAIN}"; then
  echo "legacy public CTA labels must not remain" >&2
  exit 1
fi

if grep -q "href=\"#\"\|href=\"#footer\"\|Условия использования\|Политика конфиденциальности" "${FRONTEND_MAIN}"; then
  echo "empty or fake public links must not remain" >&2
  exit 1
fi

grep -q "Public Website V6: reference PNGs are not page assets" "${CSS_FILE}" || { echo "V6 CSS missing" >&2; exit 1; }
grep -Eq "position:[[:space:]]*(fixed|sticky)[[:space:]]*!important" "${CSS_FILE}" || { echo "fixed/sticky header CSS missing" >&2; exit 1; }
grep -Eq "z-index:[[:space:]]*9999[[:space:]]*!important" "${CSS_FILE}" || { echo "header z-index missing" >&2; exit 1; }
grep -Eq "workflowCard-6|workflowStepNav" "${CSS_FILE}" || { echo "six step workflow CSS missing" >&2; exit 1; }
grep -q "connectionCard" "${CSS_FILE}" || { echo "connection card CSS missing" >&2; exit 1; }
grep -q "stlMarketingViewer" "${CSS_FILE}" || { echo "STL viewer CSS missing" >&2; exit 1; }
grep -q "demoWorkflowSection" "${CSS_FILE}" || { echo "workflow feature CSS missing" >&2; exit 1; }
grep -q "demoCompareSection" "${CSS_FILE}" || { echo "compare CSS missing" >&2; exit 1; }
grep -q "modalArtScene" "${CSS_FILE}" || { echo "component modal CSS missing" >&2; exit 1; }
grep -q "premiumComparePanel" "${CSS_FILE}" || { echo "premium comparison CSS missing" >&2; exit 1; }
grep -q "@media (max-width:720px)" "${CSS_FILE}" || { echo "mobile CSS missing" >&2; exit 1; }
grep -q "IntersectionObserver" "${FRONTEND_MAIN}" || { echo "IntersectionObserver reveal missing" >&2; exit 1; }

if grep -R "Geely\|geely\|990 ₽\|vk.com/im?sel=3dmodeliron" "${PROJECT_DIR}/frontend/src" "${PROJECT_DIR}/frontend/public" >/tmp/stl_public_forbidden.txt; then
  cat /tmp/stl_public_forbidden.txt >&2
  exit 1
fi

echo "Public pixel-perfect design contract passed."
