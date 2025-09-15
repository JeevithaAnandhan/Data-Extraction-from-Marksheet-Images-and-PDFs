let currentUser = null, selectedType = null, selectedFile = null, uploadHistory = [], isProcessing = false;
let downloadUrl = null;

const adminCredentials = { username: "admin", password: "admin123" };
const marksheetTypes = {
  "10th": { id: "10th", name: "10th Marksheet", description: "Extract data from Class 10 marksheets", color: "#4F46E5", icon: "🎓" },
  "12th": { id: "12th", name: "12th Marksheet", description: "Extract data from Class 12 marksheets", color: "#059669", icon: "📜" },
  "semester": { id: "semester", name: "Semester Marksheet", description: "Extract data from university semester marksheets", color: "#DC2626", icon: "🏆" }
};

document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
  setupGlobalListeners();
  loadUploadHistory();
  setupFileUploadHandlers();
  checkLoginStatus();
  checkUrlParams();
  setupRegistrationHandlers();
});

function checkUrlParams() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('login') === 'success') {
    showToast('Successfully logged in with Google!', 'success');
    checkCurrentUser();
    showSection('dashboard');
  } else if (urlParams.get('login') === 'error') {
    showToast('Google login failed. Please try again.', 'error');
  }
}

async function checkCurrentUser() {
  try {
    const response = await fetch('/api/auth/user');
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        currentUser = data.user;
        updateAuthUI();
        return true;
      }
    }
    currentUser = null;
    updateAuthUI();
    return false;
  } catch (error) {
    console.error('Error checking user status:', error);
    return false;
  }
}

async function checkLoginStatus() {
  const isLoggedIn = await checkCurrentUser();
  if (isLoggedIn) {
    loadUploadHistory();
  }
}

function setupFileUploadHandlers() {
  const chooseFileBtn = document.getElementById('choose-file-btn');
  const fileInput = document.getElementById('file-input');
  if (chooseFileBtn && fileInput) {
    chooseFileBtn.removeEventListener('click', handleChooseFileClick);
    fileInput.removeEventListener('change', handleFileInputChange);
    chooseFileBtn.addEventListener('click', handleChooseFileClick);
    fileInput.addEventListener('change', handleFileInputChange);
  }
}

function handleChooseFileClick(e) {
  e.preventDefault();
  const fileInput = document.getElementById('file-input');
  if (fileInput) fileInput.click();
}

function handleFileInputChange(event) {
  const file = event.target.files[0];
  if (file) handleFileSelection(file);
}

function initializeApp() {
  showSection('landing');
  updateAuthUI();
  document.body.classList.add('fade-in');
}

// NEW FUNCTION: Handle Get Started Button Click
function handleGetStarted() {
  console.log('Get Started clicked, checking login status...');
  
  if (currentUser) {
    // User is already logged in, go directly to dashboard
    console.log('User already logged in:', currentUser.username);
    showToast(`Welcome back, ${currentUser.username || currentUser.email}! Redirecting to dashboard...`, 'success');
    showSection('dashboard');
    
    // Optional: Add smooth scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    // User is not logged in, show welcome message and login options
    console.log('User not logged in, showing login options');
    showToast('Welcome! Please login or create an account to start processing marksheets.', 'info');
    showSection('login');
    
    // Optional: Add smooth scroll to top when switching sections
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function setupGlobalListeners() {
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !isProcessing) resetProcess();
    if (e.ctrlKey && e.key === 'l' && !currentUser) {
      e.preventDefault();
      showSection('login');
    }
  });
}

// --- USER REGISTRATION FEATURE ---
function setupRegistrationHandlers() {
  const regForm = document.getElementById('register-form');
  if (regForm) {
    regForm.addEventListener('submit', handleRegistration);
  }
}

