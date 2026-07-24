import React from "react";
import "../../styles/ui.css";

export function Panel({ title, actions, className = "", children, ...props }) {
  return (
    <aside className={["stlm-ui-panel", className].filter(Boolean).join(" ")} {...props}>
      {(title || actions) && (
        <div className="stlm-ui-panel__header">
          {title && <h3 className="stlm-ui-panel__title">{title}</h3>}
          {actions}
        </div>
      )}
      {children}
    </aside>
  );
}
