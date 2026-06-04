export default function CarouselNavigation({ panels, activePanel, onChangePanel }) {
  const activeIndex = panels.findIndex((panel) => panel.id === activePanel);

  const focusPanelByIndex = (nextIndex) => {
    const safeIndex = (nextIndex + panels.length) % panels.length;
    onChangePanel(panels[safeIndex].id);
  };

  const handleKeyDown = (event) => {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      focusPanelByIndex(activeIndex + 1);
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      focusPanelByIndex(activeIndex - 1);
    }
    if (event.key === "Home") {
      event.preventDefault();
      focusPanelByIndex(0);
    }
    if (event.key === "End") {
      event.preventDefault();
      focusPanelByIndex(panels.length - 1);
    }
  };

  return (
    <div
      className="carousel-nav"
      role="tablist"
      aria-label="Product showcase panels"
      onKeyDown={handleKeyDown}
    >
      {panels.map((panel) => {
        const isActive = panel.id === activePanel;
        const tabId = `showcase-tab-${panel.id}`;
        const panelId = `showcase-panel-${panel.id}`;

        return (
          <button
            key={panel.id}
            id={tabId}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={panelId}
            tabIndex={isActive ? 0 : -1}
            className={isActive ? "active" : ""}
            onClick={() => onChangePanel(panel.id)}
          >
            <span>{panel.title}</span>
          </button>
        );
      })}
    </div>
  );
}
