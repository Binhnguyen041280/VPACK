# CRITICAL FRONTEND ARCHITECTURE CORRECTION

## 🚨 URGENT AGENT INSTRUCTION

### ACTIVE FRONTEND SYSTEM
- **LOCATION**: `/Users/annhu/vtrack_app/V_Track/frontend/`
- **FRAMEWORK**: Next.js 14+ with TypeScript
- **START COMMAND**: `npm run dev` (port 3000)
- **STRUCTURE**:
  - `frontend/app/` - Next.js App Router
  - `frontend/src/` - Components and utilities
  - `frontend/components/` - UI components
  - `frontend/public/` - Static assets

### ❌ DEPRECATED SYSTEM (DO NOT USE)
- **LOCATION**: `/Users/annhu/vtrack_app/V_Track/docs/FE/`
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

**Last Updated**: 2025-09-24 by Human Orchestrator
**Critical Priority**: All agents must read and follow this guidance