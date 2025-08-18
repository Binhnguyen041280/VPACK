<?xml version="1.0" encoding="UTF-8"?>
<!--
  V_track Project Context Preparation Command
  File: prepare-context.md
  Purpose: Create optimized context files for Claude chat sessions
  Usage: /prepare-context $ARGUMENTS
-->

<prepare-context>
  <description>
    Generate optimized context file for feature: $ARGUMENTS
    Creates chat-ready context with accurate content, proper size, clear naming
    Output location: /Users/annhu/vtrack_app/V_Track/docs
  </description>

  <execution>
    
    <!-- STEP 1: INTELLIGENT CACHE CHECK -->
    <step number="1" title="Smart Cache and Feature Resolution">
      <objective>Check cache validity and identify feature efficiently</objective>
      
      <cache-check>
        <context-cache>
          <location>.claude/cache/generated-contexts/</location>
          <check-existing>Look for existing context file for $ARGUMENTS</check-existing>
          <validate-freshness>
            <project-hash>Compare current project state with cached hash</project-hash>
            <file-timestamps>Check if source files modified since cache</file-timestamps>
            <cache-age>Context cache valid for 3 days</cache-age>
          </validate-freshness>
        </context-cache>
        
        <feature-catalog-check>
          <location>.claude/cache/features-catalog.json</location>
          <auto-refresh>If missing or stale, run /list-features automatically</auto-refresh>
          <background-update>Update catalog without user intervention</background-update>
        </feature-catalog-check>
        
        <cache-decision>
          <use-cache-if>All cache valid and no source file changes</use-cache-if>
          <partial-update-if>Feature catalog valid but context stale</partial-update-if>
          <full-rebuild-if>Feature catalog missing or major project changes</full-rebuild-if>
        </cache-decision>
      </cache-check>

      <feature-resolution>
        <load-catalog>
          <source>.claude/cache/features-catalog.json</source>
          <auto-generate>Run /list-features if catalog missing</auto-generate>
          <silent-mode>Don't show feature discovery progress unless requested</silent-mode>
        </load-catalog>
        
        <smart-matching>
          <exact-match>Direct feature name match from catalog</exact-match>
          <fuzzy-search>Match $ARGUMENTS against feature keywords</fuzzy-search>
          <interactive-select>Show options only if multiple strong matches</interactive-select>
          <auto-select>Use best match if confidence > 80%</auto-select>
        </smart-matching>
      </feature-resolution>
    </step>

    <!-- STEP 2: INTELLIGENT FILE COLLECTION -->
    <step number="2" title="Collect Essential Files">
      <objective>Gather only essential files with accurate relationships</objective>
      
      <file-collection-strategy>
        <use-feature-analysis>
          <source>Use /feature-files results or run analysis</source>
          <priority-files>
            <critical-files weight="150">app.py, main.py, __init__.py (entry points)</critical-files>
            <database-files weight="140">database/, models.py, migrations/, db config</database-files>
            <core-files weight="100">Main implementation files</core-files>
            <interface-files weight="80">Types, interfaces, contracts</interface-files>
            <config-files weight="60">Routes, API endpoints, schemas</config-files>
            <test-files weight="40">Key test files for understanding</test-files>
            <supporting-files weight="20">Only if directly referenced</supporting-files>
          </priority-files>
        </use-feature-analysis>
        
        <size-optimization>
          <max-total-size>150KB (roughly 50k tokens)</max-total-size>
          <per-file-limit>15KB per file</per-file-limit>
          <priority-cutoff>Include by priority until size limit</priority-cutoff>
        </size-optimization>
        
        <dependency-analysis>
          <critical-dependencies>Include files that define interfaces used by feature</critical-dependencies>
          <backend-entry-points>Always include app.py, main.py if feature has backend components</backend-entry-points>
          <database-layer>Always include database models, config, and related migrations</database-layer>
          <exclude-common>Skip common utilities, lodash, etc.</exclude-common>
          <include-types>Always include TypeScript type definitions</include-types>
          <path-resolution>Resolve all import/export paths to absolute file system paths</path-resolution>
        </dependency-analysis>
      </file-collection-strategy>
    </step>

    <!-- STEP 3: CONTENT OPTIMIZATION -->
    <step number="3" title="Optimize File Content">
      <objective>Extract essential code while maintaining readability</objective>
      
      <content-processing>
        <code-extraction>
          <preserve-structure>Keep function signatures and class definitions</preserve-structure>
          <remove-noise>
            <target>Remove long comment blocks (keep brief explanations)</target>
            <target>Remove console.log and debug statements</target>
            <target>Remove extensive test data and mocks</target>
            <target>Compress whitespace but maintain readability</target>
          </remove-noise>
          <smart-truncation>
            <method>If function too long, keep signature + first few lines + "..."</method>
            <method>For large objects, show structure with key properties</method>
            <method>For arrays with many items, show first few + length indicator</method>
          </smart-truncation>
        </code-extraction>
        
        <context-enhancement>
          <add-file-headers>Include full absolute path and relative path for each file section</add-file-headers>
          <path-format>
            <absolute>/Users/annhu/vtrack_app/V_Track/path/to/file.ext</absolute>
            <relative>./path/to/file.ext (from project root)</relative>
            <comment-in-code># File: /Users/annhu/vtrack_app/V_Track/path/to/file.ext</comment-in-code>
          </path-format>
          <critical-files>
            <app-py>Always include app.py with full context if feature touches backend</app-py>
            <database>Always include relevant database files (models.py, config.py, migrations)</database>
            <entry-points>Include main entry points and initialization files</entry-points>
          </critical-files>
          <relationship-notes>Add brief notes about file relationships with path references</relationship-notes>
          <key-exports>Highlight main exports/functions for each file</key-exports>
        </context-enhancement>
      </content-processing>
    </step>

    <!-- STEP 4: INTELLIGENT FILE NAMING -->
    <step number="4" title="Generate Clear File Names">
      <objective>Create descriptive, searchable file names</objective>
      
      <naming-strategy>
        <timestamp>YYYY-MM-DD format for chronological sorting</timestamp>
        <feature-name>Clear, kebab-case feature identifier</feature-name>
        <scope-indicator>Brief scope description</scope-indicator>
        <version-suffix>Increment if file exists</version-suffix>
        
        <naming-pattern>
          <format>{date}-context-{feature-name}-{scope}.md</format>
          <examples>
            <example>2025-01-15-context-user-authentication-full.md</example>
            <example>2025-01-15-context-payment-processing-core.md</example>
            <example>2025-01-15-context-dashboard-analytics-frontend.md</example>
          </examples>
        </naming-pattern>
        
        <scope-types>
          <full>Complete feature context (all related files)</full>
          <core>Only core implementation files</core>
          <frontend>Only UI/frontend files</frontend>
          <backend>Only API/backend files</backend>
          <config>Only configuration and setup files</config>
        </scope-types>
      </naming-strategy>
    </step>

    <!-- STEP 5: CONTEXT FILE GENERATION -->
    <step number="5" title="Generate Context File">
      <objective>Create optimized context file for Claude consumption</objective>
      
      <file-structure>
        <header-section>
          <title># V_track Context: {Feature Name}</title>
          <metadata>
            ```
            Generated: {timestamp}
            Feature: {feature_name}
            Scope: {scope_type}
            Files: {file_count}
            Total Size: {size_kb}KB
            ```
          </metadata>
          <purpose>Brief description of the feature and context purpose</purpose>
          <key-components>List of main components/files included</key-components>
        </header-section>
        
        <summary-section>
          <architecture-overview>High-level architecture of the feature</architecture-overview>
          <data-flow>How data flows through the feature</data-flow>
          <key-functions>Main functions and their purposes</key-functions>
          <external-dependencies>Important external dependencies</external-dependencies>
        </summary-section>
        
        <files-section>
          <file-organization>
            ```markdown
            ## 🔧 Core Implementation
            
            ### File: src/auth/login.js
            **Path**: `/Users/annhu/vtrack_app/V_Track/src/auth/login.js`
            **Purpose**: Main login logic and authentication flow
            
            ```javascript
            // File: /Users/annhu/vtrack_app/V_Track/src/auth/login.js
            // Key exports: loginUser, validateCredentials
            export const loginUser = async (credentials) => {
              // Implementation here...
            }
            ```
            
            ### File: app.py  
            **Path**: `/Users/annhu/vtrack_app/V_Track/app.py`
            **Purpose**: Main Flask/FastAPI application entry point
            
            ```python
            # File: /Users/annhu/vtrack_app/V_Track/app.py
            # Main application setup and routes
            from flask import Flask, request, jsonify
            # Implementation here...
            ```
            
            ## 🗄️ Database Layer
            
            ### File: database/models.py
            **Path**: `/Users/annhu/vtrack_app/V_Track/database/models.py`
            **Purpose**: Database models and schema definitions
            
            ```python
            # File: /Users/annhu/vtrack_app/V_Track/database/models.py
            # Database models for the application
            from sqlalchemy import Column, Integer, String
            # Implementation here...
            ```
            
            ### File: database/config.py
            **Path**: `/Users/annhu/vtrack_app/V_Track/database/config.py`
            **Purpose**: Database connection and configuration
            
            ## 🎨 UI Components  
            
            ### File: components/LoginForm.vue
            **Path**: `/Users/annhu/vtrack_app/V_Track/components/LoginForm.vue`
            **Purpose**: Login form component with validation
            
            ```vue
            <!-- File: /Users/annhu/vtrack_app/V_Track/components/LoginForm.vue -->
            <template>
              <!-- Component template -->
            </template>
            ```
            
            ## ⚙️ Configuration
            
            ### File: config/auth-routes.js
            **Path**: `/Users/annhu/vtrack_app/V_Track/config/auth-routes.js`
            **Purpose**: Authentication route definitions
            
            ```javascript
            // File: /Users/annhu/vtrack_app/V_Track/config/auth-routes.js
            // Route configurations for authentication
            ```
            ```
          </file-organization>
        </files-section>
        
        <footer-section>
          <modification-notes>Areas likely to need changes</modification-notes>
          <related-features>Links to related features</related-features>
          <next-steps>Suggested actions or improvements</next-steps>
        </footer-section>
      </file-structure>
    </step>

    <!-- STEP 6: SAVE AND INDEX -->
    <step number="6" title="Save and Index Context">
      <objective>Save file and maintain searchable index</objective>
      
      <save-operation>
        <target-directory>/Users/annhu/vtrack_app/V_Track/docs</target-directory>
        <ensure-directory>Create directory if it doesn't exist</ensure-directory>
        <write-file>Save context file with generated name</write-file>
        <set-permissions>Ensure file is readable</set-permissions>
      </save-operation>
      
      <index-maintenance>
        <index-file>/Users/annhu/vtrack_app/V_Track/docs/context-index.md</index-file>
        <update-index>
          <entry-format>
            ```markdown
            ## {date} - {feature-name}
            - **File**: {filename}
            - **Scope**: {scope_type}
            - **Size**: {size}KB
            - **Purpose**: {brief_description}
            ```
          </entry-format>
        </update-index>
        <cleanup-old>Remove entries older than 30 days from index</cleanup-old>
      </index-maintenance>
    </step>

    <!-- STEP 7: CACHE MANAGEMENT -->
    <step number="7" title="Update Cache System">
      <objective>Maintain cache for future fast access</objective>
      
      <cache-update>
        <context-metadata>
          <location>.claude/cache/context-cache/{feature-name}.json</location>
          <content>
            ```json
            {
              "feature": "user-authentication",
              "generated": "2025-01-15T14:30:00Z",
              "project_hash": "abc123...",
              "source_files": [
                "/Users/annhu/vtrack_app/V_Track/app.py",
                "/Users/annhu/vtrack_app/V_Track/src/auth/login.js"
              ],
              "file_timestamps": {
                "app.py": "2025-01-15T10:00:00Z",
                "login.js": "2025-01-14T16:30:00Z"
              },
              "output_file": "2025-01-15-context-user-authentication-full.md",
              "scope": "full",
              "size_kb": 142
            }
            ```
          </content>
        </context-metadata>
        
        <generated-context-cache>
          <location>.claude/cache/generated-contexts/{feature-name}-{scope}.md</location>
          <purpose>Cache final context file for instant reuse</purpose>
        </generated-context-cache>
        
        <cleanup-old-cache>
          <remove-expired>Delete context cache older than 7 days</remove-expired>
          <remove-invalid>Delete cache for deleted/moved source files</remove-invalid>
        </cleanup-old-cache>
      </cache-update>
    </step>

  </execution>

  <!-- SIZE OPTIMIZATION RULES -->
  <size-optimization>
    <token-estimation>
      <calculation>1 token ≈ 3 characters (conservative estimate)</calculation>
      <target-size>150KB ≈ 50k tokens (safe for most contexts)</target-size>
      <warning-size>200KB ≈ 65k tokens (warn user)</warning-size>
      <max-size>250KB ≈ 80k tokens (hard limit)</max-size>
    </token-estimation>
    
    <reduction-strategies>
      <priority-based>Remove lowest priority files first</priority-based>
      <content-compression>
        <method>Remove verbose comments</method>
        <method>Compress repeated patterns</method>
        <method>Summarize large functions</method>
        <method>Extract key type definitions only</method>
      </content-compression>
      <selective-inclusion>
        <strategy>Include function signatures without full implementation</strategy>
        <strategy>Show structure of complex objects</strategy>
        <strategy>Reference external dependencies by name only</strategy>
      </selective-inclusion>
    </reduction-strategies>
  </size-optimization>

  <!-- SMART CONTENT EXTRACTION -->
  <content-extraction>
    <code-patterns>
      <preserve>
        <item>Full file paths (absolute and relative)</item>
        <item>Function signatures and JSDoc</item>
        <item>Type definitions and interfaces</item>
        <item>Class structures and key methods</item>
        <item>Export/import statements with their paths</item>
        <item>Configuration objects</item>
        <item>Database connection strings and model references</item>
      </preserve>
      
      <compress>
        <item>Long function bodies (keep first/last few lines)</item>
        <item>Repetitive code patterns</item>
        <item>Test data and mock objects</item>
        <item>Verbose comments and documentation</item>
      </compress>
      
      <exclude>
        <item>Node_modules references</item>
        <item>Build artifacts and generated code</item>
        <item>Debugging statements</item>
        <item>Commented-out code</item>
      </exclude>
    </code-patterns>
  </content-extraction>

  <!-- USAGE EXAMPLES -->
  <usage-examples>
    <example>
      <command>/prepare-context user authentication</command>
      <description>Create context for authentication feature</description>
      <output>2025-01-15-context-user-authentication-full.md</output>
    </example>
    <example>
      <command>/prepare-context payment --scope core</command>
      <description>Create context for payment feature, core files only</description>
      <output>2025-01-15-context-payment-processing-core.md</output>
    </example>
    <example>
      <command>/prepare-context dashboard --frontend</command>
      <description>Create context for dashboard, frontend files only</description>
      <output>2025-01-15-context-dashboard-analytics-frontend.md</output>
    </example>
  </usage-examples>

  <!-- INTEGRATION -->
  <integration>
    <feature-files-integration>
      <description>Use /feature-files analysis as input</description>
      <workflow>Run /feature-files → Use results for accurate file collection</workflow>
    </feature-files-integration>
    
    <catalog-integration>
      <description>Use feature catalog for name resolution</description>
      <fallback>If catalog missing, prompt to run /list-features</fallback>
    </catalog-integration>
  </integration>

  <!-- EXPECTED OUTPUT -->
  <expected-output>
    <immediate>
      <cache-hit>Context loaded from cache: {filename} (2 seconds)</cache-hit>
      <cache-miss>Context file created: {filename} (45 seconds)</cache-miss>
      <file-stats>Size: {size}KB, Files: {count}, Tokens: ~{tokens}</file-stats>
      <cache-status>💾 Cached for future use | ⚡ Loaded from cache</cache-status>
      <usage-tip>Copy this path to provide context in new chat session</usage-tip>
    </immediate>
    
    <file-location>/Users/annhu/vtrack_app/V_Track/docs/{generated-filename}.md</file-location>
    <cache-location>.claude/cache/generated-contexts/{feature-name}-{scope}.md</cache-location>
    <index-updated>/Users/annhu/vtrack_app/V_Track/docs/context-index.md</index-updated>
  </expected-output>

</prepare-context>