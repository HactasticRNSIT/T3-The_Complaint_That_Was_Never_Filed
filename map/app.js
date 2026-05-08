const express = require('express');
const app = express();

app.set('view engine', 'ejs');
app.set('views', './views');

// --- THE IMPORTANT ADDITION ---
// This line allows your server to read the data coming from your form
app.use(express.urlencoded({ extended: true }));

// Your data starts with these "pre-filled" points
let bangaloreCoords = [
  { lat: 12.9716, lng: 77.5946, label: 'City Center' },
  { lat: 12.9352, lng: 77.6245, label: 'Koramangala' },
  { lat: 13.0358, lng: 77.5970, label: 'Hebbal' },
  { lat: 12.9279, lng: 77.6271, label: 'BTM Layout' },
  { lat: 12.9784, lng: 77.6408, label: 'Indiranagar' },
];

// 1. THE GET ROUTE: Shows the map with all current dots
app.get('/map', (req, res) => {
  res.render('map', { coords: bangaloreCoords });
});

// 2. THE POST ROUTE: Catches the new report and adds it to the list
app.post('/report-incident', (req, res) => {
    const newIncident = {
        lat: parseFloat(req.body.latitude),
        lng: parseFloat(req.body.longitude),
        label: req.body.incidentType 
    };

    bangaloreCoords.push(newIncident); // Add to our list
    console.log("New incident added:", newIncident);
    
    res.redirect('/map'); // Refresh the page to show the new dot
});

app.listen(3000, () => {
  console.log('Server running at http://localhost:3000/map');
});