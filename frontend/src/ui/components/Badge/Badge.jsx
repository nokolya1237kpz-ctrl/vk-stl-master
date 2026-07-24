import React from "react";
import "../../styles/ui.css";

const variantClass = {
  neutral: "",
  primary: "stlm-ui-badge--primary",
  success: "stlm-ui-badge--success",
  warning: "stlm-ui-badge--warning",
  danger: "stlm-ui-badge--danger",
};

export function Badge({ variant = "neutral", className = "", children, ...props }) {
  return (
    <span
      className={["stlm-ui-badge", variantClass[variant] || "", className].filter(Boolean).join(" ")}
      {...props}
    >
      {children}
    </span>
  );
}
