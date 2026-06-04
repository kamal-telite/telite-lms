import CarouselNavigation from "./CarouselNavigation";
import CarouselStage from "./CarouselStage";
import "./ProductCarousel.css";

export default function ProductCarousel({ panels, activePanel, onChangePanel }) {
  const currentPanel = panels.find((panel) => panel.id === activePanel) ?? panels[0];

  return (
    <div className="product-carousel">
      <CarouselNavigation
        panels={panels}
        activePanel={currentPanel.id}
        onChangePanel={onChangePanel}
      />
      <CarouselStage panel={currentPanel} />
    </div>
  );
}
