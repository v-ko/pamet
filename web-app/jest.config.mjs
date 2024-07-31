export default {
  preset: "ts-jest",
  testEnvironment: "node",
  moduleNameMapper: {
    "\\.(scss|sass|css)$": "identity-obj-proxy",
  },
};
