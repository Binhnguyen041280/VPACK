<?xml version="1.0" encoding="UTF-8"?>
<git>
  <description>Simple auto git commit and push</description>
  
  <script>
```bash
    #!/bin/bash
    
    # Check changes
    if [ -z "$(git status --porcelain)" ]; then
        echo "No changes"
        exit 0
    fi
    
    # Simple message with timestamp
    MESSAGE="Auto commit $(date '+%H:%M')"
    
    # Direct git commands
    git add .
    git commit -m "$MESSAGE" 
    git push
    
    echo "Done"