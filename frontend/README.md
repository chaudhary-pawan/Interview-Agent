# Sherlock Candidate Identification System (SCI) - Frontend Dashboard

This directory contains the React + TypeScript frontend dashboard for the Sherlock Candidate Identification System.

## Features
- **Live Meeting Gallery**: Displays connected participants, speaking indicators, active webcams/screenshares, and real-time candidate probabilities.
- **Explainability Panel**: Attributes positive and negative evidence for the identified candidate based on Jaro-Winkler name similarity, speech patterns, turn-taking graph centrality, semantic transcript keys, and join timing.
- **Conversation Analysis**: Displays a circular turn-taking graph (dynamic interaction edges) and a live confidence tracking timeline chart.
- **Log Feeds**: Real-time meeting stream logs and dialog transcript viewer.
- **Controls**: Choose from 6 pre-configured meeting simulation scenarios and adjust simulation speeds (1x, 2x, 5x).

## Tech Stack
- **Framework**: Vite + React 19 + TypeScript
- **Icons**: Lucide React
- **Styling**: Glassmorphism UI styled with vanilla CSS (defined in `src/index.css`)

## Getting Started
1. Install dependencies:
   ```bash
   npm install
   ```
2. Start Vite dev server:
   ```bash
   npm run dev
   ```
3. Build for production:
   ```bash
   npm run build
   ```
