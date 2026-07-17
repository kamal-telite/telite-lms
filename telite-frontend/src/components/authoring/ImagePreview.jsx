import React from "react";

// Image Preview Component with Formatting
export default function ImagePreview({ settings }) {
  const getImageStyle = () => {
    const style = {
      maxWidth: "100%",
      height: "auto",
      display: "block",
    };

    // Apply width
    if (settings.width) {
      style.width = settings.width;
    }

    // Apply height if specified
    if (settings.height) {
      style.height = settings.height;
    } else if (settings.maintain_aspect_ratio !== false) {
      style.height = "auto";
    }

    // Apply alignment
    if (settings.alignment === "center") {
      style.marginLeft = "auto";
      style.marginRight = "auto";
    } else if (settings.alignment === "left") {
      style.marginRight = "auto";
    } else if (settings.alignment === "right") {
      style.marginLeft = "auto";
    }

    // Apply margins
    if (settings.margin_top) style.marginTop = settings.margin_top;
    if (settings.margin_bottom) style.marginBottom = settings.margin_bottom;
    if (settings.margin_left) style.marginLeft = settings.margin_left;
    if (settings.margin_right) style.marginRight = settings.margin_right;

    // Apply border radius
    if (settings.border_radius) {
      style.borderRadius = settings.border_radius;
    } else {
      style.borderRadius = "8px";
    }

    // Apply border
    if (settings.border_style && settings.border_style !== "none") {
      style.borderStyle = settings.border_style;
      if (settings.border_width) style.borderWidth = settings.border_width;
      if (settings.border_color) style.borderColor = settings.border_color;
    }

    // Apply shadow
    if (settings.shadow && settings.shadow !== "none") {
      const shadows = {
        small: "0 2px 4px rgba(0,0,0,0.1)",
        medium: "0 4px 8px rgba(0,0,0,0.15)",
        large: "0 8px 16px rgba(0,0,0,0.2)",
      };
      style.boxShadow = shadows[settings.shadow] || shadows.medium;
    }

    // Apply responsive behavior
    if (settings.responsive !== false) {
      style.maxWidth = "100%";
      style.height = "auto";
    }

    return style;
  };

  const getImageWrapperStyle = () => {
    const wrapperStyle = {};

    // Apply position
    if (settings.position === "inline") {
      wrapperStyle.display = "inline-block";
      wrapperStyle.verticalAlign = "middle";
    } else if (settings.position === "above" || settings.position === "below" || settings.position === "between") {
      wrapperStyle.display = "block";
      wrapperStyle.textAlign = settings.alignment === "center" ? "center" : 
                              settings.alignment === "right" ? "right" : "left";
    }

    return wrapperStyle;
  };

  return (
    <div style={getImageWrapperStyle()}>
      <img 
        src={settings.url} 
        alt={settings.alt_text || settings.alt || ""} 
        style={getImageStyle()} 
      />
      {settings.caption && (
        <div style={{ 
          marginTop: "8px", 
          fontSize: "14px", 
          color: "var(--text-secondary)",
          textAlign: settings.alignment === "center" ? "center" : 
                   settings.alignment === "right" ? "right" : "left",
          fontStyle: "italic"
        }}>
          {settings.caption}
        </div>
      )}
    </div>
  );
}