async function handleRegistration(event) {
  event.preventDefault();
  const username = document.getElementById('register-username').value.trim();
  const email = document.getElementById('register-email').value.trim();
  const password = document.getElementById('register-password').value.trim();
  const confirm = document.getElementById('register-confirm').value.trim();

  if (!username || !email || !password) {
    showToast('Please fill all fields.', 'error');
    return;
  }
  if (password !== confirm) {
    showToast('Passwords do not match.', 'error');
    return;
  }
  if (password.length < 4) {
    showToast('Password must be at least 4 characters long.', 'error');
    return;
  }

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    const data = await res.json();
    if (data.success) {
      showToast("Account created successfully! Please login.", 'success');
      document.getElementById('register-form').reset();
      showSection('login');
    } else {
      showToast(data.message || "Registration failed.", 'error');
    }
  } catch (error) {
    console.error('Registration error:', error);
    showToast("Failed to register. Please try again.", 'error');
  }
}
// --- END USER REGISTRATION FEATURE ---

function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
  const section = document.getElementById(id);
  if (section) {
    section.classList.remove('hidden');
    section.classList.add('fade-in');
    setTimeout(() => section.classList.remove('fade-in'), 500);
  }
  updateNavigation(id);
}

function updateNavigation(active) {
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const dash = document.getElementById('dashboard-link');
  if (currentUser && active === 'dashboard') dash?.classList.add('active');
}

async function handleLogin(e) {
  e.preventDefault();
  const u = document.getElementById('username').value.trim();
  const p = document.getElementById('password').value.trim();
  if (!u || !p) {
    showToast('Please enter both username and password.', 'warning');
    return;
  }

  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: u, password: p })
    });
    const data = await response.json();
    if (data.success) {
      currentUser = data.user;
      updateAuthUI();
      showSection('dashboard');
      showToast('Login successful! Welcome to the dashboard.', 'success');
      document.getElementById('username').value = '';
      document.getElementById('password').value = '';
      loadUploadHistory();
    } else {
      showToast(data.message || 'Invalid credentials. Please try again.', 'error');
      document.getElementById('password').value = '';
      document.getElementById('username').focus();
    }
  } catch (error) {
    console.error('Login error:', error);
    showToast('Login failed. Please try again.', 'error');
  }
}

async function logout() {
  try {
    await fetch('/api/auth/logout');
    currentUser = null;
    selectedType = null;
    selectedFile = null;
    uploadHistory = [];
    updateAuthUI();
    resetProcess();
    showSection('landing');
    showToast('Logged out successfully!', 'info');
  } catch (error) {
    console.error('Logout error:', error);
    showToast('Logout failed. Please try again.', 'error');
  }
}

function updateAuthUI() {
  const loginLink = document.getElementById('login-link');
  const registerLink = document.getElementById('register-link');
  const logoutLink = document.getElementById('logout-link');
  const dashLink = document.getElementById('dashboard-link');
  const userGreeting = document.getElementById('user-greeting');
  
  if (currentUser) {
    // User is logged in - hide login/register, show logout/dashboard
    loginLink?.classList.add('hidden');
    registerLink?.classList.add('hidden');
    logoutLink?.classList.remove('hidden');
    dashLink?.classList.remove('hidden');
    
    if (userGreeting) {
      userGreeting.textContent = `Welcome, ${currentUser.full_name || currentUser.username || currentUser.email}!`;
      userGreeting.classList.remove('hidden');
    }
  } else {
    // User is not logged in - show login/register, hide logout/dashboard
    loginLink?.classList.remove('hidden');
    registerLink?.classList.remove('hidden');
    logoutLink?.classList.add('hidden');
    dashLink?.classList.add('hidden');
    
    if (userGreeting) {
      userGreeting.classList.add('hidden');
    }
  }
}

