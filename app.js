// app.js
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'https://www.gstatic.com/firebasejs/9.0.0/firebase-auth.js';

// Your Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBgYQWr4X03PCz1Qz3-fHzSjjqvD2I16ZM",
    authDomain: "wavelly-c1bb1.firebaseapp.com",
    projectId: "wavelly-c1bb1",
    storageBucket: "wavelly-c1bb1.appspot.com",
    messagingSenderId: "577295200107",
    appId: "1:577295200107:web:d00ad29fb8b193715ba62e",
    measurementId: "G-QZ9GR8CKCR"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();


// Initialize the Google Auth provider
document.getElementById('google-sign-in').addEventListener('click', function() {
    auth.signInWithPopup(provider)
        .then((result) => {
            // Signed in successfully
            console.log('User signed in with Google:', result.user);
        })
        .catch((error) => {
            console.error('Error signing in with Google:', error.message);
        });
});

document.getElementById('sign-up-form')?.addEventListener('submit', function(event) {
    event.preventDefault();
    const email = document.getElementById('sign-up-email').value;
    const password = document.getElementById('sign-up-password').value;

    auth.createUserWithEmailAndPassword(email, password)
        .then((userCredential) => {
            // Signed up successfully
            console.log('User signed up:', userCredential.user);
        })
        .catch((error) => {
            console.error('Error signing up:', error.message);
        });
});

document.getElementById('sign-in-form')?.addEventListener('submit', function(event) {
    event.preventDefault();
    const email = document.getElementById('sign-in-email').value;
    const password = document.getElementById('sign-in-password').value;

    auth.signInWithEmailAndPassword(email, password)
        .then((userCredential) => {
            // Signed in successfully
            console.log('User signed in:', userCredential.user);
        })
        .catch((error) => {
            console.error('Error signing in:', error.message);
        });
});