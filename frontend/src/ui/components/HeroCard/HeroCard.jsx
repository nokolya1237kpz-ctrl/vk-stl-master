import React from "react";
import "../../styles/ui.css";

export function HeroCard({ icon, title, text, className = "", ...props }) {
  return (
    <div className={["stlm-ui-hero-card", className].filter(Boolean).join(" ")} {...props}>
      {icon && <div className="stlm-ui-hero-card__icon">{icon}</div>}
      <div>
        {title && <h3 className="stlm-ui-hero-card__title">{title}</h3>}
        {text && <p className="stlm-ui-hero-card__text">{text}</p>}
      </div>
    </div>
  );
}
