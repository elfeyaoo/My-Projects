// server.js

const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 5000;

// Middleware
app.use(cors()); // Allow requests from any origin
app.use(express.json()); // Parse JSON bodies

// Sample anonymization function (replace with your logic)
function anonymize(data) {
  // Example: Replace all string values with '***'
  return data.map(row => {
    const anonymizedRow = {};
    for (let key in row) {
      anonymizedRow[key] = typeof row[key] === 'string' ? '***' : row[key];
    }
    return anonymizedRow;
  });
}

// Route to handle anonymization
app.post('/anonymize', (req, res) => {
  const inputData = req.body.data;

  if (!Array.isArray(inputData)) {
    return res.status(400).json({ error: 'Invalid data format. Expected an array of objects.' });
  }

  const anonymizedData = anonymize(inputData);
  res.json({ anonymizedData });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
