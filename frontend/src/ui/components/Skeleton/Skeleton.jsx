import React from "react";
import "../../styles/ui.css";

export function Skeleton({ width = "100%", height = "1rem", className = "", style, ...props }) {
  return (
    <span
      aria-hidden="true"
      className={["stlm-ui-skeleton", className].filter(Boolean).join(" ")}
      style={{ width, height, ...style }}
      {...props}
    />
  );
}
