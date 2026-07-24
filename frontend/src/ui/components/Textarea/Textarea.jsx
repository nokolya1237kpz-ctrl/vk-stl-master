import React from "react";
import "../../styles/ui.css";

export function Textarea({ label, className = "", ...props }) {
  const textarea = (
    <textarea className={["stlm-ui-textarea", className].filter(Boolean).join(" ")} {...props} />
  );

  if (!label) {
    return textarea;
  }

  return (
    <label className="stlm-ui-field">
      <span>{label}</span>
      {textarea}
    </label>
  );
}
