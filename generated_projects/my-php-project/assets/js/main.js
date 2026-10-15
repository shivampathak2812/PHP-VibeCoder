document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            let isValid = true;

            const email = document.getElementById('email');
            const password = document.getElementById('password');
            const emailError = document.getElementById('emailError');
            const passwordError = document.getElementById('passwordError');

            emailError.textContent = '';
            passwordError.textContent = '';

            if (!email.value.trim()) {
                emailError.textContent = 'Email is required.';
                isValid = false;
            } else if (!validateEmail(email.value.trim())) {
                emailError.textContent = 'Please enter a valid email address.';
                isValid = false;
            }

            if (!password.value) {
                passwordError.textContent = 'Password is required.';
                isValid = false;
            }

            if (!isValid) {
                e.preventDefault();
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            let isValid = true;

            const fullName = document.getElementById('full_name');
            const email = document.getElementById('email');
            const password = document.getElementById('password');
            const confirmPassword = document.getElementById('confirm_password');

            const nameError = document.getElementById('nameError');
            const emailError = document.getElementById('emailError');
            const passwordError = document.getElementById('passwordError');
            const confirmPasswordError = document.getElementById('confirmPasswordError');

            nameError.textContent = '';
            emailError.textContent = '';
            passwordError.textContent = '';
            confirmPasswordError.textContent = '';

            if (!fullName.value.trim()) {
                nameError.textContent = 'Full Name is required.';
                isValid = false;
            }

            if (!email.value.trim()) {
                emailError.textContent = 'Email is required.';
                isValid = false;
            } else if (!validateEmail(email.value.trim())) {
                emailError.textContent = 'Please enter a valid email address.';
                isValid = false;
            }

            if (!password.value) {
                passwordError.textContent = 'Password is required.';
                isValid = false;
            } else if (password.value.length < 8) {
                passwordError.textContent = 'Password must be at least 8 characters long.';
                isValid = false;
            }

            if (password.value !== confirmPassword.value) {
                confirmPasswordError.textContent = 'Passwords do not match.';
                isValid = false;
            }

            if (!isValid) {
                e.preventDefault();
            }
        });
    }

    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
});