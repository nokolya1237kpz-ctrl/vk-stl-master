import React from "react";
import "../../styles/ui.css";

const variantClass = {
  primary: "stlm-ui-button--primary",
  secondary: "stlm-ui-button--secondary",
  ghost: "stlm-ui-button--ghost",
  outline: "stlm-ui-button--outline",
  danger: "stlm-ui-button--danger",
};

const sizeClass = {
  sm: "stlm-ui-button--sm",
  md: "",
  lg: "stlm-ui-button--lg",
};

export function Button({
  as: Component = "button",
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}) {
  const classes = [
    "stlm-ui-button",
    variantClass[variant] || variantClass.primary,
    sizeClass[size] || "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Component className={classes} {...props}>
      {children}
    </Component>
  );
}
