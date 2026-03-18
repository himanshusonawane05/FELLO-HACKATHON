import type { TechnologySchema } from "@/types/intelligence";

interface TechStackGridProps {
  technologies: TechnologySchema[];
}

export default function TechStackGrid({ technologies }: TechStackGridProps): React.ReactElement {
  if (technologies.length === 0) {
    return (
      <div data-testid="tech-stack" className="rounded-xl border border-border bg-surface p-5">
        <h3 className="font-display font-bold text-white text-sm mb-2">Tech Stack</h3>
        <p className="text-muted text-xs font-mono">No technologies detected.</p>
      </div>
    );
  }

  return (
    <div data-testid="tech-stack" className="rounded-xl border border-border bg-surface p-5">
      <h3 className="font-display font-bold text-white text-sm mb-3">Tech Stack</h3>
      <div className="flex flex-wrap gap-2">
        {technologies.map((tech) => (
          <div
            key={tech.name}
            className="rounded-md border border-border bg-background px-3 py-1.5 flex flex-col"
          >
            <span className="text-white text-xs font-semibold">{tech.name}</span>
            <span className="text-muted text-[10px] font-mono">{tech.category}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
