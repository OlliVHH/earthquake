// Human: Browser entry — mounts React with router, i18n, and global styles.
// Agent: CALLS createRoot, BrowserRouter; READS DOM #root; WRITES none; failure mode — missing #root throws.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./i18n";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
