import os
import textwrap
import zipfile
import io

print("Preparing to create the NovaMint project ZIP file with API key included...")

# The Pexels API key you provided.
PEXELS_API_KEY_PROVIDED = "VbYkAgxmlS6UC5iKjNBd9DHoa99WfRvQPaRGvg7yREPRywkfA3InWu2T"

# A dictionary where keys are the file paths inside the zip
# and values are the file content.
project_files = {
    # --- Backend Files ---
    "novamint-enhanced/backend/app.py": """
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    from dotenv import load_dotenv
    import os
    import requests
    import base64
    from fpdf import FPDF

    # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__)
    CORS(app)  # Allow frontend to communicate with this backend

    # --- Configuration ---
    STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY") # <-- NEW API KEY

    if not STABILITY_API_KEY:
        print("WARNING: STABILITY_API_KEY not found. 'Create NFT with AI' will not work.")
    if not PEXELS_API_KEY:
        print("WARNING: PEXELS_API_KEY not found. Dashboard image generation will not work.")

    CONTRACTS_DIR = "contracts"
    TRANSACTIONS_DIR = "transactions"
    os.makedirs(CONTRACTS_DIR, exist_ok=True)
    os.makedirs(TRANSACTIONS_DIR, exist_ok=True)


    @app.route('/api/generate-ai-image', methods=['POST'])
    def generate_ai_image():
        if not STABILITY_API_KEY:
            return jsonify({"error": "AI service is not configured on the server."}), 500

        data = request.get_json()
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        api_host = 'https://api.stability.ai'
        engine_id = "stable-diffusion-v1-6"

        try:
            response = requests.post(
                f"{api_host}/v1/generation/{engine_id}/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {STABILITY_API_KEY}"
                },
                json={
                    "text_prompts": [{"text": prompt}],
                    "cfg_scale": 7, "height": 512, "width": 512, "samples": 1, "steps": 30,
                },
            )
            response.raise_for_status()
            response_data = response.json()
            image_b64 = response_data["artifacts"][0]["base64"]
            image_data_url = f"data:image/png;base64,{image_b64}"
            return jsonify({"imageDataUrl": image_data_url})
        except Exception as e:
            print(f"AI Generation Error: {e}")
            return jsonify({"error": "Failed to generate AI image."}), 500

    # --- NEW ENDPOINT FOR DASHBOARD IMAGE GENERATION ---
    @app.route('/api/generate-dashboard-image', methods=['POST'])
    def generate_dashboard_image():
        if not PEXELS_API_KEY:
            return jsonify({"error": "Image generation service is not configured."}), 500

        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({"error": "A prompt is required."}), 400

        try:
            headers = {"Authorization": PEXELS_API_KEY}
            url = f"https://api.pexels.com/v1/search?query={prompt}&per_page=1"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            pexels_data = response.json()
            if not pexels_data.get("photos"):
                return jsonify({"error": "No images found for that prompt."}), 404
                
            # Get the URL of the medium-sized photo
            image_url = pexels_data["photos"][0]["src"]["medium"]
            return jsonify({"imageUrl": image_url})

        except Exception as e:
            print(f"Pexels API Error: {e}")
            return jsonify({"error": "Failed to fetch image from Pexels."}), 500


    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'NovaMint Document', 0, 1, 'C')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    @app.route('/api/save-contract', methods=['POST'])
    def save_contract():
        data = request.get_json()
        filename = data.get('filename', 'contract.sol')
        code = data.get('code', '')
        if not code: return jsonify({"error": "Contract code is required"}), 400
        
        pdf_filename = filename.replace('.sol', '.pdf')
        safe_filename = "".join([c for c in pdf_filename if c.isalpha() or c.isdigit() or c in ('.','_')]).rstrip()
        filepath = os.path.join(CONTRACTS_DIR, safe_filename)

        try:
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Courier", size=10)
            pdf.multi_cell(0, 5, txt=code)
            pdf.output(filepath)
            return jsonify({"message": f"Contract saved as {safe_filename} in the backend."})
        except Exception as e:
            print(f"PDF Generation Error: {e}")
            return jsonify({"error": "Failed to save contract as PDF."}), 500

    @app.route('/api/record-transaction', methods=['POST'])
    def record_transaction():
        data = request.get_json()
        nft_name = data.get('nftName', 'Unknown NFT')
        buyer_info = data.get('buyerInfo', 'Unknown Buyer')
        timestamp = data.get('timestamp', 'N/A')

        receipt_content = (
            f"--- NovaMint Transaction Receipt ---\\n\\n"
            f"Item: {nft_name}\\n"
            f"Buyer: {buyer_info}\\n"
            f"Date: {timestamp}\\n\\n"
            f"This document certifies the simulated purchase of the above NFT.\\n"
            f"This is for demonstration purposes only."
        )
        safe_filename = f"receipt_{nft_name.replace(' ', '_')}_{str(timestamp).replace(':', '-')}.pdf"
        filepath = os.path.join(TRANSACTIONS_DIR, safe_filename)

        try:
            pdf = PDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=receipt_content)
            pdf.output(filepath)
            return jsonify({"message": f"Transaction receipt saved as {safe_filename}."})
        except Exception as e:
            print(f"Receipt Generation Error: {e}")
            return jsonify({"error": "Failed to generate transaction receipt."}), 500

    if __name__ == '__main__':
        print("Starting NovaMint backend server on http://127.0.0.1:5001")
        app.run(host='0.0.0.0', port=5001, debug=True)
    """,

    "novamint-enhanced/backend/requirements.txt": """
    Flask
    Flask-Cors
    python-dotenv
    requests
    fpdf
    """,

    # The .env file now includes the key you provided.
    "novamint-enhanced/backend/.env": f"""
    # You can get a Stability AI key from https://platform.stability.ai/
    STABILITY_API_KEY="YOUR_STABILITY_AI_API_KEY_HERE"

    # Pexels API Key for dashboard image generation
    PEXELS_API_KEY="{PEXELS_API_KEY_PROVIDED}"
    """,

    # --- Frontend Files ---
    "novamint-enhanced/frontend/index.html": """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to NovaMint</title>
        <link rel="stylesheet" href="assets/css/style.css">
    </head>
    <body>
        <div class="auth-wrapper">
            <div class="auth-box">
                <h1 id="formTitle">Login to <span>NovaMint</span></h1>
                <div id="errorMessage" class="error-message"></div>
                <div id="metamaskInstallPrompt" class="metamask-install-prompt" style="display: none;">
                    <p><strong>Metamask Wallet Not Detected!</strong></p>
                    <p>To interact with NovaMint, you need the Metamask browser extension.</p>
                    <a href="https://metamask.io/download/" target="_blank" rel="noopener noreferrer">Install Metamask</a>
                </div>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="loginEmail">Email</label>
                        <input type="email" id="loginEmail" required>
                    </div>
                    <div class="form-group">
                        <label for="loginPassword">Password</label>
                        <input type="password" id="loginPassword" required>
                    </div>
                    <button type="submit" class="auth-button">Login</button>
                </form>
                <form id="signupForm" style="display: none;">
                    <div class="form-group">
                        <label for="signupName">Full Name</label>
                        <input type="text" id="signupName" required>
                    </div>
                    <div class="form-group">
                        <label for="signupEmail">Email</label>
                        <input type="email" id="signupEmail" required>
                    </div>
                    <div class="form-group">
                        <label for="signupPassword">Password</label>
                        <input type="password" id="signupPassword" required>
                    </div>
                    <div class="form-group">
                        <label for="signupMetamask">Metamask Address (Optional)</label>
                        <input type="text" id="signupMetamask" placeholder="0x...">
                    </div>
                    <button type="submit" class="auth-button">Sign Up</button>
                </form>
                <button id="connectMetamaskBtn" class="auth-button metamask-button">Login with Metamask</button>
                <p class="toggle-auth-link">
                    <span id="toggleMessage">Don't have an account? </span>
                    <a href="#" id="toggleLink">Sign Up</a>
                </p>
            </div>
        </div>
        <script>
            const loginForm = document.getElementById('loginForm');
            const signupForm = document.getElementById('signupForm');
            const formTitle = document.getElementById('formTitle');
            const toggleMessage = document.getElementById('toggleMessage');
            const toggleLink = document.getElementById('toggleLink');
            const connectMetamaskBtn = document.getElementById('connectMetamaskBtn');
            const errorMessageDiv = document.getElementById('errorMessage');
            const metamaskInstallPrompt = document.getElementById('metamaskInstallPrompt');
            const USERS_DB_KEY = 'novaMintUsers';
            const CURRENT_USER_KEY = 'novaMintCurrentUser';
            if (!localStorage.getItem(USERS_DB_KEY)) {
                localStorage.setItem(USERS_DB_KEY, JSON.stringify([]));
            }
            function displayError(message) { errorMessageDiv.textContent = message; }
            function clearError() { errorMessageDiv.textContent = ''; }
            function getUsers() { return JSON.parse(localStorage.getItem(USERS_DB_KEY)); }
            function saveUsers(users) { localStorage.setItem(USERS_DB_KEY, JSON.stringify(users)); }
            function setCurrentUser(user) {
                localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
                window.location.href = 'dashboard.html';
            }
            if (typeof window.ethereum === 'undefined') {
                if (metamaskInstallPrompt) metamaskInstallPrompt.style.display = 'block';
                if (connectMetamaskBtn) {
                    connectMetamaskBtn.disabled = true;
                    connectMetamaskBtn.style.opacity = '0.5';
                    connectMetamaskBtn.style.cursor = 'not-allowed';
                }
            }
            if (toggleLink) {
                toggleLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    clearError();
                    if (loginForm.style.display === 'none') {
                        loginForm.style.display = 'block';
                        signupForm.style.display = 'none';
                        formTitle.innerHTML = 'Login to <span>NovaMint</span>';
                        toggleMessage.textContent = "Don't have an account? ";
                        toggleLink.textContent = 'Sign Up';
                        if (connectMetamaskBtn) connectMetamaskBtn.textContent = 'Login with Metamask';
                    } else {
                        loginForm.style.display = 'none';
                        signupForm.style.display = 'block';
                        formTitle.innerHTML = 'Sign Up for <span>NovaMint</span>';
                        toggleMessage.textContent = 'Already have an account? ';
                        toggleLink.textContent = 'Login';
                        if (connectMetamaskBtn) connectMetamaskBtn.textContent = 'Sign Up with Metamask';
                    }
                });
            }
            if (loginForm) {
                loginForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    clearError();
                    const email = document.getElementById('loginEmail').value;
                    const password = document.getElementById('loginPassword').value;
                    const users = getUsers();
                    const user = users.find(u => u.email === email && u.password === password);
                    if (user) {
                        setCurrentUser(user);
                    } else {
                        displayError('Invalid email or password.');
                    }
                });
            }
            if (signupForm) {
                signupForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    clearError();
                    const name = document.getElementById('signupName').value.trim();
                    const email = document.getElementById('signupEmail').value.trim();
                    const password = document.getElementById('signupPassword').value;
                    const metamaskAddressInput = document.getElementById('signupMetamask').value.trim().toLowerCase();
                    if (!name || !email || !password) {
                        displayError('Name, Email, and Password are required.');
                        return;
                    }
                    const users = getUsers();
                    if (users.find(u => u.email === email)) {
                        displayError('An account with this email already exists.');
                        return;
                    }
                    if (metamaskAddressInput && metamaskAddressInput.length > 0 && users.find(u => u.metamaskAddress === metamaskAddressInput)) {
                        displayError('This Metamask address is already associated with an account.');
                        return;
                    }
                    const newUser = { name, email, password, metamaskAddress: metamaskAddressInput || null, profilePicDataUrl: null, bio: "" };
                    users.push(newUser);
                    saveUsers(users);
                    setCurrentUser(newUser);
                });
            }
            if (connectMetamaskBtn) {
                connectMetamaskBtn.addEventListener('click', async () => {
                    clearError();
                    if (typeof window.ethereum === 'undefined') {
                        if (metamaskInstallPrompt) metamaskInstallPrompt.style.display = 'block';
                        displayError('Please install Metamask to use this feature.');
                        return;
                    }
                    try {
                        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                        const connectedMetamaskAddress = accounts[0].toLowerCase();
                        const users = getUsers();
                        let user = users.find(u => u.metamaskAddress === connectedMetamaskAddress);
                        if (user) {
                            setCurrentUser(user);
                        } else {
                            let name, email;
                            if (signupForm.style.display !== 'none') {
                                name = document.getElementById('signupName').value.trim();
                                email = document.getElementById('signupEmail').value.trim();
                                if (!name || !email) {
                                    displayError('Please enter Name and Email on the form before signing up with Metamask, or switch to the Login view to auto-generate details.');
                                    return;
                                }
                                if (users.find(u => u.email === email)) {
                                    displayError('The email entered on the form is already registered. Try logging in or use a different email.');
                                    return;
                                }
                            } else {
                                name = `User ${connectedMetamaskAddress.substring(2, 8)}`;
                                let potentialEmail = `metamask-${connectedMetamaskAddress.substring(2, 8)}@novamint.io`;
                                let counter = 0;
                                while (users.find(u => u.email === potentialEmail)) {
                                    counter++;
                                    potentialEmail = `metamask-${connectedMetamaskAddress.substring(2, 8)}-${counter}@novamint.io`;
                                }
                                email = potentialEmail;
                            }
                            const newUser = { name: name, email: email, password: `metamask_pw_${Date.now()}`, metamaskAddress: connectedMetamaskAddress, profilePicDataUrl: null, bio: "" };
                            users.push(newUser);
                            saveUsers(users);
                            setCurrentUser(newUser);
                        }
                    } catch (error) {
                        console.error("Metamask connection error:", error);
                        if (error.code === 4001) {
                            displayError('Metamask connection request rejected.');
                        } else {
                            displayError('Error connecting to Metamask. See console for details.');
                        }
                    }
                });
            }
            if (localStorage.getItem(CURRENT_USER_KEY)) {
                window.location.href = 'dashboard.html';
            }
        </script>
    </body>
    </html>
    """,

    "novamint-enhanced/frontend/dashboard.html": """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - NovaMint</title>
        <link rel="stylesheet" href="assets/css/style.css">
    </head>
    <body>
        <header class="main-header">
            <div class="logo-container">
                <a href="dashboard.html" class="logo-text">Nova<span>Mint</span></a>
            </div>
            <nav class="nav-buttons">
                <a href="https://remix.ethereum.org/" target="_blank" class="header-action-button">Open Remix IDE</a>
                <button id="createNftBtnHeader" class="header-action-button">Create NFT with AI</button>
                <button id="mintNftBtnHeader" class="header-action-button" onclick="window.location.href='mint.html'">Mint NFT</button>
                <button id="uploadNftBtnHeader" class="header-action-button" onclick="window.location.href='upload.html'">Upload NFT</button>
            </nav>
            <div class="profile-area">
                <div id="profileAvatar" class="profile-avatar">?</div>
                <div id="profileDropdown" class="profile-dropdown">
                    <div class="profile-dropdown-item user-name" id="dropdownUserName">User Name</div>
                    <div class="profile-dropdown-item user-email" id="dropdownUserEmail">user@example.com</div>
                    <div class="profile-dropdown-item user-metamask" id="dropdownUserMetamask">Metamask: Not Linked</div>
                    <div class="profile-dropdown-item user-bio" id="dropdownUserBio"></div>
                    <hr>
                    <button class="profile-dropdown-button" id="editProfileBtn">Edit Profile</button>
                    <button class="profile-dropdown-button" id="logoutButton">Logout</button>
                </div>
            </div>
        </header>

        <main class="container dashboard-main">
            <h1 class="page-title" id="welcomeMessage">Welcome to <span>NovaMint</span></h1>

            <!-- NEW IMAGE GENERATION SECTION -->
            <section class="image-generation-section">
                <h2 class="section-title">🎨 Image Generation Tool</h2>
                <div class="form-page-container" style="max-width: none; padding: 1.5rem;">
                    <div class="form-group">
                        <label for="dashboardPrompt">Enter a prompt to generate an image (e.g., "tigers in the snow")</label>
                        <input type="text" id="dashboardPrompt" placeholder="Your image idea...">
                    </div>
                    <button id="dashboardGenerateBtn" class="submit-button" style="width: auto; padding: 0.8rem 1.5rem;">Generate Image</button>
                    <div id="dashboardImageResult" style="margin-top: 1.5rem; min-height: 50px;">
                        <p>Your generated image will appear here.</p>
                    </div>
                </div>
            </section>

            <section class="activity-feed-section">
                <h2 class="section-title">🌍 Global Activity</h2>
                <div id="globalActivityFeed" class="nft-grid">
                    <p style="color: var(--secondary-text);">No global activity yet.</p>
                </div>
            </section>
        </main>

        <div id="aiCreatePopupOverlay" class="popup-overlay">
            <div class="popup-content">
                <button class="popup-close-btn" id="closeAiPopupBtn">×</button>
                <h2>Create NFT with AI</h2>
                <div class="form-group">
                    <label for="aiPrompt">Describe your image (e.g., "a futuristic cat in space"):</label>
                    <input type="text" id="aiPrompt" placeholder="Enter your image idea...">
                </div>
                <div id="aiImageResultContainer">
                    <p>Enter a description and click "Generate Image".</p>
                </div>
                <button id="generateAiImageBtn" class="submit-button">Generate Image</button>
            </div>
        </div>

        <div id="editProfileModal" class="popup-overlay">
            <div class="popup-content">
                <button class="popup-close-btn" id="closeEditProfileModalBtn">×</button>
                <h2>Edit Your Profile</h2>
                <img id="profilePicPreview" src="" alt="Profile Preview" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 1rem;">
                <div class="form-group">
                    <label for="profilePicInput">Change Profile Picture</label>
                    <input type="file" id="profilePicInput" accept="image/*">
                </div>
                <div class="form-group">
                    <label for="profileNameInput">Full Name</label>
                    <input type="text" id="profileNameInput">
                </div>
                <div class="form-group">
                    <label for="profileBioInput">Bio (max 150 chars)</label>
                    <textarea id="profileBioInput" rows="3" maxlength="150"></textarea>
                </div>
                <button id="saveProfileChangesBtn" class="submit-button">Save Changes</button>
            </div>
        </div>

        <script>
            const CURRENT_USER_KEY = 'novaMintCurrentUser';
            const USERS_DB_KEY = 'novaMintUsers';
            const GLOBAL_ACTIVITY_KEY = 'novaMintGlobalActivity';
            const BACKEND_URL = 'http://127.0.0.1:5001';
            let newProfilePicDataUrl = null;

            const profileAvatar = document.getElementById('profileAvatar');
            const profileDropdown = document.getElementById('profileDropdown');
            const dropdownUserName = document.getElementById('dropdownUserName');
            const dropdownUserEmail = document.getElementById('dropdownUserEmail');
            const dropdownUserMetamask = document.getElementById('dropdownUserMetamask');
            const dropdownUserBio = document.getElementById('dropdownUserBio');
            const editProfileBtn = document.getElementById('editProfileBtn');
            const logoutButton = document.getElementById('logoutButton');
            const welcomeMessage = document.getElementById('welcomeMessage');
            const globalActivityFeed = document.getElementById('globalActivityFeed');
            const aiCreatePopupOverlay = document.getElementById('aiCreatePopupOverlay');
            const closeAiPopupBtn = document.getElementById('closeAiPopupBtn');
            const aiPromptInput = document.getElementById('aiPrompt');
            const aiImageResultContainer = document.getElementById('aiImageResultContainer');
            const generateAiImageBtn = document.getElementById('generateAiImageBtn');
            const createNftBtnHeader = document.getElementById('createNftBtnHeader');
            const dashboardPromptInput = document.getElementById('dashboardPrompt');
            const dashboardGenerateBtn = document.getElementById('dashboardGenerateBtn');
            const dashboardImageResult = document.getElementById('dashboardImageResult');
            const editProfileModal = document.getElementById('editProfileModal');
            const closeEditProfileModalBtn = document.getElementById('closeEditProfileModalBtn');
            const profilePicPreview = document.getElementById('profilePicPreview');
            const profilePicInput = document.getElementById('profilePicInput');
            const profileNameInput = document.getElementById('profileNameInput');
            const profileBioInput = document.getElementById('profileBioInput');
            const saveProfileChangesBtn = document.getElementById('saveProfileChangesBtn');

            function getCurrentUser() { return JSON.parse(localStorage.getItem(CURRENT_USER_KEY)); }
            function logout() { localStorage.removeItem(CURRENT_USER_KEY); window.location.href = 'index.html'; }
            function updateProfileDisplay(user) {
                if (!user) return;
                if (user.profilePicDataUrl) {
                    profileAvatar.innerHTML = `<img src="${user.profilePicDataUrl}" alt="${user.name?.[0]}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
                } else {
                    profileAvatar.textContent = user.name ? user.name[0].toUpperCase() : (user.email ? user.email[0].toUpperCase() : 'U');
                }
                dropdownUserName.textContent = user.name || "N/A";
                dropdownUserEmail.textContent = user.email || "N/A";
                dropdownUserMetamask.textContent = user.metamaskAddress ? `Metamask: ${user.metamaskAddress.substring(0,10)}...` : "Metamask: Not Linked";
                dropdownUserBio.textContent = user.bio || "No bio yet.";
                welcomeMessage.innerHTML = `Welcome, <span>${user.name || user.email?.split('@')[0]}</span>!`;
            }
            function displayActivityItem(item, feedElement) {
                const card = document.createElement('div');
                card.classList.add('activity-card');
                const imageHtml = (item.imageDataUrl || item.assetDataUrl) ? `<div class="activity-card-image"><img src="${item.imageDataUrl || item.assetDataUrl}" alt="${item.name}"></div>` : '';
                card.innerHTML = `${imageHtml}<h3 class="activity-card-title">${item.name}</h3><p class="activity-card-details">By: ${item.uploaderName || 'Unknown'}</p><p class="activity-card-details">Date: ${new Date(item.timestamp).toLocaleDateString()}</p><p class="activity-card-type">${item.type || 'Item'}</p><button class="buy-button" data-nft-name="${item.name}">Buy (Simulated)</button>`;
                feedElement.appendChild(card);
            }
            function loadActivityFeed() {
                const allActivity = JSON.parse(localStorage.getItem(GLOBAL_ACTIVITY_KEY)) || [];
                globalActivityFeed.innerHTML = '';
                if (allActivity.length === 0) {
                    globalActivityFeed.innerHTML = '<p style="color: var(--secondary-text); grid-column: 1 / -1;">No global activity yet.</p>';
                } else {
                    allActivity.slice().reverse().forEach(item => displayActivityItem(item, globalActivityFeed));
                }
            }
            async function handleBuyClick(event) {
                const button = event.target;
                if (!button.classList.contains('buy-button')) return;
                const nftName = button.dataset.nftName;
                const currentUser = getCurrentUser();
                button.textContent = 'Processing...';
                button.disabled = true;
                try {
                    const response = await fetch(`${BACKEND_URL}/api/record-transaction`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nftName: nftName, buyerInfo: `${currentUser.name} (${currentUser.email})`, timestamp: new Date().toISOString() })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Failed to record transaction');
                    alert(`Purchase simulated! Receipt PDF generated on the backend: ${result.message}`);
                } catch (error) {
                    console.error('Buy Error:', error);
                    alert(`Error during purchase simulation: ${error.message}`);
                } finally {
                    button.textContent = 'Buy (Simulated)';
                    button.disabled = false;
                }
            }
            async function handleAIGeneration() {
                const prompt = aiPromptInput.value.trim();
                if (!prompt) {
                    aiImageResultContainer.innerHTML = '<p style="color: var(--error-color);">Please enter a prompt.</p>';
                    return;
                }
                generateAiImageBtn.textContent = 'Generating...';
                generateAiImageBtn.disabled = true;
                aiImageResultContainer.innerHTML = '<p>Contacting AI... please wait.</p>';
                try {
                    const response = await fetch(`${BACKEND_URL}/api/generate-ai-image`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: prompt })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Unknown error from AI service');
                    aiImageResultContainer.innerHTML = `<img src="${result.imageDataUrl}" alt="AI Generated Image for ${prompt}" style="max-width: 100%; border-radius: 4px;"><p>Image generated! You can right-click to save this image and use it on the Mint or Upload pages.</p>`;
                } catch (error) {
                    console.error('AI Generation Error:', error);
                    aiImageResultContainer.innerHTML = `<p style="color: var(--error-color);">Error: ${error.message}</p>`;
                } finally {
                    generateAiImageBtn.textContent = 'Generate Image';
                    generateAiImageBtn.disabled = false;
                }
            }
            async function handleDashboardImageGeneration() {
                const prompt = dashboardPromptInput.value.trim();
                if (!prompt) {
                    dashboardImageResult.innerHTML = '<p style="color: var(--error-color);">Please enter a prompt.</p>';
                    return;
                }
                dashboardGenerateBtn.textContent = 'Generating...';
                dashboardGenerateBtn.disabled = true;
                dashboardImageResult.innerHTML = '<p>Fetching image...</p>';
                try {
                    const response = await fetch(`${BACKEND_URL}/api/generate-dashboard-image`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: prompt })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Unknown error from image service');
                    dashboardImageResult.innerHTML = `<img src="${result.imageUrl}" alt="Image for ${prompt}" style="max-width: 100%; max-height: 400px; border-radius: 4px;">`;
                } catch (error) {
                    console.error('Dashboard Image Generation Error:', error);
                    dashboardImageResult.innerHTML = `<p style="color: var(--error-color);">Error: ${error.message}</p>`;
                } finally {
                    dashboardGenerateBtn.textContent = 'Generate Image';
                    dashboardGenerateBtn.disabled = false;
                }
            }
            document.addEventListener('DOMContentLoaded', () => {
                const currentUser = getCurrentUser();
                if (!currentUser) { window.location.href = 'index.html'; return; }
                updateProfileDisplay(currentUser);
                loadActivityFeed();
                profileAvatar.addEventListener('click', (e) => { e.stopPropagation(); profileDropdown.style.display = profileDropdown.style.display === 'block' ? 'none' : 'block'; });
                document.addEventListener('click', (e) => { if (!profileAvatar.contains(e.target) && !profileDropdown.contains(e.target)) { profileDropdown.style.display = 'none'; } });
                logoutButton.addEventListener('click', logout);
                globalActivityFeed.addEventListener('click', handleBuyClick);
                createNftBtnHeader.addEventListener('click', () => aiCreatePopupOverlay.style.display = 'flex');
                closeAiPopupBtn.addEventListener('click', () => aiCreatePopupOverlay.style.display = 'none');
                generateAiImageBtn.addEventListener('click', handleAIGeneration);
                dashboardGenerateBtn.addEventListener('click', handleDashboardImageGeneration);
                editProfileBtn.addEventListener('click', () => {
                    const user = getCurrentUser();
                    profileNameInput.value = user.name || '';
                    profileBioInput.value = user.bio || '';
                    profilePicPreview.src = user.profilePicDataUrl || 'assets/images/avatar_placeholder.png';
                    newProfilePicDataUrl = user.profilePicDataUrl;
                    editProfileModal.style.display = 'flex';
                });
                closeEditProfileModalBtn.addEventListener('click', () => editProfileModal.style.display = 'none');
                profilePicInput.addEventListener('change', (event) => {
                    const file = event.target.files[0];
                    if (file) {
                        const reader = new FileReader();
                        reader.onload = (e) => { newProfilePicDataUrl = e.target.result; profilePicPreview.src = newProfilePicDataUrl; };
                        reader.readAsDataURL(file);
                    }
                });
                saveProfileChangesBtn.addEventListener('click', () => {
                    let user = getCurrentUser();
                    user.name = profileNameInput.value.trim();
                    user.bio = profileBioInput.value.trim();
                    user.profilePicDataUrl = newProfilePicDataUrl;
                    let users = JSON.parse(localStorage.getItem(USERS_DB_KEY)) || [];
                    const userIndex = users.findIndex(u => u.email === user.email);
                    if (userIndex > -1) { users[userIndex] = user; localStorage.setItem(USERS_DB_KEY, JSON.stringify(users)); }
                    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
                    updateProfileDisplay(user);
                    editProfileModal.style.display = 'none';
                });
            });
        </script>
    </body>
    </html>
    """,

    "novamint-enhanced/frontend/mint.html": """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mint NFT - NovaMint</title>
        <link rel="stylesheet" href="assets/css/style.css">
    </head>
    <body>
        <header class="main-header">
            <div class="logo-container">
                <a href="dashboard.html" class="logo-text">Nova<span>Mint</span></a>
            </div>
            <nav class="nav-buttons">
                <a href="dashboard.html" class="header-action-button">Dashboard</a>
            </nav>
        </header>
        <main class="container">
            <div class="form-page-container">
                <h1>Define & Mint New NFT</h1>
                <form id="mintForm">
                    <div class="form-group">
                        <label for="nftNameMint">NFT Collection/Item Name</label>
                        <input type="text" id="nftNameMint" required>
                    </div>
                    <div class="form-group">
                        <label for="nftDescriptionMint">Description (Optional)</label>
                        <textarea id="nftDescriptionMint" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="nftImageMint">NFT Asset (Image, GIF, etc.)</label>
                        <input type="file" id="nftImageMint" accept="image/*" required>
                    </div>
                    <button type="submit" class="submit-button">Define & Generate Contract</button>
                </form>
                <div id="solidityCodeContainerMint" class="solidity-code-box" style="display:none;">
                    <h3>Generated Solidity Contract (ERC721 Template)</h3>
                    <pre id="solidityCodeOutputMint"></pre>
                    <button id="savePdfButton" class="submit-button download-sol-button">Save Contract as PDF</button>
                    <p style="font-size:0.8em; color: var(--secondary-text); margin-top:10px;">
                        This will save a PDF of the contract code to the backend server.
                    </p>
                </div>
            </div>
        </main>
        <script>
            const CURRENT_USER_KEY_PAGE = 'novaMintCurrentUser';
            const GLOBAL_ACTIVITY_KEY = 'novaMintGlobalActivity';
            const BACKEND_URL = 'http://127.0.0.1:5001';
            let currentUser;
            document.addEventListener('DOMContentLoaded', () => {
                const userJson = localStorage.getItem(CURRENT_USER_KEY_PAGE);
                if (!userJson) {
                    alert("You need to be logged in to access this page.");
                    window.location.href = 'index.html';
                    return;
                }
                currentUser = JSON.parse(userJson);
            });
            const mintForm = document.getElementById('mintForm');
            const solidityCodeContainerMint = document.getElementById('solidityCodeContainerMint');
            const solidityCodeOutputMint = document.getElementById('solidityCodeOutputMint');
            const savePdfButton = document.getElementById('savePdfButton');
            mintForm.addEventListener('submit', function(event) {
                event.preventDefault();
                const name = document.getElementById('nftNameMint').value.trim();
                const description = document.getElementById('nftDescriptionMint').value.trim();
                const assetFile = document.getElementById('nftImageMint').files[0];
                if (!name || !assetFile) {
                    alert('Please provide NFT name and an asset file.');
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(e) {
                    const newActivityItem = {
                        type: 'mint',
                        name: name,
                        description: description,
                        assetName: assetFile.name,
                        assetDataUrl: e.target.result,
                        timestamp: Date.now(),
                        uploaderEmail: currentUser.email,
                        uploaderName: currentUser.name
                    };
                    const globalActivity = JSON.parse(localStorage.getItem(GLOBAL_ACTIVITY_KEY)) || [];
                    globalActivity.push(newActivityItem);
                    localStorage.setItem(GLOBAL_ACTIVITY_KEY, JSON.stringify(globalActivity));
                    const contractCode = generateSolidityContractForMint(name, assetFile.name, description, Math.floor(Date.now() / 1000));
                    solidityCodeOutputMint.textContent = contractCode;
                    solidityCodeContainerMint.style.display = 'block';
                    alert('NFT Mint definition added to global feed and Solidity contract generated!');
                };
                reader.readAsDataURL(assetFile);
            });
            savePdfButton.addEventListener('click', async () => {
                const code = solidityCodeOutputMint.textContent;
                const nftName = document.getElementById('nftNameMint').value.trim();
                const contractFileName = `${nftName.replace(/[^a-zA-Z0-9]/g, '_') || 'NFT'}_Collection.sol`;
                savePdfButton.textContent = 'Saving...';
                savePdfButton.disabled = true;
                try {
                    const response = await fetch(`${BACKEND_URL}/api/save-contract`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: contractFileName, code: code })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Failed to save contract');
                    alert(result.message);
                } catch (error) {
                    console.error('Save PDF Error:', error);
                    alert(`Error saving contract: ${error.message}`);
                } finally {
                    savePdfButton.textContent = 'Save Contract as PDF';
                    savePdfButton.disabled = false;
                }
            });
            function generateSolidityContractForMint(nftName, assetName, description, timestamp) {
                const contractNftName = nftName.replace(/[^a-zA-Z0-9_]/g, '').replace(/\\s+/g, '') || "MyNFTCollection";
                const descriptionComment = description ? `    // Description: ${description.replace(/\\n/g, '\\n//              ')}\\n` : '';
                return `// SPDX-License-Identifier: MIT\\npragma solidity ^0.8.20;\\nimport "@openzeppelin/contracts/token/ERC721/ERC721.sol";\\nimport "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";\\nimport "@openzeppelin/contracts/access/Ownable.sol";\\nimport "@openzeppelin/contracts/utils/Counters.sol";\\n\\ncontract ${contractNftName} is ERC721, ERC721URIStorage, Ownable {\\n    using Counters for Counters.Counter;\\n    Counters.Counter private _tokenIdCounter;\\n    string public constant collectionName = "${nftName}";\\n${descriptionComment}    string public constant defaultAssetName = "${assetName}";\\n    uint256 public constant creationTimestamp = ${timestamp};\\n\\n    constructor(address initialOwner)\\n        ERC721("${nftName}", "${contractNftName.substring(0,4).toUpperCase()}") Ownable(initialOwner) {}\\n\\n    function mintNFT(address recipient, string memory tokenURI) public onlyOwner returns (uint256) {\\n        _tokenIdCounter.increment();\\n        uint256 newItemId = _tokenIdCounter.current();\\n        _safeMint(recipient, newItemId);\\n        _setTokenURI(newItemId, tokenURI);\\n        return newItemId;\\n    }\\n    function _update(address to, uint256 tokenId, address auth) internal override(ERC721, ERC721URIStorage) returns (address) { return super._update(to, tokenId, auth); }\\n    function _increaseBalance(address account, uint128 amount) internal override(ERC721, ERC721URIStorage) { super._increaseBalance(account, amount); }\\n    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) { return super.tokenURI(tokenId); }\\n    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage) returns (bool) { return super.supportsInterface(interfaceId); }\\n    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) { super._burn(tokenId); }\\n}`;
            }
        </script>
    </body>
    </html>
    """,

    "novamint-enhanced/frontend/upload.html": """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload NFT - NovaMint</title>
        <link rel="stylesheet" href="assets/css/style.css">
    </head>
    <body>
        <header class="main-header">
            <div class="logo-container">
                <a href="dashboard.html" class="logo-text">Nova<span>Mint</span></a>
            </div>
            <nav class="nav-buttons">
                <a href="dashboard.html" class="header-action-button">Dashboard</a>
            </nav>
        </header>
        <main class="container">
            <div class="form-page-container">
                <h1>Upload Your NFT</h1>
                <form id="uploadForm">
                    <div class="form-group">
                        <label for="nftName">NFT Name</label>
                        <input type="text" id="nftName" required>
                    </div>
                    <div class="form-group">
                        <label for="nftImage">NFT Picture (Image File)</label>
                        <input type="file" id="nftImage" accept="image/*" required>
                    </div>
                    <button type="submit" class="submit-button">Upload & Generate Contract</button>
                </form>
                <div id="solidityCodeContainer" class="solidity-code-box" style="display:none;">
                    <h3>Generated Solidity Contract (ERC721 Template)</h3>
                    <pre id="solidityCodeOutput"></pre>
                    <button id="savePdfButton" class="submit-button download-sol-button">Save Contract as PDF</button>
                     <p style="font-size:0.8em; color: var(--secondary-text); margin-top:10px;">
                        This will save a PDF of the contract code to the backend server.
                    </p>
                </div>
            </div>
        </main>
        <script>
            const CURRENT_USER_KEY_PAGE = 'novaMintCurrentUser';
            const GLOBAL_ACTIVITY_KEY = 'novaMintGlobalActivity';
            const BACKEND_URL = 'http://127.0.0.1:5001';
            let currentUser;
            document.addEventListener('DOMContentLoaded', () => {
                const userJson = localStorage.getItem(CURRENT_USER_KEY_PAGE);
                if (!userJson) {
                    alert("You need to be logged in to access this page.");
                    window.location.href = 'index.html';
                    return;
                }
                currentUser = JSON.parse(userJson);
            });
            const uploadForm = document.getElementById('uploadForm');
            const solidityCodeContainer = document.getElementById('solidityCodeContainer');
            const solidityCodeOutput = document.getElementById('solidityCodeOutput');
            const savePdfButton = document.getElementById('savePdfButton');
            uploadForm.addEventListener('submit', function(event) {
                event.preventDefault();
                const name = document.getElementById('nftName').value.trim();
                const imageFile = document.getElementById('nftImage').files[0];
                if (!name || !imageFile) {
                    alert('Please provide both NFT name and an image file.');
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(e) {
                    const newActivityItem = {
                        type: 'upload',
                        name: name,
                        imageName: imageFile.name,
                        imageDataUrl: e.target.result,
                        timestamp: Date.now(),
                        uploaderEmail: currentUser.email,
                        uploaderName: currentUser.name
                    };
                    const globalActivity = JSON.parse(localStorage.getItem(GLOBAL_ACTIVITY_KEY)) || [];
                    globalActivity.push(newActivityItem);
                    localStorage.setItem(GLOBAL_ACTIVITY_KEY, JSON.stringify(globalActivity));
                    const contractCode = generateSolidityContract(name, imageFile.name, Math.floor(Date.now() / 1000));
                    solidityCodeOutput.textContent = contractCode;
                    solidityCodeContainer.style.display = 'block';
                    alert('NFT uploaded to global feed and Solidity contract generated!');
                };
                reader.readAsDataURL(imageFile);
            });
            savePdfButton.addEventListener('click', async () => {
                const code = solidityCodeOutput.textContent;
                const nftName = document.getElementById('nftName').value.trim();
                const contractFileName = `${nftName.replace(/[^a-zA-Z0-9]/g, '_') || 'NFT'}_Contract.sol`;
                savePdfButton.textContent = 'Saving...';
                savePdfButton.disabled = true;
                try {
                    const response = await fetch(`${BACKEND_URL}/api/save-contract`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename: contractFileName, code: code })
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Failed to save contract');
                    alert(result.message);
                } catch (error) {
                    console.error('Save PDF Error:', error);
                    alert(`Error saving contract: ${error.message}`);
                } finally {
                    savePdfButton.textContent = 'Save Contract as PDF';
                    savePdfButton.disabled = false;
                }
            });
            function generateSolidityContract(nftName, imageName, timestamp) {
                const contractNftName = nftName.replace(/[^a-zA-Z0-9_]/g, '').replace(/\\s+/g, '') || "MyNFT";
                return `// SPDX-License-Identifier: MIT\\npragma solidity ^0.8.20;\\nimport "@openzeppelin/contracts/token/ERC721/ERC721.sol";\\nimport "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";\\nimport "@openzeppelin/contracts/access/Ownable.sol";\\nimport "@openzeppelin/contracts/utils/Counters.sol";\\n\\ncontract ${contractNftName} is ERC721, ERC721URIStorage, Ownable {\\n    using Counters for Counters.Counter;\\n    Counters.Counter private _tokenIdCounter;\\n    string public constant nftCollectionName = "${nftName}";\\n    string public constant nftImageReference = "${imageName}";\\n    uint256 public constant creationTimestamp = ${timestamp};\\n\\n    constructor(address initialOwner)\\n        ERC721("${nftName}", "${contractNftName.substring(0,4).toUpperCase()}") Ownable(initialOwner) {}\\n\\n    function safeMint(address to, string memory uri) public onlyOwner returns (uint256) {\\n        _tokenIdCounter.increment();\\n        uint256 newItemId = _tokenIdCounter.current();\\n        _safeMint(to, newItemId);\\n        _setTokenURI(newItemId, uri);\\n        return newItemId;\\n    }\\n    function _update(address to, uint256 tokenId, address auth) internal override(ERC721, ERC721URIStorage) returns (address) { return super._update(to, tokenId, auth); }\\n    function _increaseBalance(address account, uint128 amount) internal override(ERC721, ERC721URIStorage) { super._increaseBalance(account, amount); }\\n    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) { return super.tokenURI(tokenId); }\\n    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage) returns (bool) { return super.supportsInterface(interfaceId); }\\n    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) { super._burn(tokenId); }\\n}`;
            }
        </script>
    </body>
    </html>
    """,
    
    "novamint-enhanced/frontend/assets/css/style.css": """
    /* A basic, clean stylesheet to make the app usable */
    :root {
        --primary-bg: #121212;
        --secondary-bg: #1e1e1e;
        --primary-text: #e0e0e0;
        --secondary-text: #b3b3b3;
        --accent-color: #4a90e2;
        --accent-hover: #6aa3e9;
        --error-color: #e24a4a;
        --border-color: #333;
    }
    body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: var(--primary-bg);
        color: var(--primary-text);
    }
    .auth-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
    }
    .auth-box {
        background-color: var(--secondary-bg);
        padding: 2rem;
        border-radius: 8px;
        width: 100%;
        max-width: 400px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .auth-box h1 { text-align: center; margin-bottom: 1.5rem; }
    .auth-box h1 span { color: var(--accent-color); }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; margin-bottom: 0.5rem; color: var(--secondary-text); }
    .form-group input, .form-group textarea {
        width: 100%;
        padding: 0.75rem;
        background-color: var(--primary-bg);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        color: var(--primary-text);
        font-size: 1rem;
        box-sizing: border-box;
    }
    .auth-button, .submit-button {
        width: 100%;
        padding: 0.8rem;
        border: none;
        border-radius: 4px;
        background-color: var(--accent-color);
        color: white;
        font-size: 1.1rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .auth-button:hover, .submit-button:hover { background-color: var(--accent-hover); }
    .metamask-button { margin-top: 1rem; background-color: #f6851b; }
    .metamask-button:hover { background-color: #e76f0a; }
    .toggle-auth-link { text-align: center; margin-top: 1.5rem; color: var(--secondary-text); }
    .toggle-auth-link a { color: var(--accent-color); text-decoration: none; font-weight: bold; }
    .error-message { color: var(--error-color); text-align: center; margin-bottom: 1rem; min-height: 1.2em; }
    .main-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 2rem; background-color: var(--secondary-bg); }
    .logo-text { font-size: 1.8rem; font-weight: bold; text-decoration: none; color: var(--primary-text); }
    .logo-text span { color: var(--accent-color); }
    .nav-buttons { display: flex; gap: 1rem; }
    .header-action-button {
        padding: 0.6rem 1.2rem;
        background-color: transparent;
        border: 1px solid var(--accent-color);
        color: var(--accent-color);
        border-radius: 5px;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.2s;
    }
    .header-action-button:hover { background-color: var(--accent-color); color: white; }
    .profile-area { position: relative; }
    .profile-avatar {
        width: 40px; height: 40px; border-radius: 50%; background-color: var(--accent-color);
        display: flex; justify-content: center; align-items: center; font-size: 1.5rem; font-weight: bold; cursor: pointer;
    }
    .profile-dropdown {
        display: none; position: absolute; right: 0; top: 50px; background-color: var(--secondary-bg);
        border: 1px solid var(--border-color); border-radius: 5px; width: 250px; padding: 1rem; z-index: 100;
    }
    .profile-dropdown-item { padding: 0.5rem 0; }
    .profile-dropdown-button { width: 100%; margin-top: 0.5rem; padding: 0.5rem; }
    .container { max-width: 1200px; margin: 2rem auto; padding: 0 2rem; }
    .page-title { font-size: 2.5rem; margin-bottom: 2rem; }
    .page-title span { color: var(--accent-color); }
    .activity-feed-section, .image-generation-section { margin-bottom: 3rem; }
    .section-title { font-size: 1.8rem; border-bottom: 2px solid var(--accent-color); padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
    .nft-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1.5rem; }
    .activity-card {
        background-color: var(--secondary-bg); border-radius: 8px; overflow: hidden;
        border: 1px solid var(--border-color); padding: 1rem;
    }
    .activity-card-image img { width: 100%; height: 180px; object-fit: cover; border-radius: 4px; margin-bottom: 1rem; }
    .buy-button { margin-top: 1rem; width: 100%; padding: 0.6rem; }
    .popup-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.7);
        display: none; justify-content: center; align-items: center; z-index: 1000;
    }
    .popup-content {
        background-color: var(--secondary-bg); padding: 2rem; border-radius: 8px;
        width: 90%; max-width: 500px; position: relative;
    }
    .popup-close-btn {
        position: absolute; top: 10px; right: 15px; background: none; border: none;
        color: var(--primary-text); font-size: 2rem; cursor: pointer;
    }
    .form-page-container {
        background-color: var(--secondary-bg); padding: 2rem; border-radius: 8px;
        max-width: 600px; margin: 0 auto;
    }
    .solidity-code-box {
        margin-top: 2rem; background-color: var(--primary-bg); padding: 1rem;
        border-radius: 5px; border: 1px solid var(--border-color);
    }
    .solidity-code-box pre { white-space: pre-wrap; word-wrap: break-word; max-height: 400px; overflow-y: auto; }
    .download-sol-button { margin-top: 1rem; }
    """,
}

def create_project_zip():
    """Creates a zip file containing the entire project structure."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filepath, content in project_files.items():
            file_content_bytes = textwrap.dedent(content).strip().encode('utf-8')
            zip_file.writestr(filepath, file_content_bytes)
    
    zip_filename = "novamint-enhanced.zip"
    with open(zip_filename, "wb") as f:
        f.write(zip_buffer.getvalue())
        
    print(f"\nProject successfully created as '{zip_filename}'!")
    print("You can now unzip this file and follow the setup instructions.")

if __name__ == "__main__":
    create_project_zip()
