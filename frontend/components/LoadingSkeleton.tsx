interface LoadingSkeletonProps {
  count?: number;
}

export default function LoadingSkeleton({ count = 1 }: LoadingSkeletonProps): React.ReactElement {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-24 rounded-lg bg-surface border border-border animate-pulse"
        />
      ))}
    </div>
  );
}
