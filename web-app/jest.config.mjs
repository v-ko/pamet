export default {
  preset: "ts-jest",
  testEnvironment: "node",
  moduleNameMapper: {
    "\\.(scss|sass|css)$": "identity-obj-proxy",
  },
  // transform: { did not work
  //   '^.+\\.(js|jsx|ts|tsx)$': 'babel-jest', // This line configures jest to use babel-jest for JavaScript and TypeScript files
  // },
};
