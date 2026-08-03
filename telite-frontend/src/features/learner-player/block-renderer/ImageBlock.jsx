import React from 'react';

const imageShadows = {
  small: "0 2px 4px rgba(0,0,0,0.1)",
  medium: "0 4px 8px rgba(0,0,0,0.15)",
  large: "0 8px 16px rgba(0,0,0,0.2)",
};

const alignToText = (alignment) => alignment === "center" ? "center" : alignment === "right" ? "right" : "left";

export function getImageStyle(settings = {}) {
  const style = { maxWidth: "100%", height: "auto", display: "block" };

  if (settings.width) style.width = settings.width;

  if (settings.height) style.height = settings.height;
  else if (settings.maintain_aspect_ratio !== false && settings.maintainAspectRatio !== false) style.height = "auto";

  if (settings.alignment === "center") {
    style.marginLeft = "auto";
    style.marginRight = "auto";
  } else if (settings.alignment === "left") {
    style.marginRight = "auto";
  } else if (settings.alignment === "right") {
    style.marginLeft = "auto";
  }

  const marginTop = settings.margin_top ?? settings.marginTop;
  const marginBottom = settings.margin_bottom ?? settings.marginBottom;
  const marginLeft = settings.margin_left ?? settings.marginLeft;
  const marginRight = settings.margin_right ?? settings.marginRight;
  if (marginTop) style.marginTop = marginTop;
  if (marginBottom) style.marginBottom = marginBottom;
  if (marginLeft) style.marginLeft = marginLeft;
  if (marginRight) style.marginRight = marginRight;

  style.borderRadius = settings.border_radius ?? settings.borderRadius ?? "8px";

  const borderStyle = settings.border_style ?? settings.borderStyle;
  if (borderStyle && borderStyle !== "none") {
    style.borderStyle = borderStyle;
    const borderWidth = settings.border_width ?? settings.borderWidth;
    const borderColor = settings.border_color ?? settings.borderColor;
    if (borderWidth) style.borderWidth = borderWidth;
    if (borderColor) style.borderColor = borderColor;
  }

  if (settings.shadow && settings.shadow !== "none") {
    style.boxShadow = imageShadows[settings.shadow] || imageShadows.medium;
  }

  if (settings.responsive !== false) {
    style.maxWidth = "100%";
    style.height = "auto";
  }

  return style;
}

export function getImageWrapperStyle(settings = {}) {
  const wrapperStyle = {};

  if (settings.position === "inline") {
    wrapperStyle.display = "inline-block";
    wrapperStyle.verticalAlign = "middle";
  } else if (["above", "below", "between"].includes(settings.position)) {
    wrapperStyle.display = "block";
    wrapperStyle.textAlign = alignToText(settings.alignment);
  }

  return wrapperStyle;
}

export function ImageBlock({ settings = {}, src, alt, title }) {
  return (
    <div style={getImageWrapperStyle(settings)}>
      <img
        src={src ?? settings.url ?? settings.src}
        alt={alt ?? settings.alt_text ?? settings.alt ?? ""}
        title={title ?? settings.title}
        style={getImageStyle(settings)}
      />
      {settings.caption && (
        <div style={{ marginTop: "8px", fontSize: "14px", color: "var(--text-secondary)", textAlign: alignToText(settings.alignment), fontStyle: "italic" }}>
          {settings.caption}
        </div>
      )}
    </div>
  );
}
