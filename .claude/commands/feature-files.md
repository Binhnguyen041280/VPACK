<?xml version="1.0" encoding="UTF-8"?>
<!--
  V_track Project Feature Files Discovery Command
  File: feature-files.md
  Purpose: Find all files related to a specific feature/functionality
  Usage: /feature-files $ARGUMENTS
-->

<feature-files>
  <description>
    Comprehensive discovery of all files related to feature: $ARGUMENTS
    Uses multi-step analysis to find direct and indirect dependencies
  </description>

  <execution>
    
    <!-- STEP 1: INITIAL DISCOVERY -->
    <step number="1" title="Feature Context Discovery">
      <objective>Understand the feature scope and identify entry points</objective>
      
      <actions>
        <analyze-feature-description>
          <input>$ARGUMENTS</input>
          <output>Feature understanding and search keywords</output>
        </analyze-feature-description>
        
        <scan-project-structure>
          <command>find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.vue" -o -name "*.css" -o -name "*.scss" \) | grep -v node_modules | grep -v build | grep -v dist</command>
          <purpose>Get complete source file list</purpose>
        </scan-project-structure>
        
        <identify-likely-files>
          <method>Pattern matching on filenames</method>
          <patterns>
            <pattern>Files containing feature name in filename</pattern>
            <pattern>Directory names related to feature</pattern>
            <pattern>Component names matching feature</pattern>
          </patterns>
        </identify-likely-files>
      </actions>
    </step>

    <!-- STEP 2: SEMANTIC SEARCH -->
    <step number="2" title="Content-Based Discovery">
      <objective>Find files containing feature-related code</objective>
      
      <search-strategies>
        <ripgrep-definitions>
          <command>rg -n "class|function|const|export|import.*($FEATURE_KEYWORDS)" --type js --type ts</command>
          <purpose>Find function/class definitions</purpose>
        </ripgrep-definitions>
        
        <content-search>
          <method>Search for feature-specific terms</method>
          <search-patterns>
            <pattern>Function names containing feature keywords</pattern>
            <pattern>Variable names related to feature</pattern>
            <pattern>Comments mentioning feature</pattern>
            <pattern>API endpoints related to feature</pattern>
            <pattern>Database table/field names</pattern>
          </search-patterns>
        </content-search>
        
        <ui-component-search>
          <command>rg -n "($FEATURE_KEYWORDS)" --type html --type css --type scss</command>
          <purpose>Find UI elements and styles</purpose>
        </ui-component-search>
      </search-strategies>
    </step>

    <!-- STEP 3: DEPENDENCY ANALYSIS -->
    <step number="3" title="Dependency Tracking">
      <objective>Find files that import/export or depend on discovered files</objective>
      
      <dependency-analysis>
        <forward-dependencies>
          <description>Files that the feature files import/require</description>
          <method>
            <analyze-imports>Parse import statements in discovered files</analyze-imports>
            <resolve-paths>Convert relative paths to absolute</resolve-paths>
            <trace-dependencies>Follow dependency chain</trace-dependencies>
          </method>
        </forward-dependencies>
        
        <backward-dependencies>
          <description>Files that import/use the feature files</description>
          <method>
            <search-references>
              <command>rg -n "import.*($DISCOVERED_FILES)" --type js --type ts</command>
            </search-references>
            <find-usage>
              <command>rg -n "($EXPORTED_FUNCTIONS|$EXPORTED_CLASSES)" --type js --type ts</command>
            </find-usage>
          </method>
        </backward-dependencies>
        
        <configuration-files>
          <description>Config files that may reference the feature</description>
          <file-types>
            <type>package.json - scripts and dependencies</type>
            <type>webpack.config.js - entry points and aliases</type>
            <type>router files - route definitions</type>
            <type>.env files - environment variables</type>
            <type>API route files - backend endpoints</type>
          </file-types>
        </configuration-files>
      </dependency-analysis>
    </step>

    <!-- STEP 4: CATEGORIZATION -->
    <step number="4" title="File Categorization">
      <objective>Organize discovered files by their role in the feature</objective>
      
      <categories>
        <core-files>
          <description>Primary implementation files</description>
          <criteria>
            <criterion>Contains main feature logic</criterion>
            <criterion>Exports feature's primary functions/classes</criterion>
            <criterion>Feature entry points</criterion>
          </criteria>
        </core-files>
        
        <supporting-files>
          <description>Helper and utility files</description>
          <criteria>
            <criterion>Utilities used by core files</criterion>
            <criterion>Shared components/functions</criterion>
            <criterion>Type definitions</criterion>
          </criteria>
        </supporting-files>
        
        <ui-files>
          <description>User interface related files</description>
          <criteria>
            <criterion>Component files</criterion>
            <criterion>Style files (CSS/SCSS)</criterion>
            <criterion>Template files</criterion>
          </criteria>
        </ui-files>
        
        <test-files>
          <description>Testing related files</description>
          <criteria>
            <criterion>Unit tests for feature</criterion>
            <criterion>Integration tests</criterion>
            <criterion>Mock files</criterion>
          </criteria>
        </test-files>
        
        <config-files>
          <description>Configuration and setup files</description>
          <criteria>
            <criterion>Route definitions</criterion>
            <criterion>API endpoints</criterion>
            <criterion>Database schemas</criterion>
            <criterion>Build configurations</criterion>
          </criteria>
        </config-files>
        
        <documentation-files>
          <description>Documentation and specifications</description>
          <criteria>
            <criterion>README files</criterion>
            <criterion>API documentation</criterion>
            <criterion>Feature specifications</criterion>
          </criteria>
        </documentation-files>
      </categories>
    </step>

    <!-- STEP 5: IMPACT ANALYSIS -->
    <step number="5" title="Impact Assessment">
      <objective>Understand the scope of feature modifications</objective>
      
      <impact-assessment>
        <risk-levels>
          <high-risk>
            <description>Changes would affect core business logic</description>
            <files>Database schemas, API contracts, core algorithms</files>
          </high-risk>
          
          <medium-risk>
            <description>Changes would affect user experience</description>
            <files>UI components, user flows, validation logic</files>
          </medium-risk>
          
          <low-risk>
            <description>Changes are mostly cosmetic or additive</description>
            <files>Styles, documentation, test files</files>
          </low-risk>
        </risk-levels>
        
        <affected-areas>
          <frontend>List of frontend files and components</frontend>
          <backend>List of backend files and APIs</backend>
          <database>List of database-related files</database>
          <build-system>List of build and deployment files</build-system>
        </affected-areas>
      </impact-assessment>
    </step>

    <!-- STEP 6: REPORT GENERATION -->
    <step number="6" title="Generate Feature Map">
      <objective>Create comprehensive report of feature files</objective>
      
      <report-format>
        <summary>
          <feature-name>$ARGUMENTS</feature-name>
          <total-files-found>Count of discovered files</total-files-found>
          <complexity-score>Based on number of dependencies</complexity-score>
        </summary>
        
        <file-tree>
          <structure>Organized by category and risk level</structure>
          <format>
            ```
            Feature: $ARGUMENTS
            ├── Core Files (High Impact)
            │   ├── src/features/auth/login.js
            │   └── src/features/auth/auth-service.js
            ├── Supporting Files (Medium Impact)
            │   ├── src/utils/validation.js
            │   └── src/types/user.ts
            ├── UI Files (Medium Impact)
            │   ├── src/components/LoginForm.vue
            │   └── src/styles/login.scss
            ├── Test Files (Low Impact)
            │   ├── tests/auth/login.test.js
            │   └── tests/auth/auth-service.test.js
            └── Config Files (Variable Impact)
                ├── src/router/auth-routes.js
                └── api/routes/auth.js
            ```
          </format>
        </file-tree>
        
        <dependency-graph>
          <relationships>Show import/export relationships</relationships>
          <critical-paths>Identify key dependency chains</critical-paths>
        </dependency-graph>
        
        <modification-guide>
          <safe-to-modify>Files that can be changed with minimal risk</safe-to-modify>
          <requires-testing>Files that need thorough testing after changes</requires-testing>
          <breaking-changes>Files that could cause breaking changes</breaking-changes>
        </modification-guide>
      </report-format>
      
      <export-options>
        <markdown-file>Save to .claude/docs/feature-map-$ARGUMENTS.md</markdown-file>
        <json-export>Save structured data to .claude/cache/feature-data-$ARGUMENTS.json</json-export>
      </export-options>
    </step>

  </execution>

  <!-- SEARCH CONFIGURATION -->
  <search-config>
    <file-extensions>
      <include>.js, .ts, .jsx, .tsx, .vue, .css, .scss, .html, .json, .md</include>
      <exclude>node_modules, build, dist, coverage, .git</exclude>
    </file-extensions>
    
    <search-depth>
      <max-levels>5</max-levels>
      <dependency-limit>50</dependency-limit>
    </search-depth>
    
    <cache-strategy>
      <location>.claude/cache/feature-analysis/</location>
      <expiry>7 days</expiry>
    </cache-strategy>
  </search-config>

  <!-- USAGE EXAMPLES -->
  <usage-examples>
    <example>
      <command>/feature-files authentication</command>
      <description>Find all files related to user authentication feature</description>
    </example>
    <example>
      <command>/feature-files user profile</command>
      <description>Find files related to user profile management</description>
    </example>
    <example>
      <command>/feature-files payment checkout</command>
      <description>Find files for payment and checkout functionality</description>
    </example>
  </usage-examples>

  <!-- EXPECTED OUTPUT -->
  <expected-output>
    <console-display>Categorized file list with risk levels</console-display>
    <markdown-report>Detailed feature map in .claude/docs/</markdown-report>
    <actionable-insights>Modification guidelines and impact assessment</actionable-insights>
  </expected-output>

</feature-files>