import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { TextEncoder, TextDecoder } from "util";

// Router 7 requires the browser encoding API, absent in Jest's jsdom runtime.
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
// CRA Jest does not understand Router 7's conditional package exports and its
// legacy react-router-dom main path is absent. Use its genuine re-exported core
// implementation rather than mocking Link's click handling.
jest.mock("react-router-dom", () => jest.requireActual("react-router"), { virtual: true });
const { MemoryRouter, useLocation, useNavigate } = require("react-router-dom");

jest.mock("../context/SettingsContext", () => ({ useSettings: () => ({ social: {} }) }));
jest.mock("../context/AuthContext", () => ({ useAuth: () => ({ user: null }) }));
const Header = require("./Header").default;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function Location() {
  const location = useLocation();
  return <output data-testid="current-route">{location.pathname}{location.search}</output>;
}
function mount(header) {
  const container = document.createElement("div"); document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<MemoryRouter initialEntries={["/reader/a-ghost-story"]}>{header}<Location /></MemoryRouter>));
  return { container, cleanup: () => act(() => { root.unmount(); container.remove(); }) };
}

describe("canonical Header with actual React Router links", () => {
  let view;
  afterEach(() => view?.cleanup());

  test("settles immersive navigation before Link can perform its own router navigation", async () => {
    let finishExit;
    const sessionExit = new Promise((resolve) => { finishExit = resolve; });
    const onExit = jest.fn();
    function ImmersiveShell() {
      const navigate = useNavigate();
      return <Header onNavigatePath={async (item) => { onExit(item); await sessionExit; navigate(item.to); }} />;
    }
    view = mount(<ImmersiveShell />);
    await act(async () => view.container.querySelector('[data-nav-key="journal"]').dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })));
    expect(onExit).toHaveBeenCalledTimes(1);
    expect(onExit).toHaveBeenCalledWith({ key: "journal", to: "/journal", label: "Blog" });
    expect(view.container.querySelector('[data-testid="current-route"]').textContent).toBe("/reader/a-ghost-story");
    await act(async () => finishExit());
    expect(view.container.querySelector('[data-testid="current-route"]').textContent).toBe("/journal");
  });

  test("ordinary public Header navigation still uses the router without an exit callback", () => {
    view = mount(<Header />);
    act(() => view.container.querySelector('[data-nav-key="journal"]').dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })));
    expect(view.container.querySelector('[data-testid="current-route"]').textContent).toBe("/journal");
  });

  test.each([{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }])("preserves native modified link behavior: %p", (options) => {
    const onNavigatePath = jest.fn(); view = mount(<Header onNavigatePath={onNavigatePath} />);
    const link = view.container.querySelector('[data-nav-key="journal"]');
    // Native navigation is outside jsdom; prevent its default at the target
    // after the Header capture handler has already evaluated the modifier.
    link.addEventListener("click", (event) => event.preventDefault(), { once: true });
    act(() => link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, ...options })));
    expect(onNavigatePath).not.toHaveBeenCalled();
    expect(view.container.querySelector('[data-testid="current-route"]').textContent).toBe("/reader/a-ghost-story");
  });
});
