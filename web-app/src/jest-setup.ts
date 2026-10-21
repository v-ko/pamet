// jsdom lacks TextEncoder, which browsers and Node have
import { TextEncoder } from 'util';

if (typeof globalThis.TextEncoder === 'undefined') {
  Object.assign(globalThis, { TextEncoder });
}
