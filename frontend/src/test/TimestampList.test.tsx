import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TimestampList from '../components/TimestampList'
import type { TimestampRef } from '../types'

const timestamps: TimestampRef[] = [
  { start: 0, end: 5, text: 'Hello world', relevance_score: 1.0 },
  { start: 65, end: 75, text: 'Python programming', relevance_score: 0.8 },
]

describe('TimestampList', () => {
  it('renders nothing when timestamps empty', () => {
    const { container } = render(<TimestampList timestamps={[]} onPlay={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders timestamps', () => {
    render(<TimestampList timestamps={timestamps} onPlay={vi.fn()} />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
    expect(screen.getByText('Python programming')).toBeInTheDocument()
  })

  it('formats time correctly — 0:00 for start=0', () => {
    render(<TimestampList timestamps={timestamps} onPlay={vi.fn()} />)
    expect(screen.getByText(/0:00/)).toBeInTheDocument()
  })

  it('formats time correctly — 1:05 for start=65', () => {
    render(<TimestampList timestamps={timestamps} onPlay={vi.fn()} />)
    expect(screen.getByText(/1:05/)).toBeInTheDocument()
  })

  it('calls onPlay with correct timestamp on button click', () => {
    const onPlay = vi.fn()
    render(<TimestampList timestamps={timestamps} onPlay={onPlay} />)
    const buttons = screen.getAllByRole('button')
    fireEvent.click(buttons[0])
    expect(onPlay).toHaveBeenCalledWith(0)
    fireEvent.click(buttons[1])
    expect(onPlay).toHaveBeenCalledWith(65)
  })

  it('shows "Relevant timestamps" header', () => {
    render(<TimestampList timestamps={timestamps} onPlay={vi.fn()} />)
    expect(screen.getByText('Relevant timestamps')).toBeInTheDocument()
  })
})
