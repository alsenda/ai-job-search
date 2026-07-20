/**
 * Entry point: a two-route hash router (dashboard and import).
 * Quiz sessions are started from the dashboard and render in place;
 * a page reload during a quiz simply returns to the dashboard.
 */

import { showDashboard } from "./dashboard";
import { showImport } from "./import";

function route(): void {
  if (window.location.hash.startsWith("#/import")) {
    showImport();
  } else {
    void showDashboard();
  }
}

window.addEventListener("hashchange", route);
route();
