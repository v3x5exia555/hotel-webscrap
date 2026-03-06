#!/bin/bash
# scripts/git_auto.sh
# Automates: New Branch -> Add -> Commit -> Push

MESSAGE=$1

if [ -z "$MESSAGE" ]; then
    echo "Usage: ./git_auto.sh 'your commit message'"
    exit 1
fi

# 1. Generate Branch Name (feature/timestamp)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BRANCH_NAME="update-$TIMESTAMP"

echo "🚀 Starting Git Automation for branch: $BRANCH_NAME"

# 2. Create and Switch to New Branch
git checkout -b "$BRANCH_NAME"

# 3. Add all changes (obeying .gitignore)
git add .

# 4. Commit
git commit -m "$MESSAGE"

# 5. Push to GitHub
# Assuming 'origin' is the remote name
git push -u origin "$BRANCH_NAME"

echo "✅ Successfully pushed to GitHub on branch: $BRANCH_NAME"
echo "🔗 You can now create a Pull Request on GitHub."

# 6. Optional: Return to main (uncomment if desired)
# git checkout main
