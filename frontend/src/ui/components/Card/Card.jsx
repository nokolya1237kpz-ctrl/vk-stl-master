import React from "react";
import "../../styles/ui.css";

export function Card({ compact = false, interactive = false, className = "", children, ...props }) {
  const classes = [
    "stlm-ui-card",
    compact ? "stlm-ui-card--compact" : "",
    interactive ? "stlm-ui-card--interactive" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
}
