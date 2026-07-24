import React from "react";
import "../../styles/ui.css";

export function Input({ label, className = "", ...props }) {
  const input = <input className={["stlm-ui-input", className].filter(Boolean).join(" ")} {...props} />;

  if (!label) {
    return input;
  }

  return (
    <label className="stlm-ui-field">
      <span>{label}</span>
      {input}
    </label>
  );
}
