document.addEventListener('DOMContentLoaded', () => {
    // Example starter JavaScript for disabling form submissions if there are invalid fields
    (() => {
        'use strict'

        // Fetch all the forms we want to apply custom Bootstrap validation styles to
        const forms = document.querySelectorAll('.needs-validation')

        // Loop over them and prevent submission
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault()
                    event.stopPropagation()
                }

                form.classList.add('was-validated')
            }, false)
        })
    })()

    const savedTheme = localStorage.getItem("bs-theme");
    if (savedTheme) {
        document.documentElement.setAttribute("data-bs-theme", savedTheme);
    }
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", function (e) {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute("data-bs-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-bs-theme", newTheme);
            localStorage.setItem("bs-theme", newTheme);
        });
    }
});

if (localStorage.getItem("theme") === "dark") {
    document.documentElement.setAttribute("data-bs-theme", "dark");
}

// 点击按钮时切换主题
function toggleTheme() {
    const html = document.documentElement;
    if (html.getAttribute("data-bs-theme") === "dark") {
        html.removeAttribute("data-bs-theme");
        localStorage.removeItem("theme");
    } else {
        html.setAttribute("data-bs-theme", "dark");
        localStorage.setItem("theme", "dark");
    }
}
