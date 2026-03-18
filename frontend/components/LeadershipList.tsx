import type { LeaderSchema } from "@/types/intelligence";

interface LeadershipListProps {
  leaders: LeaderSchema[];
}

export default function LeadershipList({ leaders }: LeadershipListProps): React.ReactElement {
  return (
    <div data-testid="leadership-list" className="rounded-xl border border-border bg-surface p-5">
      <h3 className="font-display font-bold text-white text-sm mb-3">Leadership</h3>
      {leaders.length === 0 ? (
        <p className="text-muted text-xs font-mono">No leaders discovered.</p>
      ) : (
        <ul className="space-y-3">
          {leaders.map((leader, idx) => (
            <li key={idx} className="flex items-start justify-between gap-4">
              <div>
                <span className="text-white text-sm font-semibold">{leader.name}</span>
                <span className="text-muted text-xs font-mono block">{leader.title}</span>
                {leader.department && (
                  <span className="text-muted text-[10px] font-mono">{leader.department}</span>
                )}
              </div>
              {leader.linkedin_url && (
                <a
                  href={leader.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent text-xs font-mono hover:underline shrink-0"
                >
                  LinkedIn ↗
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
