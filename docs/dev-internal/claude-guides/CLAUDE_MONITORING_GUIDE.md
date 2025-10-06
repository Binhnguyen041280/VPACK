# CLAUDE MONITORING GUIDE - How to Track & Control Claude CLI

## 🎯 **PROMPT TEMPLATES để kiểm soát Claude**

### 1. **Force Decision Transparency**
```
Before you do anything, explain:
1. What approach you're choosing (tools/subagent/custom agent)
2. Why you chose this approach
3. What alternatives you considered

Then proceed with the task.
```

### 2. **Escalation Monitoring**
```
If you need to escalate from your initial choice:
1. Stop and explain what you discovered
2. Tell me why the initial approach wasn't sufficient
3. Get my approval before escalating

Then continue.
```

### 3. **Context Management Check**
```
Before starting any complex task:
1. Check if you need to /clear context
2. Tell me if this task would benefit from parallel agents
3. Estimate the complexity level (simple/medium/complex)

Then proceed.
```

### 4. **Best Practice Compliance**
```
Apply 2025 best practices:
1. Use parallel processing for 3+ component tasks
2. Prefer specialized agents over general ones
3. Clear context every 10-15 exchanges
4. Use Plan Mode for complex research

Report your choices.
```

## 📊 **MONITORING CHECKLIST for Users**

### **✅ Claude Decision Quality Check**

#### **Quick Decision (30 seconds)**
- [ ] Did Claude analyze the task before choosing tools?
- [ ] Did Claude explain WHY they chose this approach?
- [ ] Did Claude consider alternatives?

#### **Efficiency Check (During task)**
- [ ] Is Claude using the right-sized tool? (no "dao mổ trâu giết gà")
- [ ] Is Claude escalating intelligently when stuck?
- [ ] Is Claude avoiding unnecessary complexity?

#### **Best Practice Compliance**
- [ ] For 3+ step tasks: Did Claude consider parallel agents?
- [ ] For V_Track specific: Did Claude use domain specialists?
- [ ] For research: Did Claude use Plan Mode or subagents?

### **🚨 RED FLAGS - When Claude is doing it WRONG**

1. **Using @tech-lead-orchestrator for simple file reads**
2. **Using Read tool for complex system analysis**
3. **Not explaining decision rationale**
4. **Escalating without attempting simpler approaches first**
5. **Not using parallel processing for obvious multi-component tasks**

## 🎮 **CONTROL COMMANDS for Users**

### **Immediate Control**
```bash
# Stop and reconsider approach
"Stop. Explain your approach choice and try a different method."

# Force specific tool
"Use only Read/Edit tools for this task"
"Use subagent for this research"
"Use @backend-developer for this V_Track issue"

# Request transparency
"Show me your decision process step by step"
```

### **Workflow Overrides**
```bash
# Force parallel processing
"Do this using parallel agents"

# Force escalation
"This is more complex than you think. Use a specialist."

# Force simplification
"This is simpler than you're making it. Use basic tools."
```

### **Context Management**
```bash
# Clear and restart
"/clear - start fresh with this task"

# Plan mode first
"Use Plan Mode to analyze this before executing"

# Specialized routing
"Route this to the most appropriate specialist agent"
```

## 📈 **PERFORMANCE TRACKING**

### **Daily Check Questions**
1. **Efficiency**: Did Claude choose right-sized tools today?
2. **Intelligence**: Did Claude adapt when initial approach failed?
3. **Speed**: Did Claude avoid unnecessary complexity?
4. **Quality**: Did Claude use domain experts for V_Track tasks?

### **Weekly Review**
- Count how often Claude escalated appropriately
- Note patterns in decision quality
- Track time saved vs. time wasted on wrong approaches

### **Success Metrics**
- **High Success**: Claude explains choices, uses right tools, escalates smartly
- **Medium Success**: Claude gets results but uses wrong-sized tools
- **Low Success**: Claude uses "dao mổ trâu giết gà" frequently

## 🔧 **TROUBLESHOOTING CLAUDE BEHAVIOR**

### **If Claude is too simplistic:**
```
"Consider more powerful tools. This task is more complex than you think."
```

### **If Claude is overcomplicating:**
```
"Use simpler tools. This task doesn't need heavy artillery."
```

### **If Claude isn't explaining decisions:**
```
"Before proceeding, explain your tool selection rationale."
```

### **If Claude ignores best practices:**
```
"Apply 2025 best practices: [specify which ones]"
```

## 🎯 **QUICK REFERENCE CARD**

| User Wants | Say This | Expect Claude To |
|------------|----------|------------------|
| **Transparency** | "Explain your approach first" | Show decision process |
| **Right-sizing** | "Choose appropriate tool complexity" | Match tool to task |
| **Efficiency** | "Start simple, escalate if needed" | Progressive enhancement |
| **Parallel work** | "Use parallel agents for this" | Multiple concurrent agents |
| **Specialization** | "Use domain expert for this" | @specialist agents |

---
**GOAL**: Keep Claude efficient but powerful, transparent but decisive!