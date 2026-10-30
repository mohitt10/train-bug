// Thin fetch wrapper shared by all phases. Phases 3 and 4 should add their
// functions on top of apiRequest() instead of calling fetch() directly.

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'UNKNOWN', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export async function apiRequest(path, { method = 'GET', body } = {}) {
  const options = { method, headers: {}, credentials: 'same-origin' }
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(path, options)
  } catch {
    throw new ApiError('Cannot reach the server. Check that the backend is running.', {
      code: 'NETWORK_ERROR',
    })
  }

  if (response.status === 204) return null

  let payload = null
  try {
    payload = await response.json()
  } catch {
    // Non-JSON response; handled below.
  }

  if (!response.ok) {
    const err = payload?.error
    throw new ApiError(err?.message ?? `Request failed (${response.status}).`, {
      status: response.status,
      code: err?.code,
      details: err?.details,
    })
  }
  return payload?.data ?? null
}
