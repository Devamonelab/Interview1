/**
 * Candidate Interview JavaScript
 * Handles candidate interview interactions for InterviewAI platform
 */

// Wait for the DOM to be fully loaded before executing scripts
document.addEventListener('DOMContentLoaded', function() {
    // Interview state
    const interviewState = {
        candidateName: '',
        currentQuestionIndex: 0,
        totalQuestions: 0,
        isRecording: false,
        isCompleted: false,
        // Add settings that can be passed via URL parameters
        monitoringEnabled: true,
        voiceEnabled: false,
        cameraFailedRetryCount: 0,
        maxCameraRetries: 3,
        useDummyCamera: false  // Flag to use dummy camera display if real camera fails
    };

    // Parse URL parameters if available
    function parseUrlParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Check for candidate name parameter
        const candidateParam = urlParams.get('candidate');
        if (candidateParam) {
            interviewState.candidateName = decodeURIComponent(candidateParam);
            console.log('Found candidate name in URL:', interviewState.candidateName);
            
            // Pre-fill the candidate name input if it exists
            const candidateNameInput = document.getElementById('candidateName');
            if (candidateNameInput) {
                candidateNameInput.value = interviewState.candidateName;
            }
        }
        
        // Check for monitoring parameter
        const monitoringParam = urlParams.get('monitoring');
        if (monitoringParam !== null) {
            interviewState.monitoringEnabled = monitoringParam === 'true';
            console.log('Monitoring enabled:', interviewState.monitoringEnabled);
        }
        
        // Check for voice parameter
        const voiceParam = urlParams.get('voice');
        if (voiceParam !== null) {
            interviewState.voiceEnabled = voiceParam === 'true';
            console.log('Voice enabled:', interviewState.voiceEnabled);
            
            // Update voice toggle if it exists
            const voiceToggle = document.getElementById('voiceToggle');
            if (voiceToggle) {
                voiceToggle.checked = interviewState.voiceEnabled;
                voiceEnabled = interviewState.voiceEnabled; // Update the global variable
            }
        }
    }
    
    // Parse URL parameters on page load
    parseUrlParameters();

    // Get DOM elements
    const loginScreen = document.getElementById('loginScreen');
    const interviewScreen = document.getElementById('interviewScreen');
    const completionScreen = document.getElementById('completionScreen');
    const loginForm = document.getElementById('loginForm');
    const questionContainer = document.getElementById('questionContainer');
    const questionText = document.getElementById('questionText');
    const questionCategory = document.getElementById('questionCategory');
    const responseOptions = document.getElementById('responseOptions');
    const textResponseOption = document.getElementById('textResponseOption');
    const voiceResponseOption = document.getElementById('voiceResponseOption');
    const textResponseContainer = document.getElementById('textResponseContainer');
    const voiceResponseContainer = document.getElementById('voiceResponseContainer');
    const textResponseForm = document.getElementById('textResponseForm');
    const textResponseInput = document.getElementById('textResponseInput');
    const startRecordingBtn = document.getElementById('startRecordingBtn');
    const stopRecordingBtn = document.getElementById('stopRecordingBtn');
    const recordingStatus = document.getElementById('recordingStatus');
    const recordingTimer = document.getElementById('recordingTimer');
    const speakQuestionBtn = document.getElementById('speakQuestionBtn');
    const feedbackContainer = document.getElementById('feedbackContainer');
    const feedbackText = document.getElementById('feedbackText');
    const feedbackScore = document.getElementById('feedbackScore');
    const candidateVideo = document.getElementById('candidateVideo');
    const cameraStatus = document.getElementById('cameraStatus');
    const retryCameraBtn = document.getElementById('retryCameraBtn');
    const nextQuestionBtn = document.getElementById('nextQuestionBtn');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const voiceToggle = document.getElementById('voiceToggle');
    
    // Timer variables
    let recordingTimerId = null;
    let recordingSeconds = 0;
    
    // Voice preference
    let voiceEnabled = false;
    
    // Initialize camera with slight delay to ensure UI is ready and prevent initial error flash
    setTimeout(() => {
        console.log('Initializing camera...');
        initializeCamera();
    }, 1000);
    
    // Handle login form submission
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Get candidate name from input or URL parameters
            let candidateName = document.getElementById('candidateName').value.trim();
            
            // If the input is empty but we have a name from URL parameters, use that
            if (!candidateName && interviewState.candidateName) {
                candidateName = interviewState.candidateName;
            }
            
            if (!candidateName) {
                alert('Please enter your name to continue');
                return;
            }
            
            interviewState.candidateName = candidateName;
            
            // Show loading state
            document.getElementById('loginButton').disabled = true;
            document.getElementById('loginButton').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
            
            try {
                console.log('Starting interview for:', candidateName);
                
                // Start the interview immediately by sending a text response API call
                const response = await API.candidate.startInterview(candidateName);
                console.log('Interview started, response:', response);
                
                // Check for camera permissions right after login
                if (interviewState.monitoringEnabled) {
                    await initializeCamera();
                } else {
                    console.log('Camera monitoring disabled for this interview');
                    // Hide camera container if monitoring is disabled
                    const cameraCards = document.querySelectorAll('.card');
                    for (const card of cameraCards) {
                        if (card.querySelector('#candidateVideo')) {
                            card.style.display = 'none';
                            break;
                        }
                    }
                }
                
                // Process the first question
                processInterviewResponse(response);
                
                // Hide login screen and show interview screen
                loginScreen.style.display = 'none';
                interviewScreen.style.display = 'block';
                
                // Update progress bar for first question
                updateProgress(1, response.total_questions || 5);
                
            } catch (error) {
                console.error('Error starting interview:', error);
                alert('Error: ' + (error.message || 'Unable to start interview. Please try again.'));
                document.getElementById('loginButton').disabled = false;
                document.getElementById('loginButton').textContent = 'Start Interview';
            }
        });
    }
    
    // Handle text response form submission
    if (textResponseForm) {
        textResponseForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const answer = textResponseInput.value.trim();
            if (!answer) {
                alert('Please enter your answer before submitting');
                return;
            }
            
            // Disable submit button
            document.getElementById('submitTextBtn').disabled = true;
            document.getElementById('submitTextBtn').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
            
            try {
                // Submit the text answer using the voice setting from interviewState
                const response = await API.candidate.submitTextAnswer(
                    interviewState.candidateName, 
                    answer,
                    interviewState.voiceEnabled || voiceEnabled // Use either voice setting
                );
                
                // Clear text input
                textResponseInput.value = '';
                
                // Process the response
                processInterviewResponse(response);
                
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                // Re-enable submit button
                document.getElementById('submitTextBtn').disabled = false;
                document.getElementById('submitTextBtn').textContent = 'Submit Answer';
            }
        });
    }
    
    // Response option switching (Text/Voice)
    if (textResponseOption && voiceResponseOption) {
        textResponseOption.addEventListener('click', function() {
            textResponseContainer.style.display = 'block';
            voiceResponseContainer.style.display = 'none';
            textResponseOption.classList.add('active');
            voiceResponseOption.classList.remove('active');
        });
        
        voiceResponseOption.addEventListener('click', function() {
            textResponseContainer.style.display = 'none';
            voiceResponseContainer.style.display = 'block';
            textResponseOption.classList.remove('active');
            voiceResponseOption.classList.add('active');
        });
    }
    
    // Handle voice toggle
    if (voiceToggle) {
        voiceToggle.addEventListener('change', function() {
            voiceEnabled = this.checked;
            interviewState.voiceEnabled = this.checked;
        });
    }
    
    // Handle start recording button
    if (startRecordingBtn) {
        startRecordingBtn.addEventListener('click', async function() {
            if (interviewState.isRecording) return;
            
            try {
                // Start recording
                const response = await API.candidate.startRecording(
                    interviewState.candidateName,
                    interviewState.voiceEnabled || voiceEnabled // Use either voice setting
                );
                
                // Update UI
                interviewState.isRecording = true;
                startRecordingBtn.style.display = 'none';
                stopRecordingBtn.style.display = 'inline-block';
                recordingStatus.textContent = 'Recording in progress...';
                recordingStatus.classList.add('text-danger');
                
                // Start timer
                startRecordingTimer();
                
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    }
    
    // Handle stop recording button
    if (stopRecordingBtn) {
        stopRecordingBtn.addEventListener('click', async function() {
            if (!interviewState.isRecording) return;
            
            try {
                // Stop recording
                stopRecordingBtn.disabled = true;
                stopRecordingBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                
                // Stop timer
                stopRecordingTimer();
                
                const response = await API.candidate.stopRecording(
                    interviewState.candidateName,
                    interviewState.voiceEnabled || voiceEnabled // Use either voice setting
                );
                
                // Update UI
                interviewState.isRecording = false;
                startRecordingBtn.style.display = 'inline-block';
                stopRecordingBtn.style.display = 'none';
                stopRecordingBtn.disabled = false;
                stopRecordingBtn.textContent = 'Stop Recording';
                recordingStatus.textContent = 'Click the button to start recording your answer';
                recordingStatus.classList.remove('text-danger');
                
                // Process the response
                processInterviewResponse(response);
                
            } catch (error) {
                // Revert UI changes
                interviewState.isRecording = false;
                startRecordingBtn.style.display = 'inline-block';
                stopRecordingBtn.style.display = 'none';
                stopRecordingBtn.disabled = false;
                stopRecordingBtn.textContent = 'Stop Recording';
                recordingStatus.textContent = 'Click the button to start recording your answer';
                recordingStatus.classList.remove('text-danger');
                
                // Stop timer
                stopRecordingTimer();
                
                alert('Error: ' + error.message);
            }
        });
    }
    
    // Handle speak question button
    if (speakQuestionBtn) {
        speakQuestionBtn.addEventListener('click', async function() {
            try {
                speakQuestionBtn.disabled = true;
                speakQuestionBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Speaking...';
                
                await API.candidate.speakQuestion(interviewState.candidateName);
                
                // Re-enable button after a short delay
                setTimeout(() => {
                    speakQuestionBtn.disabled = false;
                    speakQuestionBtn.innerHTML = '<i class="fas fa-volume-up"></i> Speak Question';
                }, 2000);
                
            } catch (error) {
                alert('Error: ' + error.message);
                speakQuestionBtn.disabled = false;
                speakQuestionBtn.innerHTML = '<i class="fas fa-volume-up"></i> Speak Question';
            }
        });
    }
    
    // Function to start recording timer
    function startRecordingTimer() {
        recordingSeconds = 0;
        updateRecordingTimer();
        recordingTimerId = setInterval(updateRecordingTimer, 1000);
    }
    
    // Function to stop recording timer
    function stopRecordingTimer() {
        if (recordingTimerId) {
            clearInterval(recordingTimerId);
            recordingTimerId = null;
        }
    }
    
    // Function to update recording timer display
    function updateRecordingTimer() {
        recordingSeconds++;
        const minutes = Math.floor(recordingSeconds / 60);
        const seconds = recordingSeconds % 60;
        recordingTimer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // Function to process interview response
    function processInterviewResponse(response) {
        console.log('Processing interview response:', response);
        
        // Handle interview completion
        if (response.message && response.message.includes('completed')) {
            interviewState.isCompleted = true;
            interviewScreen.style.display = 'none';
            completionScreen.style.display = 'block';
            return;
        }
        
        // Display current question
        questionText.textContent = response.current_question;
        
        // Display category if available
        if (response.current_category) {
            const category = response.current_category.replace(/_/g, ' ');
            questionCategory.textContent = `Category: ${category}`;
            questionCategory.style.display = 'inline-block';
        } else {
            questionCategory.style.display = 'none';
        }
        
        // Display feedback if available
        if (response.feedback && response.score) {
            feedbackContainer.style.display = 'block';
            feedbackText.textContent = response.feedback;
            feedbackScore.textContent = `${response.score}/10`;
            
            // Set score color based on value
            const score = parseFloat(response.score);
            if (score >= 7) {
                feedbackScore.className = 'badge bg-success';
            } else if (score >= 5) {
                feedbackScore.className = 'badge bg-warning';
            } else {
                feedbackScore.className = 'badge bg-danger';
            }
            
            // Increment question index when we have feedback (after first question)
            interviewState.currentQuestionIndex++;
        } else {
            feedbackContainer.style.display = 'none';
            
            // For initial question (when no feedback), set question index to 1
            if (interviewState.currentQuestionIndex === 0) {
                interviewState.currentQuestionIndex = 1;
            }
        }
        
        // Get total questions from response if available, otherwise use default
        interviewState.totalQuestions = response.total_questions || 5;
        
        // Update progress display
        updateProgress(interviewState.currentQuestionIndex, interviewState.totalQuestions);
        
        // Auto-speak the question if voice is enabled
        if (interviewState.voiceEnabled || voiceEnabled) {
            setTimeout(() => {
                speakQuestionBtn.click();
            }, 1000);
        }
    }
    
    // Function to update progress bar
    function updateProgress(questionIndex, totalQuestions = 5) {
        const percentage = Math.min(100, Math.round((questionIndex / totalQuestions) * 100));
        
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        progressText.textContent = `Question ${questionIndex} of ${totalQuestions}`;
    }
    
    // Function to handle camera initialization
    async function initializeCamera() {
        // Reset any previous camera state
        if (candidateVideo && candidateVideo.srcObject) {
            const tracks = candidateVideo.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            candidateVideo.srcObject = null;
        }
        
        // Check for URL parameters that might disable camera
        const urlParams = new URLSearchParams(window.location.search);
        const disableCamera = urlParams.get('disable_camera') === 'true';
        
        if (disableCamera || interviewState.useDummyCamera) {
            console.log('Using dummy camera mode');
            showDummyCamera();
            return;
        }
        
        // First try to enumerate devices to check if we already have permissions
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            let cameraExists = false;
            let hasPermissions = false;
            
            // Check if we have video devices and permissions
            for (const device of devices) {
                if (device.kind === 'videoinput') {
                    cameraExists = true;
                    if (device.label) {
                        // If we can see device labels, we have permission
                        hasPermissions = true;
                    }
                }
            }
            
            if (!cameraExists) {
                console.log('No camera detected on this device');
                showCameraError({ name: 'NoCameraDetected', message: 'No camera found on this device' });
                return;
            }
            
            if (hasPermissions) {
                console.log('Camera permissions already granted');
            }
            
            // Proceed to access the camera
            checkCameraPermission();
            
        } catch (err) {
            console.error('Error during device enumeration:', err);
            // Still try to access camera directly
            checkCameraPermission();
        }
    }

    // Check for camera permissions and set up video display
    async function checkCameraPermission() {
        try {
            // Clear any previous error states
            if (cameraStatus) {
                const cameraConnecting = document.getElementById('cameraConnecting');
                const cameraError = document.getElementById('cameraError');
                
                if (cameraConnecting && cameraError) {
                    cameraConnecting.style.display = 'block';
                    cameraError.style.display = 'none';
                }
                
                // Make sure the camera status is visible while connecting
                cameraStatus.style.display = 'block';
            }
            
            if (candidateVideo) {
                candidateVideo.style.display = 'block';
            }
            
            console.log('Requesting camera access...');
            
            // Request camera access with more flexible constraints
            // Try a sequence of increasingly permissive constraints
            let stream = null;
            const constraints = [
                // First try ideal settings
                {
                    video: {
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                        facingMode: "user"
                    },
                    audio: false
                },
                // Then try minimum viable settings
                {
                    video: true,
                    audio: false
                },
                // Finally try with any available camera
                {
                    video: { facingMode: "user" },
                    audio: false
                }
            ];
            
            // Try each constraint set until one works
            for (const constraint of constraints) {
                try {
                    console.log('Trying constraints:', constraint);
                    stream = await navigator.mediaDevices.getUserMedia(constraint);
                    console.log('Camera access granted with constraints:', constraint);
                    break; // Exit the loop if successful
                } catch (err) {
                    console.log('Failed with constraints:', constraint, 'Error:', err);
                    // Continue to the next constraint set
                    continue;
                }
            }
            
            // If we still don't have a stream after trying all constraints
            if (!stream) {
                if (interviewState.cameraFailedRetryCount < interviewState.maxCameraRetries) {
                    interviewState.cameraFailedRetryCount++;
                    console.log(`Camera initialization failed. Retry attempt ${interviewState.cameraFailedRetryCount}...`);
                    setTimeout(checkCameraPermission, 1000);
                    return;
                } else {
                    console.log('Failed to initialize camera after multiple attempts. Switching to dummy mode.');
                    interviewState.useDummyCamera = true;
                    showDummyCamera();
                    return;
                }
            }
            
            console.log('Camera access granted, got stream:', stream);
            
            // Set up video element with the stream
            if (candidateVideo) {
                candidateVideo.srcObject = stream;
                
                // Make sure the video element is visible
                candidateVideo.style.display = 'block';
                
                // When video starts playing, update the UI
                candidateVideo.onloadedmetadata = function() {
                    console.log('Video metadata loaded, attempting to play');
                    candidateVideo.play().then(() => {
                        console.log('Video playing successfully');
                        
                        // Hide camera status overlay
                        if (cameraStatus) {
                            cameraStatus.style.display = 'none';
                        }
                        
                        // Display the camera controls
                        const cameraControls = document.querySelector('.camera-controls');
                        if (cameraControls) {
                            cameraControls.style.opacity = '1';
                        }
                    }).catch(err => {
                        console.error('Error playing video:', err);
                        showCameraError('Could not play video: ' + err.message);
                    });
                };
                
                // Handle errors during video loading
                candidateVideo.onerror = function(err) {
                    console.error('Error with video element:', err);
                    showCameraError('Video element error');
                };
                
                console.log('Camera initialized successfully');
                return true;
            }
        } catch (error) {
            console.error('Error accessing camera:', error);
            showCameraError(error);
            return false;
        }
    }

    // New function to show dummy camera feed
    function showDummyCamera() {
        if (candidateVideo) {
            // Create a canvas element to generate a dummy video feed
            const canvas = document.createElement('canvas');
            canvas.width = 640;
            canvas.height = 480;
            const ctx = canvas.getContext('2d');
            
            // Create a dummy video stream from the canvas
            const dummyStream = canvas.captureStream(30); // 30 fps
            candidateVideo.srcObject = dummyStream;
            candidateVideo.style.display = 'block';
            
            // Hide camera status overlay
            if (cameraStatus) {
                cameraStatus.style.display = 'none';
            }
            
            // Show camera controls
            const cameraControls = document.querySelector('.camera-controls');
            if (cameraControls) {
                cameraControls.style.opacity = '1';
            }
            
            // Animate the dummy feed
            let hue = 0;
            function drawDummyFrame() {
                // Create a gradient background
                const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                gradient.addColorStop(0, `hsl(${hue}, 100%, 80%)`);
                gradient.addColorStop(1, `hsl(${hue + 60}, 100%, 50%)`);
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Draw text
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.font = 'bold 24px Arial';
                ctx.textAlign = 'center';
                ctx.fillText('Camera Simulation Mode', canvas.width/2, canvas.height/2 - 20);
                ctx.font = '18px Arial';
                ctx.fillText('Interview continues with monitoring disabled', canvas.width/2, canvas.height/2 + 20);
                
                // Update hue for animation
                hue = (hue + 0.5) % 360;
                requestAnimationFrame(drawDummyFrame);
            }
            
            // Start the animation
            drawDummyFrame();
            
            // Add notification about dummy mode
            const cameraCard = candidateVideo.closest('.card');
            if (cameraCard) {
                const notification = document.createElement('div');
                notification.className = 'alert alert-warning mt-2';
                notification.innerHTML = '<strong>Note:</strong> Using simulated camera feed. Monitoring has been disabled.';
                cameraCard.querySelector('.card-body').appendChild(notification);
            }
            
            console.log('Dummy camera display initialized');
            
            // Tell the server that monitoring should be disabled
            interviewState.monitoringEnabled = false;
        }
    }

    // Helper function to show camera error with appropriate message
    function showCameraError(error) {
        // Update camera status to show error with more detailed information
        if (cameraStatus) {
            const cameraConnecting = document.getElementById('cameraConnecting');
            const cameraError = document.getElementById('cameraError');
            const cameraErrorMessage = document.getElementById('cameraErrorMessage');
            
            if (cameraConnecting && cameraError && cameraErrorMessage) {
                cameraConnecting.style.display = 'none';
                cameraError.style.display = 'block';
                
                // Set appropriate error message based on the error type
                let errorMsg = 'Camera error occurred';
                let errorDetails = '';
                
                if (error instanceof Error) {
                    if (error.name === 'NotAllowedError') {
                        errorMsg = 'Camera access denied';
                        errorDetails = 'Please enable camera permissions in your browser settings and refresh the page. Look for the camera icon in your browser address bar.';
                    } else if (error.name === 'NotFoundError') {
                        errorMsg = 'No camera detected';
                        errorDetails = 'Please connect a camera to your device and refresh the page.';
                    } else if (error.name === 'NotReadableError') {
                        errorMsg = 'Camera in use';
                        errorDetails = 'Your camera might be in use by another application. Please close other applications that might be using your camera.';
                    } else if (error.name === 'OverconstrainedError') {
                        errorMsg = 'Camera not compatible';
                        errorDetails = 'Your camera cannot meet the required constraints. Try using a different camera.';
                    } else if (error.name === 'AbortError') {
                        errorMsg = 'Camera access interrupted';
                        errorDetails = 'Something interrupted the camera access process. Please try again.';
                    } else if (error.name === 'CameraDisabled') {
                        errorMsg = 'Camera disabled';
                        errorDetails = 'Camera has been disabled for this interview by the administrator.';
                    } else {
                        errorMsg = `Camera error: ${error.name}`;
                        errorDetails = error.message || 'Unknown error occurred while accessing your camera.';
                    }
                } else if (typeof error === 'string') {
                    errorMsg = 'Camera error';
                    errorDetails = error;
                } else {
                    errorMsg = 'Camera error';
                    errorDetails = 'Unknown error occurred while accessing your camera.';
                }
                
                cameraErrorMessage.innerHTML = `
                    <div>${errorMsg}</div>
                    <small class="d-block mt-2 text-light">${errorDetails}</small>
                `;
                
                // Make sure the retry button is attached and visible
                const retryBtn = document.getElementById('retryCameraBtn');
                if (retryBtn) {
                    retryBtn.style.display = 'inline-block';
                }
            }
        }
        
        // Hide the video element since it's not working
        if (candidateVideo) {
            candidateVideo.style.display = 'none';
        }
        
        // Log the error for debugging
        console.error('Camera error displayed to user:', error);
    }

    // Setup fullscreen button for camera
    const fullscreenCamera = document.getElementById('fullscreenCamera');
    if (fullscreenCamera && candidateVideo) {
        fullscreenCamera.addEventListener('click', function() {
            if (candidateVideo.requestFullscreen) {
                candidateVideo.requestFullscreen();
            } else if (candidateVideo.webkitRequestFullscreen) { /* Safari */
                candidateVideo.webkitRequestFullscreen();
            } else if (candidateVideo.msRequestFullscreen) { /* IE11 */
                candidateVideo.msRequestFullscreen();
            }
        });
    }

    // Setup retry camera button
    if (retryCameraBtn) {
        retryCameraBtn.addEventListener('click', function() {
            console.log('Retrying camera access...');
            checkCameraPermission();
        });
    }
}); 