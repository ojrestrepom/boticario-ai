#!/usr/bin/env bash
set -euo pipefail
export PATH=/opt/homebrew/share/flutter/bin:$PATH
QA="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$QA/../../../../.." && pwd)"
cd "$ROOT/app"
{
  date -u '+%Y-%m-%dT%H:%M:%SZ'
  echo '$ flutter --version'
  flutter --version
  echo '$ flutter test --no-pub --reporter expanded test/features/explore/explore_page_test.dart'
  flutter test --no-pub --reporter expanded test/features/explore/explore_page_test.dart
  echo '$ flutter test --no-pub --reporter expanded "$QA/flutter/explore_qa_test.dart"'
  flutter test --no-pub --reporter expanded "$QA/flutter/explore_qa_test.dart"
  echo '$ flutter test --no-pub --reporter expanded test/'
  flutter test --no-pub --reporter expanded test/
  echo '$ dart format --output=none --set-exit-if-changed .'
  dart format --output=none --set-exit-if-changed .
  echo '$ flutter analyze --no-pub'
  flutter analyze --no-pub
} 2>&1 | tee "$QA/evidence/rerun.log"
