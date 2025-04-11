// DOM Elements
const shareFoodBtn = document.getElementById('shareFoodBtn');
const shareFoodModal = document.querySelector('.share-food-modal');
const closeModal = document.querySelector('.close-modal');
const foodShareForm = document.getElementById('foodShareForm');
const listingsContainer = document.getElementById('listingsContainer');
const foodSavedStat = document.getElementById('foodSavedStat');
const co2SavedStat = document.getElementById('co2SavedStat');
const mealsSharedStat = document.getElementById('mealsSharedStat');

// Google Maps variables
let map;
let markers = [];
let autocomplete;

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
    const shareFoodBtn = document.getElementById("shareFoodBtn");
    const shareFoodModal = document.getElementById("share-food");
    const closeModal = document.querySelector(".close-modal");

    // Show the modal when the button is clicked
    shareFoodBtn.addEventListener("click", () => {
        shareFoodModal.style.display = "block";
    });

    // Hide the modal when the close button is clicked
    closeModal.addEventListener("click", () => {
        shareFoodModal.style.display = "none";
    });

    // Hide the modal when clicking outside the modal content
    window.addEventListener("click", (event) => {
        if (event.target === shareFoodModal) {
            shareFoodModal.style.display = "none";
        }
    });
});

// High accuracy location fetch
function getHighAccuracyLocation() {
    return new Promise((resolve) => {
        resolve({ lat: 17.2095462, lng: 78.6186294, accuracy: 0 });
    });
}

// Initialize Google Map
async function initMap() {
    try {
        const coords = await getHighAccuracyLocation();

        if (coords.accuracy > 50) {
            console.warn(`Location accuracy is ${coords.accuracy} meters.`);
        }

        map = new google.maps.Map(document.getElementById('map'), {
            center: { lat: coords.lat, lng: coords.lng },
            zoom: 15,
            mapTypeControl: false,
            streetViewControl: false
        });

        new google.maps.Marker({
            position: { lat: coords.lat, lng: coords.lng },
            map: map,
            title: 'Your Location',
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: '#4285F4',
                fillOpacity: 1,
                strokeColor: '#FFFFFF',
                strokeWeight: 2
            }
        });

        new google.maps.Circle({
            strokeColor: '#4285F4',
            strokeOpacity: 0.4,
            strokeWeight: 1,
            fillColor: '#4285F4',
            fillOpacity: 0.2,
            map: map,
            center: { lat: coords.lat, lng: coords.lng },
            radius: coords.accuracy
        });

        initAutocomplete(coords);
    } catch (error) {
        console.error('Error getting location:', error);
        createMap({ lat: 40.7128, lng: -74.0060 });
    }
}

function createMap(center) {
    map = new google.maps.Map(document.getElementById('map'), {
        center: center,
        zoom: 12
    });
    addExistingMarkers();
}

function initAutocomplete(coords) {
    const defaultBounds = new google.maps.LatLngBounds(
        new google.maps.LatLng(coords.lat - 0.1, coords.lng - 0.1),
        new google.maps.LatLng(coords.lat + 0.1, coords.lng + 0.1)
    );

    autocomplete = new google.maps.places.Autocomplete(
        document.getElementById('location'),
        {
            bounds: defaultBounds,
            strictBounds: true,
            types: ['address'],
            componentRestrictions: { country: 'India' }
        }
    );

    autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (!place.geometry) return;

        document.getElementById('latitude').value = place.geometry.location.lat();
        document.getElementById('longitude').value = place.geometry.location.lng();

        map.setCenter(place.geometry.location);
        map.setZoom(16);
    });
}

function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}

function addMarker(location, title) {
    const marker = new google.maps.Marker({
        position: location,
        map: map,
        title: title
    });
    markers.push(marker);
    return marker;
}

function addExistingMarkers(listings) {
    if (!map || !listings) return;
    clearMarkers();

    listings.forEach(listing => {
        const marker = addMarker(
            { lat: listing.latitude, lng: listing.longitude },
            listing.title
        );

        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div class="map-info-window">
                    <h3>${listing.title}</h3>
                    <p>${listing.quantity}</p>
                    <p>Expires: ${new Date(listing.expiry_date).toLocaleDateString()}</p>
                    <p>Location: ${listing.location}</p>
                    <button class="map-claim-btn" data-id="${listing.id}">Claim</button>
                </div>
            `
        });

        marker.addListener('click', () => {
            infoWindow.open(map, marker);
            setTimeout(() => {
                document.querySelector('.map-claim-btn')?.addEventListener('click', (e) => {
                    handleClaimFood(e);
                    infoWindow.close();
                });
            }, 100);
        });
    });

    if (listings.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        listings.forEach(listing => {
            bounds.extend(new google.maps.LatLng(listing.latitude, listing.longitude));
        });
        map.fitBounds(bounds);
    }
}

async function loadListings() {
    try {
        const response = await fetch('/api/listings');
        const listings = await response.json();

        displayListings(listings);

        if (map) {
            addExistingMarkers(listings);
        } else {
            setTimeout(() => addExistingMarkers(listings), 1000);
        }
    } catch (error) {
        console.error('Error loading listings:', error);
    }
}
// Function to claim food
async function claimFood(listingId) {
    try {
        const response = await fetch('/api/claims', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ listing_id: listingId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to claim food');
        }
        
        alert(`Successfully claimed! Contact donor at: ${data.claim.donor_contact}`);
        loadUserClaims();
        loadAvailableListings();
    } catch (error) {
        alert(error.message);
    }
}

// Function to load user's claims
async function loadUserClaims() {
    try {
        const response = await fetch('/api/claims', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        const claims = await response.json();
        
        if (!response.ok) {
            throw new Error('Failed to load claims');
        }
        
        const tableBody = document.querySelector('#claimsTable tbody');
        tableBody.innerHTML = '';
        
        if (claims.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5">You have no active claims</td></tr>';
            return;
        }
        
        claims.forEach(claim => {
            const row = document.createElement('tr');
            
            row.innerHTML = `
                <td>${claim.title}</td>
                <td>${claim.quantity}</td>
                <td>${claim.donor_name}</td>
                <td><span class="status-badge status-${claim.status}">${claim.status}</span></td>
                <td>
                    ${claim.status === 'pending' ? 
                        `<button class="action-btn view-btn" onclick="viewClaimDetails(${claim.id})">
                            <i class="fas fa-info-circle"></i> Details
                        </button>
                        <button class="action-btn edit-btn" onclick="completeClaim(${claim.id})">
                            <i class="fas fa-check"></i> Complete
                        </button>` : 
                        `<button class="action-btn view-btn" onclick="viewClaimDetails(${claim.id})">
                            <i class="fas fa-info-circle"></i> Details
                        </button>`}
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading claims:', error);
    }
}

// Function to complete a claim
async function completeClaim(claimId) {
    if (!confirm('Mark this claim as completed?')) return;
    
    try {
        const response = await fetch(`/api/claims/${claimId}/complete`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to complete claim');
        }
        
        loadUserClaims();
    } catch (error) {
        alert(error.message);
    }
}

// Function to view claim details
function viewClaimDetails(claimId) {
    // In a real app, you would show a modal with full details
    alert('Showing claim details for ID: ' + claimId);
}

// Update your existing claim button event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Load claims when dashboard loads
    if (window.location.pathname.includes('dashboard')) {
        loadUserClaims();
    }
    
    // Update existing claim buttons
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('claim-btn')) {
            const listingId = e.target.getAttribute('data-id');
            claimFood(listingId);
        }
    });
});
// Display listings in the grid (unchanged from your original)
// ... Keep your existing displayListings and handleClaimFood code
