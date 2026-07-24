import React from "react";
import "../../styles/ui.css";

export function MetricCard({ value, label, delta, className = "", ...props }) {
  return (
    <div className={["stlm-ui-metric-card", className].filter(Boolean).join(" ")} {...props}>
      <div className="stlm-ui-metric-card__value">{value}</div>
      <div className="stlm-ui-metric-card__label">{label}</div>
      {delta && <div className="stlm-ui-metric-card__delta">{delta}</div>}
    </div>
  );
}
