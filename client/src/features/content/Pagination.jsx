export function Pagination({ nextCursor, onLoadMore, isLoading }) {
  if (!nextCursor) {
    return (
      <div className="pagination-end">
        <p>— End of feed —</p>
      </div>
    );
  }

  return (
    <div className="pagination-container">
      <button
        type="button"
        className="btn btn-secondary btn-pagination"
        onClick={onLoadMore}
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <span className="spinner-inline" aria-hidden="true" />
            Loading more posts…
          </>
        ) : (
          'Load more posts ↓'
        )}
      </button>
    </div>
  );
}
