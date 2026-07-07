import { render, screen } from '@testing-library/react'
import { App } from './App'

describe('App', () => {
  it('renders the application header', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'SRM Credit Engine' })).toBeInTheDocument()
  })
})
