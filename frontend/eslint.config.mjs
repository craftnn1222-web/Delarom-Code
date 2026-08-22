// ESLint flat config (v9) for Continents of Delarom frontend.
//
// The two rules we care about most are kept at "error" so violations
// fail the pre-commit hook (lint-staged) and CI lint runs. These are
// the rules the 2026-05-30 code review report flagged the most: 75
// hook-deps violations + many unused vars. Catching them at commit
// time prevents them from creeping back in.

import js from '@eslint/js';
import globals from 'globals';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import jsxA11yPlugin from 'eslint-plugin-jsx-a11y';
import importPlugin from 'eslint-plugin-import';

export default [
  // Skip generated / vendor folders entirely.
  {
    ignores: [
      'build/**',
      'node_modules/**',
      'public/**',
      'plugins/**',
      'src/components/ui/**', // shadcn-generated; not our hand-written code
    ],
  },

  js.configs.recommended,

  {
    files: ['src/**/*.{js,jsx}'],
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
      'jsx-a11y': jsxA11yPlugin,
      import: importPlugin,
    },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    settings: {
      react: { version: 'detect' },
    },
    rules: {
      // Enabled so `import React from 'react'` and JSX-only identifiers
      // are correctly marked as used under the modern JSX transform.
      'react/jsx-uses-react': 'error',
      'react/jsx-uses-vars': 'error',

      // ── HARD ERRORS ── (block commits via lint-staged)
      // These are the bug-prevention rules the code review specifically asked
      // us to enforce. A stale closure or a wrong hook call is a real bug.
      'react-hooks/rules-of-hooks':   'error',
      'react-hooks/exhaustive-deps': 'error',

      // ── WARNINGS ── (visible in `yarn lint`, do NOT block commits)
      // The existing codebase has ~600 unused-import warnings (React, dead
      // lucide icons, etc.). Surfacing them as warnings keeps the noise
      // discoverable without forcing a giant cleanup sweep before any commit.
      'no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^(_|React$)',
        caughtErrorsIgnorePattern: '^_',
      }],
      'no-empty': ['warn', { allowEmptyCatch: false }],

      // ── DISABLED ──
      'react/prop-types':           'off',  // not used in this codebase
      'react/react-in-jsx-scope':   'off',  // React 17+ JSX transform
    },
  },
];
