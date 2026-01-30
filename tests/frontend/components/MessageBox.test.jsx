// tests/frontend/components/MessageBox.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MessageBox from '@src/components/MessageBox'

describe('MessageBox', () => {
  // Happy cases - rendering
  it('should render error message by default', () => {
    render(<MessageBox message="Error occurred" />)
    expect(screen.getByText('Error occurred')).toBeInTheDocument()
  })

  it('should render success message when type is success', () => {
    render(<MessageBox type="success" message="Operation successful" />)
    expect(screen.getByText('Operation successful')).toBeInTheDocument()
  })

  it('should render info message when type is info', () => {
    render(<MessageBox type="info" message="Information message" />)
    expect(screen.getByText('Information message')).toBeInTheDocument()
  })

  it('should render children when message is not provided', () => {
    render(
      <MessageBox>
        <span>Child content</span>
      </MessageBox>
    )
    expect(screen.getByText('Child content')).toBeInTheDocument()
  })

  it('should prioritize message over children', () => {
    render(
      <MessageBox message="Message text">
        <span>Child content</span>
      </MessageBox>
    )
    expect(screen.getByText('Message text')).toBeInTheDocument()
    expect(screen.queryByText('Child content')).not.toBeInTheDocument()
  })

  // User interactions
  it('should call onClose when close button is clicked', async () => {
    const user = userEvent.setup()
    const handleClose = vi.fn()
    render(<MessageBox message="Test message" onClose={handleClose} />)
    
    const closeButton = screen.getByLabelText('Close')
    await user.click(closeButton)
    
    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('should not render close button when onClose is not provided', () => {
    render(<MessageBox message="Test message" />)
    expect(screen.queryByLabelText('Close')).not.toBeInTheDocument()
  })

  // Sad cases - edge cases
  it('should return null when neither message nor children are provided', () => {
    const { container } = render(<MessageBox />)
    expect(container.firstChild).toBeNull()
  })

  it('should return null when message is empty string', () => {
    const { container } = render(<MessageBox message="" />)
    expect(container.firstChild).toBeNull()
  })

  it('should handle empty children', () => {
    const { container } = render(<MessageBox>{null}</MessageBox>)
    expect(container.firstChild).toBeNull()
  })

  // Accessibility
  it('should have proper aria-label on close button', () => {
    render(<MessageBox message="Test" onClose={() => {}} />)
    const closeButton = screen.getByLabelText('Close')
    expect(closeButton).toBeInTheDocument()
  })

  // Multiple close clicks
  it('should call onClose multiple times when close button is clicked multiple times', async () => {
    const user = userEvent.setup()
    const handleClose = vi.fn()
    render(<MessageBox message="Test message" onClose={handleClose} />)
    
    const closeButton = screen.getByLabelText('Close')
    await user.click(closeButton)
    await user.click(closeButton)
    
    expect(handleClose).toHaveBeenCalledTimes(2)
  })
})

