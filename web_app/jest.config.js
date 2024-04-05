/** @type {import('jest').Config} */
const config = {
    preset: "ts-jest",
    testEnvironment: "node",
    // resolver: "<rootDir>/jest-resolver.cjs",
    moduleNameMapper: {
        "\\.(scss|sass|css)$": "identity-obj-proxy",
        // "^fusion$": "<rootDir>/src/fusion",
    },
    // haste: {
    //     enableSymlinks: true,
    //   },
    silent: false,
    verbose: true,
    roots: ["<rootDir>/src"],
    moduleDirectories: ["node_modules", "src", "src/fusion"],
};

export default config;
