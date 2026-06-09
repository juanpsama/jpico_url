document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.querySelector('.navbar-toggle');
    var items = document.querySelector('.navbar-items');

    if (toggle && items) {
        toggle.addEventListener('click', function () {
            var isOpen = items.classList.toggle('open');
            toggle.textContent = isOpen ? '\u2715' : '\u2630';
        });
    }
});
