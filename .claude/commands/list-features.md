<?xml version="1.0" encoding="UTF-8"?>
<!--
  V_track Project Feature Discovery Command
  File: list-features.md
  Purpose: Auto-discover and catalog all features in the project
  Usage: /list-features
-->

<list-features>
  <description>
    Automatically discover and catalog all features/functionalities in V_track project
    Creates a comprehensive feature inventory for easier navigation
  </description>

  <execution>
    
    <!-- STEP 1: PROJECT STRUCTURE ANALYSIS -->
    <step number="1" title="Analyze Project Structure">
      <objective>Understand the project organization and identify feature boundaries</objective>
      
      <structure-analysis>
        <scan-directories>
          <command>find . -type d -not -path "./node_modules*" -not -path "./.git*" -not -path "./build*" -not -path "./dist*" | head -50</command>
          <purpose>Get main directory structure</purpose>
        </scan-directories>
        
        <identify-feature-patterns>
          <pattern-types>
            <folder-based>Features organized in separate folders</folder-based>
            <file-based>Features identified by file naming conventions</file-based>
            <route-based>Features defined by routing structure</route-based>
            <component-based>Features as reusable components</component-based>
          </pattern-types>
        </identify-feature-patterns>
        
        <architectural-hints>
          <mvc-pattern>Models, Views, Controllers structure</mvc-pattern>
          <component-architecture>React/Vue component hierarchy</component-architecture>
          <module-system>ES6 modules and exports</module-system>
          <api-structure>REST endpoints and API routes</api-structure>
        </architectural-hints>
      </structure-analysis>
    </step>

    <!-- STEP 2: ROUTE AND NAVIGATION ANALYSIS -->
    <step number="2" title="Extract Routes and Navigation">
      <objective>Discover features through routing and navigation patterns</objective>
      
      <route-discovery>
        <frontend-routes>
          <search-patterns>
            <pattern>Router configuration files</pattern>
            <pattern>Route definitions (React Router, Vue Router)</pattern>
            <pattern>Navigation menus and links</pattern>
            <pattern>Breadcrumb definitions</pattern>
          </search-patterns>
          <commands>
            <command>rg -n "route|path.*:|to.*:" --type js --type ts --type vue | head -30</command>
            <command>rg -n "Navigate|Link|href" --type js --type ts --type vue | head -20</command>
          </commands>
        </frontend-routes>
        
        <backend-routes>
          <search-patterns>
            <pattern>API endpoint definitions</pattern>
            <pattern>Express/Fastify route handlers</pattern>
            <pattern>Controller methods</pattern>
            <pattern>Middleware definitions</pattern>
          </search-patterns>
          <commands>
            <command>rg -n "app\.(get|post|put|delete)|router\." --type js --type ts | head -20</command>
            <command>rg -n "endpoint|api.*/" --type js --type ts | head -15</command>
          </commands>
        </backend-routes>
      </route-discovery>
    </step>

    <!-- STEP 3: COMPONENT AND MODULE ANALYSIS -->
    <step number="3" title="Analyze Components and Modules">
      <objective>Identify features through component and module structure</objective>
      
      <component-analysis>
        <ui-components>
          <search-strategy>
            <find-main-components>
              <command>find . -name "*.vue" -o -name "*Component.js" -o -name "*Component.tsx" | grep -v node_modules | head -25</command>
            </find-main-components>
            <analyze-component-names>
              <method>Extract meaningful names from component files</method>
              <examples>
                <example>UserProfile.vue → User Profile Management</example>
                <example>PaymentForm.js → Payment Processing</example>
                <example>ProductCatalog.tsx → Product Catalog</example>
              </examples>
            </analyze-component-names>
          </search-strategy>
        </ui-components>
        
        <business-modules>
          <search-strategy>
            <find-business-logic>
              <command>rg -n "class.*Service|class.*Manager|class.*Controller" --type js --type ts | head -20</command>
              <command>rg -n "export.*function.*" --type js --type ts | grep -E "(create|update|delete|get|manage)" | head -15</command>
            </find-business-logic>
            <extract-domain-concepts>
              <method>Identify business domain terms from class and function names</method>
            </extract-domain-concepts>
          </search-strategy>
        </business-modules>
      </component-analysis>
    </step>

    <!-- STEP 4: DATABASE AND API ANALYSIS -->
    <step number="4" title="Database and API Pattern Analysis">
      <objective>Discover features through data models and API patterns</objective>
      
      <data-analysis>
        <database-models>
          <search-patterns>
            <pattern>Model definitions (Mongoose, Sequelize, etc.)</pattern>
            <pattern>Database schema files</pattern>
            <pattern>Migration files</pattern>
            <pattern>Entity definitions</pattern>
          </search-patterns>
          <commands>
            <command>rg -n "Schema|Model|Entity" --type js --type ts | head -20</command>
            <command>find . -name "*model*" -o -name "*schema*" -o -name "*entity*" | grep -v node_modules | head -15</command>
          </commands>
        </database-models>
        
        <api-endpoints>
          <search-patterns>
            <pattern>REST API endpoints</pattern>
            <pattern>GraphQL schemas</pattern>
            <pattern>API documentation</pattern>
            <pattern>Request/Response types</pattern>
          </search-patterns>
          <commands>
            <command>rg -n "\/api\/|endpoint.*:|@Get|@Post|@Put|@Delete" --type js --type ts | head -20</command>
          </commands>
        </api-endpoints>
      </data-analysis>
    </step>

    <!-- STEP 5: DOCUMENTATION AND COMMENT ANALYSIS -->
    <step number="5" title="Extract from Documentation">
      <objective>Find feature descriptions from docs and comments</objective>
      
      <documentation-mining>
        <readme-files>
          <command>find . -name "README*" -o -name "*.md" | grep -v node_modules | head -10</command>
          <analysis>Extract feature lists and descriptions from markdown files</analysis>
        </readme-files>
        
        <code-comments>
          <search-strategy>
            <feature-comments>
              <command>rg -n "Feature:|TODO:|FEATURE:|Module:" --type js --type ts --type vue | head -15</command>
            </feature-comments>
            <documentation-blocks>
              <command>rg -n "\/\*\*.*@|Description:|Purpose:" --type js --type ts | head -10</command>
            </documentation-blocks>
          </search-strategy>
        </code-comments>
        
        <package-json-analysis>
          <command>cat package.json | jq '.scripts'</command>
          <purpose>Extract npm scripts that might indicate features</purpose>
        </package-json-analysis>
      </documentation-mining>
    </step>

    <!-- STEP 6: INTELLIGENT CATEGORIZATION -->
    <step number="6" title="Categorize and Organize Features">
      <objective>Group discovered features into logical categories</objective>
      
      <categorization>
        <feature-categories>
          <authentication>
            <keywords>login, auth, signin, signup, register, password, token, session</keywords>
            <description>User authentication and authorization</description>
          </authentication>
          
          <user-management>
            <keywords>user, profile, account, settings, preferences</keywords>
            <description>User profile and account management</description>
          </user-management>
          
          <content-management>
            <keywords>post, article, content, cms, editor, publish</keywords>
            <description>Content creation and management</description>
          </content-management>
          
          <e-commerce>
            <keywords>product, cart, checkout, payment, order, shop, buy</keywords>
            <description>E-commerce and shopping functionality</description>
          </e-commerce>
          
          <communication>
            <keywords>message, chat, notification, email, comment, feedback</keywords>
            <description>Communication and messaging features</description>
          </communication>
          
          <analytics>
            <keywords>analytics, report, dashboard, chart, statistics, metrics</keywords>
            <description>Analytics and reporting features</description>
          </analytics>
          
          <admin>
            <keywords>admin, management, control, config, settings, system</keywords>
            <description>Administrative and system management</description>
          </admin>
          
          <core-utilities>
            <keywords>util, helper, service, api, data, storage</keywords>
            <description>Core utilities and infrastructure</description>
          </core-utilities>
        </feature-categories>
        
        <confidence-scoring>
          <high-confidence>Clear evidence from multiple sources (routes + components + docs)</high-confidence>
          <medium-confidence>Evidence from 2 sources (e.g., routes + components)</medium-confidence>
          <low-confidence>Evidence from 1 source or unclear patterns</low-confidence>
        </confidence-scoring>
      </categorization>
    </step>

    <!-- STEP 7: GENERATE FEATURE CATALOG -->
    <step number="7" title="Generate Feature Catalog">
      <objective>Create comprehensive, searchable feature inventory</objective>
      
      <catalog-format>
        <json-database>
          <location>.claude/cache/features-catalog.json</location>
          <structure>
            ```json
            {
              "project": "V_track",
              "generated": "2025-01-XX",
              "features": {
                "authentication": {
                  "name": "User Authentication",
                  "category": "authentication",
                  "confidence": "high",
                  "keywords": ["login", "auth", "signin"],
                  "files": ["src/auth/login.js", "components/LoginForm.vue"],
                  "routes": ["/login", "/register"],
                  "description": "User login and registration system"
                }
              }
            }
            ```
          </structure>
        </json-database>
        
        <markdown-index>
          <location>.claude/docs/features-index.md</location>
          <format>
            ```markdown
            # V_track Features Catalog
            
            ## 🔐 Authentication (High Confidence)
            - **User Login** - Login and authentication system
              - Keywords: login, auth, signin
              - Files: `src/auth/login.js`, `components/LoginForm.vue`
              - Routes: `/login`, `/register`
            
            ## 👤 User Management (High Confidence)
            - **User Profile** - User profile management
              - Keywords: profile, user, account
              - Files: `src/user/profile.js`, `components/UserProfile.vue`
            ```
          </format>
        </markdown-index>
        
        <interactive-menu>
          <console-display>
            ```
            V_track Features Discovered:
            
            🔐 Authentication
            1. User Login System
            2. Password Reset
            3. Registration Flow
            
            👤 User Management  
            4. User Profile
            5. Account Settings
            
            📊 Analytics
            6. Dashboard
            7. Reports
            
            Type number or search term to explore feature files...
            ```
          </console-display>
        </interactive-menu>
      </catalog-format>
    </step>

  </execution>

  <!-- INTEGRATION WITH FEATURE-FILES COMMAND -->
  <integration>
    <enhanced-search>
      <description>Update /feature-files command to use this catalog</description>
      <workflow>
        <step>User runs /feature-files without arguments</step>
        <step>Display interactive menu from catalog</step>
        <step>User selects feature or searches</step>
        <step>Run detailed analysis on selected feature</step>
      </workflow>
    </enhanced-search>
    
    <auto-update>
      <description>Keep catalog fresh</description>
      <triggers>
        <trigger>Run automatically when project structure changes</trigger>
        <trigger>Manual refresh with /list-features --refresh</trigger>
        <trigger>Integration with git hooks</trigger>
      </triggers>
    </auto-update>
  </integration>

  <!-- USAGE EXAMPLES -->
  <usage-examples>
    <example>
      <command>/list-features</command>
      <description>Discover all features in current project</description>
    </example>
    <example>
      <command>/list-features --refresh</command>
      <description>Force refresh of feature catalog</description>
    </example>
    <example>
      <command>/list-features --category authentication</command>
      <description>Show only authentication-related features</description>
    </example>
  </usage-examples>

  <!-- EXPECTED OUTPUT -->
  <expected-output>
    <immediate>Interactive feature menu in console</immediate>
    <persistent>JSON catalog and markdown index in .claude/</persistent>
    <integration>Enhanced /feature-files command with feature picker</integration>
  </expected-output>

</list-features>