import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

const sourceDir = 'telite-frontend/src/assets/screenshots/source';
const outputDir = 'telite-frontend/public/screenshots';

if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

const files = fs.readdirSync(sourceDir);

files.forEach(async (file) => {
  const ext = path.extname(file);
  const name = path.basename(file, ext);
  
  // Convert to WebP
  await sharp(path.join(sourceDir, file))
    .resize(1200)
    .webp({ quality: 80 })
    .toFile(path.join(outputDir, `${name}.webp`));
    
  console.log(`Optimized: ${file}`);
});
