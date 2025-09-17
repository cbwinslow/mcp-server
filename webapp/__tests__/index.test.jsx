import { render, screen } from '@testing-library/react';
import Home from '../pages/index';

test('renders dashboard heading', () => {
  render(<Home />);
  expect(screen.getByText(/Status/i)).toBeInTheDocument();
});

