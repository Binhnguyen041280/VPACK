# V_Track - Video Processing & Analysis Platform

## 🚨 UI Development Standards

**TARGET PLATFORM: Desktop/Laptop ONLY (PC & Laptop - NO Mobile)**

**CRITICAL: Always use ChatGPT-style layout pattern for new pages.**

📖 **Full Documentation**: See `.claude/instructions.md` for complete UI guidelines

### Quick Reference
```tsx
// Standard pattern for ALL new UI layouts
<Flex position="fixed" bottom="0" left={toggleSidebar ? "95px" : "288px"} right="0" justifyContent="center">
  <Flex maxW="1000px" px="20px">
    {/* Content */}
  </Flex>
</Flex>
```

**Reference Implementation**: `/frontend/app/trace/page.tsx`

---

## Project Overview

V_Track is a comprehensive video processing and analysis platform built with:

- **Frontend**: Next.js 15 + Chakra UI + TypeScript
- **Backend**: Python Flask + SQLite
- **UI**: Horizon AI Template Pro with ChatGPT-style layouts

## Tech Stack

### Frontend
- Next.js 15.1.6 (App Router)
- React 19.0.0-rc.1
- Chakra UI 2.8.2
- TypeScript 4.9.5
- Framer Motion for animations

### Backend
- Python Flask
- SQLite database
- Google Drive API integration
- Cloud Functions support

## Project Structure

```
V_Track/
├── .claude/                    # Claude AI development standards
│   └── instructions.md         # UI guidelines and patterns
├── frontend/                   # Next.js frontend application
│   ├── app/                    # App router pages
│   │   ├── page.tsx           # Main chat page (2 layout modes)
│   │   └── trace/             # Trace page (ChatGPT-style reference)
│   └── src/                   # Components and utilities
│       └── components/        # Reusable UI components
├── backend/                   # Python Flask backend
│   ├── database/             # SQLite database
│   └── modules/              # Backend modules
└── README.md                 # This file
```

## Development Guidelines

### UI Development
1. **Always** reference `.claude/instructions.md` for layout patterns
2. Use ChatGPT-style container positioning for new pages
3. Follow Chakra UI design system conventions
4. Maintain responsive design across all zoom levels

### Code Standards
- TypeScript for type safety
- Component-based architecture
- Responsive design first
- Professional alignment and spacing

## Getting Started

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Backend Development
```bash
cd backend
# Setup Python environment and dependencies
# Start Flask server on port 8080
```

## Key Features

- **Trace Page**: Real-time tracking code analysis with ChatGPT-style UI
- **Main Page**: Dual-layout chat interface with configuration panels
- **Video Processing**: Advanced video analysis and ROI detection
- **Cloud Integration**: Google Drive API for video source management

## Development Status

- ✅ ChatGPT-style layout pattern established
- ✅ Trace page implementation complete
- ✅ Real API integration functional
- ✅ Responsive design across zoom levels

---

**Last Updated**: 2025-09-20
**Current Version**: 3.0.0