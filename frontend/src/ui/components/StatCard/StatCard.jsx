import React from "react";
import "../../styles/ui.css";

export function StatCard({ value, label, icon, className = "", ...props }) {
  return (
    <div className={["stlm-ui-stat-card", className].filter(Boolean).join(" ")} {...props}>
      {icon}
      <div className="stlm-ui-stat-card__value">{value}</div>
      <div className="stlm-ui-stat-card__label">{label}</div>
    </div>
  );
}
