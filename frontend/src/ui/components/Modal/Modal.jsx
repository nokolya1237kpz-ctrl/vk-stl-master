import React from "react";
import "../../styles/ui.css";

export function Modal({
  open = false,
  title,
  children,
  footer,
  onClose,
  closeLabel = "Закрыть",
  className = "",
  ...props
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="stlm-ui-modal-backdrop">
      <div
        aria-modal="true"
        className={["stlm-ui-modal", className].filter(Boolean).join(" ")}
        role="dialog"
        {...props}
      >
        <div className="stlm-ui-modal__header">
          {title && <h2 className="stlm-ui-modal__title">{title}</h2>}
          {onClose && (
            <button aria-label={closeLabel} className="stlm-ui-icon-button" type="button" onClick={onClose}>
              x
            </button>
          )}
        </div>
        <div className="stlm-ui-modal__body">{children}</div>
        {footer && <div className="stlm-ui-modal__footer">{footer}</div>}
      </div>
    </div>
  );
}
