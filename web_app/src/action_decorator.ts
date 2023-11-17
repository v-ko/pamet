// function mobxAction(key, descriptor) {
//     // dummy implementation
//     console.log('mobxAction', key, descriptor)
//     return descriptor;
// }

// function action(...args: any[]) {
//     // This function acts as a decorator factory when arguments are provided
//     // and as a decorator when no arguments are provided

//     function processMethod(descriptor, name, issuer) {
//         const originalMethod = descriptor.value; // Save the original method
//         // And add the issuer to the name
//         let funcName = `[${issuer}]${name}`;
//         descriptor.value = mobxAction(funcName, originalMethod);

//         return descriptor;
//     }

//     // Check if it's being used as a decorator (without arguments)
//     if (args.length === 3 && typeof args[0] === "function") {
//         const [target, key, descriptor] = args;
//         return processMethod(descriptor, key, 'user')
//     } else if (args.length === 1) {
//         // There's an options dict supplied, which holds the named parameters
//         const [options] = args;
//         let name: string | undefined = options.name;
//         let issuer = options.issuer || 'user';
//         return function (target, key, descriptor) {
//             name = name || key;
//             issuer = issuer || 'user';
//             return processMethod(descriptor, name, issuer);
//         }
//     }
// }


// class DummyClass {
//     @action(true)
//     dummy(test) {
//         console.log('dummy', test)
//     }

//     @action
//     dummy2(test) {
//         console.log('dummy', test)
//     }
// }
// let dummy = new DummyClass()
// dummy.dummy('test')
// dummy.dummy2('test')

export{}
