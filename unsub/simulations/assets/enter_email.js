document.getElementById("unsubscribeForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent actual form submission

    const email = document.getElementById("email").value.trim();
    const checkboxes = document.querySelectorAll('input[name="subscriptions"]:checked');

    if (email === "annabelle.lee@gmail.com" && checkboxes.length === 0) {
        window.location.href = "/updated_success";
    } else {
        window.location.href = "/updated_failure";
    }
});