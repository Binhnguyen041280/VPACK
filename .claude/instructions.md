# V_Track UI Development Standards

## 🚨 CRITICAL: Desktop-Only Web Application

**TARGET PLATFORM: PC & Laptop ONLY. NO Mobile Support Required.**

- ✅ Optimize for desktop screens (1280px+ width)
- ✅ Focus on laptop/desktop user experience
- ❌ NO mobile responsive design needed
- ❌ NO tablet optimization required
- ❌ NO touch interface considerations

## 🚨 CRITICAL: ChatGPT-Style Layout Pattern

**ALWAYS USE ChatGPT-style container pattern for ALL new UI layouts. NO EXCEPTIONS.**

### ✅ Standard Pattern (MANDATORY)

```tsx
// STANDARD TEMPLATE - Use this for all new pages
<Flex
  position="fixed"
  bottom="0"
  left={toggleSidebar ? "95px" : "288px"}
  right="0"
  justifyContent="center"
  transition="left 0.2s linear"
  zIndex={10}
  bg={mainBg}
  h="54px"
>
  <Flex
    maxW="1000px"
    px="20px"
    alignItems="center"
    w="100%"
  >
    {/* Your content here */}
  </Flex>
</Flex>
```

### 📖 Reference Implementation
- **File**: `/frontend/app/trace/page.tsx`
- **Lines**: Chat input container (around line 340-370)
- **Status**: ✅ Production-ready ChatGPT-style implementation

### ❌ NEVER Use These Anti-Patterns
- Complex `calc()` positioning: `left={'calc(95px + (100vw - 95px - 800px) / 2)'}`
- Fixed width containers without centering
- Viewport-based calculations
- Offset-based alignment approaches

### 🎯 Why ChatGPT-Style?
- ✅ Cross-zoom compatibility (75%-150%) on desktop
- ✅ Perfect content alignment for PC/laptop screens
- ✅ Simple, maintainable code
- ✅ Professional desktop user experience
- ✅ Consistent across desktop browsers

### 🔧 Technical Details
- **Container**: Full-width fixed positioning with sidebar awareness
- **Content**: Centered with `maxW="1000px"` constraint
- **Padding**: Consistent `px="20px"` matching main content areas
- **Desktop-Optimized**: Works seamlessly across desktop zoom levels (75%-150%)

### 📝 Implementation Checklist
When creating new UI layouts:
1. ✅ Use container-based positioning
2. ✅ Center content with `justifyContent="center"`
3. ✅ Set `maxW="1000px"` for content area
4. ✅ Add `px="20px"` padding
5. ✅ Include sidebar state awareness
6. ✅ Test across desktop zoom levels (75%-150%)
7. ✅ Ensure minimum width support (1280px+)
8. ✅ Optimize for mouse/keyboard interaction

## 🏗️ Project Architecture

### UI Library Stack
- **Chakra UI**: Primary component system
- **Horizon AI Template Pro**: Professional template base
- **React Icons**: Icon system
- **Framer Motion**: Animations

### File Structure
- `/frontend/app/`: Next.js app router pages
- `/frontend/src/components/`: Reusable UI components
- `/frontend/src/components/trace/`: Trace-specific components

### Sidebar Integration
- Use `toggleSidebar` context for responsive behavior
- Collapsed: `95px` left offset
- Expanded: `288px` left offset
- Always include smooth transition: `transition="left 0.2s linear"`

## 🎨 Design System Notes

### Color System
- Use theme-aware colors from Chakra UI
- `mainBg`, `chatBorderColor`, `chatTextColor` for consistency
- Follow existing color patterns in trace page

### Typography
- `fontSize="sm"` for input fields
- `fontWeight="500"` for user inputs
- Consistent with existing design system

### Spacing
- `h="54px"` for input containers
- `borderRadius="full"` for modern appearance
- `px="20px"` horizontal padding standard

## 🚀 Quick Start Template

Copy this boilerplate for new pages:

```tsx
'use client';
import { Flex, Box, Input, Button } from '@chakra-ui/react';
import { useSidebar } from '../../../contexts/SidebarContext';

export default function NewPage() {
  const { toggleSidebar } = useSidebar();

  return (
    <>
      {/* Main content area */}
      <Flex
        direction="column"
        mx="auto"
        maxW="1000px"
        px="20px"
        pt="80px"
        pb="160px"
      >
        {/* Your page content */}
      </Flex>

      {/* Chat input - ChatGPT style */}
      <Flex
        position="fixed"
        bottom="0"
        left={toggleSidebar ? "95px" : "288px"}
        right="0"
        justifyContent="center"
        transition="left 0.2s linear"
        zIndex={10}
        bg={mainBg}
        h="54px"
      >
        <Flex maxW="1000px" px="20px" alignItems="center" w="100%">
          {/* Your input/controls */}
        </Flex>
      </Flex>
    </>
  );
}
```

---

**Last Updated**: 2025-09-20
**Status**: Production Standard - Implemented in trace page
**Next Action**: Apply to all new UI developments