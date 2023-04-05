
let LOG_LEVEL = 2;  // 0: info, 1: warning, 2: error

class Logger {
    name: string;

    constructor(name) {
        this.name = name;
    }
    info(...args) {
        if (LOG_LEVEL > 0) {
            return;
        }
        console.info(`[${this.name}]`, ...args);
    }
    warning(...args) {
        if (LOG_LEVEL > 1) {
            return;
        }
        console.warn(`[${this.name}]`, ...args);
    }
    error(...args) {
        console.error(`[${this.name}]`, ...args);
    }
}


export function get_logger(name) {
    return new Logger(name);
}
