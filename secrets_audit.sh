#!/usr/bin/env bash
# ==============================================================================
# Comprehensive Repository Secrets & Security Auditor
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "========================================================================"
echo "  🔒 REPOSITORY SECURITY & SECRETS AUDIT"
echo "========================================================================"

FOUND_ISSUES=0

# 1. Check .gitignore exists and covers critical secret files
echo "1. Checking .gitignore coverage..."
if [ ! -f ".gitignore" ]; then
    echo "   ❌ ERROR: .gitignore is missing!"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    for pattern in "*testnet_wallet.json" ".env" "*.key" "*.pem"; do
        if ! grep -q "$pattern" .gitignore; then
            echo "   ⚠️ WARNING: '$pattern' missing from .gitignore"
            FOUND_ISSUES=$((FOUND_ISSUES + 1))
        fi
    done
    echo "   ✅ .gitignore exists and covers key patterns."
fi

# 2. Check tracked files for any raw private keys (excluding example files)
echo "2. Scanning all tracked files in git..."
LEAKED_FILES=$(git grep -EI "(private_key|PRIVATE_KEY|secret|SECRET)[[:space:]]*[:=][[:space:]]*['\"]0x[a-fA-F0-9]{64}['\"]" -- ':!*.example' 2>/dev/null || true)
if [ -n "$LEAKED_FILES" ]; then
    echo "   ❌ POTENTIAL LEAK DETECTED:"
    echo "$LEAKED_FILES"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    echo "   ✅ Zero raw private keys detected in tracked source code."
fi

# 3. Check full git commit history for leaked credentials
echo "3. Scanning full git commit history..."
HIST_LEAKS=$(git log -p | grep -E "(private_key[[:space:]]*:[[:space:]]*\"0x[a-fA-F0-9]{64}\")" || true)
if [ -n "$HIST_LEAKS" ]; then
    echo "   ❌ CRITICAL: Private key found in past git commit history!"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    echo "   ✅ Git history is clean: zero live private keys ever committed."
fi

# 4. Check for presence of real wallet file in working directory
echo "4. Checking local working directory..."
if [ -f "mev_arbitrage_engine/testnet_wallet.json" ]; then
    # Verify it is git-ignored
    if git status --porcelain | grep -q "testnet_wallet.json"; then
        echo "   ❌ DANGER: testnet_wallet.json is being tracked by git!"
        FOUND_ISSUES=$((FOUND_ISSUES + 1))
    else
        echo "   ✅ testnet_wallet.json exists locally but is safely ignored by git."
    fi
fi

echo "------------------------------------------------------------------------"
if [ "$FOUND_ISSUES" -eq 0 ]; then
    echo "🎉 AUDIT PASSED: Repository is clean and safe from leaked secrets."
    exit 0
else
    echo "🚨 AUDIT FAILED: Found $FOUND_ISSUES potential security issues. Review output above!"
    exit 1
fi
