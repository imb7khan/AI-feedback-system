import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../App';

test('renders assignment feedback title', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /AI Assignment Feedback System/i })).toBeInTheDocument();
});
