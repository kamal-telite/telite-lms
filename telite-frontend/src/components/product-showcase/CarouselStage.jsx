import ProductFrame from "./ProductFrame";
import useReducedMotionSafe from "../../hooks/useReducedMotionSafe";
import { motionPresets } from "../../utils/motionPresets";

export default function CarouselStage({ panel }) {
  const reducedMotion = useReducedMotionSafe();
  const preset = reducedMotion ? motionPresets.reduced : motionPresets.cinematicFade;
  const PanelComponent = panel.Component;
  const panelId = `showcase-panel-${panel.id}`;
  const tabId = `showcase-tab-${panel.id}`;

  return (
    <div className="carousel-stage">
      <div className="ambient-glow" aria-hidden="true" />
      <ProductFrame title={panel.title}>
        <div
          id={panelId}
          role="tabpanel"
          aria-labelledby={tabId}
          className="panel-transition-wrapper"
          key={panel.id}
          style={{
            "--panel-duration": preset.duration,
            "--panel-easing": preset.easing,
            "--panel-translate-start": preset.translateStart,
            "--panel-scale-start": preset.scaleStart,
            "--panel-blur-start": preset.blurStart,
          }}
        >
          <PanelComponent />
        </div>
      </ProductFrame>
    </div>
  );
}
