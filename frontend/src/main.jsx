import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Button, ConfigProvider, Panel, PanelHeader, Progress, View } from "@vkontakte/vkui";
import "@vkontakte/vkui/dist/vkui.css";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import "./styles.css";
import "./studio/studio.css";
import "./styles/tokens.css";
import "./design/tokens/color-tokens.css";
import "./design/tokens/typography.css";
import "./styles/reset.css";
import "./styles/shared.css";
import "./landing/landing.css";
import "./admin/admin.css";
import { StudioHeader, StudioSidebar, StudioEmptyState, StudioWorkflowBar } from "./studio/StudioComponents.jsx";
import {
  Badge as UiBadge,
  Button as UiButton,
  HeroCard as UiHeroCard,
  Panel as UiPanel,
  StatCard as UiStatCard,
} from "./ui/index.js";

const HISTORY_STORAGE_KEY = "stl-master-job-history";
const HISTORY_LIMIT = 10;
const ACCESS_CODE_STORAGE_KEY = "stl-master-access-code";
const PREMIUM_APPLICATION_STORAGE_KEY = "stl-master-premium-application-id";
const PREMIUM_REQUEST_NUMBER_STORAGE_KEY = "stl-master-premium-request-number";
const PREMIUM_CLIENT_STORAGE_KEY = "stl-master-premium-client-id";
const STL_MASTER_COMMUNITY_URL = "https://vk.ru/pechatdlyadoma";
const STL_MASTER_SUPPORT_URL = "https://vk.ru/3dmodeliron";
const STL_MASTER_TELEGRAM_URL = "https://t.me/chat_pechatdlyadoma";
const STL_MASTER_PIKABU_URL = "https://pikabu.ru/@PechatDlyaDoma";
const currentYear = new Date().getFullYear();
const mainNavigation = [
  { id: "features", label: "Возможности" },
  { id: "connectors", label: "Соединения" },
  { id: "compare", label: "До / После" },
  { id: "premium", label: "Тарифы" },
  { id: "faq", label: "FAQ" },
];
const footerNavigation = [
  {
    title: "Продукт",
    links: [
      { label: "Возможности", href: "#features" },
      { label: "Соединения", href: "#connectors" },
      { label: "До / После", href: "#compare" },
      { label: "Тарифы", href: "#premium" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    title: "Инструменты",
    links: [
      { label: "Проверка STL", href: "#features" },
      { label: "Ремонт модели", href: "#features" },
      { label: "Разрез модели", href: "#connectors" },
      { label: "Подготовка соединений", href: "#connectors" },
      { label: "Ориентация", href: "#features" },
      { label: "Экспорт результатов", href: "#features" },
    ],
  },
];
const socialLinks = [
  { label: "VK", href: STL_MASTER_COMMUNITY_URL, ariaLabel: "STL Master во ВКонтакте, откроется в новой вкладке", icon: "vk" },
  { label: "Telegram", href: STL_MASTER_TELEGRAM_URL, ariaLabel: "Чат STL Master в Telegram, откроется в новой вкладке", icon: "telegram" },
  { label: "Pikabu", href: STL_MASTER_PIKABU_URL, ariaLabel: "Канал STL Master на Pikabu, откроется в новой вкладке", icon: "pikabu" },
];
const DEFAULT_FEATURE_FLAGS = {
  beta_mode: true,
  beta_upload_limit_mb: 100,
  active_upload_limit_mb: 100,
  absolute_upload_limit_mb: 500,
  surface_recovery: false,
  local_smoothing: true,
  split: true,
  fit_to_bed_split: true,
  orientation: true,
  auto_orientation: true,
  compare_view: true,
  remove_ai_artifacts: true,
  print_repair: true,
  reduce_polygons: true,
  fix_symmetry: false,
};

const processingOperations = [
  {
    id: "analyze",
    title: "Анализ модели",
    description: "Размер, тип файла, количество треугольников и габариты.",
    available: true,
  },
  {
    id: "print_check",
    title: "Проверка к печати",
    description: "Проверка размеров под стол 220x220x250 мм.",
    available: true,
  },
  {
    id: "model_improvement",
    title: "Улучшить модель",
    description: "Сглаживает поверхность, исправляет нормали и убирает мелкие артефакты.",
    available: true,
  },
  {
    id: "remove_ai_artifacts",
    title: "Удалить AI-артефакты",
    description: "Удаляет мусорные фрагменты, наросты и лишние куски после AI-генерации.",
    available: true,
  },
  {
    id: "surface_recovery",
    title: "Восстановить поверхность",
    description: "Локально сглаживает рябь, волнистость, бугры и неестественные пики.",
    available: true,
  },
  {
    id: "reduce_polygons",
    title: "Уменьшить полигоны",
    description: "Сделать файл легче для просмотра и передачи.",
    available: true,
  },
  {
    id: "split_model",
    title: "Разрезать модель",
    description: "Разделить модель на несколько частей.",
    available: true,
  },
  {
    id: "fix_symmetry",
    title: "Исправить симметрию",
    description: "Сравнивает стороны модели и восстанавливает симметрию.",
    available: true,
  },
  {
    id: "apply_orientation",
    title: "Применить ориентацию",
    description: "Сохранить текущий поворот модели и поставить её на стол.",
    available: true,
  },
  {
    id: "auto_orientation",
    title: "Подобрать ориентацию для печати",
    description: "Автоматически выбрать положение модели для печати.",
    available: true,
  },
  {
    id: "prepare_package",
    title: "Подготовить пакет",
    description: "Собрать ZIP с моделями и понятными отчётами.",
    available: true,
  },
];

const operationTitles = {
  ...Object.fromEntries(processingOperations.map((operation) => [operation.id, operation.title])),
};

function expandOperationsForUpload(operations) {
  return [...new Set(operations)];
}

function getProcessedPreviewUrl(result) {
  return (result && result.final_download_url) || (result && result.after_download_url) || (result && result.model_improvement && result.model_improvement.after_download_url) || null;
}

function getChangeMapUrl(result) {
  return result?.change_map?.available && result.change_map.download_url ? result.change_map.download_url : null;
}

function getArtifactMapUrl(result) {
  return result?.artifact_map?.available && result.artifact_map.download_url ? result.artifact_map.download_url : null;
}

function createDemoStl({ cleaned = false } = {}) {
  const spikeHeight = cleaned ? 1 : 2.4;
  const triangles = [
    [[-10, 0, -10], [10, 0, -10], [10, 0, 10]], [[-10, 0, -10], [10, 0, 10], [-10, 0, 10]],
    [[-10, 20, -10], [10, 20, 10], [10, 20, -10]], [[-10, 20, -10], [-10, 20, 10], [10, 20, 10]],
    [[-10, 0, -10], [-10, 20, -10], [10, 20, -10]], [[-10, 0, -10], [10, 20, -10], [10, 0, -10]],
    [[10, 0, -10], [10, 20, -10], [10, 20, 10]], [[10, 0, -10], [10, 20, 10], [10, 0, 10]],
    [[10, 0, 10], [10, 20, 10], [-10, 20, 10]], [[10, 0, 10], [-10, 20, 10], [-10, 0, 10]],
    [[-10, 0, 10], [-10, 20, 10], [-10, 20, -10]], [[-10, 0, 10], [-10, 20, -10], [-10, 0, -10]],
    [[-2, 20, -2], [2, 20, -2], [0, 20 + spikeHeight, 0]],
    [[2, 20, -2], [2, 20, 2], [0, 20 + spikeHeight, 0]],
    [[2, 20, 2], [-2, 20, 2], [0, 20 + spikeHeight, 0]],
    [[-2, 20, 2], [-2, 20, -2], [0, 20 + spikeHeight, 0]],
  ];
  const body = triangles.map((triangle) => (
    `  facet normal 0 0 0\n    outer loop\n${triangle.map((point) => `      vertex ${point[0]} ${point[1]} ${point[2]}`).join("\n")}\n    endloop\n  endfacet`
  )).join("\n");
  const content = `solid stl_master_demo\n${body}\nendsolid stl_master_demo\n`;
  return new File([content], cleaned ? "demo_final.stl" : "demo_original.stl", { type: "model/stl" });
}

function demoJobStatus() {
  return {
    job_id: "demo",
    status: "completed",
    progress: 100,
    operations: ["analyze", "print_check", "remove_ai_artifacts"],
    result: {
      model_qa: {
        health_score: 73,
        status: "needs_repair",
        artifact_quality: {
          suspicious_regions: 12,
          spikes_detected: 4,
          elongated_faces: 9,
          artifact_penalty: 18,
        },
      },
      ai_cleanup: {
        success: true,
        health_score_before: 73,
        health_score_after: 88,
        suspicious_regions_before: 12,
        suspicious_regions_after: 3,
        removed_components: 6,
        output_file: "demo_final.stl",
      },
      final_model: "demo_final.stl",
      final_download_url: null,
      generated_files: [],
      processing_history: [
        { step: 1, operation: "original", title: "Исходная модель", file: "demo_original.stl", visible_result: { created: true } },
        { step: 2, operation: "remove_ai_artifacts", title: "Очистка AI-артефактов", file: "demo_final.stl", visible_result: { created: true } },
      ],
      change_map: { available: false },
      artifact_map: { available: false },
    },
  };
}

const dragonSkullPoster = "/assets/marketing/dragon_skull_cutout.png";

const publicWorkflowSteps = [
  { number: "1", title: "Загрузите STL", text: <>Просто перетащите<br />файл в окно редактора</>, icon: "upload" },
  { number: "2", title: "Проверьте модель", text: <>Авто-анализ на ошибки<br />и проблемные зоны</>, icon: "inspect" },
  { number: "3", title: "Исправьте и оптимизируйте", text: <>AI-исправление, очистка сетки,<br />снижение полигонов</>, icon: "magic" },
  { number: "4", title: "Разрежьте и соедините", text: <>Разделите модель и добавьте<br />соединения для печати</>, icon: "blocks" },
  { number: "5", title: "Проверьте печать", text: <>Проверка на толщину,<br />нависы и печатаемость</>, icon: "shieldCheck" },
  { number: "6", title: "Экспортируйте", text: <>Сохраните готовую модель<br />или отправьте в печать</>, icon: "export" },
];

const connectionModes = [
  {
    id: "simple",
    number: "01",
    title: "Обычный разрез",
    description: "Ровное разделение модели без дополнительных соединительных элементов.",
    image: "/images/connections/stlmaster_render_01_simple_cut.png?v=20260719-clean2",
    alt: "Обычный разрез STL-модели",
    meta: "Чистая плоскость",
  },
  {
    id: "glue",
    number: "02",
    title: "Под склейку",
    description: "Подготовленные поверхности для точного совмещения и прочной фиксации деталей.",
    image: "/images/connections/stlmaster_render_02_glue_surface.png?v=20260719-clean2",
    alt: "Поверхности STL-модели под склейку",
    meta: "Контактные поверхности",
  },
  {
    id: "pins",
    number: "03",
    title: "Штифты",
    description: "Цилиндрические направляющие для точного позиционирования частей при сборке.",
    image: "/images/connections/stlmaster_render_03_alignment_pins.png?v=20260719-clean2",
    alt: "Штифтовое соединение частей STL-модели",
    meta: "Точная стыковка",
  },
  {
    id: "magnets",
    number: "04",
    title: "Магниты",
    description: "Посадочные места под круглые магниты для удобной сборки и разборки модели.",
    image: "/images/connections/stlmaster_render_04_magnetic_connectors.png?v=20260719-clean2",
    alt: "Посадочные места под магниты в STL-модели",
    meta: "5×2 мм · 6×2 мм · 8×3 мм · 10×3 мм",
  },
  {
    id: "lock",
    number: "05",
    title: "Профильный замок",
    description: "Фигурное соединение для прочного и предсказуемого совмещения половин модели.",
    image: "/images/connections/stlmaster_render_05_profile_lock.png?v=20260719-clean2",
    alt: "Профильный замок между частями STL-модели",
    meta: "Шип-паз · Ласточкин хвост · Волновой профиль",
  },
  {
    id: "slots",
    number: "06",
    title: "Пазы и направляющие",
    description: "Продольные направляющие для точного позиционирования частей перед фиксацией.",
    image: "/images/connections/stlmaster_render_06_slots_guides.png?v=20260719-clean2",
    alt: "Пазы и направляющие между частями STL-модели",
    meta: "Линейное позиционирование",
  },
];

const connectionParameters = [
  { label: "Размер соединителя", value: "3 / 4 / 6 мм" },
  { label: "Количество", value: "2 / 3 / 4" },
  { label: "Зазор", value: "0,15 / 0,25 / 0,40 мм" },
  { label: "Глубина", value: "2–30 мм" },
  { label: "Толщина стенки", value: "0,4–5 мм" },
];

const featureCategories = [
  "Проверка и ремонт",
  "Очистка и оптимизация",
  "Разрез и сборка",
  "Подготовка результата",
];

const productFeatures = [
  {
    id: "geometry-check",
    category: "Проверка и ремонт",
    status: "Стабильно",
    title: "Проверка геометрии",
    description: "Находит открытые края, non-manifold участки, ошибки нормалей, дублирующиеся элементы и другие проблемы STL-сетки.",
    technical: ["Open edges", "Non-manifold", "Normals", "Duplicates"],
    visual: "diagnostics",
    size: "large",
  },
  {
    id: "auto-repair",
    category: "Проверка и ремонт",
    status: "BETA",
    title: "Автоматический ремонт STL",
    description: "Исправляет основные дефекты сетки и формирует обновлённую модель с отчётом о выполненных изменениях.",
    technical: ["Holes", "Normals", "Manifold", "Repair report"],
    visual: "repair",
    size: "large",
  },
  {
    id: "ai-cleanup",
    category: "Очистка и оптимизация",
    status: "BETA",
    title: "Очистка AI-моделей",
    description: "Находит подозрительные выступы, вытянутые полигоны, мелкие островки и локальные дефекты моделей, созданных генераторами.",
    technical: ["Spikes", "Tiny islands", "Artifacts", "Change map"],
    visual: "cleanup",
    note: "Выборочное сглаживание области: радиус и сила обработки.",
  },
  {
    id: "reduce-weight",
    category: "Очистка и оптимизация",
    status: "Зависит от конфигурации",
    title: "Уменьшение веса модели",
    description: "Сокращает количество полигонов на 25%, 50% или 75%, уменьшая размер модели и сохраняя её узнаваемую форму.",
    technical: ["25%", "50%", "75%"],
    visual: "reduce",
  },
  {
    id: "split-model",
    category: "Разрез и сборка",
    status: "BETA",
    title: "Разрез модели на части",
    description: "Разделяет STL по осям X, Y или Z на 2–4 части с настройкой положения плоскости разреза.",
    technical: ["X / Y / Z", "2–4 части", "Offset"],
    visual: "split",
    size: "wide",
  },
  {
    id: "assembly-connectors",
    category: "Разрез и сборка",
    status: "BETA",
    title: "Соединения для сборки",
    description: "Подготавливает разрез под склейку, штифты, магниты или базовый профильный замок.",
    technical: ["Glue", "Pins", "Magnets", "Tongue & Groove"],
    visual: "connectors",
    size: "wide",
  },
  {
    id: "print-orientation",
    category: "Подготовка результата",
    status: "Стабильно",
    title: "Ориентация под печать",
    description: "Анализирует модель и подбирает более подходящее положение на печатном столе. Также доступны ручные повороты по осям.",
    technical: ["Auto orientation", "Rotate X/Y/Z", "Place on table"],
    visual: "orientation",
  },
  {
    id: "reports-export",
    category: "Подготовка результата",
    status: "Стабильно",
    title: "До / после и отчёты",
    description: "Показывает обработанную модель, карту изменений и предоставляет STL, ZIP и технические отчёты по результатам обработки.",
    technical: ["STL", "ZIP", "JSON", "TXT"],
    visual: "reports",
  },
];

const featureWorkflowSteps = [
  { icon: "upload", title: "Загрузка" },
  { icon: "analyze", title: "Анализ" },
  { icon: "repair", title: "Обработка" },
  { icon: "shield", title: "Проверка" },
  { icon: "export", title: "Экспорт" },
];

const pricingAccessLevels = {
  free: {
    title: "Бесплатно",
    uploadLimitMb: 100,
    activeJobs: 1,
    queuedJobs: 2,
    uploadsPerHour: 5,
    priority: "Стандартный",
  },
  premium: {
    title: "Premium",
    uploadLimitMb: 300,
    activeJobs: 2,
    queuedJobs: 10,
    uploadsPerHour: 50,
    priority: "Повышенный",
  },
  earlyAccess: {
    title: "Early Access",
    uploadLimitMb: 100,
    activeJobs: 1,
    queuedJobs: 3,
    uploadsPerHour: 15,
    priority: "Выше бесплатного",
  },
};

const pricingPlan = {
  title: "STL Master Premium",
  subtitle: "Для регулярной работы с STL-моделями",
  badge: "Подключение через заявку",
  priceLabel: "299 ₽ / месяц",
  priceNote: "2 999 ₽ в год (-17%). Premium активируется после заявки и подтверждения.",
  cta: "Подключить Premium",
  footnote: "Заявку проверяет администратор и выдаёт access-code для подключения Premium.",
  benefits: [
    "Файлы STL до 300 МБ",
    "До 2 активных задач одновременно",
    "До 10 задач в очереди",
    "До 50 загрузок в час",
    "Повышенный приоритет обработки",
    "STL, ZIP, JSON и TXT в пакете результата",
  ],
};

function buildPricingComparison(featureFlags = DEFAULT_FEATURE_FLAGS) {
  const freeUploadMb = Number(featureFlags.active_upload_limit_mb || featureFlags.beta_upload_limit_mb || pricingAccessLevels.free.uploadLimitMb);
  return [
    {
      feature: "Размер STL-файла",
      free: `до ${freeUploadMb} МБ`,
      premium: `до ${pricingAccessLevels.premium.uploadLimitMb} МБ`,
      accent: true,
    },
    {
      feature: "Активные задачи",
      free: `${pricingAccessLevels.free.activeJobs} задача`,
      premium: `${pricingAccessLevels.premium.activeJobs} задачи`,
    },
    {
      feature: "Очередь пользователя",
      free: `до ${pricingAccessLevels.free.queuedJobs} задач`,
      premium: `до ${pricingAccessLevels.premium.queuedJobs} задач`,
    },
    {
      feature: "Загрузки в час",
      free: `${pricingAccessLevels.free.uploadsPerHour}`,
      premium: `${pricingAccessLevels.premium.uploadsPerHour}`,
    },
    {
      feature: "Приоритет обработки",
      free: pricingAccessLevels.free.priority,
      premium: pricingAccessLevels.premium.priority,
      accent: true,
    },
    {
      feature: "Редактор и операции STL",
      free: "Тот же редактор",
      premium: "Тот же редактор",
    },
    {
      feature: "Пакет результата",
      free: "STL / ZIP / JSON / TXT",
      premium: "STL / ZIP / JSON / TXT",
    },
    {
      feature: "Подключение",
      free: "Без access-code",
      premium: "Заявка и одобрение",
    },
  ];
}

const pricingTrustItems = [
  ["Работает в браузере", "Ничего не нужно устанавливать для запуска редактора."],
  ["Исходный STL сохраняется", "Оригинальная модель остаётся в пакете результата."],
  ["Технические отчёты", "ZIP может включать JSON, TXT, manifest и карты изменений."],
  ["Условия перед активацией", "Premium подключается после заявки и подтверждения."],
];

const faqItems = [
  {
    id: "supported-files",
    category: "Файлы и результаты",
    question: "Какие файлы поддерживает STL Master?",
    answer: "Сейчас редактор принимает STL-файлы. Результаты обработки могут включать STL-модели, ZIP-пакет и технические отчёты в форматах JSON и TXT.",
  },
  {
    id: "browser-work",
    category: "Начало работы",
    question: "Нужно ли устанавливать программу?",
    answer: "Нет. STL Master работает в браузере. Загрузите STL, выберите операции и дождитесь завершения обработки.",
  },
  {
    id: "mesh-diagnostics",
    category: "Обработка",
    question: "Что STL Master проверяет в модели?",
    answer: "Редактор анализирует замкнутость сетки, открытые и non-manifold рёбра, нормали, дублирующиеся и вырожденные элементы, мелкие островки, подозрительные артефакты и соответствие модели заданному печатному столу.",
  },
  {
    id: "repair-beta",
    category: "Обработка",
    question: "Может ли STL Master исправить повреждённую модель?",
    answer: "STL Master умеет исправлять основные дефекты сетки и формировать обновлённую версию модели с отчётом. Ремонт находится в beta, поэтому итог рекомендуется проверить в слайсере.",
  },
  {
    id: "reduce-polygons",
    category: "Обработка",
    question: "Можно ли уменьшить количество полигонов?",
    answer: "Да. Доступны режимы уменьшения количества полигонов на 25%, 50% и 75%. Доступность операции может зависеть от конфигурации обработчика.",
  },
  {
    id: "split-model",
    category: "Обработка",
    question: "Можно ли разрезать модель на части?",
    answer: "Да. Модель можно разделить по осям X, Y или Z на 2–4 части и настроить положение плоскости разреза.",
  },
  {
    id: "connectors",
    category: "Обработка",
    question: "Какие соединения поддерживаются?",
    answer: "Доступны подготовка под склейку, штифты, посадочные места под магниты и базовый профильный замок. Некоторые режимы находятся в beta и требуют проверки перед печатью.",
  },
  {
    id: "source-model",
    category: "Файлы и результаты",
    question: "Сохраняется ли исходная модель?",
    answer: "Исходный STL включается в историю и результаты обработки в соответствии с текущим процессом задачи. Дополнительно могут быть доступны промежуточные модели и отчёты.",
  },
  {
    id: "result-package",
    category: "Файлы и результаты",
    question: "Что я получу после обработки?",
    answer: "В зависимости от выбранных операций результат может содержать исправленную STL-модель, части разрезанной модели, ZIP-пакет, анализ, отчёт проверки печати и JSON-отчёты по выполненным операциям.",
  },
  {
    id: "print-guarantee",
    category: "Обработка",
    question: "Гарантирует ли сервис успешную печать?",
    answer: "Нет. STL Master помогает обнаружить и исправить основные проблемы, но результат рекомендуется дополнительно проверить в слайсере с учётом принтера, материала и настроек печати.",
  },
  {
    id: "premium-difference",
    category: "Тарифы и доступ",
    question: "Чем бесплатный режим отличается от Premium?",
    answer: "Бесплатный режим использует лимит STL до 100 МБ, 1 активную задачу, до 2 задач в очереди, 5 загрузок в час и стандартный приоритет. Premium повышает лимиты до 300 МБ, 2 активных задач, 10 задач в очереди, 50 загрузок в час и получает повышенный приоритет обработки. Подключение Premium выполняется по заявке.",
  },
  {
    id: "support",
    category: "Поддержка",
    question: "Как связаться с поддержкой?",
    answer: "Напишите в официальное сообщество STL Master во ВКонтакте или в Telegram-чат. Приложите описание проблемы, скриншот и, если возможно, название операции, на которой возникла ошибка.",
  },
];

const faqCategories = ["Начало работы", "Обработка", "Файлы и результаты", "Тарифы и доступ", "Поддержка"];

function localSmoothingImpactLabel({ selectedVertices = 0, selectedPercent = 0, changedVertices = 0, strength = "balanced" } = {}) {
  const vertices = Number(changedVertices || selectedVertices || 0);
  const percent = Number(selectedPercent || 0);
  const strengthWeight = strength === "strong" ? 2 : strength === "balanced" ? 1 : 0;
  if (vertices >= 1200 || percent >= 2 || strengthWeight === 2) return "Сильное";
  if (vertices >= 250 || percent >= 0.4 || strengthWeight === 1) return "Среднее";
  return "Минимальное";
}

function buildWhatChangedItems(result) {
  if (!result) return [];
  const items = [];
  const cleanup = result.ai_cleanup || result.remove_ai_artifacts;
  const localSmoothing = result.local_smoothing;
  const reduction = result.reduce_polygons;
  const orientation = result.apply_orientation;
  const split = result.split_model;

  if (cleanup) {
    const found = cleanup.suspicious_regions ?? result.model_qa?.artifact_quality?.suspicious_regions;
    const fixed = cleanup.removed_components ?? cleanup.changed_vertices ?? cleanup.vertices_modified;
    const output = cleanup.output_file || result.final_model;
    items.push({
      title: "Удаление AI-артефактов",
      details: [
        `Найдено подозрительных участков: ${formatMetric(found)}`,
        `Исправлено или удалено: ${formatMetric(fixed || 0)}`,
        `Итоговый файл: ${output || "не создан"}`,
      ],
    });
  }

  if (localSmoothing) {
    items.push({
      title: "Выборочная правка",
      details: [
        `Выбрано областей: ${formatMetric(localSmoothing.selected_regions)}`,
        `Изменено вершин: ${formatMetric(localSmoothing.changed_vertices)}`,
        `Сила обработки: ${localSmoothing.strength || "balanced"}`,
      ],
    });
  }

  if (reduction) {
    items.push({
      title: "Уменьшение полигонов",
      details: [
        `Было полигонов: ${formatMetric(reduction.original_faces)}`,
        `Стало полигонов: ${formatMetric(reduction.reduced_faces)}`,
        `Уменьшение: ${formatMetric(reduction.reduction_percent, "%")}`,
      ],
    });
  }

  if (orientation) {
    const rotation = orientation.rotation || {};
    items.push({
      title: "Ориентация",
      details: [
        `Сохранён поворот: X=${formatMetric(rotation.x, "°")}, Y=${formatMetric(rotation.y, "°")}, Z=${formatMetric(rotation.z, "°")}`,
        `Смещение по столу: X=${formatMetric(orientation.translate_x_mm ?? orientation.translation?.x, " мм")}, Z=${formatMetric(orientation.translate_z_mm ?? orientation.translation?.z, " мм")}`,
        `Модель поставлена на стол: ${orientation.translated_to_floor ? "да" : "нет"}`,
      ],
    });
  }

  if (split) {
    const partCount = split.output_files?.length || split.split_parts || 0;
    items.push({
      title: "Разрезание модели",
      details: [
        `Создано частей: ${formatMetric(partCount)}`,
        `Ось разреза: ${(split.axis_used || split.split_axis || "—").toString().toUpperCase()}`,
        `Смещение плоскости: ${formatMetric(split.split_plane_offset_mm || 0, " мм")}`,
        `Соединение: ${splitModeTitles[split.split_mode] || split.split_mode || "без соединителей"}`,
      ],
    });
  }

  return items;
}

const splitPresetDefaults = {
  split: { splitMode: "simple", lockProfile: "tongue_groove" },
  split_pins: { splitMode: "pins", lockProfile: "tongue_groove" },
  split_tongue: { splitMode: "lock", lockProfile: "tongue_groove" },
  split_dovetail: { splitMode: "lock", lockProfile: "dovetail" },
  split_puzzle: { splitMode: "slots", lockProfile: "wave" },
};

const splitPresetIds = new Set(Object.keys(splitPresetDefaults));

function isSplitPreset(modeId) {
  return splitPresetIds.has(modeId);
}

const operationPresets = [
  {
    id: "check",
    title: "Проверить модель",
    description: "Быстрая проверка размеров, треугольников и готовности к печати.",
    result: "Понятный отчёт о состоянии STL",
    icon: "🔎",
    status: "Рекомендуется",
    operations: ["analyze", "print_check", "prepare_package"],
  },
  {
    id: "improve",
    title: "Улучшить модель",
    description: "Сгладить AI-шум, исправить нормали и убрать мелкие артефакты.",
    result: "Исправляет сетку и нормали",
    icon: "✨",
    status: "Pro",
    featureKey: "print_repair",
    operations: ["analyze", "print_check", "model_improvement", "prepare_package"],
  },
  {
    id: "remove_artifacts",
    title: "Удалить AI-артефакты",
    description: "Убирает лишние островки, шипы, наросты и мусор, который часто появляется после генерации модели нейросетями.",
    result: "Убирает мусорные фрагменты",
    icon: "🧹",
    status: "Рекомендуется",
    featureKey: "remove_ai_artifacts",
    operations: ["analyze", "print_check", "remove_ai_artifacts", "prepare_package"],
  },
  {
    id: "surface",
    title: "Восстановить поверхность",
    description: "Помогает убрать волны, бугры и мелкую рябь на поверхности. Не предназначено для удаления отдельных деталей.",
    result: "Сглаживает шум и рябь",
    icon: "🧼",
    status: "В разработке",
    featureKey: "surface_recovery",
    operations: ["analyze", "print_check", "surface_recovery", "prepare_package"],
  },
  {
    id: "local",
    title: "Выборочная правка",
    description: "Выделите кистью проблемную область и сгладьте только выбранный участок.",
    result: "Локально сглаживает выбранную область",
    icon: "🎯",
    status: "Pro",
    featureKey: "local_smoothing",
    operations: ["analyze", "print_check", "local_smoothing", "prepare_package"],
  },
  {
    id: "reduce",
    title: "Уменьшить вес",
    description: "Сделать STL легче, сохранив рабочую подготовку сетки.",
    result: "Уменьшает количество полигонов",
    icon: "🪶",
    status: "Pro",
    featureKey: "reduce_polygons",
    operations: ["analyze", "print_check", "model_improvement", "reduce_polygons", "prepare_package"],
  },
  {
    id: "split",
    title: "Плоский разрез",
    description: "Обычный инженерный разрез без соединителей, пазов и штифтов. Только чистое разделение модели.",
    result: "Части без соединений",
    icon: "✂️",
    status: "Pro",
    featureKey: "split",
    operations: ["analyze", "print_check", "repair_mesh", "split_model", "prepare_package"],
  },
  {
    id: "split_pins",
    title: "Разрез со штифтами",
    description: "Разделяет модель и готовит цилиндрические направляющие: диаметр, глубина, количество, отступ и автопозиционирование.",
    result: "Части + штифты",
    icon: "●",
    status: "Pro",
    featureKey: "split",
    operations: ["analyze", "print_check", "repair_mesh", "split_model", "prepare_package"],
  },
  {
    id: "split_tongue",
    title: "Разрез паз-гребень",
    description: "Готовит стыковку по профилю паз-гребень для предсказуемого совмещения половин модели.",
    result: "Профильный паз-гребень",
    icon: "▰",
    status: "Скоро",
    disabled: true,
    disabledReason: "Геометрия профиля ещё не включена в производственную обработку.",
    featureKey: "split",
    operations: ["analyze", "print_check", "repair_mesh", "split_model", "prepare_package"],
  },
  {
    id: "split_dovetail",
    title: "Ласточкин хвост",
    description: "Подготавливает профиль с механической фиксацией на сдвиг. Генерация развивается поверх существующего пайплайна замков.",
    result: "Замок на сдвиг",
    icon: "▣",
    status: "Скоро",
    disabled: true,
    disabledReason: "Ласточкин хвост пока доступен только как предварительный просмотр, без готового экспорта.",
    featureKey: "split",
    operations: ["analyze", "print_check", "repair_mesh", "split_model", "prepare_package"],
  },
  {
    id: "split_puzzle",
    title: "Пазловое соединение",
    description: "Фундамент для волнового/пазлового соединения: предварительный просмотр и параметры соединителей уже отделены от обычного разреза.",
    result: "Пазловый профиль",
    icon: "⌁",
    status: "Скоро",
    disabled: true,
    disabledReason: "Пазловый профиль пока не создаётся как готовая геометрия для печати.",
    featureKey: "split",
    operations: ["analyze", "print_check", "repair_mesh", "split_model", "prepare_package"],
  },
  {
    id: "fit_to_bed",
    title: "Разрезать под стол",
    description: "Автоматически делит большую модель на части под выбранный размер стола.",
    result: "Части помещаются на стол принтера",
    icon: "🧩",
    status: "Pro",
    featureKey: "fit_to_bed_split",
    operations: ["analyze", "print_check", "fit_to_bed_split", "prepare_package"],
  },
  {
    id: "symmetry",
    title: "Исправить симметрию",
    description: "Сравнить стороны модели и зеркально восстановить выбранную ось.",
    result: "Выравнивает стороны модели",
    icon: "🪞",
    status: "В разработке",
    featureKey: "fix_symmetry",
    operations: ["analyze", "print_check", "fix_symmetry", "prepare_package"],
  },
  {
    id: "orientation",
    title: "Применить ориентацию",
    description: "Сохраняет текущий поворот и положение модели в итоговый STL.",
    result: "Сохраняет текущий поворот",
    icon: "📐",
    status: "Готово",
    featureKey: "orientation",
    operations: ["analyze", "print_check", "apply_orientation", "prepare_package"],
  },
  {
    id: "auto_orientation",
    title: "Подобрать ориентацию для печати",
    description: "Сервис проверит несколько положений модели и выберет вариант, который лучше стоит на столе и требует меньше поддержек.",
    result: "Выбирает удобное положение",
    icon: "🧭",
    status: "Pro",
    featureKey: "auto_orientation",
    operations: ["analyze", "print_check", "auto_orientation", "prepare_package"],
  },
];

function operationsForMode(modeId) {
  return operationPresets.find((preset) => preset.id === modeId)?.operations || operationPresets[0].operations;
}

function featureEnabled(flags, key) {
  if (!key) return true;
  return flags?.[key] !== false;
}

function visiblePresetsForFlags(flags) {
  return operationPresets.filter((preset) => featureEnabled(flags, preset.featureKey));
}

const improvementStrengthOptions = [
  { id: "light", title: "Аккуратно", description: "Минимально исправляет сетку и нормали." },
  { id: "balanced", title: "Баланс", description: "Сглаживает поверхность и убирает мелкие артефакты." },
  { id: "strong", title: "Сильно", description: "Заметнее сглаживает AI-шум, но может немного изменить форму." },
];

const artifactCleanupStrengthOptions = [
  { id: "light", title: "Аккуратно", description: "Удаляет только самые маленькие отдельные фрагменты." },
  { id: "balanced", title: "Баланс", description: "Убирает мусорные островки без резких изменений." },
  { id: "strong", title: "Сильно", description: "Удаляет больше мелких фрагментов, но требует проверки." },
];

const splitModeOptions = [
  { id: "simple", icon: "—", title: "Плоский разрез", description: "Одна секущая плоскость без соединителей." },
  { id: "pins", icon: "●", title: "Штифты", description: "Цилиндрические направляющие и ответные отверстия." },
  { id: "lock", icon: "▣", title: "Паз-гребень", description: "Профильная стыковка для точного совмещения." },
  { id: "slots", icon: "⌁", title: "Пазловое соединение", description: "Основа для направляющих и пазлового профиля." },
];

const connectorSizeOptions = [3, 4, 6];
const connectorClearanceOptions = [0.15, 0.25, 0.4];
const connectorCountOptions = [2, 3, 4];
const connectorDepthOptions = [4, 6, 10];
const connectorWallOptions = [0.8, 1.2, 1.6];
const magnetSizeOptions = [
  { id: "5x2", title: "5×2", diameter: 5, thickness: 2 },
  { id: "6x2", title: "6×2", diameter: 6, thickness: 2 },
  { id: "8x3", title: "8×3", diameter: 8, thickness: 3 },
  { id: "10x3", title: "10×3", diameter: 10, thickness: 3 },
];
const lockProfileOptions = [
  { id: "tongue_groove", title: "Паз-гребень" },
  { id: "dovetail", title: "Ласточкин хвост" },
  { id: "wave", title: "Пазловый профиль" },
];
const connectorPlacementOptions = [
  { id: "auto", title: "Авто", description: "STL Master сам расставляет соединители в рабочей зоне." },
  { id: "manual", title: "Ручная", description: "Архитектура для будущей корректировки позиций в viewer." },
];
const splitModeTitles = Object.fromEntries(splitModeOptions.map((mode) => [mode.id, mode.title]));
const bedSizeOptions = [
  { id: "180", title: "180×180×180", x: 180, y: 180, z: 180 },
  { id: "220", title: "220×220×250", x: 220, y: 250, z: 220 },
  { id: "256", title: "256×256×256", x: 256, y: 256, z: 256 },
  { id: "300", title: "300×300×300", x: 300, y: 300, z: 300 },
  { id: "custom", title: "Свой размер", x: 220, y: 250, z: 220 },
];
const bedConnectorOptions = [
  { id: "none", title: "Без соединителей" },
  { id: "pins", title: "Штифты" },
  { id: "slots", title: "Пазы" },
];
const orientationPriorityOptions = [
  { id: "supports", title: "Меньше поддержек", description: "Выбрать положение с меньшим риском нависаний." },
  { id: "speed", title: "Быстрее печать", description: "Снизить высоту модели на столе." },
  { id: "quality", title: "Лучше качество поверхности", description: "Уменьшить сильные нависания на заметных участках." },
];
const orientationPriorityTitles = Object.fromEntries(orientationPriorityOptions.map((item) => [item.id, item.title]));

function getApiBaseUrl() {
  const { hostname, origin, protocol } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1") {
    return `${protocol}//${hostname}:8000`;
  }
  if (hostname === "app.stlmaster.online" || hostname.endsWith(".stlmaster.online")) {
    return protocol === "http:" ? `https://${hostname}` : "";
  }
  return origin;
}

function getApiUrl(path) {
  return `${getApiBaseUrl()}${path}`;
}

async function fetchCurrentUser(apiBaseUrl, accessCode, signal) {
  const normalizedCode = String(accessCode || "").trim();
  const headers = normalizedCode ? { "X-Beta-Access-Code": normalizedCode } : undefined;
  const response = await fetch(`${apiBaseUrl}/api/v1/me`, {
    method: "GET",
    headers,
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw new Error("Не удалось получить статус пользователя");
  return response.json();
}

function formatDateRu(value, { month = "long" } = {}) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ru-RU", { day: "numeric", month, year: "numeric" });
}

function formatPremiumShortDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function premiumTimeLabel(currentUser) {
  if (!currentUser?.premium_active) {
    return currentUser?.premium_expires_at && Number(currentUser?.premium_days_left || 0) <= 0
      ? "Премиум истёк"
      : "Получить Премиум";
  }
  if (!currentUser.premium_expires_at) return "Без ограничения срока";
  const daysLeft = Number(currentUser.premium_days_left);
  if (Number.isFinite(daysLeft) && daysLeft > 1) return `Осталось ${daysLeft} дн.`;
  if (Number.isFinite(daysLeft) && daysLeft === 1) return "Остался 1 день";
  return "Осталось менее 1 дня";
}

function premiumUntilLabel(currentUser) {
  if (!currentUser?.premium_active) return "Премиум не активен";
  if (!currentUser.premium_expires_at) return "Премиум активен без срока";
  return `Премиум до ${formatPremiumShortDate(currentUser.premium_expires_at)}`;
}

function formatMetric(value, suffix = "") {
  if (value === null || value === undefined) return "—";
  return `${value}${suffix}`;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!value) return "—";
  if (value >= 1024 * 1024 * 1024) return `${(value / 1024 / 1024 / 1024).toFixed(2)} ГБ`;
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} МБ`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} КБ`;
  return `${value} Б`;
}

function formatDuration(seconds) {
  const value = Number(seconds || 0);
  if (!Number.isFinite(value) || value <= 0) return "—";
  if (value < 60) return `${Math.round(value)} сек`;
  return `${Math.ceil(value / 60)} мин`;
}

function queuePriorityLabel(priority) {
  const labels = {
    premium: "Премиум",
    early_access: "Ранний доступ",
    free: "Бесплатно",
  };
  return labels[priority] || labels.free;
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(status) {
  const labels = {
    queued: "Ожидание",
    processing: "Обработка",
    completed: "Готово",
    failed: "Ошибка",
    expired: "Устарела",
    error: "Ошибка",
    loading: "Загрузка",
  };
  return labels[status] || "Ожидание";
}

function statusMessage(status, fallback = "") {
  const messages = {
    queued: "Файл принят, задача ожидает начала обработки.",
    processing: "Модель обрабатывается. Можно оставить страницу открытой.",
    completed: "Результат готов. Можно скачать ZIP или отдельные файлы.",
    failed: "Не удалось обработать модель.",
    expired: "Задача устарела или удалена.",
    error: "Не удалось получить данные.",
  };
  return messages[status] || fallback || "Получаем статус...";
}

function fileTypeLabel(type) {
  const labels = {
    source: "исходник",
    model: "модель",
    model_part: "часть",
    report: "отчёт",
  };
  return labels[type] || "файл";
}

function displayGeneratedFile(file) {
  const aliases = {
    "repaired.stl": { label: "Модель после улучшения сетки", name: "STL после улучшения" },
    "ai_cleaned.stl": { label: "Улучшенная модель", name: "STL после обработки" },
    "cleaned_artifacts.stl": { label: "Модель без AI-артефактов", name: "STL после очистки" },
    "repair_report.json": { label: "Отчёт улучшения сетки", name: "Отчёт улучшения" },
    "ai_cleanup_report.json": { label: "Отчёт улучшения поверхности", name: "Отчёт улучшения" },
    "artifact_cleanup_report.json": { label: "Отчёт удаления AI-артефактов", name: "Отчёт очистки" },
  };
  return aliases[file.name] || { label: file.label || file.name, name: file.name };
}

function isRealJobHistoryId(jobId) {
  return typeof jobId === "string" && jobId.trim() && jobId !== "demo";
}

function readJobHistory() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(HISTORY_STORAGE_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    const history = parsed.filter(isRealJobHistoryId).slice(0, HISTORY_LIMIT);
    writeJobHistory(history);
    return history;
  } catch {
    return [];
  }
}

function writeJobHistory(jobIds) {
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(jobIds.filter(isRealJobHistoryId).slice(0, HISTORY_LIMIT)));
}

function addJobToHistory(jobId) {
  if (!isRealJobHistoryId(jobId)) return readJobHistory();
  const nextHistory = [jobId, ...readJobHistory().filter((item) => item !== jobId)].slice(0, HISTORY_LIMIT);
  writeJobHistory(nextHistory);
  return nextHistory;
}

function shortJobId(jobId) {
  if (!jobId) return "—";
  return `${jobId.slice(0, 8)}…${jobId.slice(-4)}`;
}

function qualityTone(score) {
  if (typeof score !== "number") {
    return { className: "qualityUnknown", label: "Состояние не оценено", icon: "○" };
  }
  if (score >= 90) return { className: "qualityReady", label: "Готово к печати", icon: "●" };
  if (score >= 75) return { className: "qualityGood", label: "Хорошее состояние", icon: "●" };
  return { className: "qualityNeedsWork", label: "Требует исправления", icon: "●" };
}

function GeneratedFilesBlock({ files = [] }) {
  const visibleFiles = files.filter(
    (file) => !["repaired.stl", "repair_report.json", "ai_cleaned.stl", "ai_cleanup_report.json", "artifact_cleanup_report.json"].includes(file.name)
  );
  if (!visibleFiles.length) return null;

  const groups = [
    {
      title: "Модели",
      types: ["source", "model"],
    },
    {
      title: "Части",
      types: ["model_part"],
    },
    {
      title: "Отчёты",
      types: ["report"],
    },
  ];

  const filesByGroup = groups
    .map((group) => ({
      ...group,
      files: visibleFiles.filter((file) => group.types.includes(file.type)),
    }))
    .filter((group) => group.files.length > 0);

  const knownTypes = new Set(groups.flatMap((group) => group.types));
  const otherFiles = visibleFiles.filter((file) => !knownTypes.has(file.type));
  if (otherFiles.length > 0) {
    filesByGroup.push({ title: "Другое", types: [], files: otherFiles });
  }

  return (
    <div className="generatedFilesPanel">
      <div className="analysisHeader">
        <p className="panelLabel">Состав результата</p>
        <h2>Файлы в ZIP</h2>
      </div>
      <div className="generatedFilesGroups">
        {filesByGroup.map((group) => (
          <section className="generatedFilesGroup" key={group.title}>
            <h3>{group.title}</h3>
            <div className="generatedFilesList">
              {group.files.map((file) => (
                <article className="generatedFileItem" key={file.name}>
                  <div>
                    <strong>{displayGeneratedFile(file).label}</strong>
                    <span>{displayGeneratedFile(file).name}</span>
                  </div>
                  <div className="generatedFileActions">
                    <em>{fileTypeLabel(file.type)}</em>
                    {file.download_url && (
                      <a href={`${getApiBaseUrl()}${file.download_url}`}>
                        Скачать
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function HistoryGeneratedFiles({ files = [] }) {
  if (!files.length) return null;
  const previewFiles = files.slice(0, 5);
  const hiddenCount = files.length - previewFiles.length;

  return (
    <div className="historyFiles" role="group" aria-label={`Файлы результата · ${files.length}`}>
      <strong>Файлы результата · {files.length}</strong>
      <div>
        {previewFiles.map((file) => (
          <span key={file.name}>{displayGeneratedFile(file).label}</span>
        ))}
        {hiddenCount > 0 && <span>+{hiddenCount}</span>}
      </div>
    </div>
  );
}

function JobHistory({ apiBaseUrl, currentJobId, onOpenJob }) {
  const [history, setHistory] = useState(() => readJobHistory());
  const [statuses, setStatuses] = useState({});

  const refreshHistory = async (jobIds = history) => {
    if (!jobIds.length) {
      setStatuses({});
      return;
    }

    const entries = await Promise.all(
      jobIds.map(async (historyJobId) => {
        try {
          const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${historyJobId}`);
          if (response.status === 404) {
            return [historyJobId, { status: "expired", message: "Задача устарела или удалена" }];
          }
          if (!response.ok) {
            return [historyJobId, { status: "error", message: "Не удалось получить статус" }];
          }
          const data = await response.json();
          return [historyJobId, data];
        } catch {
          return [historyJobId, { status: "error", message: "Сервис временно недоступен" }];
        }
      }),
    );
    setStatuses(Object.fromEntries(entries));
  };

  useEffect(() => {
    const storedHistory = readJobHistory();
    setHistory(storedHistory);
    refreshHistory(storedHistory);
  }, []);

  useEffect(() => {
    if (!currentJobId) return;
    const nextHistory = addJobToHistory(currentJobId);
    setHistory(nextHistory);
    refreshHistory(nextHistory);
  }, [currentJobId]);

  const removeFromHistory = (historyJobId) => {
    const nextHistory = history.filter((item) => item !== historyJobId);
    writeJobHistory(nextHistory);
    setHistory(nextHistory);
    setStatuses((current) => {
      const nextStatuses = { ...current };
      delete nextStatuses[historyJobId];
      return nextStatuses;
    });
  };

  if (!history.length) return null;

  return (
    <section className="historySection">
      <div className="sectionTitle">
        <h2>Последние обработки</h2>
      </div>
      <div className="historyList">
        {history.map((historyJobId) => {
          const status = statuses[historyJobId];
          const result = status?.result;
          const isCompleted = status?.status === "completed";
          const generatedFiles = result?.generated_files || [];
          return (
            <article className="historyCard" key={historyJobId}>
              <div className="historyCardTop">
                <div>
                  <span title={historyJobId}>№ {shortJobId(historyJobId)}</span>
                </div>
                <em className={`historyStatus ${status?.status || "loading"}`}>
                  {statusLabel(status?.status || "loading")}
                </em>
              </div>
              <p>{statusMessage(status?.status, status?.message)}</p>
              {status?.status === "expired" && (
                <p className="historyWarning">Задача устарела или удалена.</p>
              )}
              {isCompleted && result?.download_ready && result?.download_url && (
                <a className="historyDownload" href={`${apiBaseUrl}${result.download_url}`}>
                  Скачать всё ZIP
                </a>
              )}
              {isCompleted && <HistoryGeneratedFiles files={generatedFiles} />}
              <div className="historyActions">
                <button type="button" onClick={() => onOpenJob(historyJobId)}>
                  Открыть результат
                </button>
                <button type="button" onClick={() => removeFromHistory(historyJobId)}>
                  Удалить из истории
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function StlPreview({
  file,
  sourceFile,
  splitPreviewEnabled,
  splitOperationTitle,
  splitAxis,
  splitParts,
  splitMode,
  splitPlaneOffset,
  symmetryPreviewEnabled,
  symmetryAxis,
  compareMode,
  heatmapEnabled,
  heatmapData,
  heatmapError,
  artifactMapEnabled,
  artifactMapData,
  artifactMapError,
  localSelectionEnabled,
  localSelectionRadius,
  localSelectionStrength,
  localSelectionMode,
  localSelection,
  onLocalSelectionChange,
  onClearModel,
  onSelectFile,
  orientationTransform,
  onOrientationChange,
  uploading,
  progress,
  jobStatus,
}) {
  const mountRef = useRef(null);
  const rendererRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const frameRef = useRef(null);
  const modelRef = useRef(null);
  const splitOverlayRef = useRef(null);
  const symmetryOverlayRef = useRef(null);
  const localSelectionOverlayRef = useRef(null);
  const modelBoxRef = useRef(null);
  const modelSphereRef = useRef(null);
  const modelMetricsRef = useRef(null);
  const gridRef = useRef(null);
  const floorRef = useRef(null);
  const performanceRef = useRef({ lastTime: 0, frames: 0, fps: 0, frameTime: 0 });
  const localSelectionEnabledRef = useRef(false);
  const localSelectionRadiusRef = useRef(10);
  const localSelectionStrengthRef = useRef("balanced");
  const localSelectionModeRef = useRef("point");
  const onLocalSelectionChangeRef = useRef(null);
  const brushActiveRef = useRef(false);
  const lastBrushWorldPointRef = useRef(null);
  const [previewStatus, setPreviewStatus] = useState("STL-модель ещё не выбрана");
  const [previewState, setPreviewState] = useState("idle");
  const [viewerMetrics, setViewerMetrics] = useState(null);
  const [viewVersion, setViewVersion] = useState(0);

  const formatViewerNumber = (value) => {
    const number = Number(value || 0);
    if (!Number.isFinite(number) || number <= 0) return "0";
    if (number >= 1000000) return `${Math.round(number / 100000) / 10}M`;
    if (number >= 1000) return `${Math.round(number / 100) / 10}K`;
    return `${Math.round(number)}`;
  };

  const formatViewerSize = (value) => {
    const number = Number(value || 0);
    if (!Number.isFinite(number)) return "0";
    if (Math.abs(number) >= 100) return `${Math.round(number)}`;
    return `${Math.round(number * 10) / 10}`;
  };

  const jobPhase = String(jobStatus?.status || "").toLowerCase();
  const isViewerBusy = Boolean(uploading || ["queued", "pending", "processing", "running"].includes(jobPhase));
  const isViewerResult = Boolean(["completed", "done", "success"].includes(jobPhase));

  const disposeObject = (object) => {
    object.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((material) => material.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  };

  useEffect(() => {
    localSelectionEnabledRef.current = Boolean(localSelectionEnabled);
    localSelectionRadiusRef.current = Number(localSelectionRadius || 10);
    localSelectionStrengthRef.current = localSelectionStrength || "balanced";
    localSelectionModeRef.current = localSelectionMode || "point";
    onLocalSelectionChangeRef.current = onLocalSelectionChange;
  }, [localSelectionEnabled, localSelectionRadius, localSelectionStrength, localSelectionMode, onLocalSelectionChange]);

  const clearSplitOverlay = () => {
    if (splitOverlayRef.current && sceneRef.current) {
      sceneRef.current.remove(splitOverlayRef.current);
      disposeObject(splitOverlayRef.current);
      splitOverlayRef.current = null;
    }
  };

  const clearSymmetryOverlay = () => {
    if (symmetryOverlayRef.current && sceneRef.current) {
      sceneRef.current.remove(symmetryOverlayRef.current);
      disposeObject(symmetryOverlayRef.current);
      symmetryOverlayRef.current = null;
    }
  };

  const clearLocalSelectionOverlay = () => {
    if (localSelectionOverlayRef.current && sceneRef.current) {
      sceneRef.current.remove(localSelectionOverlayRef.current);
      disposeObject(localSelectionOverlayRef.current);
      localSelectionOverlayRef.current = null;
    }
  };

  const primaryPreviewMesh = () => {
    const model = modelRef.current;
    if (!model) return null;
    if (model.isMesh) return model;
    let mesh = null;
    model.traverse?.((child) => {
      if (!mesh && child.isMesh && child.geometry?.attributes?.position) mesh = child;
    });
    return mesh;
  };

  const resetLocalSelectionColors = () => {
    const mesh = primaryPreviewMesh();
    const geometry = mesh?.geometry;
    if (!mesh || !geometry) return;
    if (geometry.getAttribute("color")) {
      geometry.deleteAttribute("color");
    }
    if (Array.isArray(mesh.material)) {
      mesh.material.forEach((material) => {
        material.vertexColors = false;
        material.color?.set?.(0x8bd9ff);
        material.needsUpdate = true;
      });
    } else if (mesh.material) {
      mesh.material.vertexColors = false;
      mesh.material.color?.set?.(0x8bd9ff);
      mesh.material.needsUpdate = true;
    }
  };

  const computeLocalSelectionPreview = (regions) => {
    const mesh = primaryPreviewMesh();
    const geometry = mesh?.geometry;
    const position = geometry?.attributes?.position;
    if (!mesh || !geometry || !position || !Array.isArray(regions) || regions.length === 0) {
      return { selectedVertices: 0, selectedFaces: 0, selectedPercent: 0, selectedIndices: new Set(), selectedPoints: [] };
    }
    const offset = geometry.userData?.originalOffset || { x: 0, y: 0, z: 0 };
    const selectedIndices = new Set();
    const selectedPoints = [];
    for (let index = 0; index < position.count; index += 1) {
      const x = position.getX(index) + offset.x;
      const y = position.getY(index) + offset.y;
      const z = position.getZ(index) + offset.z;
      const isInside = regions.some((region) => {
        const center = region.center || [];
        const radius = Number(region.radius_mm || 0);
        const dx = x - Number(center[0] || 0);
        const dy = y - Number(center[1] || 0);
        const dz = z - Number(center[2] || 0);
        return dx * dx + dy * dy + dz * dz <= radius * radius;
      });
      if (isInside) {
        selectedIndices.add(index);
        if (selectedPoints.length < 5000) {
          selectedPoints.push(new THREE.Vector3(position.getX(index), position.getY(index), position.getZ(index)));
        }
      }
    }
    let selectedFaces = 0;
    const faceCount = Math.floor(position.count / 3);
    for (let faceIndex = 0; faceIndex < faceCount; faceIndex += 1) {
      if (
        selectedIndices.has(faceIndex * 3) ||
        selectedIndices.has(faceIndex * 3 + 1) ||
        selectedIndices.has(faceIndex * 3 + 2)
      ) {
        selectedFaces += 1;
      }
    }
    return {
      selectedVertices: selectedIndices.size,
      selectedFaces,
      selectedPercent: position.count ? Math.round((selectedIndices.size / position.count) * 1000) / 10 : 0,
      selectedIndices,
      selectedPoints,
    };
  };

  const applyLocalSelectionColors = (regions) => {
    const mesh = primaryPreviewMesh();
    const geometry = mesh?.geometry;
    const position = geometry?.attributes?.position;
    if (!mesh || !geometry || !position) return computeLocalSelectionPreview(regions);
    const preview = computeLocalSelectionPreview(regions);
    const base = new THREE.Color(0x79c7ff);
    const faceColor = new THREE.Color(0xff9f1c);
    const vertexColor = new THREE.Color(0xfff36a);
    const colors = new Float32Array(position.count * 3);
    for (let index = 0; index < position.count; index += 1) {
      colors[index * 3] = base.r;
      colors[index * 3 + 1] = base.g;
      colors[index * 3 + 2] = base.b;
    }
    const faceCount = Math.floor(position.count / 3);
    for (let faceIndex = 0; faceIndex < faceCount; faceIndex += 1) {
      const selectedFace = preview.selectedIndices.has(faceIndex * 3) || preview.selectedIndices.has(faceIndex * 3 + 1) || preview.selectedIndices.has(faceIndex * 3 + 2);
      if (!selectedFace) continue;
      for (let offset = 0; offset < 3; offset += 1) {
        const vertexIndex = faceIndex * 3 + offset;
        colors[vertexIndex * 3] = faceColor.r;
        colors[vertexIndex * 3 + 1] = faceColor.g;
        colors[vertexIndex * 3 + 2] = faceColor.b;
      }
    }
    preview.selectedIndices.forEach((vertexIndex) => {
      colors[vertexIndex * 3] = vertexColor.r;
      colors[vertexIndex * 3 + 1] = vertexColor.g;
      colors[vertexIndex * 3 + 2] = vertexColor.b;
    });
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geometry.attributes.color.needsUpdate = true;
    if (Array.isArray(mesh.material)) {
      mesh.material.forEach((material) => {
        material.vertexColors = true;
        material.needsUpdate = true;
      });
    } else if (mesh.material) {
      mesh.material.vertexColors = true;
      mesh.material.color?.set?.(0xffffff);
      mesh.material.needsUpdate = true;
    }
    return preview;
  };

  const estimateSelectedVertices = (regions) => {
    return computeLocalSelectionPreview(regions).selectedVertices;
  };

  const normalizeSelectionRegions = (selection) => {
    if (!selection) return [];
    if (selection.type === "spheres") return Array.isArray(selection.regions) ? selection.regions : [];
    if (selection.type === "sphere" && Array.isArray(selection.center)) {
      return [{ center: selection.center, radius_mm: selection.radius_mm || localSelectionRadiusRef.current }];
    }
    return [];
  };

  const originalPointToWorld = (region) => {
    const model = modelRef.current;
    if (!model || !region?.center) return null;
    const offset = model.geometry?.userData?.originalOffset || { x: 0, y: 0, z: 0 };
    return model.localToWorld(new THREE.Vector3(
      Number(region.center[0] || 0) - offset.x,
      Number(region.center[1] || 0) - offset.y,
      Number(region.center[2] || 0) - offset.z,
    ));
  };

  const drawLocalSelectionOverlay = (regions) => {
    clearLocalSelectionOverlay();
    if (!sceneRef.current || !Array.isArray(regions) || regions.length === 0) {
      resetLocalSelectionColors();
      return { selectedVertices: 0, selectedFaces: 0, selectedPercent: 0 };
    }
    const group = new THREE.Group();
    const preview = applyLocalSelectionColors(regions);
    if (preview.selectedPoints.length > 0) {
      const pointGeometry = new THREE.BufferGeometry().setFromPoints(preview.selectedPoints);
      const points = new THREE.Points(
        pointGeometry,
        new THREE.PointsMaterial({
          color: 0xfff36a,
          size: 0.85,
          transparent: true,
          opacity: 0.95,
          depthWrite: false,
        }),
      );
      points.renderOrder = 10;
      group.add(points);
    }
    regions.slice(-1).forEach((region) => {
      const center = originalPointToWorld(region);
      const radius = Number(region.radius_mm || localSelectionRadiusRef.current);
      if (!center || !radius) return;
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 32, 18),
        new THREE.MeshBasicMaterial({
          color: localSelectionModeRef.current === "brush" ? 0x60a5fa : 0xff9f1c,
          transparent: true,
          opacity: 0.1,
          depthWrite: false,
        }),
      );
      sphere.position.copy(center);
      sphere.renderOrder = 8;
      group.add(sphere);
      const ring = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.SphereGeometry(radius, 28, 10)),
        new THREE.LineBasicMaterial({ color: localSelectionModeRef.current === "brush" ? 0x8bd9ff : 0xffd166, transparent: true, opacity: 0.84, depthWrite: false }),
      );
      ring.position.copy(center);
      ring.renderOrder = 9;
      group.add(ring);
    });
    sceneRef.current.add(group);
    localSelectionOverlayRef.current = group;
    return preview;
  };

  const rebuildEngineeringGrid = (metrics) => {
    const scene = sceneRef.current;
    if (!scene || !metrics?.box) return;

    if (gridRef.current) {
      scene.remove(gridRef.current);
      disposeObject(gridRef.current);
      gridRef.current = null;
    }
    if (floorRef.current) {
      scene.remove(floorRef.current);
      disposeObject(floorRef.current);
      floorRef.current = null;
    }

    const gridSize = THREE.MathUtils.clamp(Math.ceil(Math.max(metrics.diagonal * 1.9, 80) / 10) * 10, 80, 2400);
    const divisions = THREE.MathUtils.clamp(Math.round(gridSize / 10), 16, 96);
    const floorY = Number.isFinite(metrics.box.min.y) ? metrics.box.min.y : 0;

    const grid = new THREE.GridHelper(gridSize, divisions, 0x35d7ff, 0x19354c);
    grid.position.y = floorY;
    grid.material.transparent = true;
    grid.material.opacity = 0.28;
    gridRef.current = grid;
    scene.add(grid);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(gridSize, gridSize),
      new THREE.MeshStandardMaterial({
        color: 0x050c16,
        metalness: 0.08,
        roughness: 0.92,
        transparent: true,
        opacity: 0.34,
        depthWrite: false,
      }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = floorY - Math.max(metrics.diagonal * 0.002, 0.02);
    floorRef.current = floor;
    scene.add(floor);
  };

  const updateModelBox = ({ refreshGrid = false } = {}) => {
    if (!modelRef.current) return null;
    const box = new THREE.Box3().setFromObject(modelRef.current);
    if (box.isEmpty()) return null;

    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const sphere = new THREE.Sphere();
    box.getBoundingSphere(sphere);
    const diagonal = Math.max(size.length(), 1);

    let vertices = 0;
    let triangles = 0;
    modelRef.current.traverse?.((child) => {
      const geometry = child.geometry;
      if (!geometry?.attributes?.position) return;
      vertices += geometry.attributes.position.count || 0;
      triangles += geometry.index?.count
        ? Math.floor(geometry.index.count / 3)
        : Math.floor((geometry.attributes.position.count || 0) / 3);
    });

    const metrics = {
      box,
      size,
      center,
      sphere,
      radius: Math.max(sphere.radius || diagonal / 2, 1),
      diagonal,
      vertices,
      triangles,
    };
    modelBoxRef.current = box;
    modelSphereRef.current = sphere;
    modelMetricsRef.current = metrics;
    setViewerMetrics((current) => ({
      ...current,
      width: size.x,
      height: size.y,
      depth: size.z,
      radius: metrics.radius,
      diagonal,
      vertices,
      triangles,
    }));
    if (refreshGrid) rebuildEngineeringGrid(metrics);
    return box;
  };

  const centerView = () => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    updateModelBox({ refreshGrid: true });
    const metrics = modelMetricsRef.current;
    if (!camera || !controls || !metrics) return;

    const target = metrics.center.clone();
    const radius = Math.max(metrics.radius, 1);
    const fov = THREE.MathUtils.degToRad(camera.fov);
    const aspect = Math.max(camera.aspect || 1, 0.1);
    const fitHeightDistance = radius / Math.sin(fov / 2);
    const fitWidthDistance = radius / Math.sin(Math.atan(Math.tan(fov / 2) * aspect));
    const distance = Math.max(fitHeightDistance, fitWidthDistance) * 1.18;

    camera.position.copy(target.clone().add(new THREE.Vector3(distance * 0.78, distance * 0.54, distance * 0.86)));
    camera.near = Math.max(radius / 180, 0.001);
    camera.far = Math.max(distance * 8, radius * 16, metrics.diagonal * 6);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
    controls.target.copy(target);
    controls.minDistance = Math.max(radius * 0.08, 0.02);
    controls.maxDistance = Math.max(radius * 18, distance * 4);
    controls.update();
  };

  const placeModelOnTable = () => {
    const model = modelRef.current;
    if (!model) return;
    const box = updateModelBox();
    if (!box) return;
    const center = box.getCenter(new THREE.Vector3());
    model.position.x -= center.x;
    model.position.y -= box.min.y;
    model.position.z -= center.z;
    updateModelBox({ refreshGrid: true });
    clearSplitOverlay();
    clearSymmetryOverlay();
    setViewVersion((value) => value + 1);
    centerView();
    if (compareMode !== "after") {
      onOrientationChange?.((current) => ({
        ...current,
        translate_to_floor: true,
      }));
    }
    setPreviewStatus("Модель поставлена на стол");
  };

  const rotateModel = (axis) => {
    const model = modelRef.current;
    if (!model) return;
    const angle = Math.PI / 2;
    if (axis === "x") model.rotation.x += angle;
    if (axis === "y") model.rotation.y += angle;
    if (axis === "z") model.rotation.z += angle;
    if (compareMode !== "after") {
      onOrientationChange?.((current) => ({
        ...current,
        [`rotation_${axis}`]: ((Number(current[`rotation_${axis}_deg`] ?? current[`rotation_${axis}`] ?? 0) + 90) % 360),
        [`rotation_${axis}_deg`]: ((Number(current[`rotation_${axis}_deg`] ?? current[`rotation_${axis}`] ?? 0) + 90) % 360),
      }));
    }
    placeModelOnTable();
    setPreviewStatus(`Модель повернута по ${axis.toUpperCase()}`);
  };

  useEffect(() => {
    const model = modelRef.current;
    if (!model || previewState !== "ready" || compareMode === "after") return;
    const transform = orientationTransform || {};
    const rotationX = Number(transform.rotation_x_deg ?? transform.rotation_x ?? 0) || 0;
    const rotationY = Number(transform.rotation_y_deg ?? transform.rotation_y ?? 0) || 0;
    const rotationZ = Number(transform.rotation_z_deg ?? transform.rotation_z ?? 0) || 0;
    model.rotation.set(
      THREE.MathUtils.degToRad(rotationX),
      THREE.MathUtils.degToRad(rotationY),
      THREE.MathUtils.degToRad(rotationZ),
    );
    model.position.set(
      Number(transform.translate_x_mm || 0),
      0,
      Number(transform.translate_z_mm || 0),
    );
    if (transform.translate_to_floor) {
      const box = updateModelBox();
      if (box) model.position.y -= box.min.y;
    }
    updateModelBox();
    clearSplitOverlay();
    clearSymmetryOverlay();
    setViewVersion((value) => value + 1);
  }, [orientationTransform, previewState, compareMode]);

  const getPlaneDimensions = (axis, size) => {
    if (axis === "x") return [Math.max(size.z, 1) * 1.18, Math.max(size.y, 1) * 1.18];
    if (axis === "y") return [Math.max(size.x, 1) * 1.18, Math.max(size.z, 1) * 1.18];
    return [Math.max(size.x, 1) * 1.18, Math.max(size.y, 1) * 1.18];
  };

  const positionOnPlane = (axis, planeValue, center, offsetA, offsetB) => {
    if (axis === "x") return new THREE.Vector3(planeValue, center.y + offsetB, center.z + offsetA);
    if (axis === "y") return new THREE.Vector3(center.x + offsetA, planeValue, center.z + offsetB);
    return new THREE.Vector3(center.x + offsetA, center.y + offsetB, planeValue);
  };

  const orientPlane = (mesh, axis) => {
    if (axis === "x") mesh.rotation.y = Math.PI / 2;
    if (axis === "y") mesh.rotation.x = Math.PI / 2;
  };

  const createConnectorHints = (axis, mode, planeValue, center, planeWidth, planeHeight, normalSize) => {
    const group = new THREE.Group();
    const markerPositions = [
      [-planeWidth * 0.24, -planeHeight * 0.22],
      [planeWidth * 0.24, -planeHeight * 0.22],
      [-planeWidth * 0.24, planeHeight * 0.22],
      [planeWidth * 0.24, planeHeight * 0.22],
    ];

    if (mode === "pins" || mode === "magnets") {
      const material = new THREE.MeshBasicMaterial({ color: mode === "magnets" ? 0x60a5fa : 0x4ade80, transparent: true, opacity: 0.9, depthWrite: false });
      markerPositions.forEach(([offsetA, offsetB]) => {
        const marker = new THREE.Mesh(
          mode === "magnets"
            ? new THREE.CylinderGeometry(Math.max(normalSize * 0.02, 1), Math.max(normalSize * 0.02, 1), Math.max(normalSize * 0.01, 0.5), 28)
            : new THREE.SphereGeometry(Math.max(normalSize * 0.018, 0.8), 18, 12),
          material,
        );
        orientPlane(marker, axis);
        marker.position.copy(positionOnPlane(axis, planeValue, center, offsetA, offsetB));
        marker.renderOrder = 4;
        group.add(marker);
      });
    }

    if (mode === "slots" || mode === "glue" || mode === "lock") {
      const color = mode === "glue" ? 0xf59e0b : mode === "lock" ? 0xc084fc : 0xffd166;
      const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.88, depthWrite: false });
      markerPositions.forEach(([offsetA, offsetB], index) => {
        const slotLength = Math.max(planeWidth * (mode === "glue" ? 0.22 : 0.16), 2);
        const slotWidth = Math.max(planeHeight * (mode === "lock" ? 0.06 : 0.04), 0.8);
        const slotDepth = Math.max(normalSize * 0.01, 0.5);
        const geometry =
          axis === "x"
            ? new THREE.BoxGeometry(slotDepth, slotWidth, slotLength)
            : axis === "y"
              ? new THREE.BoxGeometry(slotLength, slotDepth, slotWidth)
              : new THREE.BoxGeometry(slotLength, slotWidth, slotDepth);
        const marker = new THREE.Mesh(geometry, material);
        marker.position.copy(positionOnPlane(axis, planeValue, center, offsetA, offsetB));
        if (index % 2 === 1 && axis === "z") marker.rotation.z = Math.PI / 2;
        marker.renderOrder = 4;
        group.add(marker);
      });
    }

    return group;
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    scene.background = null;
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 10000);
    camera.position.set(120, 90, 120);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.02;
    renderer.setClearColor(0x000000, 0);
    rendererRef.current = renderer;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.enableRotate = true;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.screenSpacePanning = false;
    controls.rotateSpeed = 0.72;
    controls.zoomSpeed = 0.78;
    controls.panSpeed = 0.58;
    controlsRef.current = controls;

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const hitSelectionPoint = (event) => {
      if (!modelRef.current) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / Math.max(rect.height, 1)) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const intersections = raycaster.intersectObject(modelRef.current, true);
      const hit = intersections.find((item) => item.object?.geometry);
      if (!hit) return null;
      const worldPoint = hit.point.clone();
      const localPoint = hit.object.worldToLocal(worldPoint.clone());
      const offset = hit.object.geometry?.userData?.originalOffset || { x: 0, y: 0, z: 0 };
      const originalPoint = [
        Number((localPoint.x + offset.x).toFixed(6)),
        Number((localPoint.y + offset.y).toFixed(6)),
        Number((localPoint.z + offset.z).toFixed(6)),
      ];
      return { worldPoint, originalPoint };
    };
    const addLocalSelectionRegion = (event, force = false) => {
      if (!localSelectionEnabledRef.current || !modelRef.current) return;
      const hit = hitSelectionPoint(event);
      if (!hit) return;
      const radius = Number(localSelectionRadiusRef.current || 10);
      if (!force && lastBrushWorldPointRef.current) {
        const distance = hit.worldPoint.distanceTo(lastBrushWorldPointRef.current);
        if (distance < radius / 2) return;
      }
      lastBrushWorldPointRef.current = hit.worldPoint.clone();
      onLocalSelectionChangeRef.current?.((current) => {
        const currentRegions = normalizeSelectionRegions(current);
        if (currentRegions.length >= 30) {
          setPreviewStatus("Достигнут лимит выделения для текущего режима");
          return current;
        }
        const nextRegions = [
          ...currentRegions,
          { center: hit.originalPoint, radius_mm: radius },
        ];
        const preview = drawLocalSelectionOverlay(nextRegions) || {};
        const estimatedVertices = preview.selectedVertices ?? estimateSelectedVertices(nextRegions);
        setPreviewStatus(estimatedVertices < 50 ? "Область слишком маленькая. Увеличьте радиус кисти." : "Область выбрана для локальной правки");
        return {
          type: "spheres",
          regions: nextRegions,
          strength: localSelectionStrengthRef.current,
          estimated_vertices: estimatedVertices,
          estimated_faces: preview.selectedFaces || 0,
          selected_percent: preview.selectedPercent || 0,
        };
      });
    };
    const handleSelectionPointerDown = (event) => {
      if (!localSelectionEnabledRef.current) return;
      event.preventDefault();
      if (localSelectionModeRef.current === "brush") {
        brushActiveRef.current = true;
        controls.enabled = false;
        addLocalSelectionRegion(event, true);
      }
    };
    const handleSelectionPointerMove = (event) => {
      if (!localSelectionEnabledRef.current || localSelectionModeRef.current !== "brush" || !brushActiveRef.current) return;
      event.preventDefault();
      addLocalSelectionRegion(event);
    };
    const handleSelectionPointerUp = () => {
      brushActiveRef.current = false;
      lastBrushWorldPointRef.current = null;
      controls.enabled = true;
    };
    const handleSelectionClick = (event) => {
      if (!localSelectionEnabledRef.current || localSelectionModeRef.current !== "point") return;
      addLocalSelectionRegion(event, true);
      setPreviewStatus("Область выбрана для локальной правки");
    };
    renderer.domElement.addEventListener("pointerdown", handleSelectionPointerDown);
    renderer.domElement.addEventListener("pointermove", handleSelectionPointerMove);
    window.addEventListener("pointerup", handleSelectionPointerUp);
    renderer.domElement.addEventListener("click", handleSelectionClick);

    scene.add(new THREE.HemisphereLight(0xcdefff, 0x162235, 1.16));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.15);
    keyLight.position.set(90, 130, 80);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x8bd9ff, 0.64);
    fillLight.position.set(-80, 40, 90);
    scene.add(fillLight);
    const rimLight = new THREE.DirectionalLight(0x68f0d8, 1.05);
    rimLight.position.set(-90, 80, -60);
    scene.add(rimLight);

    rebuildEngineeringGrid({
      box: new THREE.Box3(new THREE.Vector3(-40, 0, -40), new THREE.Vector3(40, 40, 40)),
      diagonal: 120,
    });

    const resize = () => {
      const width = mount.clientWidth || 640;
      const height = mount.clientHeight || 420;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);

    const animate = (time = 0) => {
      controls.update();
      renderer.render(scene, camera);
      const perf = performanceRef.current;
      perf.frames += 1;
      if (!perf.lastTime) perf.lastTime = time;
      const elapsed = time - perf.lastTime;
      if (elapsed >= 750) {
        perf.fps = Math.round((perf.frames * 1000) / elapsed);
        perf.frameTime = Math.round((elapsed / Math.max(perf.frames, 1)) * 10) / 10;
        perf.frames = 0;
        perf.lastTime = time;
        setViewerMetrics((current) => current ? ({
          ...current,
          fps: perf.fps,
          frameTime: perf.frameTime,
          drawCalls: renderer.info.render.calls,
          renderTriangles: renderer.info.render.triangles,
          geometries: renderer.info.memory.geometries,
          textures: renderer.info.memory.textures,
        }) : current);
      }
      frameRef.current = window.requestAnimationFrame(animate);
    };
    animate();

    return () => {
      resizeObserver.disconnect();
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
      clearSplitOverlay();
      clearSymmetryOverlay();
      clearLocalSelectionOverlay();
      if (gridRef.current) {
        scene.remove(gridRef.current);
        disposeObject(gridRef.current);
        gridRef.current = null;
      }
      if (floorRef.current) {
        scene.remove(floorRef.current);
        disposeObject(floorRef.current);
        floorRef.current = null;
      }
      renderer.domElement.removeEventListener("pointerdown", handleSelectionPointerDown);
      renderer.domElement.removeEventListener("pointermove", handleSelectionPointerMove);
      window.removeEventListener("pointerup", handleSelectionPointerUp);
      renderer.domElement.removeEventListener("click", handleSelectionClick);
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  const clearScene = () => {
    clearSplitOverlay();
    clearSymmetryOverlay();
    clearLocalSelectionOverlay();
    if (modelRef.current && sceneRef.current) {
      sceneRef.current.remove(modelRef.current);
      disposeObject(modelRef.current);
      modelRef.current = null;
    }
    modelBoxRef.current = null;
    modelSphereRef.current = null;
    modelMetricsRef.current = null;
    setViewerMetrics(null);
    setViewVersion((value) => value + 1);
    setPreviewState("idle");
    setPreviewStatus("Просмотр очищен");
  };

  const normalizeGeometryToCenter = (geometry) => {
    geometry.computeBoundingBox();
    const initialBox = geometry.boundingBox;
    const initialCenter = initialBox.getCenter(new THREE.Vector3());
    geometry.userData.originalOffset = {
      x: initialCenter.x,
      y: initialCenter.y,
      z: initialCenter.z,
    };
    geometry.translate(-initialCenter.x, -initialCenter.y, -initialCenter.z);
    geometry.computeVertexNormals();
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    return geometry;
  };

  const colorForChangeLevel = (level) => {
    const colors = {
      none: new THREE.Color(0x8bd9ff),
      low: new THREE.Color(0x72f0a8),
      medium: new THREE.Color(0xffd166),
      high: new THREE.Color(0xff5c7a),
    };
    return colors[level] || colors.none;
  };

  const applyChangeMapColors = (geometry, changeMap) => {
    const position = geometry.getAttribute("position");
    const vertexCount = position?.count || 0;
    const colorArray = new Float32Array(vertexCount * 3);
    const levels = new Map();
    (changeMap?.vertices || []).forEach((item) => {
      if (typeof item.index === "number") levels.set(item.index, item.level || "none");
    });

    for (let index = 0; index < vertexCount; index += 1) {
      const color = colorForChangeLevel(levels.get(index) || "none");
      colorArray[index * 3] = color.r;
      colorArray[index * 3 + 1] = color.g;
      colorArray[index * 3 + 2] = color.b;
    }
    geometry.setAttribute("color", new THREE.BufferAttribute(colorArray, 3));
  };

  const colorForArtifact = (reason, severity) => {
    if (reason === "spike" || severity === "high") return new THREE.Color(0xff365e);
    if (reason === "elongated_face" || severity === "medium") return new THREE.Color(0xff9f1c);
    return new THREE.Color(0xffd166);
  };

  const applyArtifactMapColors = (geometry, artifactMap) => {
    const position = geometry.getAttribute("position");
    const vertexCount = position?.count || 0;
    const faceCount = Math.floor(vertexCount / 3);
    const baseColor = new THREE.Color(0x8bd9ff);
    const colorArray = new Float32Array(vertexCount * 3);
    for (let index = 0; index < vertexCount; index += 1) {
      colorArray[index * 3] = baseColor.r;
      colorArray[index * 3 + 1] = baseColor.g;
      colorArray[index * 3 + 2] = baseColor.b;
    }

    (artifactMap?.faces || []).forEach((item) => {
      const faceIndex = Number(item.index);
      if (!Number.isFinite(faceIndex) || faceIndex < 0 || faceIndex >= faceCount) return;
      const color = colorForArtifact(item.reason, item.severity);
      for (let offset = 0; offset < 3; offset += 1) {
        const vertexIndex = faceIndex * 3 + offset;
        colorArray[vertexIndex * 3] = color.r;
        colorArray[vertexIndex * 3 + 1] = color.g;
        colorArray[vertexIndex * 3 + 2] = color.b;
      }
    });
    geometry.setAttribute("color", new THREE.BufferAttribute(colorArray, 3));
  };

  useEffect(() => {
    if (!file || !sceneRef.current || !cameraRef.current || !controlsRef.current) {
      return;
    }

    let cancelled = false;
    const loadPreview = async () => {
      clearScene();
      setPreviewState("loading");
      setPreviewStatus(
        artifactMapEnabled
          ? "Загружаем найденные дефекты..."
          : heatmapEnabled
            ? "Загружаем карту изменений..."
            : compareMode === "after"
              ? "Загружаем обработанную модель..."
              : "Модель загружается...",
      );
      try {
        const loader = new STLLoader();
        const buffer = await file.arrayBuffer();
        if (cancelled) return;
        const geometry = loader.parse(buffer);
        normalizeGeometryToCenter(geometry);

        if (heatmapEnabled && heatmapData) {
          const group = new THREE.Group();
          if (sourceFile) {
            const sourceBuffer = await sourceFile.arrayBuffer();
            if (cancelled) return;
            const sourceGeometry = loader.parse(sourceBuffer);
            normalizeGeometryToCenter(sourceGeometry);
            const sourceMaterial = new THREE.MeshStandardMaterial({
              color: 0xaab4c2,
              metalness: 0.08,
              roughness: 0.7,
              transparent: true,
              opacity: 0.28,
              depthWrite: false,
            });
            const sourceMesh = new THREE.Mesh(sourceGeometry, sourceMaterial);
            sourceMesh.renderOrder = 1;
            group.add(sourceMesh);
          }

          applyChangeMapColors(geometry, heatmapData);
          const targetMaterial = new THREE.MeshStandardMaterial({
            vertexColors: true,
            metalness: 0.2,
            roughness: 0.42,
            transparent: true,
            opacity: 0.96,
          });
          const targetMesh = new THREE.Mesh(geometry, targetMaterial);
          targetMesh.renderOrder = 2;
          group.add(targetMesh);
          sceneRef.current.add(group);
          modelRef.current = group;
        } else if (artifactMapEnabled && artifactMapData) {
          applyArtifactMapColors(geometry, artifactMapData);
          const material = new THREE.MeshStandardMaterial({
            vertexColors: true,
            metalness: 0.22,
            roughness: 0.42,
          });
          const mesh = new THREE.Mesh(geometry, material);
          sceneRef.current.add(mesh);
          modelRef.current = mesh;
        } else {
          const material = new THREE.MeshStandardMaterial({
            color: 0x8bd9ff,
            metalness: 0.34,
            roughness: 0.38,
          });
          const mesh = new THREE.Mesh(geometry, material);
          sceneRef.current.add(mesh);
          modelRef.current = mesh;
        }

        updateModelBox({ refreshGrid: true });
        centerView();
        setViewVersion((value) => value + 1);

        setPreviewState("ready");
        setPreviewStatus(
          artifactMapEnabled
            ? "Найденные дефекты готовы к просмотру"
            : heatmapEnabled
              ? "Карта изменений готова"
              : compareMode === "after"
                ? "Обработанная модель готова к просмотру"
                : "Модель готова к просмотру",
        );
      } catch (err) {
        setPreviewState("error");
        setPreviewStatus(
          artifactMapEnabled
            ? "Не удалось загрузить карту дефектов"
            : heatmapEnabled
              ? "Не удалось загрузить карту изменений"
              : compareMode === "after"
                ? "Не удалось открыть обработанную модель"
                : "Не удалось открыть STL",
        );
      }
    };

    loadPreview();
    return () => {
      cancelled = true;
    };
  }, [file, sourceFile, compareMode, heatmapEnabled, heatmapData, artifactMapEnabled, artifactMapData]);

  useEffect(() => {
    clearSplitOverlay();
    if (!splitPreviewEnabled || previewState !== "ready" || !sceneRef.current || !modelBoxRef.current) {
      return;
    }

    const box = modelBoxRef.current;
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const axis = splitAxis || "z";
    const axisIndex = { x: "x", y: "y", z: "z" }[axis];
    const minValue = box.min[axisIndex];
    const maxValue = box.max[axisIndex];
    const span = maxValue - minValue;
    if (!span || splitParts < 2) return;

    const overlay = new THREE.Group();
    overlay.name = "split-preview";
    const [planeWidth, planeHeight] = getPlaneDimensions(axis, size);
    const normalSize = Math.max(size.x, size.y, size.z) || 1;
    const planeMaterial = new THREE.MeshBasicMaterial({
      color: 0x8bd9ff,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const edgeMaterial = new THREE.LineBasicMaterial({ color: 0xdff6ff, transparent: true, opacity: 0.72, depthWrite: false });

    for (let index = 1; index < splitParts; index += 1) {
      const planeValue = minValue + (span * index) / splitParts + Number(splitPlaneOffset || 0);
      if (planeValue <= minValue || planeValue >= maxValue) continue;
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(planeWidth, planeHeight), planeMaterial);
      orientPlane(plane, axis);
      plane.position.copy(positionOnPlane(axis, planeValue, center, 0, 0));
      plane.renderOrder = 3;
      overlay.add(plane);

      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(plane.geometry), edgeMaterial);
      orientPlane(edges, axis);
      edges.position.copy(plane.position);
      edges.renderOrder = 4;
      overlay.add(edges);

      if (splitMode !== "simple") {
        overlay.add(createConnectorHints(axis, splitMode, planeValue, center, planeWidth, planeHeight, normalSize));
      }
    }

    sceneRef.current.add(overlay);
    splitOverlayRef.current = overlay;
  }, [splitPreviewEnabled, splitAxis, splitParts, splitMode, splitPlaneOffset, previewState, viewVersion]);

  useEffect(() => {
    clearSymmetryOverlay();
    if (!symmetryPreviewEnabled || previewState !== "ready" || !sceneRef.current || !modelBoxRef.current) {
      return;
    }

    const box = modelBoxRef.current;
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const axis = symmetryAxis || "x";
    const planeValue = center[axis];
    const [planeWidth, planeHeight] = getPlaneDimensions(axis, size);
    const normalSize = Math.max(size.x, size.y, size.z) || 1;
    const overlay = new THREE.Group();
    overlay.name = "symmetry-preview";

    const planeMaterial = new THREE.MeshBasicMaterial({
      color: 0x4ade80,
      transparent: true,
      opacity: 0.18,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x4ade80, transparent: true, opacity: 0.92, depthWrite: false });
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(planeWidth, planeHeight), planeMaterial);
    orientPlane(plane, axis);
    plane.position.copy(positionOnPlane(axis, planeValue, center, 0, 0));
    plane.renderOrder = 5;
    overlay.add(plane);

    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(plane.geometry), lineMaterial);
    orientPlane(edges, axis);
    edges.position.copy(plane.position);
    edges.renderOrder = 6;
    overlay.add(edges);

    const axisDirections = {
      x: new THREE.Vector3(1, 0, 0),
      y: new THREE.Vector3(0, 1, 0),
      z: new THREE.Vector3(0, 0, 1),
    };
    const arrow = new THREE.ArrowHelper(
      axisDirections[axis],
      center.clone().add(axisDirections[axis].clone().multiplyScalar(-normalSize * 0.42)),
      normalSize * 0.84,
      0x4ade80,
      Math.max(normalSize * 0.07, 2),
      Math.max(normalSize * 0.035, 1),
    );
    arrow.renderOrder = 7;
    overlay.add(arrow);

    sceneRef.current.add(overlay);
    symmetryOverlayRef.current = overlay;
  }, [symmetryPreviewEnabled, symmetryAxis, previewState, viewVersion]);

  useEffect(() => {
    if (!localSelectionEnabled || !localSelection) {
      clearLocalSelectionOverlay();
      return;
    }
    drawLocalSelectionOverlay(normalizeSelectionRegions(localSelection));
  }, [localSelectionEnabled, localSelection]);

  const takeScreenshot = () => {
    const renderer = rendererRef.current;
    const scene = sceneRef.current;
    const camera = cameraRef.current;
    if (!renderer || !scene || !camera) return;
    renderer.render(scene, camera);
    const link = document.createElement("a");
    link.download = "stl-master-preview.png";
    link.href = renderer.domElement.toDataURL("image/png");
    link.click();
  };

  const isLargeFile = file && file.size > 50 * 1024 * 1024;

  return (
    <div className="previewPanel">
      <div className="previewHeader">
        <div>
          <p className="panelLabel">3D-просмотр</p>
          <h2>{file ? file.name : "STL-модель будет показана после загрузки"}</h2>
        </div>
        <span className={`previewStatus ${previewState}`}>{previewStatus}</span>
      </div>
      <div className={`previewCanvas ${localSelectionEnabled ? "selectionActive" : ""}`}>
        <div className="previewCanvasStage" ref={mountRef} />
        <div className="viewerMetricHud" aria-hidden="true">
          <span><b>{formatViewerNumber(viewerMetrics?.triangles)}</b><small>треуг.</small></span>
          <span><b>{formatViewerSize(viewerMetrics?.radius)}</b><small>радиус</small></span>
          <span><b>{viewerMetrics?.fps || 0}</b><small>FPS</small></span>
        </div>
        <div className="viewerAxisGizmo" aria-hidden="true">
          <span className="viewerAxis viewerAxisX">X</span>
          <span className="viewerAxis viewerAxisY">Y</span>
          <span className="viewerAxis viewerAxisZ">Z</span>
          <i />
        </div>
        {previewState === "loading" && (
          <div className="viewerOverlay viewerOverlayLoading" role="status">
            <span />
            <strong>Готовим 3D-просмотр</strong>
            <small>STL остаётся в инженерной сцене после загрузки</small>
          </div>
        )}
        {isViewerBusy && previewState === "ready" && (
          <div className="viewerOverlay viewerOverlayProcessing" role="status">
            <span />
            <strong>Обработка выполняется</strong>
            <small>{uploading ? `Загрузка ${Math.round(Number(progress || 0))}%` : "Текущая модель остаётся доступной"}</small>
          </div>
        )}
        {isViewerResult && previewState === "ready" && (
          <div className="viewerResultBadge" role="status">
            <strong>Готово</strong>
            <small>Можно скачать результат или сравнить модели</small>
          </div>
        )}
        {splitPreviewEnabled && previewState === "ready" && (
          <div className="viewerSplitPreviewBadge" role="status">
            <strong>{splitOperationTitle || "Предпросмотр разреза"}</strong>
            <small>{splitParts} части · ось {String(splitAxis || "z").toUpperCase()} · {splitModeTitles[splitMode] || splitMode}</small>
          </div>
        )}
      </div>
      <p className="previewHelp">Если модель лежит не так, используйте кнопки поворота. Это меняет только просмотр, STL на сервере не изменяется.</p>
      {localSelectionEnabled && (
        <p className="previewWarning">
          Режим выборочной правки активен: {localSelectionMode === "brush" ? "зажмите мышь и проведите кистью по дефекту." : "кликните по проблемному месту на модели."}
        </p>
      )}
      {heatmapEnabled && (
        <div className="heatmapLegend">
          <span><i className="heatNone" />нет изменений</span>
          <span><i className="heatLow" />слабые</span>
          <span><i className="heatMedium" />средние</span>
          <span><i className="heatHigh" />сильные</span>
        </div>
      )}
      {heatmapEnabled && heatmapData?.sampled && (
        <p className="previewWarning">Показаны основные изменённые зоны.</p>
      )}
      {artifactMapEnabled && (
        <div className="heatmapLegend artifactLegend">
          <span><i className="artifactElongated" />вытянутые полигоны</span>
          <span><i className="artifactSpike" />шипы</span>
          <span><i className="artifactSuspicious" />подозрительные зоны</span>
        </div>
      )}
      {artifactMapEnabled && artifactMapData?.sampled && (
        <p className="previewWarning">Показаны основные найденные дефекты.</p>
      )}
      {heatmapError && <p className="previewWarning">{heatmapError}</p>}
      {artifactMapError && <p className="previewWarning">{artifactMapError}</p>}
      {isLargeFile && (
        <p className="previewWarning">Файл большой, 3D-просмотр может занять время и нагрузить устройство.</p>
      )}
      <div className="previewActions viewerToolbar" aria-label="Панель инструментов просмотра">
        <button className="viewerToolButton" type="button" disabled={previewState !== "ready"} aria-label="Центрировать модель" onClick={centerView}>
          <LaunchIcon type="target" />
          <span>Центрировать</span>
        </button>
        <button className="viewerToolButton" type="button" disabled={previewState !== "ready"} aria-label="Повернуть модель по оси X" onClick={() => rotateModel("x")}>
          <LaunchIcon type="rotateX" />
          <span>Повернуть по X</span>
        </button>
        <button className="viewerToolButton" type="button" disabled={previewState !== "ready"} aria-label="Повернуть модель по оси Y" onClick={() => rotateModel("y")}>
          <LaunchIcon type="rotateY" />
          <span>Повернуть по Y</span>
        </button>
        <button className="viewerToolButton" type="button" disabled={previewState !== "ready"} aria-label="Повернуть модель по оси Z" onClick={() => rotateModel("z")}>
          <LaunchIcon type="rotateZ" />
          <span>Повернуть по Z</span>
        </button>
        <button className="viewerToolButton" type="button" disabled={previewState !== "ready"} aria-label="Сбросить вид модели" onClick={placeModelOnTable}>
          <LaunchIcon type="resetView" />
          <span>Сбросить вид</span>
        </button>
        <button className="viewerToolButton" type="button" aria-label="Очистить текущую модель" onClick={onClearModel || clearScene}>
          <LaunchIcon type="clearModel" />
          <span>Очистить</span>
        </button>
        <button className="viewerToolButton viewerToolButtonWide" type="button" aria-label="Загрузить другую STL-модель" onClick={onSelectFile}>
          <LaunchIcon type="upload" />
          <span>Загрузить другую модель</span>
        </button>
        <button className="viewerToolButton" type="button" disabled={previewState !== "ready"} aria-label="Сделать снимок окна просмотра" onClick={takeScreenshot}>
          <LaunchIcon type="camera" />
          <span>Сделать снимок</span>
        </button>
      </div>
    </div>
  );
}

function normalizeCompareGeometry(geometry) {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  const center = box.getCenter(new THREE.Vector3());
  geometry.translate(-center.x, -box.min.y, -center.z);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

function compareChangeColor(level) {
  const colors = {
    none: new THREE.Color(0x8190a4),
    low: new THREE.Color(0x6ee7b7),
    medium: new THREE.Color(0xfacc15),
    high: new THREE.Color(0xfb7185),
  };
  return colors[level] || colors.none;
}

function applyCompareChangeMap(geometry, changeMap) {
  const position = geometry.getAttribute("position");
  const vertexCount = position?.count || 0;
  const colors = new Float32Array(vertexCount * 3);
  const changed = new Map();
  (changeMap?.vertices || []).forEach((vertex) => {
    if (typeof vertex.index === "number") changed.set(vertex.index, vertex.level || "none");
  });

  for (let index = 0; index < vertexCount; index += 1) {
    const color = compareChangeColor(changed.get(index) || "none");
    colors[index * 3] = color.r;
    colors[index * 3 + 1] = color.g;
    colors[index * 3 + 2] = color.b;
  }

  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
}

function compareArtifactColor(reason, severity) {
  if (reason === "spike" || severity === "high") return new THREE.Color(0xff365e);
  if (reason === "elongated_face" || severity === "medium") return new THREE.Color(0xff9f1c);
  return new THREE.Color(0xffd166);
}

function applyCompareArtifactMap(geometry, artifactMap) {
  const position = geometry.getAttribute("position");
  const vertexCount = position?.count || 0;
  const faceCount = Math.floor(vertexCount / 3);
  const baseColor = new THREE.Color(0x8ca1b8);
  const colors = new Float32Array(vertexCount * 3);

  for (let index = 0; index < vertexCount; index += 1) {
    colors[index * 3] = baseColor.r;
    colors[index * 3 + 1] = baseColor.g;
    colors[index * 3 + 2] = baseColor.b;
  }

  (artifactMap?.faces || []).forEach((face) => {
    const faceIndex = Number(face.index);
    if (!Number.isFinite(faceIndex) || faceIndex < 0 || faceIndex >= faceCount) return;
    const color = compareArtifactColor(face.reason, face.severity);
    for (let offset = 0; offset < 3; offset += 1) {
      const vertexIndex = faceIndex * 3 + offset;
      colors[vertexIndex * 3] = color.r;
      colors[vertexIndex * 3 + 1] = color.g;
      colors[vertexIndex * 3 + 2] = color.b;
    }
  });

  (artifactMap?.regions || []).forEach((region) => {
    if (!Array.isArray(region.center)) return;
    const center = new THREE.Vector3(region.center[0], region.center[1], region.center[2]);
    const radius = Number(region.radius || 0);
    if (!radius) return;
    const color = compareArtifactColor(region.reason, region.severity);
    for (let index = 0; index < vertexCount; index += 1) {
      const point = new THREE.Vector3(position.getX(index), position.getY(index), position.getZ(index));
      if (point.distanceTo(center) <= radius) {
        colors[index * 3] = color.r;
        colors[index * 3 + 1] = color.g;
        colors[index * 3 + 2] = color.b;
      }
    }
  });

  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
}

function ComparePane({
  id,
  title,
  file,
  overlayFile,
  overlayOpacity = 0.42,
  highlightChanges,
  highlightDefects,
  changeMapData,
  artifactMapData,
  focusChangesVersion,
  sharedCameraState,
  setSharedCameraState,
}) {
  const mountRef = useRef(null);
  const rendererRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const frameRef = useRef(null);
  const groupRef = useRef(null);
  const [status, setStatus] = useState(file ? "Загрузка модели..." : "Модель недоступна");

  const disposeObject = (object) => {
    object.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach((material) => material.dispose());
        else child.material.dispose();
      }
    });
  };

  const clearModel = () => {
    if (groupRef.current && sceneRef.current) {
      sceneRef.current.remove(groupRef.current);
      disposeObject(groupRef.current);
      groupRef.current = null;
    }
  };

  const fitCameraToGroup = (group) => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls || !group) return;
    const box = new THREE.Box3().setFromObject(group);
    const size = box.getSize(new THREE.Vector3());
    const maxSize = Math.max(size.x, size.y, size.z) || 1;
    const target = new THREE.Vector3(0, Math.max(size.y * 0.5, 0), 0);
    const distance = (maxSize / (2 * Math.tan((camera.fov * Math.PI) / 360))) * 1.55;
    camera.position.set(distance * 0.92, target.y + distance * 0.7, distance * 0.92);
    camera.near = Math.max(distance / 100, 0.01);
    camera.far = Math.max(distance * 120, maxSize * 30);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
    controls.target.copy(target);
    controls.update();
    setSharedCameraState?.({
      source: id,
      version: Date.now(),
      position: camera.position.toArray(),
      target: controls.target.toArray(),
      zoom: camera.zoom,
    });
  };

  const focusCameraOnChangeMap = () => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    const group = groupRef.current;
    if (!camera || !controls || !group || !changeMapData?.vertices?.length) return;
    const changed = changeMapData.vertices.filter((vertex) => Number(vertex.distance || 0) > Number(changeMapData.thresholds?.low || 0.05));
    if (!changed.length) return;
    let targetMesh = null;
    group.traverse((child) => {
      if (!targetMesh && child.isMesh && child.geometry?.attributes?.position) targetMesh = child;
    });
    const position = targetMesh?.geometry?.attributes?.position;
    if (!position) return;
    const box = new THREE.Box3();
    changed.forEach((vertex) => {
      const index = Number(vertex.index);
      if (!Number.isFinite(index) || index < 0 || index >= position.count) return;
      box.expandByPoint(new THREE.Vector3(position.getX(index), position.getY(index), position.getZ(index)));
    });
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const target = box.getCenter(new THREE.Vector3());
    const maxSize = Math.max(size.x, size.y, size.z, 2);
    const distance = (maxSize / (2 * Math.tan((camera.fov * Math.PI) / 360))) * 2.8;
    camera.position.set(target.x + distance * 0.8, target.y + distance * 0.55, target.z + distance * 0.8);
    camera.near = Math.max(distance / 100, 0.01);
    camera.far = Math.max(distance * 120, maxSize * 50);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
    controls.target.copy(target);
    controls.update();
    setSharedCameraState?.({
      source: id,
      version: Date.now(),
      position: camera.position.toArray(),
      target: controls.target.toArray(),
      zoom: camera.zoom,
    });
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    scene.background = null;
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
    camera.position.set(120, 90, 120);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    rendererRef.current = renderer;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enableRotate = true;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.screenSpacePanning = true;
    controlsRef.current = controls;

    controls.addEventListener("change", () => {
      setSharedCameraState?.({
        source: id,
        version: Date.now(),
        position: camera.position.toArray(),
        target: controls.target.toArray(),
        zoom: camera.zoom,
      });
    });

    scene.add(new THREE.HemisphereLight(0xcdefff, 0x111827, 1.75));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.45);
    keyLight.position.set(80, 120, 70);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0x68f0d8, 1.15);
    rimLight.position.set(-90, 80, -60);
    scene.add(rimLight);

    const grid = new THREE.GridHelper(180, 18, 0x6ee7f9, 0x24384c);
    grid.position.y = 0;
    scene.add(grid);

    const resize = () => {
      const width = mount.clientWidth || 420;
      const height = mount.clientHeight || 320;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);

    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      frameRef.current = window.requestAnimationFrame(animate);
    };
    animate();

    return () => {
      resizeObserver.disconnect();
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
      clearModel();
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  useEffect(() => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls || !sharedCameraState || sharedCameraState.source === id) return;
    if (Array.isArray(sharedCameraState.position)) {
      camera.position.fromArray(sharedCameraState.position);
    }
    if (Array.isArray(sharedCameraState.target)) {
      controls.target.fromArray(sharedCameraState.target);
    }
    if (typeof sharedCameraState.zoom === "number") {
      camera.zoom = sharedCameraState.zoom;
    }
    camera.updateProjectionMatrix();
    controls.update();
  }, [sharedCameraState?.version]);

  useEffect(() => {
    if (!file || !sceneRef.current) {
      setStatus("Модель недоступна");
      clearModel();
      return undefined;
    }

    let cancelled = false;
    const load = async () => {
      clearModel();
      setStatus("Загрузка модели...");
      try {
        const loader = new STLLoader();
        const group = new THREE.Group();

        if (overlayFile) {
          const overlayGeometry = normalizeCompareGeometry(loader.parse(await overlayFile.arrayBuffer()));
          const overlayMesh = new THREE.Mesh(
            overlayGeometry,
            new THREE.MeshStandardMaterial({
              color: 0xaab4c2,
              metalness: 0.06,
              roughness: 0.72,
              transparent: true,
              opacity: overlayOpacity,
              depthWrite: false,
            }),
          );
          overlayMesh.renderOrder = 1;
          group.add(overlayMesh);
        }

        const geometry = normalizeCompareGeometry(loader.parse(await file.arrayBuffer()));
        const usesVertexColors = Boolean((highlightChanges && changeMapData) || (highlightDefects && artifactMapData));
        if (highlightChanges && changeMapData) {
          applyCompareChangeMap(geometry, changeMapData);
        }
        if (highlightDefects && artifactMapData) {
          applyCompareArtifactMap(geometry, artifactMapData);
        }

        const material = new THREE.MeshStandardMaterial({
          color: usesVertexColors ? 0xffffff : 0x8bd9ff,
          vertexColors: usesVertexColors,
          metalness: 0.24,
          roughness: 0.42,
          transparent: Boolean(overlayFile),
          opacity: overlayFile ? 0.96 : 1,
        });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.renderOrder = 2;
        group.add(mesh);

        if (cancelled) {
          disposeObject(group);
          return;
        }
        sceneRef.current.add(group);
        groupRef.current = group;
        fitCameraToGroup(group);
        setStatus("Готово");
      } catch {
        setStatus("Не удалось открыть STL");
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [file, overlayFile, overlayOpacity, highlightChanges, highlightDefects, changeMapData, artifactMapData]);

  useEffect(() => {
    if (!focusChangesVersion) return;
    focusCameraOnChangeMap();
  }, [focusChangesVersion]);

  return (
    <div className="comparePane">
      <div className="comparePaneHeader">
        <strong>{title}</strong>
        <span>{status}</span>
      </div>
      <div className="compareCanvas" ref={mountRef} />
    </div>
  );
}

function CompareView2({
  sourceFile,
  finalFile,
  mode,
  setMode,
  highlightChanges,
  highlightDefects,
  onToggleChanges,
  onToggleDefects,
  changeMapData,
  artifactMapData,
  hasChangeMap,
  hasArtifactMap,
  heatmapLoading,
  artifactMapLoading,
  focusChangesVersion,
  qualityScoreBefore,
  qualityScoreAfter,
  fixedDefects,
}) {
  const [sharedCameraState, setSharedCameraState] = useState(null);
  const [overlayOpacity, setOverlayOpacity] = useState(58);
  const qualityDelta =
    typeof qualityScoreBefore === "number" && typeof qualityScoreAfter === "number"
      ? qualityScoreAfter - qualityScoreBefore
      : null;

  const renderSinglePane = () => (
    <div className="compareViewportGrid single">
      <ComparePane
        artifactMapData={artifactMapData}
        changeMapData={changeMapData}
        file={mode === "before" ? sourceFile : finalFile}
        focusChangesVersion={mode !== "before" ? focusChangesVersion : 0}
        highlightChanges={mode !== "before" && highlightChanges}
        highlightDefects={highlightDefects}
        id={mode}
        setSharedCameraState={setSharedCameraState}
        sharedCameraState={sharedCameraState}
        title={mode === "before" ? "Исходная модель" : "Итоговая модель"}
      />
    </div>
  );

  return (
    <div className="compareView2">
      <div className="compareToolbar">
        <div className="compareModeTabs" role="group" aria-label="Режим сравнения">
          {[
            ["before", "До"],
            ["after", "После"],
            ["compare", "Сравнение"],
            ["overlay", "Наложение"],
          ].map(([value, label]) => (
            <button className={mode === value ? "active" : ""} key={value} type="button" onClick={() => setMode?.(value)}>
              {label}
            </button>
          ))}
        </div>
        <div className="compareHighlightActions">
          <button
            className={highlightChanges ? "active" : ""}
            type="button"
            disabled={!hasChangeMap || heatmapLoading}
            onClick={onToggleChanges}
          >
            {heatmapLoading ? "Загружаем..." : "Подсветить изменения"}
          </button>
          <button
            className={highlightDefects ? "active" : ""}
            type="button"
            disabled={!hasArtifactMap || artifactMapLoading}
            onClick={onToggleDefects}
          >
            {artifactMapLoading ? "Загружаем..." : "Подсветить дефекты"}
          </button>
        </div>
      </div>

      {mode === "compare" ? (
        <div className="compareViewportGrid split">
          <ComparePane
            artifactMapData={artifactMapData}
            changeMapData={changeMapData}
            file={sourceFile}
            focusChangesVersion={0}
            highlightChanges={false}
            highlightDefects={highlightDefects}
            id="before"
            setSharedCameraState={setSharedCameraState}
            sharedCameraState={sharedCameraState}
            title="Исходная модель"
          />
          <ComparePane
            artifactMapData={artifactMapData}
            changeMapData={changeMapData}
            file={finalFile}
            focusChangesVersion={focusChangesVersion}
            highlightChanges={highlightChanges}
            highlightDefects={false}
            id="after"
            setSharedCameraState={setSharedCameraState}
            sharedCameraState={sharedCameraState}
            title="Итоговая модель"
          />
        </div>
      ) : mode === "overlay" ? (
        <div className="compareOverlayMode">
          <ComparePane
            artifactMapData={artifactMapData}
            changeMapData={changeMapData}
            file={finalFile}
            focusChangesVersion={focusChangesVersion}
            highlightChanges={highlightChanges}
            highlightDefects={highlightDefects}
            id="overlay"
            overlayFile={sourceFile}
            overlayOpacity={overlayOpacity / 100}
            setSharedCameraState={setSharedCameraState}
            sharedCameraState={sharedCameraState}
            title="Наложение: исходная + итоговая"
          />
          <label className="overlayControl">
            <span>Прозрачность исходной модели</span>
            <input
              type="range"
              min="0"
              max="100"
              value={overlayOpacity}
              onChange={(event) => setOverlayOpacity(Number(event.target.value))}
            />
            <strong>{overlayOpacity}%</strong>
          </label>
        </div>
      ) : (
        renderSinglePane()
      )}

      <div className="compareMetrics">
        <div>
          <span>До</span>
          <strong>{formatMetric(qualityScoreBefore, "/100")}</strong>
        </div>
        <div>
          <span>После</span>
          <strong>{formatMetric(qualityScoreAfter, "/100")}</strong>
        </div>
        <div>
          <span>Улучшение</span>
          <strong>{qualityDelta === null ? "—" : `${qualityDelta > 0 ? "+" : ""}${qualityDelta}`}</strong>
        </div>
        <div>
          <span>Исправлено</span>
          <strong>{formatMetric(fixedDefects)} дефектов</strong>
        </div>
      </div>

      {highlightChanges && changeMapData?.sampled && (
        <p className="compareHint">Показаны основные изменённые зоны.</p>
      )}
      {highlightDefects && (
        <div className="compareLegend">
          <span><i className="defectRed" /> серьёзные дефекты</span>
          <span><i className="defectOrange" /> AI-артефакты</span>
          <span><i className="defectYellow" /> подозрительные зоны</span>
        </div>
      )}
    </div>
  );
}

function WorkflowPanel({ id, title, meta, success = true, activePanel, setActivePanel, children, className = "" }) {
  const isOpen = activePanel === id;
  const toggle = () => setActivePanel?.(isOpen ? null : id);

  return (
    <section className={`workflowPanel processingStage ${success ? "stageOk" : "stageWarn"} ${isOpen ? "open" : ""} ${className}`}>
      <button className="workflowPanelHeader" type="button" aria-expanded={isOpen} onClick={toggle}>
        <span className="stageChevron" aria-hidden="true">▶</span>
        <span>{title}</span>
        <em>{meta || (success ? "готово" : "требует внимания")}</em>
      </button>
      {isOpen && <div className="workflowPanelBody stageBody">{children}</div>}
    </section>
  );
}

function ProcessingStage({ id, title, success, activePanel, setActivePanel, children }) {
  return (
    <WorkflowPanel
      activePanel={activePanel}
      id={id}
      setActivePanel={setActivePanel}
      success={success}
      title={title}
    >
      {children}
    </WorkflowPanel>
  );
}

function CurrentModelSummary({
  result,
  history,
  activePanel,
  setActivePanel,
  qualityScoreBefore,
  qualityScoreAfter,
}) {
  const usefulHistory = Array.isArray(history)
    ? [...history].reverse().find((item) => item.visible_result?.created)
    : null;
  const finalModel = result?.final_model || result?.after_file || "original.stl";
  const finalDownloadUrl = result?.final_download_url || result?.after_download_url || result?.download_url;
  const qualityDelta =
    typeof qualityScoreBefore === "number" && typeof qualityScoreAfter === "number"
      ? qualityScoreAfter - qualityScoreBefore
      : null;

  return (
    <section className={`currentModelSummary workflowPanel ${activePanel === "current_model" ? "open" : ""}`}>
      <button
        className="workflowPanelHeader currentModelHeader"
        type="button"
        aria-expanded={activePanel === "current_model"}
        onClick={() => setActivePanel?.(activePanel === "current_model" ? null : "current_model")}
      >
        <span className="stageChevron" aria-hidden="true">▶</span>
        <span>Текущая модель</span>
        <em>{finalModel}</em>
      </button>
      {activePanel === "current_model" && (
        <div className="workflowPanelBody currentModelBody">
          <div className="currentModelGrid">
            <div>
              <span>Файл</span>
              <strong>{finalModel}</strong>
            </div>
            <div>
              <span>Источник</span>
              <strong>{usefulHistory?.title || "Исходная модель"}</strong>
            </div>
            <div>
              <span>Качество до</span>
              <strong>{formatMetric(qualityScoreBefore, "/100")}</strong>
            </div>
            <div>
              <span>Качество после</span>
              <strong>{formatMetric(qualityScoreAfter, "/100")}</strong>
            </div>
            <div>
              <span>Изменение</span>
              <strong>{qualityDelta === null ? "—" : `${qualityDelta > 0 ? "+" : ""}${qualityDelta}`}</strong>
            </div>
          </div>
          <div className="currentModelActions">
            {finalDownloadUrl && (
              <a href={`${getApiBaseUrl()}${finalDownloadUrl}`} download>
                Скачать текущую модель
              </a>
            )}
            <button type="button" onClick={() => setActivePanel?.("history")}>
              Показать историю
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function CurrentResultBlock({
  result,
  sourceFile,
  finalFile,
  changeMapData,
  artifactMapData,
  heatmapEnabled,
  artifactMapEnabled,
  qualityScoreBefore,
  qualityScoreAfter,
  fixedDefects,
  activePanel,
  setActivePanel,
  hasProcessedPreview,
  hasArtifactMap,
  hasChangeMap,
  onCompare,
  onShowChanges,
  onFocusChanges,
  onShowDefects,
  heatmapLoading,
  artifactMapLoading,
  focusChangesVersion,
}) {
  const [compareViewMode, setCompareViewMode] = useState("compare");
  const finalModel = result?.final_model || result?.after_file || "original.stl";
  const finalDownloadUrl = result?.final_download_url || result?.after_download_url;
  const qualityDelta =
    typeof qualityScoreBefore === "number" && typeof qualityScoreAfter === "number"
      ? qualityScoreAfter - qualityScoreBefore
      : null;
  const tone = qualityTone(qualityScoreAfter ?? qualityScoreBefore);
  const compareOpen = activePanel === "result:compare";

  return (
    <section className="currentResultBlock">
      <div className="resultHeroTop">
        <div>
          <p className="panelLabel">Результат обработки</p>
          <h2>{tone.label}</h2>
        </div>
        <div className={`qualityPill ${tone.className}`}>
          <span>{tone.icon}</span>
          <strong>{formatMetric(qualityScoreAfter ?? qualityScoreBefore, " / 100")}</strong>
        </div>
      </div>
      <div className="resultHeroGrid">
        <div>
          <span>Качество</span>
          <strong>{formatMetric(qualityScoreBefore, "")} → {formatMetric(qualityScoreAfter, "")}</strong>
          {qualityDelta !== null && <small>{qualityDelta > 0 ? `+${qualityDelta} баллов` : "без заметного роста"}</small>}
        </div>
        <div>
          <span>Исправлено</span>
          <strong>{formatMetric(fixedDefects)} дефектов</strong>
          <small>по данным анализа модели</small>
        </div>
        <div>
          <span>Текущая модель</span>
          <strong>{finalModel}</strong>
          <small>итоговый STL</small>
        </div>
      </div>
      <div className="resultPrimaryActions">
        <button
          type="button"
          disabled={!hasProcessedPreview}
          onClick={() => {
            setActivePanel?.(compareOpen ? "current_model" : "result:compare");
            setCompareViewMode("compare");
            onCompare?.("after");
          }}
        >
          Сравнить модели
        </button>
        <button
          type="button"
          disabled={!hasChangeMap || !hasProcessedPreview}
          onClick={() => {
            setActivePanel?.("result:compare");
            setCompareViewMode("overlay");
            onShowChanges?.();
          }}
        >
          {heatmapLoading ? "Загружаем..." : "Подсветить изменения"}
        </button>
        <button
          type="button"
          disabled={!hasChangeMap || !hasProcessedPreview}
          onClick={() => {
            setActivePanel?.("result:compare");
            setCompareViewMode("overlay");
            onFocusChanges?.();
          }}
        >
          Фокус на изменениях
        </button>
        <button
          type="button"
          disabled={!hasArtifactMap}
          onClick={() => {
            setActivePanel?.("result:compare");
            setCompareViewMode("before");
            onShowDefects?.();
          }}
        >
          {artifactMapLoading ? "Загружаем..." : "Показать дефекты"}
        </button>
        {finalDownloadUrl && (
          <a href={`${getApiBaseUrl()}${finalDownloadUrl}`} download>
            Скачать STL
          </a>
        )}
      </div>
      {compareOpen && (
        <div className="compareView">
          <div className="compareViewHeader">
            <p className="panelLabel">Сравнение моделей</p>
            <h3>Исходная модель и итоговый STL</h3>
          </div>
          <CompareView2
            artifactMapData={artifactMapData}
            artifactMapLoading={artifactMapLoading}
            changeMapData={changeMapData}
            finalFile={finalFile}
            fixedDefects={fixedDefects}
            hasArtifactMap={hasArtifactMap}
            hasChangeMap={hasChangeMap}
            heatmapLoading={heatmapLoading}
            focusChangesVersion={focusChangesVersion}
            highlightChanges={heatmapEnabled}
            highlightDefects={artifactMapEnabled}
            mode={compareViewMode}
            onToggleChanges={onShowChanges}
            onToggleDefects={onShowDefects}
            qualityScoreAfter={qualityScoreAfter}
            qualityScoreBefore={qualityScoreBefore}
            setMode={(mode) => {
              setCompareViewMode(mode);
              if (mode === "before" || mode === "after") onCompare?.(mode);
            }}
            sourceFile={sourceFile}
          />
        </div>
      )}
    </section>
  );
}

function ProcessingHistoryTimeline({
  history,
  generatedFiles = [],
  onOpenFile,
  onShowChanges,
  onShowArtifacts,
  activePanel,
  setActivePanel,
  heatmapLoading,
  artifactMapLoading,
}) {
  if (!Array.isArray(history) || history.length === 0) return null;

  const historyOpen = activePanel === "history" || String(activePanel || "").startsWith("history:");

  return (
    <section className={`processingHistory workflowPanel ${historyOpen ? "open" : ""}`}>
      <button
        className="workflowPanelHeader"
        type="button"
        aria-expanded={historyOpen}
        onClick={() => setActivePanel?.(historyOpen ? "current_model" : "history")}
      >
        <span className="stageChevron" aria-hidden="true">▶</span>
        <span>Дополнительно</span>
        <em>История · JSON · Manifest</em>
      </button>
      {historyOpen && (
        <div className="workflowPanelBody historyPanelBody">
          <div className="additionalIntro">
            <p className="panelLabel">История обработки</p>
            <h3>Технические данные и файлы результата</h3>
          </div>
          {history.map((item) => {
            const files = item.files || (item.file ? [{ name: item.file, download_url: item.download_url }] : []);
            const firstFile = files[0];
            const stepPanelId = `history:${item.step}`;
            const stepOpen = activePanel === stepPanelId;
            return (
              <section
                className={`processingStage historyStage ${item.visible_result?.created ? "stageOk" : "stageWarn"} ${stepOpen ? "open" : ""}`}
                key={`${item.step}-${item.operation}`}
              >
                <button
                  className="workflowPanelHeader"
                  type="button"
                  aria-expanded={stepOpen}
                  onClick={() => setActivePanel?.(stepOpen ? "history" : stepPanelId)}
                >
                  <span className="stageChevron" aria-hidden="true">▶</span>
                  <span>#{item.step} · {item.title}</span>
                  <em>{files.length > 1 ? `${files.length} файлов` : firstFile?.name || "без файла"}</em>
                </button>
                {stepOpen && (
                  <div className="workflowPanelBody stageBody">
              <div className="historyFileList">
                {files.map((fileItem) => (
                  <div className="historyFileRow" key={fileItem.name}>
                    <div>
                      <strong>{fileItem.name}</strong>
                      <span>{item.operation}</span>
                    </div>
                    <div className="historyActions">
                      <button type="button" onClick={() => onOpenFile?.(fileItem.download_url, fileItem.name)}>
                        Открыть
                      </button>
                      <a href={fileItem.download_url} download>
                        Скачать
                      </a>
                    </div>
                  </div>
                ))}
              </div>
              <div className="historyActions historyStageActions">
                {item.change_map_url && firstFile && (
                  <button type="button" disabled={heatmapLoading} onClick={() => onShowChanges?.(item.change_map_url)}>
                    {heatmapLoading ? "Загружаем..." : "Сравнить модели"}
                  </button>
                )}
                {item.artifact_map_url && (
                  <button type="button" disabled={artifactMapLoading} onClick={onShowArtifacts}>
                    {artifactMapLoading ? "Загружаем..." : "Показать дефекты"}
                  </button>
                )}
                <button
                  className={activePanel === stepPanelId ? "selectedContinuation" : ""}
                  type="button"
                  onClick={() => setActivePanel?.(stepPanelId)}
                >
                  Продолжить от этого этапа
                </button>
              </div>
              {item.operation === "local_smoothing" && (
                <div className="historyLocalStats">
                  <span>Областей: {formatMetric(item.selected_regions)}</span>
                  <span>Вершин: {formatMetric(item.selected_vertices)}</span>
                  <span>Граней: {formatMetric(item.selected_faces)}</span>
                  <span>Изменено: {formatMetric(item.changed_vertices)}</span>
                  <span>Сила: {item.strength || "—"}</span>
                </div>
              )}
                  </div>
                )}
              </section>
            );
          })}
          <GeneratedFilesBlock files={generatedFiles} />
        </div>
      )}
    </section>
  );
}

function LaunchIcon({ type }) {
  const paths = {
    logo: "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM8 10.5h8M9.5 14h5M12 7v3.5",
    flash: "M13 2L4 14h7l-1 8 10-13h-7l1-7z",
    play: "M8 5v14l11-7-11-7z",
    upload: "M12 16V4M7 9l5-5 5 5M5 20h14",
    analyze: "M4 12a8 8 0 1016 0 8 8 0 00-16 0zM12 8v4l3 2",
    gauge: "M5 17a7 7 0 1114 0M12 17l4-6M8 17h8",
    repair: "M5 16l4 4 10-12M7 7h10v6H7z",
    split: "M12 3v18M5 8h14M5 16h14",
    connectors: "M7 8h4v8H7zM13 8h4v8h-4zM11 12h2",
    check: "M4 12l5 5L20 6",
    export: "M12 4v10M8 10l4 4 4-4M5 20h14",
    shield: "M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3z",
    shieldCheck: "M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3zM9 12l2 2 4-5",
    cube: "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM4 7.5l8 4.5 8-4.5M12 12v9",
    sliders: "M5 7h9M18 7h1M5 17h1M10 17h9M8 5v4M16 15v4",
    vk: "M5 8c.3 4 2.5 7 5.5 7h1v-2c1.8.2 2.5 2 4.2 2h2.1c-.4-1.4-1.4-2.4-2.8-3.1 1.3-1.4 2.1-2.7 2.5-3.9h-2.4c-.5 1.1-1.1 2-2.1 3V8h-2.2v4.7C9.8 12 9 10.3 8.5 8H5z",
    telegram: "M21 4L3 11l6 2 2 6 3-4 4 3 3-14zM9 13l8-6-6 8",
    pikabu: "M6 19V5h7.5c2.8 0 4.5 1.7 4.5 4.1s-1.7 4.1-4.5 4.1H10v5.8H6zM10 9v.9h3.1c.6 0 .9-.2.9-.7s-.3-.8-.9-.8H10z",
    close: "M6 6l12 12M18 6L6 18",
    copy: "M8 8h10v10H8zM5 5h10v3M5 5v10h3",
    lock: "M7 11V8a5 5 0 0110 0v3M6 11h12v9H6z",
    premium: "M4 17h16M6 17L5 7l4 4 3-6 3 6 4-4-1 10M8 21h8",
    target: "M12 5v3M12 16v3M5 12h3M16 12h3M8.5 8.5l2 2M15.5 8.5l-2 2M8.5 15.5l2-2M15.5 15.5l-2-2M12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z",
    rotateX: "M5 12c0-3.3 3.1-6 7-6 2.1 0 4 .8 5.3 2M17.3 8H14M17.3 8V4.7M19 12c0 3.3-3.1 6-7 6-2.1 0-4-.8-5.3-2M6.7 16H10M6.7 16v3.3M8 9l8 6M16 9l-8 6",
    rotateY: "M12 4c3.9 0 7 3.6 7 8s-3.1 8-7 8-7-3.6-7-8 3.1-8 7-8zM12 4v16M9 9l3 3 3-3",
    rotateZ: "M7 7a7.1 7.1 0 019.8-.2M17 7h-3.5M17 7V3.5M17 17a7.1 7.1 0 01-9.8.2M7 17h3.5M7 17v3.5M9 12h6",
    resetView: "M5 5h6v6H5zM13 5h6v6h-6zM5 13h6v6H5zM13 13h6v6h-6zM8 8h.01M16 8h.01M8 16h.01M16 16h.01",
    clearModel: "M7 7l10 10M17 7L7 17M4 12a8 8 0 1016 0 8 8 0 00-16 0z",
    camera: "M5 8h3l1.5-2h5L16 8h3v10H5zM12 11a3 3 0 100 6 3 3 0 000-6z",
  };
  return <svg className="launchSvgIcon" viewBox="0 0 24 24" aria-hidden="true"><path d={paths[type] || paths.cube} /></svg>;
}

function PremiumStatusControl({ currentUser, loading = false, onOpenPremium, onOpenApplication, className = "" }) {
  const [open, setOpen] = useState(false);
  const premiumActive = Boolean(currentUser?.premium_active);
  const limits = currentUser?.limits || {};
  const buttonClass = `premiumStatusControl ${premiumActive ? "active" : "inactive"} ${className}`.trim();

  if (!premiumActive) {
    return (
      <button className={`publicTopCta topCtaV8 premiumHeaderButtonV9 ${className}`.trim()} type="button" onClick={onOpenPremium} aria-label="Получить Премиум STL Master">
        {loading ? "Проверяем..." : "Получить Премиум"} <LaunchIcon type="premium" />
      </button>
    );
  }

  return (
    <div className="premiumStatusWrap">
      <button
        className={buttonClass}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`${premiumUntilLabel(currentUser)}. ${premiumTimeLabel(currentUser)}`}
      >
        <LaunchIcon type="premium" />
        <span>
          <b>Премиум активен</b>
          <small>{premiumTimeLabel(currentUser)}</small>
        </span>
      </button>
      {open && (
        <div className="premiumStatusPopover" role="dialog" aria-label="Статус Премиум">
          <strong>Тариф: Премиум</strong>
          <dl>
            <div><dt>Действует до</dt><dd>{currentUser.premium_expires_at ? formatDateRu(currentUser.premium_expires_at) : "Без ограничения срока"}</dd></div>
            <div><dt>Осталось</dt><dd>{premiumTimeLabel(currentUser)}</dd></div>
            <div><dt>Приоритет очереди</dt><dd>{limits.priority === "premium" ? "Повышенный" : "Обычный"}</dd></div>
            <div><dt>Максимальный файл</dt><dd>{limits.max_file_size_mb || 300} МБ</dd></div>
          </dl>
          <div>
            <button type="button" onClick={() => { setOpen(false); onOpenApplication?.(); }}>Открыть приложение</button>
            <button type="button" onClick={() => { setOpen(false); onOpenPremium?.(); }}>Управление доступом</button>
          </div>
        </div>
      )}
    </div>
  );
}

function StudioMockup() {
  const tools = [
    ["analyze", "Анализ", "Проверка модели"],
    ["repair", "Исправление", "AI-ремонт сетки"],
    ["split", "Разрез", "Разделение модели"],
    ["connectors", "Соединения", "Штифты, магниты"],
    ["shield", "Проверка печати", "Толщина, навесы"],
    ["analyze", "Оптимизация", "Уменьшение полигонов"],
    ["export", "Экспорт", "Сохранение файла"],
  ];
  const quickActions = ["Авто-исправление", "Заполнить отверстия", "Уплотнить сетку", "Оптимизировать"];
  return (
    <aside className="studioShellV8" aria-label="STL Master Studio mockup">
      <div className="studioTopbar studioTopbarV8">
        <strong><LaunchIcon type="logo" /> STL Master Studio</strong>
        <span>Dragon_Skull.stl</span>
        <div><em>100%</em><button type="button"><LaunchIcon type="export" /> Экспорт</button><span className="studioMenuDots">⋮</span></div>
      </div>
      <div className="studioBody studioBodyV8">
        <nav className="studioTools studioToolsV8" aria-label="Инструменты Studio">
          <small>ИНСТРУМЕНТЫ</small>
          {tools.map(([icon, title, text], index) => (
            <button className={index === 1 ? "active" : ""} type="button" key={title}>
              <LaunchIcon type={icon} />
              <span><b>{title}</b><em>{text}</em></span>
            </button>
          ))}
          <div className="studioToolFoot"><span>⚙</span><span>?</span><span>«</span></div>
        </nav>
        <section className="studioViewport studioViewportV8" aria-label="Viewport с черепом дракона">
          <div className="viewportSideRail">{["⌕", "↕", "⛓", "◎", "□", "⌁", "◉", "⊕"].map((item) => <span key={item}>{item}</span>)}</div>
          <svg className="sectionPlaneSvg" viewBox="0 0 100 100" aria-hidden="true" preserveAspectRatio="none">
            <polygon points="0,0 62,14 62,100 0,80" />
            <line x1="0" y1="0" x2="62" y2="14" />
            <line x1="0" y1="80" x2="62" y2="100" />
            <line x1="0" y1="0" x2="0" y2="80" />
            <line x1="62" y1="14" x2="62" y2="100" />
          </svg>
          <img className="studioSkull" src={dragonSkullPoster} alt="Большой череп дракона в STL Master Studio" />
          <svg className="sectionCutSvg" viewBox="0 0 10 100" aria-hidden="true" preserveAspectRatio="none">
            <line x1="5" y1="0" x2="5" y2="100" />
          </svg>
          <div className="axisGizmo viewportGizmo" aria-hidden="true">
            <i className="axisX"><span>X</span></i>
            <i className="axisY"><span>Y</span></i>
            <i className="axisZ"><span>Z</span></i>
            <b />
          </div>
          <div className="viewportBottomBar">{["repair", "cube", "split", "connectors", "shield", "export"].map((icon) => <button type="button" key={icon}><LaunchIcon type={icon} /></button>)}</div>
        </section>
        <aside className="studioInfo studioInfoV8">
          <h3>ИНФОРМАЦИЯ О МОДЕЛИ</h3>
          <dl>
            <div><dt>Треугольников</dt><dd>2 853 184</dd></div>
            <div><dt>Вершин</dt><dd>1 426 592</dd></div>
            <div><dt>Объём</dt><dd>312.7 см³</dd></div>
            <div><dt>Размер</dt><dd>201 × 112 × 96 мм</dd></div>
          </dl>
          <h3>ПРОВЕРКА МОДЕЛИ</h3>
          <ul className="studioChecks">
            <li><span className="bad" /> Ошибок <b>3</b></li>
            <li><span className="warn" /> Предупреждений <b>7</b></li>
            <li><span className="warn" /> Тонкие стены <b>12</b></li>
            <li><span className="warn" /> Открытые края <b>8</b></li>
          </ul>
          <button className="studioCheckButton" type="button">Запустить проверку</button>
          <h3>БЫСТРЫЕ ДЕЙСТВИЯ</h3>
          <div className="quickActions">{quickActions.map((item) => <button type="button" key={item}>{item}</button>)}</div>
        </aside>
      </div>
    </aside>
  );
}

function SectionHeader({ label, title, text, action }) {
  const labelMatch = typeof label === "string" ? label.match(/^(\d{2})(?:\s*\/\s*|\s+)(.+)$/) : null;
  return (
    <div className="launchSectionHeader">
      {label && (
        <p className="sectionKicker">
          {labelMatch ? (
            <>
              <span className="sectionKickerNumber">{labelMatch[1]}</span>
              <span className="sectionKickerDivider">/</span>
              <span className="sectionKickerLabel">{labelMatch[2]}</span>
            </>
          ) : label}
        </p>
      )}
      <div>
        <h2>{title}</h2>
        {text && <p>{text}</p>}
      </div>
      {action}
    </div>
  );
}

function HeroSection({ onOpenApplication }) {
  const openFeatures = () => {
    document.getElementById("features")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const benefits = [
    { icon: "gauge", title: "Быстро", text: "AI-исправление за секунды" },
    { icon: "shieldCheck", title: "Надёжно", text: "Точная подготовка к печати" },
    { icon: "sliders", title: "Удобно", text: "Интуитивный интерфейс" },
  ];
  const metrics = [
    ["rating", "4.9/5", "Рейтинг пользователей"],
    ["users", "100K+", "Активных пользователей"],
    ["cube", "1M+", "Обработанных моделей"],
    ["success", "99.9%", "Успешных обработок"],
    ["support", "24/7", "Поддержка пользователей"],
  ];
  const metricIconType = (icon) => (
    icon === "cube" ? "cube" :
    icon === "support" ? "analyze" :
    icon === "success" ? "check" :
    icon === "users" ? "connectors" :
    "shield"
  );

  return (
    <section className="launchHero heroV8 revealSection in-view" id="hero">
      <div className="heroCopy heroCopyV8">
        <UiBadge className="heroLabel heroLabelV8" variant="primary"><span /> ПРОФЕССИОНАЛЬНЫЙ ОНЛАЙН-РЕДАКТОР STL</UiBadge>
        <h1>
          <span className="heroTitleLine">Исправляйте, режьте</span>
          <span className="heroTitleLine">и готовьте модели</span>
          <span className="heroTitleLine">к <span className="heroTitleAccent">3D-печати</span></span>
        </h1>
        <p className="heroLead">Автоматическое исправление сетки, разрез на части,<br /> соединения, проверка на печать и многое другое.<br /> Всё в одном инструменте.</p>
        <div className="heroBenefits heroBenefitsV8">
          {benefits.map((benefit) => (
            <UiHeroCard
              key={benefit.title}
              icon={<LaunchIcon type={benefit.icon} />}
              text={benefit.text}
              title={benefit.title}
            />
          ))}
        </div>
        <div className="launchActions heroActionsV8">
          <UiButton className="primaryCta" type="button" onClick={onOpenApplication} aria-label="Загрузить STL в редактор STL Master"><LaunchIcon type="upload" /> Загрузить STL<span>Открыть редактор</span></UiButton>
          <UiButton className="secondaryCta" variant="secondary" type="button" onClick={openFeatures}><LaunchIcon type="analyze" /> Смотреть возможности<span>Все инструменты</span></UiButton>
        </div>
        <div className="formatRow formatRowV8"><span>Поддерживаемые форматы</span>{[".stl", ".obj", ".3mf", ".ply", ".amf", ".step", "+ ещё"].map((item) => <b key={item}>{item}</b>)}</div>
      </div>
      <StudioMockup />
      <div className="heroMetrics heroMetricsV8">
        {metrics.map(([icon, value, label]) => (
          <UiStatCard
            key={label}
            className={`heroMetricItem heroMetric-${icon}`}
            icon={<span className={`metricIcon metricIcon-${icon}`}><LaunchIcon type={metricIconType(icon)} /></span>}
            label={label}
            value={value}
          />
        ))}
      </div>
      <UiPanel className="browserNote browserNoteV8"><LaunchIcon type="lock" /><div><b>Работает прямо в браузере.</b><span>Ничего не нужно устанавливать. Ваши модели в безопасности.</span></div><i /></UiPanel>
    </section>
  );
}

function WorkflowIcon({ type }) {
  const icons = {
    upload: (
      <>
        <path d="M15 4H7a2 2 0 0 0-2 2v24a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V12z" />
        <path d="M15 4v8h8" />
        <path d="M16 27V17" />
        <path d="M11 22l5-5 5 5" />
      </>
    ),
    inspect: (
      <>
        <path d="M15 7l8 4.5v9L15 25l-8-4.5v-9z" />
        <path d="M7 11.5l8 4.5 8-4.5" />
        <path d="M15 16v9" />
        <circle cx="22" cy="24" r="5" />
        <path d="M26 28l4 4" />
      </>
    ),
    magic: (
      <>
        <path d="M8 28L27 9" />
        <path d="M23 7l4 4" />
        <path d="M9 7v5" />
        <path d="M6.5 9.5h5" />
        <path d="M27 22v5" />
        <path d="M24.5 24.5h5" />
        <path d="M16 4l1.5 3L21 8.5 17.5 10 16 13l-1.5-3L11 8.5 14.5 7z" />
      </>
    ),
    blocks: (
      <>
        <path d="M9 10l7-4 7 4-7 4z" />
        <path d="M9 10v8l7 4 7-4v-8" />
        <path d="M16 14v8" />
        <path d="M4 20l6-3.5 6 3.5-6 3.5z" />
        <path d="M22 20l6-3.5 6 3.5-6 3.5z" />
      </>
    ),
    shieldCheck: (
      <>
        <path d="M18 4l11 4v8c0 8-5 13-11 16C12 29 7 24 7 16V8z" />
        <path d="M12 17l4 4 8-9" />
      </>
    ),
    export: (
      <>
        <path d="M9 9H6a2 2 0 0 0-2 2v17a2 2 0 0 0 2 2h17a2 2 0 0 0 2-2v-3" />
        <path d="M19 5h10v10" />
        <path d="M14 20L29 5" />
      </>
    ),
  };
  return <svg viewBox="0 0 36 36" aria-hidden="true">{icons[type] || icons.upload}</svg>;
}

function WorkflowSection() {
  return (
    <section className="publicSection workflowSection revealSection" id="workflow">
      <div className="sectionEyebrow workflowEyebrow">
        <span className="sectionNumber">02</span>
        <span className="sectionLabel">WORKFLOW / КАК ЭТО РАБОТАЕТ</span>
      </div>
      <div className="workflowIntro">
        <h2>Весь процесс в одном редакторе</h2>
        <p>От загрузки STL до готовой модели к печати</p>
      </div>
      <span className="workflowTrack" aria-hidden="true" />
      <div className="workflowGrid">
        {publicWorkflowSteps.map((step) => (
          <article className={`workflowCard workflowCard-${step.number}`} key={step.number}>
            <div className="workflowCardTitle">
              <span className="workflowStepNumber">{step.number}</span>
              <h3>{step.title}</h3>
            </div>
            <p className="workflowDescription">{step.text}</p>
            <div className="workflowIcon">
              <WorkflowIcon type={step.icon} />
            </div>
            <span className="workflowArrow" aria-hidden="true" />
          </article>
        ))}
      </div>
    </section>
  );
}

function ConnectionCard({ item }) {
  return (
    <article className={`connectionCard connectionCard--${item.id}`}>
      <div className="connectionCardTopline">
        <span className="connectionCardNumber">{item.number}</span>
        <span className="connectionCardMode">{item.id}</span>
      </div>
      <div className="connectionCardContent">
        <h3>{item.title}</h3>
        <p>{item.description}</p>
      </div>
      <div className="connectionVisual">
        <img
          src={item.image}
          alt={item.alt}
          loading="lazy"
          decoding="async"
          draggable="false"
        />
      </div>
      <p className="connectionCaption">{item.meta}</p>
      <span className="connectionCardAccent" aria-hidden="true" />
    </article>
  );
}

function ConnectionParameters() {
  return (
    <aside className="connectionParameters" aria-label="Настраиваемые параметры соединений">
      <div className="connectionParametersIntro">
        <span>CAD параметры</span>
        <h3>Полностью настраиваемые параметры</h3>
        <p>Настройте соединение под материал, точность принтера и особенности конкретной модели.</p>
      </div>
      <div className="connectionParameterGrid">
        {connectionParameters.map((item) => (
          <div className="connectionParameterItem" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <i aria-hidden="true" />
          </div>
        ))}
      </div>
    </aside>
  );
}

function ConnectorsSection({ onStartCut }) {
  return (
    <section className="publicSection connectorsSection revealSection in-view" id="connectors">
      <div className="sectionEyebrow connectionsEyebrow">
        <span className="sectionNumber">03</span>
        <span className="sectionLabel">СОЕДИНЕНИЯ</span>
      </div>
      <div className="connectionsHeading">
        <h2>Разделите модель именно так, как нужно вам</h2>
        <p>STL Master поддерживает несколько способов подготовки разреза и соединения деталей. Выберите подходящий вариант для склейки, точного позиционирования, разборной конструкции или установки магнитов.</p>
      </div>
      <div className="connectionsGrid">
        {connectionModes.map((item) => <ConnectionCard item={item} key={item.id} />)}
      </div>
      <ConnectionParameters />
      <div className="connectionsCta">
        <div>
          <span>Split Studio</span>
          <h3>Подготовьте модель к сборке за несколько минут</h3>
          <p>Загрузите STL, выберите плоскость разреза и настройте подходящий тип соединения.</p>
        </div>
        <button className="connectionsCtaButton" type="button" onClick={onStartCut}>
          Попробовать разрезание
          <LaunchIcon type="flash" />
        </button>
      </div>
    </section>
  );
}

const demoModelUrls = {
  problematic: "/demo-models/stlmaster_demo_model_problematic.stl",
  cleanHigh: "/demo-models/stlmaster_demo_model_clean_high.stl",
  cleanLow: "/demo-models/stlmaster_demo_model_clean_low.stl",
};

const demoModelMetrics = {
  problematicTriangles: 28828,
  cleanHighTriangles: 28772,
  cleanLowTriangles: 6788,
  size: "93.02 × 76.76 × 100 мм",
};

const polygonReductionPercent = Math.round((1 - demoModelMetrics.cleanLowTriangles / demoModelMetrics.cleanHighTriangles) * 100);
const marketingGeometryCache = new Map();

function formatNumber(value) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

function getPrefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
}

function canUseWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(window.WebGLRenderingContext && (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")));
  } catch {
    return false;
  }
}

function loadMarketingGeometry(modelUrl) {
  if (!marketingGeometryCache.has(modelUrl)) {
    marketingGeometryCache.set(modelUrl, fetch(modelUrl).then((response) => {
      if (!response.ok) throw new Error(`Failed to load ${modelUrl}`);
      return response.arrayBuffer();
    }).then((buffer) => {
      const geometry = new STLLoader().parse(buffer);
      geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      return geometry;
    }));
  }
  return marketingGeometryCache.get(modelUrl);
}

function disposeMarketingObject(object) {
  object?.traverse?.((child) => {
    if (child.geometry && !child.geometry.userData?.cachedMarketingGeometry) {
      child.geometry.dispose();
    }
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.filter(Boolean).forEach((material) => material.dispose?.());
  });
}

function createMarketingMaterial({ variant = "clean", transparent = false, opacity = 1, wireframe = false } = {}) {
  const color = variant === "problematic" ? 0xd6d1ca : variant === "low" ? 0xc4ccd3 : 0xd9dde2;
  return new THREE.MeshStandardMaterial({
    color,
    metalness: 0.04,
    roughness: 0.72,
    transparent,
    opacity,
    wireframe,
  });
}

function normalizeMarketingMesh(geometry, variant) {
  const cloned = geometry.clone();
  cloned.computeBoundingBox();
  const box = cloned.boundingBox;
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const scale = 2.4 / Math.max(size.x, size.y, size.z, 1);
  cloned.translate(-center.x, -center.y, -center.z);
  cloned.scale(scale, scale, scale);
  cloned.computeVertexNormals();
  cloned.computeBoundingBox();
  const mesh = new THREE.Mesh(cloned, createMarketingMaterial({ variant }));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function addMarketingGrid(scene) {
  const grid = new THREE.GridHelper(4.8, 24, 0x35d7ff, 0x1d3449);
  grid.position.y = -1.28;
  grid.material.transparent = true;
  grid.material.opacity = 0.34;
  scene.add(grid);
}

function addPrintBed(scene) {
  const bed = new THREE.Mesh(
    new THREE.PlaneGeometry(4.6, 4.6),
    new THREE.MeshStandardMaterial({ color: 0x07111d, roughness: 0.84, metalness: 0.02, transparent: true, opacity: 0.68 }),
  );
  bed.rotation.x = -Math.PI / 2;
  bed.position.y = -1.29;
  scene.add(bed);
  addMarketingGrid(scene);
}

function addIssueMarkers(group, mode = "analysis") {
  const red = new THREE.MeshBasicMaterial({ color: 0xff5f78 });
  const cyan = new THREE.MeshBasicMaterial({ color: 0x35d7ff });
  const markerData = [
    { p: [-0.72, 0.38, 0.42], r: 0.045, material: red },
    { p: [0.36, 0.64, -0.16], r: 0.035, material: red },
    { p: [0.74, -0.12, 0.36], r: 0.032, material: red },
    { p: [-0.26, -0.58, -0.58], r: 0.03, material: red },
    { p: [0.08, 0.10, 0.74], r: 0.026, material: cyan },
  ];
  markerData.forEach(({ p, r, material }) => {
    const marker = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 12), material);
    marker.position.set(...p);
    marker.renderOrder = 4;
    group.add(marker);
  });
  if (mode === "cleanup") {
    const plate = new THREE.Mesh(
      new THREE.BoxGeometry(0.42, 0.035, 0.28),
      new THREE.MeshBasicMaterial({ color: 0xff5f78, transparent: true, opacity: 0.72 }),
    );
    plate.position.set(0.92, -0.2, -0.42);
    plate.rotation.set(0.2, 0.6, -0.18);
    group.add(plate);
  }
}

function addSplitPlane(group, axis = "x") {
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(1.18, 2.55),
    new THREE.MeshBasicMaterial({ color: 0x35d7ff, transparent: true, opacity: 0.13, side: THREE.DoubleSide, depthWrite: false }),
  );
  plane.renderOrder = 3;
  if (axis === "y") plane.rotation.x = Math.PI / 2;
  if (axis === "z") plane.rotation.y = Math.PI / 2;
  if (axis === "x") plane.rotation.y = -0.12;
  group.add(plane);

  const line = new THREE.Mesh(
    new THREE.BoxGeometry(0.018, 2.6, 0.018),
    new THREE.MeshBasicMaterial({ color: 0x35d7ff }),
  );
  line.renderOrder = 4;
  group.add(line);
}

function addConnectorPreview(group, mode = "pins") {
  const color = mode === "magnets" ? 0x78ffc8 : mode === "lock" ? 0x8b5cf6 : 0x35d7ff;
  const material = new THREE.MeshStandardMaterial({ color, roughness: 0.46, metalness: 0.08 });
  const positions = [-0.36, 0, 0.36];
  positions.forEach((y) => {
    const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.86, 28), material);
    pin.rotation.z = Math.PI / 2;
    pin.position.set(0, y, 0.52);
    group.add(pin);
  });
  if (mode === "glue") {
    const seam = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.35, 1.36), new THREE.MeshBasicMaterial({ color: 0x35d7ff, transparent: true, opacity: 0.25 }));
    group.add(seam);
  }
}

function StlMarketingViewer({
  modelUrl,
  secondaryModelUrl,
  variant = "clean",
  mode = "analysis",
  showGrid = true,
  showWireframe = false,
  showIssueMarkers = false,
  showSplitPlane = false,
  showPrintBed = false,
  showChangeOverlay = false,
  autoRotate = false,
  cameraPreset = "hero",
  interactive = false,
  connectorMode = "pins",
  splitAxis = "x",
  className = "",
  ariaLabel = "3D-превью STL Master Demo Core",
}) {
  const mountRef = useRef(null);
  const groupRef = useRef(null);
  const frameRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [isNearViewport, setIsNearViewport] = useState(false);
  const [fallback, setFallback] = useState("");

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setIsNearViewport(true);
    }, { rootMargin: "420px 0px" });
    observer.observe(mount);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !isNearViewport) return undefined;
    if (!canUseWebGL()) {
      setFallback("3D-превью недоступно в этом браузере");
      return undefined;
    }

    let cancelled = false;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    const cameraPositions = {
      hero: [3.4, 2.1, 3.55],
      compare: [3.2, 1.9, 3.35],
      top: [2.65, 3.0, 2.65],
    };
    camera.position.set(...(cameraPositions[cameraPreset] || cameraPositions.hero));

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, window.innerWidth < 720 ? 1.5 : 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enableRotate = interactive;
    controls.enablePan = false;
    controls.enableZoom = interactive;
    controls.autoRotate = false;
    controls.target.set(0, 0, 0);

    scene.add(new THREE.HemisphereLight(0xdde9f2, 0x101827, 1.75));
    const key = new THREE.DirectionalLight(0xffffff, 2.45);
    key.position.set(3.2, 4.8, 3.1);
    scene.add(key);
    const cyan = new THREE.DirectionalLight(0x35d7ff, 1.12);
    cyan.position.set(-3.2, 2.2, -2.7);
    scene.add(cyan);
    const violet = new THREE.DirectionalLight(0x8b5cf6, 0.68);
    violet.position.set(2.6, 1.7, -3.4);
    scene.add(violet);

    if (showPrintBed) addPrintBed(scene);
    else if (showGrid) addMarketingGrid(scene);

    const resize = () => {
      const width = Math.max(mount.clientWidth || 1, 1);
      const height = Math.max(mount.clientHeight || 1, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);

    const buildScene = async () => {
      setStatus("loading");
      try {
        const root = new THREE.Group();
        const geometry = await loadMarketingGeometry(modelUrl);
        if (cancelled) return;

        if (showChangeOverlay && secondaryModelUrl) {
          const secondaryGeometry = await loadMarketingGeometry(secondaryModelUrl);
          if (cancelled) return;
          const ghost = normalizeMarketingMesh(secondaryGeometry, "problematic");
          ghost.material.transparent = true;
          ghost.material.opacity = 0.22;
          ghost.material.depthWrite = false;
          ghost.position.x = -0.02;
          root.add(ghost);
        }

        const mesh = normalizeMarketingMesh(geometry, variant);
        if (mode === "orientation") {
          mesh.rotation.z = -0.22;
          mesh.position.y = -0.04;
        }
        if (mode === "split" || mode === "connectors") {
          mesh.scale.x = 0.98;
        }
        root.add(mesh);

        if (showWireframe) {
          const wire = normalizeMarketingMesh(geometry, "low");
          wire.material = new THREE.MeshBasicMaterial({ color: mode === "optimization" ? 0x78ffc8 : 0x35d7ff, wireframe: true, transparent: true, opacity: 0.32 });
          wire.scale.multiplyScalar(1.004);
          root.add(wire);
        }
        if (showIssueMarkers) addIssueMarkers(root, mode);
        if (showSplitPlane) addSplitPlane(root, splitAxis);
        if (mode === "connectors") addConnectorPreview(root, connectorMode);
        if (mode === "export") {
          const halo = new THREE.Mesh(new THREE.SphereGeometry(1.42, 48, 24), new THREE.MeshBasicMaterial({ color: 0x35d7ff, transparent: true, opacity: 0.035, wireframe: true }));
          root.add(halo);
        }

        scene.add(root);
        groupRef.current = root;
        setStatus("ready");
      } catch {
        setFallback("3D-превью недоступно в этом браузере");
        setStatus("error");
      }
    };

    buildScene();
    const reducedMotion = getPrefersReducedMotion();
    const animate = () => {
      if (!cancelled) {
        if (groupRef.current && autoRotate && !reducedMotion && !interactive) {
          groupRef.current.rotation.y += 0.004;
        }
        controls.update();
        renderer.render(scene, camera);
        frameRef.current = window.requestAnimationFrame(animate);
      }
    };
    animate();

    return () => {
      cancelled = true;
      resizeObserver.disconnect();
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current);
      controls.dispose();
      disposeMarketingObject(scene);
      renderer.dispose();
      renderer.domElement.remove();
      groupRef.current = null;
    };
  }, [modelUrl, secondaryModelUrl, variant, mode, showGrid, showWireframe, showIssueMarkers, showSplitPlane, showPrintBed, showChangeOverlay, autoRotate, cameraPreset, interactive, connectorMode, splitAxis, isNearViewport]);

  return (
    <div className={`stlMarketingViewer ${className}`} aria-label={ariaLabel} role="img">
      <div ref={mountRef} className="stlMarketingCanvas" />
      {status !== "ready" && !fallback && <div className="stlMarketingLoader"><span />Загружаем STL Master Demo Core</div>}
      {fallback && <div className="stlMarketingFallback"><b>{fallback}</b><span>Тексты, показатели и навигация остаются доступны без WebGL.</span></div>}
    </div>
  );
}

const compareBeforeProblems = [
  "Открытый участок поверхности",
  "Перевёрнутые нормали",
  "Шип-артефакт",
  "Плавающий островок",
  "Лишняя отдельная геометрия",
];

const compareAfterFixes = [
  "Повреждённая область восстановлена",
  "Локальные артефакты удалены",
  "Модель снова замкнута",
  "Геометрия проверена",
  "Результат доступен для дальнейшей подготовки",
];

const comparePrimaryMetrics = [
  { label: "Треугольники", before: "28 828", after: "28 772" },
  { label: "Замкнутая сетка", before: "Нет", after: "Да" },
  { label: "Артефакты", before: "Обнаружены", after: "Удалены" },
  { label: "Проверка геометрии", before: "Требуется", after: "Выполнена" },
];

function BeforeAfterShowcase() {
  const [position, setPosition] = useState(50);
  const stageRef = useRef(null);
  const updatePosition = (event) => {
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPosition(Math.min(84, Math.max(16, Math.round(((event.clientX - rect.left) / rect.width) * 100))));
  };
  const handleSliderKeyDown = (event) => {
    const keyMap = {
      ArrowLeft: -2,
      ArrowDown: -2,
      ArrowRight: 2,
      ArrowUp: 2,
    };
    if (event.key === "Home") {
      event.preventDefault();
      setPosition(16);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      setPosition(84);
      return;
    }
    if (keyMap[event.key]) {
      event.preventDefault();
      setPosition((value) => Math.min(84, Math.max(16, value + keyMap[event.key])));
    }
  };

  return (
    <section className="publicSection beforeAfterShowcase demoCompareSection revealSection in-view" id="compare">
      <SectionHeader
        label={<><span className="sectionNumber">04</span><span className="sectionLabel">ДО И ПОСЛЕ</span></>}
        title="Посмотрите, как меняется модель после обработки"
        text="Сравните исходную STL-модель с исправленной версией. STL Master находит основные дефекты сетки, удаляет локальные артефакты и помогает подготовить геометрию к дальнейшей проверке и печати."
        action={<a className="sectionGhostLink compact compareMoreLink" href="#features">Как это работает <span>›</span></a>}
      />
      <div className="demoCompareCard">
        <div className="demoCompareWorkbench">
          <aside className="demoComparePanel demoComparePanelBefore">
            <b>ДО</b>
            <h3>Исходная модель</h3>
            <strong>Обнаружено несколько типов проблем:</strong>
            <ul>{compareBeforeProblems.map((item) => <li key={item}>{item}</li>)}</ul>
          </aside>
          <div className="demoCompareStageShell">
            <p className="compareDragHint">Перетащите для сравнения</p>
            <div
              className="beforeAfterStage demoBeforeAfterStage"
              ref={stageRef}
              onPointerDown={(event) => { updatePosition(event); event.currentTarget.setPointerCapture?.(event.pointerId); }}
              onPointerMove={(event) => { if (event.buttons === 1) updatePosition(event); }}
            >
              <span className="compareSideBadge compareSideBadge-before">ДО · problematic STL</span>
              <span className="compareSideBadge compareSideBadge-after">ПОСЛЕ · clean high STL</span>
              <StlMarketingViewer
                modelUrl={demoModelUrls.problematic}
                variant="problematic"
                mode="analysis"
                showIssueMarkers
                showWireframe
                cameraPreset="compare"
                className="compareViewer compareViewerBefore"
                ariaLabel="Проблемная версия STL Master Demo Core"
              />
              <div className="compareAfterClip" style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}>
                <StlMarketingViewer
                  modelUrl={demoModelUrls.cleanHigh}
                  variant="clean"
                  mode="repair"
                  showGrid
                  cameraPreset="compare"
                  className="compareViewer compareViewerAfter"
                  ariaLabel="Исправленная версия STL Master Demo Core"
                />
              </div>
              <div className="beforeAfterDivider" style={{ left: `${position}%` }}><span>↔</span></div>
              <input
                aria-label="Перетащите для сравнения исходной и исправленной STL-модели"
                aria-valuemin="16"
                aria-valuemax="84"
                aria-valuenow={position}
                className="beforeAfterSlider"
                role="slider"
                type="range"
                min="16"
                max="84"
                value={position}
                onChange={(event) => setPosition(Number(event.target.value))}
                onKeyDown={handleSliderKeyDown}
              />
            </div>
          </div>
          <aside className="demoComparePanel demoComparePanelAfter">
            <b>ПОСЛЕ</b>
            <h3>Исправленная модель</h3>
            <strong>Основные дефекты исправлены</strong>
            <ul>{compareAfterFixes.map((item) => <li key={item}>{item}</li>)}</ul>
          </aside>
        </div>
        <div className="compareReadyStatus" role="status">
          <span aria-hidden="true" />
          <div>
            <strong>Проверено и подготовлено к печати</strong>
            <p>Демонстрационный сценарий обработки STL Master Demo Core.</p>
          </div>
        </div>
        <div className="compareMetrics demoCompareMetrics">
          {comparePrimaryMetrics.map((item) => (
            <article key={item.label}>
              <span>{item.label}</span>
              <div><b>{item.before}</b><i>→</i><b>{item.after}</b></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

const workflowSteps = [
  {
    id: "analysis",
    title: "Анализ модели",
    status: "Диагностика",
    modelUrl: demoModelUrls.problematic,
    variant: "problematic",
    mode: "analysis",
    showWireframe: true,
    showIssueMarkers: true,
    titleText: "Проверка геометрии",
    description: "STL Master анализирует сетку и отмечает участки, которые требуют внимания.",
    facts: ["28 828 треугольников", "Сетка не замкнута", "Обнаружены локальные артефакты", "Рекомендуется ремонт"],
    tags: ["STL", "analysis", "artifact map"],
  },
  {
    id: "repair",
    title: "Ремонт сетки",
    status: "BETA",
    modelUrl: demoModelUrls.cleanHigh,
    secondaryModelUrl: demoModelUrls.problematic,
    variant: "clean",
    mode: "repair",
    showChangeOverlay: true,
    titleText: "Автоматический ремонт STL",
    description: "Исправляет основные дефекты сетки и формирует обновлённую версию модели вместе с отчётом.",
    facts: ["problematic → clean_high", "28 772 треугольника", "Замкнутая сетка", "Отчёт по изменениям"],
    tags: ["BETA", "repair", "report"],
  },
  {
    id: "cleanup",
    title: "Очистка артефактов",
    status: "BETA",
    modelUrl: demoModelUrls.problematic,
    secondaryModelUrl: demoModelUrls.cleanHigh,
    variant: "problematic",
    mode: "cleanup",
    showIssueMarkers: true,
    showChangeOverlay: true,
    titleText: "Очистка AI-моделей",
    description: "Помогает находить подозрительные выступы, мелкие островки и локальные дефекты моделей, созданных генераторами.",
    facts: ["Шип-артефакт", "Плавающий островок", "Отдельная пластина", "Доступно выборочное сглаживание области"],
    tags: ["BETA", "cleanup", "local smoothing"],
  },
  {
    id: "optimization",
    title: "Оптимизация",
    status: `-${polygonReductionPercent}%`,
    modelUrl: demoModelUrls.cleanLow,
    secondaryModelUrl: demoModelUrls.cleanHigh,
    variant: "low",
    mode: "optimization",
    showWireframe: true,
    showChangeOverlay: true,
    titleText: "Уменьшение веса модели",
    description: "Снижает количество полигонов и размер модели, сохраняя её узнаваемую форму настолько, насколько позволяет исходная геометрия.",
    facts: [`${formatNumber(demoModelMetrics.cleanHighTriangles)} → ${formatNumber(demoModelMetrics.cleanLowTriangles)} треугольников`, `Снижение примерно на ${polygonReductionPercent}%`, "Одинаковая камера", "Сохранена форма Demo Core"],
    tags: ["low poly", "wireframe", "STL"],
  },
  {
    id: "split",
    title: "Разрез",
    status: "X/Y/Z",
    modelUrl: demoModelUrls.cleanHigh,
    variant: "clean",
    mode: "split",
    showSplitPlane: true,
    titleText: "Разрез модели на части",
    description: "Разделение по выбранной оси на 2–4 части с настройкой положения плоскости.",
    facts: ["Виртуальная плоскость", "Оси X / Y / Z", "2–4 части", "Параметры перед обработкой"],
    tags: ["split plane", "preview", "axis"],
    link: ["Подробнее о соединениях", "#connectors"],
  },
  {
    id: "connectors",
    title: "Соединения",
    status: "Pins",
    modelUrl: demoModelUrls.cleanHigh,
    variant: "clean",
    mode: "connectors",
    showSplitPlane: true,
    titleText: "Соединения для сборки",
    description: "Показывает понятный предпросмотр разреза и режим штифтов. В приложении параметры соединения настраиваются перед обработкой.",
    facts: ["Под склейку", "Штифты", "Магниты", "Базовый замок"],
    tags: ["pins", "magnets", "lock"],
    link: ["Перейти к секции 03", "#connectors"],
  },
  {
    id: "orientation",
    title: "Ориентация",
    status: "Print bed",
    modelUrl: demoModelUrls.cleanHigh,
    variant: "clean",
    mode: "orientation",
    showPrintBed: true,
    titleText: "Ориентация под печать",
    description: "Анализирует положение модели и помогает установить её на виртуальный печатный стол.",
    facts: ["Печатный стол", "Предпросмотр поворота", demoModelMetrics.size, "Положение перед экспортом"],
    tags: ["bed", "orientation", "preview"],
  },
  {
    id: "export",
    title: "Экспорт",
    status: "STL ZIP JSON TXT",
    modelUrl: demoModelUrls.cleanHigh,
    variant: "clean",
    mode: "export",
    titleText: "Результаты и отчёты",
    description: "Скачивайте обработанные STL-файлы, ZIP-пакет и технические отчёты по этапам обработки.",
    facts: ["stlmaster_demo_model_clean_high.stl", "analysis.json", "print_report.txt", "result_package.zip"],
    tags: ["STL", "ZIP", "JSON", "TXT"],
  },
];

function featureToolIconType(id) {
  const icons = {
    analysis: "inspect",
    repair: "magic",
    cleanup: "magic",
    optimization: "blocks",
    split: "blocks",
    connectors: "blocks",
    orientation: "shieldCheck",
    export: "export",
  };
  return icons[id] || "inspect";
}

function FeaturesSection({ onStartUpload }) {
  const [activeId, setActiveId] = useState(workflowSteps[0].id);
  const [connectorMode, setConnectorMode] = useState("pins");
  const [splitAxis, setSplitAxis] = useState("x");
  const activeIndex = workflowSteps.findIndex((step) => step.id === activeId);
  const activeStep = workflowSteps[activeIndex] || workflowSteps[0];
  const selectStep = (id) => setActiveId(id);
  const handleStepKey = (event) => {
    if (!["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(event.key)) return;
    event.preventDefault();
    const direction = event.key === "ArrowDown" || event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (activeIndex + direction + workflowSteps.length) % workflowSteps.length;
    setActiveId(workflowSteps[nextIndex].id);
  };

  return (
    <section className="publicSection keyFeaturesSection demoWorkflowSection featuresToolSection revealSection in-view" id="features">
      <SectionHeader
        label={<><span className="sectionNumber">05</span><span className="sectionLabel">ВОЗМОЖНОСТИ</span></>}
        title="Весь процесс подготовки STL — в одном приложении"
        text="Загрузите модель, проверьте сетку, исправьте основные дефекты, оптимизируйте геометрию, подготовьте разрез и скачайте результаты вместе с техническими отчётами."
      />
      <p className="workflowBridge">Все показанные выше изменения выполняются последовательным набором инструментов STL Master.</p>
      <div className="demoWorkflowShell featuresToolShell">
        <nav className="workflowStepNav featuresToolNav" aria-label="Инструменты STL Master" onKeyDown={handleStepKey}>
          {workflowSteps.map((step) => (
            <button
              type="button"
              key={step.id}
              className={step.id === activeStep.id ? "active" : ""}
              aria-current={step.id === activeStep.id ? "step" : undefined}
              onClick={() => selectStep(step.id)}
            >
              <span className="featureToolIcon"><WorkflowIcon type={featureToolIconType(step.id)} /></span>
              <strong>{step.title}</strong>
              <em>{step.status}</em>
            </button>
          ))}
        </nav>
        <div className="workflowDemoStage featuresToolStage">
          <StlMarketingViewer
            modelUrl={activeStep.modelUrl}
            secondaryModelUrl={activeStep.secondaryModelUrl}
            variant={activeStep.variant}
            mode={activeStep.mode}
            showGrid={!activeStep.showPrintBed}
            showWireframe={activeStep.showWireframe}
            showIssueMarkers={activeStep.showIssueMarkers}
            showSplitPlane={activeStep.showSplitPlane}
            showPrintBed={activeStep.showPrintBed}
            showChangeOverlay={activeStep.showChangeOverlay}
            autoRotate
            cameraPreset={activeStep.mode === "orientation" ? "top" : "hero"}
            interactive
            connectorMode={connectorMode}
            splitAxis={splitAxis}
            className="workflowStlViewer"
            ariaLabel={`Этап ${activeIndex + 1}: ${activeStep.title}`}
          />
          {(activeStep.id === "split" || activeStep.id === "connectors") && (
            <div className="workflowToggleRail" aria-label={activeStep.id === "split" ? "Ось разреза" : "Тип соединения"}>
              {activeStep.id === "split" ? ["x", "y", "z"].map((axis) => (
                <button type="button" key={axis} className={splitAxis === axis ? "active" : ""} onClick={() => setSplitAxis(axis)}>{axis.toUpperCase()}</button>
              )) : [["glue", "Под склейку"], ["pins", "Штифты"], ["magnets", "Магниты"], ["lock", "Базовый замок"]].map(([id, label]) => (
                <button type="button" key={id} className={connectorMode === id ? "active" : ""} onClick={() => setConnectorMode(id)}>{label}</button>
              ))}
            </div>
          )}
          {activeStep.id === "export" && (
            <div className="workflowFilePanel" aria-label="Файлы результата">
              {["stlmaster_demo_model_clean_high.stl", "analysis.json", "print_report.txt", "manifest.json", "result_package.zip"].map((file) => <span key={file}>{file}</span>)}
            </div>
          )}
          <aside className="workflowInfoPanel featuresToolInfoPanel">
            <span>{activeStep.status}</span>
            <h3>{activeStep.titleText}</h3>
            <p>{activeStep.description}</p>
            <ul>{activeStep.facts.map((fact) => <li key={fact}>{fact}</li>)}</ul>
            <div>{activeStep.tags.map((tag) => <b key={tag}>{tag}</b>)}</div>
            {activeStep.link && <a href={activeStep.link[1]}>{activeStep.link[0]} <span>›</span></a>}
          </aside>
        </div>
      </div>
      <div className="featuresCtaPanel demoWorkflowCta featuresToolCta">
        <div>
          <span>STL Master pipeline</span>
          <h3>Подготовьте свою STL-модель</h3>
          <p>Загрузите файл, выберите необходимые операции и получите обработанную модель вместе с отчётами.</p>
        </div>
        <div className="featuresCtaActions">
          <button className="featuresPrimaryCta" type="button" onClick={onStartUpload}>
            <LaunchIcon type="upload" />
            Загрузить STL
          </button>
          <a className="featuresSecondaryLink" href="#compare">Сравнить до и после</a>
        </div>
      </div>
    </section>
  );
}

function ModalArtScene() {
  return (
    <div className="modalArtScene" aria-hidden="true">
      <div className="modalMiniWindow">
        <span className="modalMiniTop" />
        <span className="modalMiniSidebar" />
        <span className="modalMiniViewport">
          <span className="modalMiniModel" />
          <span className="modalMiniPlane" />
          <span className="modalMiniPoint pointA" />
          <span className="modalMiniPoint pointB" />
        </span>
      </div>
      <div className="modalAccessCard">
        <span>Access</span>
        <b>STL Master</b>
        <i />
      </div>
    </div>
  );
}

function DemoStudioPreview() {
  return (
    <div className="demoStudioPreview" aria-hidden="true">
      <div className="demoStudioTop"><span /><span /><span /><b>Dragon_Skull.stl</b></div>
      <div className="demoStudioGrid">
        <aside>{["Анализ", "Разрез", "Соединения", "Экспорт"].map((item) => <span key={item}>{item}</span>)}</aside>
        <section>
          <img src={dragonSkullPoster} alt="" loading="lazy" />
          <span className="demoCutPlane" />
          <span className="demoConnector one" />
          <span className="demoConnector two" />
        </section>
      </div>
    </div>
  );
}

function PricingComparison({ rows }) {
  return (
    <div className="premiumComparePanel" aria-label="Сравнение бесплатного режима и Premium">
      <div className="premiumCompareHeader">
        <span>Возможность</span>
        <span>Бесплатно</span>
        <span>Premium</span>
      </div>
      <div className="premiumCompareRows">
        {rows.map((row) => (
          <article className={row.accent ? "premiumCompareRow accent" : "premiumCompareRow"} key={row.feature}>
            <h3>{row.feature}</h3>
            <span>{row.free}</span>
            <strong>{row.premium}</strong>
          </article>
        ))}
      </div>
    </div>
  );
}

function PremiumPlanCard({ onPremium }) {
  return (
    <article className="premiumPricingCard">
      <div className="premiumCardTop">
        <span className="premiumBadge">{pricingPlan.badge}</span>
        <span className="premiumMark" aria-hidden="true"><LaunchIcon type="premium" /></span>
      </div>
      <h3>{pricingPlan.title}</h3>
      <p>{pricingPlan.subtitle}</p>
      <ul>
        {pricingPlan.benefits.map((item) => <li key={item}>{item}</li>)}
      </ul>
      <div className="premiumRequestPrice">
        <strong>{pricingPlan.priceLabel}</strong>
        <span>{pricingPlan.priceNote}</span>
      </div>
      <button className="premiumPrimaryButton" type="button" onClick={onPremium} aria-label="Подключить STL Master Premium">
        {pricingPlan.cta} <LaunchIcon type="flash" />
      </button>
      <small>{pricingPlan.footnote}</small>
    </article>
  );
}

function PricingTrustBar() {
  return (
    <div className="pricingTrustBar">
      {pricingTrustItems.map(([title, text]) => (
        <article key={title}>
          <span aria-hidden="true"><LaunchIcon type="check" /></span>
          <div>
            <strong>{title}</strong>
            <p>{text}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function PremiumShowcase({ onPremium, featureFlags = DEFAULT_FEATURE_FLAGS }) {
  const rows = buildPricingComparison(featureFlags);
  return (
    <section className="publicSection premiumShowcase revealSection" id="premium">
      <SectionHeader
        label="06 / ТАРИФЫ"
        title="Выберите подходящий режим работы"
        text="Начните с бесплатного доступа и подключите Premium, когда потребуются увеличенные лимиты, повышенный приоритет и регулярная обработка тяжёлых STL."
      />
      <div className="premiumFrame">
        <PremiumPlanCard onPremium={onPremium} />
        <div className="premiumCompareWrap">
          <div>
            <span className="premiumCompareEyebrow">Free / Premium</span>
            <h3>Разница в лимитах и очереди</h3>
            <p>Оба режима используют один редактор. Premium не открывает неподтверждённые форматы или оплату, а даёт больше ресурсов обработки и повышенный приоритет.</p>
          </div>
          <PricingComparison rows={rows} />
        </div>
      </div>
      <PricingTrustBar />
    </section>
  );
}

function FAQSection() {
  const [openId, setOpenId] = useState(faqItems[0]?.id || "");
  const [activeCategory, setActiveCategory] = useState("Все");
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const filteredItems = faqItems.filter((item) => {
    const matchesCategory = activeCategory === "Все" || item.category === activeCategory;
    const matchesQuery = !normalizedQuery || `${item.question} ${item.answer} ${item.category}`.toLowerCase().includes(normalizedQuery);
    return matchesCategory && matchesQuery;
  });
  const clearSearch = () => {
    setQuery("");
    setActiveCategory("Все");
  };
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  };

  return (
    <section className="publicSection faqSection revealSection" id="faq">
      <SectionHeader
        label="07 / FAQ"
        title="Ответы на частые вопросы"
        text="Коротко о форматах, обработке моделей, результатах, ограничениях и поддержке STL Master."
        action={<a className="faqHeaderSupport" href={STL_MASTER_SUPPORT_URL} target="_blank" rel="noopener noreferrer">Не нашли нужный ответ? Напишите нам во ВКонтакте</a>}
      />
      <div className="faqLayout">
        <aside className="faqIntroCard">
          <span className="faqIntroBadge">FAQ</span>
          <h3>Перед загрузкой STL</h3>
          <p>Выберите тему или найдите ответ по ключевым словам. Вопросы основаны на текущих возможностях проекта и beta-ограничениях.</p>
          <div className="faqCategoryList" aria-label="Категории FAQ">
            {["Все", ...faqCategories].map((category) => (
              <button
                type="button"
                key={category}
                className={activeCategory === category ? "active" : ""}
                onClick={() => setActiveCategory(category)}
              >
                {category}
                <span>{category === "Все" ? faqItems.length : faqItems.filter((item) => item.category === category).length}</span>
              </button>
            ))}
          </div>
          <div className="faqSupportCard">
            <LaunchIcon type="vk" />
            <h3>Не нашли ответ?</h3>
            <p>Напишите нам во ВКонтакте или в Telegram — поможем разобраться с загрузкой, обработкой или результатами.</p>
            <a href={STL_MASTER_SUPPORT_URL} target="_blank" rel="noopener noreferrer">Написать в поддержку</a>
          </div>
        </aside>
        <div className="faqAccordionColumn">
          <label className="faqSearch">
            <span>Поиск по FAQ</span>
            <input
              type="search"
              placeholder="Найти ответ"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            {(query || activeCategory !== "Все") && <button type="button" onClick={clearSearch}>Очистить</button>}
          </label>
          {filteredItems.length > 0 ? (
            <div className="faqAccordion" data-count={filteredItems.length}>
              {filteredItems.map((item) => {
                const isOpen = openId === item.id;
                const panelId = `faq-panel-${item.id}`;
                const buttonId = `faq-button-${item.id}`;
                return (
                  <article className={isOpen ? "faqAccordionItem open" : "faqAccordionItem"} key={item.id}>
                    <h3>
                      <button
                        id={buttonId}
                        type="button"
                        aria-expanded={isOpen}
                        aria-controls={panelId}
                        onClick={() => setOpenId(isOpen ? "" : item.id)}
                      >
                        <span>{item.category}</span>
                        {item.question}
                        <i aria-hidden="true">{isOpen ? "−" : "+"}</i>
                      </button>
                    </h3>
                    <div
                      id={panelId}
                      className="faqAccordionPanel"
                      role="region"
                      aria-labelledby={buttonId}
                      aria-hidden={!isOpen}
                    >
                      <p>{item.answer}</p>
                      {item.id === "support" && <a href={STL_MASTER_SUPPORT_URL} target="_blank" rel="noopener noreferrer" tabIndex={isOpen ? 0 : -1}>Написать автору поддержки</a>}
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="faqEmptyState" role="status">
              <h3>Ничего не найдено</h3>
              <p>Попробуйте изменить запрос или напишите нам во ВКонтакте либо в Telegram.</p>
              <a href={STL_MASTER_SUPPORT_URL} target="_blank" rel="noopener noreferrer">Написать в поддержку</a>
            </div>
          )}
        </div>
      </div>
      <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
    </section>
  );
}

function LaunchContacts({ onOpenApplication }) {
  return (
    <footer className="launchContacts footerV9 revealSection in-view" id="footer">
      <div className="footerBrand">
        <a className="publicTopBrand footerLogo" href="#top" aria-label="STL Master, наверх страницы">
          <LaunchIcon type="logo" />
          <strong>STL <span>Master</span></strong>
        </a>
        <p>Онлайн-инструмент для проверки, ремонта, оптимизации и подготовки STL-моделей к 3D-печати.</p>
        <button className="footerAppButton" type="button" onClick={onOpenApplication} aria-label="Открыть редактор STL Master">
          <LaunchIcon type="cube" />
          Открыть приложение
        </button>
      </div>
      {footerNavigation.map((group) => (
        <nav key={group.title} aria-label={group.title}>
          <h3>{group.title}</h3>
          <ul>
            {group.links.map((link) => (
              <li key={`${group.title}-${link.href}-${link.label}`}><a href={link.href}>{link.label}</a></li>
            ))}
          </ul>
        </nav>
      ))}
      <nav aria-label="Поддержка">
        <h3>Поддержка</h3>
        <ul>
          <li><a href="#faq">FAQ</a></li>
          <li><a href={STL_MASTER_SUPPORT_URL} target="_blank" rel="noopener noreferrer">Написать в поддержку</a></li>
          <li><a href={STL_MASTER_COMMUNITY_URL} target="_blank" rel="noopener noreferrer">Сообщество ВКонтакте</a></li>
          <li><a href={STL_MASTER_TELEGRAM_URL} target="_blank" rel="noopener noreferrer">Telegram-чат</a></li>
          <li><a href={STL_MASTER_PIKABU_URL} target="_blank" rel="noopener noreferrer">Канал на Pikabu</a></li>
        </ul>
        <h3>Мы в соцсетях</h3>
        <div className="socialLinks">
          {socialLinks.map((link) => (
            <a key={link.label} href={link.href} target="_blank" rel="noopener noreferrer" aria-label={link.ariaLabel}>
              <LaunchIcon type={link.icon} />
              {link.label}
            </a>
          ))}
        </div>
      </nav>
      <div className="footerBottom">
        <span>© {currentYear} STL Master. Все права защищены.</span>
        <a href={STL_MASTER_TELEGRAM_URL} target="_blank" rel="noopener noreferrer">Telegram: @chat_pechatdlyadoma</a>
      </div>
    </footer>
  );
}

const premiumModalErrors = {
  invalid_code: "Код не найден. Проверьте символы и попробуйте ещё раз.",
  expired_code: "Срок действия кода истёк. Запросите новый код.",
  already_used: "Этот код уже был активирован.",
  request_not_found: "Заявка не найдена. Создайте новую заявку.",
  request_rejected: "Заявка отклонена. Для уточнения напишите администратору.",
  user_blocked: "Доступ по этому коду ограничен. Напишите администратору.",
  rate_limited: "Слишком много попыток. Попробуйте позже.",
  timeout: "Сервис временно недоступен. Повторите попытку.",
  create_timeout: "Сервис временно недоступен. Повторите попытку.",
  create_network_error: "Проверьте соединение и повторите попытку.",
  create_invalid_json: "Сервер вернул некорректный ответ. Повторите попытку.",
  create_http_error: "Сервер отклонил заявку. Повторите попытку или напишите администратору.",
  create_business_error: "Заявка не была принята. Повторите попытку или напишите администратору.",
  create_frontend_exception: "Не удалось обработать ответ сервера. Повторите попытку.",
  network_error: "Не удалось связаться с сервером. Проверьте соединение и повторите попытку.",
  status_error: "Не удалось проверить статус заявки.",
  create_failed: "Проверьте соединение и повторите попытку.",
  server_error: "Сервис временно недоступен. Попробуйте позже.",
};

const PREMIUM_MODAL_STATES = {
  INTRO: "intro",
  CREATING_REQUEST: "creating_request",
  MESSAGE_READY: "message_ready",
  WAITING_FOR_CODE: "waiting_for_code",
  ENTER_CODE: "enter_code",
  VERIFYING_CODE: "verifying_code",
  PREMIUM_ACTIVE: "premium_active",
  REQUEST_REJECTED: "request_rejected",
  ERROR: "error",
};

function getPremiumClientId() {
  const existing = localStorage.getItem(PREMIUM_CLIENT_STORAGE_KEY);
  if (existing) return existing;
  const generated = `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  localStorage.setItem(PREMIUM_CLIENT_STORAGE_KEY, generated);
  return generated;
}

function createIdempotencyKey() {
  if (window.crypto?.randomUUID) return `premium-${window.crypto.randomUUID()}`;
  return `premium-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

function normalizePremiumCode(value) {
  return value.trim().replace(/\s+/g, "").replace(/[^A-Za-z0-9_-]/g, "").toUpperCase().slice(0, 80);
}

async function copyTextWithFallback(text) {
  try {
    await navigator.clipboard?.writeText?.(text);
    return true;
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      return document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }
  }
}

function fetchWithSoftTimeout(url, options = {}, ms = 15000, timeoutKey = "timeout") {
  let timeoutId;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => {
      const error = new Error(timeoutKey);
      error.name = "TimeoutError";
      reject(error);
    }, ms);
  });
  return Promise.race([fetch(url, options), timeoutPromise]).finally(() => window.clearTimeout(timeoutId));
}

function PremiumAccessModal({ onClose, onOpenApplication, onActivated }) {
  const [step, setStep] = useState(PREMIUM_MODAL_STATES.INTRO);
  const [buttonState, setButtonState] = useState("idle");
  const [applicationId, setApplicationId] = useState(() => localStorage.getItem(PREMIUM_APPLICATION_STORAGE_KEY) || "");
  const [requestNumber, setRequestNumber] = useState(() => localStorage.getItem(PREMIUM_REQUEST_NUMBER_STORAGE_KEY) || "");
  const [applicationStatus, setApplicationStatus] = useState("");
  const [applicationMeta, setApplicationMeta] = useState(null);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [status, setStatus] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [activatedPremium, setActivatedPremium] = useState(null);
  const closeButtonRef = useRef(null);
  const dialogRef = useRef(null);
  const pollStartedAtRef = useRef(0);
  const idempotencyKeyRef = useRef(createIdempotencyKey());
  const busy = buttonState === "loading" || buttonState === "verifying";
  const premiumMonthlyText = pricingPlan.priceLabel.replace(/\s*\/\s*/, " в ");
  const requestMessage = [
    "Здравствуйте! Хочу подключить Premium в STL Master.",
    "",
    `Номер заявки: ${requestNumber || "—"}`,
    "",
    `Стоимость: ${premiumMonthlyText}.`,
    "",
    "Подскажите порядок оплаты. После подтверждения, пожалуйста, отправьте мне Premium-код.",
  ].join("\n");

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus?.();
    const onKeyDown = (event) => {
      if (event.key === "Escape" && !busy) onClose();
      if (event.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(dialogRef.current.querySelectorAll("button, a, input, textarea, [tabindex]:not([tabindex='-1'])")).filter((item) => !item.disabled && item.offsetParent !== null);
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [busy, onClose]);

  useEffect(() => {
    if ((!requestNumber && !applicationId) || step !== PREMIUM_MODAL_STATES.WAITING_FOR_CODE) return undefined;
    if (!pollStartedAtRef.current) pollStartedAtRef.current = Date.now();
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "hidden") return;
      if (Date.now() - pollStartedAtRef.current > 10 * 60 * 1000) {
        window.clearInterval(intervalId);
        return;
      }
      checkApplicationStatus({ silent: true });
    }, 9000);
    return () => window.clearInterval(intervalId);
  }, [applicationId, requestNumber, step]);

  const parsePremiumError = async (response) => {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const errorKey = typeof detail === "object" && detail ? detail.error : payload.error;
    return errorKey || "server_error";
  };

  const readPremiumJson = async (response) => {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.toLowerCase().includes("application/json")) {
      const bodyPreview = await response.text().catch(() => "");
      const error = new Error("create_invalid_json");
      error.diagnostic = {
        category: "invalid_json",
        status: response.status,
        contentType,
        bodyPreview: bodyPreview.slice(0, 120),
      };
      throw error;
    }
    return response.json();
  };

  const createRequest = async () => {
    setButtonState("loading");
    setStep(PREMIUM_MODAL_STATES.CREATING_REQUEST);
    setStatus("");
    setErrorCode("");
    setCodeError("");
    const requestUrl = getApiUrl("/api/v1/premium-requests");
    const requestBody = {
      source: "website",
      requested_plan: "premium_monthly_299",
      client_id: getPremiumClientId(),
      idempotency_key: idempotencyKeyRef.current,
      comment: "Premium request from public modal",
    };
    try {
      const response = await fetchWithSoftTimeout(requestUrl, {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=UTF-8" },
        credentials: "omit",
        cache: "no-store",
        body: JSON.stringify(requestBody),
      }, 15000, "create_timeout");
      const payload = await readPremiumJson(response);
      if (!response.ok) {
        const detail = typeof payload.detail === "object" && payload.detail ? payload.detail.error : payload.detail;
        const error = new Error(detail || payload.error || "create_http_error");
        error.diagnostic = { category: "http_error", status: response.status, responseKeys: Object.keys(payload || {}) };
        throw error;
      }
      if (payload.ok === false) {
        const error = new Error(payload.error || "create_business_error");
        error.diagnostic = { category: "business_error", status: response.status, responseKeys: Object.keys(payload || {}) };
        throw error;
      }
      const nextId = String(payload.application_id || "");
      if (nextId) {
        setApplicationId(nextId);
        localStorage.setItem(PREMIUM_APPLICATION_STORAGE_KEY, nextId);
      }
      const nextNumber = String(payload.request_number || "");
      if (!nextNumber) {
        const error = new Error("create_failed");
        error.diagnostic = { category: "frontend_exception", status: response.status, responseKeys: Object.keys(payload || {}) };
        throw error;
      }
      setRequestNumber(nextNumber);
      localStorage.setItem(PREMIUM_REQUEST_NUMBER_STORAGE_KEY, nextNumber);
      setApplicationStatus("pending");
      setApplicationMeta({ application_id: nextId, request_number: nextNumber, status: "pending", created_at: payload.created_at || null });
      setStep(PREMIUM_MODAL_STATES.MESSAGE_READY);
    } catch (err) {
      const timedOut = err.name === "AbortError" || err.name === "TimeoutError" || err.message === "create_timeout";
      const knownCreateError = ["create_failed", "create_timeout", "create_invalid_json", "create_http_error", "create_business_error", "create_frontend_exception"].includes(err.message);
      const key = timedOut ? "create_timeout" : (knownCreateError ? err.message : "create_network_error");
      if (window.STL_PREMIUM_DEBUG) {
        console.debug("[premium-request]", {
          url: requestUrl,
          error: key,
          diagnostic: err.diagnostic || { category: timedOut ? "timeout" : "network" },
        });
      }
      setErrorCode(key);
      setStatus(premiumModalErrors[key] || premiumModalErrors.create_failed);
      setStep(PREMIUM_MODAL_STATES.INTRO);
    } finally {
      setButtonState("idle");
    }
  };

  const copyMessage = async () => {
    const copied = await copyTextWithFallback(requestMessage);
    if (copied) {
      setButtonState("success");
      setStatus("Сообщение скопировано");
    } else {
      setButtonState("error");
      setStatus("Скопируйте сообщение вручную");
    }
  };

  const applyApplicationStatus = (payload) => {
    const nextStatus = String(payload?.status || "");
    setApplicationStatus(nextStatus);
    setApplicationMeta(payload || null);
    if (payload?.application_id) {
      setApplicationId(String(payload.application_id));
      localStorage.setItem(PREMIUM_APPLICATION_STORAGE_KEY, String(payload.application_id));
    }
    if (payload?.request_number) {
      setRequestNumber(String(payload.request_number));
      localStorage.setItem(PREMIUM_REQUEST_NUMBER_STORAGE_KEY, String(payload.request_number));
    }
    if (payload?.activated || nextStatus === "activated") {
      setStep(PREMIUM_MODAL_STATES.PREMIUM_ACTIVE);
      return;
    }
    if (nextStatus === "rejected") {
      setStep(PREMIUM_MODAL_STATES.REQUEST_REJECTED);
      return;
    }
    if (nextStatus === "code_issued" || nextStatus === "approved") {
      setStatus("Заявка одобрена. Введите Premium-код, полученный от администратора.");
      setStep(PREMIUM_MODAL_STATES.WAITING_FOR_CODE);
      return;
    }
    setStatus("Заявка ожидает решения.");
    setStep(PREMIUM_MODAL_STATES.WAITING_FOR_CODE);
  };

  const checkApplicationStatus = async ({ silent = false } = {}) => {
    if (!requestNumber && !applicationId) {
      setStatus("Сначала создайте заявку.");
      return;
    }
    if (!silent) {
      setButtonState("loading");
      setStatus("");
    }
    try {
      const statusPath = requestNumber
        ? `/api/v1/premium-requests/by-number/${encodeURIComponent(requestNumber)}`
        : `/api/v1/premium-requests/${encodeURIComponent(applicationId)}`;
      const response = await fetchWithSoftTimeout(getApiUrl(statusPath), {
        method: "GET",
        credentials: "omit",
        cache: "no-store",
      }, 12000, "timeout");
      if (!response.ok) {
        const errorKey = await parsePremiumError(response);
        throw new Error(errorKey);
      }
      const payload = await response.json();
      applyApplicationStatus(payload);
    } catch (err) {
      if (!silent) {
        const key = err.message === "request_not_found" ? "request_not_found" : (err.name === "AbortError" ? "timeout" : "status_error");
        setErrorCode(key);
        setStatus(premiumModalErrors[key] || premiumModalErrors.status_error);
        setStep(PREMIUM_MODAL_STATES.ERROR);
      }
    } finally {
      if (!silent) setButtonState("idle");
    }
  };

  const openAdminProfile = () => {
    window.open(STL_MASTER_SUPPORT_URL, "_blank", "noopener,noreferrer");
  };

  const verifyCode = async (event) => {
    event?.preventDefault?.();
    const normalized = normalizePremiumCode(code);
    setCode(normalized);
    setStatus("");
    setErrorCode("");
    if (!normalized) {
      setCodeError("Введите Premium-код.");
      return;
    }
    if (normalized.length < 10) {
      setCodeError("Код выглядит слишком коротким.");
      return;
    }
    setCodeError("");
    setButtonState("verifying");
    setStep(PREMIUM_MODAL_STATES.VERIFYING_CODE);
    try {
      const response = await fetchWithSoftTimeout(getApiUrl("/api/v1/premium/activate"), {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=UTF-8" },
        credentials: "omit",
        cache: "no-store",
        body: JSON.stringify({ code: normalized, request_number: requestNumber || undefined, application_id: applicationId || undefined }),
      }, 15000, "timeout");
      if (!response.ok) {
        const errorKey = await parsePremiumError(response);
        setErrorCode(errorKey);
        setStatus(premiumModalErrors[errorKey] || premiumModalErrors.server_error);
        setStep(PREMIUM_MODAL_STATES.ERROR);
        return;
      }
      const payload = await response.json();
      localStorage.setItem(ACCESS_CODE_STORAGE_KEY, normalized);
      onActivated?.(normalized, payload);
      setActivatedPremium(payload);
      setApplicationStatus("activated");
      if (payload?.request_number) {
        setRequestNumber(String(payload.request_number));
        localStorage.setItem(PREMIUM_REQUEST_NUMBER_STORAGE_KEY, String(payload.request_number));
      }
      setStep(PREMIUM_MODAL_STATES.PREMIUM_ACTIVE);
    } catch (err) {
      const key = err.name === "AbortError" ? "timeout" : "network_error";
      setErrorCode(key);
      setStatus(premiumModalErrors[key] || premiumModalErrors.network_error);
      setStep(PREMIUM_MODAL_STATES.ERROR);
    } finally {
      setButtonState("idle");
    }
  };

  const resetToRequest = () => {
    setButtonState("idle");
    setStatus("");
    setErrorCode("");
    setCodeError("");
    setStep(PREMIUM_MODAL_STATES.INTRO);
  };
  const switchToCode = () => {
    setButtonState("idle");
    setStatus("");
    setErrorCode("");
    setCodeError("");
    setStep(PREMIUM_MODAL_STATES.ENTER_CODE);
  };

  const renderPrimaryButtonLabel = () => {
    if (buttonState === "loading") return "Создаём заявку…";
    if (buttonState === "verifying") return "Проверяем код…";
    if (step === PREMIUM_MODAL_STATES.INTRO && ["create_timeout", "create_network_error", "create_failed"].includes(errorCode)) return "Повторить";
    return step === PREMIUM_MODAL_STATES.ENTER_CODE ? "Активировать Premium" : "Создать заявку";
  };

  return (
    <div className="publicModalBackdrop premiumModalBackdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <section
        ref={dialogRef}
        className={`premiumAccessModal premiumAccessModal-${step}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="premium-modal-title"
        aria-describedby="premium-modal-description"
      >
        <button ref={closeButtonRef} className="modalClose premiumModalClose" type="button" onClick={onClose} disabled={busy} aria-label="Закрыть окно Premium">
          <LaunchIcon type="close" />
        </button>
        <div className="premiumModalArt" aria-hidden="true">
          <div className="premiumModalRenderStage">
            <img src={dragonSkullPoster} alt="" />
            <span className="premiumRenderGlow" />
            <span className="premiumRenderGrid" />
          </div>
          <div className="premiumModalRenderBadge">
            <span>STL Master</span>
            <b>Premium</b>
          </div>
        </div>
        <div className="premiumModalContent">
          {step === PREMIUM_MODAL_STATES.INTRO && (
            <>
              <p className="sectionKicker">STL Master Premium</p>
              <h2 id="premium-modal-title">Получите Premium-доступ к STL Master</h2>
              <p id="premium-modal-description">Создайте заявку, отправьте её номер администратору во ВКонтакте и получите персональный Premium-код после подтверждения.</p>
              <ol className="premiumModalSteps">
                <li><b>1</b><span>Создайте заявку.</span></li>
                <li><b>2</b><span>Отправьте её номер администратору.</span></li>
                <li><b>3</b><span>Получите код и активируйте Premium.</span></li>
              </ol>
              {["create_timeout", "create_network_error", "create_failed"].includes(errorCode) && (
                <div className="premiumInlineAlert" role="alert">
                  <strong>Заявку не удалось создать</strong>
                  <span>{status || premiumModalErrors.create_failed}</span>
                </div>
              )}
              <button className={`premiumFlowButton ${buttonState}`} type="button" onClick={createRequest} disabled={busy}>
                {buttonState === "loading" && <span className="premiumButtonSpinner" aria-hidden="true" />}
                <LaunchIcon type="premium" />
                {renderPrimaryButtonLabel()}
              </button>
              {["create_timeout", "create_network_error", "create_failed"].includes(errorCode) && (
                <button className="premiumModalLinkButton" type="button" onClick={openAdminProfile}>Связаться с администратором</button>
              )}
              <button className="premiumModalLinkButton" type="button" onClick={switchToCode}>У меня уже есть Premium-код</button>
              <small>Стоимость Premium: {premiumMonthlyText}.</small>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.CREATING_REQUEST && (
            <>
              <div className="modalStatusIcon pending"><LaunchIcon type="premium" /></div>
              <h2 id="premium-modal-title">Создаём заявку</h2>
              <p id="premium-modal-description">Регистрируем заявку на сервере, чтобы администратор увидел её в панели STL Master.</p>
              <div className="premiumWaitingCard"><span className="premiumWaitingSpinner" aria-hidden="true" /><div><b>Создаём заявку</b><small>Обычно это занимает несколько секунд</small></div></div>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.MESSAGE_READY && (
            <>
              <div className="modalStatusIcon success"><LaunchIcon type="check" /></div>
              <h2 id="premium-modal-title">Сообщение подготовлено</h2>
              <p id="premium-modal-description">Скопируйте текст с номером заявки и отправьте его администратору STL Master во ВКонтакте.</p>
              <div className="premiumApplicationId"><span>Номер заявки</span><strong>{requestNumber || "—"}</strong></div>
              <pre className="premiumMessagePreview">{requestMessage}</pre>
              <button className={`premiumFlowButton ${buttonState}`} type="button" onClick={copyMessage}>
                <LaunchIcon type="copy" />
                {status === "Сообщение скопировано" ? "Сообщение скопировано" : "Скопировать сообщение"}
              </button>
              <button className="modalVkButton" type="button" onClick={openAdminProfile}><LaunchIcon type="vk" /> Открыть профиль администратора</button>
              <button className="premiumModalLinkButton" type="button" onClick={() => { pollStartedAtRef.current = Date.now(); setStep(PREMIUM_MODAL_STATES.WAITING_FOR_CODE); }}>Я отправил сообщение</button>
              <button className="premiumModalLinkButton" type="button" onClick={switchToCode}>У меня уже есть Premium-код</button>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.WAITING_FOR_CODE && (
            <>
              <div className="modalStatusIcon pending"><LaunchIcon type="analyze" /></div>
              <h2 id="premium-modal-title">Ожидаем Premium-код</h2>
              <p id="premium-modal-description">Администратор проверит заявку и отправит персональный код в ответном сообщении во ВКонтакте.</p>
              <div className="premiumApplicationId"><span>Номер заявки</span><strong>{requestNumber || "—"}</strong></div>
              <div className="premiumWaitingCard">
                <LaunchIcon type="premium" />
                <div><b>{applicationStatus === "code_issued" ? "Код выпущен" : "Ожидает решения"}</b><small>{applicationStatus || "pending"}</small></div>
              </div>
              <div className="premiumModalActions">
                <button className="premiumFlowButton" type="button" onClick={switchToCode}>Ввести Premium-код</button>
                <button className="copyMessageButton" type="button" onClick={openAdminProfile}><LaunchIcon type="vk" /> Открыть профиль администратора</button>
                <button className="copyMessageButton" type="button" onClick={copyMessage}><LaunchIcon type="copy" /> Скопировать сообщение ещё раз</button>
                <button className="copyMessageButton" type="button" onClick={() => checkApplicationStatus()} disabled={busy}>
                  {buttonState === "loading" && <span className="premiumButtonSpinner" aria-hidden="true" />}
                  Проверить статус
                </button>
              </div>
              <button className="premiumModalLinkButton" type="button" onClick={() => setStep(PREMIUM_MODAL_STATES.MESSAGE_READY)}>Вернуться к сообщению</button>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.ENTER_CODE && (
            <>
              <p className="sectionKicker">Активация Premium</p>
              <h2 id="premium-modal-title">Активировать Premium</h2>
              <p id="premium-modal-description">Введите персональный код, который администратор отправил вам во ВКонтакте.</p>
              {requestNumber && <div className="premiumApplicationId compact"><span>Заявка</span><strong>{requestNumber}</strong></div>}
              <form className="premiumCodeForm" onSubmit={verifyCode}>
                <label>
                  <span>Premium-код</span>
                  <input
                    autoComplete="one-time-code"
                    inputMode="text"
                    maxLength={80}
                    placeholder="STL-XXXX-XXXX-XXXX"
                    value={code}
                    onChange={(event) => {
                      setCode(normalizePremiumCode(event.target.value));
                      setCodeError("");
                    }}
                    aria-invalid={Boolean(codeError)}
                  />
                </label>
                {codeError && <p className="premiumInlineError">{codeError}</p>}
                <button className={`premiumFlowButton ${buttonState}`} type="submit" disabled={busy || !code.trim()}>
                  {buttonState === "verifying" && <span className="premiumButtonSpinner" aria-hidden="true" />}
                  <LaunchIcon type="premium" />
                  {renderPrimaryButtonLabel()}
                </button>
              </form>
              <button className="premiumModalLinkButton" type="button" onClick={() => (requestNumber || applicationId) ? setStep(PREMIUM_MODAL_STATES.WAITING_FOR_CODE) : resetToRequest()}>Вернуться к заявке</button>
              <button className="premiumModalLinkButton" type="button" onClick={openAdminProfile}>Открыть профиль администратора</button>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.VERIFYING_CODE && (
            <>
              <div className="modalStatusIcon pending"><LaunchIcon type="premium" /></div>
              <h2 id="premium-modal-title">Проверяем код</h2>
              <p id="premium-modal-description">Связываемся с сервером и активируем Premium-доступ.</p>
              <div className="premiumWaitingCard"><span className="premiumWaitingSpinner" aria-hidden="true" /><div><b>Проверка кода</b><small>Это займёт несколько секунд</small></div></div>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.PREMIUM_ACTIVE && (
            <>
              <div className="modalStatusIcon opened"><LaunchIcon type="lock" /></div>
              <h2 id="premium-modal-title">Premium активирован</h2>
              <p id="premium-modal-description">Персональный код принят. Premium-возможности STL Master доступны.</p>
              <dl className="premiumSuccessMeta">
                <div><dt>Статус</dt><dd>Premium</dd></div>
                {requestNumber && <div><dt>Заявка</dt><dd>{requestNumber}</dd></div>}
                {activatedPremium?.expires_at && <div><dt>Действует до</dt><dd>{activatedPremium.expires_at}</dd></div>}
                {activatedPremium?.plan && <div><dt>Тариф</dt><dd>{activatedPremium.plan}</dd></div>}
              </dl>
              <button className="modalOpenButton" type="button" onClick={() => { onClose(); onOpenApplication?.(); }}><LaunchIcon type="flash" /> Открыть приложение</button>
              <button className="premiumModalLinkButton" type="button" onClick={openAdminProfile}>Открыть профиль администратора</button>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.REQUEST_REJECTED && (
            <>
              <div className="modalStatusIcon error"><LaunchIcon type="close" /></div>
              <h2 id="premium-modal-title">Заявка отклонена</h2>
              <p id="premium-modal-description">Запрос не был одобрен. Для уточнения напишите администратору STL Master.</p>
              {applicationMeta?.rejected_reason && <div className="premiumTipCard"><strong>Причина</strong><span>{applicationMeta.rejected_reason}</span></div>}
              <button className="modalErrorButton" type="button" onClick={openAdminProfile}><LaunchIcon type="vk" /> Написать администратору</button>
              <button className="premiumModalLinkButton" type="button" onClick={resetToRequest}>Создать новую заявку</button>
            </>
          )}

          {step === PREMIUM_MODAL_STATES.ERROR && (
            <>
              <div className="modalStatusIcon error"><LaunchIcon type="close" /></div>
              <h2 id="premium-modal-title">Не удалось активировать Premium</h2>
              <p id="premium-modal-description">{status || premiumModalErrors.server_error}</p>
              <div className="premiumTipCard">
                <strong>Нужна помощь?</strong>
                <span>Напишите администратору STL Master, если ошибка повторяется.</span>
                <button type="button" onClick={openAdminProfile}>Открыть профиль администратора</button>
              </div>
              <div className="premiumModalActions">
                <button className="modalErrorButton" type="button" onClick={errorCode === "status_error" ? () => checkApplicationStatus() : switchToCode}>Повторить</button>
                <button className="copyMessageButton" type="button" onClick={openAdminProfile}>Открыть профиль администратора</button>
              </div>
            </>
          )}

          {status && step !== PREMIUM_MODAL_STATES.ERROR && <p className="launchStatus" role="status" aria-live="polite">{status}</p>}
        </div>
      </section>
    </div>
  );
}

function PublicModal({ type, onClose }) {
  const isDemo = type === "demo";
  const [form, setForm] = useState({ name: "", email: "", telegram: "", occupation: "", use_case: "" });
  const [step, setStep] = useState(isDemo ? "demo" : "form");
  const [buttonState, setButtonState] = useState("idle");
  const [status, setStatus] = useState("");
  const contact = form.telegram || form.email || form.name || "не указан";
  const accessMessage = `Хочу получить ранний доступ к STL Master. Контакт: ${contact}`;
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => {
    event.preventDefault();
    setStatus("");
    setButtonState("loading");
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/access-requests`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Не удалось отправить сообщение");
      }
      setStep("sent");
      setButtonState("success");
      setStatus("Сообщение отправлено");
    } catch (err) {
      setStep("error");
      setButtonState("error");
      setStatus(err.message || "Ошибка, попробуйте снова");
    }
  };
  const copyMessage = async () => {
    try {
      await navigator.clipboard?.writeText?.(accessMessage);
      setStep("copy");
      setStatus("Сообщение скопировано");
    } catch {
      setStep("copy");
      setStatus("Скопируйте сообщение вручную");
    }
  };
  const openCommunity = () => {
    setButtonState("loading");
    window.setTimeout(() => {
      setButtonState("success");
      setStep("opened");
      window.open(STL_MASTER_COMMUNITY_URL, "_blank", "noopener,noreferrer");
    }, 550);
  };
  if (isDemo) {
    return <div className="publicModalBackdrop" role="dialog" aria-modal="true"><section className="publicModal demoModal"><button className="modalClose" type="button" onClick={onClose}><LaunchIcon type="close" /></button><DemoStudioPreview /><div><p className="sectionKicker">Пример</p><h2>STL Master Studio в действии</h2><p>Разрез, соединения, проверка печати и экспорт показаны как интерактивный интерфейс редактора.</p><button className="modalPrimaryButton" type="button" onClick={onClose}>Закрыть пример</button></div></section></div>;
  }
  return (
    <div className="publicModalBackdrop" role="dialog" aria-modal="true">
      <section className={`publicModal modalState-${step}`}>
        <button className="modalClose" type="button" onClick={onClose}><LaunchIcon type="close" /></button>
        <div className="modalArt"><ModalArtScene /></div>
        <div className="modalContent">
          <p className="sectionKicker">Ранний доступ</p>
          {step === "form" && <><h2>Оставьте заявку на ранний доступ</h2><p>В режиме раннего доступа принимаются STL до 100 МБ. Отправьте заявку к приложению, мы рассмотрим её и свяжемся с вами.</p><ol><li>Заполните имя и email</li><li>Опишите, для чего нужен STL Master</li><li>Получите access-code после одобрения</li></ol><div className="accessHowToCard"><strong>Как тестировать</strong><span>После одобрения используйте access-code в STL Master Studio и загружайте реальные STL-файлы через редактор.</span></div><form className="publicForm" onSubmit={submit}><input required placeholder="Имя" value={form.name} onChange={(event) => update("name", event.target.value)} /><input required type="email" placeholder="Email" value={form.email} onChange={(event) => update("email", event.target.value)} /><input placeholder="Telegram или VK" value={form.telegram} onChange={(event) => update("telegram", event.target.value)} /><textarea placeholder="Комментарий" value={form.use_case} onChange={(event) => update("use_case", event.target.value)} /><button className={`modalVkButton ${buttonState}`} type="submit"><LaunchIcon type="vk" /> {buttonState === "loading" ? "Отправляем заявку..." : "Отправить заявку"}</button></form><button className="copyMessageButton" type="button" onClick={copyMessage}><LaunchIcon type="copy" /> Скопировать сообщение</button><small>Заявка сохраняется в системе раннего доступа.</small></>}
          {step === "sent" && <><div className="modalStatusIcon success"><LaunchIcon type="check" /></div><h2>Сообщение отправлено!</h2><p>Спасибо! Мы получили вашу заявку на доступ к STL Master.</p><div className="modalProgress"><span>Заявка создана</span><span>Проверка данных</span><span>Подтверждение</span><span>Access-code</span></div><button className="modalVkButton" type="button" onClick={openCommunity}><LaunchIcon type="vk" /> Перейти в сообщество</button></>}
          {step === "opened" && <><div className="modalStatusIcon opened"><LaunchIcon type="lock" /></div><h2>Доступ открыт!</h2><p>Добро пожаловать в STL Master. Приложение уже готово к работе.</p><button className="modalOpenButton" type="button" onClick={onClose}><LaunchIcon type="flash" /> Открыть приложение</button><a className="modalSecondaryLink" href={STL_MASTER_COMMUNITY_URL} target="_blank" rel="noopener noreferrer">Перейти к сообществу</a></>}
          {step === "error" && <><div className="modalStatusIcon error"><LaunchIcon type="close" /></div><h2>Не удалось открыть доступ</h2><p>Мы не получили ваше сообщение. Пожалуйста, попробуйте ещё раз.</p><ul className="errorReasons"><li>Сообщение не отправлено</li><li>Вы не подписаны на сообщество</li><li>Техническая задержка</li></ul><button className="modalErrorButton" type="button" onClick={() => { setStep("form"); setButtonState("idle"); }}>Попробовать снова</button></>}
          {step === "copy" && <><h2>Отправьте это сообщение сообществу</h2><p>Скопируйте текст и отправьте его в сообщения.</p><pre>{accessMessage}</pre><button className="modalVkButton" type="button" onClick={openCommunity}><LaunchIcon type="vk" /> Написать сообществу</button><button className="modalTextButton" type="button" onClick={onClose}>Закрыть</button></>}
          {status && <p className="launchStatus">{status}</p>}
        </div>
      </section>
    </div>
  );
}

function PublicLanding({ onStartCut, onDemo, onPremiumActivated, currentUser = null, currentUserLoading = false, featureFlags = DEFAULT_FEATURE_FLAGS }) {
  const [compactHeader, setCompactHeader] = useState(false);
  const [activeSection, setActiveSection] = useState("hero");
  const [modal, setModal] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const openApplication = () => {
    setMenuOpen(false);
    onStartCut?.();
  };
  const openPremium = () => {
    setMenuOpen(false);
    setModal("premium");
  };
  const openSupport = () => {
    setMenuOpen(false);
    window.open(STL_MASTER_SUPPORT_URL, "_blank", "noopener,noreferrer");
  };
  const openExample = () => {
    setMenuOpen(false);
    if (typeof onDemo === "function") {
      onDemo();
    } else {
      setModal("demo");
    }
  };
  const closeMenu = () => setMenuOpen(false);
  useEffect(() => { const onScroll = () => setCompactHeader(window.scrollY > 36); onScroll(); window.addEventListener("scroll", onScroll, { passive: true }); return () => window.removeEventListener("scroll", onScroll); }, []);
  useEffect(() => { const sections = Array.from(document.querySelectorAll(".publicSite section[id], .publicSite footer[id]")); const observer = new IntersectionObserver((entries) => { entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("in-view"); setActiveSection(entry.target.id); } }); }, { threshold: 0.18, rootMargin: "-12% 0px -55%" }); sections.forEach((section) => observer.observe(section)); return () => observer.disconnect(); }, []);
  return (
    <main className="publicLanding publicSite" id="top">
      <header className={`publicTopNav topNavV8 ${compactHeader ? "compact" : ""}`}>
        <a className="publicTopBrand topBrandV8" href="#top" aria-label="STL Master v2.0" onClick={closeMenu}><LaunchIcon type="logo" /><strong>STL <span>Master</span></strong><em>v2.0</em></a>
        <button
          className="publicMenuButton"
          type="button"
          aria-label="Открыть меню сайта"
          aria-controls="public-navigation"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((value) => !value)}
        >
          <span />
          <span />
        </button>
        <div className={menuOpen ? "publicTopPanel open" : "publicTopPanel"} id="public-navigation">
          <nav className="publicTopLinks topLinksV8" aria-label="Навигация публичного сайта">
            {mainNavigation.map(({ id, label }) => <a key={id} className={activeSection === id ? "active" : ""} href={`#${id}`} onClick={closeMenu}>{label}</a>)}
          </nav>
          <div className="publicTopActions topActionsV8">
            <button className="appOpenButton appOpenButtonV9" type="button" onClick={openApplication} aria-label="Открыть редактор STL Master"><LaunchIcon type="cube" /> Открыть приложение</button>
            <PremiumStatusControl
              currentUser={currentUser}
              loading={currentUserLoading}
              onOpenApplication={openApplication}
              onOpenPremium={openPremium}
            />
            <button className="mobileSupportButton" type="button" onClick={openSupport}><LaunchIcon type="vk" /> Поддержка VK</button>
          </div>
        </div>
      </header>
      <HeroSection onOpenApplication={openApplication} onExample={openExample} />
      <WorkflowSection />
      <ConnectorsSection onStartCut={onStartCut} />
      <BeforeAfterShowcase />
      <FeaturesSection onStartUpload={onStartCut} />
      <PremiumShowcase onPremium={openPremium} featureFlags={featureFlags} />
      <FAQSection />
      <LaunchContacts onOpenApplication={openApplication} />
      {modal === "premium" && (
        <PremiumAccessModal
          onActivated={onPremiumActivated}
          onClose={() => setModal(null)}
          onOpenApplication={openApplication}
        />
      )}
      {modal && modal !== "premium" && <PublicModal type={modal} onClose={() => setModal(null)} />}
    </main>
  );
}

function AccessRequestForm({ apiBaseUrl, onBack }) {
  const [form, setForm] = useState({ name: "", email: "", telegram: "", occupation: "", use_case: "" });
  const [status, setStatus] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const submit = async (event) => { event.preventDefault(); setSubmitting(true); setStatus(""); setSuccess(false); try { const response = await fetch(`${apiBaseUrl}/api/v1/access-requests`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) }); const payload = await response.json().catch(() => ({})); if (!response.ok) throw new Error(payload.detail || "Не удалось отправить заявку"); setSuccess(true); setStatus("Заявка отправлена"); setForm({ name: "", email: "", telegram: "", occupation: "", use_case: "" }); } catch (err) { setStatus(err.message || "Не удалось отправить заявку"); } finally { setSubmitting(false); } };
  return <main className="publicLanding publicSite publicFormPage"><section className="launchFormPanel"><button className="ghostBackButton" type="button" onClick={onBack}>← На главную</button><p className="panelLabel">Ранний доступ</p><h1>Получить ранний доступ</h1>{success ? <div className="formSuccessState"><h2>Заявка отправлена</h2><p>Мы рассмотрим её и свяжемся с вами.</p><button type="button" onClick={onBack}>Вернуться на главную</button></div> : <form className="publicForm" onSubmit={submit}><label><span>Имя</span><input required value={form.name} onChange={(event) => update("name", event.target.value)} /></label><label><span>Email</span><input required type="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></label><label><span>Telegram или VK</span><input value={form.telegram} onChange={(event) => update("telegram", event.target.value)} /></label><label><span>Для чего хотите использовать STL Master?</span><textarea value={form.use_case} onChange={(event) => update("use_case", event.target.value)} /></label><button type="submit" disabled={submitting}>{submitting ? "Отправляем..." : "Отправить заявку"}</button></form>}{status && !success && <p className="launchStatus">{status}</p>}</section></main>;
}

function JobInfoPanel({ jobStatus, result }) {
  const [copyStatus, setCopyStatus] = useState("");
  if (!jobStatus) return null;
  const generatedFiles = Array.isArray(result?.generated_files) ? result.generated_files : [];
  const finalModel = result?.final_model;
  const finalFile = generatedFiles.find((item) => item.name === finalModel) || generatedFiles.find((item) => item.type === "model");
  const operations = Array.isArray(jobStatus.operations) ? jobStatus.operations : [];

  const copyJobId = async () => {
    if (!jobStatus.job_id) return;
    try {
      await navigator.clipboard.writeText(jobStatus.job_id);
      setCopyStatus("Job ID скопирован.");
    } catch {
      setCopyStatus("Не удалось скопировать Job ID автоматически.");
    }
  };

  return (
    <section className="jobInfoPanel" data-job-info="true">
      <div>
        <p className="panelLabel">Информация о задаче</p>
        <h3>Данные обработки</h3>
      </div>
      <div className="jobInfoGrid">
        <span>
          <em>Job ID</em>
          <strong>{jobStatus.job_id || "—"}</strong>
          {jobStatus.job_id && (
            <button className="copyJobButton" type="button" onClick={copyJobId}>
              Скопировать Job ID
            </button>
          )}
          {copyStatus && <small>{copyStatus}</small>}
        </span>
        <span>
          <em>Время обработки</em>
          <strong>{jobStatus.processing_seconds ? `${Math.round(jobStatus.processing_seconds)} сек` : "—"}</strong>
        </span>
        <span>
          <em>Исходный STL</em>
          <strong>{formatBytes(jobStatus.size_bytes || result?.file?.size_bytes)}</strong>
        </span>
        <span>
          <em>Итоговый STL</em>
          <strong>{formatBytes(finalFile?.size_bytes)}</strong>
        </span>
        <span>
          <em>Операции</em>
          <strong>{operations.map((operation) => operationTitles[operation] || operation).join(", ") || "—"}</strong>
        </span>
        <span>
          <em>Завершено</em>
          <strong>{formatDateTime(jobStatus.completed_at)}</strong>
        </span>
      </div>
    </section>
  );
}

function FeedbackPanel({ apiBaseUrl, jobStatus }) {
  const [rating, setRating] = useState("");
  const [comment, setComment] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);

  const submitFeedback = async () => {
    if (!rating) {
      setStatus("Выберите оценку результата.");
      return;
    }
    if (rating === "problem" && !comment.trim()) {
      setStatus("Опишите проблему перед отправкой.");
      return;
    }
    setSending(true);
    setStatus("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobStatus?.job_id,
          operations: Array.isArray(jobStatus?.operations) ? jobStatus.operations : [],
          rating,
          comment,
          contact,
        }),
      });
      if (!response.ok) throw new Error("Не удалось отправить отзыв");
      setStatus("Спасибо! Отзыв сохранён. Если нужно, пришлите Job ID в чат.");
      setComment("");
      setContact("");
    } catch {
      setStatus("Не удалось отправить отзыв. Попробуйте позже.");
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="feedbackPanel" data-feedback-panel="true">
      <div>
        <p className="panelLabel">Обратная связь</p>
        <h3>Помогите улучшить STL Master</h3>
        <p className="feedbackHint">Отзыв сохранится вместе с Job ID, чтобы мы могли найти вашу обработку и исправить проблему.</p>
      </div>
      <div className="feedbackChoice">
        <button className={rating === "good" ? "active" : ""} type="button" onClick={() => setRating("good")}>
          👍 Всё хорошо
        </button>
        <button className={rating === "problem" ? "active" : ""} type="button" onClick={() => setRating("problem")}>
          👎 Есть проблема
        </button>
      </div>
      {rating && (
        <div className="feedbackForm">
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder={rating === "problem" ? "Что пошло не так? Например: модель не разрезалась, результат не скачался, качество стало хуже." : "Что получилось хорошо или что можно улучшить?"}
            maxLength={2000}
            required={rating === "problem"}
          />
          <input
            type="text"
            value={contact}
            onChange={(event) => setContact(event.target.value)}
            placeholder="Email или Telegram, необязательно"
            maxLength={180}
          />
          <button type="button" disabled={sending} onClick={submitFeedback}>
            {sending ? "Отправляем..." : "Отправить отзыв"}
          </button>
        </div>
      )}
      {status && <p className="feedbackStatus">{status}</p>}
    </section>
  );
}

function ContextPanelActions({ onHistory, onDetails, onFeedback, showFeedback = false }) {
  return (
    <div className="contextPanelActions" aria-label="Дополнительные действия">
      <button type="button" onClick={onHistory}>История</button>
      <button type="button" onClick={onDetails}>Подробнее</button>
      {showFeedback && <button type="button" onClick={onFeedback}>Отзыв</button>}
    </div>
  );
}

function ContextOverlay({ title, subtitle, onClose, children }) {
  return (
    <div className="studioContextOverlay" role="dialog" aria-modal="true" aria-label={title}>
      <div className="studioContextBackdrop" onClick={onClose} />
      <section className="studioContextDrawer">
        <header>
          <div>
            <p className="studioPanelLabel">{subtitle}</p>
            <h2>{title}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Закрыть">×</button>
        </header>
        <div className="studioContextDrawerBody">
          {children}
        </div>
      </section>
    </div>
  );
}

function ContextStartPanel({ uploadLimitMb, onHistory }) {
  return (
    <section className="studioInspectorCard studioNextStepCard contextStartPanel">
      <p className="studioPanelLabel">Начало работы</p>
      <h2>Загрузите STL</h2>
      <p className="studioInspectorLead">Правая панель будет меняться по шагам: модель, анализ, обработка и результат. Сейчас нужен только файл.</p>
      <dl>
        <div><dt>Формат</dt><dd>.stl</dd></div>
        <div><dt>Лимит</dt><dd>{uploadLimitMb} МБ</dd></div>
        <div><dt>Демо</dt><dd>Отдельно</dd></div>
        <div><dt>История</dt><dd><button type="button" onClick={onHistory}>Открыть</button></dd></div>
      </dl>
    </section>
  );
}

function ContextModelPanel({ file, result, selectedPreset, settings, uploadLimitMb, onHistory, onDetails }) {
  const dimensions = result?.dimensions || {};
  const printability = result?.printability || {};
  const modelQa = result?.model_qa || {};
  const boundingBox =
    dimensions.width || dimensions.depth || dimensions.height
      ? `${formatMetric(dimensions.width)} × ${formatMetric(dimensions.depth)} × ${formatMetric(dimensions.height)} мм`
      : "После анализа";
  return (
    <>
      <section className="studioInspectorCard contextModelCard">
        <p className="studioPanelLabel">Текущая модель</p>
        <h2>{file?.name || "STL-модель"}</h2>
        <p className="studioInspectorLead">Здесь только данные текущего файла. История, отзывы и технические детали открываются отдельно.</p>
        <dl>
          <div><dt>Размер файла</dt><dd>{formatBytes(file?.size)}</dd></div>
          <div><dt>Треугольники</dt><dd>{formatMetric(result?.triangles ?? result?.triangles_count ?? modelQa.faces)}</dd></div>
          <div><dt>Размеры</dt><dd>{boundingBox}</dd></div>
          <div><dt>Объём</dt><dd>{formatMetric(result?.volume_cm3 ?? result?.volume, result?.volume_cm3 ? " см³" : "")}</dd></div>
          <div><dt>Поверхности</dt><dd>{formatMetric(result?.surfaces_count ?? modelQa.components)}</dd></div>
          <div><dt>Bounding Box</dt><dd>{boundingBox}</dd></div>
          <div><dt>Стол</dt><dd>{printability.bed_fit_220_220_250 === undefined ? "После анализа" : printability.bed_fit_220_220_250 ? "Помещается" : "Не помещается"}</dd></div>
          <div><dt>Лимит STL</dt><dd>{uploadLimitMb} МБ</dd></div>
        </dl>
      </section>

      <section className="studioInspectorCard studioOperationCard contextOperationCard">
        <p className="studioPanelLabel">Текущая операция</p>
        <h2>{selectedPreset.title}</h2>
        <p className="studioInspectorLead">{selectedPreset.description}</p>
        {settings}
      </section>

      <ContextPanelActions onHistory={onHistory} onDetails={onDetails} />
    </>
  );
}

function ContextAnalysisPanel({ result, onHistory, onDetails }) {
  const modelQa = result?.model_qa || {};
  const artifactQuality = modelQa.artifact_quality || {};
  const printability = result?.printability || {};
  const warnings = [
    ...(printability.warnings || []),
    Number(modelQa.open_edges || 0) > 0 ? `Открытые края: ${formatMetric(modelQa.open_edges)}` : null,
    Number(modelQa.non_manifold_edges || 0) > 0 ? `Non-manifold рёбра: ${formatMetric(modelQa.non_manifold_edges)}` : null,
    Number(modelQa.tiny_islands || 0) > 0 ? `Мелкие островки: ${formatMetric(modelQa.tiny_islands)}` : null,
    Number(artifactQuality.suspicious_regions || 0) > 0 ? `Подозрительные зоны: ${formatMetric(artifactQuality.suspicious_regions)}` : null,
  ].filter(Boolean);
  const recommendations = printability.recommendations || [];
  return (
    <>
      <section className="studioInspectorCard contextAnalysisCard">
        <p className="studioPanelLabel">Анализ модели</p>
        <h2>{modelQa.health_label || "Проверка завершена"}</h2>
        <div className="contextScore">
          <span>Оценка</span>
          <strong>{formatMetric(modelQa.health_score ?? result?.score ?? 0)}</strong>
        </div>
        <div className="contextIssueGrid">
          <span><em>Ошибки</em><strong>{formatMetric(Number(modelQa.non_manifold_edges || 0) + Number(modelQa.open_edges || 0))}</strong></span>
          <span><em>Предупреждения</em><strong>{formatMetric(warnings.length)}</strong></span>
          <span><em>Артефакты</em><strong>{formatMetric(artifactQuality.suspicious_regions)}</strong></span>
        </div>
      </section>

      <section className="studioInspectorCard contextListCard">
        <p className="studioPanelLabel">Что проверить</p>
        <h2>Ошибки и предупреждения</h2>
        {warnings.length ? (
          <ul>{warnings.slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul>
        ) : (
          <p>Критичных ошибок не найдено.</p>
        )}
      </section>

      <section className="studioInspectorCard contextListCard">
        <p className="studioPanelLabel">Рекомендации</p>
        <h2>Следующий шаг</h2>
        {recommendations.length ? (
          <ul>{recommendations.slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>
        ) : (
          <p>Можно выбрать ремонт, оптимизацию или подготовку к печати.</p>
        )}
      </section>

      <ContextPanelActions onHistory={onHistory} onDetails={onDetails} />
    </>
  );
}

function ContextProcessingPanel({ jobStatus, progress, statusMessage }) {
  const operations = Array.isArray(jobStatus?.operations) ? jobStatus.operations : [];
  const currentOperation = operations.map((operation) => operationTitles[operation] || operation).join(" · ") || "Подготовка результата";
  const isFailed = jobStatus?.status === "failed";
  return (
    <section className={`studioInspectorCard contextProcessingCard ${isFailed ? "failed" : ""}`}>
      <p className="studioPanelLabel">Обработка</p>
      <h2>{isFailed ? "Обработка остановлена" : "Идёт обработка"}</h2>
      <div className="contextProgressValue">
        <strong>{formatMetric(progress, "%")}</strong>
        <span>{currentOperation}</span>
      </div>
      <Progress value={progress} />
      <dl>
        <div><dt>Текущая операция</dt><dd>{currentOperation}</dd></div>
        <div><dt>Статус</dt><dd>{statusLabel(jobStatus?.status)}</dd></div>
        <div><dt>Ожидание</dt><dd>{formatDuration(jobStatus?.estimated_wait_seconds)}</dd></div>
        <div><dt>Следующий этап</dt><dd>{jobStatus?.status === "queued" ? "Запуск обработчика" : "Формирование результата"}</dd></div>
      </dl>
      <p className="contextQueueHint">Премиум-задачи обрабатываются быстрее.</p>
      <p>{statusMessage(jobStatus?.status, jobStatus?.message)}</p>
    </section>
  );
}

function ContextResultPanel({ apiBaseUrl, result, onCompare, onOpenResult, onRepeat, onHistory, onDetails, onFeedback, canRun, uploading }) {
  const generatedFiles = Array.isArray(result?.generated_files) ? result.generated_files : [];
  const zipUrl = result?.download_url;
  const stlUrl = getProcessedPreviewUrl(result);
  const jsonFile = generatedFiles.find((file) => String(file.name || "").toLowerCase().endsWith(".json") && !String(file.name || "").toLowerCase().includes("manifest"));
  const txtFile = generatedFiles.find((file) => String(file.name || "").toLowerCase().endsWith(".txt"));
  const fileUrl = (file) => file?.download_url || file?.url;

  return (
    <>
      <section className="studioInspectorCard contextResultCard">
        <p className="studioPanelLabel">Результат</p>
        <h2>Результат готов</h2>
        <p className="studioInspectorLead">Главное действие — скачать ZIP. Отдельные файлы и технические детали доступны по запросу.</p>
        {zipUrl && <a className="contextPrimaryDownload" href={`${apiBaseUrl}${zipUrl}`}>Скачать ZIP</a>}
        <span className="contextDownloadLabel">Дополнительные файлы</span>
        <div className="contextDownloadGrid">
          {stlUrl && <a href={`${apiBaseUrl}${stlUrl}`}>STL</a>}
          {jsonFile && <a href={`${apiBaseUrl}${fileUrl(jsonFile)}`}>JSON</a>}
          {txtFile && <a href={`${apiBaseUrl}${fileUrl(txtFile)}`}>TXT</a>}
        </div>
      </section>

      <section className="studioInspectorCard contextResultActions">
        <p className="studioPanelLabel">Действия</p>
        <button type="button" onClick={onCompare}>Сравнить</button>
        <button type="button" onClick={onOpenResult} disabled={!stlUrl}>Открыть результат</button>
        <button type="button" onClick={onRepeat} disabled={!canRun || uploading}>{uploading ? "Запускаем..." : "Повторить обработку"}</button>
      </section>

      <ContextPanelActions onHistory={onHistory} onDetails={onDetails} onFeedback={onFeedback} showFeedback />
    </>
  );
}

function AnalysisResult({
  result,
  jobStatus,
  apiBaseUrl,
  sourceFile,
  processedPreviewFile,
  activePanel,
  setActivePanel,
  compareMode,
  onCompareModeChange,
  onShowChanges,
  onFocusChanges,
  onShowArtifacts,
  onOpenHistoryFile,
  hasProcessedPreview,
  processedPreviewLoading,
  processedPreviewError,
  heatmapEnabled,
  heatmapData,
  heatmapLoading,
  heatmapError,
  artifactMapEnabled,
  artifactMapData,
  artifactMapLoading,
  artifactMapError,
  focusChangesVersion,
}) {
  if (!result) return null;

  const dimensions = result.dimensions || {};
  const printability = result.printability || {};
  const modelQa = result.model_qa;
  const artifactQuality = modelQa?.artifact_quality;
  const hasArtifactQuality =
    artifactQuality &&
    (Number(artifactQuality.suspicious_regions || 0) > 0 ||
      Number(artifactQuality.elongated_faces || 0) > 0 ||
      Number(artifactQuality.spikes_detected || 0) > 0);
  const warnings = printability.warnings || [];
  const recommendations = printability.recommendations || [];
  const plannedOperations = result.planned_operations || [];
  const printRepair = result.print_repair;
  const modelImprovement = result.model_improvement;
  const applyOrientation = result.apply_orientation;
  const autoOrientation = result.auto_orientation;
  const surfaceRecovery = result.surface_recovery;
  const localSmoothing = result.local_smoothing;
  const localSmoothingImpact = localSmoothingImpactLabel({
    selectedVertices: localSmoothing?.selected_vertices,
    changedVertices: localSmoothing?.changed_vertices,
    strength: localSmoothing?.strength,
  });
  const surfaceRecoveryDelta = surfaceRecovery?.delta || {};
  const surfaceRecoveryArtifactBefore = surfaceRecovery?.artifact_quality_before || {};
  const surfaceRecoveryArtifactAfter = surfaceRecovery?.artifact_quality_after || {};
  const surfaceRecoveryImproved = Boolean(
    Number(surfaceRecoveryDelta.health_score_delta || 0) > 0 ||
      Number(surfaceRecoveryDelta.artifact_penalty_delta || 0) < 0,
  );
  const cleanupScoreAfter = result.ai_cleanup?.health_score_after ?? result.remove_ai_artifacts?.health_score_after;
  const surfaceScoreAfter = surfaceRecovery?.health_score_after;
  const repairScoreAfter = printRepair?.qa_after?.health_score ?? printRepair?.qa_delta?.score_after;
  const qualityScoreBefore = modelQa?.health_score ?? printRepair?.qa_delta?.score_before;
  const qualityScoreAfter = surfaceScoreAfter ?? cleanupScoreAfter ?? repairScoreAfter ?? qualityScoreBefore;
  const qualityImprovement =
    typeof qualityScoreBefore === "number" && typeof qualityScoreAfter === "number"
      ? qualityScoreAfter - qualityScoreBefore
      : null;
  const hasQualityComparison = Boolean(modelQa && (surfaceRecovery || result.ai_cleanup || result.remove_ai_artifacts || printRepair));
  const hasChangeMap = Boolean(result.change_map?.available && result.change_map?.download_url);
  const hasArtifactMap = Boolean(result.artifact_map?.available && result.artifact_map?.download_url);
  const qualityGateRejected = Boolean(
    (result.remove_ai_artifacts && !result.remove_ai_artifacts.success && result.remove_ai_artifacts.quality_gate_passed === false) ||
      (printRepair && !printRepair.success && printRepair.quality_gate_passed === false)
  );
  const reduction = result.reduce_polygons;
  const splitModel = result.split_model;
  const fitToBedSplit = result.fit_to_bed_split;
  const symmetry = result.fix_symmetry;
  const skippedOperations = result.skipped_operations || [];
  const generatedFiles = result.generated_files || [];
  const improved = Boolean(printRepair || modelImprovement);
  const meshErrorsFixed = Boolean(printRepair?.success || modelImprovement?.summary?.mesh_errors_fixed || modelImprovement?.success);
  const removeArtifacts = result.remove_ai_artifacts;
  const artifactsRemoved = Number(printRepair?.removed_islands ?? modelImprovement?.components_removed ?? 0);
  const smoothingDone = Boolean(printRepair?.limited_smooth_applied || modelImprovement?.surface_smoothing || modelImprovement?.summary?.smoothing_applied);
  const polygonsBefore =
    result.remove_ai_artifacts?.faces_before ??
    surfaceRecovery?.faces_before ??
    printRepair?.faces_before ??
    modelImprovement?.faces_before ??
    modelImprovement?.summary?.faces_before ??
    result.triangles_count ??
    result.triangles;
  const polygonsAfter =
    result.remove_ai_artifacts?.faces_after ??
    surfaceRecovery?.faces_after ??
    printRepair?.faces_after ??
    modelImprovement?.faces_after ??
    modelImprovement?.summary?.faces_after ??
    polygonsBefore;
  const polygonDelta = typeof polygonsBefore === "number" && typeof polygonsAfter === "number" ? polygonsAfter - polygonsBefore : null;
  const processedFileIsTechnical =
    Boolean(result.final_model || result.after_file) &&
    (!qualityImprovement || qualityImprovement <= 0) &&
    (polygonDelta === 0 || polygonDelta === null);
  const resultTitle = qualityImprovement > 0
    ? `Улучшено на +${qualityImprovement} баллов`
    : processedFileIsTechnical
      ? "Технически обработанный файл"
      : "Серьёзных улучшений не найдено";
  const processingStages = [
    { id: "improve", title: "Улучшение модели", active: improved, success: Boolean(printRepair?.success || modelImprovement?.success) },
    { id: "cleanup", title: "Очистка AI-артефактов", active: Boolean(removeArtifacts), success: Boolean(removeArtifacts?.success) },
    {
      id: "surface",
      title: "Восстановление поверхности",
      active: Boolean(surfaceRecovery?.success || surfaceRecovery?.effect_detected),
      success: Boolean(surfaceRecovery?.success),
    },
    { id: "local", title: "Выборочная правка", active: Boolean(localSmoothing), success: Boolean(localSmoothing?.success) },
    { id: "reduction", title: "Уменьшение полигонов", active: Boolean(reduction), success: Boolean(reduction?.success) },
    { id: "symmetry", title: "Симметрия", active: Boolean(symmetry), success: Boolean(symmetry?.success) },
    { id: "orientation", title: "Ориентация", active: Boolean(applyOrientation), success: Boolean(applyOrientation?.success) },
    { id: "auto_orientation", title: "Автоориентация", active: Boolean(autoOrientation), success: Boolean(autoOrientation?.success) },
    { id: "fit_to_bed", title: "Разрезание под стол", active: Boolean(fitToBedSplit), success: Boolean(fitToBedSplit?.success) },
    { id: "split", title: "Разрезание модели", active: Boolean(splitModel), success: Boolean(splitModel?.success) },
  ].filter((stage) => stage.active);
  const processingHistory = Array.isArray(result.processing_history) ? result.processing_history : [];
  const hasProcessingHistory = processingHistory.length > 0;
  const fixedDefects = Math.max(
    0,
    Number(result.ai_cleanup?.delta?.suspicious_regions_delta || 0) * -1,
    Number(result.remove_ai_artifacts?.delta?.suspicious_regions_delta || 0) * -1,
    Number(printRepair?.holes_fixed || 0) + Number(printRepair?.removed_islands || 0) + Number(printRepair?.merged_vertices || 0),
  );
  const whatChangedItems = buildWhatChangedItems(result);

  return (
    <div className="analysisPanel">
      <div className="analysisHeader">
        <p className="panelLabel">Результат обработки</p>
        <h2>Что получилось</h2>
      </div>
      <CurrentResultBlock
        activePanel={activePanel}
        artifactMapData={artifactMapData}
        changeMapData={heatmapData}
        artifactMapLoading={artifactMapLoading}
        fixedDefects={fixedDefects}
        artifactMapEnabled={artifactMapEnabled}
        hasArtifactMap={hasArtifactMap}
        hasChangeMap={hasChangeMap}
        hasProcessedPreview={hasProcessedPreview}
        heatmapEnabled={heatmapEnabled}
        heatmapLoading={heatmapLoading}
        finalFile={processedPreviewFile}
        onCompare={(mode = "after") => {
          if (mode === "before" || mode === "after") {
            onCompareModeChange?.(mode);
          } else {
            onCompareModeChange?.("after");
          }
        }}
        onShowChanges={onShowChanges}
        onFocusChanges={onFocusChanges}
        onShowDefects={onShowArtifacts}
        qualityScoreAfter={qualityScoreAfter}
        qualityScoreBefore={qualityScoreBefore}
        result={result}
        setActivePanel={setActivePanel}
        sourceFile={sourceFile}
      />
      {whatChangedItems.length > 0 && (
        <section className="whatChangedPanel" data-what-changed="true">
          <div>
            <p className="panelLabel">Что изменилось</p>
            <h3>Коротко о результате</h3>
          </div>
          <div className="whatChangedGrid">
            {whatChangedItems.map((item) => (
              <article className="whatChangedCard" key={item.title}>
                <strong>{item.title}</strong>
                <ul>
                  {item.details.map((detail) => <li key={detail}>{detail}</li>)}
                </ul>
              </article>
            ))}
          </div>
        </section>
      )}
      {localSmoothing && (
        <div className={localSmoothing.success ? "localSmoothingSummary success" : "localSmoothingSummary warning"}>
          <div>
            <p className="panelLabel">Выборочная правка</p>
            <h3>{localSmoothing.success ? "Локальная правка выполнена" : "Выбранная область не была изменена"}</h3>
          </div>
          <div className="improveStats">
            <span>Областей: {formatMetric(localSmoothing.selected_regions)}</span>
            <span>Выбрано вершин: {formatMetric(localSmoothing.selected_vertices)}</span>
            <span>Выбрано граней: {formatMetric(localSmoothing.selected_faces)}</span>
            <span>Изменено вершин: {formatMetric(localSmoothing.changed_vertices)}</span>
            <span>Сила: {localSmoothing.strength || "balanced"}</span>
            <span>Влияние: {localSmoothingImpact}</span>
          </div>
          {!localSmoothing.success && (
            <p>Попробуйте увеличить радиус кисти. {localSmoothing.reason || ""}</p>
          )}
        </div>
      )}
      <div className="analysisGrid">
        <div>
          <span>Тип STL</span>
          <strong>{result.stl_type || "—"}</strong>
        </div>
        <div>
          <span>Треугольники</span>
          <strong>{formatMetric(result.triangles)}</strong>
        </div>
        <div>
          <span>Размер файла</span>
          <strong>{formatMetric(result.file?.size_mb, " МБ")}</strong>
        </div>
        <div>
          <span>Габариты</span>
          <strong>
            {formatMetric(dimensions.width)} × {formatMetric(dimensions.depth)} × {formatMetric(dimensions.height)}
          </strong>
        </div>
      </div>
      {modelQa && (
        <div className="printabilityPanel">
          <div className="analysisHeader">
            <p className="panelLabel">Состояние модели</p>
            <h2>{modelQa.health_label || "—"}</h2>
          </div>
          <div className="printabilitySummary">
            <div className={modelQa.health_score >= 75 ? "fitBadge fitOk" : "fitBadge fitWarn"}>
              {formatMetric(modelQa.health_score, "/100")}
            </div>
            <div>
              <span>Ремонт</span>
              <strong>{modelQa.repair_recommended ? "рекомендуется" : "не требуется"}</strong>
            </div>
          </div>
          <div className="improveStats">
            <span>Открытые рёбра: {formatMetric(modelQa.open_edges)}</span>
            <span>Non-manifold: {formatMetric(modelQa.non_manifold_edges)}</span>
            <span>Дубликаты граней: {formatMetric(modelQa.duplicate_faces)}</span>
            <span>Вырожденные грани: {formatMetric(modelQa.degenerate_faces)}</span>
            <span>Компонентов: {formatMetric(modelQa.components)}</span>
            <span>Мелких островков: {formatMetric(modelQa.tiny_islands)}</span>
            {artifactQuality && (
              <>
                <span>Подозрительных участков: {formatMetric(artifactQuality.suspicious_regions)}</span>
                <span>Вытянутых полигонов: {formatMetric(artifactQuality.elongated_faces)}</span>
                <span>Шипов и наростов: {formatMetric(artifactQuality.spikes_detected)}</span>
              </>
            )}
          </div>
          {hasArtifactQuality && (
            <p className="resultNote">Найдены возможные AI-артефакты. Рекомендуется очистка или улучшение модели.</p>
          )}
          {hasArtifactMap && (
            <button className="showChangesButton" type="button" disabled={artifactMapLoading} onClick={onShowArtifacts}>
              {artifactMapLoading ? "Загружаем дефекты..." : "Показать дефекты"}
            </button>
          )}
          {artifactMapError && <p className="improveHint">{artifactMapError}</p>}
        </div>
      )}
      {hasChangeMap && !hasQualityComparison && (
        <div className="changeMapPanel">
          <div>
            <p className="panelLabel">Карта изменений</p>
            <h2>Можно подсветить изменённые участки</h2>
          </div>
          <p>В 3D-просмотре исходная модель будет показана серым, а обработанная — с подсветкой изменений.</p>
          <button className="showChangesButton" type="button" disabled={!hasProcessedPreview || heatmapLoading} onClick={() => onShowChanges?.()}>
            {heatmapLoading ? "Загружаем сравнение..." : "Сравнить модели"}
          </button>
          {heatmapError && <p className="improveHint">{heatmapError}</p>}
        </div>
      )}
      {hasQualityComparison && (
        <div className="printabilityPanel">
          <div className="analysisHeader">
            <p className="panelLabel">Качество модели</p>
            <h2>{resultTitle}</h2>
          </div>
          <div className="beforeAfterToggle" aria-label="Сравнение модели">
            <button
              className={compareMode === "before" ? "active" : ""}
              type="button"
              onClick={() => onCompareModeChange?.("before")}
            >
              До обработки
            </button>
            <button
              className={compareMode === "after" ? "active" : ""}
              type="button"
              disabled={!hasProcessedPreview}
              onClick={() => onCompareModeChange?.("after")}
            >
              После обработки
            </button>
          </div>
          {processedPreviewLoading && <p className="improveHint">Загружаем обработанную модель...</p>}
          {!processedPreviewLoading && processedPreviewError && <p className="improveHint">{processedPreviewError}</p>}
          <div className="analysisGrid">
            <div>
              <span>До обработки</span>
              <strong>{formatMetric(qualityScoreBefore, "/100")}</strong>
            </div>
            <div>
              <span>После обработки</span>
              <strong>{formatMetric(qualityScoreAfter, "/100")}</strong>
            </div>
            <div>
              <span>Найдено AI-артефактов</span>
              <strong>{formatMetric(surfaceRecovery?.regions_detected ?? result.ai_cleanup?.suspicious_regions ?? artifactQuality?.suspicious_regions)}</strong>
            </div>
            <div>
              <span>Вытянутых полигонов</span>
              <strong>{formatMetric(result.ai_cleanup?.elongated_faces ?? artifactQuality?.elongated_faces)}</strong>
            </div>
            <div>
              <span>Компонентов</span>
              <strong>{formatMetric(modelQa.components)}</strong>
            </div>
            <div>
              <span>Итоговый файл</span>
              <strong>{result.final_model || result.after_file || "—"}</strong>
            </div>
          </div>
          {qualityImprovement > 0 ? (
            <p className="resultNote">Обработанная модель доступна в 3D-просмотре и в составе результата.</p>
          ) : processedFileIsTechnical ? (
            <p className="resultNote">Технически обработанный файл доступен для просмотра. Визуальные изменения могут быть незаметны.</p>
          ) : (
            <p className="resultNote">Серьёзных улучшений не найдено. Модель уже была достаточно чистой.</p>
          )}
          <div className="improveStats">
            <span>Найдено: {formatMetric(surfaceRecovery?.regions_detected ?? result.ai_cleanup?.suspicious_regions ?? artifactQuality?.suspicious_regions)} подозрительных участков</span>
            <span>Исправлено: {qualityImprovement > 0 ? `+${qualityImprovement} баллов` : "без заметного роста рейтинга"}</span>
            <span>Не изменилось: {polygonDelta === 0 ? "количество полигонов" : "—"}</span>
          </div>
          {qualityGateRejected && (
            <p className="improveHint">Обработка отклонена, чтобы не повредить модель.</p>
          )}
          <button className="showChangesButton" type="button" disabled={!hasChangeMap || !hasProcessedPreview || heatmapLoading} onClick={() => onShowChanges?.()}>
            {heatmapLoading ? "Загружаем сравнение..." : "Сравнить модели"}
          </button>
          {heatmapError && <p className="improveHint">{heatmapError}</p>}
        </div>
      )}
      <CurrentModelSummary
        activePanel={activePanel}
        history={processingHistory}
        qualityScoreAfter={qualityScoreAfter}
        qualityScoreBefore={qualityScoreBefore}
        result={result}
        setActivePanel={setActivePanel}
      />
      <JobInfoPanel jobStatus={jobStatus} result={result} />
      <FeedbackPanel apiBaseUrl={apiBaseUrl} jobStatus={jobStatus} />
      {hasProcessingHistory ? (
        <ProcessingHistoryTimeline
          activePanel={activePanel}
          generatedFiles={generatedFiles}
          history={processingHistory}
          onOpenFile={onOpenHistoryFile}
          onShowChanges={onShowChanges}
          onShowArtifacts={onShowArtifacts}
          setActivePanel={setActivePanel}
        heatmapLoading={heatmapLoading}
        focusChangesVersion={focusChangesVersion}
          artifactMapLoading={artifactMapLoading}
        />
      ) : processingStages.length > 0 && (
        <div className="processingHistory">
          <div className="analysisHeader compactHeader">
            <p className="panelLabel">История обработки</p>
            <h2>Этапы результата</h2>
          </div>
          {improved && (
            <ProcessingStage activePanel={activePanel} id="result:improve" setActivePanel={setActivePanel} title="Улучшение модели" success={Boolean(printRepair?.success || modelImprovement?.success)}>
              <div className={modelImprovement?.success ? "improvePanel improveOk" : "improvePanel improveWarn"}>
                <div>
                  <p className="panelLabel">Улучшение модели</p>
                  <h2>{qualityImprovement > 0 ? "Модель улучшена" : "Техническая обработка выполнена"}</h2>
                </div>
                <p>
                  Готовит STL к печати: объединяет близкие вершины, удаляет loose geometry, закрывает небольшие отверстия и пересчитывает нормали.
                </p>
                <div className="improveStats">
                  <span>Исправлено отверстий: {formatMetric(printRepair?.holes_fixed ?? 0)}</span>
                  <span>Удалено островков: {artifactsRemoved}</span>
                  <span>Объединено дубликатов вершин: {formatMetric(printRepair?.merged_vertices ?? 0)}</span>
                  <span>Пересчитаны нормали: {printRepair?.normals_recalculated || meshErrorsFixed ? "да" : "нет"}</span>
                  <span>Полигонов до/после: {formatMetric(polygonsBefore)} / {formatMetric(polygonsAfter)}</span>
                  <span>Изменено количество полигонов: {polygonDelta === null ? "—" : `${polygonDelta > 0 ? "+" : ""}${polygonDelta}`}</span>
                </div>
                {printRepair?.quality_gate?.reason && <p className="improveHint">{printRepair.quality_gate.reason}</p>}
                {printRepair?.message && <p className="improveHint">{printRepair.message}</p>}
                {printRepair?.qa_delta && (
                  <div className="improveStats">
                    <span>Найдено открытых рёбер: {formatMetric(printRepair.qa_delta.found?.open_edges)}</span>
                    <span>Исправлено открытых рёбер: {formatMetric(printRepair.qa_delta.fixed?.open_edges)}</span>
                    <span>Осталось открытых рёбер: {formatMetric(printRepair.qa_delta.remaining?.open_edges)}</span>
                    <span>Рейтинг до/после: {formatMetric(printRepair.qa_delta.score_before)} / {formatMetric(printRepair.qa_delta.score_after)}</span>
                  </div>
                )}
                {printRepair && !printRepair.success && (
                  <p className="improveHint">{printRepair.quality_gate?.reason || printRepair.warning || "Ремонт не применён: quality gate отклонил результат."}</p>
                )}
                {modelImprovement?.fallback_used && !printRepair && (
                  <p className="improveHint">Blender недоступен или не завершил обработку, поэтому использован быстрый безопасный вариант.</p>
                )}
                {modelImprovement?.notes?.some((note) => note.includes("визуально почти не измениться")) && (
                  <p className="improveHint">Изменения могут быть техническими: модель станет корректнее, но визуально почти не изменится.</p>
                )}
                {modelImprovement?.warnings?.length > 0 && (
                  <ul className="improveWarnings">
                    {modelImprovement.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                  </ul>
                )}
              </div>
            </ProcessingStage>
          )}
          {removeArtifacts && (
            <ProcessingStage activePanel={activePanel} id="result:cleanup" setActivePanel={setActivePanel} title="Очистка AI-артефактов" success={Boolean(removeArtifacts.success)}>
              <div className={removeArtifacts.success ? "aiCleanupPanel aiCleanupOk" : "aiCleanupPanel aiCleanupWarn"}>
                <div>
                  <p className="panelLabel">Удаление AI-артефактов</p>
                  <h2>{removeArtifacts.success ? "Модель очищена" : "Очистка не применена"}</h2>
                </div>
                <p>
                  Удаляет только отдельные мусорные островки и disconnected components без резкого изменения формы.
                </p>
                <div className="aiCleanupStats">
                  <span>Найдено артефактов: {formatMetric(removeArtifacts.suspicious_regions)}</span>
                  <span>Найдено шипов: {formatMetric(removeArtifacts.spikes_detected)}</span>
                  <span>Вытянутых полигонов: {formatMetric(removeArtifacts.elongated_faces)}</span>
                  <span>Сглаживание: {removeArtifacts.smoothing_applied ? "применено" : "нет"}</span>
                  <span>Удалено фрагментов: {Number(removeArtifacts.removed_components || 0)}</span>
                  <span>Компонентов было: {formatMetric(removeArtifacts.components_before)}</span>
                  <span>Компонентов стало: {formatMetric(removeArtifacts.components_after)}</span>
                  <span>Граней было: {formatMetric(removeArtifacts.faces_before)}</span>
                  <span>Граней стало: {formatMetric(removeArtifacts.faces_after)}</span>
                  <span>Результат: {removeArtifacts.quality_gate_passed ? "принят" : "отклонён"}</span>
                </div>
                {removeArtifacts.output_file && (
                  <p>
                    Файл <strong>{removeArtifacts.output_file}</strong> добавлен в ZIP как очищенная модель.
                  </p>
                )}
                {!removeArtifacts.success && (
                  <p>Очистка могла повредить модель, поэтому результат не был применён.</p>
                )}
                {removeArtifacts.reason && (
                  <p className="aiCleanupHint">Причина: {removeArtifacts.reason}</p>
                )}
              </div>
            </ProcessingStage>
          )}
          {surfaceRecovery && (
            <ProcessingStage activePanel={activePanel} id="result:surface" setActivePanel={setActivePanel} title="Восстановление поверхности" success={Boolean(surfaceRecovery.success && surfaceRecoveryImproved)}>
              <div className={surfaceRecovery.success ? "surfaceRecoveryPanel surfaceRecoveryOk" : "surfaceRecoveryPanel surfaceRecoveryWarn"}>
                <div>
                  <p className="panelLabel">Восстановить поверхность</p>
                  <h2>{surfaceRecovery.success && surfaceRecoveryImproved ? "Поверхность восстановлена" : "Заметных улучшений не найдено"}</h2>
                </div>
                {surfaceRecovery.success && surfaceRecoveryImproved ? (
                  <p>
                    Локально сглаживает найденные проблемные зоны: рябь, волнистость, бугры, складки и неестественные пики.
                  </p>
                ) : (
                  <p>
                    Поверхность уже находится в хорошем состоянии. Заметных улучшений не обнаружено.
                  </p>
                )}
                <div className="aiCleanupStats">
                  <span>Проблемных зон: {formatMetric(surfaceRecovery.regions_detected)}</span>
                  <span>Исправлено вершин: {formatMetric(surfaceRecovery.vertices_modified)}</span>
                  <span>Полигонов до: {formatMetric(surfaceRecovery.faces_before)}</span>
                  <span>Полигонов после: {formatMetric(surfaceRecovery.faces_after)}</span>
                  <span>Качество до: {formatMetric(surfaceRecovery.health_score_before, "/100")}</span>
                  <span>Качество после: {formatMetric(surfaceRecovery.health_score_after, "/100")}</span>
                  <span>Изменение качества: {formatMetric(surfaceRecoveryDelta.health_score_delta, " баллов")}</span>
                  <span>Штраф за артефакты до: {formatMetric(surfaceRecoveryArtifactBefore.artifact_score_penalty)}</span>
                  <span>Штраф за артефакты после: {formatMetric(surfaceRecoveryArtifactAfter.artifact_score_penalty)}</span>
                  <span>Изменение штрафа: {formatMetric(surfaceRecoveryDelta.artifact_penalty_delta)}</span>
                  <span>Подозрительных участков: {formatMetric(surfaceRecoveryDelta.suspicious_regions_delta)}</span>
                  <span>Вытянутых полигонов: {formatMetric(surfaceRecoveryDelta.elongated_faces_delta)}</span>
                </div>
                {surfaceRecovery.success && surfaceRecoveryImproved && surfaceRecovery.output_file && (
                  <p>
                    Файл <strong>{surfaceRecovery.output_file}</strong> добавлен в ZIP как модель с восстановленной поверхностью.
                  </p>
                )}
                {surfaceRecovery.reason && <p className="aiCleanupHint">{surfaceRecovery.reason}</p>}
              </div>
            </ProcessingStage>
          )}
          {localSmoothing && (
            <ProcessingStage activePanel={activePanel} id="result:local" setActivePanel={setActivePanel} title="Выборочная правка" success={Boolean(localSmoothing.success)}>
              <div className={localSmoothing.success ? "localSmoothingPanel localSmoothingOk" : "localSmoothingPanel localSmoothingWarn"}>
                <div>
                  <p className="panelLabel">Выборочная правка</p>
                  <h2>{localSmoothing.success ? "Локальная правка выполнена" : "Выбранная область не была изменена"}</h2>
                </div>
                {localSmoothing.success ? (
                  <p>
                    Файл <strong>{localSmoothing.output_file}</strong> создан только для выбранной области. Используйте “Сравнить модели”, чтобы увидеть изменения.
                  </p>
                ) : (
                  <p>
                    Выбранная область не была изменена. Попробуйте увеличить радиус кисти.
                  </p>
                )}
                <div className="aiCleanupStats">
                  <span>Областей: {formatMetric(localSmoothing.selected_regions)}</span>
                  <span>Выбрано вершин: {formatMetric(localSmoothing.selected_vertices)}</span>
                  <span>Выбрано граней: {formatMetric(localSmoothing.selected_faces)}</span>
                  <span>Изменено вершин: {formatMetric(localSmoothing.changed_vertices)}</span>
                  <span>Сила: {localSmoothing.strength || "balanced"}</span>
                  <span>Влияние: {localSmoothingImpact}</span>
                  <span>BBox: {formatMetric(localSmoothing.bbox_change_percent, "%")}</span>
                  <span>Объём: {formatMetric(localSmoothing.volume_change_percent, "%")}</span>
                  <span>Quality gate: {localSmoothing.quality_gate_passed ? "пройден" : "не пройден"}</span>
                </div>
                {localSmoothing.reason && <p className="aiCleanupHint">{localSmoothing.reason}</p>}
              </div>
            </ProcessingStage>
          )}
          {reduction && (
            <ProcessingStage activePanel={activePanel} id="result:reduction" setActivePanel={setActivePanel} title="Уменьшение полигонов" success={Boolean(reduction.success)}>
              <div className={reduction.success ? "reductionPanel reductionOk" : "reductionPanel reductionWarn"}>
                <div>
                  <p className="panelLabel">Уменьшение полигонов</p>
                  <h2>{reduction.success ? "Модель стала легче" : "Не удалось уменьшить модель"}</h2>
                </div>
                {reduction.success ? (
                  <p>
                    Файл <strong>reduced.stl</strong> добавлен в ZIP. Цель: уменьшить полигоны примерно на {reduction.reduction_percent}%.
                  </p>
                ) : (
                  <p>
                    Задача завершена без ошибки, но уменьшение не выполнено. Причина: {reduction.reason || "способ уменьшения недоступен"}.
                  </p>
                )}
                <div className="reductionStats">
                  <span>Было граней: {formatMetric(reduction.original_faces)}</span>
                  <span>Цель: {formatMetric(reduction.target_faces)}</span>
                  <span>Стало: {formatMetric(reduction.reduced_faces)}</span>
                </div>
              </div>
            </ProcessingStage>
          )}
          {symmetry && (
            <ProcessingStage activePanel={activePanel} id="result:symmetry" setActivePanel={setActivePanel} title="Симметрия" success={Boolean(symmetry.success)}>
              <div className={symmetry.success ? "symmetryPanel symmetryOk" : "symmetryPanel symmetryWarn"}>
                <div>
                  <p className="panelLabel">Симметрия</p>
                  <h2>{symmetry.mode === "fix" ? "Проверка и исправление" : "Анализ симметрии"}</h2>
                </div>
                <div className="symmetryScore">
                  <span>Симметрия</span>
                  <strong>{formatMetric(symmetry.symmetry_score_before ?? symmetry.symmetry_score, "%")}</strong>
                </div>
                {symmetry.mode === "fix" && (
                  <div className="symmetryStats">
                    <span>До: {formatMetric(symmetry.symmetry_score_before, "%")}</span>
                    <span>После: {formatMetric(symmetry.symmetry_score_after, "%")}</span>
                    <span>Ось: {(symmetry.symmetry_axis || "x").toUpperCase()}</span>
                  </div>
                )}
                {symmetry.output_file && <p>Файл <strong>{symmetry.output_file}</strong> добавлен в результат.</p>}
                {!symmetry.success && <p>{symmetry.reason || "Исправление не применено, исходная модель сохранена."}</p>}
              </div>
            </ProcessingStage>
          )}
          {applyOrientation && (
            <ProcessingStage activePanel={activePanel} id="result:orientation" setActivePanel={setActivePanel} title="Ориентация" success={Boolean(applyOrientation.success)}>
              <div className={applyOrientation.success ? "orientationPanel orientationOk" : "orientationPanel orientationWarn"}>
        <div>
          <p className="panelLabel">Ориентация применена</p>
          <h2>{applyOrientation.success ? "Поворот сохранён в STL" : "Ориентация не применена"}</h2>
          </div>
          <p>
            Визуальный поворот из 3D-просмотра сохранён в итоговом файле. Кнопка “После обработки” открывает ориентированную модель.
          </p>
          <div className="beforeAfterToggle" aria-label="Сравнение ориентации">
            <button
              className={compareMode === "before" ? "active" : ""}
              type="button"
              onClick={() => onCompareModeChange?.("before")}
            >
              До обработки
            </button>
            <button
              className={compareMode === "after" ? "active" : ""}
              type="button"
              disabled={!hasProcessedPreview}
              onClick={() => onCompareModeChange?.("after")}
            >
              После обработки
            </button>
          </div>
          {processedPreviewLoading && <p className="improveHint">Загружаем обработанную модель...</p>}
          {!processedPreviewLoading && processedPreviewError && <p className="improveHint">{processedPreviewError}</p>}
          <div className="improveStats">
            <span>X: {formatMetric(applyOrientation.rotation?.x, "°")}</span>
            <span>Y: {formatMetric(applyOrientation.rotation?.y, "°")}</span>
            <span>Z: {formatMetric(applyOrientation.rotation?.z, "°")}</span>
            <span>Поставлена на стол: {applyOrientation.translated_to_floor ? "да" : "нет"}</span>
            <span>Итоговый файл: {applyOrientation.output_file || "—"}</span>
          </div>
          {!applyOrientation.success && (
            <p className="improveHint">{applyOrientation.reason || "Ориентация не применена: итоговый STL не прошёл проверку."}</p>
          )}
        </div>
            </ProcessingStage>
      )}
	      {autoOrientation && (
	            <ProcessingStage activePanel={activePanel} id="result:auto_orientation" setActivePanel={setActivePanel} title="Автоориентация" success={Boolean(autoOrientation.success)}>
	              <div className={autoOrientation.success ? "orientationPanel orientationOk" : "orientationPanel orientationWarn"}>
          <div>
            <p className="panelLabel">Ориентация для печати подобрана</p>
            <h2>{autoOrientation.no_change_needed ? "Текущее положение уже оптимально" : autoOrientation.success ? "Лучшее положение выбрано" : "Ориентация не выбрана"}</h2>
          </div>
          <p>{autoOrientation.recommendation || "Если сервис не уверен, выберите ориентацию вручную в 3D-просмотре."}</p>
          <div className="beforeAfterToggle" aria-label="Сравнение автоориентации">
            <button
              className={compareMode === "before" ? "active" : ""}
              type="button"
              onClick={() => onCompareModeChange?.("before")}
            >
              До обработки
            </button>
            <button
              className={compareMode === "after" ? "active" : ""}
              type="button"
              disabled={!hasProcessedPreview || autoOrientation.no_change_needed}
              onClick={() => onCompareModeChange?.("after")}
            >
              После обработки
            </button>
          </div>
          {processedPreviewLoading && <p className="improveHint">Загружаем обработанную модель...</p>}
          {!processedPreviewLoading && processedPreviewError && <p className="improveHint">{processedPreviewError}</p>}
          <div className="improveStats">
            <span>Вариант: {autoOrientation.selected_candidate || "—"}</span>
            <span>Приоритет: {orientationPriorityTitles[autoOrientation.priority] || "Меньше поддержек"}</span>
            <span>Риск поддержек: {formatMetric(autoOrientation.metrics?.support_risk, "%")}</span>
            <span>Устойчивость: {formatMetric(autoOrientation.metrics?.stability_score)}</span>
            <span>Высота: {formatMetric(autoOrientation.metrics?.height, " мм")}</span>
            <span>Площадь опоры: {formatMetric(autoOrientation.metrics?.footprint_area, " мм²")}</span>
          </div>
          {!autoOrientation.success && (
            <p className="improveHint">{autoOrientation.reason || "Автоориентация не применена: выберите положение вручную."}</p>
          )}
	        </div>
	            </ProcessingStage>
	      )}
          {fitToBedSplit && (
            <ProcessingStage activePanel={activePanel} id="result:fit_to_bed" setActivePanel={setActivePanel} title="Разрезание под стол" success={Boolean(fitToBedSplit.success)}>
              <div className={fitToBedSplit.success ? "splitPanel splitOk" : "splitPanel splitWarn"}>
                <div>
                  <p className="panelLabel">Разрезание под стол</p>
                  <h2>
                    {fitToBedSplit.no_split_needed
                      ? "Модель уже помещается"
                      : fitToBedSplit.success
                        ? "Части под стол созданы"
                        : "Разрезание под стол не выполнено"}
                  </h2>
                </div>
                <div className="splitSummary">
                  <span>
                    Стол: {formatMetric(fitToBedSplit.bed_size?.x, " мм")} × {formatMetric(fitToBedSplit.bed_size?.z, " мм")} × {formatMetric(fitToBedSplit.bed_size?.y, " мм")}
                  </span>
                  <span>
                    Модель: {formatMetric(fitToBedSplit.model_size_before?.x, " мм")} × {formatMetric(fitToBedSplit.model_size_before?.z, " мм")} × {formatMetric(fitToBedSplit.model_size_before?.y, " мм")}
                  </span>
                  <span>Частей: {formatMetric(fitToBedSplit.total_parts)}</span>
                  <span>Все части помещаются: {fitToBedSplit.all_parts_fit_bed ? "да" : "нет"}</span>
                </div>
                {fitToBedSplit.no_split_needed ? (
                  <p>{fitToBedSplit.recommendation || "Модель уже помещается на выбранный стол."}</p>
                ) : fitToBedSplit.success ? (
                  <>
                    <p>{fitToBedSplit.recommendation || "Модель разделена на печатные части."}</p>
                    <div className="splitFiles">
                      {(fitToBedSplit.output_files || []).map((fileName) => <span key={fileName}>{fileName}</span>)}
                    </div>
                  </>
                ) : (
                  <p>
                    Задача завершена без ошибки, но автоматический раскрой не применён. Причина: {fitToBedSplit.reason || "модель не удалось безопасно разделить"}.
                  </p>
                )}
                {fitToBedSplit.connectors?.mode && fitToBedSplit.connectors.mode !== "none" && (
                  <div className="connectorNotice">
                    <strong>Соединители</strong>
                    <span>{fitToBedSplit.connectors.mode === "pins" ? "Штифты" : "Пазы"}</span>
                    <p>{fitToBedSplit.connectors.reason || "Соединители будут встроены только после успешной проверки качества."}</p>
                  </div>
                )}
              </div>
            </ProcessingStage>
          )}
          {splitModel && (
            <ProcessingStage activePanel={activePanel} id="result:split" setActivePanel={setActivePanel} title="Разрезание модели" success={Boolean(splitModel.success)}>
              <div className={splitModel.success ? "splitPanel splitOk" : "splitPanel splitWarn"}>
                <div>
                  <p className="panelLabel">Разрезание модели</p>
                  <h2>{splitModel.success ? "Части модели созданы" : "Не удалось разрезать модель"}</h2>
                </div>
                {splitModel.success ? (
                  <div>
                    <div className="splitSummary">
                      <span>Режим: {splitModeTitles[splitModel.split_mode] || "Простой разрез"}</span>
                      <span>Частей: {splitModel.split_parts || splitModel.output_files.length}</span>
                    </div>
                    <p>После разрезания модель состоит из отдельных частей. Скачайте ZIP или отдельные части.</p>
                    <div className="splitFiles">
                      {splitModel.output_files.map((fileName) => <span key={fileName}>{fileName}</span>)}
                    </div>
                    {splitModel.connectors?.integrated ? (
                      <div className="connectorNotice">
                        <strong>Соединители встроены в детали</strong>
                        <span>Размер: {splitModel.connectors.connector_size_mm || splitModel.connector_size_mm} мм · Зазор: {splitModel.connectors.connector_clearance_mm || splitModel.connector_clearance_mm} мм · Количество: {splitModel.connectors.connector_count || splitModel.connector_count}</span>
                        <p>{splitModel.connectors.qa?.assembly_check_passed ? "Посадка соединителей проверена." : "Требуется ручная проверка соединителей."}</p>
                        {splitModel.connectors.qa && (
                          <span>
                            Clearance: {splitModel.connectors.qa.minimum_clearance_mm ?? "—"} мм · Intersection: {splitModel.connectors.qa.maximum_intersection_mm ?? "—"} мм
                          </span>
                        )}
                      </div>
                    ) : (splitModel.connectors?.files?.length > 0 || splitModel.connectors?.connector_files?.length > 0) && (
                      <div className="connectorNotice">
                        <strong>Соединители созданы отдельными файлами-подсказками</strong>
                        <span>{(splitModel.connectors.files || splitModel.connectors.connector_files).join(", ")}</span>
                        <p>{splitModel.connectors.reason || splitModel.connectors.note || "Встроить соединители автоматически не удалось."}</p>
                        <p>Требуется ручная проверка соединителей.</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <p>
                    Задача завершена без ошибки, но разрезание не выполнено. Причина: {splitModel.reason || "модель не удалось разделить"}.
                  </p>
                )}
              </div>
            </ProcessingStage>
          )}
        </div>
      )}
      <div className="printabilityPanel">
        <div className="analysisHeader">
          <p className="panelLabel">Проверка к печати</p>
          <h2>Стол 220x220x250 мм</h2>
        </div>
        <div className="printabilitySummary">
          <div className={printability.bed_fit_220_220_250 ? "fitBadge fitOk" : "fitBadge fitWarn"}>
            {printability.bed_fit_220_220_250 ? "Подходит" : "Не подходит"}
          </div>
          <div>
            <span>Класс размера</span>
            <strong>{printability.size_class || "—"}</strong>
          </div>
        </div>
        <div className="noticeGrid">
          <div>
            <h3>Предупреждения</h3>
            {warnings.length > 0 ? (
              <ul>
                {warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            ) : (
              <p>Критичных предупреждений нет.</p>
            )}
          </div>
          <div>
            <h3>Рекомендации</h3>
            {recommendations.length > 0 ? (
              <ul>
                {recommendations.map((item) => <li key={item}>{item}</li>)}
              </ul>
            ) : (
              <p>Дополнительные действия не требуются.</p>
            )}
          </div>
        </div>
      </div>
      {skippedOperations.length > 0 && (
        <div className="skippedPanel">
          <h2>Некоторые операции пропущены для защиты сервера</h2>
          <ul>
            {skippedOperations.map((item) => (
              <li key={item.operation}>
                <strong>{operationTitles[item.operation] || item.operation}</strong>: {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      <GeneratedFilesBlock files={generatedFiles} />
      {result.download_ready && result.download_url && (
        <a className="downloadButton" href={`${getApiBaseUrl()}${result.download_url}`}>
          Скачать всё ZIP
        </a>
      )}
      {result.package_ready && (
        <div className="packageReady">
          <strong>Пакет подготовки создан</strong>
          <span>В ZIP лежат модели, отчёты и список созданных файлов.</span>
        </div>
      )}
      {plannedOperations.length > 0 && (
        <div className="plannedOperations">
          <h3>Будущие операции</h3>
          {plannedOperations.map((item) => (
            <span key={item.operation}>{operationTitles[item.operation] || item.title}: скоро</span>
          ))}
        </div>
      )}
    </div>
  );
}

function App() {
  const studioFileInputRef = useRef(null);
  const [publicView, setPublicView] = useState(() => (window.location.pathname === "/app" ? "app" : "home"));
  const [demoMode, setDemoMode] = useState(false);
  const [accessGateMessage, setAccessGateMessage] = useState("");
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [featureFlags, setFeatureFlags] = useState(DEFAULT_FEATURE_FLAGS);
  const [accessCode, setAccessCode] = useState(() => localStorage.getItem(ACCESS_CODE_STORAGE_KEY) || "");
  const [currentUser, setCurrentUser] = useState(null);
  const [currentUserLoading, setCurrentUserLoading] = useState(true);
  const [currentUserError, setCurrentUserError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [selectedMode, setSelectedMode] = useState("check");
  const [activePanel, setActivePanel] = useState("settings:check");
  const [reductionPercent, setReductionPercent] = useState(50);
  const [splitAxis, setSplitAxis] = useState("z");
  const [splitParts, setSplitParts] = useState(2);
  const [splitMode, setSplitMode] = useState("simple");
  const [splitPlaneOffset, setSplitPlaneOffset] = useState(0);
  const [connectorSize, setConnectorSize] = useState(4);
  const [connectorClearance, setConnectorClearance] = useState(0.25);
  const [connectorCount, setConnectorCount] = useState(2);
  const [connectorDepth, setConnectorDepth] = useState(6);
  const [connectorWallThickness, setConnectorWallThickness] = useState(1.2);
  const [connectorPlacement, setConnectorPlacement] = useState("auto");
  const [magnetSize, setMagnetSize] = useState("6x2");
  const [lockProfile, setLockProfile] = useState("tongue_groove");
  const [bedSizePreset, setBedSizePreset] = useState("220");
  const [bedSizeX, setBedSizeX] = useState(220);
  const [bedSizeY, setBedSizeY] = useState(250);
  const [bedSizeZ, setBedSizeZ] = useState(220);
  const [bedConnectorMode, setBedConnectorMode] = useState("none");
  const [bedConnectorClearance, setBedConnectorClearance] = useState(0.25);
  const [symmetryAxis, setSymmetryAxis] = useState("x");
  const [symmetryMode, setSymmetryMode] = useState("analyze");
  const [modelImprovementStrength, setModelImprovementStrength] = useState("balanced");
  const [artifactCleanupStrength, setArtifactCleanupStrength] = useState("balanced");
  const [localSelectionRadius, setLocalSelectionRadius] = useState(10);
  const [localSmoothingStrength, setLocalSmoothingStrength] = useState("balanced");
  const [localSelectionMode, setLocalSelectionMode] = useState("point");
  const [localSelection, setLocalSelection] = useState(null);
  const [orientationPriority, setOrientationPriority] = useState("supports");
  const [modelName, setModelName] = useState("");
  const [orientationTransform, setOrientationTransform] = useState({
    rotation_x: 0,
    rotation_y: 0,
    rotation_z: 0,
    rotation_x_deg: 0,
    rotation_y_deg: 0,
    rotation_z_deg: 0,
    translate_to_floor: false,
    translate_x_mm: 0,
    translate_z_mm: 0,
  });
  const [bedMoveStep, setBedMoveStep] = useState(5);
  const [previewMode, setPreviewMode] = useState("before");
  const [processedPreviewFile, setProcessedPreviewFile] = useState(null);
  const [processedPreviewLoading, setProcessedPreviewLoading] = useState(false);
  const [processedPreviewError, setProcessedPreviewError] = useState("");
  const [heatmapEnabled, setHeatmapEnabled] = useState(false);
  const [heatmapData, setHeatmapData] = useState(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState("");
  const [focusChangesVersion, setFocusChangesVersion] = useState(0);
  const [artifactMapEnabled, setArtifactMapEnabled] = useState(false);
  const [artifactMapData, setArtifactMapData] = useState(null);
  const [artifactMapLoading, setArtifactMapLoading] = useState(false);
  const [artifactMapError, setArtifactMapError] = useState("");
  const [studioOverlay, setStudioOverlay] = useState(null);
  const apiBaseUrl = useMemo(getApiBaseUrl, []);
  const visiblePresets = useMemo(() => visiblePresetsForFlags(featureFlags), [featureFlags]);
  const uploadLimitMb = Number(currentUser?.limits?.max_file_size_mb || featureFlags.active_upload_limit_mb || featureFlags.beta_upload_limit_mb || 100);
  const hasUploadAccess = Boolean(accessCode.trim());
  const progress = jobStatus?.progress ?? 0;
  const activePreviewFile = previewMode === "after" && processedPreviewFile ? processedPreviewFile : file;
  const afterDownloadUrl = getProcessedPreviewUrl(jobStatus?.result);
  const changeMapUrl = getChangeMapUrl(jobStatus?.result);
  const artifactMapUrl = getArtifactMapUrl(jobStatus?.result);
  const orientationHasVisualChanges =
    Boolean(orientationTransform.translate_to_floor) ||
    ["rotation_x_deg", "rotation_y_deg", "rotation_z_deg", "rotation_x", "rotation_y", "rotation_z", "translate_x_mm", "translate_z_mm"].some((key) => Number(orientationTransform[key] || 0) !== 0);

  const navigatePublicView = (view) => {
    setPublicView(view);
    if (view !== "home" && view !== "app") return;
    const targetPath = view === "app" ? "/app" : "/";
    if (window.location.pathname !== targetPath) {
      window.history.pushState({ view }, "", targetPath);
    }
  };

  useEffect(() => {
    setActivePanel(`settings:${selectedMode}`);
  }, [selectedMode]);

  useEffect(() => {
    const onPopState = () => {
      setPublicView(window.location.pathname === "/app" ? "app" : "home");
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (accessCode.trim()) {
      localStorage.setItem(ACCESS_CODE_STORAGE_KEY, accessCode.trim());
    } else {
      localStorage.removeItem(ACCESS_CODE_STORAGE_KEY);
    }
  }, [accessCode]);

  useEffect(() => {
    const controller = new AbortController();
    const loadCurrentUser = async () => {
      setCurrentUserLoading(true);
      setCurrentUserError("");
      try {
        const payload = await fetchCurrentUser(apiBaseUrl, accessCode, controller.signal);
        setCurrentUser(payload);
      } catch (err) {
        if (err.name !== "AbortError") {
          setCurrentUser((current) => current || null);
          setCurrentUserError("Не удалось подтвердить статус доступа.");
        }
      } finally {
        if (!controller.signal.aborted) setCurrentUserLoading(false);
      }
    };
    loadCurrentUser();
    return () => controller.abort();
  }, [accessCode, apiBaseUrl]);

  useEffect(() => {
    const refreshOnVisible = () => {
      if (document.visibilityState !== "visible") return;
      fetchCurrentUser(apiBaseUrl, accessCode)
        .then((payload) => {
          setCurrentUser(payload);
          setCurrentUserError("");
        })
        .catch(() => setCurrentUserError("Не удалось подтвердить статус доступа."));
    };
    document.addEventListener("visibilitychange", refreshOnVisible);
    window.addEventListener("focus", refreshOnVisible);
    return () => {
      document.removeEventListener("visibilitychange", refreshOnVisible);
      window.removeEventListener("focus", refreshOnVisible);
    };
  }, [accessCode, apiBaseUrl]);

  useEffect(() => {
    let stopped = false;
    const applyFeatureFlags = (data) => {
      if (!stopped) setFeatureFlags({ ...DEFAULT_FEATURE_FLAGS, ...data });
    };
    const loadFeatureFlags = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/config/features`, { cache: "no-store" });
        if (!response.ok) throw new Error("features unavailable");
        applyFeatureFlags(await response.json());
        return;
      } catch {
        // Static fallback is useful for local static previews without backend.
      }
      try {
        const staticResponse = await fetch("/config/features.json", { cache: "no-store" });
        if (staticResponse.ok) {
          applyFeatureFlags(await staticResponse.json());
          return;
        }
      } catch {
        // Default feature flags below.
      }
      if (!stopped) setFeatureFlags(DEFAULT_FEATURE_FLAGS);
    };
    loadFeatureFlags();
    return () => {
      stopped = true;
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    const currentPreset = operationPresets.find((preset) => preset.id === selectedMode);
    if (currentPreset && (!featureEnabled(featureFlags, currentPreset.featureKey) || currentPreset.disabled)) {
      setSelectedMode("check");
    }
  }, [featureFlags, selectedMode]);

  useEffect(() => {
    if (jobStatus?.status === "completed" && jobStatus.result) {
      setActivePanel("current_model");
    }
  }, [jobStatus?.job_id, jobStatus?.status, jobStatus?.result?.final_model]);

  useEffect(() => {
    setOrientationTransform({
      rotation_x: 0,
      rotation_y: 0,
      rotation_z: 0,
      rotation_x_deg: 0,
      rotation_y_deg: 0,
      rotation_z_deg: 0,
      translate_to_floor: false,
      translate_x_mm: 0,
      translate_z_mm: 0,
    });
    setHeatmapEnabled(false);
    setHeatmapData(null);
    setHeatmapError("");
    setHeatmapLoading(false);
    setFocusChangesVersion(0);
    setArtifactMapEnabled(false);
    setArtifactMapData(null);
    setArtifactMapError("");
    setArtifactMapLoading(false);
    setLocalSelection(null);
    setStudioOverlay(null);
  }, [file?.name, file?.size]);

  useEffect(() => {
    if (!jobId || jobId === "demo") return undefined;

    let stopped = false;
    let timer = null;
    const loadStatus = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}`);
        if (!response.ok) throw new Error("Не удалось получить статус задачи");
        const data = await response.json();
        if (!stopped) {
          setJobStatus(data);
          if ((data.status === "completed" || data.status === "failed") && timer) {
            window.clearInterval(timer);
          }
        }
      } catch (err) {
        if (!stopped) setError(err.message);
      }
    };

    loadStatus();
    timer = window.setInterval(loadStatus, 1500);
    return () => {
      stopped = true;
      if (timer) window.clearInterval(timer);
    };
  }, [apiBaseUrl, jobId]);

  useEffect(() => {
    setHeatmapEnabled(false);
    setHeatmapData(null);
    setHeatmapLoading(false);
    setHeatmapError("");
    setFocusChangesVersion(0);
    setArtifactMapEnabled(false);
    setArtifactMapData(null);
    setArtifactMapLoading(false);
    setArtifactMapError("");
  }, [jobStatus?.job_id]);

  useEffect(() => {
    setProcessedPreviewFile(null);
    setProcessedPreviewError("");
    setProcessedPreviewLoading(false);

    if (jobStatus?.status !== "completed") return undefined;

    if (!afterDownloadUrl) {
      setProcessedPreviewError("Обработанная модель пока недоступна");
      return undefined;
    }

    let stopped = false;
    const loadProcessedPreview = async () => {
      setProcessedPreviewLoading(true);
      try {
        const response = await fetch(`${apiBaseUrl}${afterDownloadUrl}`);
        if (!response.ok) throw new Error("Не удалось загрузить обработанную модель");
        const blob = await response.blob();
        if (!stopped) {
          setProcessedPreviewFile(new File([blob], "stl-master-after.stl", { type: "model/stl" }));
          setProcessedPreviewError("");
        }
      } catch {
        if (!stopped) {
          setProcessedPreviewFile(null);
          setProcessedPreviewError("Не удалось загрузить обработанную модель");
        }
      } finally {
        if (!stopped) setProcessedPreviewLoading(false);
      }
    };

    loadProcessedPreview();
    return () => {
      stopped = true;
    };
  }, [apiBaseUrl, jobStatus?.job_id, jobStatus?.status, afterDownloadUrl]);

  const handleShowChanges = async (overrideChangeMapUrl = null) => {
    const mapUrl = overrideChangeMapUrl || changeMapUrl;
    if (!mapUrl || !processedPreviewFile) return;
    if (heatmapEnabled) {
      setHeatmapEnabled(false);
      setPreviewMode("after");
      return;
    }

    setHeatmapLoading(true);
    setHeatmapError("");
    try {
      const response = await fetch(`${apiBaseUrl}${mapUrl}`);
      if (!response.ok) throw new Error("Не удалось загрузить карту изменений.");
      const data = await response.json();
      setHeatmapData(data);
      setHeatmapEnabled(true);
      setArtifactMapEnabled(false);
      setArtifactMapData(null);
      setArtifactMapError("");
      setPreviewMode("after");
    } catch {
      setHeatmapData(null);
      setHeatmapEnabled(false);
      setHeatmapError("Не удалось загрузить карту изменений.");
    } finally {
      setHeatmapLoading(false);
    }
  };

  const handleFocusChanges = async () => {
    const mapUrl = changeMapUrl;
    if (!mapUrl || !processedPreviewFile) return;
    setHeatmapLoading(true);
    setHeatmapError("");
    try {
      let data = heatmapData;
      if (!data) {
        const response = await fetch(`${apiBaseUrl}${mapUrl}`);
        if (!response.ok) throw new Error("Не удалось загрузить карту изменений.");
        data = await response.json();
      }
      setHeatmapData(data);
      setHeatmapEnabled(true);
      setArtifactMapEnabled(false);
      setArtifactMapData(null);
      setArtifactMapError("");
      setPreviewMode("after");
      setFocusChangesVersion((value) => value + 1);
    } catch {
      setHeatmapData(null);
      setHeatmapEnabled(false);
      setHeatmapError("Не удалось загрузить карту изменений.");
    } finally {
      setHeatmapLoading(false);
    }
  };

  const handleOpenHistoryFile = async (downloadUrl, fileName) => {
    if (!downloadUrl) return;
    setProcessedPreviewLoading(true);
    setProcessedPreviewError("");
    setHeatmapEnabled(false);
    setHeatmapData(null);
    setHeatmapError("");
    setArtifactMapEnabled(false);
    setArtifactMapData(null);
    setArtifactMapError("");
    try {
      const response = await fetch(`${apiBaseUrl}${downloadUrl}`);
      if (!response.ok) throw new Error("Не удалось открыть файл этапа");
      const blob = await response.blob();
      setProcessedPreviewFile(new File([blob], fileName || "stl-master-stage.stl", { type: "model/stl" }));
      setPreviewMode("after");
    } catch {
      setProcessedPreviewError("Не удалось открыть файл этапа");
    } finally {
      setProcessedPreviewLoading(false);
    }
  };

  const handleShowArtifacts = async () => {
    if (!artifactMapUrl) return;
    if (artifactMapEnabled) {
      setArtifactMapEnabled(false);
      return;
    }

    setArtifactMapLoading(true);
    setArtifactMapError("");
    try {
      const response = await fetch(`${apiBaseUrl}${artifactMapUrl}`);
      if (!response.ok) throw new Error("Не удалось загрузить карту дефектов.");
      const data = await response.json();
      setArtifactMapData(data);
      setArtifactMapEnabled(true);
      setHeatmapEnabled(false);
      setHeatmapData(null);
      setHeatmapError("");
      setPreviewMode("before");
    } catch {
      setArtifactMapData(null);
      setArtifactMapEnabled(false);
      setArtifactMapError("Не удалось загрузить карту дефектов.");
    } finally {
      setArtifactMapLoading(false);
    }
  };

  const localSelectionRegions = Array.isArray(localSelection?.regions)
    ? localSelection.regions
    : localSelection?.center
      ? [{ center: localSelection.center, radius_mm: localSelection.radius_mm || localSelectionRadius }]
      : [];

  const localSelectionPayload = localSelectionRegions.length > 0
    ? {
        type: "spheres",
        regions: localSelectionRegions.slice(0, 30).map((region) => ({
          center: region.center,
          radius_mm: Number(region.radius_mm || localSelectionRadius),
        })),
        strength: localSmoothingStrength,
      }
    : null;

  const localSelectionPreviewStats = {
    selectedRegions: localSelectionRegions.length,
    selectedVertices: Number(localSelection?.estimated_vertices || 0),
    selectedFaces: Number(localSelection?.estimated_faces || 0),
    selectedPercent: Number(localSelection?.selected_percent || 0),
  };
  const localSelectionImpact = localSmoothingImpactLabel({
    selectedVertices: localSelectionPreviewStats.selectedVertices,
    selectedPercent: localSelectionPreviewStats.selectedPercent,
    strength: localSmoothingStrength,
  });
  const shouldWarnSmallRadius = selectedMode === "local" && localSelectionRadius === 2 && (file?.size || 0) > 5 * 1024 * 1024;

  const applyPremiumActivation = async (code, payload) => {
    const normalizedCode = String(code || "").trim();
    if (normalizedCode) setAccessCode(normalizedCode);
    if (payload?.current_user) {
      setCurrentUser(payload.current_user);
      setCurrentUserError("");
      return;
    }
    try {
      setCurrentUserLoading(true);
      const nextUser = await fetchCurrentUser(apiBaseUrl, normalizedCode || accessCode);
      setCurrentUser(nextUser);
      setCurrentUserError("");
    } catch {
      setCurrentUserError("Premium активирован, но статус не удалось обновить автоматически.");
    } finally {
      setCurrentUserLoading(false);
    }
  };

  const goHomeFromEditor = () => {
    const hasActiveWork = Boolean(file || jobId || orientationHasVisualChanges);
    if (hasActiveWork) {
      const confirmed = window.confirm("Перейти на главную? Текущая модель останется доступна в истории обработки.");
      if (!confirmed) return;
    }
    navigatePublicView("home");
  };

  const undoLocalSelection = () => {
    setLocalSelection((current) => {
      const regions = Array.isArray(current?.regions)
        ? current.regions
        : current?.center
          ? [{ center: current.center, radius_mm: current.radius_mm || localSelectionRadius }]
          : [];
      const nextRegions = regions.slice(0, -1);
      if (nextRegions.length === 0) return null;
      return {
        type: "spheres",
        regions: nextRegions,
        strength: localSmoothingStrength,
        estimated_vertices: current?.estimated_vertices,
      };
    });
  };

  const setOrientationAxis = (axis, value) => {
    const normalized = Number.isFinite(Number(value)) ? Number(value) : 0;
    setOrientationTransform((current) => ({
      ...current,
      [`rotation_${axis}`]: normalized,
      [`rotation_${axis}_deg`]: normalized,
    }));
  };

  const nudgeOrientationAxis = (axis, delta) => {
    const currentValue = Number(orientationTransform[`rotation_${axis}_deg`] ?? orientationTransform[`rotation_${axis}`] ?? 0);
    setOrientationAxis(axis, currentValue + delta);
  };

  const moveOnBed = (axis, delta) => {
    const key = axis === "x" ? "translate_x_mm" : "translate_z_mm";
    setOrientationTransform((current) => ({
      ...current,
      translate_to_floor: true,
      [key]: Number(current[key] || 0) + delta,
    }));
  };

  const centerOnBed = () => {
    setOrientationTransform((current) => ({
      ...current,
      translate_to_floor: true,
      translate_x_mm: 0,
      translate_z_mm: 0,
    }));
  };

  const resetOrientationTransform = () => {
    setOrientationTransform({
      rotation_x: 0,
      rotation_y: 0,
      rotation_z: 0,
      rotation_x_deg: 0,
      rotation_y_deg: 0,
      rotation_z_deg: 0,
      translate_to_floor: false,
      translate_x_mm: 0,
      translate_z_mm: 0,
    });
  };

  const resetStudioModel = () => {
    setDemoMode(false);
    setFile(null);
    setProcessedPreviewFile(null);
    setProcessedPreviewLoading(false);
    setProcessedPreviewError("");
    setJobId(null);
    setJobStatus(null);
    setUploading(false);
    setPreviewMode("before");
    setError("");
    setAccessGateMessage("");
    setHeatmapEnabled(false);
    setHeatmapData(null);
    setHeatmapLoading(false);
    setHeatmapError("");
    setArtifactMapEnabled(false);
    setArtifactMapData(null);
    setArtifactMapLoading(false);
    setArtifactMapError("");
    setFocusChangesVersion(0);
    setLocalSelection(null);
    setStudioOverlay(null);
    setModelName("");
    setSelectedMode("check");
    setActivePanel("settings:check");
    resetOrientationTransform();
  };

  const openDemo = () => {
    const original = createDemoStl({ cleaned: false });
    const cleaned = createDemoStl({ cleaned: true });
    resetStudioModel();
    setDemoMode(true);
    navigatePublicView("app");
    setFile(original);
    setProcessedPreviewFile(cleaned);
    setJobId("demo");
    setJobStatus(demoJobStatus());
    setSelectedMode("remove_artifacts");
    setPreviewMode("after");
    setError("");
    setAccessGateMessage("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const openUpload = () => {
    setDemoMode(false);
    navigatePublicView("app");
    setError("");
    setAccessGateMessage("");
    window.setTimeout(() => {
      document.querySelector(".studioWorkspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  };

  const showAccessGate = () => {
    setAccessGateMessage("Для обработки собственных моделей необходимо получить ранний доступ или оформить Premium.");
  };

  const applySelectedStudioFile = (nextFile) => {
    if (!nextFile) return;
    if (!String(nextFile.name || "").toLowerCase().endsWith(".stl")) {
      setError("Редактор принимает только STL-файлы.");
      return;
    }
    resetStudioModel();
    setDemoMode(false);
    setFile(nextFile);
    setProcessedPreviewFile(null);
    setProcessedPreviewLoading(false);
    setProcessedPreviewError("");
    setPreviewMode("before");
    setJobId(null);
    setJobStatus(null);
    setError("");
    setAccessGateMessage("");
  };

  const requestStudioFile = () => {
    if (!hasUploadAccess) {
      showAccessGate();
      return;
    }
    studioFileInputRef.current?.click();
  };

  const handleStudioFileChange = (event) => {
    if (!hasUploadAccess) {
      event.target.value = "";
      showAccessGate();
      return;
    }
    applySelectedStudioFile(event.target.files?.[0] || null);
    event.target.value = "";
  };

  const handleStudioDrop = (event) => {
    event.preventDefault();
    if (!hasUploadAccess) {
      showAccessGate();
      return;
    }
    applySelectedStudioFile(event.dataTransfer?.files?.[0] || null);
  };

  const handleStudioDragOver = (event) => {
    event.preventDefault();
  };

  const handleUpload = async () => {
    if (demoMode && !hasUploadAccess) {
      showAccessGate();
      return;
    }
    if (!hasUploadAccess) {
      showAccessGate();
      return;
    }
    if (!file) {
      setError("Добавьте STL-модель перед запуском.");
      return;
    }
    const uploadOperations = expandOperationsForUpload(operationsForMode(selectedMode));
    const localSmoothingSelected = uploadOperations.includes("local_smoothing");
    if (localSmoothingSelected && !localSelectionPayload) {
      setError("Сначала выберите участок модели.");
      return;
    }

    setUploading(true);
    setError("");
    setJobStatus(null);
    setProcessedPreviewFile(null);
    setProcessedPreviewLoading(false);
    setProcessedPreviewError("");
    setHeatmapEnabled(false);
    setHeatmapData(null);
    setHeatmapLoading(false);
    setHeatmapError("");
    setArtifactMapEnabled(false);
    setArtifactMapData(null);
    setArtifactMapLoading(false);
    setArtifactMapError("");
    setPreviewMode("before");

    const formData = new FormData();
    const applyOrientationSelected = uploadOperations.includes("apply_orientation");
    const autoOrientationSelected = uploadOperations.includes("auto_orientation");
    const fitToBedSelected = uploadOperations.includes("fit_to_bed_split");
    formData.append("file", file);
    formData.append("operations", JSON.stringify(uploadOperations));
    formData.append("reduction_percent", String(reductionPercent));
    formData.append("split_axis", splitAxis);
    formData.append("split_parts", String(splitParts));
    formData.append("split_mode", splitMode);
    formData.append("split_engine", "blender_boolean");
    formData.append("split_plane_offset_mm", String(splitPlaneOffset));
    formData.append("connector_size_mm", String(connectorSize));
    formData.append("connector_clearance_mm", String(connectorClearance));
    formData.append("connector_count", String(connectorCount));
    formData.append("connector_depth_mm", String(connectorDepth));
    formData.append("connector_wall_thickness_mm", String(connectorWallThickness));
    formData.append("magnet_size", magnetSize);
    const selectedMagnet = magnetSizeOptions.find((item) => item.id === magnetSize) || magnetSizeOptions[1];
    formData.append("magnet_diameter_mm", String(selectedMagnet.diameter));
    formData.append("magnet_thickness_mm", String(selectedMagnet.thickness));
    formData.append("lock_profile", lockProfile);
    formData.append("symmetry_axis", symmetryAxis);
    formData.append("symmetry_mode", symmetryMode);
    formData.append("artifact_cleanup_strength", artifactCleanupStrength);
    formData.append("model_improvement_strength", modelImprovementStrength);
    formData.append("model_name", modelName);
    formData.append("apply_orientation", String(applyOrientationSelected));
    formData.append("orientation_transform", JSON.stringify(orientationTransform));
    formData.append("auto_orientation", String(autoOrientationSelected));
    formData.append("orientation_priority", orientationPriority);
    formData.append("fit_to_bed", String(fitToBedSelected));
    formData.append("bed_size_x", String(bedSizeX));
    formData.append("bed_size_y", String(bedSizeY));
    formData.append("bed_size_z", String(bedSizeZ));
    formData.append("bed_connector_mode", bedConnectorMode);
    formData.append("bed_connector_clearance_mm", String(bedConnectorClearance));
    if (localSmoothingSelected && localSelectionPayload) {
      formData.append("local_selection", JSON.stringify(localSelectionPayload));
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/jobs/upload`, {
        method: "POST",
        headers: accessCode.trim() ? { "X-Beta-Access-Code": accessCode.trim() } : undefined,
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Ошибка загрузки");
      setJobId(data.job_id);
      setJobStatus({ ...data, job_id: data.job_id, status: data.status, progress: 0, message: "Задача поставлена в очередь" });
      addJobToHistory(data.job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const openHistoryJob = (historyJobId) => {
    setJobId(historyJobId);
    setJobStatus(null);
    setError("");
    setPreviewMode("before");
    setProcessedPreviewFile(null);
    setStudioOverlay(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const studioSelectedPreset = operationPresets.find((preset) => preset.id === selectedMode) || operationPresets[0];
  const studioSelectedOperations = studioSelectedPreset.disabled ? [] : expandOperationsForUpload(operationsForMode(selectedMode));
  const splitWorkflowActive = isSplitPreset(selectedMode);
  const selectedSplitModeOption = splitModeOptions.find((mode) => mode.id === splitMode);

  const selectStudioMode = (modeId) => {
    const nextPreset = operationPresets.find((preset) => preset.id === modeId);
    if (nextPreset?.disabled) return;
    setSelectedMode(modeId);
    const splitDefaults = splitPresetDefaults[modeId];
    if (splitDefaults) {
      setSplitMode(splitDefaults.splitMode);
      setLockProfile(splitDefaults.lockProfile);
    }
  };
  const studioGeneratedFiles = Array.isArray(jobStatus?.result?.generated_files) ? jobStatus.result.generated_files : [];
  const canRunStudioJob = Boolean(file && hasUploadAccess && !studioSelectedPreset.disabled);
  const jobIsRunning = uploading || ["queued", "processing", "running"].includes(jobStatus?.status);
  const jobIsAnalysis = jobStatus?.status === "completed" && selectedMode === "check";
  const jobIsCompleted = jobStatus?.status === "completed" && !jobIsAnalysis;
  const resultStlUrl = getProcessedPreviewUrl(jobStatus?.result);

  const renderOptionButtons = (items, value, onChange, formatter = (item) => item) => (
    <div className="studioSegmentGroup">
      {items.map((item) => {
        const itemValue = typeof item === "object" ? item.id : item;
        const label = formatter(item);
        return (
          <button className={value === itemValue ? "active" : ""} key={itemValue} type="button" onClick={() => onChange(itemValue, item)}>
            {label}
          </button>
        );
      })}
    </div>
  );

  const renderStudioSettings = () => {
    if (!studioSelectedPreset || selectedMode === "check") {
      return (
        <div className="studioSettingBlock">
          <h3>Проверка модели</h3>
          <p>STL Master проверит габариты, целостность сетки, тонкие места и готовность к печати.</p>
        </div>
      );
    }

    if (selectedMode === "improve") {
      return (
        <div className="studioSettingBlock">
          <h3>Улучшение модели</h3>
          <p>Сглаживает AI-шум, исправляет нормали и готовит STL к проверке.</p>
          <label className="studioTextField">
            <span>Название модели</span>
            <input value={modelName} maxLength={120} placeholder="Например: фигурка, корпус, деталь" onChange={(event) => setModelName(event.target.value)} />
          </label>
          {renderOptionButtons(improvementStrengthOptions, modelImprovementStrength, setModelImprovementStrength, (item) => item.title)}
        </div>
      );
    }

    if (selectedMode === "remove_artifacts") {
      return (
        <div className="studioSettingBlock">
          <h3>Очистка артефактов</h3>
          <p>Удаляет отдельные островки, шипы и мусорные фрагменты после генераторов.</p>
          {renderOptionButtons(artifactCleanupStrengthOptions, artifactCleanupStrength, setArtifactCleanupStrength, (item) => item.title)}
        </div>
      );
    }

    if (selectedMode === "surface") {
      return (
        <div className="studioSettingBlock">
          <h3>Восстановление поверхности</h3>
          <p>Экспериментальный режим ищет волны, бугры и мелкую рябь. Изменения применяются только при безопасном результате.</p>
        </div>
      );
    }

    if (selectedMode === "local") {
      return (
        <div className="studioSettingBlock">
          <h3>Выборочная правка</h3>
          <p>{localSelectionMode === "brush" ? "Проведите кистью по дефекту в 3D-окне." : "Кликните по проблемной области модели в 3D-окне."}</p>
          <span className="studioSettingLabel">Режим выделения</span>
          {renderOptionButtons([
            { id: "point", title: "Точка" },
            { id: "brush", title: "Кисть" },
          ], localSelectionMode, setLocalSelectionMode, (item) => item.title)}
          <span className="studioSettingLabel">Радиус</span>
          {renderOptionButtons([2, 5, 10, 20], localSelectionRadius, setLocalSelectionRadius, (item) => `${item} мм`)}
          <span className="studioSettingLabel">Сила</span>
          {renderOptionButtons([
            { id: "light", title: "Лёгкая" },
            { id: "balanced", title: "Средняя" },
            { id: "strong", title: "Сильная" },
          ], localSmoothingStrength, (value) => {
            setLocalSmoothingStrength(value);
            setLocalSelection((current) => current ? { ...current, strength: value } : current);
          }, (item) => item.title)}
          <div className={`studioSelectionSummary ${localSelection ? "ready" : ""}`}>
            <strong>{localSelection ? `Областей: ${localSelectionPreviewStats.selectedRegions}` : "Область не выбрана"}</strong>
            <span>Вершин: {formatMetric(localSelectionPreviewStats.selectedVertices)} · граней: {formatMetric(localSelectionPreviewStats.selectedFaces)}</span>
            <span>Ожидаемое воздействие: {localSelectionImpact}</span>
            {shouldWarnSmallRadius && <em>Для крупных моделей лучше выбрать радиус 10–20 мм.</em>}
          </div>
          <div className="studioInlineActions">
            <button type="button" onClick={undoLocalSelection} disabled={!localSelection}>Отменить последнее</button>
            <button type="button" onClick={() => setLocalSelection(null)}>Очистить</button>
          </div>
        </div>
      );
    }

    if (selectedMode === "reduce") {
      return (
        <div className="studioSettingBlock">
          <h3>Снижение полигонов</h3>
          <p>Уменьшает вес STL и сохраняет рабочую подготовку сетки.</p>
          {renderOptionButtons([25, 50, 75], reductionPercent, setReductionPercent, (item) => `${item}%`)}
        </div>
      );
    }

    if (splitWorkflowActive) {
      const connectorEnabled = splitMode !== "simple";
      const lockProfileVisible = splitMode === "lock" || splitMode === "slots";
      return (
        <div className="studioSettingBlock splitSetupPanel">
          <h3>Плоскость разреза</h3>
          <p>{studioSelectedPreset.title}: {studioSelectedPreset.description}</p>
          <div className="splitModeSummary" aria-live="polite">
            <strong>{selectedSplitModeOption?.title || "Разрез"}</strong>
            <span>{selectedSplitModeOption?.description || "Предварительный просмотр разреза активен."}</span>
          </div>
          <span className="studioSettingLabel">Ось разреза</span>
          {renderOptionButtons(["x", "y", "z"], splitAxis, setSplitAxis, (item) => item.toUpperCase())}
          <span className="studioSettingLabel">Количество частей</span>
          {renderOptionButtons([2, 3, 4], splitParts, setSplitParts)}
          <label className="studioRangeField">
            <span>Смещение плоскости: {Number(splitPlaneOffset || 0)} мм</span>
            <input type="range" min="-100" max="100" step="1" value={splitPlaneOffset} onChange={(event) => setSplitPlaneOffset(Number(event.target.value) || 0)} />
          </label>
          {connectorEnabled && (
            <>
              <span className="studioSettingLabel">Диаметр / размер</span>
              {renderOptionButtons(connectorSizeOptions, connectorSize, setConnectorSize, (item) => `${item} мм`)}
              <span className="studioSettingLabel">Глубина</span>
              {renderOptionButtons(connectorDepthOptions, connectorDepth, setConnectorDepth, (item) => `${item} мм`)}
              <span className="studioSettingLabel">Отступ / зазор</span>
              {renderOptionButtons(connectorClearanceOptions, connectorClearance, setConnectorClearance, (item) => `${item} мм`)}
              <span className="studioSettingLabel">Количество</span>
              {renderOptionButtons(connectorCountOptions, connectorCount, setConnectorCount)}
              <span className="studioSettingLabel">Расстановка</span>
              {renderOptionButtons(connectorPlacementOptions, connectorPlacement, setConnectorPlacement, (item) => item.title)}
              {lockProfileVisible && (
                <>
                  <span className="studioSettingLabel">Профиль</span>
                  {renderOptionButtons(lockProfileOptions, lockProfile, setLockProfile, (item) => item.title)}
                </>
              )}
              {splitMode === "pins" && (
                <div className="splitEngineeringNote">
                  <b>Штифты готовы к настройке</b>
                  <span>Диаметр, глубина, количество и отступ передаются в обработку. Ручная корректировка подготовлена как режим интерфейса.</span>
                </div>
              )}
            </>
          )}
          {splitMode === "simple" && (
            <div className="splitEngineeringNote">
              <b>Только разделение модели</b>
              <span>Соединители не создаются. Viewer показывает одну область разрезания до запуска обработки.</span>
            </div>
          )}
        </div>
      );
    }

    if (selectedMode === "fit_to_bed") {
      return (
        <div className="studioSettingBlock">
          <h3>Раскрой под стол</h3>
          <span className="studioSettingLabel">Размер рабочей области</span>
          {renderOptionButtons(bedSizeOptions, bedSizePreset, (value, item) => {
            setBedSizePreset(value);
            if (item?.id !== "custom") {
              setBedSizeX(item.x);
              setBedSizeY(item.y);
              setBedSizeZ(item.z);
            }
          }, (item) => item.title)}
          {bedSizePreset === "custom" && (
            <div className="studioSizeGrid">
              <label><span>X</span><input type="number" value={bedSizeX} onChange={(event) => setBedSizeX(Number(event.target.value) || 1)} /></label>
              <label><span>Y</span><input type="number" value={bedSizeY} onChange={(event) => setBedSizeY(Number(event.target.value) || 1)} /></label>
              <label><span>Z</span><input type="number" value={bedSizeZ} onChange={(event) => setBedSizeZ(Number(event.target.value) || 1)} /></label>
            </div>
          )}
          <span className="studioSettingLabel">Соединение частей</span>
          {renderOptionButtons(bedConnectorOptions, bedConnectorMode, setBedConnectorMode, (item) => item.title)}
        </div>
      );
    }

    if (selectedMode === "orientation") {
      return (
        <div className="studioSettingBlock">
          <h3>Ориентация модели</h3>
          <p>Будет сохранён текущий поворот модели и смещение по рабочему столу.</p>
          <div className="studioSizeGrid">
            {["x", "y", "z"].map((axis) => (
              <label key={axis}>
                <span>{axis.toUpperCase()}, °</span>
                <input type="number" value={Number(orientationTransform[`rotation_${axis}_deg`] ?? 0)} onChange={(event) => setOrientationAxis(axis, event.target.value)} />
              </label>
            ))}
          </div>
          <span className="studioSettingLabel">Положение на столе</span>
          <div className="studioInlineActions">
            <button type="button" onClick={() => setOrientationTransform((current) => ({ ...current, translate_to_floor: true }))}>Поставить на стол</button>
            <button type="button" onClick={centerOnBed}>По центру</button>
            <button type="button" onClick={resetOrientationTransform}>Сброс</button>
          </div>
          <span className="studioSettingLabel">Шаг перемещения</span>
          {renderOptionButtons([1, 5, 10], bedMoveStep, setBedMoveStep, (item) => `${item} мм`)}
          <div className="studioMovePad">
            <button type="button" onClick={() => moveOnBed("z", -bedMoveStep)}>↑</button>
            <button type="button" onClick={() => moveOnBed("x", -bedMoveStep)}>←</button>
            <button type="button" onClick={() => moveOnBed("x", bedMoveStep)}>→</button>
            <button type="button" onClick={() => moveOnBed("z", bedMoveStep)}>↓</button>
          </div>
        </div>
      );
    }

    if (selectedMode === "auto_orientation") {
      return (
        <div className="studioSettingBlock">
          <h3>Автоориентация</h3>
          <p>Сервис проверит несколько положений модели и выберет лучшее для печати.</p>
          {renderOptionButtons(orientationPriorityOptions, orientationPriority, setOrientationPriority, (item) => item.title)}
        </div>
      );
    }

    if (selectedMode === "symmetry") {
      return (
        <div className="studioSettingBlock">
          <h3>Симметрия</h3>
          <span className="studioSettingLabel">Ось</span>
          {renderOptionButtons(["x", "y", "z"], symmetryAxis, setSymmetryAxis, (item) => item.toUpperCase())}
          <span className="studioSettingLabel">Режим</span>
          {renderOptionButtons([
            { id: "analyze", title: "Анализ" },
            { id: "fix", title: "Исправить" },
          ], symmetryMode, setSymmetryMode, (item) => item.title)}
        </div>
      );
    }

    return null;
  };

  const renderAnalysisResultDetails = () => (
    jobStatus?.status === "completed" ? (
      <AnalysisResult
        activePanel={activePanel}
        apiBaseUrl={apiBaseUrl}
        result={jobStatus.result}
        jobStatus={jobStatus}
        sourceFile={file}
        processedPreviewFile={processedPreviewFile}
        setActivePanel={setActivePanel}
        compareMode={previewMode}
        hasProcessedPreview={Boolean(processedPreviewFile)}
        processedPreviewLoading={processedPreviewLoading}
        processedPreviewError={processedPreviewError}
        heatmapEnabled={heatmapEnabled}
        heatmapData={heatmapData}
        heatmapLoading={heatmapLoading}
        heatmapError={heatmapError}
        focusChangesVersion={focusChangesVersion}
        artifactMapEnabled={artifactMapEnabled}
        artifactMapData={artifactMapData}
        artifactMapLoading={artifactMapLoading}
        artifactMapError={artifactMapError}
        onCompareModeChange={(mode) => {
          setHeatmapEnabled(false);
          setArtifactMapEnabled(false);
          setPreviewMode(mode);
        }}
        onShowChanges={handleShowChanges}
        onFocusChanges={handleFocusChanges}
        onShowArtifacts={handleShowArtifacts}
        onOpenHistoryFile={handleOpenHistoryFile}
      />
    ) : null
  );

  const renderContextInspector = () => {
    if (!file) {
      return <ContextStartPanel uploadLimitMb={uploadLimitMb} onHistory={() => setStudioOverlay("history")} />;
    }

    if (jobIsRunning || jobStatus?.status === "failed") {
      return <ContextProcessingPanel jobStatus={jobStatus} progress={progress} statusMessage={statusMessage} />;
    }

    if (jobIsAnalysis) {
      return (
        <ContextAnalysisPanel
          result={jobStatus.result}
          onHistory={() => setStudioOverlay("history")}
          onDetails={() => setStudioOverlay("details")}
        />
      );
    }

    if (jobIsCompleted) {
      return (
        <ContextResultPanel
          apiBaseUrl={apiBaseUrl}
          result={jobStatus.result}
          canRun={canRunStudioJob}
          uploading={uploading}
          onCompare={() => {
            setHeatmapEnabled(false);
            setArtifactMapEnabled(false);
            setPreviewMode("after");
          }}
          onOpenResult={() => {
            if (!resultStlUrl) return;
            setHeatmapEnabled(false);
            setArtifactMapEnabled(false);
            setPreviewMode("after");
          }}
          onRepeat={handleUpload}
          onHistory={() => setStudioOverlay("history")}
          onDetails={() => setStudioOverlay("details")}
          onFeedback={() => setStudioOverlay("feedback")}
        />
      );
    }

    return (
      <ContextModelPanel
        file={file}
        result={jobStatus?.result}
        selectedPreset={studioSelectedPreset}
        settings={renderStudioSettings()}
        uploadLimitMb={uploadLimitMb}
        onHistory={() => setStudioOverlay("history")}
        onDetails={() => setStudioOverlay("details")}
      />
    );
  };

  const renderStudioOverlay = () => {
    if (!studioOverlay) return null;

    if (studioOverlay === "history") {
      return (
        <ContextOverlay title="История обработок" subtitle="Отдельный режим" onClose={() => setStudioOverlay(null)}>
          <JobHistory apiBaseUrl={apiBaseUrl} currentJobId={jobId} onOpenJob={openHistoryJob} />
        </ContextOverlay>
      );
    }

    if (studioOverlay === "feedback" && jobStatus?.status === "completed") {
      return (
        <ContextOverlay title="Отзыв о результате" subtitle="Поддержка" onClose={() => setStudioOverlay(null)}>
          <FeedbackPanel apiBaseUrl={apiBaseUrl} jobStatus={jobStatus} />
        </ContextOverlay>
      );
    }

    return (
      <ContextOverlay title="Подробности" subtitle="Техническая информация" onClose={() => setStudioOverlay(null)}>
        {jobStatus ? <JobInfoPanel jobStatus={jobStatus} result={jobStatus.result} /> : (
          <section className="studioInspectorCard">
            <p className="studioPanelLabel">Текущая модель</p>
            <h2>{file?.name || "STL-модель"}</h2>
            <p>Задача ещё не запускалась. Технические отчёты и manifest появятся после обработки.</p>
          </section>
        )}
        {renderAnalysisResultDetails()}
        {studioGeneratedFiles.length > 0 && <GeneratedFilesBlock files={studioGeneratedFiles} />}
      </ContextOverlay>
    );
  };

  if (publicView === "home") {
    return (
      <ConfigProvider appearance="dark">
        <PublicLanding
          onDemo={openDemo}
          onEarlyAccess={() => setPublicView("access")}
          onPremiumActivated={applyPremiumActivation}
          onPremium={() => setPublicView("premium")}
          onStartCut={openUpload}
          currentUser={currentUser}
          currentUserLoading={currentUserLoading}
          featureFlags={featureFlags}
        />
      </ConfigProvider>
    );
  }

  if (publicView === "access") {
    return (
      <ConfigProvider appearance="dark">
        <AccessRequestForm apiBaseUrl={apiBaseUrl} onBack={() => navigatePublicView("home")} />
      </ConfigProvider>
    );
  }

  if (publicView === "premium") {
    return (
      <ConfigProvider appearance="dark">
        <main className="publicLanding publicSite publicFormPage">
          <PremiumAccessModal
            onActivated={applyPremiumActivation}
            onClose={() => navigatePublicView("home")}
            onOpenApplication={() => navigatePublicView("app")}
          />
        </main>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider appearance="dark">
      <View activePanel="main">
        <Panel id="main">
          <main className="studioShell">
            <StudioHeader
              apiBaseUrl={apiBaseUrl}
              currentUser={currentUser}
              currentUserLoading={currentUserLoading}
              file={file}
              jobStatus={jobStatus}
              onGoHome={goHomeFromEditor}
              onOpenApplication={() => navigatePublicView("app")}
              onOpenPremium={() => setPublicView("premium")}
              Icon={LaunchIcon}
              PremiumStatusControl={PremiumStatusControl}
              statusLabel={statusLabel}
              supportUrl={STL_MASTER_SUPPORT_URL}
            />

            {currentUserError && <p className="studioWarning" role="status">{currentUserError}</p>}
            {accessGateMessage && (
              <section className="studioAccessBanner" role="status">
                <div>
                  <strong>Доступ к обработке закрыт</strong>
                  <span>{accessGateMessage}</span>
                </div>
                <button type="button" onClick={() => setPublicView("premium")}>Подключить Premium</button>
                <button type="button" onClick={() => setPublicView("access")}>Ранний доступ</button>
              </section>
            )}

            <section className="studioWorkspace">
              <StudioSidebar presets={visiblePresets} selectedMode={selectedMode} onSelect={selectStudioMode} hasFile={Boolean(file)} />

              <section className="studioViewerWorkspace" aria-label="3D viewport STL Master Studio" onDrop={handleStudioDrop} onDragOver={handleStudioDragOver}>
                {file ? (
                  <StlPreview
                    file={activePreviewFile}
                    sourceFile={file}
                    splitPreviewEnabled={splitWorkflowActive}
                    splitOperationTitle={studioSelectedPreset?.title}
                    splitAxis={splitAxis}
                    splitParts={splitParts}
                    splitMode={splitMode}
                    splitPlaneOffset={splitPlaneOffset}
                    symmetryPreviewEnabled={selectedMode === "symmetry"}
                    symmetryAxis={symmetryAxis}
                    compareMode={previewMode}
                    heatmapEnabled={heatmapEnabled}
                    heatmapData={heatmapData}
                    heatmapError={heatmapError}
                    artifactMapEnabled={artifactMapEnabled}
                    artifactMapData={artifactMapData}
                    artifactMapError={artifactMapError}
                    localSelectionEnabled={selectedMode === "local"}
                    localSelectionRadius={localSelectionRadius}
                    localSelectionStrength={localSmoothingStrength}
                    localSelectionMode={localSelectionMode}
                    localSelection={localSelection}
                    onLocalSelectionChange={setLocalSelection}
                    onClearModel={resetStudioModel}
                    onSelectFile={requestStudioFile}
                    orientationTransform={orientationTransform}
                    onOrientationChange={setOrientationTransform}
                    uploading={uploading}
                    progress={progress}
                    jobStatus={jobStatus}
                  />
                ) : (
                  <StudioEmptyState
                    hasUploadAccess={hasUploadAccess}
                    uploadLimitMb={uploadLimitMb}
                    onDragOver={handleStudioDragOver}
                    onDrop={handleStudioDrop}
                    onOpenDemo={openDemo}
                    onOpenRequirements={() => window.alert("Требования к файлу:\n\n- Формат: STL\n- Размер: до " + uploadLimitMb + " МБ\n- Результаты: STL, ZIP, JSON и TXT\n- Не загружайте конфиденциальные модели без Premium-доступа.")}
                    onRequestAccess={showAccessGate}
                    onSelectFile={requestStudioFile}
                    Icon={LaunchIcon}
                  />
                )}
              </section>

              <StudioWorkflowBar
                apiBaseUrl={apiBaseUrl}
                canRun={canRunStudioJob}
                error={error}
                jobId={jobId}
                jobStatus={jobStatus}
                progress={progress}
                result={jobStatus?.result}
                selectedOperations={studioSelectedOperations}
                selectedPreset={studioSelectedPreset}
                uploading={uploading}
                onRun={handleUpload}
                operationTitles={operationTitles}
                shortJobId={shortJobId}
                statusMessage={statusMessage}
                ProgressComponent={Progress}
              />

              <aside className={`studioInspector ${file ? "hasModel" : "isEmpty"} contextState-${!file ? "start" : jobIsRunning ? "processing" : jobIsAnalysis ? "analysis" : jobIsCompleted ? "result" : "model"}`} aria-label="Контекстная панель Studio">
                {renderContextInspector()}
              </aside>
            </section>

            {renderStudioOverlay()}

            <input ref={studioFileInputRef} className="studioFileInput" type="file" accept=".stl" aria-label="Выбрать STL-файл" onChange={handleStudioFileChange} />
          </main>
        </Panel>
      </View>
    </ConfigProvider>
  );
}
function formatFeedbackDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("ru-RU", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const ADMIN_SESSION_STORAGE_KEY = "stl-master-admin-session";

const adminSectionDescriptions = {
  overview: "Состояние сервисов, очереди, пользователей, заявок и хранилища.",
  applications: "Проверка обращений на ранний доступ и Премиум.",
  premiumCodes: "Выдача, активация, отзыв и контроль Премиум-кодов.",
  users: "Управление доступом, тарифами, блокировками и данными пользователей.",
  queue: "Контроль обработки моделей, очереди и ошибок заданий.",
  cleanup: "Анализ хранилища и безопасное удаление временных и истёкших файлов.",
  features: "Готовность и доступность возможностей приложения.",
  feedback: "Отзывы пользователей, оценки операций и сообщения о проблемах.",
  system: "Состояние административного доступа и история критических действий.",
};

const adminStatusLabels = {
  ok: "В норме",
  issued: "Выдан",
  activated: "Активирован",
  revoked: "Отозван",
  expired: "Истёк",
  pending: "Ожидает решения",
  new: "Новая",
  approved: "Одобрена",
  code_issued: "Код выдан",
  rejected: "Отклонена",
  queued: "В очереди",
  processing: "Обрабатывается",
  stale_processing: "Зависло",
  completed: "Завершено",
  failed: "Ошибка",
  cancelled: "Отменено",
  free: "Бесплатный",
  early_access: "Ранний доступ",
  premium: "Премиум",
  blocked: "Заблокирован",
  stable: "Стабильно",
  beta: "Бета",
  disabled: "Выключено",
};

const adminBulkActionTitles = {
  delete: "удалено",
  quarantine: "перемещено в карантин",
  release_lock: "освобождена блокировка",
  retry: "повторно поставлено",
  force_delete: "принудительно удалено",
  archive: "архивировано",
  reject: "отклонено",
  approve: "одобрено",
  block: "заблокировано",
  unblock: "разблокировано",
  grant_premium: "выдан Премиум",
  remove_premium: "Премиум снят",
  delete_with_jobs: "удалено вместе с заданиями",
  delete_with_premium: "удалено вместе с кодами",
  delete_with_feedback: "удалено вместе с отзывами",
  delete_with_all: "удалено полностью",
  stale_jobs: "зависшие задания",
  orphan_files: "неиспользуемые файлы",
  empty_dirs: "пустые папки",
  redis: "проверка Redis",
  cache: "кэш",
  temp: "временные файлы",
};

const adminOperationLabels = {
  analyze: "Анализ модели",
  print_check: "Проверка печати",
  repair_mesh: "Ремонт сетки",
  reduce_polygons: "Уменьшение полигонов",
  split_model: "Разрез модели",
  remove_ai_artifacts: "Очистка AI-артефактов",
  ai_cleanup: "Очистка AI-артефактов",
  apply_orientation: "Ориентация под печать",
  auto_orientation: "Автоориентация",
  fit_to_bed_split: "Подгонка под печатный стол",
  local_smoothing: "Выборочное сглаживание",
  surface_recovery: "Восстановление поверхности",
  prepare_package: "Подготовка пакета",
};

const adminNavIcons = {
  overview: "⌁",
  applications: "◫",
  premiumCodes: "♛",
  users: "◎",
  queue: "⇄",
  cleanup: "⌬",
  features: "✦",
  feedback: "◌",
  system: "◈",
};

function AdminFeedbackDashboard({ apiBaseUrl }) {
  const [adminSession, setAdminSession] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(ADMIN_SESSION_STORAGE_KEY) || "null") || null;
    } catch {
      return null;
    }
  });
  const [passwordInput, setPasswordInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockActive, setCapsLockActive] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [adminTab, setAdminTab] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem("stl-master-admin-sidebar") === "collapsed");
  const [globalSearch, setGlobalSearch] = useState("");
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [overviewState, setOverviewState] = useState(null);
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [userPage, setUserPage] = useState(1);
  const [userPerPage, setUserPerPage] = useState(25);
  const [userMenuOpen, setUserMenuOpen] = useState("");
  const [userDeletionPlan, setUserDeletionPlan] = useState(null);
  const [applications, setApplications] = useState({ early_access: [], premium: [] });
  const [applicationFilter, setApplicationFilter] = useState("active");
  const [selectedApplications, setSelectedApplications] = useState([]);
  const [premiumCodes, setPremiumCodes] = useState({ items: [], total: 0 });
  const [premiumSearch, setPremiumSearch] = useState("");
  const [premiumStatusFilter, setPremiumStatusFilter] = useState("active");
  const [featureState, setFeatureState] = useState({ items: [], total: 0 });
  const [cleanupState, setCleanupState] = useState(null);
  const [cleanupPlan, setCleanupPlan] = useState(null);
  const [cleanupSelection, setCleanupSelection] = useState([]);
  const [testDataState, setTestDataState] = useState(null);
  const [testDataBusy, setTestDataBusy] = useState(false);
  const [queueState, setQueueState] = useState(null);
  const [queueFilter, setQueueFilter] = useState("active");
  const [selectedJobs, setSelectedJobs] = useState([]);
  const [securityState, setSecurityState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState("real");
  const [filter, setFilter] = useState("all");
  const [operationFilter, setOperationFilter] = useState("all");
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedJobLoading, setSelectedJobLoading] = useState(false);
  const [selectedJobError, setSelectedJobError] = useState("");
  const [cleanupStatus, setCleanupStatus] = useState("");
  const [systemCleanupPreview, setSystemCleanupPreview] = useState(null);
  const [systemCleanupBusy, setSystemCleanupBusy] = useState(false);
  const [newUserContact, setNewUserContact] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [lastAccessCode, setLastAccessCode] = useState("");
  const [approvedApplicationMessage, setApprovedApplicationMessage] = useState("");
  const [approvedApplication, setApprovedApplication] = useState(null);
  const [applicationSearch, setApplicationSearch] = useState("");
  const [adminToast, setAdminToast] = useState("");

  const adminHeaders = adminSession?.session_token ? { Authorization: `Bearer ${adminSession.session_token}` } : {};

  const adminLogin = async () => {
    if (!passwordInput || loginLoading) return;
    setError("");
    setLoginLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: passwordInput }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 429) throw new Error("Слишком много попыток. Вход временно заблокирован примерно на 15 минут.");
        throw new Error(payload.detail || "Не удалось войти в панель управления");
      }
      sessionStorage.setItem(ADMIN_SESSION_STORAGE_KEY, JSON.stringify(payload));
      setAdminSession(payload);
      setPasswordInput("");
    } catch (err) {
      setError(err.message || "Не удалось войти в панель управления");
    } finally {
      setLoginLoading(false);
    }
  };

  const logoutAdmin = () => {
    sessionStorage.removeItem(ADMIN_SESSION_STORAGE_KEY);
    setAdminSession(null);
    setItems([]);
    setSummary(null);
    setUsers([]);
    setApplications({ early_access: [], premium: [] });
    setOverviewState(null);
    setPremiumCodes({ items: [], total: 0 });
    setFeatureState({ items: [], total: 0 });
    setCleanupState(null);
    setCleanupPlan(null);
    setCleanupSelection([]);
    setTestDataState(null);
    setSelectedUsers([]);
    setSelectedApplications([]);
    setSelectedJobs([]);
    setQueueState(null);
    setSecurityState(null);
  };

  const loadData = async ({ silent = false } = {}) => {
    if (!adminSession?.session_token) return;
    if (!silent) setLoading(true);
    setError("");
    try {
      const [overviewResponse, itemsResponse, summaryResponse, usersResponse, applicationsResponse, premiumCodesResponse, cleanupResponse, queueResponse, securityResponse, featuresResponse, testDataResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/api/v1/admin/overview`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/feedback`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/feedback/summary`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/users`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/applications`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/premium-codes`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/cleanup/status`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/queue`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/security`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/features`, { cache: "no-store", headers: adminHeaders }),
        fetch(`${apiBaseUrl}/api/v1/admin/test-data/scan`, { method: "POST", cache: "no-store", headers: { "Content-Type": "application/json", ...adminHeaders }, body: JSON.stringify({ include_items: false }) }),
      ]);
      if ([overviewResponse, itemsResponse, summaryResponse, usersResponse, applicationsResponse, premiumCodesResponse, cleanupResponse, queueResponse, securityResponse, featuresResponse, testDataResponse].some((response) => response.status === 401)) {
        logoutAdmin();
        throw new Error("Сессия администратора истекла. Войдите снова.");
      }
      if (!itemsResponse.ok || !summaryResponse.ok) throw new Error("Не удалось загрузить отзывы");
      const [overviewData, itemsData, summaryData, usersData, applicationsData, premiumCodesData, cleanupData, queueData, securityData, featuresData, testDataData] = await Promise.all([
        overviewResponse.ok ? overviewResponse.json() : null,
        itemsResponse.json(),
        summaryResponse.json(),
        usersResponse.ok ? usersResponse.json() : [],
        applicationsResponse.ok ? applicationsResponse.json() : { early_access: [], premium: [] },
        premiumCodesResponse.ok ? premiumCodesResponse.json() : { items: [], total: 0 },
        cleanupResponse.ok ? cleanupResponse.json() : null,
        queueResponse.ok ? queueResponse.json() : null,
        securityResponse.ok ? securityResponse.json() : null,
        featuresResponse.ok ? featuresResponse.json() : { items: [], total: 0 },
        testDataResponse.ok ? testDataResponse.json() : null,
      ]);
      setOverviewState(overviewData || null);
      setItems(Array.isArray(itemsData) ? itemsData : []);
      setSummary(summaryData || null);
      setUsers(Array.isArray(usersData) ? usersData : []);
      setApplications(applicationsData || { early_access: [], premium: [] });
      setPremiumCodes(premiumCodesData || { items: [], total: 0 });
      setCleanupState(cleanupData || null);
      setQueueState(queueData || null);
      setSecurityState(securityData || null);
      setFeatureState(featuresData || { items: [], total: 0 });
      setTestDataState(testDataData || null);
      setLastUpdatedAt(new Date());
    } catch {
      setError("Не удалось загрузить данные админки. Проверьте admin-пароль.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [apiBaseUrl, adminSession?.session_token]);

  const loadJobDetails = async (jobId) => {
    if (!jobId) return;
    setSelectedJob(null);
    setSelectedJobError("");
    setSelectedJobLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}`, { cache: "no-store" });
      if (!response.ok) throw new Error("not found");
      setSelectedJob(await response.json());
    } catch {
      setSelectedJobError("Данные job уже удалены или недоступны.");
    } finally {
      setSelectedJobLoading(false);
    }
  };

  const cleanupTestFeedback = async () => {
    setCleanupStatus("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/feedback/cleanup-test`, { method: "POST", headers: adminHeaders });
      if (!response.ok) throw new Error("cleanup failed");
      const payload = await response.json();
      setCleanupStatus(`Архивировано тестовых отзывов: ${payload.archived || 0}.`);
      await loadData({ silent: true });
    } catch {
      setCleanupStatus("Не удалось архивировать тестовые отзывы.");
    }
  };

  const deleteTestApplications = async (applicationIds = selectedApplications) => {
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/applications/delete-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify({ application_ids: applicationIds }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Не удалось удалить тестовые заявки.");
      setSelectedApplications([]);
      setAdminToast(`Тестовые заявки перенесены в архив: ${payload.archived || 0}.`);
      await loadData({ silent: true });
    } catch (err) {
      setError(err.message || "Не удалось удалить тестовые заявки.");
    }
  };

  const deleteTestJobs = async (jobIds = selectedJobs) => {
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/jobs/delete-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify({ job_ids: jobIds }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось удалить тестовые задания.");
      setSelectedJobs([]);
      setAdminToast(`Тестовые задания удалены: ${payload.deleted || 0}, защищено активных: ${payload.protected || 0}.`);
      await loadData({ silent: true });
    } catch (err) {
      setError(err.message || "Не удалось удалить тестовые задания.");
    }
  };

  const bulkReportToast = (entity, action, payload) => {
    const report = payload?.report || {};
    const success = Array.isArray(report.success) ? report.success.length : 0;
    const skipped = Array.isArray(report.skipped) ? report.skipped.length : 0;
    const protectedCount = Array.isArray(report.protected) ? report.protected.length : 0;
    const errors = Array.isArray(report.errors) ? report.errors.length : 0;
    const actionTitle = adminBulkActionTitles[action] || "обработано";
    return `${entity}: ${actionTitle} ${success}, пропущено ${skipped}, защищено ${protectedCount}, ошибок ${errors}.`;
  };

  const runIntegrityCheck = async (autoFix = true) => {
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/integrity-check`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ auto_fix: autoFix }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Не удалось выполнить проверку целостности.");
    setAdminToast(`Проверка целостности завершена: найдено ${Object.values(payload.summary || {}).reduce((sum, value) => sum + Number(value || 0), 0)} проблем.`);
    return payload;
  };

  const bulkApplications = async (action, applicationIds = selectedApplications) => {
    if (!applicationIds.length) return;
    setError("");
    const body = { action, ids: applicationIds };
    if (action === "reject") {
      body.reason = window.prompt("Причина отклонения выбранных заявок, необязательно:", "") || "Массовое отклонение";
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/applications/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось выполнить действие по заявкам.");
      const issuedCodes = (payload.report?.success || []).filter((item) => item.access_code);
      if (issuedCodes.length) {
        setApprovedApplicationMessage(issuedCodes.map((item) => `${item.request_number || item.id}: ${item.access_code}`).join("\n"));
      }
      setSelectedApplications([]);
      setAdminToast(bulkReportToast("Заявки", action, payload));
      await loadData({ silent: true });
    } catch (err) {
      setError(err.message || "Не удалось выполнить действие по заявкам.");
    }
  };

  const bulkJobs = async (action, jobIds = selectedJobs) => {
    if (!jobIds.length) return;
    setError("");
    const body = { action, ids: jobIds };
    if (action === "force_delete") {
      const confirmation = window.prompt("Принудительное удаление уберёт задание, результаты, загрузки, отзывы, кэш, Redis и lock. Введите: ПРИНУДИТЕЛЬНО УДАЛИТЬ", "");
      if (confirmation !== "ПРИНУДИТЕЛЬНО УДАЛИТЬ") {
        setAdminToast("Принудительное удаление отменено.");
        return;
      }
      body.confirmation = confirmation;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/jobs/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось выполнить действие по заданиям.");
      setSelectedJobs([]);
      setAdminToast(bulkReportToast("Задания", action, payload));
      await loadData({ silent: true });
    } catch (err) {
      setError(err.message || "Не удалось выполнить действие по заданиям.");
    }
  };

  const bulkUsers = async (action, userIds = selectedUsers) => {
    if (!userIds.length) return;
    setError("");
    const body = { action, ids: userIds };
    if (action.includes("delete")) {
      const selected = users.filter((user) => userIds.includes(user.id));
      const summary = selected.reduce((acc, user) => {
        acc.jobs += Number(user.jobs_count || 0);
        acc.premium += user.access_level === "premium" || user.has_access_code ? 1 : 0;
        return acc;
      }, { jobs: 0, premium: 0 });
      const confirmation = window.prompt(`Будет удалено пользователей: ${userIds.length}. Связанные задания: ${summary.jobs}. Премиум-коды: ${summary.premium}. Для подтверждения введите: УДАЛИТЬ ПОЛЬЗОВАТЕЛЕЙ`, "");
      if (confirmation !== "УДАЛИТЬ ПОЛЬЗОВАТЕЛЕЙ") {
        setAdminToast("Удаление пользователей отменено.");
        return;
      }
      body.confirmation = confirmation;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/users/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось выполнить действие по пользователям.");
      if (Array.isArray(payload.users)) setUsers(payload.users);
      const issuedCode = (payload.report?.success || []).find((item) => item.access_code)?.access_code;
      if (issuedCode) setLastAccessCode(issuedCode);
      setSelectedUsers([]);
      setAdminToast(bulkReportToast("Пользователи", action, payload));
      await loadData({ silent: true });
    } catch (err) {
      setError(err.message || "Не удалось выполнить действие по пользователям.");
    }
  };

  const createUser = async () => {
    if (!newUserContact.trim()) return;
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ contact: newUserContact, name: newUserName }),
    });
    if (!response.ok) {
      setError("Не удалось создать пользователя.");
      return;
    }
    const user = await response.json();
    setLastAccessCode(user.access_code || "");
    setNewUserContact("");
    setNewUserName("");
    await loadData({ silent: true });
  };

  const approveApplication = async (kind, applicationId, premiumDays = 30) => {
    setError("");
    setApprovedApplicationMessage("");
    setApprovedApplication(null);
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/applications/${kind}/${applicationId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ premium_days: premiumDays }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setError(payload.detail || "Не удалось одобрить заявку.");
      return;
    }
    setLastAccessCode(payload.access_code || "");
    setApprovedApplicationMessage(payload.message || "");
    setApprovedApplication({
      requestNumber: payload.request_number || payload.application?.request_number || "",
      accessCode: payload.access_code || "",
      applicationId,
      kind,
    });
    await loadData({ silent: true });
  };

  const rejectApplication = async (kind, applicationId) => {
    setError("");
    const reason = window.prompt("Причина отклонения заявки, необязательно:", "") || "";
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/applications/${kind}/${applicationId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ reason }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setError(payload.detail || "Не удалось отклонить заявку.");
      return;
    }
    await loadData({ silent: true });
  };

  const userAction = async (userId, action, body = null) => {
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/users/${userId}/${action}`, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json", ...adminHeaders } : adminHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      setError("Не удалось обновить пользователя.");
      return;
    }
    const payload = await response.json();
    if (payload.access_code) setLastAccessCode(payload.access_code);
    await loadData({ silent: true });
  };

  const scanCleanup = async () => {
    setCleanupStatus("Сканируем хранилище...");
    setCleanupPlan(null);
    setCleanupSelection([]);
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/cleanup/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ older_than_hours: 6 }),
    });
    if (!response.ok) {
      setCleanupStatus("");
      setError("Не удалось просканировать хранилище.");
      return;
    }
    const plan = await response.json();
    setCleanupPlan(plan);
    setCleanupSelection((plan.items || []).filter((item) => item.safe_to_delete).map((item) => item.id));
    setCleanupStatus(`Найдено файлов/директорий: ${(plan.items || []).length}, потенциально освободится ${formatBytes(plan.total_size_bytes)}.`);
    await loadData({ silent: true });
  };

  const executeCleanup = async () => {
    if (!cleanupPlan?.scan_id) return;
    const token = window.prompt(`Для удаления выбранных объектов введите: ${cleanupPlan.confirmation_token}`, "");
    if (token !== cleanupPlan.confirmation_token) {
      setCleanupStatus("Удаление отменено: токен подтверждения не совпал.");
      return;
    }
    setCleanupStatus("Удаляем выбранные объекты...");
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/cleanup/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ scan_id: cleanupPlan.scan_id, item_ids: cleanupSelection, confirmation_token: token }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setCleanupStatus("");
      setError(payload.detail || "Не удалось выполнить безопасную очистку.");
      return;
    }
    setCleanupState({ ...(cleanupState || {}), last_run: payload });
    setCleanupStatus(`Удалено: ${payload.deleted || 0}, карантин: ${payload.quarantined || 0}, защищено: ${payload.protected || 0}, ошибок: ${payload.errors || 0}, освобождено ${formatBytes(payload.freed_bytes)}.`);
    setCleanupPlan(null);
    setCleanupSelection([]);
    await loadData({ silent: true });
  };

  const scanTestData = async (includeItems = true) => {
    setTestDataBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/test-data/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify({ include_items: includeItems }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Не удалось просканировать тестовые данные.");
      setTestDataState(payload);
      setAdminToast("Сканирование тестовых данных завершено.");
    } catch (err) {
      setError(err.message || "Не удалось просканировать тестовые данные.");
    } finally {
      setTestDataBusy(false);
    }
  };

  const cleanupTestData = async () => {
    const confirmation = window.prompt("Для удаления подтверждённых тестовых данных введите: УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ", "");
    if (confirmation !== "УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ") {
      setAdminToast("Очистка тестовых данных отменена.");
      return;
    }
    setTestDataBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/test-data/cleanup`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify({ confirmation }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось очистить тестовые данные.");
      setAdminToast(`Тестовые данные очищены: пользователей ${payload.counts?.users || 0}, заявок ${payload.counts?.applications || 0}, заданий ${payload.counts?.jobs || 0}, отзывов ${payload.counts?.feedback || 0}.`);
      await loadData({ silent: true });
    } catch (err) {
      setError(err.message || "Не удалось очистить тестовые данные.");
    } finally {
      setTestDataBusy(false);
    }
  };

  const systemCleanup = async (actions) => {
    setCleanupStatus("Готовим предварительный расчёт очистки...");
    setError("");
    setSystemCleanupBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/system-cleanup/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify({ actions }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось подготовить предварительный расчёт очистки.");
      setSystemCleanupPreview({ actions, payload });
      setCleanupStatus(`Предварительный расчёт готов. Потенциально освободится ${formatBytes(payload.freed_bytes || 0)}.`);
    } catch (err) {
      setCleanupStatus("");
      setError(err.message || "Не удалось подготовить предварительный расчёт очистки.");
    } finally {
      setSystemCleanupBusy(false);
    }
  };

  const executeSystemCleanup = async () => {
    if (!systemCleanupPreview?.actions?.length) return;
    const actions = systemCleanupPreview.actions;
    const confirmation = actions.includes("quarantine") ? "ОЧИСТИТЬ КАРАНТИН" : undefined;
    setCleanupStatus("Выполняем подтверждённую очистку системы...");
    setError("");
    setSystemCleanupBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/system-cleanup`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminHeaders },
        body: JSON.stringify({ actions, confirmation }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Не удалось выполнить очистку системы.");
      setCleanupStatus(`Очистка системы завершена. Освобождено ${formatBytes(payload.freed_bytes || 0)}.`);
      setAdminToast(`Очистка системы: ${Object.keys(payload.actions || {}).length} действий выполнено.`);
      setSystemCleanupPreview(null);
      await loadData({ silent: true });
    } catch (err) {
      setCleanupStatus("");
      setError(err.message || "Не удалось выполнить очистку системы.");
    } finally {
      setSystemCleanupBusy(false);
    }
  };

  const previewUserDeletion = async (mode = "archive", userIds = selectedUsers) => {
    if (!userIds.length) return;
    setError("");
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/users/deletion-preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({
        user_ids: userIds,
        mode,
        options: { delete_uploads: true, delete_results: true, delete_feedback: true, revoke_codes: true },
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setError(payload.detail || "Не удалось построить план удаления пользователя.");
      return;
    }
    setUserDeletionPlan(payload);
    setAdminToast("План удаления построен. Проверьте связанные данные и подтвердите действие.");
  };

  const executeUserDeletion = async () => {
    if (!userDeletionPlan?.plan_id) return;
    const confirmation = window.prompt(`Введите подтверждение: ${userDeletionPlan.confirmation_token}`, "");
    if (confirmation !== userDeletionPlan.confirmation_token) {
      setAdminToast("Удаление пользователя отменено.");
      return;
    }
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/users/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...adminHeaders },
      body: JSON.stringify({ plan_id: userDeletionPlan.plan_id, confirmation }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setError(typeof payload.detail === "string" ? payload.detail : "Удаление заблокировано: есть активные задания или защищённые записи.");
      return;
    }
    setUsers(Array.isArray(payload.users) ? payload.users : users);
    setSelectedUsers([]);
    setUserDeletionPlan(null);
    setAdminToast(`Готово: архивировано ${payload.archived || 0}, удалено ${payload.removed || 0}.`);
    await loadData({ silent: true });
  };

  const cancelAdminJob = async (jobId) => {
    if (!jobId) return;
    const response = await fetch(`${apiBaseUrl}/api/v1/admin/jobs/${jobId}/cancel`, {
      method: "POST",
      headers: adminHeaders,
    });
    if (!response.ok) {
      setError("Не удалось отменить задачу.");
      return;
    }
    await loadData({ silent: true });
  };

  if (!adminSession?.session_token) {
    return (
      <main className="adminLoginScreen">
        <section className="adminLoginInfo">
          <div className="adminBrand loginBrand">
            <span className="brandIcon"><LaunchIcon type="box" /></span>
            <div><strong>STL Master</strong><small>Панель управления</small></div>
          </div>
          <h1>Администрирование сервиса обработки STL</h1>
          <p>Контроль заявок, Премиум-доступа, очереди обработки, обратной связи и безопасной очистки тестовых данных.</p>
          <div className="adminLoginGrid" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <a className="adminBackLink" href="/">Вернуться на сайт</a>
        </section>
        <section className="adminLoginPanel" aria-labelledby="admin-login-title">
          <p className="panelLabel">Защищённый раздел</p>
          <h2 id="admin-login-title">Вход в панель управления</h2>
          <p>Сессия завершается после закрытия браузера или истечения срока доступа.</p>
          <label>
            <span>Пароль администратора</span>
            <div className="adminPasswordField">
              <input
                autoFocus
                autoComplete="current-password"
                type={showPassword ? "text" : "password"}
                value={passwordInput}
                onChange={(event) => setPasswordInput(event.target.value)}
                onKeyDown={(event) => {
                  setCapsLockActive(Boolean(event.getModifierState?.("CapsLock")));
                  if (event.key === "Enter") adminLogin();
                }}
                onKeyUp={(event) => setCapsLockActive(Boolean(event.getModifierState?.("CapsLock")))}
                placeholder="Введите пароль"
              />
              <button type="button" onClick={() => setShowPassword((value) => !value)}>{showPassword ? "Скрыть" : "Показать"}</button>
            </div>
          </label>
          {capsLockActive && <p className="adminNotice compact">Включён Caps Lock.</p>}
          {error && <p className="error" aria-live="polite">{error}</p>}
          <button className="adminLoginButton" type="button" onClick={adminLogin} disabled={loginLoading || !passwordInput.trim()}>
            {loginLoading ? "Проверяем..." : "Войти"}
          </button>
          <small>После нескольких неверных попыток вход временно блокируется.</small>
        </section>
      </main>
    );
  }

  const operations = Array.from(new Set(items.flatMap((item) => Array.isArray(item.operations) ? item.operations : []))).sort();
  const filteredItems = items.filter((item) => {
    const rating = Number(item.rating || 0);
    if (visibilityFilter === "real" && item.is_test) return false;
    if (visibilityFilter === "test" && !item.is_test) return false;
    if (filter === "problem" && rating > 2) return false;
    if (filter === "good" && rating < 4) return false;
    if (operationFilter !== "all" && !(item.operations || []).includes(operationFilter)) return false;
    return true;
  });
  const allOperationStats = summary?.by_operation || {};
  const realOperationStats = summary?.real_by_operation || {};
  const operationRows = Array.from(new Set([...Object.keys(allOperationStats), ...Object.keys(realOperationStats)])).map((operation) => ({
    operation,
    count: allOperationStats[operation]?.count || 0,
    average: realOperationStats[operation]?.average_rating || allOperationStats[operation]?.average_rating || 0,
    problems: realOperationStats[operation]?.problems_count || allOperationStats[operation]?.problems_count || 0,
    test: allOperationStats[operation]?.test_feedback || 0,
    real: realOperationStats[operation]?.count || allOperationStats[operation]?.real_feedback || 0,
  })).sort((a, b) => b.real - a.real || b.count - a.count || a.operation.localeCompare(b.operation));
  const jobResult = selectedJob?.result || {};
  const jobGeneratedFiles = Array.isArray(jobResult.generated_files) ? jobResult.generated_files : [];
  const jobProcessingHistory = Array.isArray(jobResult.processing_history) ? jobResult.processing_history : [];
  const allApplications = [...(applications.early_access || []), ...(applications.premium || [])];
  const pendingApplicationsCount = allApplications.filter((application) => ["pending", "new"].includes(String(application.status || "pending"))).length;
  const problemJobsCount = Number(queueState?.failed_24h || 0) + Number(queueState?.stale_processing_jobs || 0);
  const testDataSummary = testDataState?.summary || {};
  const searchableEntities = [
    ...users.map((user) => ({ type: "Пользователь", id: user.id, title: user.name || user.contact || user.id, subtitle: user.contact || user.plan || "", target: "users" })),
    ...allApplications.map((application) => ({ type: "Заявка", id: application.id, title: application.request_number || application.id, subtitle: application.email || application.contact || application.status || "", target: "applications" })),
    ...(premiumCodes.items || []).map((code) => ({ type: "Премиум-код", id: code.id || code.user_id, title: code.masked_code || code.request_number || code.user_id, subtitle: code.request_number || code.status || "", target: "premiumCodes" })),
    ...(queueState?.jobs || []).map((job) => ({ type: "Задание", id: job.job_id, title: job.job_id, subtitle: (job.operation_labels || job.operations || []).join(", "), target: "queue" })),
    ...items.map((item) => ({ type: "Отзыв", id: item.feedback_id || item.job_id, title: item.contact || item.job_id || "Отзыв", subtitle: item.comment || "", target: "feedback" })),
  ];
  const globalSearchResults = globalSearch.trim()
    ? searchableEntities.filter((entry) => [entry.title, entry.subtitle, entry.id, entry.type].join(" ").toLowerCase().includes(globalSearch.trim().toLowerCase())).slice(0, 8)
    : [];
  const filteredUsers = users.filter((user) => {
    const query = userSearch.trim().toLowerCase();
    if (!query) return true;
    return [user.name, user.contact, user.id, user.plan, user.access_level].filter(Boolean).join(" ").toLowerCase().includes(query);
  });
  const userPageCount = Math.max(1, Math.ceil(filteredUsers.length / userPerPage));
  const visibleUsers = filteredUsers.slice((userPage - 1) * userPerPage, userPage * userPerPage);
  const filteredApplications = allApplications
    .filter((application) => {
      const classification = application.classification || "";
      if (applicationFilter === "active" && classification === "test") return false;
      if (applicationFilter === "test" && classification !== "test") return false;
      if (applicationFilter === "premium" && application.type !== "premium") return false;
      if (applicationFilter === "early_access" && application.type !== "early_access") return false;
      if (applicationFilter === "pending" && !["pending", "new"].includes(String(application.status || ""))) return false;
      if (applicationFilter === "approved" && !["approved", "code_issued", "activated"].includes(String(application.status || ""))) return false;
      if (applicationFilter === "rejected" && String(application.status || "") !== "rejected") return false;
      const query = applicationSearch.trim().toLowerCase();
      if (!query) return true;
      return [application.request_number, application.id, application.client_id, application.contact, application.email, application.telegram].filter(Boolean).join(" ").toLowerCase().includes(query);
    })
    .sort((a, b) => {
      const aPending = ["pending", "new"].includes(String(a.status || ""));
      const bPending = ["pending", "new"].includes(String(b.status || ""));
      if (aPending !== bPending) return aPending ? -1 : 1;
      return String(b.created_at || "").localeCompare(String(a.created_at || ""));
    });
  const filteredPremiumCodes = (premiumCodes.items || []).filter((code) => {
    if (premiumStatusFilter === "active" && ["revoked", "expired"].includes(String(code.status || ""))) return false;
    if (premiumStatusFilter !== "active" && premiumStatusFilter !== "all" && String(code.status || "") !== premiumStatusFilter) return false;
    const query = premiumSearch.trim().toLowerCase();
    if (!query) return true;
    return [code.masked_code, code.request_number, code.user_id, code.status].filter(Boolean).join(" ").toLowerCase().includes(query);
  });
  const filteredQueueJobs = (queueState?.jobs || []).filter((job) => {
    if (queueFilter === "active") return ["queued", "processing", "stale_processing"].includes(job.status);
    if (queueFilter === "test") return job.classification === "test";
    if (queueFilter === "errors") return ["failed", "stale_processing"].includes(job.status);
    if (queueFilter === "all") return true;
    return job.status === queueFilter;
  });
  const adminNavItems = [
    ["overview", "Обзор"],
    ["applications", "Заявки"],
    ["premiumCodes", "Премиум и коды"],
    ["users", "Пользователи"],
    ["queue", "Задания и очередь"],
    ["cleanup", "Файлы и очистка"],
    ["features", "Функции"],
    ["feedback", "Обратная связь"],
    ["system", "Безопасность и журнал"],
  ];

  return (
    <main className={`adminDashboard adminApp ${sidebarCollapsed ? "sidebarCollapsed" : ""}`}>
      <aside className="adminSidebar">
        <div className="adminBrand">
          <span className="brandIcon"><LaunchIcon type="box" /></span>
          <div><strong>STL Master</strong><small>Панель управления</small></div>
        </div>
        <button className="adminSidebarToggle" type="button" onClick={() => {
          setSidebarCollapsed((value) => {
            localStorage.setItem("stl-master-admin-sidebar", value ? "expanded" : "collapsed");
            return !value;
          });
        }}>{sidebarCollapsed ? "Развернуть" : "Свернуть"}</button>
        <nav className="adminTabs" aria-label="Разделы админки">
          {adminNavItems.map(([id, title]) => (
            <button key={id} type="button" className={adminTab === id ? "active" : ""} aria-label={title} title={title} onClick={() => setAdminTab(id)}>
              <span className="adminNavIcon">{adminNavIcons[id]}</span>
              <span className="adminNavTitle">{title}</span>
              {id === "applications" && pendingApplicationsCount > 0 && <span className="adminNavBadge">{pendingApplicationsCount}</span>}
              {id === "queue" && problemJobsCount > 0 && <span className="adminNavBadge danger">{problemJobsCount}</span>}
              {id === "cleanup" && Number(testDataSummary?.test_size_mb || 0) > 0 && <span className="adminNavBadge">{testDataSummary.test_size_mb} МБ</span>}
            </button>
          ))}
        </nav>
        <small className="adminVersion">STL Master v2.0</small>
        <button className="adminLogout" type="button" onClick={logoutAdmin}>Выйти из админки</button>
      </aside>

      <section className="adminWorkspace">
        <header className="adminTopbar">
          <div>
            <p className="panelLabel">Администрирование</p>
            <h1>{adminNavItems.find(([id]) => id === adminTab)?.[1] || "STL Master"}</h1>
            <p>{adminSectionDescriptions[adminTab] || "Панель управления STL Master."}</p>
          </div>
          <div className="adminGlobalSearch">
            <input value={globalSearch} onChange={(event) => setGlobalSearch(event.target.value)} placeholder="Поиск: пользователь, заявка, ID задания..." />
            {globalSearchResults.length > 0 && (
              <div className="adminSearchResults">
                {globalSearchResults.map((entry) => (
                  <button key={`${entry.type}-${entry.id}`} type="button" onClick={() => { setAdminTab(entry.target); setGlobalSearch(""); }}>
                    <span>{entry.type}</span>
                    <strong>{entry.title}</strong>
                    <small>{entry.subtitle || entry.id}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="adminSystemPills">
            <span className={overviewState?.redis?.status === "ok" ? "ok" : "danger"}>Redis: {adminStatusLabels[overviewState?.redis?.status] || "—"}</span>
            <span>Очередь: {queueState?.queue_size ?? overviewState?.queue?.queue_size ?? 0}</span>
            <span>Ожидают: {pendingApplicationsCount}</span>
            <span>Сессия до: {formatFeedbackDate(adminSession?.expires_at)}</span>
            <button type="button" onClick={() => loadData({ silent: true })}>Обновить</button>
            <small>{lastUpdatedAt ? `Обновлено: ${lastUpdatedAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}` : "Ещё не обновлялось"}</small>
          </div>
        </header>

      {error && <p className="error">{error}</p>}
      {adminToast && <p className="adminNotice">{adminToast}</p>}

      {adminTab === "overview" && (
        <section className="adminSectionStack">
          <div className="adminSummaryGrid">
            <article className="adminSummaryCard"><span>Сервер</span><strong>{adminStatusLabels[overviewState?.backend?.status] || overviewState?.backend?.status || "—"}</strong></article>
            <article className="adminSummaryCard"><span>Redis, состояние</span><strong>{adminStatusLabels[overviewState?.redis?.status] || overviewState?.redis?.status || "—"}</strong></article>
            <article className="adminSummaryCard"><span>В очереди / обрабатывается</span><strong>{`${overviewState?.queue?.queued_jobs ?? 0} / ${overviewState?.queue?.processing_jobs ?? 0}`}</strong></article>
            <article className="adminSummaryCard"><span>Ошибки 24ч</span><strong>{overviewState?.queue?.failed_24h ?? 0}</strong></article>
            <article className="adminSummaryCard"><span>Пользователи</span><strong>{overviewState?.users?.total ?? users.length}</strong></article>
            <article className="adminSummaryCard"><span>Премиум</span><strong>{overviewState?.users?.premium ?? users.filter((user) => user.access_level === "premium").length}</strong></article>
            <article className="adminSummaryCard"><span>Заявки ожидают решения</span><strong>{overviewState?.applications?.pending ?? pendingApplicationsCount}</strong></article>
            <article className="adminSummaryCard"><span>Свободно на диске</span><strong>{formatBytes(overviewState?.storage?.disk?.free)}</strong></article>
            <article className="adminSummaryCard"><span>Тестовые данные</span><strong>{testDataSummary?.test_size_mb ?? 0} МБ</strong></article>
          </div>
          <section className="adminJobPanel">
            <div>
              <p className="panelLabel">Требует внимания</p>
              <h2>Операционные сигналы</h2>
            </div>
            <div className="adminAttentionList">
              {(overviewState?.attention || []).map((item, index) => (
                <button key={`${item.type}-${index}`} type="button" onClick={() => setAdminTab(item.target || "overview")}>
                  <span className={`adminBadge ${item.severity === "critical" ? "danger" : item.severity === "warning" ? "test" : "real"}`}>{item.severity || "info"}</span>
                  <strong>{item.title}</strong>
                  <em>{item.count ?? ""}</em>
                </button>
              ))}
              {!(overviewState?.attention || []).length && <p className="adminNotice">Критичных сигналов сейчас нет. Очередь и заявки в норме.</p>}
            </div>
          </section>
          <section className="adminJobPanel">
            <div>
              <p className="panelLabel">Последние действия</p>
              <h2>Журнал действий</h2>
            </div>
            <pre className="adminJsonPreview">{JSON.stringify(overviewState?.audit_events || [], null, 2)}</pre>
          </section>
        </section>
      )}

      {adminTab === "applications" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Заявки</p>
            <h2>Ранний доступ и Премиум</h2>
          </div>
          {approvedApplicationMessage && (
            <div className="approvalMessagePanel">
              <strong>Премиум-код для пользователя</strong>
              {approvedApplication?.requestNumber && <span>Заявка: <code>{approvedApplication.requestNumber}</code></span>}
              {approvedApplication?.accessCode && (
                <p className="adminIssuedCode">
                  <code>{approvedApplication.accessCode}</code>
                  <button type="button" onClick={() => navigator.clipboard?.writeText?.(approvedApplication.accessCode)}>Скопировать код</button>
                </p>
              )}
              <pre>{approvedApplicationMessage}</pre>
              <button type="button" onClick={() => navigator.clipboard?.writeText?.(approvedApplicationMessage)}>Скопировать сообщение</button>
            </div>
          )}
          <section className="adminToolbar">
            <input type="search" placeholder="Номер заявки, контакт, email, client ID" value={applicationSearch} onChange={(event) => setApplicationSearch(event.target.value)} />
            <div className="segmentedOptions">
              {[
                ["active", "Все рабочие"],
                ["premium", "Премиум"],
                ["early_access", "Ранний доступ"],
                ["pending", "Ожидают"],
                ["approved", "Одобрены"],
                ["rejected", "Отклонены"],
                ["test", "Тестовые"],
                ["all", "Все"],
              ].map(([id, title]) => (
                <button key={id} type="button" className={applicationFilter === id ? "active" : ""} onClick={() => setApplicationFilter(id)}>{title}</button>
              ))}
            </div>
          </section>
          {selectedApplications.length > 0 && (
            <section className="adminBulkBar">
              <strong>Выбрано заявок: {selectedApplications.length}</strong>
              <button type="button" onClick={() => bulkApplications("delete")}>Удалить выбранные</button>
              <button type="button" onClick={() => bulkApplications("approve")}>Одобрить выбранные</button>
              <button type="button" onClick={() => bulkApplications("reject")}>Отклонить выбранные</button>
              <button type="button" onClick={() => bulkApplications("archive")}>Архивировать</button>
              <button type="button" onClick={() => setSelectedApplications(filteredApplications.map((application) => application.id))}>Выделить все</button>
              <button type="button" onClick={() => setSelectedApplications([])}>Снять выбор</button>
            </section>
          )}
          <div className="adminTableWrap">
            <table className="adminTable">
              <thead>
                <tr>
                  <th><input type="checkbox" checked={filteredApplications.length > 0 && filteredApplications.every((application) => selectedApplications.includes(application.id))} onChange={(event) => setSelectedApplications(event.target.checked ? filteredApplications.map((application) => application.id) : [])} /></th>
                  <th>Номер заявки</th>
                  <th>Тип</th>
                  <th>Контакт</th>
                  <th>Дата</th>
                  <th>Статус</th>
                  <th>Пользователь</th>
                  <th>Код</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredApplications.map((application) => {
                  const isFinalApplicationStatus = ["approved", "code_issued", "activated", "rejected"].includes(String(application.status || ""));
                  const kind = application.type === "premium" ? "premium" : "early_access";
                  return (
                    <tr key={application.id}>
                      <td><input type="checkbox" checked={selectedApplications.includes(application.id)} onChange={(event) => setSelectedApplications((current) => event.target.checked ? [...new Set([...current, application.id])] : current.filter((id) => id !== application.id))} /></td>
                      <td><code>{application.request_number || "Старая запись"}</code></td>
                      <td>{kind === "premium" ? "Премиум" : "Ранний доступ"}</td>
                      <td>{application.email || application.telegram || application.contact || application.client_id || "—"}</td>
                      <td>{formatFeedbackDate(application.created_at)}</td>
                      <td><span className={`adminBadge ${isFinalApplicationStatus ? "real" : "test"}`}>{adminStatusLabels[application.status] || application.status || "Новая"}</span>{application.classification === "test" && <small> Тестовая</small>}</td>
                      <td><code>{application.user_id || "—"}</code></td>
                      <td>{application.code_status ? adminStatusLabels[application.code_status] || application.code_status : "—"}</td>
                      <td>
                        <div className="adminRowActions">
                          {!isFinalApplicationStatus && <button type="button" onClick={() => approveApplication(kind, application.id, kind === "premium" ? 30 : 7)}>Одобрить</button>}
                          {!isFinalApplicationStatus && <button type="button" onClick={() => rejectApplication(kind, application.id)}>Отклонить</button>}
                          {application.request_number && <button type="button" onClick={() => navigator.clipboard?.writeText?.(application.request_number)}>Копировать номер</button>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {!loading && filteredApplications.length === 0 && (
                  <tr><td className="adminEmpty" colSpan="9">Заявок по фильтру нет.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {adminTab === "premiumCodes" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Премиум</p>
            <h2>Коды и активации</h2>
            <p>Полные Премиум-коды не раскрываются повторно и не логируются. Полный код показывается только сразу после генерации.</p>
          </div>
          {lastAccessCode && (
            <p className="adminNotice">Последний выданный код: <code>{lastAccessCode}</code> <button type="button" onClick={() => navigator.clipboard?.writeText?.(lastAccessCode)}>Скопировать</button></p>
          )}
          <section className="adminToolbar">
            <input type="search" placeholder="Код, заявка, пользователь..." value={premiumSearch} onChange={(event) => setPremiumSearch(event.target.value)} />
            <div className="segmentedOptions">
              {[
                ["active", "Активные"],
                ["issued", "Выданы"],
                ["activated", "Активированы"],
                ["revoked", "Отозваны"],
                ["expired", "Истекли"],
                ["all", "Все"],
              ].map(([id, title]) => (
                <button key={id} type="button" className={premiumStatusFilter === id ? "active" : ""} onClick={() => setPremiumStatusFilter(id)}>{title}</button>
              ))}
            </div>
          </section>
          <div className="adminTableWrap">
            <table className="adminTable">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Статус</th>
                  <th>Заявка</th>
                  <th>Пользователь</th>
                  <th>Создан</th>
                  <th>Активирован</th>
                  <th>Истекает</th>
                  <th>Использования</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredPremiumCodes.map((code) => (
                  <tr key={code.id || `${code.request_number}-${code.user_id}`}>
                    <td><code>{code.masked_code || "STL-••••-••••-••••"}</code></td>
                    <td><span className={`adminBadge ${code.status === "activated" ? "real" : code.status === "revoked" ? "danger" : "test"}`}>{adminStatusLabels[code.status] || code.status || "Выдан"}</span></td>
                    <td>{code.request_number || code.application_id || "—"}</td>
                    <td><code>{code.user_id || "—"}</code></td>
                    <td>{formatFeedbackDate(code.created_at)}</td>
                    <td>{formatFeedbackDate(code.activated_at)}</td>
                    <td>{formatFeedbackDate(code.expires_at)}</td>
                    <td>{code.uses || 0} / {code.max_uses || 1}</td>
                    <td>
                      <div className="adminRowActions">
                        {code.user_id && <button type="button" onClick={() => { setAdminTab("users"); setAdminToast(`Найдите пользователя: ${code.user_id}`); }}>К пользователю</button>}
                        {code.request_number && <button type="button" onClick={() => { setAdminTab("applications"); setApplicationSearch(code.request_number); }}>К заявке</button>}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && !filteredPremiumCodes.length && (
                  <tr><td colSpan="9" className="adminEmpty">Премиум-кодов по фильтру нет.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {adminTab === "feedback" && (
        <>
      <section className="adminSummaryGrid">
        <article className="adminSummaryCard">
          <span>Реальных отзывов</span>
          <strong>{loading ? "…" : summary?.real_feedback ?? 0}</strong>
        </article>
        <article className="adminSummaryCard">
          <span>Средняя оценка реальных</span>
          <strong>{loading ? "…" : summary?.real_average_rating ?? 0}</strong>
        </article>
        <article className="adminSummaryCard">
          <span>Проблемных реальных</span>
          <strong>{loading ? "…" : summary?.real_problems_count ?? 0}</strong>
        </article>
        <article className="adminSummaryCard">
          <span>Тестовых отзывов</span>
          <strong>{loading ? "…" : summary?.test_feedback ?? 0}</strong>
        </article>
      </section>

      {!loading && Number(summary?.real_feedback || 0) === 0 && (
        <p className="adminNotice">Пока отображаются только тестовые отзывы. Реальная статистика появится после отзывов пользователей.</p>
      )}

      <section className="adminFilters">
        <div className="segmentedOptions">
          {[
            ["real", "Реальные"],
            ["test", "Тестовые"],
            ["all", "Все"],
          ].map(([id, title]) => (
            <button key={id} type="button" className={visibilityFilter === id ? "active" : ""} onClick={() => setVisibilityFilter(id)}>
              {title}
            </button>
          ))}
        </div>
        <div className="segmentedOptions">
          {[
            ["all", "Все оценки"],
            ["problem", "С проблемой"],
            ["good", "Хорошие"],
          ].map(([id, title]) => (
            <button key={id} type="button" className={filter === id ? "active" : ""} onClick={() => setFilter(id)}>
              {title}
            </button>
          ))}
        </div>
        <label className="adminOperationFilter">
          <span>По операции</span>
          <select value={operationFilter} onChange={(event) => setOperationFilter(event.target.value)}>
            <option value="all">Все операции</option>
            {operations.map((operation) => (
              <option key={operation} value={operation}>{operation}</option>
            ))}
          </select>
        </label>
        <button className="adminCleanupButton" type="button" onClick={cleanupTestFeedback}>
          Архивировать тестовые отзывы
        </button>
        {cleanupStatus && <span className="adminCleanupStatus">{cleanupStatus}</span>}
      </section>

      <section className="adminAnalyticsPanel">
        <div>
          <p className="panelLabel">Статистика по функциям</p>
          <h2>Статистика обработки</h2>
        </div>
        <div className="adminTableWrap">
          <table className="adminTable">
            <thead>
              <tr>
                <th>Операция</th>
                <th>Отзывов</th>
                <th>Средняя оценка</th>
                <th>Проблем</th>
                <th>Тестовых</th>
                <th>Реальных</th>
              </tr>
            </thead>
            <tbody>
              {operationRows.map((row) => (
                <tr key={row.operation}>
                  <td>{operationTitles[row.operation] || row.operation}</td>
                  <td>{row.count}</td>
                  <td>{row.average}</td>
                  <td>{row.problems}</td>
                  <td>{row.test}</td>
                  <td>{row.real}</td>
                </tr>
              ))}
              {!loading && operationRows.length === 0 && (
                <tr>
                  <td colSpan="6" className="adminEmpty">Нет данных по функциям.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="adminTableWrap">
        <table className="adminTable">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Тип</th>
              <th>ID задания</th>
              <th>Операции</th>
              <th>Оценка</th>
              <th>Комментарий</th>
              <th>Контакт</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => (
              <tr key={`${item.timestamp}-${item.job_id}`}>
                <td>{formatFeedbackDate(item.timestamp)}</td>
                <td><span className={item.is_test ? "adminBadge test" : "adminBadge real"}>{item.is_test ? "Служебный" : "Реальный"}</span></td>
                <td><code>{item.job_id || "—"}</code></td>
                <td>{(item.operations || []).map((operation) => adminOperationLabels[operation] || operation).join(", ") || "—"}</td>
                <td>{item.rating || "—"}</td>
                <td>{item.comment || "—"}</td>
                <td>{item.contact || "—"}</td>
                <td>
                  <div className="adminRowActions">
                    <button type="button" onClick={() => navigator.clipboard?.writeText?.(item.job_id || "")}>Скопировать ID</button>
                    <button type="button" onClick={() => loadJobDetails(item.job_id)}>Данные задания</button>
                    <a href={`${apiBaseUrl}/api/v1/jobs/${item.job_id}`} target="_blank" rel="noreferrer">JSON</a>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && filteredItems.length === 0 && (
              <tr>
                <td colSpan="8" className="adminEmpty">Отзывов пока нет.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="adminJobPanel">
        <div>
          <p className="panelLabel">Данные задания</p>
          <h2>Просмотр обработки по отзыву</h2>
        </div>
        {selectedJobLoading && <p>Загружаем данные задания...</p>}
        {selectedJobError && <p className="adminNotice">{selectedJobError}</p>}
        {!selectedJobLoading && !selectedJobError && !selectedJob && <p>Выберите отзыв и нажмите “Данные задания”.</p>}
        {selectedJob && (
          <div className="adminJobGrid">
            <span><em>ID задания</em><strong>{selectedJob.job_id || "—"}</strong></span>
            <span><em>Статус</em><strong>{adminStatusLabels[selectedJob.status] || selectedJob.status || "—"}</strong></span>
            <span><em>Операции</em><strong>{(selectedJob.operations || []).map((operation) => adminOperationLabels[operation] || operation).join(", ") || "—"}</strong></span>
            <span><em>Имя исходного файла</em><strong>{selectedJob.original_filename || selectedJob.filename || "—"}</strong></span>
            <span><em>Размер файла</em><strong>{formatBytes(selectedJob.size_bytes || jobResult.file?.size_bytes)}</strong></span>
            <span><em>Итоговая модель</em><strong>{jobResult.final_model || "—"}</strong></span>
            <span><em>Ошибка или причина</em><strong>{selectedJob.error || jobResult.reason || "—"}</strong></span>
            <span><em>Созданные файлы</em><strong>{jobGeneratedFiles.map((file) => file.name || file).join(", ") || "—"}</strong></span>
            <span><em>История обработки</em><strong>{jobProcessingHistory.map((step) => step.title || adminOperationLabels[step.operation] || step.operation).join(" → ") || "—"}</strong></span>
          </div>
        )}
      </section>
        </>
      )}

      {adminTab === "users" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Пользователи</p>
            <h2>Пользователи и Премиум-доступ</h2>
          </div>
          <div className="adminUserForm">
            <input value={newUserName} onChange={(event) => setNewUserName(event.target.value)} placeholder="Имя, необязательно" />
            <input value={newUserContact} onChange={(event) => setNewUserContact(event.target.value)} placeholder="Telegram / email / VK" />
            <button type="button" onClick={createUser}>Создать пользователя</button>
          </div>
          {lastAccessCode && (
            <p className="adminNotice">Код доступа создан: <code>{lastAccessCode}</code> <button type="button" onClick={() => navigator.clipboard?.writeText?.(lastAccessCode)}>Скопировать код</button></p>
          )}
          <section className="adminToolbar">
            <input type="search" value={userSearch} onChange={(event) => { setUserSearch(event.target.value); setUserPage(1); }} placeholder="Поиск по имени, контакту, ID..." />
            <select value={userPerPage} onChange={(event) => { setUserPerPage(Number(event.target.value)); setUserPage(1); }}>
              {[25, 50, 100].map((value) => <option key={value} value={value}>{value} строк</option>)}
            </select>
            <span>{filteredUsers.length ? `${(userPage - 1) * userPerPage + 1}–${Math.min(userPage * userPerPage, filteredUsers.length)} из ${filteredUsers.length}` : "0 из 0"}</span>
          </section>
          {selectedUsers.length > 0 && (
            <section className="adminBulkBar">
              <strong>Выбрано: {selectedUsers.length}</strong>
              <button type="button" onClick={() => bulkUsers("delete")}>Удалить</button>
              <button type="button" onClick={() => bulkUsers("block")}>Заблокировать</button>
              <button type="button" onClick={() => bulkUsers("unblock")}>Разблокировать</button>
              <button type="button" onClick={() => bulkUsers("grant_premium")}>Выдать Премиум</button>
              <button type="button" onClick={() => bulkUsers("remove_premium")}>Снять Премиум</button>
              <button type="button" onClick={() => bulkUsers("delete_with_jobs")}>Удалить вместе с заданиями</button>
              <button type="button" onClick={() => bulkUsers("delete_with_premium")}>Удалить вместе с кодами</button>
              <button type="button" onClick={() => bulkUsers("delete_with_feedback")}>Удалить вместе с отзывами</button>
              <button type="button" onClick={() => bulkUsers("delete_with_all")}>Удалить всё связанное</button>
              <button type="button" onClick={() => setSelectedUsers([])}>Снять выбор</button>
            </section>
          )}
          {userDeletionPlan && (
            <section className="adminDangerPanel">
              <div>
                <p className="panelLabel">План удаления</p>
                <h3>{userDeletionPlan.mode === "delete" ? "Окончательное удаление пользователей" : "Архивация пользователей"}</h3>
                <p>Пользователей: {(userDeletionPlan.items || []).length}. Файлы: {formatBytes(userDeletionPlan.estimated_size_bytes)}. Подтверждение: <code>{userDeletionPlan.confirmation_token}</code></p>
                {(userDeletionPlan.protected_items || []).length > 0 && <p className="error">Есть активные задания. Удаление будет заблокировано до отмены/завершения.</p>}
              </div>
              <div className="adminRowActions">
                <button type="button" onClick={executeUserDeletion}>Подтвердить действие</button>
                <button type="button" onClick={() => setUserDeletionPlan(null)}>Отмена</button>
              </div>
              <pre className="adminJsonPreview">{JSON.stringify((userDeletionPlan.items || []).map((item) => ({
                user: item.user?.contact || item.user?.id,
                classification: item.classification,
                applications: item.applications?.length || 0,
                jobs: item.jobs?.length || 0,
                feedback: item.feedback?.length || 0,
                files_size: item.files_size_bytes,
                can_delete_permanently: item.can_delete_permanently,
              })), null, 2)}</pre>
            </section>
          )}
          <div className="adminTableWrap">
            <table className="adminTable">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      checked={visibleUsers.length > 0 && visibleUsers.every((user) => selectedUsers.includes(user.id))}
                      onChange={(event) => {
                        setSelectedUsers((current) => event.target.checked
                          ? [...new Set([...current, ...visibleUsers.map((user) => user.id)])]
                          : current.filter((id) => !visibleUsers.some((user) => user.id === id)));
                      }}
                    />
                  </th>
                  <th>Имя</th>
                  <th>Контакт</th>
                  <th>Тариф</th>
                  <th>Премиум до</th>
                  <th>Заданий</th>
                  <th>Последняя активность</th>
                  <th>Статус</th>
                  <th>Меню</th>
                </tr>
              </thead>
              <tbody>
                {visibleUsers.map((user) => (
                  <tr key={user.id}>
                    <td><input type="checkbox" checked={selectedUsers.includes(user.id)} onChange={(event) => setSelectedUsers((current) => event.target.checked ? [...new Set([...current, user.id])] : current.filter((id) => id !== user.id))} /></td>
                    <td>{user.name || "—"}</td>
                    <td>{user.contact || "—"}</td>
                    <td><span className={`adminBadge ${user.access_level === "premium" ? "real" : user.access_level === "blocked" ? "danger" : "test"}`}>{user.plan || adminStatusLabels[user.access_level] || "Бесплатный"}</span></td>
                    <td>{user.premium_expires_at ? `${formatFeedbackDate(user.premium_expires_at)}${user.premium_days_left !== null ? `, осталось ${user.premium_days_left} дн.` : ""}` : "—"}</td>
                    <td>{user.jobs_count || 0}</td>
                    <td>{formatFeedbackDate(user.last_seen_at)}</td>
                    <td>{user.classification === "test" ? "Тестовый" : user.classification === "uncertain" ? "Требует проверки" : (user.blocked ? "Заблокирован" : "Активен")}</td>
                    <td>
                      <div className="adminContextMenu">
                        <button type="button" onClick={() => setUserMenuOpen(userMenuOpen === user.id ? "" : user.id)}>⋯</button>
                        {userMenuOpen === user.id && (
                          <div className="adminContextMenuList">
                            <button type="button" onClick={() => previewUserDeletion("archive", [user.id])}>Архивировать</button>
                            <button type="button" onClick={() => previewUserDeletion("delete", [user.id])}>Удалить</button>
                            <button type="button" onClick={() => bulkUsers("grant_premium", [user.id])}>Выдать Премиум</button>
                            <button type="button" onClick={() => bulkUsers("remove_premium", [user.id])}>Снять Премиум</button>
                            <button type="button" onClick={() => userAction(user.id, "block")}>Заблокировать</button>
                            <button type="button" onClick={() => userAction(user.id, "unblock")}>Разблокировать</button>
                            <button type="button" onClick={() => userAction(user.id, "reset-code")}>Сбросить код доступа</button>
                            <button type="button" onClick={() => navigator.clipboard?.writeText?.(JSON.stringify(user, null, 2))}>Экспортировать</button>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && visibleUsers.length === 0 && (
                  <tr><td colSpan="9" className="adminEmpty">Пользователей пока нет.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="adminPagination">
            <button type="button" disabled={userPage <= 1} onClick={() => setUserPage((page) => Math.max(1, page - 1))}>Назад</button>
            <span>Страница {Math.min(userPage, userPageCount)} из {userPageCount}</span>
            <button type="button" disabled={userPage >= userPageCount} onClick={() => setUserPage((page) => Math.min(userPageCount, page + 1))}>Вперёд</button>
          </div>
        </section>
      )}

      {adminTab === "queue" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Очередь</p>
            <h2>Нагрузка и задачи обработки</h2>
          </div>
          <div className="adminSummaryGrid">
            <article className="adminSummaryCard">
              <span>В очереди</span>
              <strong>{queueState?.queued_jobs ?? 0}</strong>
            </article>
            <article className="adminSummaryCard">
              <span>В обработке</span>
              <strong>{queueState?.processing_jobs ?? 0}</strong>
            </article>
            <article className="adminSummaryCard">
              <span>Ошибки за 24 часа</span>
              <strong>{queueState?.failed_24h ?? 0}</strong>
            </article>
            <article className="adminSummaryCard">
              <span>Зависшие задания</span>
              <strong>{queueState?.stale_processing_jobs ?? 0}</strong>
            </article>
          </div>
          <div className="adminJobGrid">
            <span><em>Размер очереди</em><strong>{queueState?.queue_size ?? 0}</strong></span>
            <span><em>Завершено за 24 часа</em><strong>{queueState?.completed_24h ?? 0}</strong></span>
            <span><em>Среднее время</em><strong>{formatDuration(queueState?.average_processing_seconds)}</strong></span>
            <span><em>Бесплатно / ранний / Премиум</em><strong>{`${queueState?.by_access_level?.free || 0} / ${queueState?.by_access_level?.early_access || 0} / ${queueState?.by_access_level?.premium || 0}`}</strong></span>
            <span><em>Текущая нагрузка</em><strong>{Number(queueState?.processing_jobs || 0) > 0 ? "Есть обработка" : "Нет активной обработки"}</strong></span>
          </div>
          <section className="adminToolbar">
            <div className="segmentedOptions">
              {[
                ["active", "Активные"],
                ["queued", "В очереди"],
                ["processing", "В обработке"],
                ["errors", "Ошибки"],
                ["test", "Тестовые"],
                ["all", "Все"],
              ].map(([id, title]) => (
                <button key={id} type="button" className={queueFilter === id ? "active" : ""} onClick={() => setQueueFilter(id)}>{title}</button>
              ))}
            </div>
            <button type="button" onClick={() => loadData({ silent: true })}>Обновить очередь</button>
          </section>
          {selectedJobs.length > 0 && (
            <section className="adminBulkBar">
              <strong>Выбрано заданий: {selectedJobs.length}</strong>
              <button type="button" onClick={() => bulkJobs("delete")}>Удалить</button>
              <button type="button" onClick={() => bulkJobs("quarantine")}>Переместить в карантин</button>
              <button type="button" onClick={() => bulkJobs("release_lock")}>Освободить блокировку</button>
              <button type="button" onClick={() => bulkJobs("retry")}>Повторить</button>
              <button type="button" onClick={() => bulkJobs("force_delete")}>Принудительно удалить выбранные</button>
              <button type="button" onClick={() => setSelectedJobs([])}>Снять выбор</button>
            </section>
          )}
          <div className="adminTableWrap">
            <table className="adminTable">
              <thead>
                <tr>
                  <th><input type="checkbox" checked={filteredQueueJobs.length > 0 && filteredQueueJobs.every((job) => selectedJobs.includes(job.job_id))} onChange={(event) => setSelectedJobs(event.target.checked ? filteredQueueJobs.map((job) => job.job_id) : [])} /></th>
                  <th>ID задания</th>
                  <th>Статус</th>
                  <th>Операции</th>
                  <th>Доступ</th>
                  <th>Приоритет</th>
                  <th>Позиция</th>
                  <th>Создана</th>
                  <th>PID</th>
                  <th>Воркер</th>
                  <th>Запуск</th>
                  <th>Последний сигнал</th>
                  <th>Изменение</th>
                  <th>Контейнер</th>
                  <th>Ключ Redis</th>
                  <th>Блокировка</th>
                  <th>Владелец</th>
                  <th>Длительность</th>
                  <th>Размер</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredQueueJobs.map((job) => (
                  <tr key={job.job_id}>
                    <td><input type="checkbox" checked={selectedJobs.includes(job.job_id)} onChange={(event) => setSelectedJobs((current) => event.target.checked ? [...new Set([...current, job.job_id])] : current.filter((id) => id !== job.job_id))} /></td>
                    <td><code>{shortJobId(job.job_id)}</code></td>
                    <td><span className={`adminBadge ${job.status === "processing" || job.status === "completed" ? "real" : job.status === "failed" ? "danger" : "test"}`}>{adminStatusLabels[job.status] || job.status}</span>{job.classification === "test" && <small> Тестовое</small>}</td>
                    <td>{(job.operation_labels || job.operations || []).join(", ") || "—"}</td>
                    <td>{adminStatusLabels[job.access_level] || job.access_level || "Бесплатный"}</td>
                    <td>{queuePriorityLabel(job.priority)}</td>
                    <td>{job.queue_position || "—"}</td>
                    <td>{formatFeedbackDate(job.created_at)}</td>
                    <td>{job.pid || job.runtime?.pid || "—"}</td>
                    <td>{job.worker || job.runtime?.worker || "—"}</td>
                    <td>{formatFeedbackDate(job.runtime?.started_at || job.started_at)}</td>
                    <td>{formatFeedbackDate(job.last_heartbeat || job.runtime?.last_heartbeat)}</td>
                    <td>{formatFeedbackDate(job.last_update || job.runtime?.last_update)}</td>
                    <td>{job.container || job.runtime?.container || "—"}</td>
                    <td><code>{job.redis_key || job.runtime?.redis_key || "—"}</code></td>
                    <td>{(job.lock_status || job.runtime?.lock_status) === "locked" ? "Есть" : "Нет"}</td>
                    <td>{job.owner || job.runtime?.owner || "—"}</td>
                    <td>{formatDuration(job.duration)}</td>
                    <td>{job.file_size_mb ? `${job.file_size_mb} МБ` : "—"}</td>
                    <td>
                      <div className="adminRowActions">
                        <button type="button" onClick={() => navigator.clipboard?.writeText?.(job.job_id || "")}>Скопировать ID</button>
                        <button type="button" onClick={() => loadJobDetails(job.job_id)}>Данные задания</button>
                        <button type="button" onClick={() => bulkJobs("release_lock", [job.job_id])}>Освободить блокировку</button>
                        <button type="button" onClick={() => bulkJobs("retry", [job.job_id])}>Повторить</button>
                        <button type="button" onClick={() => bulkJobs("delete", [job.job_id])}>Удалить</button>
                        <button type="button" onClick={() => bulkJobs("force_delete", [job.job_id])}>Принудительно удалить</button>
                        {(job.status === "queued" || job.status === "processing") && (
                          <button type="button" onClick={() => cancelAdminJob(job.job_id)}>Отменить задачу</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && !filteredQueueJobs.length && (
                  <tr><td colSpan="20" className="adminEmpty">Заданий по фильтру нет.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {adminTab === "cleanup" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Очистка сервера</p>
            <h2>Безопасная очистка артефактов обработки</h2>
          </div>
          <section className="adminDangerPanel">
            <div>
              <p className="panelLabel">Центр тестовых данных</p>
              <h3>Подтверждённые служебные записи</h3>
              <p>Удаляются только записи, классифицированные как тестовые. Реальные и сомнительные данные остаются на месте.</p>
            </div>
            <div className="adminJobGrid">
              <span><em>Пользователи</em><strong>{testDataSummary?.users?.test ?? 0} тестовых / {testDataSummary?.users?.uncertain ?? 0} спорных</strong></span>
              <span><em>Заявки</em><strong>{testDataSummary?.applications?.test ?? 0} тестовых / {testDataSummary?.applications?.uncertain ?? 0} спорных</strong></span>
              <span><em>Задания</em><strong>{testDataSummary?.jobs?.test ?? 0} тестовых / {testDataSummary?.jobs?.uncertain ?? 0} спорных</strong></span>
              <span><em>Отзывы</em><strong>{testDataSummary?.feedback?.test ?? 0} тестовых / {testDataSummary?.feedback?.uncertain ?? 0} спорных</strong></span>
              <span><em>Тестовые файлы</em><strong>{testDataSummary?.test_size_mb ?? 0} МБ</strong></span>
              <span><em>Защищено активных</em><strong>{testDataSummary?.protected_active_jobs ?? 0}</strong></span>
            </div>
            <div className="adminRowActions">
              <button type="button" disabled={testDataBusy} onClick={() => scanTestData(true)}>{testDataBusy ? "Сканируем..." : "Просканировать тестовые данные"}</button>
              <button type="button" disabled={testDataBusy} onClick={cleanupTestData}>Удалить подтверждённые тестовые</button>
            </div>
            {(testDataState?.items || []).length > 0 && (
              <pre className="adminJsonPreview">{JSON.stringify(testDataState.items.slice(0, 40), null, 2)}</pre>
            )}
          </section>
          <section className="adminDangerPanel">
            <div>
              <p className="panelLabel">Очистка системы</p>
              <h3>Быстрые безопасные операции</h3>
              <p>После каждого удаления автоматически запускается проверка целостности. Опасные операции с кэшем, временными файлами и карантином помечаются как требующие отдельного подтверждения.</p>
            </div>
            <div className="adminJobGrid">
              <span><em>Можно освободить</em><strong>{formatBytes(cleanupPlan?.total_size_bytes || 0)}</strong></span>
              <span><em>Зависшие задания</em><strong>{queueState?.stale_processing_jobs ?? 0}</strong></span>
              <span><em>Пустые папки</em><strong>Проверка по кнопке</strong></span>
              <span><em>Карантин</em><strong>Требует подтверждения</strong></span>
            </div>
            <div className="adminRowActions">
              <button type="button" disabled={testDataBusy} onClick={cleanupTestData}>Удалить все тестовые данные</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["stale_jobs"])}>Удалить зависшие задания</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["orphan_files"])}>Удалить неиспользуемые файлы</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["empty_dirs"])}>Удалить пустые папки</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["redis"])}>Очистить Redis</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["cache"])}>Очистить кэш</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["temp"])}>Очистить временные файлы</button>
              <button type="button" disabled={systemCleanupBusy} onClick={() => systemCleanup(["quarantine"])}>Очистить карантин</button>
              <button type="button" onClick={() => runIntegrityCheck(true)}>Проверка целостности</button>
            </div>
          </section>
          <div className="adminJobGrid">
            <span><em>Свободно на диске</em><strong>{formatBytes(cleanupState?.disk?.free)}</strong></span>
            <span><em>Загрузки</em><strong>{formatBytes(cleanupState?.uploads_size_bytes)}</strong></span>
            <span><em>Результаты</em><strong>{formatBytes(cleanupState?.results_size_bytes)}</strong></span>
            <span><em>Отзывы</em><strong>{formatBytes(cleanupState?.feedback_size_bytes)}</strong></span>
            <span><em>Пользователи</em><strong>{formatBytes(cleanupState?.users_size_bytes)}</strong></span>
            <span><em>Карантин</em><strong>{formatBytes(cleanupState?.quarantine_size_bytes)}</strong></span>
            <span><em>Каталоги job</em><strong>{cleanupState?.job_dirs ? `${cleanupState.job_dirs.uploads}/${cleanupState.job_dirs.results}` : "—"}</strong></span>
            <span><em>Активные задания</em><strong>{(cleanupState?.active_jobs || []).length}</strong></span>
            <span><em>Последняя очистка</em><strong>{cleanupState?.last_run ? `${cleanupState.last_run.deleted} удалено, ${cleanupState.last_run.freed_mb} МБ` : "—"}</strong></span>
          </div>
          <div className="adminRowActions">
            <button type="button" onClick={() => loadData({ silent: true })}>Проверить место</button>
            <button type="button" onClick={scanCleanup}>Просканировать</button>
            <button type="button" disabled={!cleanupPlan || cleanupSelection.length === 0} onClick={executeCleanup}>Удалить выбранное</button>
            <button type="button" onClick={() => navigator.clipboard?.writeText?.("cp deploy/systemd/stl-master-cleanup.* /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now stl-master-cleanup.timer")}>Скопировать команду установки автоочистки</button>
          </div>
          {cleanupStatus && <p className="adminCleanupStatus">{cleanupStatus}</p>}
          {cleanupPlan && (
            <section className="cleanupPlanPanel">
              <div>
                <p className="panelLabel">План очистки</p>
                <h3>Сканирование {cleanupPlan.scan_id}</h3>
                <p>Подтверждение для выбранного удаления: <code>{cleanupPlan.confirmation_token}</code></p>
                <p>Всего: {(cleanupPlan.items || []).length}, защищено: {cleanupPlan.protected_count || 0}, потенциально освободится: {formatBytes(cleanupPlan.total_size_bytes)}.</p>
              </div>
              <div className="adminTableWrap">
                <table className="adminTable">
                  <thead>
                    <tr>
                      <th>Выбор</th>
                      <th>Категория</th>
                      <th>Путь</th>
                      <th>Размер</th>
                      <th>Возраст</th>
                      <th>Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cleanupPlan.items || []).slice(0, 80).map((item) => (
                      <tr key={item.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={cleanupSelection.includes(item.id)}
                            disabled={!item.safe_to_delete}
                            onChange={(event) => {
                              setCleanupSelection((current) => event.target.checked ? [...new Set([...current, item.id])] : current.filter((id) => id !== item.id));
                            }}
                          />
                        </td>
                        <td><span className="adminBadge test">{item.category}</span></td>
                        <td><code>{item.path_masked}</code></td>
                        <td>{formatBytes(item.size_bytes)}</td>
                        <td>{item.age_hours} ч</td>
                        <td>{item.reason}</td>
                      </tr>
                    ))}
                    {!(cleanupPlan.items || []).length && (
                      <tr><td colSpan="6" className="adminEmpty">Удалять нечего. Защищённые файлы не попадут в удаление.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {(cleanupPlan.protected_examples || []).length > 0 && (
                <pre className="adminJsonPreview">{JSON.stringify(cleanupPlan.protected_examples, null, 2)}</pre>
              )}
            </section>
          )}
          {cleanupState?.last_run && <pre className="adminJsonPreview">{JSON.stringify(cleanupState.last_run, null, 2)}</pre>}
          {systemCleanupPreview && (
            <div className="adminConfirmOverlay" role="dialog" aria-modal="true" aria-labelledby="system-cleanup-confirm-title">
              <section className="adminConfirmModal">
                <button className="adminConfirmClose" type="button" onClick={() => setSystemCleanupPreview(null)} disabled={systemCleanupBusy} aria-label="Закрыть подтверждение">×</button>
                <p className="panelLabel">Подтверждение очистки</p>
                <h3 id="system-cleanup-confirm-title">Проверьте предварительный расчёт</h3>
                <p>Операция выполнится только по выбранной категории. Пользовательские загрузки, результаты и активные задания защищены allowlist и проверкой состояния.</p>
                <div className="adminJobGrid compact">
                  <span><em>Действия</em><strong>{systemCleanupPreview.actions.map((action) => adminBulkActionTitles[action] || action).join(", ")}</strong></span>
                  <span><em>Потенциально освободится</em><strong>{formatBytes(systemCleanupPreview.payload?.freed_bytes || 0)}</strong></span>
                  <span><em>Карантин</em><strong>{formatBytes(cleanupState?.quarantine_size_bytes || 0)}</strong></span>
                  <span><em>Проверка целостности</em><strong>После удаления</strong></span>
                </div>
                <pre className="adminJsonPreview">{JSON.stringify(systemCleanupPreview.payload?.actions || {}, null, 2)}</pre>
                {systemCleanupPreview.actions.includes("quarantine") && (
                  <p className="adminNotice warning">Карантин будет очищен только потому, что вы нажали отдельную кнопку “Очистить карантин”. Это действие не входит в обычную очистку файлов.</p>
                )}
                <div className="adminRowActions confirmActions">
                  <button type="button" disabled={systemCleanupBusy} onClick={executeSystemCleanup}>{systemCleanupBusy ? "Выполняем..." : "Подтвердить очистку"}</button>
                  <button type="button" disabled={systemCleanupBusy} onClick={() => setSystemCleanupPreview(null)}>Отмена</button>
                </div>
              </section>
            </div>
          )}
        </section>
      )}

      {adminTab === "features" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Функции приложения</p>
            <h2>Готовность функций</h2>
            <p>Раздел показывает реальное состояние функций. Переключатели не добавлены там, где нет безопасного backend-отката и проверки worker.</p>
          </div>
          <div className="adminRowActions">
            <button type="button" onClick={() => loadData({ silent: true })}>Проверить готовность</button>
          </div>
          <div className="adminTableWrap">
            <table className="adminTable">
              <thead>
                <tr>
                  <th>Функция</th>
                  <th>ID</th>
                  <th>Статус</th>
                  <th>Доступ</th>
                  <th>Frontend</th>
                  <th>Backend</th>
                  <th>Worker</th>
                  <th>Причина</th>
                </tr>
              </thead>
              <tbody>
                {(featureState.items || []).map((feature) => (
                  <tr key={feature.id}>
                    <td>{feature.name}</td>
                    <td><code>{feature.id}</code></td>
                    <td><span className={`adminBadge ${feature.status === "stable" ? "real" : feature.status === "beta" ? "test" : "danger"}`}>{feature.status_label || adminStatusLabels[feature.status] || feature.status}</span></td>
                    <td>{adminStatusLabels[feature.access] || feature.access || "Бесплатный"}</td>
                    <td>{feature.frontend_visible ? "Да" : "Нет"}</td>
                    <td>{feature.backend_enabled ? "Да" : "Нет"}</td>
                    <td>{feature.worker_available ? "Да" : "Нет"}</td>
                    <td>{feature.reason || "—"}</td>
                  </tr>
                ))}
                {!loading && !(featureState.items || []).length && (
                  <tr><td colSpan="8" className="adminEmpty">Feature flags недоступны.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {adminTab === "system" && (
        <section className="adminJobPanel">
          <div>
            <p className="panelLabel">Система</p>
            <h2>Безопасность и доступ</h2>
          </div>
          <div className="adminJobGrid">
            <span><em>Ранний доступ</em><strong>100 МБ, базовые функции</strong></span>
            <span><em>Премиум</em><strong>300 МБ, локальное сглаживание, соединения, подгонка под стол</strong></span>
            <span><em>Заблокирован</em><strong>Загрузка запрещена</strong></span>
            <span><em>Вход администратора</em><strong>{securityState?.admin_auth_enabled ? "Включён" : "Выключен"}</strong></span>
            <span><em>Резервный токен</em><strong>{securityState?.emergency_token_enabled ? "Включён" : "Выключен"}</strong></span>
            <span><em>Сессия до</em><strong>{formatFeedbackDate(adminSession?.expires_at)}</strong></span>
            <span><em>Ошибок входа</em><strong>{securityState?.failed_login_attempts ?? 0}</strong></span>
            <span><em>Блокировка</em><strong>{securityState?.locked ? "Да" : "Нет"}</strong></span>
          </div>
          <div className="adminAnalyticsPanel">
            <p className="panelLabel">Журнал безопасности</p>
            <h2>Последние события</h2>
            <div className="adminTableWrap">
              <table className="adminTable">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Событие</th>
                    <th>IP</th>
                    <th>Детали</th>
                  </tr>
                </thead>
                <tbody>
                  {(securityState?.audit_events || []).map((event, index) => (
                    <tr key={`${event.timestamp}-${event.event}-${index}`}>
                      <td>{formatFeedbackDate(event.timestamp)}</td>
                      <td>{event.event}</td>
                      <td>{event.ip || "—"}</td>
                      <td>{JSON.stringify(event.details || {})}</td>
                    </tr>
                  ))}
                  {!(securityState?.audit_events || []).length && (
                    <tr><td className="adminEmpty" colSpan="4">Событий журнала пока нет.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
      </section>
    </main>
  );
}

function AdminApp() {
  const apiBaseUrl = useMemo(getApiBaseUrl, []);
  return (
    <ConfigProvider>
      <View activePanel="admin">
        <Panel id="admin">
          <PanelHeader className="adminVkPanelHeader">Панель STL Master</PanelHeader>
          <AdminFeedbackDashboard apiBaseUrl={apiBaseUrl} />
        </Panel>
      </View>
    </ConfigProvider>
  );
}

const RootComponent = typeof window !== "undefined" && window.location.pathname === "/admin" ? AdminApp : App;

createRoot(document.getElementById("root")).render(<RootComponent />);
