import React, { useEffect, useMemo, useState } from "react";
import { Progress } from "@vkontakte/vkui";

export const studioToolGroups = [
  {
    title: "Анализ",
    caption: "Проверка модели перед обработкой",
    items: ["check"],
  },
  {
    title: "Ремонт",
    caption: "Исправление сетки и AI-артефактов",
    items: ["remove_artifacts", "improve", "surface", "local"],
  },
  {
    title: "Оптимизация",
    caption: "Снижение веса модели",
    items: ["reduce"],
  },
  {
    title: "Подготовка к печати",
    caption: "Ориентация, стол и симметрия",
    items: ["orientation", "auto_orientation", "symmetry", "fit_to_bed"],
  },
  {
    title: "Разделение",
    caption: "Плоский разрез и типы соединений",
    items: ["split", "split_pins", "split_tongue", "split_dovetail", "split_puzzle"],
  },
  {
    title: "Экспорт",
    caption: "Пакет STL, ZIP, JSON и TXT",
    items: [],
  },
];

const studioSteps = ["Загрузка", "Анализ", "Настройка", "Обработка", "Проверка", "Экспорт"];

export function StudioHeader({
  currentUser,
  currentUserLoading,
  file,
  jobStatus,
  apiBaseUrl,
  onGoHome,
  onOpenPremium,
  onOpenApplication,
  Icon,
  PremiumStatusControl,
  statusLabel,
  supportUrl,
}) {
  const canExport = Boolean(jobStatus?.result?.download_url);
  return (
    <header className="studioHeader">
      <button className="studioBrand" type="button" onClick={onGoHome}>
        <Icon type="logo" />
        <span>
          <b>STL Master Studio</b>
          <small>{file?.name || "Рабочая область"}</small>
        </span>
      </button>
      <div className="studioProjectStatus" aria-live="polite">
        <span>{jobStatus?.status ? statusLabel(jobStatus.status) : "Готово к работе"}</span>
        <em>{jobStatus?.message || "Вход: STL · Результат: STL, ZIP, JSON, TXT"}</em>
      </div>
      <div className="studioHeaderActions">
        <PremiumStatusControl
          className="studioPremiumButton"
          currentUser={currentUser}
          loading={currentUserLoading}
          onOpenApplication={onOpenApplication}
          onOpenPremium={onOpenPremium}
        />
        <button className="studioIconButton" type="button" onClick={() => window.open(supportUrl, "_blank", "noopener,noreferrer")}>
          Помощь
        </button>
        <button
          className="studioExportButton"
          disabled={!canExport}
          type="button"
          onClick={() => canExport && window.open(`${apiBaseUrl}${jobStatus.result.download_url}`, "_blank", "noopener,noreferrer")}
        >
          <Icon type="export" />
          Экспорт
        </button>
      </div>
    </header>
  );
}

export function StudioSidebar({ presets, selectedMode, onSelect, hasFile = false }) {
  const presetsById = useMemo(() => new Map(presets.map((preset) => [preset.id, preset])), [presets]);
  const activeGroupTitle = studioToolGroups.find((group) => group.items.includes(selectedMode))?.title || "Анализ";
  const [openGroupTitle, setOpenGroupTitle] = useState(activeGroupTitle);

  useEffect(() => {
    setOpenGroupTitle(activeGroupTitle);
  }, [activeGroupTitle]);

  return (
    <aside className="studioSidebar" aria-label="Инструменты STL Master Studio">
      <div className="studioSidebarTop">
        <div className="studioToolsHeader">
          <span className="studioPanelLabel">Операции</span>
          <strong>{hasFile ? activeGroupTitle : "После загрузки STL"}</strong>
          <small>{hasFile ? "Выберите действие и запустите обработку." : "Сначала загрузите модель в центральную область."}</small>
        </div>
        {studioToolGroups.map((group) => {
          const groupItems = group.items.map((id) => presetsById.get(id)).filter(Boolean);
          const enabledCount = groupItems.filter((preset) => !preset.disabled).length;
          const isOpen = openGroupTitle === group.title;
          const hasActive = group.items.includes(selectedMode);
          const panelId = `studio-tool-group-${group.title.toLowerCase().replace(/\s+/g, "-")}`;
          return (
            <section className={`studioToolGroup ${isOpen ? "open" : ""} ${hasActive ? "hasActive" : ""}`} key={group.title}>
              <button
                className="studioToolGroupTitle"
                type="button"
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => setOpenGroupTitle((current) => current === group.title ? "" : group.title)}
              >
                <span>
                  <strong className="studioToolGroupHeading">{group.title}</strong>
                  <small>{hasActive ? `Выбрано: ${presetsById.get(selectedMode)?.title || group.caption}` : group.caption}</small>
                </span>
                <b>{enabledCount}/{group.items.length}</b>
                <i aria-hidden="true">⌄</i>
              </button>
              <div className="studioToolList" id={panelId} hidden={!isOpen}>
                {groupItems.length > 0 ? groupItems.map((preset) => {
                  const disabled = Boolean(preset.disabled || (!hasFile && preset.id !== "check"));
                  const caption = preset.disabled ? (preset.disabledReason || "Режим готовится") : preset.result;
                  return (
                    <button
                      className={`studioToolButton ${selectedMode === preset.id ? "active" : ""} ${preset.disabled ? "comingSoon" : ""}`}
                      key={preset.id}
                      type="button"
                      aria-pressed={selectedMode === preset.id}
                      aria-disabled={disabled}
                      disabled={disabled}
                      title={preset.disabled ? caption : undefined}
                      onClick={() => !disabled && onSelect(preset.id)}
                    >
                      <span className="studioToolIcon">{preset.icon}</span>
                      <span>
                        <b>{preset.title}</b>
                        <small>{caption}</small>
                      </span>
                    </button>
                  );
                }) : (
                  <p className="studioToolGroupEmpty">Экспорт и файлы результата появятся после обработки.</p>
                )}
              </div>
            </section>
          );
        })}
      </div>
      <div className="studioSidebarFoot">
        <span>Формат входа</span>
        <b>STL</b>
      </div>
    </aside>
  );
}

