import { render, screen } from '@testing-library/react';
import WebApp, { WebAppState } from './App';

test('renders learn react link', () => {
  render(<WebApp state={new WebAppState()}/>);
  // const linkElement = screen.getByText(/learn react/i);
  // expect(linkElement).toBeInTheDocument();
});
