import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ReaderExperienceV2 from "./ReaderExperienceV2";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("ReaderExperienceV2 text controls", () => {
  test("changes the rendered reading text size through both desktop and mobile controls", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => root.render(<ReaderExperienceV2 onNavigate={() => {}} />));
    const readingText = container.querySelector('[data-testid="reader-reading-text"]');
    expect(readingText.style.fontSize).toBe("1rem");
    const controls = [...container.querySelectorAll('button[aria-label="Increase text size"], button[aria-label="Decrease text size"]')];
    const desktopIncrease = controls.find((control) => control.getAttribute("aria-label") === "Increase text size");
    act(() => desktopIncrease.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(readingText.style.fontSize).toBe("1.05rem");
    const mobileDecrease = controls.find((control) => control.getAttribute("aria-label") === "Decrease text size");
    act(() => mobileDecrease.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    expect(readingText.style.fontSize).toBe("1rem");
    act(() => root.unmount());
    container.remove();
  });
});
