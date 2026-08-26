import "./PublicPageFrame.css";

/** Shared light editorial wrapper for public, non-standalone route families. */
export default function PublicPageFrame({ children, className = "", tone = "editorial", testId }) {
  return (
    <div className={`public-page-frame public-page-frame--${tone} ${className}`.trim()} data-testid={testId}>
      {children}
    </div>
  );
}
