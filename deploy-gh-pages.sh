#!/bin/bash
cd /Users/phucnguyen/Desktop/AI/day10/K4-L3-DAY10-ABCD-DataPipeline
git checkout -b gh-pages 2>/dev/null || git checkout gh-pages
cp -r front_end/dist/* .
git add .
git commit -m "Deploy to GitHub Pages"
git push -u origin gh-pages --force
echo "✅ Deployed!"
echo "Enable tại: https://github.com/rin1652/K4-L3-DAY10-ABCD-DataPipeline/settings/pages"
