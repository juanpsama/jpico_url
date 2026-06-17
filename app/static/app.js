var TOKEN_KEY = 'access_token';

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

/* ── Navbar toggle ──────────────────── */

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

/* ── Login ──────────────────────────── */

(function () {
    var form = document.getElementById('login-form');
    if (!form) return;

    var errorEl = document.getElementById('login-error');

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        var data = new URLSearchParams();
        data.set('username', form.elements.username.value);
        data.set('password', form.elements.password.value);

        fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: data,
        })
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (body) {
                        throw new Error(body.detail || 'Login failed');
                    });
                }
                return res.json();
            })
            .then(function (json) {
                setToken(json.access_token);
                window.location.href = '/web/dashboard';
            })
            .catch(function (err) {
                errorEl.textContent = err.message;
            });
    });
})();

/* ── Dashboard ──────────────────────── */

(function () {
    var dashboardEl = document.getElementById('dashboard');
    if (!dashboardEl) return;

    var token = getToken();
    if (!token) {
        window.location.href = '/web/login';
        return;
    }

    var welcomeEl = document.getElementById('welcome-username');
    var logoutBtn = document.getElementById('logout-btn');

    fetch('/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token },
    })
        .then(function (res) {
            if (!res.ok) {
                throw new Error('Session expired');
            }
            return res.json();
        })
        .then(function (user) {
            if (welcomeEl) welcomeEl.textContent = user.username;
            var infoUsername = document.getElementById('info-username');
            var infoEmail = document.getElementById('info-email');
            var infoJoined = document.getElementById('info-joined');
            if (infoUsername) infoUsername.textContent = user.username;
            if (infoEmail) infoEmail.textContent = user.email;
            if (infoJoined) infoJoined.textContent = new Date(user.created_at).toLocaleDateString();
        })
        .catch(function () {
            clearToken();
            window.location.href = '/web/login';
        });

    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            clearToken();
            window.location.href = '/web';
        });
    }
})();
