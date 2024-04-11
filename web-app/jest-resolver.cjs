// Workaround for Jest to preserve symlinks
const resolve = require("resolve");
console.log("resolve", resolve);
module.exports = (request, options) => {
  try {
    return resolve.sync(request, {
      ...options,
      preserveSymlinks: true,
    });
  } catch (e) {
    throw Error(`Cannot resolve module '${request}'`);
  }
};
