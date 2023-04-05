export type Callable = (...args: any[]) => any;

let objectCounter = 0;

export function get_counted_id(obj) {
  if (typeof obj.__uniqueid === "undefined") {
    obj.__uniqueid = ++objectCounter;
  }
  return obj.__uniqueid;
}


export function get_new_id() {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let id = '';
  for (let i = 0; i < 8; i++) {
    const index = Math.floor(Math.random() * alphabet.length);
    id += alphabet.charAt(index);
  }
  return id;
}


export function current_time() {
  return new Date();
}
