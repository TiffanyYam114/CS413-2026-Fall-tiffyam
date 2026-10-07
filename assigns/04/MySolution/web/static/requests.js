/* Bound both the HTTP request and reading its JSON response. */
export class ConnectionError extends Error {}
export const REQUEST_TIMEOUT_MS = 5000;

export async function requestJSON(url, options = {}) {
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), REQUEST_TIMEOUT_MS);
    try {
        const response = await fetch(url, {
            ...options, signal: abort.signal, cache: "no-store",
            headers: {Accept: "application/json", ...options.headers},
        });
        const payload = await response.json();
        if (!payload.state || !Number.isInteger(payload.state.version)) {
            throw new Error("The server did not return current source state.");
        }
        return {response, payload};
    } catch (error) {
        throw new ConnectionError(abort.signal.aborted ?
            "Request timed out. Checking the current source state…" :
            "Could not read the server response. Checking the current source state…");
    } finally {
        clearTimeout(timer);
    }
}
