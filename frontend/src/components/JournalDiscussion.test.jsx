import React, { act } from "react";
import { createRoot } from "react-dom/client";

let mockUser = null;
const mockPublicGet = jest.fn();
const mockPrivateGet = jest.fn();
const mockPut = jest.fn();
const mockDelete = jest.fn();
const mockPost = jest.fn();

jest.mock("react-router-dom", () => ({ Link: ({ to, children, ...props }) => <a href={to} {...props} onClick={(event) => event.preventDefault()}>{children}</a> }), { virtual: true });
jest.mock("../context/AuthContext", () => ({ useAuth: () => ({ user: mockUser }) }));
jest.mock("../lib/api", () => ({
  api: { get: (...args) => mockPublicGet(...args) },
  userApi: { get: (...args) => mockPrivateGet(...args), put: (...args) => mockPut(...args), delete: (...args) => mockDelete(...args), post: (...args) => mockPost(...args) },
}));
import JournalDiscussion from "./JournalDiscussion";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const deferred = () => { let resolve; let reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

function mount(slug = "first-article") {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  return {
    container,
    render: async (next = slug) => { await act(async () => { root.render(<JournalDiscussion slug={next} />); }); },
    cleanup: () => act(() => { root.unmount(); container.remove(); }),
  };
}
const click = async (button) => act(async () => { button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); });
const fillComment = async (container, value) => act(async () => {
  const textarea = container.querySelector("textarea");
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(textarea, value);
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
});
const submit = async (container) => act(async () => { container.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });

