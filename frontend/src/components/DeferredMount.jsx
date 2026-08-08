import { useEffect, useRef, useState } from "react";

export default function DeferredMount({
  children,
  className = "",
  minHeight = 1,
  rootMargin = "600px 0px",
  testId,
}) {
  const boundaryRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (ready) return undefined;
    const boundary = boundaryRef.current;
    if (!boundary) return undefined;

    if (typeof IntersectionObserver !== "function") {
      const idle = typeof window.requestIdleCallback === "function"
        ? window.requestIdleCallback(() => setReady(true), { timeout: 1800 })
        : window.setTimeout(() => setReady(true), 250);
      return () => {
        if (typeof window.cancelIdleCallback === "function") window.cancelIdleCallback(idle);
        else window.clearTimeout(idle);
      };
    }

    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      setReady(true);
      observer.disconnect();
    }, { rootMargin });
    observer.observe(boundary);
    return () => observer.disconnect();
  }, [ready, rootMargin]);

  return (
    <div
      ref={boundaryRef}
      className={className}
      data-deferred-state={ready ? "mounted" : "pending"}
      data-testid={testId}
      style={ready ? undefined : { minHeight }}
    >
      {ready ? children : null}
    </div>
  );
}
