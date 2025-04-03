/**
 * Admin Portal JavaScript
 * Handles admin interface interactions for InterviewAI platform
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const setupForm = document.getElementById('interviewSetupForm');
    const candidateSearchForm = document.getElementById('candidateSearchForm');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const categoryInputs = document.querySelectorAll('.category-input');
    const numQuestionsInput = document.getElementById('numQuestions');
    const categoryError = document.getElementById('categoryError');
    const resultsContainer = document.getElementById('resultsContainer');
    const noResultsMessage = document.getElementById('noResultsMessage');
    const candidateSearch = document.getElementById('candidateSearch');
    const logoutButton = document.getElementById('adminLogout');
    const progressIndicator = document.getElementById('progressIndicator');
    const successMessage = document.getElementById('successMessage');

    // Tab switching functionality
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Deactivate all tabs
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Activate the clicked tab
            button.classList.add('active');
            const tabId = `${button.dataset.tab}-tab`;
            document.getElementById(tabId).classList.add('active');
            
            // Hide success message when switching tabs
            if (successMessage) {
                successMessage.style.display = 'none';
            }
            
            // If switching to results tab with a candidate name in query params, search for that candidate
            if (button.dataset.tab === 'results') {
                const urlParams = new URLSearchParams(window.location.search);
                const candidateParam = urlParams.get('candidate');
                
                if (candidateParam && document.getElementById('candidateSearch')) {
                    document.getElementById('candidateSearch').value = candidateParam;
                    searchCandidate(candidateParam);
                }
            }
        });
    });

    // Category validation
    function validateCategories() {
        const totalQuestions = parseInt(numQuestionsInput.value) || 5;
        let totalCategoryQuestions = 0;
        
        categoryInputs.forEach(input => {
            totalCategoryQuestions += parseInt(input.value) || 0;
        });
        
        if (totalCategoryQuestions > totalQuestions) {
            categoryError.textContent = `Total category questions (${totalCategoryQuestions}) exceeds total questions (${totalQuestions})`;
            return false;
        } else {
            categoryError.textContent = '';
            return true;
        }
    }
    
    // Add validation to category inputs
    categoryInputs.forEach(input => {
        input.addEventListener('change', validateCategories);
    });
    
    numQuestionsInput.addEventListener('change', validateCategories);

    // Handle setup form submission
    if (setupForm) {
        setupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!validateCategories()) {
                return;
            }
            
            // Show loading state
            progressIndicator.style.display = 'flex';
            const submitButton = setupForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';
            
            // Gather form data
            const candidateName = document.getElementById('candidateName').value;
            const numQuestions = parseInt(document.getElementById('numQuestions').value);
            const interviewTime = parseInt(document.getElementById('interviewTime').value);
            const adminInstructions = document.getElementById('adminInstructions').value;
            const voiceEnabled = document.getElementById('voiceEnabled').checked;
            const monitoringEnabled = document.getElementById('monitoringEnabled').checked;
            const projectQuestions = parseInt(document.getElementById('projectQuestions').value) || 0;
            const skillsQuestions = parseInt(document.getElementById('skillsQuestions').value) || 0;
            const technicalQuestions = parseInt(document.getElementById('technicalQuestions').value) || 0;
            const scenarioQuestions = parseInt(document.getElementById('scenarioQuestions').value) || 0;
            
            // Resume handling
            const resumeFile = document.getElementById('resumeInput').files[0];
            const resumeText = document.getElementById('resumeText').value;
            
            if (!resumeFile && !resumeText) {
                alert('Please either upload a resume PDF or provide resume text.');
                progressIndicator.style.display = 'none';
                submitButton.disabled = false;
                submitButton.textContent = 'Create Interview';
                return;
            }
            
            // Log the data to help with debugging
            console.log('Submitting interview setup with data:', {
                candidateName,
                numQuestions,
                interviewTime,
                adminInstructions,
                voiceEnabled,
                monitoringEnabled,
                projectQuestions,
                skillsQuestions,
                technicalQuestions,
                scenarioQuestions,
                resumeFile: resumeFile ? resumeFile.name : 'No file',
                resumeText: resumeText ? 'Text provided' : 'No text'
            });
            
            // Create setup data object
            const setupData = {
                candidateName,
                numQuestions,
                interviewTime,
                adminInstructions,
                voiceEnabled,
                monitoringEnabled,
                projectQuestions,
                skillsQuestions,
                technicalQuestions,
                scenarioQuestions,
                resumeFile,
                resumeText
            };
            
            try {
                // Call API to set up interview
                const response = await API.admin.setupInterview(setupData);
                console.log('API response:', response);
                
                // Hide loading state
                progressIndicator.style.display = 'none';
                submitButton.disabled = false;
                submitButton.textContent = 'Create Interview';
                
                // Show success message with candidate name and interview link
                successMessage.style.display = 'block';
                
                // Build a link that includes the candidate name as a parameter
                const candidateParam = encodeURIComponent(candidateName);
                const monitoringParam = setupData.monitoringEnabled ? 'true' : 'false';
                const voiceParam = setupData.voiceEnabled ? 'true' : 'false';
                
                const candidateLink = `${window.location.origin}/interview.html?candidate=${candidateParam}&monitoring=${monitoringParam}&voice=${voiceParam}`;
                
                // Update the success message HTML
                successMessage.querySelector('.card-body').innerHTML = `
                    <h4 class="text-success"><i class="fas fa-check-circle"></i> Interview Created Successfully!</h4>
                    <p>Interview for <strong>${candidateName}</strong> has been created.</p>
                    
                    <div class="alert alert-info">
                        <p class="mb-1"><strong>Instructions for candidate:</strong></p>
                        <ol class="mb-2">
                            <li>Click the direct link below</li>
                            <li>The name will be pre-filled</li>
                            <li>Press "Start Interview" to begin</li>
                        </ol>
                    </div>
                    
                    <div class="input-group mb-3">
                        <input type="text" class="form-control" id="candidateLinkInput" value="${candidateLink}" readonly>
                        <button class="btn btn-outline-secondary" type="button" id="copyLinkBtn" 
                            onclick="navigator.clipboard.writeText('${candidateLink}').then(() => { this.innerHTML = '<i class=\\'fas fa-check\\'></i> Copied'; setTimeout(() => { this.innerHTML = '<i class=\\'fas fa-copy\\'></i> Copy Link'; }, 2000); })">
                            <i class="fas fa-copy"></i> Copy Link
                        </button>
                    </div>
                    
                    <div class="mt-3">
                        <button class="btn btn-secondary me-2" onclick="window.open('${candidateLink}', '_blank')">
                            <i class="fas fa-external-link-alt me-1"></i> Open Candidate Link
                        </button>
                        <button class="btn btn-primary" onclick="showResults('${candidateName}')">
                            <i class="fas fa-chart-bar me-1"></i> View Results
                        </button>
                    </div>
                `;
                
                // Reset form
                setupForm.reset();
                
                // Scroll to the success message
                window.scrollTo({
                    top: successMessage.offsetTop - 20,
                    behavior: 'smooth'
                });
                
            } catch (error) {
                // Hide loading state
                progressIndicator.style.display = 'none';
                submitButton.disabled = false;
                submitButton.textContent = 'Create Interview';
                
                // Show error alert with more detailed information
                console.error('Error creating interview:', error);
                
                // Display error in success message area with red styling
                successMessage.style.display = 'block';
                successMessage.querySelector('.card-header').className = 'card-header bg-danger text-white';
                successMessage.querySelector('.card-header h5').innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                
                successMessage.querySelector('.card-body').innerHTML = `
                    <h4 class="text-danger">Interview Creation Failed</h4>
                    <p>There was an error creating the interview for <strong>${candidateName}</strong>:</p>
                    <div class="alert alert-danger">
                        ${error.message || 'Unknown error occurred. Please check your network connection and try again.'}
                    </div>
                    <p>Please check the browser console for more detailed error information.</p>
                `;
                
                // Scroll to the error message
                window.scrollTo({
                    top: successMessage.offsetTop - 20,
                    behavior: 'smooth'
                });
            }
        });
    }

    // Search for candidate results
    if (candidateSearchForm) {
        candidateSearchForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const candidateName = document.getElementById('candidateSearch').value.trim();
            if (!candidateName) {
                alert('Please enter a candidate name to search');
                return;
            }
            
            searchCandidate(candidateName);
        });
    }

    // Handle search button click
    const searchButton = document.getElementById('searchButton');
    if (searchButton) {
        searchButton.addEventListener('click', (e) => {
            e.preventDefault();
            const candidateName = document.getElementById('candidateSearch').value.trim();
            if (candidateName) {
                searchCandidate(candidateName);
            } else {
                alert('Please enter a candidate name to search');
            }
        });
    }
    
    // Function to search for a candidate's results
    async function searchCandidate(candidateName) {
        try {
            // Update UI to show loading state
            document.getElementById('noResultsMessage').style.display = 'none';
            document.getElementById('resultsContainer').classList.add('d-none');
            document.getElementById('searchResultsLoading').style.display = 'block';
            
            console.log('Searching for candidate:', candidateName);
            
            // Call API to get results
            const results = await API.admin.getInterviewResults(candidateName);
            console.log('Search results:', results);
            
            // Hide loading state
            document.getElementById('searchResultsLoading').style.display = 'none';
            
            // Display results
            displayResults(results, candidateName);
            
            // Show results container
            document.getElementById('noResultsMessage').style.display = 'none';
            document.getElementById('resultsContainer').classList.remove('d-none');
            
        } catch (error) {
            console.error('Error searching for candidate:', error);
            
            // Hide loading state
            document.getElementById('searchResultsLoading').style.display = 'none';
            
            // Show error message
            document.getElementById('noResultsMessage').style.display = 'block';
            document.getElementById('noResultsMessage').className = 'alert alert-danger';
            document.getElementById('noResultsMessage').innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${error.message || 'An error occurred while searching for results.'}
                <p class="mt-2 mb-0 small">The interview for this candidate might still be in progress or hasn't been created yet.</p>
            `;
            
            // Hide results container
            document.getElementById('resultsContainer').classList.add('d-none');
        }
    }

    // Handle logout
    if (logoutButton) {
        logoutButton.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                window.location.href = 'index.html';
            }
        });
    }

    // Function to display interview results
    function displayResults(results, candidateName) {
        resultsContainer.style.display = 'block';
        resultsContainer.classList.add('d-block');
        resultsContainer.classList.remove('d-none');
        noResultsMessage.style.display = 'none';
        
        // Build the HTML for the results
        let resultsHTML = `
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h4><i class="fas fa-user-graduate"></i> Results for ${candidateName || results.history[0]?.candidate_name || 'Candidate'}</h4>
                </div>
                <div class="card-body">
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-header bg-info text-white">
                                    <h5><i class="fas fa-star"></i> Overall Score</h5>
                                </div>
                                <div class="card-body text-center">
                                    <h2 class="display-4">${parseFloat(results.overall_score).toFixed(1)}/10</h2>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-header bg-info text-white">
                                    <h5><i class="fas fa-comment"></i> Final Feedback</h5>
                                </div>
                                <div class="card-body">
                                    <p>${results.final_feedback}</p>
                                </div>
                            </div>
                        </div>
                    </div>
        `;
        
        // Add monitoring metrics if available
        if (results.monitoring_metrics) {
            const metrics = results.monitoring_metrics;
            
            // Check if there are any suspicious activities logged
            const hasSuspiciousActivities = metrics.suspicious_activity_log && 
                                           metrics.suspicious_activity_log.length > 0;
            
            resultsHTML += `
                <div class="card mb-4">
                    <div class="card-header bg-warning">
                        <h5><i class="fas fa-video"></i> Monitoring Metrics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Mobile Device Detection:</h6>
                                <p>Times detected: ${metrics.mobile_detection_count}</p>
                                
                                <h6>Head Position Events:</h6>
                                <ul class="list-group">
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Left
                                        <span class="badge bg-primary rounded-pill">${metrics.head_pose_events['Looking Left']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Right
                                        <span class="badge bg-primary rounded-pill">${metrics.head_pose_events['Looking Right']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Up
                                        <span class="badge bg-primary rounded-pill">${metrics.head_pose_events['Looking Up']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Down
                                        <span class="badge bg-primary rounded-pill">${metrics.head_pose_events['Looking Down']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Tilted
                                        <span class="badge bg-primary rounded-pill">${metrics.head_pose_events['Tilted']}</span>
                                    </li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6>Eye Movement Events:</h6>
                                <ul class="list-group">
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Left
                                        <span class="badge bg-primary rounded-pill">${metrics.eye_movement_events['Looking Left']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Right
                                        <span class="badge bg-primary rounded-pill">${metrics.eye_movement_events['Looking Right']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Up
                                        <span class="badge bg-primary rounded-pill">${metrics.eye_movement_events['Looking Up']}</span>
                                    </li>
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        Looking Down
                                        <span class="badge bg-primary rounded-pill">${metrics.eye_movement_events['Looking Down']}</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                        
                        ${hasSuspiciousActivities ? `
                            <div class="mt-4">
                                <h6 class="border-bottom pb-2 mb-3">Candidate Screenshots:</h6>
                                <div class="row">
                                    ${metrics.suspicious_activity_log.map((activity, idx) => `
                                        <div class="col-md-3 mb-3">
                                            <div class="card h-100">
                                                <div class="card-img-top screenshot-thumbnail" 
                                                     style="background-image: url('${activity.screenshot.replace(/\\/g, '/')}'); height: 150px; background-size: cover; background-position: center; cursor: pointer;"
                                                     data-bs-toggle="modal" 
                                                     data-bs-target="#screenshotModal"
                                                     data-screenshot="${activity.screenshot.replace(/\\/g, '/')}"
                                                     data-type="${activity.type}"
                                                     data-direction="${activity.direction || ''}"
                                                     data-timestamp="${new Date(activity.timestamp * 1000).toLocaleString()}">
                                                </div>
                                                <div class="card-body p-2 text-center">
                                                    <small class="text-muted">
                                                        ${activity.type === 'head_pose' ? 'Head: ' + activity.direction : 
                                                          activity.type === 'eye_movement' ? 'Eyes: ' + activity.direction : 
                                                          'Mobile Device'}
                                                    </small>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        // Add individual question results
        resultsHTML += `
            <div class="accordion" id="interviewAccordion">
        `;
        
        results.history.forEach((item, index) => {
            resultsHTML += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading${index}">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}" aria-expanded="false" aria-controls="collapse${index}">
                            <div class="w-100 d-flex justify-content-between">
                                <span>Question ${index + 1}: ${item.category ? item.category.replace(/_/g, ' ') : 'General'}</span>
                                <span class="badge ${parseFloat(item.score) >= 7 ? 'bg-success' : parseFloat(item.score) >= 5 ? 'bg-warning' : 'bg-danger'}">${item.score}/10</span>
                            </div>
                        </button>
                    </h2>
                    <div id="collapse${index}" class="accordion-collapse collapse" aria-labelledby="heading${index}" data-bs-parent="#interviewAccordion">
                        <div class="accordion-body">
                            <div class="row">
                                <div class="col-md-12 mb-3">
                                    <h6>Question:</h6>
                                    <p>${item.question}</p>
                                </div>
                                <div class="col-md-6">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6>Candidate's Answer:</h6>
                                        </div>
                                        <div class="card-body">
                                            <p>${item.candidate_answer}</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6>Ideal Answer:</h6>
                                        </div>
                                        <div class="card-body">
                                            <p>${item.ideal_answer || 'No ideal answer provided'}</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-12 mt-3">
                                    <div class="card">
                                        <div class="card-header bg-light">
                                            <h6>Feedback:</h6>
                                        </div>
                                        <div class="card-body">
                                            <p>${item.feedback || 'No feedback available'}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsHTML += `
            </div>
            </div>
            </div>
        `;
        
        resultsContainer.innerHTML = resultsHTML;
        
        // Add event listeners for screenshot thumbnails
        document.querySelectorAll('.screenshot-thumbnail').forEach(thumbnail => {
            thumbnail.addEventListener('click', function() {
                const screenshot = this.getAttribute('data-screenshot');
                const type = this.getAttribute('data-type');
                const direction = this.getAttribute('data-direction');
                const timestamp = this.getAttribute('data-timestamp');
                
                const screenshotImage = document.getElementById('screenshotImage');
                const screenshotInfo = document.getElementById('screenshotInfo');
                
                // Set the image source
                screenshotImage.src = screenshot;
                
                // Set the info text
                let infoText = '';
                if (type === 'head_pose') {
                    infoText = `Head Position: ${direction} - Detected at ${timestamp}`;
                } else if (type === 'eye_movement') {
                    infoText = `Eye Movement: ${direction} - Detected at ${timestamp}`;
                } else if (type === 'mobile_detected') {
                    infoText = `Mobile Device Detected - ${timestamp}`;
                }
                
                screenshotInfo.textContent = infoText;
                
                // Show the modal
                const modal = new bootstrap.Modal(document.getElementById('screenshotModal'));
                modal.show();
            });
        });
    }

    // Function to switch to results tab and search for a candidate
    function showResults(candidateName) {
        // Switch to results tab
        const resultsTabButton = document.querySelector('[data-tab="results"]');
        if (resultsTabButton) {
            resultsTabButton.click();
        }
        
        // Fill in search field and search
        if (candidateName && document.getElementById('candidateSearch')) {
            document.getElementById('candidateSearch').value = candidateName;
            searchCandidate(candidateName);
        }
    }
    
    // Check URL parameters for automatic actions
    document.addEventListener('DOMContentLoaded', function() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // If ?tab=results is in URL, switch to results tab
        if (urlParams.get('tab') === 'results') {
            const resultsTabButton = document.querySelector('[data-tab="results"]');
            if (resultsTabButton) {
                resultsTabButton.click();
            }
            
            // If ?candidate=name is also in URL, search for that candidate
            const candidateName = urlParams.get('candidate');
            if (candidateName && document.getElementById('candidateSearch')) {
                document.getElementById('candidateSearch').value = candidateName;
                searchCandidate(candidateName);
            }
        }
    });
}); 