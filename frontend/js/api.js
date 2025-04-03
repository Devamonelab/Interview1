/**
 * API Utilities for InterviewAI Platform
 * This file contains all the functions for communicating with the backend API
 */

const API = {
    // Base URL for API requests - change this to your server URL
    baseURL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? `${window.location.protocol}//${window.location.hostname}:5000` 
        : '',  // Empty string means it will use the same server that hosts the frontend
    
    // Max API retries on failure
    maxRetries: 3,
    
    // Generic fetch with retry logic
    fetchWithRetry: async (url, options, retries = 0) => {
        try {
            console.log(`Fetching ${url}, attempt ${retries + 1}/${API.maxRetries + 1}`);
            const response = await fetch(url, options);
            
            // Check if we received a 429 (Too Many Requests) or 503 (Service Unavailable)
            if ((response.status === 429 || response.status === 503) && retries < API.maxRetries) {
                // Exponential backoff
                const delay = Math.min(1000 * Math.pow(2, retries), 10000);
                console.log(`Rate limited or server unavailable. Retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return API.fetchWithRetry(url, options, retries + 1);
            }
            
            // Check for other error status codes
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `HTTP error ${response.status}` }));
                throw new Error(errorData.error || `Request failed with status ${response.status}`);
            }
            
            return response;
        } catch (error) {
            // Network errors or other fetch failures
            if (retries < API.maxRetries && !error.message.includes('Failed to fetch')) {
                const delay = Math.min(1000 * Math.pow(2, retries), 10000);
                console.log(`Network error. Retrying in ${delay}ms...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                return API.fetchWithRetry(url, options, retries + 1);
            }
            throw error;
        }
    },
    
    // Admin API Methods
    admin: {
        /**
         * Set up a new interview for a candidate
         * @param {Object} setupData - Interview setup data
         * @returns {Promise<Object>} Response from the server
         */
        setupInterview: async (setupData) => {
            try {
                console.log("Setting up interview with data:", setupData);
                console.log("API base URL:", API.baseURL);
                
                // Create form data for multipart upload (for PDF resume)
                const formData = new FormData();
                
                // Add all regular fields
                formData.append('candidate_name', setupData.candidateName);
                formData.append('num_questions', setupData.numQuestions);
                formData.append('admin_instructions', setupData.adminInstructions);
                formData.append('interview_time', setupData.interviewTime);
                formData.append('voice', setupData.voiceEnabled);
                formData.append('monitoring', setupData.monitoringEnabled);
                
                // Add question categories
                formData.append('project_on_resume', setupData.projectQuestions);
                formData.append('skills_evaluations', setupData.skillsQuestions);
                formData.append('tough_technical_question', setupData.technicalQuestions);
                formData.append('scenario_based_question', setupData.scenarioQuestions);
                
                // Add resume - either as PDF file or text
                if (setupData.resumeFile) {
                    formData.append('resume_pdf', setupData.resumeFile);
                } else if (setupData.resumeText) {
                    formData.append('resume_text', setupData.resumeText);
                }
                
                console.log("Sending API request to:", `${API.baseURL}/admin`);
                const response = await API.fetchWithRetry(`${API.baseURL}/admin`, {
                    method: 'POST',
                    body: formData,
                });
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },
        
        /**
         * Get interview results for a candidate
         * @param {string} candidateName - Name of the candidate
         * @returns {Promise<Object>} Interview results
         */
        getInterviewResults: async (candidateName) => {
            try {
                const response = await API.fetchWithRetry(
                    `${API.baseURL}/admin_results?candidate_name=${encodeURIComponent(candidateName)}&result=true`
                );
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        }
    },
    
    // Candidate API Methods
    candidate: {
        /**
         * Start the interview process for a candidate
         * @param {string} candidateName - Candidate's name
         * @returns {Promise<Object>} First question and instructions
         */
        startInterview: async (candidateName) => {
            try {
                const response = await API.fetchWithRetry(`${API.baseURL}/candidate_text`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        candidate_name: candidateName,
                        candidate_answer: "I'm ready to begin the interview.",
                    }),
                });
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },
        
        /**
         * Submit a text answer for a question
         * @param {string} candidateName - Candidate's name
         * @param {string} answer - Candidate's text answer
         * @param {boolean} voiceEnabled - Whether voice is enabled
         * @returns {Promise<Object>} Next question, feedback, etc.
         */
        submitTextAnswer: async (candidateName, answer, voiceEnabled = false) => {
            try {
                const response = await API.fetchWithRetry(`${API.baseURL}/candidate_text`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        candidate_name: candidateName,
                        candidate_answer: answer,
                        voice: voiceEnabled
                    }),
                });
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },
        
        /**
         * Start voice recording for an answer
         * @param {string} candidateName - Candidate's name
         * @param {boolean} voiceEnabled - Whether voice is enabled
         * @returns {Promise<Object>} Recording status
         */
        startRecording: async (candidateName, voiceEnabled = true) => {
            try {
                const response = await API.fetchWithRetry(`${API.baseURL}/candidate_voice`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        candidate_name: candidateName,
                        action: 'start',
                        voice: voiceEnabled
                    }),
                });
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },
        
        /**
         * Stop voice recording and submit the answer
         * @param {string} candidateName - Candidate's name
         * @param {boolean} voiceEnabled - Whether voice is enabled
         * @returns {Promise<Object>} Next question, feedback, etc.
         */
        stopRecording: async (candidateName, voiceEnabled = true) => {
            try {
                const response = await API.fetchWithRetry(`${API.baseURL}/candidate_voice`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        candidate_name: candidateName,
                        action: 'stop',
                        voice: voiceEnabled
                    }),
                });
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },
        
        /**
         * Request the current question to be spoken
         * @param {string} candidateName - Candidate's name
         * @returns {Promise<Object>} Speak status
         */
        speakQuestion: async (candidateName) => {
            try {
                const response = await API.fetchWithRetry(
                    `${API.baseURL}/speak_question?candidate_name=${encodeURIComponent(candidateName)}`
                );
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        }
    }
};

// Export the API object for use in other scripts
window.API = API; 