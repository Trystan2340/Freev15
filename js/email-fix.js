        // ── Fix email : reconstruit le mailto en JS (contourne Cloudflare) ────
        (function() {
            var u = 'trystan.bonnin27';
            var d = 'icloud.com';
            var e = u + '\u0040' + d;
            var m = 'mailto:' + e;
            document.querySelectorAll('.email-link').forEach(function(a) {
                a.href = m;
            });
            document.querySelectorAll('.email-text').forEach(function(a) {
                a.textContent = e;
            });
        })();
