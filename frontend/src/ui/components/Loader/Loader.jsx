import React from "react";
import "../../styles/ui.css";

export function Loader({ label = "Загрузка", className = "", ...props }) {
  return (
    <span
      aria-label={label}
      className={["stlm-ui-loader", className].filter(Boolean).join(" ")}
      role="status"
      {...props}
    />
  );
}
