import { RpcClient } from './rpc-client.mjs';
import { SearchController } from './controller.mjs';
import { BoardView } from './view.mjs';

const view = new BoardView(document);
const controller = new SearchController(new RpcClient(), state => view.render(state));
const element = id => document.getElementById(id);
element('size').addEventListener('change', event => void controller.changeSize(Number(event.target.value)));
element('start').addEventListener('click', () => void controller.start(Number(element('size').value)));
element('restart').addEventListener('click', () => void controller.start(Number(element('size').value)));
element('reset').addEventListener('click', () => void controller.reset());
element('step').addEventListener('click', () => void controller.step());
element('play').addEventListener('click', () => void controller.playPause());
element('next-solution').addEventListener('click', () => void controller.nextSolution());
element('speed').addEventListener('input', event => {
  controller.setDelay(event.target.value);
  element('speed-value').textContent = `${controller.delay} ms / event`;
});
// Closing a tab is best effort. Inactivity expiration covers failed delivery.
window.addEventListener('pagehide', () => {
  if (controller.streamId) navigator.sendBeacon('/rpc', new Blob([JSON.stringify({
    jsonrpc: '2.0', method: 'queens.close', params: { stream_id: controller.streamId },
  })], { type: 'application/json' }));
});
