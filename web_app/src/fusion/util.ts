export type Callable = (...args: any[]) => any;

let objectCounter = 0;
let _fakeTime: Date | null = null;  // For testing purposes

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

export function currentTime(): Date {
  if (_fakeTime) {
    return _fakeTime;
  }

  return new Date();
}

export function timestamp(dt: Date, microseconds: boolean = false): string {
  if (microseconds) {
    return dt.toISOString();
  } else {
    return dt.toISOString().split('.')[0] + 'Z';
  }
}

export function degreesToRadians(degrees: number) {
  return degrees * (Math.PI / 180);
}
