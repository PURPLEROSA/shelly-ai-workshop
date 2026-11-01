#!/bin/bash
# בונה את המצגת. דורש: npm install (pptxgenjs, sharp, lucide-static)
cd "$(dirname "$0")" && NODE_PATH="$PWD/node_modules" node build.js
