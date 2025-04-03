/**
 * Main JavaScript for InterviewAI Platform
 * Contains shared functionality and utilities
 */

document.addEventListener('DOMContentLoaded', () => {
    // Handle error responses from API
    window.handleApiError = (error) => {
        console.error('API Error:', error);
        
        // Check if the error message is available
        const errorMessage = error.message || 'An unknown error occurred';
        
        // Show an alert with the error message
        alert(`Error: ${errorMessage}`);
        
        return errorMessage;
    };
    
    // Toast notification system
    window.showToast = (message, type = 'info') => {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create a unique ID for this toast
        const toastId = 'toast-' + Date.now();
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.setAttribute('id', toastId);
        
        // Create toast content
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add toast to container
        toastContainer.appendChild(toast);
        
        // Initialize and show the toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove the toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    };
    
    // Utility for formatting dates
    window.formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    };
    
    // Utility for checking if a string is empty
    window.isEmpty = (str) => {
        return !str || str.trim() === '';
    };
    
    // Add animation to features on scroll
    const animateOnScroll = () => {
        const elements = document.querySelectorAll('.feature-card');
        elements.forEach(el => {
            const position = el.getBoundingClientRect();
            // If element is in viewport
            if (position.top < window.innerHeight && position.bottom >= 0) {
                el.classList.add('animated');
            }
        });
    };
    
    // Listen for scroll events to trigger animations
    window.addEventListener('scroll', animateOnScroll);
    
    // Trigger once on page load
    animateOnScroll();
}); 