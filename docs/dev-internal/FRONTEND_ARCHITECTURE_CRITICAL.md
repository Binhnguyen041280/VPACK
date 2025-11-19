# CRITICAL FRONTEND ARCHITECTURE CORRECTION

## 🚨 URGENT AGENT INSTRUCTION

### ACTIVE FRONTEND SYSTEM
- **LOCATION**: `/Users/annhu/vtrack_app/ePACK/frontend/`
- **FRAMEWORK**: Next.js 15.1.6 with TypeScript 4.9.5
- **REACT VERSION**: React 19.2.0 (Stable) - Upgraded 2025-10-07
- **START COMMAND**: `npm run dev` (port 3000)
- **STRUCTURE**:
  - `frontend/app/` - Next.js App Router
  - `frontend/src/` - Components and utilities
  - `frontend/components/` - UI components
  - `frontend/public/` - Static assets

### ❌ DEPRECATED SYSTEM (DO NOT USE)
- **LOCATION**: `/Users/annhu/vtrack_app/ePACK/docs/FE/`
- **STATUS**: Legacy React app - INACTIVE
- **WARNING**: Any work on docs/FE/ is wasted effort

## 🤖 FOR ALL AGENTS

### MANDATORY RULES
1. **ALWAYS work with `/frontend/` directory**
2. **NEVER work with `/docs/FE/` directory**
3. **Verify correct path before any modifications**
4. **Report architecture questions to Human Orchestrator**

### BACKEND INTEGRATION
- Backend: Flask on port 8080
- Frontend: Next.js on port 3000
- API calls: http://localhost:8080/program, /health, etc.

### HUEY MIGRATION IMPACT
- Program cards UI must be fixed in `/frontend/` for migration testing
- Agent C fixed wrong system (docs/FE) - needs correction
- All future agents must target correct frontend

## 📋 VALIDATION CHECKLIST
- [ ] Agent working in `/frontend/` directory?
- [ ] Using Next.js components and TypeScript?
- [ ] Testing against correct backend endpoints?
- [ ] Confirming program cards functionality?

**Last Updated**: 2025-10-07 - React 19 Stable Upgrade
**Critical Priority**: All agents must read and follow this guidance

## 📦 RECENT UPDATES (2025-10-07)

### React 19 Stable Migration
- **Upgraded**: React 19.0.0-rc.1 → React 19.2.0 (stable)
- **Status**: Production-ready, fully tested
- **TypeScript**: Fixed 10+ strict type checking errors for React 19 compatibility
- **Key Changes**:
  - Box component children must use Fragment wrapper for multiple elements
  - Stricter type checking for props (undefined handling required)
  - Image component alt prop must handle undefined values
  - Object spread order matters for duplicate properties

### Configuration Cleanup
- **Removed**: pnpm-specific configs from `.npmrc`
  - ❌ `auto-install-peers=true` (deprecated)
  - ❌ `strict-peer-dependencies=false` (deprecated)
- **Kept**: `legacy-peer-deps=true` (required for React 19)

### Compatibility Notes
- ⚠️ Chakra UI 2.8.2 not fully optimized for React 19
- ✅ All core features working correctly
- ✅ Dev server and production builds functional
- 📝 Future consideration: Upgrade to Chakra UI v3 for full React 19 support