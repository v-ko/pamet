import { main_loop } from "./loop"
import { Callable } from "./util"

// let line_spacing_in_pixels = 20
let _reproducible_ids: boolean = false
// let _main_loop_exception_handler: Callable | null = null


// def call_delayed(callback: Callable,
//                  delay: float = 0,
//                  args: list = None,
//                  kwargs: dict = None):
//     """Call a function with a delay on the main loop.

//     Args:
//         callback (Callable): The callable to be invoked
//         delay (float, optional): The delay in seconds. Defaults to 0.
//         args (list, optional): A list with the arguments. Defaults to None.
//         kwargs (dict, optional): A dictionary with the keyword arguments.
//             Defaults to None.
//     """
//     args = args or []
//     kwargs = kwargs or {}

//     if not callback:
//         raise Exception('Callback cannot be None')

//     main_loop().call_delayed(callback, delay, args, kwargs)


export function call_delayed(callback: Callable,
                             delay: number = 0,
                             ...args) {
    if (!callback) {
        throw new Error('Callback missing')
    }

    main_loop().call_delayed(callback, delay, args)
}

// # ----------------Various---------------------
// def set_reproducible_ids(enabled: bool):
//     """When testing - use non-random ids"""
//     global _reproducible_ids
//     if enabled:
//         random.seed(0)
//         _reproducible_ids = True
//     else:
//         random.seed(time.time())
//         _reproducible_ids = False

export function set_reproducible_ids(enabled: boolean) {
    _reproducible_ids = enabled
}


export function reproducible_ids() {
    return _reproducible_ids
}

// def reproducible_ids():
//     return _reproducible_ids


// def main_loop_exception_handler(exception: Exception):
//     """Handle an exception raised in the main loop.

//     Args:
//         exception (Exception): The exception to handle.
//     """
//     if _main_loop_exception_handler:
//         _main_loop_exception_handler(exception)
//     else:
//         raise exception


// def set_main_loop_exception_handler(handler: Callable):
//     """Set a handler for exceptions raised in the main loop.

//     Args:
//         handler (Callable): A callable that takes an exception as argument.
//     """
//     global _main_loop_exception_handler
//     _main_loop_exception_handler = handler
