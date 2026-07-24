import React from "react";
import "../../styles/ui.css";

export function IconButton({ label, children, className = "", type = "button", ...props }) {
  return (
    <button
      aria-label={label}
      className={["stlm-ui-icon-button", className].filter(Boolean).join(" ")}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}
