export default {
  preset: "ts-jest",
  testEnvironment: "node",
  moduleNameMapper: {
    "\\.(scss|sass|css)$": "identity-obj-proxy",
    "^fusion/(.*)$": "<rootDir>/../fusion/js-src/src/$1",  // Ad-hoc added because Jest didn't infer it from the tsconfig. May be removed later
  },
};
