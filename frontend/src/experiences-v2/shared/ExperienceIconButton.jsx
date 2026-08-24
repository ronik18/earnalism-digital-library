export default function ExperienceIconButton({ children, label, onClick, pressed, disabled = false, className = "" }) {
  return (
    <button
      type="button"
      className={`experience-icon-button ${className}`.trim()}
      onClick={onClick}
      aria-label={label}
      aria-pressed={typeof pressed === "boolean" ? pressed : undefined}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
