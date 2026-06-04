import { useState } from "react";
import ProductCarousel from "./ProductCarousel";
import { showcaseRegistry } from "./showcaseRegistry";

export default function ShowcasePanels() {
  const [activePanel, setActivePanel] = useState(showcaseRegistry[0].id);

  return (
    <div
      className="showcase-panels"
      style={{
        "--showcase-active-glow":
          showcaseRegistry.find((panel) => panel.id === activePanel)?.glow ??
          "var(--showcase-glow-analytics)",
      }}
    >
      <ProductCarousel
        panels={showcaseRegistry}
        activePanel={activePanel}
        onChangePanel={setActivePanel}
      />
    </div>
  );
}
