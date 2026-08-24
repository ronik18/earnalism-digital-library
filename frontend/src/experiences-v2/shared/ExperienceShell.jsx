import "./experiences-v2.css";

export default function ExperienceShell({ children, className = "", labelledBy }) {
  return (
    <main className={`experience-v2 ${className}`.trim()} aria-labelledby={labelledBy}>
      {children}
    </main>
  );
}
