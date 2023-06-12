import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './containers/app/App';
import './index.css';
import reportWebVitals from './reportWebVitals';

// See the work log!
// Otherwise the setup logic should be here, yes.


const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
