# V_Track Frontend Test Suite

Comprehensive test suite for V_Track Next.js frontend.

## Directory Structure

```
tests/
├── __tests__/              # Test files
│   ├── components/        # Component tests
│   ├── services/          # Service tests
│   ├── contexts/          # Context tests
│   ├── utils/             # Utility tests
│   └── integration/       # Integration tests
├── __mocks__/             # Mock modules
├── testUtils.tsx          # Custom render & helpers
└── README.md              # This file
```

## Running Tests

```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm test -- --coverage

# Specific test file
npm test LicenseActivationModal

# Update snapshots
npm test -- -u
```

## Writing Tests

### Component Test Example

```typescript
import { render, screen, fireEvent } from '../testUtils'
import MyComponent from '@/components/MyComponent'

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

### Service Test Example

```typescript
import * as PaymentService from '@/services/paymentService'

jest.mock('@/services/paymentService')

describe('PaymentService', () => {
  it('should fetch packages', async () => {
    const mockPackages = [{ id: '1', name: 'Basic' }]
    jest.spyOn(PaymentService, 'getPackages')
      .mockResolvedValue(mockPackages)

    const result = await PaymentService.getPackages()
    expect(result).toEqual(mockPackages)
  })
})
```

## Test Markers

- `describe()` - Test suite
- `it()` / `test()` - Individual test case
- `beforeEach()` - Setup before each test
- `afterEach()` - Cleanup after each test

## Coverage Goals

- Components: 55-60%
- Services: 70%+
- Contexts: 65%+
- Utils: 60%+
- Overall: 60%+
