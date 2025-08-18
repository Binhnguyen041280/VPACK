<?xml version="1.0" encoding="UTF-8"?>
<!--
  V_track Project Cleanup & Organization Command
  File: cleanup-organize.md
  Purpose: Comprehensive cleanup using _misc/ folder system
  Usage: /cleanup-organize $ARGUMENTS
-->

<cleanup-organize>
  <!-- COMMAND DESCRIPTION -->
  <description>
    Perform comprehensive file cleanup and organization for $ARGUMENTS directory.
    Creates standardized _misc/ folder structure and safely moves non-essential files.
  </description>

  <!-- EXECUTION STEPS -->
  <execution>
    
    <!-- STEP 1: INITIAL SETUP -->
    <step number="1" title="Setup _misc/ Structure">
      <objective>Create organized storage system for miscellaneous files</objective>
      
      <actions>
        <create-folder path="_misc/" description="Main miscellaneous storage folder"/>
        
        <create-subfolders>
          <subfolder name="backup" purpose="Store old versions and replaced code"/>
          <subfolder name="demo" purpose="Store demo files, prototypes, examples"/>
          <subfolder name="fix" purpose="Store temporary patches and hotfixes"/>
          <subfolder name="test" purpose="Store experimental and old test files"/>
          <subfolder name="docs" purpose="Store notes, specifications, drafts"/>
          <subfolder name="assets" purpose="Store unused images and media files"/>
        </create-subfolders>
        
        <create-readme path="_misc/README.md" content="Explain purpose of each subfolder"/>
      </actions>
    </step>

    <!-- STEP 2: FILE ANALYSIS -->
    <step number="2" title="Analyze and Classify Files">
      <objective>Identify and categorize files for organization</objective>
      
      <scan-directory target="main directory" include-subdirectories="true"/>
      
      <file-classifications>
        <category name="Unused Code">
          <file-types>
            <type>Unused imports and dependencies</type>
            <type>Commented out code blocks</type>
            <type>Dead/unreachable code</type>
          </file-types>
          <destination>_misc/backup/</destination>
        </category>
        
        <category name="Demo Content">
          <file-types>
            <type>Example files</type>
            <type>Prototype code</type>
            <type>Demo implementations</type>
          </file-types>
          <destination>_misc/demo/</destination>
        </category>
        
        <category name="Temporary Solutions">
          <file-types>
            <type>Quick fixes</type>
            <type>Workarounds</type>
            <type>Temporary patches</type>
          </file-types>
          <destination>_misc/fix/</destination>
        </category>
        
        <category name="Test Files">
          <file-types>
            <type>Experimental tests</type>
            <type>Old test files</type>
            <type>Test prototypes</type>
          </file-types>
          <destination>_misc/test/</destination>
        </category>
        
        <category name="Documentation">
          <file-types>
            <type>Draft documentation</type>
            <type>Personal notes</type>
            <type>Specification drafts</type>
          </file-types>
          <destination>_misc/docs/</destination>
        </category>
        
        <category name="Assets">
          <file-types>
            <type>Unused images</type>
            <type>Old media files</type>
            <type>Deprecated assets</type>
          </file-types>
          <destination>_misc/assets/</destination>
        </category>
      </file-classifications>
    </step>

    <!-- STEP 3: SAFE MIGRATION -->
    <step number="3" title="Safe File Migration">
      <objective>Move classified files safely without data loss</objective>
      
      <pre-migration>
        <user-reminder type="manual-backup">
          <message>IMPORTANT: Create git commit manually before cleanup</message>
          <command>git add . && git commit -m "Before cleanup-organize"</command>
          <wait-for-confirmation>true</wait-for-confirmation>
        </user-reminder>
      </pre-migration>
      
      <migration-process>
        <rule>MOVE files (never delete permanently)</rule>
        <rule>Preserve original folder structure within _misc/ if needed</rule>
        <rule>Log all file movements for potential rollback</rule>
        <rule>Request user confirmation for each major change</rule>
        
        <migration-steps>
          <migrate category="Unused Code" to="_misc/backup/" priority="high"/>
          <migrate category="Demo Content" to="_misc/demo/" priority="medium"/>
          <migrate category="Temporary Solutions" to="_misc/fix/" priority="medium"/>
          <migrate category="Test Files" to="_misc/test/" priority="low"/>
          <migrate category="Documentation" to="_misc/docs/" priority="low"/>
          <migrate category="Assets" to="_misc/assets/" priority="low"/>
        </migration-steps>
      </migration-process>
    </step>

    <!-- STEP 4: CLEANUP MAIN DIRECTORY -->
    <step number="4" title="Clean Main Directory">
      <objective>Organize remaining files in main directory</objective>
      
      <cleanup-actions>
        <remove-empty-folders description="Delete folders left empty after migration"/>
        <consolidate-duplicates description="Merge duplicate files if found"/>
        <organize-remaining description="Group remaining files by logical categories"/>
        <update-references description="Fix import paths if necessary"/>
      </cleanup-actions>
    </step>

    <!-- STEP 5: VERIFICATION -->
    <step number="5" title="Verify and Finalize">
      <objective>Ensure everything works and complete the process</objective>
      
      <verification>
        <test-build description="Verify project still builds successfully"/>
        <test-functionality description="Check that main features still work"/>
        <update-gitignore pattern="**/_misc/" description="Ignore all _misc folders"/>
        <generate-report description="Create summary of organized files"/>
      </verification>
      
      <finalization>
        <user-reminder type="manual-commit">
          <message>REMINDER: Commit organized result manually</message>
          <command>git add . && git commit -m "Organized: moved misc files to _misc/"</command>
        </user-reminder>
      </finalization>
    </step>

  </execution>

  <!-- SAFETY PRINCIPLES -->
  <safety-principles>
    <principle priority="critical">NEVER DELETE files permanently - always move to _misc/backup/</principle>
    <principle priority="high">ASK USER PERMISSION before any major file operations</principle>
    <principle priority="high">CREATE BACKUPS in _misc/backup/ for all changes</principle>
    <principle priority="medium">TEST IMMEDIATELY after each step to prevent errors</principle>
    <principle priority="medium">ENABLE EASY ROLLBACK through git history</principle>
  </safety-principles>

  <!-- USAGE EXAMPLES -->
  <usage-examples>
    <example>
      <command>/cleanup-organize .</command>
      <description>Organize current directory and all subdirectories</description>
    </example>
    <example>
      <command>/cleanup-organize src/components</command>
      <description>Only organize the components directory</description>
    </example>
    <example>
      <command>/cleanup-organize modules/technical</command>
      <description>Organize specific technical module</description>
    </example>
  </usage-examples>

  <!-- EXPECTED RESULTS -->
  <expected-results>
    <result>Clean main directory with only essential files</result>
    <result>Organized _misc/ folder with categorized miscellaneous files</result>
    <result>Updated .gitignore to exclude _misc/ folders</result>
    <result>Full git history preserved for easy rollback</result>
    <result>Project functionality remains intact</result>
  </expected-results>

</cleanup-organize>