describe("JournalDiscussion persisted reader engagement", () => {
  let view;
  beforeEach(() => {
    jest.clearAllMocks(); mockUser = null;
    mockPublicGet.mockResolvedValue({ data: { likes: 2, comments: [] } });
    mockPrivateGet.mockResolvedValue({ data: { liked: false } });
    view = mount();
  });
  afterEach(() => view.cleanup());

  test("signed-out readers can see discussion and receive continuation links without mutations", async () => {
    await view.render();
    expect(mockPublicGet).toHaveBeenCalledWith("/blog/first-article/discussion");
    expect(view.container.querySelector("form")).toBeNull();
    const signIn = [...view.container.querySelectorAll("a")].find((node) => node.textContent.includes("Sign in to like"));
    expect(signIn.getAttribute("href")).toBe("/login?next=%2Fjournal%2Ffirst-article");
    await click(signIn);
    expect(mockPrivateGet).not.toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled(); expect(mockDelete).not.toHaveBeenCalled(); expect(mockPost).not.toHaveBeenCalled();
  });

  test("signed-in like and unlike persist once and use returned counts", async () => {
    mockUser = { id: "test-reader" };
    mockPut.mockResolvedValue({ data: { liked: true, likes: 3 } });
    mockDelete.mockResolvedValue({ data: { liked: false, likes: 2 } });
    await view.render();
    expect(mockPrivateGet).toHaveBeenCalledWith("/blog/first-article/my-like");
    await click(view.container.querySelector("button[aria-pressed]"));
    expect(mockPut).toHaveBeenCalledTimes(1);
    expect(mockPut).toHaveBeenCalledWith("/blog/first-article/like");
    expect(view.container.querySelector("button[aria-pressed]").getAttribute("aria-pressed")).toBe("true");
    expect(view.container.querySelector("button[aria-pressed]").textContent).toBe("Liked · 3");
    await click(view.container.querySelector("button[aria-pressed]"));
    expect(mockDelete).toHaveBeenCalledTimes(1);
    expect(mockDelete).toHaveBeenCalledWith("/blog/first-article/like");
    expect(view.container.querySelector("button[aria-pressed]").textContent).toBe("Like · 2");
  });

  test("failed like preserves count and presents a plain actionable error", async () => {
    mockUser = { id: "test-reader" }; mockPut.mockRejectedValue(new Error("network"));
    await view.render(); await click(view.container.querySelector("button[aria-pressed]"));
    expect(view.container.querySelector("button[aria-pressed]").textContent).toBe("Like · 2");
    expect(view.container.querySelector('[role="alert"]').textContent).toContain("Your like could not be saved");
  });

  test("comment success sends trimmed text and renders only the server-authoritative result", async () => {
    mockUser = { id: "test-reader" };
    mockPost.mockResolvedValue({ data: { id: "comment-1", author: "A Reader", text: "A thoughtful response", created_at: "2026-10-01T12:00:00Z" } });
    await view.render(); await fillComment(view.container, "  A thoughtful response  "); await submit(view.container);
    expect(mockPost).toHaveBeenCalledWith("/blog/first-article/comments", { text: "A thoughtful response" });
    expect(view.container.querySelector(".journal-comment p").textContent).toBe("A thoughtful response");
    expect(view.container.querySelector("textarea").value).toBe("");
    expect(view.container.textContent).toContain("Join the conversation · 1");
  });

  test("failed comment preserves the draft and never fabricates a saved comment", async () => {
    mockUser = { id: "test-reader" }; mockPost.mockRejectedValue(new Error("network"));
    await view.render(); await fillComment(view.container, "Keep my draft"); await submit(view.container);
    expect(view.container.querySelector("textarea").value).toBe("Keep my draft");
    expect(view.container.querySelector(".journal-comment")).toBeNull();
    expect(view.container.querySelector('[role="alert"]').textContent).toContain("Your comment could not be saved");
  });

  test("empty comments never initiate an API mutation", async () => {
    mockUser = { id: "test-reader" };
    await view.render(); await fillComment(view.container, "  "); await submit(view.container);
    expect(mockPost).not.toHaveBeenCalled();
  });

  test("a stale article discussion or my-like response cannot replace the current article state", async () => {
    mockUser = { id: "test-reader" };
    const oldDiscussion = deferred(); const oldLike = deferred();
    mockPublicGet.mockImplementation((url) => url.includes("first-article") ? oldDiscussion.promise : Promise.resolve({ data: { likes: 8, comments: [] } }));
    mockPrivateGet.mockImplementation((url) => url.includes("first-article") ? oldLike.promise : Promise.resolve({ data: { liked: false } }));
    await view.render(); await view.render("second-article");
    await act(async () => { oldDiscussion.resolve({ data: { likes: 99, comments: [{ id: "old", author: "Old", text: "Wrong article", created_at: "2026-10-01" }] } }); oldLike.resolve({ data: { liked: true } }); });
    expect(view.container.querySelector("button[aria-pressed]").textContent).toBe("Like · 8");
    expect(view.container.textContent).not.toContain("Wrong article");
  });
  test("a stale like mutation cannot overwrite the next article's count", async () => {
    mockUser = { id: "test-reader" };
    const oldMutation = deferred();
    mockPut.mockImplementation(() => oldMutation.promise);
    mockPublicGet.mockImplementation((url) => Promise.resolve({ data: { likes: url.includes("first-article") ? 2 : 8, comments: [] } }));
    await view.render(); await click(view.container.querySelector("button[aria-pressed]"));
    await view.render("second-article");
    await act(async () => oldMutation.resolve({ data: { liked: true, likes: 3 } }));
    expect(view.container.querySelector("button[aria-pressed]").textContent).toBe("Like · 8");
  });

  test("a stale comment mutation cannot append an old article's comment to the next article", async () => {
    mockUser = { id: "test-reader" };
    const oldMutation = deferred(); mockPost.mockImplementation(() => oldMutation.promise);
    await view.render(); await fillComment(view.container, "Old article reply"); await submit(view.container);
    await view.render("second-article");
    await act(async () => oldMutation.resolve({ data: { id: "old", author: "Reader", text: "Old article reply", created_at: "2026-10-01" } }));
    expect(view.container.textContent).not.toContain("Old article reply");
    expect(view.container.querySelector(".journal-comment")).toBeNull();
  });

  test("reader comments render as text rather than executable markup", async () => {
    mockPublicGet.mockResolvedValue({ data: { likes: 0, comments: [{ id: "safe", author: "<script>Reader</script>", text: '<img src=x onerror="alert(1)">', created_at: "2026-10-01" }] } });
    await view.render();
    expect(view.container.querySelector("script")).toBeNull();
    expect(view.container.querySelector(".journal-comment img")).toBeNull();
    expect(view.container.querySelector(".journal-comment p").textContent).toBe('<img src=x onerror="alert(1)">');
  });

});
