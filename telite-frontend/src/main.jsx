import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { Agentation } from "agentation";
import "./styles/tokens.css";
import "./styles/themes/dark.css";
import "./styles/themes/light.css";
import "./styles/global.css";
import "./styles/dashboard-variants.css";
import "./styles/components/notifications.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
    {import.meta.env.DEV && <Agentation />}
  </StrictMode>
);
