import React from "react";
import { Progress } from "@vkontakte/vkui";

export const studioToolGroups = [
  {
    title: "Анализ",
    items: ["check", "remove_artifacts", "improve", "surface", "local"],
  },
  {
    title: "Геометрия",
    items: ["split", "fit_to_bed", "reduce", "orientation", "auto_orientation", "symmetry"],
  },
];

export const studioSteps = ["Загрузка", "Анализ", "Настройка", "Обработка", "Проверка", "Экспорт"];

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
        <em>{jobStatus?.message || "STL вход · STL/ZIP/JSON/TXT результат"}</em>
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

export function StudioSidebar({ presets, selectedMode, onSelect }) {
  const presetsById = new Map(presets.map((preset) => [preset.id, preset]));
  return (
    <aside className="studioSidebar" aria-label="Инструменты STL Master Studio">
      <div className="studioSidebarTop">
        <span className="studioPanelLabel">Инструменты</span>
        {studioToolGroups.map((group) => {
          const groupItems = group.items.map((id) => presetsById.get(id)).filter(Boolean);
          if (groupItems.length === 0) return null;
          return (
            <section className="studioToolGroup" key={group.title}>
              <h2>{group.title}</h2>
              <div className="studioToolList">
                {groupItems.map((preset) => (
                  <button
                    className={`studioToolButton ${selectedMode === preset.id ? "active" : ""}`}
                    key={preset.id}
                    type="button"
                    aria-pressed={selectedMode === preset.id}
                    onClick={() => onSelect(preset.id)}
                  >
                    <span className="studioToolIcon">{preset.icon}</span>
                    <span>
                      <b>{preset.title}</b>
                      <small>{preset.result}</small>
                    </span>
                  </button>
                ))}
              </div>
            </section>
          );
        })}
      </div>
      <div className="studioSidebarFoot">
        <span>STL input</span>
        <b>.stl</b>
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
      <p className="studioPanelLabel">Новая сцена</p>
      <h1>Загрузите STL-модель</h1>
      <p>
        Перетащите файл в окно редактора или выберите его вручную. Для обработки собственных моделей нужен доступ, демо можно открыть без загрузки.
      </p>
      <div className="studioEmptyActions">
        <button className="studioPrimaryAction" type="button" onClick={hasUploadAccess ? onSelectFile : onRequestAccess}>
          <Icon type="upload" />
          Выбрать STL-файл
        </button>
        <button className="studioTextAction" type="button" onClick={onOpenDemo}>
          Открыть демо-модель
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
  const activeIndex =
    currentStatus === "completed" ? 5 :
      currentStatus === "failed" ? 4 :
        currentStatus === "processing" ? 3 :
          currentStatus === "queued" ? 2 :
            selectedPreset?.id === "check" ? 1 : 2;
  const downloadUrl = result?.download_url || jobStatus?.result?.download_url;
  return (
    <section className="studioWorkflowBar" aria-label="Ход обработки">
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
