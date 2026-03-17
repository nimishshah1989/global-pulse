interface Props {
  message: string
  onRetry?: () => void
}

export default function ErrorAlert({ message, onRetry }: Props): JSX.Element {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-red-800">
          Failed to load data: {message}
        </span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="rounded-lg border border-red-300 bg-white px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-50"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  )
}
