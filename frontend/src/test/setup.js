import "@testing-library/jest-dom";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom não implementa scrollIntoView (usado pelo auto-scroll do chat)
if (!window.HTMLElement.prototype.scrollIntoView) {
  window.HTMLElement.prototype.scrollIntoView = () => {};
}

// Limpa o DOM após cada teste
afterEach(() => {
  cleanup();
});