export function StudioEmptyState({ uploadLimitMb, hasUploadAccess, onSelectFile, onOpenDemo, onOpenRequirements, onRequestAccess, onDrop, onDragOver, Icon }) {
  return (
    <div className="studioEmptyState" onDrop={onDrop} onDragOver={onDragOver}>
      <div className="studioDropAura" aria-hidden="true">
        <Icon type="upload" />
      </div>
      <p className="studioPanelLabel">Первый шаг</p>
      <h1>Загрузите STL-модель</h1>
      <strong>Перетащите STL</strong>
      <p>Перетащите модель в рабочую область или выберите файл вручную. Демо можно открыть отдельно, чтобы быстро посмотреть возможности Studio.</p>
      <div className="studioEmptyActions">
        <button className="studioPrimaryAction" type="button" onClick={hasUploadAccess ? onSelectFile : onRequestAccess}>
          <Icon type="upload" />
          Выбрать STL-файл
        </button>
        <button className="studioTextAction" type="button" onClick={onOpenDemo}>
          Попробовать демо
        </button>
        <button className="studioTextAction" type="button" onClick={onOpenRequirements}>
          Требования к файлу
        </button>
      </div>
      <div className="studioFileLimits">
        <span>Входной формат: STL</span>
        <span>Лимит: до {uploadLimitMb} МБ</span>
        <span>Результат: STL, ZIP, JSON, TXT</span>
      </div>
    </div>
  );
}

export function StudioWorkflowBar({ selectedPreset, selectedOperations, jobId, jobStatus, progress, uploading, error, canRun, onRun, result, apiBaseUrl, operationTitles, shortJobId, statusMessage, ProgressComponent = Progress }) {
  const currentStatus = jobStatus?.status || (uploading ? "processing" : jobId ? "queued" : "idle");
  const activeOperations = new Set(selectedOperations || []);
  const activeIndex =
    currentStatus === "completed" ? 5 :
      currentStatus === "failed" ? 4 :
        currentStatus === "processing" ? 3 :
          currentStatus === "queued" ? 2 :
            activeOperations.has("split_model") || activeOperations.has("fit_to_bed") ? 4 :
              activeOperations.has("reduce_polygons") || activeOperations.has("apply_orientation") || activeOperations.has("auto_orientation") ? 3 :
                activeOperations.has("print_repair") || activeOperations.has("remove_ai_artifacts") || activeOperations.has("surface_recovery") ? 2 :
                  selectedPreset?.id === "check" ? 1 : 2;
  const downloadUrl = result?.download_url || jobStatus?.result?.download_url;
  return (
    <section className="studioWorkflowBar" aria-label="Ход обработки">
      <div className="studioPipelineHeader">
        <span className="studioPanelLabel">Этапы обработки</span>
        <strong>{downloadUrl ? "Результат готов" : currentStatus === "idle" ? "Готов к запуску" : statusMessage(currentStatus, jobStatus?.message)}</strong>
      </div>
      <div className="studioStepper">
        {studioSteps.map((step, index) => (
          <span className={index <= activeIndex ? "active" : ""} key={step} aria-current={index === activeIndex ? "step" : undefined}>
            <i>{index + 1}</i>
            {step}
          </span>
        ))}
      </div>
      <div className="studioRunPanel">
        <div className="studioRunMeta">
          <strong>{selectedPreset?.title || "Проверить модель"}</strong>
          <span>{selectedOperations.map((operation) => operationTitles[operation] || operation).join(" · ")}</span>
          {jobId && <em>Задание: {shortJobId(jobId)}</em>}
          {error && <em className="studioErrorText">{error}</em>}
        </div>
        {jobStatus && (
          <div className="studioProgressMini">
            <ProgressComponent value={progress} />
            <span>{progress}% · {statusMessage(jobStatus.status, jobStatus.message)}</span>
          </div>
        )}
        <div className="studioRunActions">
          {downloadUrl && (
            <a className="studioSecondaryAction" href={`${apiBaseUrl}${downloadUrl}`}>
              Скачать результат
            </a>
          )}
          <button className="studioPrimaryAction compact" disabled={!canRun || uploading} type="button" onClick={onRun}>
            {uploading ? "Обрабатываем..." : "Запустить обработку"}
          </button>
        </div>
      </div>
    </section>
  );
}
