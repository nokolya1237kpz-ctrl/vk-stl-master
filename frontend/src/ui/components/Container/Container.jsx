import React from "react";
import "../../styles/ui.css";

export function Container({ as: Component = "div", className = "", children, ...props }) {
  return (
    <Component className={["stlm-ui-container", className].filter(Boolean).join(" ")} {...props}>
      {children}
    </Component>
  );
}
