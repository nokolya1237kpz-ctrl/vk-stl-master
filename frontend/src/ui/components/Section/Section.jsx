import React from "react";
import "../../styles/ui.css";

export function Section({
  number,
  kicker,
  title,
  description,
  className = "",
  children,
  ...props
}) {
  return (
    <section className={["stlm-ui-section", className].filter(Boolean).join(" ")} {...props}>
      {(number || kicker) && (
        <div className="stlm-ui-section__kicker">
          {number && <span className="stlm-ui-section__number">{number}</span>}
          {kicker && <span>{kicker}</span>}
        </div>
      )}
      {title && <h2 className="stlm-ui-section__title">{title}</h2>}
      {description && <p className="stlm-ui-section__description">{description}</p>}
      {children}
    </section>
  );
}