function selectType(type) {
  if (!currentUser) { 
    showToast('Please login first.', 'warning'); 
    showSection('login'); 
    return; 
  }
  selectedFile = null;
  downloadUrl = null;
  const fileInput = document.getElementById('file-input');
  if (fileInput) fileInput.value = '';
  selectedType = type;
  document.querySelectorAll('.type-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.type === type));
  
  const uploadArea = document.getElementById('upload-area');
  const selectedFileDiv = document.getElementById('selected-file');
  const processingStatus = document.getElementById('processing-status');
  const downloadSection = document.getElementById('download-section');
  const uploadSection = document.getElementById('upload-section');
  
  if (uploadArea) uploadArea.style.display = 'block';
  if (selectedFileDiv) selectedFileDiv.classList.add('d-none');
  if (processingStatus) processingStatus.classList.add('d-none');
  if (downloadSection) downloadSection.classList.add('d-none');
  if (uploadSection) {
    uploadSection.style.display = 'block';
    uploadSection.classList.add('slide-up');
    uploadSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  showToast(`Selected ${marksheetTypes[type].name} for processing.`, 'info');
  setTimeout(() => { setupFileUploadHandlers(); }, 100);
}

function handleFileSelection(file) {
  if (!selectedType) { 
    showToast('Please select a marksheet type first.', 'warning'); 
    return; 
  }
  if (isProcessing) { 
    showToast('Processing in progress. Please wait.', 'warning'); 
    return; 
  }
  if (selectedFile) { 
    showToast('File already selected. Click "Clear" to select another.', 'info'); 
    return; 
  }
  
  const allowed = ['application/pdf'];
  const images = ['image/jpeg', 'image/jpg', 'image/png'];
  if (![...allowed, ...images].includes(file.type)) {
    showToast('Select a PDF or image (JPG, PNG) only.', 'error');
    document.getElementById('file-input').value = '';
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('File size should be less than 10MB.', 'error');
    document.getElementById('file-input').value = '';
    return;
  }
  selectedFile = file;
  displaySelectedFile(file);
  showToast('File selected successfully. Ready for processing!', 'success');
}

function displaySelectedFile(file) {
  const uploadArea = document.getElementById('upload-area');
  if (uploadArea) { uploadArea.style.display = 'none'; }
  
  const selectedFileDiv = document.getElementById('selected-file');
  if (selectedFileDiv) {
    selectedFileDiv.classList.remove('d-none');
    selectedFileDiv.style.display = 'block';
  }
  
  const fileNameEl = document.getElementById('file-name');
  const fileSizeEl = document.getElementById('file-size');
  if (fileNameEl) fileNameEl.textContent = file.name;
  if (fileSizeEl) fileSizeEl.textContent = formatFileSize(file.size);
  
  const uploadSection = document.getElementById('upload-section');
  if (uploadSection) uploadSection.style.display = 'block';
  
  const processingStatus = document.getElementById('processing-status');
  const downloadSection = document.getElementById('download-section');
  if (processingStatus) processingStatus.classList.add('d-none');
  if (downloadSection) downloadSection.classList.add('d-none');
}

function clearFile() {
  selectedFile = null;
  downloadUrl = null;
  const fileInput = document.getElementById('file-input');
  if (fileInput) fileInput.value = '';
  
  const uploadArea = document.getElementById('upload-area');
  const selectedFileDiv = document.getElementById('selected-file');
  const processingStatus = document.getElementById('processing-status');
  const downloadSection = document.getElementById('download-section');
  
  if (uploadArea) uploadArea.style.display = 'block';
  if (selectedFileDiv) selectedFileDiv.classList.add('d-none');
  if (processingStatus) processingStatus.classList.add('d-none');
  if (downloadSection) downloadSection.classList.add('d-none');
  showToast('File cleared. Please select another file.', 'info');
}

function addDemoFile() {
  showToast('Demo file feature not implemented yet.', 'warning');
}

async function processFile() {
  if (!selectedFile || !selectedType) {
    showToast('Select a marksheet type and file first.', 'warning');
    return;
  }
  if (isProcessing) return;
  
  isProcessing = true;
  const uploadArea = document.getElementById('upload-area');
  const selectedFileDiv = document.getElementById('selected-file');
  const processingStatus = document.getElementById('processing-status');
  const downloadSection = document.getElementById('download-section');
  
  if (uploadArea) uploadArea.style.display = 'none';
  if (selectedFileDiv) selectedFileDiv.classList.remove('d-none');
  if (processingStatus) processingStatus.classList.remove('d-none');
  if (downloadSection) downloadSection.classList.add('d-none');
  updateStatusText('Uploading file...');

  try {
    const formData = new FormData();
    formData.append('uploaded_file', selectedFile);
    const response = await fetch(`/process/${selectedType}`, { method: 'POST', body: formData });
    const data = await response.json();
    
    if (!response.ok || !data.success) {
      throw new Error(data.message || 'Processing failed.');
    }
    
    updateStatusText('Finalizing...');
    if (processingStatus) processingStatus.classList.add('d-none');
    if (downloadSection) downloadSection.classList.remove('d-none');
    
    const records = data.records_count || 0;
    const recordsCountEl = document.getElementById('records-count');
    const fileSizeStatEl = document.getElementById('file-size-stat');
    if (recordsCountEl) recordsCountEl.textContent = records;
    if (fileSizeStatEl) fileSizeStatEl.textContent = formatFileSize(selectedFile.size);
    
    downloadUrl = data.download_url;
    loadUploadHistory();
    showToast('Processing complete! You may download your file.', 'success');
  } catch (err) {
    console.error('Processing error:', err);
    showToast(`Error: ${err.message}`, 'error');
    resetProcess();
  } finally {
    isProcessing = false;
  }
}

function downloadFile() {
  if (!downloadUrl) {
    showToast('No file to download. Please process a marksheet first.', 'error');
    return;
  }
  window.open(downloadUrl, '_blank');
}

function resetProcess() {
  selectedFile = null;
  downloadUrl = null;
  isProcessing = false;
  
  const uploadArea = document.getElementById('upload-area');
  const selectedFileDiv = document.getElementById('selected-file');
  const processingStatus = document.getElementById('processing-status');
  const downloadSection = document.getElementById('download-section');
  const fileInput = document.getElementById('file-input');
  
  if (uploadArea) uploadArea.style.display = 'block';
  if (selectedFileDiv) selectedFileDiv.classList.add('d-none');
  if (processingStatus) processingStatus.classList.add('d-none');
  if (downloadSection) downloadSection.classList.add('d-none');
  if (fileInput) fileInput.value = '';
  showToast('Ready for new file upload.', 'info');
}

function updateStatusText(text) {
  const statusText = document.getElementById('status-text');
  if (statusText) statusText.textContent = text;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " bytes";
  else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  else return (bytes / 1048576).toFixed(1) + " MB";
}

function showToast(message, type = 'info') {
  const toastContainer = document.querySelector('.toast-container');
  if (!toastContainer) return;
  
  const toastId = 'toast-' + Date.now();
  const toastEl = document.createElement('div');
  toastEl.id = toastId;
  toastEl.className = `toast align-items-center text-bg-${type} border-0`;
  toastEl.role = 'alert';
  toastEl.ariaLive = 'assertive';
  toastEl.ariaAtomic = 'true';
  toastEl.dataset.bsDelay = 3000;
  
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  toastContainer.appendChild(toastEl);
  const toast = new bootstrap.Toast(toastEl);
  toast.show();
  
  toastEl.addEventListener('hidden.bs.toast', () => { 
    toastEl.remove(); 
  });
}

async function loadUploadHistory() {
  const historyList = document.getElementById('history-list');
  if (!historyList) return;
  
  try {
    const response = await fetch('/api/history');
    if (response.ok) {
      uploadHistory = await response.json();
    } else {
      uploadHistory = [];
    }
  } catch (error) {
    console.error('Error loading history:', error);
    uploadHistory = [];
  }
  
  if (uploadHistory.length === 0) {
    historyList.innerHTML = `<p class="text-center text-muted fst-italic mb-0 p-3">No files processed yet</p>`;
    return;
  }
  
  let html = '';
  uploadHistory.forEach(item => {
    html += `
      <div class="history-item d-flex justify-content-between align-items-start p-3 border-bottom">
        <div class="flex-grow-1">
          <div class="history-file fw-semibold">${item.filename}</div>
          <small class="text-muted">
            ${item.marksheet_type.toUpperCase()} • ${item.records_extracted || 0} records • 
            ${formatFileSize(item.file_size || 0)}
          </small>
        </div>
        <div class="text-end">
          <div class="history-time text-muted small">${item.date}</div>
          ${item.processed_filename ? 
            `<button class="btn btn-outline-primary btn-sm mt-1" onclick="window.open('/download/${item.processed_filename}', '_blank')">
              <i class="fas fa-download"></i> Download
            </button>` : ''
          }
        </div>
      </div>
    `;
  });
  
  historyList.innerHTML = html;
}
