export default function ExperiencePanel({ title, eyebrow, children, className = "" }) {
  return (
    <section className={`experience-panel ${className}`.trim()}>
      {(eyebrow || title) && <header className="experience-panel__header">{eyebrow && <span>{eyebrow}</span>}{title && <h2>{title}</h2>}</header>}
      {children}
    </section>
  );
}
