export const Loading = ({ label = 'Loading...' }: { label?: string }) => (
  <div className="flex items-center gap-2 text-slate-500">
    <span className="h-3 w-3 animate-ping rounded-full bg-primary" />
    <p>{label}</p>
  </div>
);
