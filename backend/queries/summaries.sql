-- name: InsertSummary :one
INSERT INTO summaries (url, title, summary, model)
VALUES ($1, $2, $3, $4)
RETURNING *;

-- name: GetSummaryByURL :one
SELECT * FROM summaries
WHERE url = $1
ORDER BY created_at DESC
LIMIT 1;

-- name: ListSummaries :many
SELECT * FROM summaries
ORDER BY created_at DESC
LIMIT 20;

-- name: DeleteSummary :exec
DELETE FROM summaries WHERE id = $1;
