// Transport only. It never opens or consumes a stream on its own.
export class RpcClient {
  constructor(fetcher = globalThis.fetch.bind(globalThis), timeout = 15000) {
    this.fetcher = fetcher;
    this.timeout = timeout;
    this.id = 0;
  }

  async call(method, params) {
    const id = ++this.id;
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), this.timeout);
    try {
      const response = await this.fetcher('/rpc', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id, method, params }), signal: abort.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}. Check that the local server is running.`);
      const reply = await response.json();
      if (!reply || reply.jsonrpc !== '2.0' || reply.id !== id) {
        throw new Error('The server returned an invalid RPC response.');
      }
      if (reply.error) {
        const error = new Error(`RPC ${reply.error.code}: ${reply.error.message}`);
        error.code = reply.error.code;
        throw error;
      }
      if (!Object.hasOwn(reply, 'result')) throw new Error('The RPC result is missing.');
      return reply.result;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The request timed out. Restart the search to try again.');
      if (error instanceof TypeError) throw new Error('Cannot reach the server. Check the connection and restart the search.');
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }
}
