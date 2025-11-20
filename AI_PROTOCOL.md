# AI AGENT PROTOCOL & RULES

This file defines the mandatory operating protocol for any AI agent (Antigravity, Claude, GPT, etc.) working on this project.

## 1. CORE PRINCIPLE: APPROVAL FIRST (QUY TẮC DUYỆT TRƯỚC)
- **PLAN & ASK:** Before editing any code, running any complex command, or modifying the system state, the AI MUST:
  1.  Analyze the problem.
  2.  Propose a detailed plan (which files to edit, what logic to change).
  3.  **Explicitly ask for user approval** (e.g., "Do you agree with this plan?", "Shall I proceed?").
- **NO AUTO-EXECUTION:** Do NOT call tools to edit code or run destructive commands in the same turn as the proposal. Wait for the user's "OK".

## 2. NO SURPRISES (KHÔNG BẤT NGỜ)
- Do not add unrequested features.
- Do not silently change business logic.
- Do not "fix" things that were not asked to be fixed unless critical and explicitly communicated.

## 3. CONTEXT AWARENESS (TÔN TRỌNG BỐI CẢNH)
- If the user states an action was taken (e.g., "I deleted the DB", "I restarted Docker"), treat this as the Source of Truth.
- Do not assume the state based on old logs if the user says otherwise.

## 4. LANGUAGE (NGÔN NGỮ)
- Respond in the same language the user is using (Vietnamese/English).
