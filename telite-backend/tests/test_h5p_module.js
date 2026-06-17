const https = require('https');

https.get('https://cdn.jsdelivr.net/npm/h5p-standalone@3.5.1/dist/main.bundle.js', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    // We mock window and document to safely eval
    const context = { window: { navigator: { userAgent: "node" } }, document: { createElement: () => ({}) }, console };
    try {
      const H5PStandalone = require('h5p-standalone');
      console.log("h5p-standalone exports:", Object.keys(H5PStandalone));
      console.log("typeof H5PStandalone:", typeof H5PStandalone);
      console.log("typeof H5PStandalone.H5P:", typeof H5PStandalone.H5P);
    } catch (e) {
      console.error(e.message);
    }
  });
});
