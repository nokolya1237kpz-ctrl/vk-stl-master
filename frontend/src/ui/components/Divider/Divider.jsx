import React from "react";
import "../../styles/ui.css";

export function Divider({ className = "", ...props }) {
  return <hr className={["stlm-ui-divider", className].filter(Boolean).join(" ")} {...props} />;
}
