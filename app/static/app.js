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

var LINKS_KEY = 'my_links';

function getLinks() {
    try {
        // console.log(JSON.parse(localStorage.getItem(LINKS_KEY) || '[]'));
        return JSON.parse(localStorage.getItem(LINKS_KEY) || '{}');
    } catch (_) {
        return {};
    }
}

function saveLink(originalUrl, shortCode) {
    var links = getLinks();
    links[originalUrl]=shortCode;
    localStorage.setItem(LINKS_KEY, JSON.stringify(links));
    console.log(links)
    return links;
}

function findLink(originalUrl) {
    var links = getLinks();
    console.log(typeof(links));
    console.log(links);
    try{
        return links[originalUrl]
    }catch(_){
        return null;
    }
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

/* ── Register ───────────────────────── */

(function () {
    var form = document.getElementById('register-form');
    if (!form) return;

    var errorEl = document.getElementById('register-error');

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: form.elements.username.value,
                email: form.elements.email.value,
                password: form.elements.password.value,
            }),
        })
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (body) {
                        throw new Error(body.detail || 'Registration failed');
                    });
                }
                return res.json();
            })
            .then(function () {
                window.location.href = '/web/login';
            })
            .catch(function (err) {
                if (errorEl) errorEl.textContent = err.message;
            });
    });
})();

/* ── Shorten ─────────────────────────── */

(function () {
    var input = document.getElementById('url-input');
    var btn = document.getElementById('shorten-btn');
    var resultEl = document.getElementById('shorten-result');
    var linkEl = document.getElementById('result-link');
    var copyBtn = document.getElementById('copy-btn');
    var listEl = document.getElementById('links-list');
    // if (!input || !btn || !resultEl || !linkEl || !copyBtn || !listEl) return;

    function prependLink(shortCode) {
        var shortUrl = window.location.origin + '/' + shortCode;
        var div = document.createElement('div');
        div.className = 'link-entry shorten-result';

        div.innerHTML =
            '<span class="result-wrap shadow">'+
                `<a id="result-link" href='${shortUrl}' target="_blank" rel="noopener">${shortUrl}</a>`+
            '</span>'+
            '<button id="copy-btn" class="shadow" title="Copy to clipboard">'+
                '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'+
                    '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'+
                    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'+
                '</svg>'+
            '</button>'
        div.querySelector('button').addEventListener('click', function () {
            navigator.clipboard.writeText(shortUrl);
        });
        listEl.insertBefore(div, listEl.firstChild);
    }

    function renderLinks(links) {
        try{
            Object.keys(links).forEach(key => {
                let shortCode = links[key]  
                prependLink(shortCode)                
            });
        }catch(e){
            console.log(e)
        }
    }

    renderLinks(getLinks());

    var btnHtml = btn.innerHTML;

    function setLoading(loading) {
        btn.disabled = loading;
        if (loading) {
            input.value = '';
            btn.innerHTML = '<span class="spinner"></span> Shortening\u2026';
        } else {
            btn.innerHTML = btnHtml;
        }
    }

    btn.addEventListener('click', function () {
        var url = input.value.trim();
        if (!url) return;

        var cached = findLink(url);
        if (cached) {
            input.value = '';
            prependLink(cached);
            return;
        }

        setLoading(true);

        fetch('/shorten', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_url: url }),
        })
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (body) {
                        throw new Error(body.detail || 'Failed to shorten');
                    });
                }
                return res.json();
            })
            .then(function (data) {
                saveLink(url, data.short_url_code);
                prependLink(data.short_url_code);
            })
            .catch(function (err) {
                console.error('Shorten failed:', err);
            })
            .finally(function () {
                setLoading(false);
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
            window.location.href = '/web/';
        });
    }
})();
