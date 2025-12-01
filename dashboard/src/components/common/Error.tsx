export const ErrorState = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="rounded-xl border border-danger/40 bg-danger/5 p-4 text-danger">
    <p className="font-semibold">{message}</p>
    {onRetry && (
      <button onClick={onRetry} className="mt-2 text-sm underline">
        Try again
      </button>
    )}
  </div>
);
