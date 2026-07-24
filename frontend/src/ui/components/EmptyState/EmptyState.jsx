import React from "react";
import "../../styles/ui.css";

export function EmptyState({ icon, title, description, action, className = "", children, ...props }) {
  return (
    <div className={["stlm-ui-empty-state", className].filter(Boolean).join(" ")} {...props}>
      {icon}
      {title && <h3 className="stlm-ui-empty-state__title">{title}</h3>}
      {description && <p className="stlm-ui-empty-state__description">{description}</p>}
      {children}
      {action}
    </div>
  );
}
