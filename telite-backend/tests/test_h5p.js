const https = require('https');

https.get('https://cdn.jsdelivr.net/npm/h5p-standalone@3.5.1/dist/main.bundle.js', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    // Look for window assignment
    const match = data.match(/window\.(.*?)=/);
    console.log("Global assignment match:", match ? match[0] : "None");
    
    // Look for H5P object structure
    console.log("Includes H5P?", data.includes('H5P'));
  });
});
