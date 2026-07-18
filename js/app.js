        // --- 1. Background Animation (Constellation Effect) ---
        const canvas = document.getElementById('hero-canvas');
        if (canvas && canvas.parentElement !== document.body) {
            canvas.setAttribute('aria-hidden', 'true');
            document.body.insertBefore(canvas, document.body.firstChild);
        }
        const ctx = canvas.getContext('2d');
        let width, height;
        let particles = [];
        let hubs = [];
        let nebulaBlobs = [];
        let sparks = [];
        let dataPulses = [];
        let canvasFrameId = null;
        let canvasIsVisible = true;
        let frameCount = 0;
        let hueShift = 0;
        let pulseTimer = 0;
        let supernovaTimer = 0;
        let lightningBolts = [];
        let lightningTimer = 0;
        let flashIntensity = 0;
        let sphereMorph = 0;
        let sphereTargetMorph = 0;
        let lastCanvasTime = 0;
        let canvasFrameDelta = 16;
        let cursorRingAngle = 0;
        let cursorTrail = [];
        const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const isLowPower = (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4)
            || (navigator.deviceMemory && navigator.deviceMemory <= 4)
            || /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
        let scrollOffset = window.scrollY || 0;
        window.addEventListener('scroll', updateScrollState, { passive: true });
        const LINK_DISTANCE = 190;
        const MOUSE_LINK_DISTANCE = 230;
        const mouse = { x: -9999, y: -9999, active: false };
        let shootingStars = [];
        let shootingStarTimer = 0;

        function clamp(value, min, max) {
            return Math.max(min, Math.min(max, value));
        }

        function smoothstep(value) {
            const t = clamp(value, 0, 1);
            return t * t * (3 - 2 * t);
        }

        function updateScrollState() {
            scrollOffset = window.scrollY || 0;
            const viewportHeight = height || window.innerHeight || 1;
            const start = Math.max(90, viewportHeight * 0.16);
            const end = Math.max(start + 260, viewportHeight * 0.9);
            const rawProgress = (scrollOffset - start) / (end - start);
            const nextTarget = smoothstep(rawProgress);
            sphereTargetMorph = prefersReducedMotion ? (nextTarget > 0.15 ? 1 : 0) : nextTarget;
        }

        function getSphereVisualState() {
            const shortSide = Math.min(width, height);
            const radius = Math.min(
                shortSide * (width < 640 ? 0.34 : 0.3),
                width * (width < 900 ? 0.36 : 0.18),
                330
            );
            const centerX = width * (width < 900 ? 0.5 : 0.72) + Math.sin(frameCount * 0.006) * 14 * sphereMorph;
            const centerY = height * (width < 640 ? 0.46 : 0.52) + Math.cos(frameCount * 0.005) * 10 * sphereMorph;
            return { x: centerX, y: centerY, radius };
        }

        function assignSphereTargets() {
            const total = Math.max(1, particles.length);
            const goldenAngle = Math.PI * (3 - Math.sqrt(5));
            particles.forEach((particle, index) => {
                const y = 1 - ((index + 0.5) / total) * 2;
                const ringRadius = Math.sqrt(Math.max(0, 1 - y * y));
                const theta = index * goldenAngle;
                particle.sphereX = Math.cos(theta) * ringRadius;
                particle.sphereY = y;
                particle.sphereZ = Math.sin(theta) * ringRadius;
                particle.spherePhase = Math.random() * Math.PI * 2;
            });
        }

        function projectParticleOnSphere(particle) {
            const sphere = getSphereVisualState();
            const rotationY = frameCount * (prefersReducedMotion ? 0.0015 : 0.008);
            const rotationX = -0.32 + Math.sin(frameCount * 0.003) * 0.12;
            const wobble = prefersReducedMotion ? 0 : Math.sin(frameCount * 0.014 + particle.spherePhase) * 0.018;
            const sx = particle.sphereX * (1 + wobble);
            const sy = particle.sphereY;
            const sz = particle.sphereZ * (1 - wobble);

            const cosX = Math.cos(rotationX);
            const sinX = Math.sin(rotationX);
            const yTilt = sy * cosX - sz * sinX;
            const zTilt = sy * sinX + sz * cosX;

            const cosY = Math.cos(rotationY);
            const sinY = Math.sin(rotationY);
            const xRot = sx * cosY + zTilt * sinY;
            const zRot = -sx * sinY + zTilt * cosY;

            const zPx = zRot * sphere.radius;
            const perspective = 900 / (900 - zPx * 0.55);
            const light = clamp((zRot + 1) / 2, 0, 1);

            return {
                x: sphere.x + xRot * sphere.radius * perspective,
                y: sphere.y + yTilt * sphere.radius * perspective,
                scale: 0.78 + perspective * 0.22,
                light
            };
        }

        function projectParticleAtHome(particle) {
            if (prefersReducedMotion) {
                return { x: particle.homeX, y: particle.homeY, scale: 1, light: 0.5 };
            }
            const driftX = Math.sin(frameCount * 0.004 + particle.homePhase) * particle.homeDrift;
            const driftY = Math.cos(frameCount * 0.003 + particle.homePhase * 0.7) * particle.homeDrift * 0.7;
            return {
                x: particle.homeX + driftX,
                y: particle.homeY + driftY,
                scale: 1,
                light: 0.5
            };
        }

        function resize() {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            initParticles();
            initNebula();
            updateScrollState();
        }
        window.addEventListener('resize', resize);

        window.addEventListener('pointermove', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
            mouse.active = mouse.x >= 0 && mouse.x <= width && mouse.y >= 0 && mouse.y <= height;
        });
        document.addEventListener('mouseleave', () => { mouse.active = false; });
        window.addEventListener('blur', () => { mouse.active = false; });
        window.addEventListener('pointerdown', (e) => {
            if (prefersReducedMotion) return;
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left, y = e.clientY - rect.top;
            if (x < 0 || x > width || y < 0 || y > height) return;
            spawnBurst(x, y);
        });

        const PARTICLE_COLORS = ['#22d3ee', '#a855f7', '#818cf8'];
        const HUB_HUES = [192, 271, 234]; // cyan, violet, indigo — couleurs de marque en teinte HSL

        function hslToRgb(h, s, l) {
            h = ((h % 360) + 360) % 360;
            const c = (1 - Math.abs(2 * l - 1)) * s;
            const x = c * (1 - Math.abs((h / 60) % 2 - 1));
            const m = l - c / 2;
            let r = 0, g = 0, b = 0;
            if (h < 60) { r = c; g = x; b = 0; }
            else if (h < 120) { r = x; g = c; b = 0; }
            else if (h < 180) { r = 0; g = c; b = x; }
            else if (h < 240) { r = 0; g = x; b = c; }
            else if (h < 300) { r = x; g = 0; b = c; }
            else { r = c; g = 0; b = x; }
            return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255), b: Math.round((b + m) * 255) };
        }

        class Particle {
            constructor() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.homeX = this.x;
                this.homeY = this.y;
                this.homePhase = Math.random() * Math.PI * 2;
                this.homeDrift = 8 + Math.random() * 20;
                // Profondeur : 0.55 (lointain, petit, discret) à 1.65 (proche, gros, lumineux).
                this.depth = 0.55 + Math.random() * 1.1;
                const speed = (prefersReducedMotion ? 0.15 : 0.45) * this.depth;
                this.vx = (Math.random() - 0.5) * speed;
                this.vy = (Math.random() - 0.5) * speed;
                this.baseSize = (Math.random() * 1.3 + 0.9) * this.depth;
                this.size = this.baseSize;
                this.baseHue = HUB_HUES[Math.floor(Math.random() * HUB_HUES.length)] + (Math.random() * 10 - 5);
                this.currentColor = { r: 255, g: 255, b: 255 };
                this.twinklePhase = Math.random() * Math.PI * 2;
                this.twinkleSpeed = 0.015 + Math.random() * 0.02;
                this.baseAlpha = Math.min(1, 0.35 + this.depth * 0.4);
                this.alpha = this.baseAlpha;
                this.isHub = false;
                this.spawnFrame = frameCount;
                this.introDuration = 70 + Math.random() * 40;
                this.introEase = 0;
                this.impactBoost = 0;
                this.sphereX = 0;
                this.sphereY = 0;
                this.sphereZ = 0;
                this.spherePhase = 0;
                this.sphereScale = 1;
                this.sphereLight = 0.5;
            }
            update() {
                const freeWeight = 1 - sphereMorph * 0.92;
                this.x += this.vx * freeWeight;
                this.y += this.vy * freeWeight;
                if (this.x < 0 || this.x > width) this.vx *= -1;
                if (this.y < 0 || this.y > height) this.vy *= -1;

                // Douce répulsion autour du curseur, plus marquée pour les particules "proches".
                if (mouse.active && sphereMorph < 0.95) {
                    const dx = this.x - mouse.x;
                    const dy = this.y - mouse.y;
                    const dist = Math.hypot(dx, dy);
                    if (dist < 110 && dist > 0.01) {
                        const force = (110 - dist) / 110 * 0.6 * this.depth * (1 - sphereMorph * 0.7);
                        this.x += (dx / dist) * force;
                        this.y += (dy / dist) * force;
                    }
                }

                // Légère attraction vers l'étoile-hub la plus proche : le nuage se structure
                // naturellement en petits amas au lieu d'une marche aléatoire pure.
                if (!this.isHub && hubs.length && sphereMorph < 0.85) {
                    let nearestHub = null, nearestDist = Infinity;
                    for (let i = 0; i < hubs.length; i++) {
                        const d = Math.hypot(this.x - hubs[i].x, this.y - hubs[i].y);
                        if (d < nearestDist) { nearestDist = d; nearestHub = hubs[i]; }
                    }
                    if (nearestHub && nearestDist > 40 && nearestDist < 260) {
                        const pull = 0.012 * (1 - sphereMorph);
                        this.x += (nearestHub.x - this.x) / nearestDist * pull;
                        this.y += (nearestHub.y - this.y) / nearestDist * pull;
                    }
                }

                if (sphereMorph > 0.001 || sphereTargetMorph > 0.001) {
                    const sphereTarget = projectParticleOnSphere(this);
                    const homeTarget = projectParticleAtHome(this);
                    const blend = smoothstep(sphereMorph);
                    const targetX = homeTarget.x + (sphereTarget.x - homeTarget.x) * blend;
                    const targetY = homeTarget.y + (sphereTarget.y - homeTarget.y) * blend;
                    const morphEase = prefersReducedMotion ? 0.58 : 1 - Math.exp(-canvasFrameDelta / (sphereTargetMorph > sphereMorph ? 180 : 130));
                    this.x += (targetX - this.x) * morphEase;
                    this.y += (targetY - this.y) * morphEase;
                    this.sphereScale = homeTarget.scale + (sphereTarget.scale - homeTarget.scale) * blend;
                    this.sphereLight = homeTarget.light + (sphereTarget.light - homeTarget.light) * blend;
                } else {
                    this.sphereScale += (1 - this.sphereScale) * 0.08;
                    this.sphereLight += (0.5 - this.sphereLight) * 0.08;
                }

                this.twinklePhase += this.twinkleSpeed;
                const sphereSizeBoost = 1 + sphereMorph * (0.35 + this.sphereLight * 0.25);
                this.size = (this.baseSize + Math.sin(this.twinklePhase) * 0.5 * this.depth) * this.sphereScale * sphereSizeBoost;
                this.currentColor = hslToRgb(this.baseHue + hueShift, 0.82, 0.62);
                this.alpha = Math.min(1, this.baseAlpha + sphereMorph * (0.16 + this.sphereLight * 0.22));

                // Apparition en fondu/zoom à la création (chargement de page ou redimensionnement).
                const introT = Math.min(1, (frameCount - this.spawnFrame) / this.introDuration);
                this.introEase = 1 - Math.pow(1 - introT, 3);

                if (this.impactBoost > 0) this.impactBoost = Math.max(0, this.impactBoost - 0.03);
            }
            draw() {
                const rgb = this.currentColor;
                const colorStr = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
                const boost = this.impactBoost || 0;
                const displaySize = (Math.max(0.4, this.size) + boost * 1.6) * this.introEase;
                ctx.save();
                ctx.globalAlpha = Math.min(1, this.alpha + boost * 0.35) * this.introEase;
                ctx.shadowColor = colorStr;
                ctx.shadowBlur = (this.isHub ? (12 + Math.sin(frameCount * 0.05 + this.twinklePhase) * 4) : (4 + this.depth * 5)) + boost * 10;
                if (this.isHub) {
                    const flare = this.size * 4.4 * this.introEase;
                    ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${0.45 * this.alpha})`;
                    ctx.lineWidth = 0.7;
                    ctx.beginPath();
                    ctx.moveTo(this.x - flare, this.y); ctx.lineTo(this.x + flare, this.y);
                    ctx.moveTo(this.x, this.y - flare); ctx.lineTo(this.x, this.y + flare);
                    ctx.stroke();
                }
                ctx.beginPath();
                ctx.arc(this.x, this.y, displaySize, 0, Math.PI * 2);
                ctx.fillStyle = colorStr;
                ctx.fill();
                ctx.restore();
            }
        }

        function initParticles() {
            particles = [];
            const baseCount = window.innerWidth < 640 ? 42 : 74;
            const count = isLowPower ? Math.round(baseCount * 0.6) : baseCount;
            for (let i = 0; i < count; i++) particles.push(new Particle());
            particles.sort((a, b) => a.depth - b.depth); // lointain dessiné en premier
            [...particles].sort((a, b) => b.depth - a.depth).slice(0, Math.min(7, particles.length)).forEach((p) => { p.isHub = true; });
            hubs = particles.filter((p) => p.isHub);
            assignSphereTargets();
        }

        function initNebula() {
            const span = Math.max(width, height);
            nebulaBlobs = [
                { x: width * 0.18, y: height * 0.28, r: span * 0.4, hue: 192, vx: 0.04, vy: 0.025 },
                { x: width * 0.82, y: height * 0.62, r: span * 0.44, hue: 271, vx: -0.035, vy: 0.02 },
                { x: width * 0.48, y: height * 0.88, r: span * 0.32, hue: 234, vx: 0.025, vy: -0.035 }
            ];
        }

        function drawNebula() {
            if (prefersReducedMotion) return;
            const parallaxX = mouse.active ? (mouse.x - width / 2) * 0.02 : 0;
            const parallaxY = (mouse.active ? (mouse.y - height / 2) * 0.02 : 0) - Math.min(scrollOffset, height) * 0.04 * (1 - sphereMorph);
            nebulaBlobs.forEach((b) => {
                b.x += b.vx; b.y += b.vy;
                if (b.x < -b.r * 0.4 || b.x > width + b.r * 0.4) b.vx *= -1;
                if (b.y < -b.r * 0.4 || b.y > height + b.r * 0.4) b.vy *= -1;
                const cx = b.x + parallaxX, cy = b.y + parallaxY;
                const rgb = hslToRgb(b.hue + hueShift * 0.6, 0.85, 0.55);
                const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, b.r);
                grad.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.14)`);
                grad.addColorStop(1, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0)`);
                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(cx, cy, b.r, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        function drawSphereGuides() {
            if (sphereMorph <= 0.02) return;
            const sphere = getSphereVisualState();
            const alpha = sphereMorph * (prefersReducedMotion ? 0.16 : 0.28);
            const rotation = frameCount * (prefersReducedMotion ? 0.0008 : 0.006);

            ctx.save();
            ctx.translate(sphere.x, sphere.y);
            ctx.globalAlpha = alpha;

            const glow = ctx.createRadialGradient(0, 0, sphere.radius * 0.12, 0, 0, sphere.radius * 1.18);
            glow.addColorStop(0, 'rgba(34, 211, 238, 0.12)');
            glow.addColorStop(0.55, 'rgba(168, 85, 247, 0.07)');
            glow.addColorStop(1, 'rgba(34, 211, 238, 0)');
            ctx.fillStyle = glow;
            ctx.beginPath();
            ctx.arc(0, 0, sphere.radius * 1.18, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.arc(0, 0, sphere.radius, 0, Math.PI * 2);
            ctx.stroke();

            ctx.strokeStyle = 'rgba(34, 211, 238, 0.34)';
            for (let i = 0; i < 4; i++) {
                ctx.save();
                ctx.rotate(rotation + i * Math.PI / 4);
                ctx.beginPath();
                ctx.ellipse(0, 0, sphere.radius * 0.96, sphere.radius * 0.22, 0, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }

            ctx.strokeStyle = 'rgba(168, 85, 247, 0.28)';
            [-0.46, -0.22, 0.22, 0.46].forEach((offset) => {
                const latitudeRadius = sphere.radius * Math.sqrt(Math.max(0, 1 - offset * offset));
                ctx.beginPath();
                ctx.ellipse(0, sphere.radius * offset, latitudeRadius, latitudeRadius * 0.16, 0, 0, Math.PI * 2);
                ctx.stroke();
            });

            ctx.restore();
        }

        function spawnBurst(x, y) {
            const count = 18;
            for (let i = 0; i < count; i++) {
                const angle = (Math.PI * 2 * i) / count + Math.random() * 0.3;
                const speed = 2 + Math.random() * 3.2;
                sparks.push({ x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: 1, color: PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)] });
            }
            sparks.push({ ring: true, x, y, r: 2, life: 1 });
            sparks.push({ ring: true, x, y, r: 2, life: 1, delay: 8 });
            // Les points existants proches du clic reçoivent un net regain d'éclat.
            particles.forEach((p) => {
                if (Math.hypot(p.x - x, p.y - y) < 220) p.impactBoost = 1;
            });
        }

        function updateDrawSparks() {
            if (!sparks.length) return;
            sparks = sparks.filter((s) => s.life > 0);
            sparks.forEach((s) => {
                if (s.ring) {
                    if (s.delay && s.delay > 0) { s.delay--; return; }
                    s.r += 4;
                    s.life -= 0.03;
                    ctx.save();
                    ctx.strokeStyle = `rgba(255, 255, 255, ${Math.max(0, s.life) * 0.7})`;
                    ctx.lineWidth = 1.8;
                    ctx.beginPath();
                    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
                    ctx.stroke();
                    ctx.restore();
                    return;
                }
                s.x += s.vx; s.y += s.vy;
                s.vx *= 0.96; s.vy *= 0.96;
                s.life -= 0.02;
                const c = hexToRgb(s.color);
                ctx.save();
                ctx.shadowColor = s.color;
                ctx.shadowBlur = 8;
                ctx.beginPath();
                ctx.arc(s.x, s.y, Math.max(0, 1.6 * s.life), 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${c.r}, ${c.g}, ${c.b}, ${Math.max(0, s.life)})`;
                ctx.fill();
                ctx.restore();
            });
        }

        function hexToRgb(hex) {
            const v = parseInt(hex.slice(1), 16);
            return { r: (v >> 16) & 255, g: (v >> 8) & 255, b: v & 255 };
        }

        function drawLink(x1, y1, x2, y2, alpha, c1, c2, lineWidth) {
            const gradient = ctx.createLinearGradient(x1, y1, x2, y2);
            gradient.addColorStop(0, `rgba(${c1.r}, ${c1.g}, ${c1.b}, ${alpha})`);
            gradient.addColorStop(1, `rgba(${c2.r}, ${c2.g}, ${c2.b}, ${alpha})`);
            ctx.strokeStyle = gradient;
            ctx.lineWidth = lineWidth;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }

        // Impulsions lumineuses qui voyagent occasionnellement le long d'une connexion active,
        // pour évoquer une donnée qui circule dans le réseau.
        function maybeSpawnDataPulse() {
            if (prefersReducedMotion) return;
            pulseTimer++;
            if (pulseTimer < 35 || Math.random() > 0.12) return;
            pulseTimer = 0;
            const candidates = [];
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const a = particles[i], b = particles[j];
                    if (Math.hypot(a.x - b.x, a.y - b.y) < LINK_DISTANCE * 0.85) candidates.push([a, b]);
                }
            }
            if (!candidates.length) return;
            const [a, b] = candidates[Math.floor(Math.random() * candidates.length)];
            dataPulses.push({ a, b, t: 0 });
            if (dataPulses.length > 12) dataPulses.shift();
        }

        function drawDataPulses() {
            if (!dataPulses.length) return;
            dataPulses.forEach((p) => {
                if (p.t >= 1 && !p.flashed) {
                    p.flashed = true;
                    sparks.push({ ring: true, x: p.b.x, y: p.b.y, r: 1, life: 0.6 });
                }
            });
            dataPulses = dataPulses.filter((p) => p.t <= 1);
            dataPulses.forEach((p) => {
                const x = p.a.x + (p.b.x - p.a.x) * p.t;
                const y = p.a.y + (p.b.y - p.a.y) * p.t;
                ctx.save();
                ctx.shadowColor = '#ffffff';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.arc(x, y, 1.8, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.fill();
                ctx.restore();
                p.t += 0.025;
            });
        }

        function buildLightningPath(x1, y1, x2, y2) {
            // Déplacement du milieu (midpoint displacement) pour un tracé en zigzag crédible.
            let points = [{ x: x1, y: y1 }, { x: x2, y: y2 }];
            for (let pass = 0; pass < 4; pass++) {
                const next = [points[0]];
                for (let i = 0; i < points.length - 1; i++) {
                    const a = points[i], b = points[i + 1];
                    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
                    const dist = Math.hypot(b.x - a.x, b.y - a.y);
                    const offset = (Math.random() - 0.5) * dist * 0.35;
                    const nx = -(b.y - a.y), ny = (b.x - a.x);
                    const len = Math.hypot(nx, ny) || 1;
                    next.push({ x: mx + (nx / len) * offset, y: my + (ny / len) * offset });
                    next.push(b);
                }
                points = next;
            }
            return points;
        }

        function maybeSpawnLightning() {
            if (prefersReducedMotion || isLowPower || hubs.length < 2) return;
            lightningTimer++;
            if (lightningTimer > 200 && Math.random() < 0.015) {
                lightningTimer = 0;
                const a = hubs[Math.floor(Math.random() * hubs.length)];
                let b = hubs[Math.floor(Math.random() * hubs.length)];
                if (b === a) b = hubs[(hubs.indexOf(a) + 1) % hubs.length];
                lightningBolts.push({ path: buildLightningPath(a.x, a.y, b.x, b.y), life: 1 });
                flashIntensity = Math.min(1, flashIntensity + 0.25);
            }
        }

        function drawLightning() {
            if (!lightningBolts.length) return;
            lightningBolts = lightningBolts.filter((l) => l.life > 0);
            lightningBolts.forEach((l) => {
                l.life -= 0.06;
                ctx.save();
                ctx.shadowColor = '#e0f2fe';
                ctx.shadowBlur = 16;
                ctx.strokeStyle = `rgba(224, 242, 254, ${Math.max(0, l.life)})`;
                ctx.lineWidth = 1.6;
                ctx.beginPath();
                l.path.forEach((p, i) => { i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y); });
                ctx.stroke();
                ctx.restore();
            });
        }

        function maybeSpawnAutoSupernova() {
            if (prefersReducedMotion || isLowPower || !hubs.length) return;
            supernovaTimer++;
            if (supernovaTimer > 240 && Math.random() < 0.012) {
                supernovaTimer = 0;
                const hub = hubs[Math.floor(Math.random() * hubs.length)];
                spawnBurst(hub.x, hub.y);
                flashIntensity = Math.min(1, flashIntensity + 0.35);
            }
        }

        function maybeSpawnShootingStar() {
            if (prefersReducedMotion || isLowPower || shootingStars.length >= 5) return;
            shootingStarTimer++;
            if (shootingStarTimer > 90 && Math.random() < 0.025) {
                shootingStarTimer = 0;
                const isShower = Math.random() < 0.25;
                const count = isShower ? 3 : 1;
                for (let i = 0; i < count; i++) {
                    const startX = Math.random() * width * 0.7;
                    shootingStars.push({
                        x: startX, y: -10 - i * 40,
                        vx: 4.5 + Math.random() * 4, vy: 5.5 + Math.random() * 3,
                        life: 1
                    });
                }
            }
        }

        function drawShootingStar() {
            if (!shootingStars.length) return;
            shootingStars = shootingStars.filter((s) => s.life > 0 && s.y <= height + 20);
            shootingStars.forEach((s) => {
                s.x += s.vx;
                s.y += s.vy;
                s.life -= 0.01;
                const tailX = s.x - s.vx * 11;
                const tailY = s.y - s.vy * 11;
                const grad = ctx.createLinearGradient(s.x, s.y, tailX, tailY);
                grad.addColorStop(0, `rgba(255, 255, 255, ${s.life})`);
                grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
                ctx.save();
                ctx.shadowColor = '#ffffff';
                ctx.shadowBlur = 12;
                ctx.strokeStyle = grad;
                ctx.lineWidth = 2.1;
                ctx.beginPath();
                ctx.moveTo(s.x, s.y);
                ctx.lineTo(tailX, tailY);
                ctx.stroke();
                ctx.restore();
            });
        }

        function drawVignette() {
            const grad = ctx.createRadialGradient(width / 2, height / 2, Math.min(width, height) * 0.32, width / 2, height / 2, Math.max(width, height) * 0.78);
            grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
            grad.addColorStop(1, 'rgba(2, 6, 23, 0.4)');
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, width, height);
        }

        function animateCanvas() {
            if (!canvasIsVisible || document.hidden) {
                canvasFrameId = null;
                return;
            }

            frameCount++;
            const now = performance.now();
            const frameDelta = lastCanvasTime ? Math.min(500, now - lastCanvasTime) : 16;
            lastCanvasTime = now;
            canvasFrameDelta = frameDelta;
            hueShift = Math.sin(frameCount * 0.004) * 26;
            updateScrollState();
            const morphDuration = prefersReducedMotion ? 90 : (sphereTargetMorph > sphereMorph ? 260 : 220);
            const morphStep = 1 - Math.exp(-frameDelta / morphDuration);
            sphereMorph += (sphereTargetMorph - sphereMorph) * morphStep;

            ctx.clearRect(0, 0, width, height);
            ctx.globalCompositeOperation = 'source-over';
            drawNebula();
            ctx.globalCompositeOperation = isLowPower ? 'source-over' : 'lighter';
            drawSphereGuides();

            // Liens entre particules proches : dégradé de couleur + épaisseur selon la proximité et la profondeur.
            const activeLinkDistance = LINK_DISTANCE - sphereMorph * 42;
            particles.forEach((p, index) => {
                p.update();
                for (let j = index + 1; j < particles.length; j++) {
                    const p2 = particles[j];
                    const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                    if (dist < activeLinkDistance) {
                        const proximity = 1 - dist / activeLinkDistance;
                        const avgDepth = (p.depth + p2.depth) / 2;
                        const sphereAlpha = 0.7 + sphereMorph * 0.22;
                        drawLink(p.x, p.y, p2.x, p2.y, proximity * sphereAlpha * avgDepth, p.currentColor, p2.currentColor, 0.5 + proximity * (1.35 + sphereMorph * 0.5) * avgDepth);
                    }
                }
                // Lien vers le curseur : la toile réagit à la souris.
                if (mouse.active && sphereMorph < 0.9) {
                    const distMouse = Math.hypot(p.x - mouse.x, p.y - mouse.y);
                    if (distMouse < MOUSE_LINK_DISTANCE) {
                        const proximity = 1 - distMouse / MOUSE_LINK_DISTANCE;
                        drawLink(p.x, p.y, mouse.x, mouse.y, proximity * 0.5 * (1 - sphereMorph), p.currentColor, { r: 255, g: 255, b: 255 }, 0.4 + proximity * 1.1);
                    }
                }
            });
            particles.forEach((p) => p.draw());
            updateDrawSparks();
            maybeSpawnDataPulse();
            maybeSpawnAutoSupernova();
            maybeSpawnLightning();
            drawLightning();
            drawDataPulses();

            if (mouse.active) {
                cursorTrail.push({ x: mouse.x, y: mouse.y });
                if (cursorTrail.length > 10) cursorTrail.shift();
            } else if (cursorTrail.length) {
                cursorTrail.shift();
            }
            if (cursorTrail.length > 1) {
                for (let i = 1; i < cursorTrail.length; i++) {
                    ctx.strokeStyle = `rgba(255, 255, 255, ${(i / cursorTrail.length) * 0.3})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(cursorTrail[i - 1].x, cursorTrail[i - 1].y);
                    ctx.lineTo(cursorTrail[i].x, cursorTrail[i].y);
                    ctx.stroke();
                }
            }

            if (mouse.active) {
                cursorRingAngle += 0.015;
                ctx.save();
                ctx.translate(mouse.x, mouse.y);
                ctx.rotate(cursorRingAngle);
                ctx.setLineDash([3, 5]);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.arc(0, 0, 15, 0, Math.PI * 2);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.restore();

                ctx.save();
                ctx.shadowColor = '#ffffff';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.arc(mouse.x, mouse.y, 2.2, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(255,255,255,0.9)';
                ctx.fill();
                ctx.restore();
            }

            maybeSpawnShootingStar();
            drawShootingStar();
            ctx.globalCompositeOperation = 'source-over';
            if (flashIntensity > 0.001) {
                ctx.fillStyle = `rgba(255, 255, 255, ${flashIntensity * 0.16})`;
                ctx.fillRect(0, 0, width, height);
                flashIntensity *= 0.88;
            } else {
                flashIntensity = 0;
            }
            drawVignette();

            canvasFrameId = requestAnimationFrame(animateCanvas);
        }

        function startCanvasAnimation() {
            if (canvasFrameId === null) {
                canvasFrameId = requestAnimationFrame(animateCanvas);
            }
        }

        function stopCanvasAnimation() {
            if (canvasFrameId !== null) {
                cancelAnimationFrame(canvasFrameId);
                canvasFrameId = null;
            }
        }

        resize();
        startCanvasAnimation();

        // Le canvas reste actif sur toutes les sections pour garder la sphere visible pendant la navigation.
        canvasIsVisible = true;

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) stopCanvasAnimation();
            else if (canvasIsVisible) startCanvasAnimation();
        });

        // --- 2. Scroll Reveal Animation ---
        const observerOptions = { threshold: 0.1 };
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, observerOptions);

        const revealElements = Array.from(document.querySelectorAll('.reveal'));
        let revealTicking = false;

        function activateVisibleReveals() {
            const activationLine = window.innerHeight * 0.92;
            revealElements.forEach((el) => {
                const rect = el.getBoundingClientRect();
                if (rect.top < activationLine && rect.bottom > -80) {
                    el.classList.add('active');
                }
            });
        }

        function scheduleRevealCheck() {
            if (revealTicking) return;
            revealTicking = true;
            requestAnimationFrame(() => {
                revealTicking = false;
                activateVisibleReveals();
            });
        }

        function activateHashTargetReveals() {
            if (!location.hash || location.hash === '#home') return;
            let target = null;
            try {
                target = document.querySelector(location.hash);
            } catch (error) {
                target = null;
            }
            target?.querySelectorAll('.reveal').forEach((el) => el.classList.add('active'));
        }

        revealElements.forEach(el => observer.observe(el));
        activateVisibleReveals();
        window.addEventListener('load', () => {
            scheduleRevealCheck();
            activateHashTargetReveals();
            setTimeout(activateVisibleReveals, 250);
            setTimeout(activateHashTargetReveals, 450);
        });
        window.addEventListener('hashchange', () => {
            scheduleRevealCheck();
            setTimeout(activateHashTargetReveals, 250);
        });
        window.addEventListener('scroll', scheduleRevealCheck, { passive: true });

        // --- 3. Navbar Interaction (Updated for Floating Pill) ---
        // Mobile Menu
        const btn = document.getElementById('mobile-menu-btn');
        const menu = document.getElementById('mobile-menu');
        let mobileMenuCloseTimer = null;
        
        function openMobileMenu() {
            if (!btn || !menu) return;
            if (mobileMenuCloseTimer) {
                clearTimeout(mobileMenuCloseTimer);
                mobileMenuCloseTimer = null;
            }
            menu.classList.remove('hidden');
            btn.setAttribute('aria-expanded', 'true');
            menu.setAttribute('aria-hidden', 'false');
            requestAnimationFrame(() => {
                menu.classList.remove('opacity-0', 'scale-95', 'translate-y-4');
            });
        }

        function closeMobileMenu() {
            if (!btn || !menu) return;
            menu.classList.add('opacity-0', 'scale-95', 'translate-y-4');
            btn.setAttribute('aria-expanded', 'false');
            menu.setAttribute('aria-hidden', 'true');
            if (mobileMenuCloseTimer) clearTimeout(mobileMenuCloseTimer);
            mobileMenuCloseTimer = setTimeout(() => {
                menu.classList.add('hidden');
                mobileMenuCloseTimer = null;
            }, 250);
        }

        btn?.addEventListener('click', () => {
            if (menu.classList.contains('hidden')) openMobileMenu();
            else closeMobileMenu();
        });

        // Close menu when clicking a link
        document.querySelectorAll('.mobile-link').forEach(link => {
            link.addEventListener('click', closeMobileMenu);
        });

        document.addEventListener('click', (event) => {
            if (!btn || !menu || menu.classList.contains('hidden')) return;
            const target = event.target instanceof Element ? event.target : event.target?.parentElement;
            if (!target) return;
            if (!target.closest('#mobile-menu') && !target.closest('#mobile-menu-btn')) {
                closeMobileMenu();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && menu && !menu.classList.contains('hidden')) {
                closeMobileMenu();
            }
        });

        window.addEventListener('resize', () => {
            if (window.innerWidth >= 768 && menu && !menu.classList.contains('hidden')) {
                closeMobileMenu();
            }
        });

        // --- 4. AI LOGIC ---

        let currentAiMode = 'freev'; // 'freev' | 'custom'
        let currentImageBase64 = null;

        // ── Mode switcher ──────────────────────────────────────────────────────
        const INACTIVE_MODE_BTN = 'px-4 sm:px-5 py-2.5 sm:py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap text-gray-400 hover:text-white';

        function setAiMode(mode) {
            currentAiMode = mode;
            const btnFreev  = document.getElementById('btn-mode-freev');
            const btnCustom = document.getElementById('btn-mode-custom');
            const btnApiSettings = document.getElementById('btn-api-settings');
            const badge     = document.getElementById('ai-mode-badge');
            const header    = document.getElementById('chat-header-label');

            // Reset des boutons
            btnFreev.className  = INACTIVE_MODE_BTN;
            btnCustom.className = INACTIVE_MODE_BTN;
            document.getElementById('api-settings-custom').classList.add('hidden');

            if (mode === 'freev') {
                btnFreev.className  = 'px-4 sm:px-5 py-2.5 sm:py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap bg-gradient-to-r from-brand-accent to-brand-secondary text-brand-dark shadow';
                btnApiSettings.classList.add('hidden');
                badge.innerHTML   = '<i class="fa-solid fa-cube"></i> Freev AI — FreevBrain v5 En ligne';
                badge.className   = 'inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-bold mb-4 border border-cyan-500/20';
                header.innerHTML  = '<i class="fa-solid fa-cube text-brand-accent"></i> FreevBrain v5 (en ligne)';
                checkServer();
            } else {
                // mode === 'custom' (ChatGPT, Gemini, Hermes 4, OpenRouter, NVIDIA, Ollama, Kimi, Qwen, Groq, DeepSeek, Mistral, Together, etc.)
                btnCustom.className = 'px-4 sm:px-5 py-2.5 sm:py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white shadow';
                btnApiSettings.classList.remove('hidden');
                loadCustomConfig();
                const modelLabel = document.getElementById('custom-model-name')?.value || 'modèle personnalisé';
                badge.innerHTML   = '<i class="fa-solid fa-plug"></i> Autre IA — ' + escapeHtml(modelLabel);
                badge.className   = 'inline-flex items-center gap-2 px-3 py-1 rounded-full bg-fuchsia-500/10 text-fuchsia-400 text-xs font-bold mb-4 border border-fuchsia-500/20';
                header.innerHTML  = '<i class="fa-solid fa-plug text-fuchsia-400"></i> ' + escapeHtml(modelLabel);
            }
        }

        // Affiche le panneau de configuration du fournisseur personnalisé
        function toggleApiSettings() {
            if (currentAiMode === 'custom') {
                document.getElementById('api-settings-custom').classList.toggle('hidden');
            }
        }

        // ── Fiabilité : état de génération, annulation, timeouts ────────────────
        let freevIsGenerating = false;
        let freevActiveController = null;

        function setGeneratingState(isGenerating) {
            freevIsGenerating = isGenerating;
            const icon = document.getElementById('ai-send-btn-icon');
            const btn  = document.getElementById('ai-send-btn');
            if (!icon || !btn) return;
            if (isGenerating) {
                icon.className = 'fa-solid fa-stop';
                btn.title = 'Arrêter la génération';
                btn.classList.add('text-red-400');
            } else {
                icon.className = 'fa-solid fa-paper-plane';
                btn.title = 'Envoyer';
                btn.classList.remove('text-red-400');
            }
        }

        function stopGeneration() {
            if (freevActiveController) {
                freevActiveController.abort('user-stop');
            }
        }

        // Message d'erreur clair selon le type de panne (réseau, CORS, timeout, HTTP...)
        function describeRequestError(err, { timedOut = false, httpStatus = null } = {}) {
            if (timedOut) return "Délai dépassé — le serveur met trop de temps à répondre.";
            if (err && err.name === 'AbortError') {
                return timedOut ? "Délai dépassé — le serveur met trop de temps à répondre." : "Génération arrêtée.";
            }
            if (httpStatus === 401 || httpStatus === 403) return "Clé API invalide ou manquante. Vérifiez votre configuration.";
            if (httpStatus === 404) return "Modèle ou endpoint introuvable. Vérifiez l'URL de base et le nom du modèle.";
            if (httpStatus === 429) return "Trop de requêtes envoyées (limite atteinte). Réessayez dans un instant.";
            if (httpStatus && httpStatus >= 500) return "Le serveur du fournisseur IA est indisponible pour le moment.";
            if (err instanceof TypeError) return "Impossible de joindre le serveur (réseau coupé, URL invalide, ou CORS bloqué).";
            return err?.message || "Erreur inconnue.";
        }

        // ── Dispatcher ─────────────────────────────────────────────────────────
        function sendMessage() {
            if (freevIsGenerating) {
                stopGeneration();
                return;
            }
            if (currentAiMode === 'custom') generateCustom();
            else generateFreev();
        }

        // ── Freev AI en ligne (FreevBrain v5) ─────────────────────────────────
        // ⚠️ Remplace cette URL par ton URL Render/Railway après déploiement
        const FREEV_SERVER = 'https://freev-iies.onrender.com';
        let serverConnected = false;

        // Vérifier connexion au serveur local au démarrage
        async function checkServer() {
            try {
                const r = await fetch(FREEV_SERVER + '/status', { signal: AbortSignal.timeout(20000) });
                const data = await r.json();
                serverConnected = data.ok;
                updateServerBadge(data);
            } catch {
                serverConnected = false;
                updateServerBadge(null);
            }
        }

        function updateServerBadge(data) {
            const badge = document.getElementById('ai-mode-badge');
            const output = document.getElementById('ai-output');
            if (currentAiMode !== 'freev') return;

            if (serverConnected && data) {
                badge.innerHTML = '<i class="fa-solid fa-circle text-green-400 text-xs"></i> Freev AI — En ligne · ' + data.pairs + ' paires';
                badge.className = 'inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 text-green-400 text-xs font-bold mb-4 border border-green-500/20';
            } else {
                badge.innerHTML = '<i class="fa-solid fa-circle text-yellow-400 text-xs animate-pulse"></i> Freev AI — Réveil du serveur...';
                badge.className = 'inline-flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 text-yellow-400 text-xs font-bold mb-4 border border-yellow-500/20';
            }
        }

        // Vérifier toutes les 30 secondes (serveur en ligne)
        checkServer();
        setInterval(checkServer, 30000);
        // Render Free se réveille en ~50s — on refait un check rapide après 40s
        setTimeout(checkServer, 40000);

        async function generateFreev() {
            const input  = document.getElementById('ai-input');
            const output = document.getElementById('ai-output');
            const prompt = input.value.trim();
            if (!prompt || freevIsGenerating) return;

            // Message utilisateur
            output.innerHTML += `<div class="mt-4 text-white p-3 bg-white/5 rounded-lg border border-white/5"><span class="text-brand-secondary font-bold">Vous :</span> ${escapeHtml(prompt)}</div>`;
            input.value = '';
            output.scrollTop = output.scrollHeight;

            // Si serveur hors ligne → message d'aide
            if (!serverConnected) {
                output.innerHTML += `
                    <div class="mt-3 p-4 bg-slate-800/80 rounded-xl border border-yellow-500/30">
                        <p class="text-yellow-400 font-bold mb-2"><i class="fa-solid fa-hourglass-half mr-2"></i>Freev AI se réveille...</p>
                        <p class="text-gray-400 text-sm mb-2">Le serveur Render (gratuit) dort quand il est inactif. Il se réveille en <strong class="text-white">30–50 secondes</strong>.</p>
                        <p class="text-gray-400 text-sm">Le badge deviendra <strong class="text-green-400">vert</strong> quand il est prêt — réessaie alors.</p>
                        <p class="text-gray-500 text-xs mt-2">Ou bascule sur <strong class="text-brand-primary">un autre modèle</strong> pour une réponse immédiate.</p>
                    </div>`;
                output.scrollTop = output.scrollHeight;
                input.value = prompt; // on ne perd pas la question tapée
                return;
            }

            const loadingId = 'loading-' + Date.now();
            output.innerHTML += `<div id="${loadingId}" class="mt-2 text-gray-500 italic flex items-center gap-2"><i class="fa-solid fa-brain fa-bounce text-brand-accent"></i> FreevBrain réfléchit... <button class="ml-1 text-xs underline text-gray-400 hover:text-white" onclick="stopGeneration()">annuler</button></div>`;
            output.scrollTop = output.scrollHeight;

            const controller = new AbortController();
            freevActiveController = controller;
            setGeneratingState(true);
            let timedOut = false;
            const timeoutId = setTimeout(() => { timedOut = true; controller.abort('timeout'); }, 25000);

            try {
                const r = await fetch(FREEV_SERVER + '/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: prompt }),
                    signal: controller.signal
                });

                if (!r.ok) throw Object.assign(new Error('Erreur serveur ' + r.status), { httpStatus: r.status });
                const data = await r.json();

                document.getElementById(loadingId)?.remove();
                const div = document.createElement('div');
                div.className = 'mt-4 text-gray-200 border-l-2 border-brand-accent pl-4 py-1';
                div.innerHTML = `<span class="text-brand-accent font-bold text-sm mb-1 block"><i class="fa-solid fa-cube mr-1"></i>Freev AI :</span>` + marked.parse(escapeHtml(data.response || ''));
                output.appendChild(div);
                output.scrollTop = output.scrollHeight;

                saveChatHistoryEntry({ mode: 'freev', model: 'FreevBrain v5', question: prompt, response: data.response || '' });

            } catch (err) {
                document.getElementById(loadingId)?.remove();
                const wasUserStop = err?.name === 'AbortError' && !timedOut;
                if (!wasUserStop) {
                    serverConnected = false;
                    updateServerBadge(null);
                }
                const msg = describeRequestError(err, { timedOut, httpStatus: err?.httpStatus });
                const canRetry = !wasUserStop;
                output.innerHTML += `<div class="mt-2 text-red-400 p-2 bg-red-900/20 rounded text-sm flex items-center justify-between gap-2">
                    <span><i class="fa-solid fa-xmark mr-1"></i>${escapeHtml(msg)}</span>
                    ${canRetry ? `<button class="text-xs underline text-red-300 hover:text-white shrink-0" onclick="retryFreevPrompt(this)" data-prompt="${escapeHtml(prompt)}">réessayer</button>` : ''}
                </div>`;
                output.scrollTop = output.scrollHeight;
                if (canRetry) input.value = prompt; // on ne perd pas la question tapée
            } finally {
                clearTimeout(timeoutId);
                freevActiveController = null;
                setGeneratingState(false);
            }
        }

        function retryFreevPrompt(btn) {
            const prompt = btn?.dataset?.prompt;
            if (!prompt) return;
            const input = document.getElementById('ai-input');
            input.value = prompt;
            sendMessage();
        }

        function escapeHtml(t) {
            return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        // ── Historique des conversations (local + IA en ligne) ──────────────────
        const CHAT_HISTORY_KEY = 'freev_chat_history';
        const CHAT_HISTORY_MAX = 300;

        function readChatHistory() {
            try {
                const raw = localStorage.getItem(CHAT_HISTORY_KEY);
                const list = raw ? JSON.parse(raw) : [];
                return Array.isArray(list) ? list : [];
            } catch (e) { return []; }
        }

        function writeChatHistory(list) {
            try { localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(list)); } catch (e) {}
        }

        // Enregistre chaque question + réponse, peu importe si l'IA est locale (Ollama/LM Studio),
        // en ligne (FreevBrain) ou via un fournisseur "Autre IA" (ChatGPT, Gemini, etc.)
        function saveChatHistoryEntry({ mode, model, question, response }) {
            if (!question && !response) return;
            const entry = {
                id: 'h-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7),
                date: new Date().toISOString(),
                mode: mode || 'freev',       // 'freev' (en ligne) | 'custom' (autre IA / local)
                model: model || (mode === 'freev' ? 'FreevBrain v5' : 'IA personnalisée'),
                question: question || '',
                response: response || ''
            };
            const list = readChatHistory();
            list.push(entry);
            while (list.length > CHAT_HISTORY_MAX) list.shift();
            writeChatHistory(list);

            // Sauvegarde aussi côté cloud si l'utilisateur est connecté (best-effort, non bloquant)
            if (window.FreevAuthActions?.getCurrentUser?.() && window.FreevAuthActions?.saveChatHistoryEntry) {
                window.FreevAuthActions.saveChatHistoryEntry(entry).catch(() => {});
            }

            if (!document.getElementById('history-modal')?.classList.contains('hidden')) {
                renderHistoryList();
            }
        }

        // Fusionne l'historique cloud (autre appareil) avec l'historique local, sans doublons
        window.syncChatHistoryFromCloud = async function () {
            if (!window.FreevAuthActions?.loadChatHistory) return;
            try {
                const cloudList = await window.FreevAuthActions.loadChatHistory();
                if (!Array.isArray(cloudList) || !cloudList.length) return;
                const local = readChatHistory();
                const knownIds = new Set(local.map(e => e.id));
                let changed = false;
                cloudList.forEach(entry => {
                    if (entry?.id && !knownIds.has(entry.id)) {
                        local.push(entry);
                        knownIds.add(entry.id);
                        changed = true;
                    }
                });
                if (changed) {
                    local.sort((a, b) => new Date(a.date) - new Date(b.date));
                    while (local.length > CHAT_HISTORY_MAX) local.shift();
                    writeChatHistory(local);
                    if (!document.getElementById('history-modal')?.classList.contains('hidden')) {
                        renderHistoryList();
                    }
                }
            } catch (e) { console.warn('Synchro historique échouée', e); }
        };

        function formatHistoryDate(iso) {
            try {
                return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
            } catch (e) { return iso; }
        }

        function renderHistoryList() {
            const container = document.getElementById('history-list');
            const countEl = document.getElementById('history-count');
            const syncStatus = document.getElementById('history-sync-status');
            if (!container) return;

            const list = readChatHistory().slice().reverse();
            countEl.textContent = list.length + (list.length > 1 ? ' échanges enregistrés' : ' échange enregistré');

            const isLoggedIn = !!window.FreevAuthActions?.getCurrentUser?.();
            syncStatus.textContent = isLoggedIn
                ? 'Enregistré sur cet appareil et synchronisé avec votre compte Freev.'
                : "Enregistré sur cet appareil. Connectez-vous pour synchroniser dans le cloud.";

            if (!list.length) {
                container.innerHTML = '<p class="text-sm text-gray-500 italic py-6 text-center">Aucune conversation enregistrée pour le moment.</p>';
                return;
            }

            container.innerHTML = list.map(entry => {
                const badgeClass = entry.mode === 'freev'
                    ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                    : 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/20';
                return `
                <div class="p-3 bg-slate-900/60 rounded-lg border border-white/10">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeClass}">${escapeHtml(entry.model)}</span>
                        <div class="flex items-center gap-3">
                            <span class="text-[10px] text-gray-500">${formatHistoryDate(entry.date)}</span>
                            <button class="text-gray-500 hover:text-red-400 text-xs" onclick="deleteHistoryEntry('${entry.id}')" title="Supprimer">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <p class="text-sm text-white mb-1"><span class="text-brand-secondary font-bold">Vous : </span>${escapeHtml(entry.question)}</p>
                    <p class="text-sm text-gray-300"><span class="text-brand-accent font-bold">IA : </span>${escapeHtml(entry.response)}</p>
                </div>`;
            }).join('');
        }

        function deleteHistoryEntry(id) {
            const list = readChatHistory().filter(e => e.id !== id);
            writeChatHistory(list);
            renderHistoryList();
        }

        function clearChatHistory() {
            if (!confirm("Vider tout l'historique des conversations sur cet appareil ?")) return;
            writeChatHistory([]);
            renderHistoryList();
        }

        function exportChatHistory() {
            const list = readChatHistory();
            if (!list.length) {
                alert("Aucune conversation à exporter pour le moment.");
                return;
            }
            const payload = {
                exportedAt: new Date().toISOString(),
                app: 'Freev',
                count: list.length,
                history: list
            };
            const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
            a.href = url;
            a.download = `freev_historique_${stamp}.json`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        }

        function openHistoryPanel() {
            const modal = document.getElementById('history-modal');
            if (!modal) return;
            renderHistoryList();
            modal.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
        }

        function closeHistoryPanel() {
            const modal = document.getElementById('history-modal');
            if (!modal) return;
            modal.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }

        document.getElementById('close-history-modal')?.addEventListener('click', closeHistoryPanel);
        document.getElementById('history-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'history-modal') closeHistoryPanel();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !document.getElementById('history-modal')?.classList.contains('hidden')) {
                closeHistoryPanel();
            }
        });

        // Image Handling
        function handleImageUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                currentImageBase64 = e.target.result.split(',')[1]; // Remove header
                const preview = document.getElementById('image-preview');
                preview.src = e.target.result;
                document.getElementById('image-preview-container').classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }

        function removeImage() {
            currentImageBase64 = null;
            document.getElementById('image-preview-container').classList.add('hidden');
            document.getElementById('image-upload').value = '';
        }

        // ── Autre IA (n'importe quelle API compatible OpenAI) ─────────────────
        // Fonctionne avec ChatGPT, Gemini, Hermes 4, OpenRouter, NVIDIA NIM, Ollama,
        // Kimi (Moonshot), Qwen (DashScope), Groq, DeepSeek, Mistral, Together AI,
        // ou tout autre fournisseur exposant un endpoint /chat/completions au format OpenAI.

        const CUSTOM_PRESETS = {
            custom:     { url: '',                                                 model: '' },
            openai:     { url: 'https://api.openai.com/v1',                        model: 'gpt-4o-mini' },
            gemini:     { url: 'https://generativelanguage.googleapis.com/v1beta/openai', model: 'gemini-2.0-flash' },
            hermes:     { url: 'https://openrouter.ai/api/v1',                     model: 'nousresearch/hermes-4-405b' },
            openrouter: { url: 'https://openrouter.ai/api/v1',                     model: 'qwen/qwen-2.5-72b-instruct' },
            nvidia:     { url: 'https://freev-nvidia-proxy.trystan-bonnin27.workers.dev/v1', model: 'nvidia/llama-3.1-nemotron-70b-instruct' },
            ollama:     { url: 'http://localhost:11434/v1',                        model: 'llama3' },
            lmstudio:   { url: 'http://localhost:1234/v1',                         model: 'local-model' },
            moonshot:   { url: 'https://api.moonshot.ai/v1',                       model: 'kimi-k2-0711-preview' },
            dashscope:  { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
            zhipu:      { url: 'https://open.bigmodel.cn/api/paas/v4',             model: 'glm-4-plus' },
            baichuan:   { url: 'https://api.baichuan-ai.com/v1',                   model: 'Baichuan4' },
            groq:       { url: 'https://api.groq.com/openai/v1',                   model: 'llama-3.3-70b-versatile' },
            deepseek:   { url: 'https://api.deepseek.com/v1',                      model: 'deepseek-chat' },
            mistral:    { url: 'https://api.mistral.ai/v1',                        model: 'mistral-large-latest' },
            together:   { url: 'https://api.together.xyz/v1',                      model: 'meta-llama/Llama-3.3-70B-Instruct-Turbo' },
            fireworks:  { url: 'https://api.fireworks.ai/inference/v1',            model: 'accounts/fireworks/models/llama-v3p3-70b-instruct' },
            cerebras:   { url: 'https://api.cerebras.ai/v1',                       model: 'llama3.3-70b' },
            xai:        { url: 'https://api.x.ai/v1',                             model: 'grok-3' },
            perplexity: { url: 'https://api.perplexity.ai',                       model: 'sonar' },
            cohere:     { url: 'https://api.cohere.ai/compatibility/v1',          model: 'command-r-plus' },
            novita:     { url: 'https://api.novita.ai/v3/openai',                 model: 'meta-llama/llama-3.3-70b-instruct' },
            siliconflow:{ url: 'https://api.siliconflow.com/v1',                  model: 'Qwen/Qwen2.5-72B-Instruct' },
            hyperbolic: { url: 'https://api.hyperbolic.xyz/v1',                   model: 'meta-llama/Llama-3.3-70B-Instruct' },
            anyscale:   { url: 'https://api.endpoints.anyscale.com/v1',           model: 'meta-llama/Llama-3-70b-chat-hf' }
        };

        function applyCustomPreset() {
            const presetKey = document.getElementById('custom-provider-preset').value;
            const preset = CUSTOM_PRESETS[presetKey];
            if (!preset) return;
            if (preset.url)   document.getElementById('custom-base-url').value = preset.url;
            if (preset.model) document.getElementById('custom-model-name').value = preset.model;

            // Affiche la bibliothèque de modèles locaux uniquement pour Ollama / LM Studio
            const localLib = document.getElementById('local-model-library');
            if (presetKey === 'ollama' || presetKey === 'lmstudio') {
                localLib.classList.remove('hidden');
            } else {
                localLib.classList.add('hidden');
            }
        }

        function applyLocalModel() {
            const modelName = document.getElementById('local-model-picker').value;
            if (!modelName) return;
            document.getElementById('custom-model-name').value = modelName;
            const hint = document.getElementById('local-model-cmd-hint');
            if (hint) hint.textContent = modelName;
        }

        // ── Bibliothèque de modèles IA : données ────────────────────────────────
        // Catalogue de référence Freev. Chaque modèle « officiel » peut être installé
        // avec Ollama ou LM Studio ; les variantes ci-dessous représentent les formats
        // de téléchargement (quantisations GGUF, formats GPU, Apple Silicon...) les plus
        // couramment publiés. Tailles et RAM sont des estimations : vérifie toujours la
        // fiche du dépôt avant de télécharger. Le moteur d'affichage est plus bas dans la page.
        const MODEL_CATALOG = [
          // Qwen
          ['Qwen3.5 0.8B','qwen3.5:0.8b','Qwen','general',0.8,2,'Ultra léger','Assistant multimodal compact.',true,true],
          ['Qwen3.5 2B','qwen3.5:2b','Qwen','general',1.7,4,'Léger','Très bon point de départ local.',true,true],
          ['Qwen3.5 4B','qwen3.5:4b','Qwen','vision',3.0,6,'Léger','Texte, image, outils et raisonnement.',true,true],
          ['Qwen3.5 9B','qwen3.5:9b','Qwen','vision',6.0,10,'Moyen','Multimodal polyvalent.',true,true],
          ['Qwen3.5 27B','qwen3.5:27b','Qwen','vision',17,24,'Puissant','Pour gros PC avec GPU.',true,true],
          ['Qwen3 1.7B','qwen3:1.7b','Qwen','reasoning',1.4,4,'Léger','Raisonnement très compact.',true,false],
          ['Qwen3 4B','qwen3:4b','Qwen','reasoning',2.5,6,'Léger','Bon modèle de réflexion local.',true,false],
          ['Qwen3 8B','qwen3:8b','Qwen','reasoning',5.2,8,'Moyen','Excellent généraliste moderne.',true,true],
          ['Qwen3 14B','qwen3:14b','Qwen','reasoning',9.0,16,'Costaud','Raisonnement plus solide.',true,false],
          ['Qwen3 30B-A3B','qwen3:30b','Qwen','reasoning',19,24,'Puissant','MoE, puissant sans être géant.',true,true],
          ['Qwen3 32B','qwen3:32b','Qwen','reasoning',20,28,'Puissant','Dense, fort en tâches complexes.',false,false],
          ['Qwen3 235B-A22B','qwen3:235b','Qwen','reasoning',140,192,'Très gros','Station ou cloud requis.',false,true],
          ['Qwen3 Coder','qwen3-coder','Qwen','code',18,24,'Puissant','Développement et agents.',true,true],
          ['Qwen3 Coder Next','qwen3-coder-next','Qwen','code',20,32,'Puissant','Coding agentique local.',true,true],
          ['Qwen3 VL','qwen3-vl','Qwen','vision',8,12,'Moyen','Analyse visuelle et documents.',true,true],
          ['Qwen3 Embedding','qwen3-embedding','Qwen','embedding',0.6,2,'Ultra léger','Recherche vectorielle pour RAG.',false,true],
          // Google / Gemma
          ['Gemma 3 1B','gemma3:1b','Gemma','general',0.8,2,'Ultra léger','Google, très léger.',true,false],
          ['Gemma 3 4B','gemma3:4b','Gemma','vision',3.3,6,'Léger','Multimodal et compact.',true,false],
          ['Gemma 3 12B','gemma3:12b','Gemma','vision',8,16,'Costaud','Bon niveau pour texte et images.',true,false],
          ['Gemma 3 27B','gemma3:27b','Gemma','vision',17,24,'Puissant','Version haute qualité.',true,false],
          ['Gemma 4 E2B','gemma4:e2b','Gemma','reasoning',7.2,10,'Moyen','Raisonnement local moderne.',true,true],
          ['Gemma 4 12B','gemma4:12b','Gemma','vision',8,16,'Costaud','Multimodal avec thinking.',true,true],
          ['Gemma 4 27B','gemma4:27b','Gemma','vision',17,24,'Puissant','Modèle avancé de Google.',true,true],
          ['TranslateGemma 4B','translategemma:4b','Gemma','translate',3,6,'Léger','Traduction multilingue.',false,true],
          ['TranslateGemma 12B','translategemma:12b','Gemma','translate',8,16,'Costaud','Traduction de meilleure qualité.',false,true],
          // Meta / Llama
          ['Llama 3.2 1B','llama3.2:1b','Llama','general',1.3,4,'Ultra léger','Rapide pour petits PC.',true,false],
          ['Llama 3.2 3B','llama3.2:3b','Llama','general',2,6,'Léger','Conversation légère.',true,false],
          ['Llama 3.1 8B','llama3.1:8b','Llama','general',4.7,8,'Moyen','Valeur sûre locale.',true,false],
          ['Llama 3.3 70B','llama3.3:70b','Llama','general',40,48,'Très gros','Généraliste 70B.',true,false],
          ['Llama 4 Scout','llama4:scout','Llama','vision',60,96,'Très gros','MoE multimodal.',true,true],
          ['Llama 4 Maverick','llama4:maverick','Llama','vision',200,256,'Très gros','Très grande configuration.',false,true],
          // Microsoft / OpenAI / DeepSeek
          ['Phi-4 Mini','phi4-mini','Phi','reasoning',2.5,6,'Léger','Microsoft, raisonnement compact.',true,false],
          ['Phi-4','phi4','Phi','reasoning',8.5,16,'Costaud','Maths et raisonnement.',true,false],
          ['GPT-OSS 20B','gpt-oss:20b','OpenAI','reasoning',13,20,'Puissant','Raisonnement et tâches agentiques.',true,true],
          ['GPT-OSS 120B','gpt-oss:120b','OpenAI','reasoning',70,96,'Très gros','Nécessite une grosse machine.',true,true],
          ['DeepSeek R1 1.5B','deepseek-r1:1.5b','DeepSeek','reasoning',1.1,4,'Ultra léger','Initiation au raisonnement.',true,false],
          ['DeepSeek R1 7B','deepseek-r1:7b','DeepSeek','reasoning',4.7,8,'Moyen','Raisonnement accessible.',true,false],
          ['DeepSeek R1 14B','deepseek-r1:14b','DeepSeek','reasoning',9,16,'Costaud','Pour tâches plus complexes.',true,false],
          ['DeepSeek R1 32B','deepseek-r1:32b','DeepSeek','reasoning',20,28,'Puissant','Très fort, très gourmand.',true,false],
          ['DeepSeek R1 70B','deepseek-r1:70b','DeepSeek','reasoning',40,48,'Très gros','Gros poste requis.',false,false],
          ['DeepSeek Coder V2','deepseek-coder-v2','DeepSeek','code',9,16,'Costaud','Spécialisé développement.',true,false],
          // Mistral / Europe
          ['Mistral 7B','mistral:7b','Mistral','general',4.1,8,'Moyen','Classique rapide et fiable.',true,false],
          ['Mistral Nemo 12B','mistral-nemo:12b','Mistral','general',7.1,16,'Costaud','Généraliste moderne.',true,false],
          ['Mistral Small 3.1','mistral-small3.1','Mistral','vision',14,24,'Puissant','Texte, image et code.',true,true],
          ['Mixtral 8x7B','mixtral:8x7b','Mistral','general',26,32,'Puissant','MoE reconnu.',true,false],
          ['Mixtral 8x22B','mixtral:8x22b','Mistral','general',80,128,'Très gros','Grosse station nécessaire.',false,false],
          ['Codestral','codestral','Mistral','code',13,20,'Puissant','Code et complétion.',true,false],
          // Autres familles utiles
          ['GLM-4.7 Flash','glm-4.7-flash','Zhipu','general',5,8,'Moyen','Généraliste rapide.',true,true],
          ['GLM-5.1','glm-5.1','Zhipu','code',40,64,'Très gros','Agentic engineering.',true,true],
          ['Command R7B','command-r7b','Cohere','general',5,8,'Moyen','RAG et outils.',false,false],
          ['Aya Expanse 8B','aya-expanse:8b','Cohere','translate',5,8,'Moyen','Multilingue et traduction.',true,false],
          ['OLMo 2 7B','olmo2:7b','AI2','general',4.7,8,'Moyen','Open source complet.',false,false],
          ['OLMo 2 13B','olmo2:13b','AI2','general',8,16,'Costaud','Open science.',false,false],
          ['SmolLM2 135M','smollm2:135m','Hugging Face','general',0.2,1,'Ultra léger','Tests et appareils modestes.',false,false],
          ['SmolLM2 1.7B','smollm2:1.7b','Hugging Face','general',1.1,3,'Ultra léger','Petit assistant local.',true,false],
          ['LFM2 1.2B','lfm2:1.2b','Liquid AI','general',0.9,3,'Ultra léger','Pensé pour l’embarqué.',true,true],
          ['LFM2 24B-A2B','lfm2:24b','Liquid AI','general',15,24,'Puissant','Hybride efficace.',true,true],
          ['Falcon3 10B','falcon3:10b','TII','general',6,12,'Moyen','Généraliste open weight.',false,false],
          ['WizardLM2 7B','wizardlm2:7b','Microsoft','general',4.1,8,'Moyen','Instructions et conversation.',false,false],
          ['Hermes 3 8B','hermes3:8b','Nous Research','general',4.7,8,'Moyen','Discussion et consignes.',true,false],
          ['Dolphin 3 8B','dolphin3:8b','Cognitive Computations','general',4.7,8,'Moyen','Assistant communautaire.',false,false],
          ['Nomic Embed Text','nomic-embed-text','Nomic','embedding',0.3,2,'Ultra léger','Embeddings pour mémoire/RAG.',true,false],
          ['BGE-M3','bge-m3','BAAI','embedding',1.5,4,'Léger','Embeddings multilingues.',false,false],
          ['Whisper Small','whisper:small','OpenAI','audio',1,3,'Ultra léger','Transcription locale.',true,false],
          ['Whisper Large V3','whisper:large-v3','OpenAI','audio',3,8,'Moyen','Transcription haute qualité.',true,false],
          ['LLaVA 7B','llava:7b','LLaVA','vision',4.7,8,'Moyen','Vision-language classique.',true,false],
          ['Moondream 2','moondream','Moondream','vision',1.1,3,'Ultra léger','Vision très légère.',true,false],
          ['MiniCPM-V','minicpm-v','OpenBMB','vision',5,8,'Moyen','Analyse d’images et OCR.',true,false]
        ].map(([name,model,family,type,sizeGB,ramGB,tag,desc,popular,recent])=>({name,model,family,type,sizeGB,ramGB,tag,desc,popular,recent,variant:'Version officielle / référence',format:'official',isVariant:false}));

        // Formats de téléchargement les plus utiles (fusion des anciennes listes GGUF / GPU / Apple
        // en une seule sélection curatée, pour éviter des milliers de quasi-doublons peu lisibles).
        const QUANT_PROFILES = [
          ['Q2_K','GGUF',0.52,0.58,'Très compact','Qualité réduite, à réserver aux machines limitées.'],
          ['Q3_K_M','GGUF',0.72,0.76,'Compact','Bon compromis compact.'],
          ['Q4_0','GGUF',0.82,0.86,'Standard','Quantisation classique légère.'],
          ['Q4_K_S','GGUF',0.90,0.96,'Standard+','GGUF, compromis taille / qualité.'],
          ['Q4_K_M','GGUF',0.94,1.00,'Recommandé','Meilleur compromis qualité / mémoire.'],
          ['Q5_K_M','GGUF',1.08,1.14,'Qualité+','Plus précis, demande davantage de mémoire.'],
          ['Q6_K','GGUF',1.24,1.30,'Haute qualité','Très bon rendu local.'],
          ['Q8_0','GGUF',1.56,1.62,'Très haute qualité','Gros fichier, qualité maximale quantifiée.'],
          ['IQ4_XS','GGUF',0.78,0.84,'i-quant','Quantisation intelligente très compacte, bon ratio mémoire.'],
          ['AWQ 4-bit','AWQ',0.90,0.98,'GPU optimisé','Format GPU : vérifier la disponibilité du dépôt.'],
          ['GPTQ 4-bit','GPTQ',0.92,1.00,'GPU optimisé','Format GPU : vérifier la disponibilité du dépôt.'],
          ['EXL2 4.0 bpw','EXL2',0.82,0.92,'GPU recommandé','Format ExLlamaV2 équilibré, GPU NVIDIA recommandé.'],
          ['MLX 4-bit','MLX',0.87,0.96,'Apple Silicon','Format MLX pour Mac Apple Silicon.'],
          ['BF16','BF16',2.00,2.05,'Précision maximale','Poids original, pour très grosse machine.']
        ];
        const BASE_MODELS = MODEL_CATALOG.slice();
        const LOCAL_VARIANT_CATALOG = BASE_MODELS.flatMap((base, baseIndex) => QUANT_PROFILES.map(([quant, format, diskFactor, ramFactor, quality, note], quantIndex) => ({
          name: `${base.name} · ${quant}`, model: base.model, family: base.family, type: base.type,
          sizeGB: Math.max(0.1, +(base.sizeGB * diskFactor).toFixed(1)), ramGB: Math.max(1, Math.ceil(base.ramGB * ramFactor)),
          tag: `${quality} · ${quant}`, desc: `${base.desc} Variante locale ${format} ${quant}. ${note}`,
          popular: base.popular && ['Q4_K_M','Q5_K_M','Q6_K','Q8_0','MLX 4-bit'].includes(quant), recent: base.recent,
          variant: `${format} · ${quant} · ${quality}`, format, isVariant: true, baseModelName: base.name,
          sourceIndex: baseIndex, quantIndex
        })));
        MODEL_CATALOG.push(...LOCAL_VARIANT_CATALOG);

        const modelTypeLabels = { general:'Généraliste', reasoning:'Raisonnement', code:'Code', vision:'Vision', embedding:'Embeddings', translate:'Traduction', audio:'Audio' };

        // Exposés pour le moteur d'affichage de la bibliothèque (plus bas dans la page).
        window.FreevModelCatalog = MODEL_CATALOG;
        window.FreevModelTypeLabels = modelTypeLabels;

        // ── Gestion de la liste des modèles sauvegardés (switch rapide) ────────
        const SAVED_MODELS_KEY = 'freev_saved_ai_configs';

        function getSavedModelsList() {
            try {
                const raw = localStorage.getItem(SAVED_MODELS_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch { return []; }
        }

        function setSavedModelsList(list) {
            localStorage.setItem(SAVED_MODELS_KEY, JSON.stringify(list));
        }

        async function syncSavedModelsListToCloud(list) {
            if (window.FreevAuthActions?.getCurrentUser?.()) {
                try { await window.FreevAuthActions.saveAiConfigsList(list); } catch (e) { console.warn('Sync liste modèles échouée', e); }
            }
        }

        function upsertSavedModel(config) {
            const list = getSavedModelsList();
            const key = (c) => (c.baseUrl || '') + '::' + (c.model || '');
            const idx = list.findIndex(c => key(c) === key(config));
            if (idx >= 0) list[idx] = config; else list.push(config);
            setSavedModelsList(list);
            syncSavedModelsListToCloud(list);
            return list;
        }

        // Migration : si la liste est vide mais qu'une ancienne config "active" existe déjà
        // (localStorage ou Firestore d'avant l'ajout du switcher), on l'ajoute à la liste.
        function ensureSavedModelsSeeded() {
            const list = getSavedModelsList();
            if (list.length > 0) return list;
            try {
                const raw = localStorage.getItem('freev_custom_ai_config');
                if (raw) {
                    const config = JSON.parse(raw);
                    if (config && config.baseUrl && config.model) {
                        return upsertSavedModel(config);
                    }
                }
            } catch {}
            return list;
        }

        function deleteSavedModel(index, event) {
            event?.stopPropagation();
            const list = getSavedModelsList();
            list.splice(index, 1);
            setSavedModelsList(list);
            syncSavedModelsListToCloud(list);
            renderModelSwitcherList();
        }

        function activateSavedModel(index) {
            const list = getSavedModelsList();
            const config = list[index];
            if (!config) return;
            localStorage.setItem('freev_custom_ai_config', JSON.stringify(config));
            if (typeof setAiMode === 'function') setAiMode('custom');
            loadCustomConfig();
            const badge = document.getElementById('ai-mode-badge');
            const header = document.getElementById('chat-header-label');
            if (badge && header) {
                badge.innerHTML  = '<i class="fa-solid fa-plug"></i> Autre IA — ' + escapeHtml(config.model);
                header.innerHTML = '<i class="fa-solid fa-plug text-fuchsia-400"></i> ' + escapeHtml(config.model);
            }
            document.getElementById('model-switcher-dropdown')?.classList.add('hidden');
        }

        function renderModelSwitcherList() {
            ensureSavedModelsSeeded();
            const list = getSavedModelsList();
            const container = document.getElementById('model-switcher-list');
            if (!container) return;
            let activeKey = null;
            try {
                const active = JSON.parse(localStorage.getItem('freev_custom_ai_config') || 'null');
                if (active) activeKey = (active.baseUrl || '') + '::' + (active.model || '');
            } catch {}

            if (!list.length) {
                container.innerHTML = '<p class="text-xs text-gray-500 p-3">Aucun modèle enregistré pour le moment. Configure une clé API pour en ajouter un.</p>';
                return;
            }
            container.innerHTML = list.map((c, i) => {
                const key = (c.baseUrl || '') + '::' + (c.model || '');
                const isActive = key === activeKey;
                return `
                <div class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/5 cursor-pointer ${isActive ? 'bg-fuchsia-500/10 border border-fuchsia-500/30' : ''}" onclick="activateSavedModel(${i})">
                    <i class="fa-solid ${isActive ? 'fa-circle-check text-fuchsia-400' : 'fa-plug text-gray-500'} text-xs"></i>
                    <div class="flex-grow min-w-0">
                        <div class="text-sm text-white truncate">${escapeHtml(c.model)}</div>
                        <div class="text-xs text-gray-500 truncate">${escapeHtml(c.baseUrl)}</div>
                    </div>
                    <button class="text-gray-600 hover:text-red-400 px-1" onclick="deleteSavedModel(${i}, event)" title="Supprimer">
                        <i class="fa-solid fa-trash text-xs"></i>
                    </button>
                </div>`;
            }).join('');
        }

        function toggleModelSwitcher() {
            const dropdown = document.getElementById('model-switcher-dropdown');
            if (!dropdown) return;
            const willShow = dropdown.classList.contains('hidden');
            if (willShow) renderModelSwitcherList();
            dropdown.classList.toggle('hidden', !willShow);
        }

        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('model-switcher-dropdown');
            const btn = document.getElementById('switch-model-btn');
            if (!dropdown || dropdown.classList.contains('hidden')) return;
            if (!dropdown.contains(e.target) && !btn?.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });

        async function saveCustomConfig() {
            const config = {
                preset:  document.getElementById('custom-provider-preset').value,
                baseUrl: document.getElementById('custom-base-url').value.trim().replace(/\/$/, ''),
                model:   document.getElementById('custom-model-name').value.trim(),
                apiKey:  document.getElementById('custom-api-key').value.trim()
            };
            if (!config.baseUrl || !config.model) {
                alert("Merci de renseigner au minimum l'URL de base et le nom du modèle.");
                return;
            }
            localStorage.setItem('freev_custom_ai_config', JSON.stringify(config));
            upsertSavedModel(config);

            let cloudSynced = false;
            if (window.FreevAuthActions?.getCurrentUser?.()) {
                try {
                    await window.FreevAuthActions.saveAiConfig(config);
                    cloudSynced = true;
                } catch (e) {
                    console.warn('Sync cloud config échouée', e);
                }
            }

            alert(cloudSynced
                ? "Configuration enregistrée et synchronisée avec votre profil Freev."
                : "Configuration enregistrée sur cet appareil. Connectez-vous à votre profil Freev pour la synchroniser sur tous vos appareils.");

            document.getElementById('api-settings-custom').classList.add('hidden');
            const badge = document.getElementById('ai-mode-badge');
            const header = document.getElementById('chat-header-label');
            if (currentAiMode === 'custom') {
                badge.innerHTML  = '<i class="fa-solid fa-plug"></i> Autre IA — ' + escapeHtml(config.model);
                header.innerHTML = '<i class="fa-solid fa-plug text-fuchsia-400"></i> ' + escapeHtml(config.model);
            }
        }

        function loadCustomConfig() {
            const raw = localStorage.getItem('freev_custom_ai_config');
            if (!raw) return;
            try {
                const config = JSON.parse(raw);
                document.getElementById('custom-provider-preset').value = config.preset || 'custom';
                document.getElementById('custom-base-url').value = config.baseUrl || '';
                document.getElementById('custom-model-name').value = config.model || '';
                document.getElementById('custom-api-key').value = config.apiKey || '';
                const localLib = document.getElementById('local-model-library');
                if (config.preset === 'ollama' || config.preset === 'lmstudio') {
                    localLib.classList.remove('hidden');
                } else {
                    localLib.classList.add('hidden');
                }
            } catch { /* config corrompue, on ignore */ }
        }

        // Appelée automatiquement dès que Firebase détecte une connexion (login, ou session déjà active au chargement).
        // Récupère la config IA sauvegardée sur le profil et la fait passer avant celle en localStorage.
        window.syncAiConfigFromCloud = async function () {
            if (!window.FreevAuthActions?.loadAiConfig) return;
            try {
                const cloudConfig = await window.FreevAuthActions.loadAiConfig();
                if (cloudConfig && cloudConfig.baseUrl && cloudConfig.model) {
                    localStorage.setItem('freev_custom_ai_config', JSON.stringify(cloudConfig));
                    loadCustomConfig();
                    const badge = document.getElementById('ai-mode-badge');
                    const header = document.getElementById('chat-header-label');
                    if (typeof currentAiMode !== 'undefined' && currentAiMode === 'custom' && badge && header) {
                        badge.innerHTML  = '<i class="fa-solid fa-plug"></i> Autre IA — ' + escapeHtml(cloudConfig.model);
                        header.innerHTML = '<i class="fa-solid fa-plug text-fuchsia-400"></i> ' + escapeHtml(cloudConfig.model);
                    }
                }
                const cloudList = await window.FreevAuthActions.loadAiConfigsList?.();
                if (Array.isArray(cloudList) && cloudList.length > 0) {
                    setSavedModelsList(cloudList);
                } else {
                    // Pas encore de liste sur ce profil : on migre l'ancienne config unique si elle existe.
                    ensureSavedModelsSeeded();
                }
                renderModelSwitcherList();
            } catch (e) {
                console.warn('Chargement config IA depuis le profil échoué', e);
            }
        };

        async function generateCustom() {
            const input  = document.getElementById('ai-input');
            const output = document.getElementById('ai-output');
            const prompt = input.value.trim();
            const raw    = localStorage.getItem('freev_custom_ai_config');

            if ((!prompt && !currentImageBase64) || freevIsGenerating) return;
            if (!raw) {
                output.innerHTML += `<div class="mt-4 text-red-400 p-2 bg-red-900/20 rounded border border-red-500/30"><i class="fa-solid fa-triangle-exclamation"></i> Erreur: Aucun fournisseur configuré. Cliquez sur "Configurer Clé API" ci-dessus et renseignez l'URL + le modèle.</div>`;
                output.scrollTop = output.scrollHeight;
                return;
            }
            let config;
            try {
                config = JSON.parse(raw);
            } catch (e) {
                output.innerHTML += `<div class="mt-4 text-red-400 p-2 bg-red-900/20 rounded border border-red-500/30"><i class="fa-solid fa-triangle-exclamation"></i> Erreur: configuration IA corrompue. Reconfigurez votre fournisseur via "Configurer Clé API".</div>`;
                output.scrollTop = output.scrollHeight;
                return;
            }
            if (!config.baseUrl || !config.model) {
                output.innerHTML += `<div class="mt-4 text-red-400 p-2 bg-red-900/20 rounded border border-red-500/30"><i class="fa-solid fa-triangle-exclamation"></i> Erreur: URL de base ou modèle manquant dans la configuration.</div>`;
                output.scrollTop = output.scrollHeight;
                return;
            }

            // Message utilisateur
            let userHtml = `<div class="mt-4 text-white p-3 bg-white/5 rounded-lg border border-white/5"><span class="text-brand-secondary font-bold">Vous:</span> ${escapeHtml(prompt)}`;
            if (currentImageBase64) userHtml += `<br><span class="text-xs text-gray-400 italic">[Image jointe]</span>`;
            userHtml += `</div>`;
            output.innerHTML += userHtml;
            input.value = '';
            output.scrollTop = output.scrollHeight;

            const loadingId = 'loading-' + Date.now();
            output.innerHTML += `<div id="${loadingId}" class="mt-2 text-gray-500 italic flex items-center gap-2"><i class="fa-solid fa-circle-notch fa-spin text-fuchsia-400"></i> ${escapeHtml(config.model)} réfléchit... <button class="ml-1 text-xs underline text-gray-400 hover:text-white" onclick="stopGeneration()">annuler</button></div>`;
            output.scrollTop = output.scrollHeight;

            // Contenu utilisateur au format OpenAI (texte + image en vision si fournie)
            let userContent;
            if (currentImageBase64) {
                userContent = [{ type: 'text', text: prompt || 'Décris cette image.' }];
                userContent.push({ type: 'image_url', image_url: { url: `data:image/jpeg;base64,${currentImageBase64}` } });
            } else {
                userContent = prompt;
            }

            const payload = {
                model: config.model,
                messages: [{ role: 'user', content: userContent }],
                stream: true
            };

            const headers = { 'Content-Type': 'application/json' };
            if (config.apiKey) headers['Authorization'] = 'Bearer ' + config.apiKey;

            const controller = new AbortController();
            freevActiveController = controller;
            setGeneratingState(true);
            let timedOut = false;
            let stalled = false;
            // Timeout global : la requête entière ne doit pas dépasser 60s
            const hardTimeoutId = setTimeout(() => { timedOut = true; controller.abort('timeout'); }, 60000);
            // Watchdog anti-blocage : si aucun octet ne circule pendant 25s pendant le stream, on coupe
            let watchdogId = null;
            const resetWatchdog = () => {
                clearTimeout(watchdogId);
                watchdogId = setTimeout(() => { stalled = true; controller.abort('stalled'); }, 25000);
            };

            let aiResponseText = '';
            let interrupted = false;

            try {
                resetWatchdog();
                const response = await fetch(`${config.baseUrl}/chat/completions`, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(payload),
                    signal: controller.signal
                });
                clearTimeout(watchdogId);

                if (!response.ok) {
                    let msg = 'Erreur API ' + response.status;
                    try { const err = await response.json(); msg = err.error?.message || err.message || msg; } catch {}
                    throw Object.assign(new Error(msg), { httpStatus: response.status });
                }

                document.getElementById(loadingId)?.remove();
                removeImage();

                const responseDiv = document.createElement('div');
                responseDiv.className = "mt-4 text-gray-200 border-l-2 border-fuchsia-400 pl-4 py-1";
                responseDiv.innerHTML = `<span class="text-fuchsia-400 font-bold text-sm mb-1 block"><i class="fa-solid fa-plug mr-1"></i>${escapeHtml(config.model)} :</span><span class="ai-stream-content"></span>`;
                output.appendChild(responseDiv);
                const streamTarget = responseDiv.querySelector('.ai-stream-content');
                output.scrollTop = output.scrollHeight;

                // Si le fournisseur ne supporte pas le streaming (réponse JSON classique), on gère aussi ce cas
                const contentType = response.headers.get('content-type') || '';

                if (contentType.includes('application/json') && !contentType.includes('event-stream')) {
                    const data = await response.json();
                    aiResponseText = data.choices?.[0]?.message?.content || '(réponse vide)';
                    streamTarget.innerHTML = marked.parse(escapeHtml(aiResponseText));
                } else if (!response.body) {
                    // Pas de flux disponible (navigateur/proxy non compatible) : on tente quand même le JSON
                    const data = await response.json().catch(() => null);
                    aiResponseText = data?.choices?.[0]?.message?.content || '(réponse vide — le streaming n\'est pas supporté ici)';
                    streamTarget.innerHTML = marked.parse(escapeHtml(aiResponseText));
                } else {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    try {
                        while (true) {
                            resetWatchdog();
                            const { done, value } = await reader.read();
                            if (done) break;
                            buffer += decoder.decode(value, { stream: true });
                            const lines = buffer.split('\n');
                            buffer = lines.pop(); // garde la ligne incomplète pour le prochain chunk

                            for (const line of lines) {
                                const trimmed = line.trim();
                                if (!trimmed.startsWith('data:')) continue;
                                const dataStr = trimmed.slice(5).trim();
                                if (dataStr === '[DONE]') continue;
                                try {
                                    const json = JSON.parse(dataStr);
                                    const delta = json.choices?.[0]?.delta?.content || json.choices?.[0]?.message?.content || '';
                                    if (delta) {
                                        aiResponseText += delta;
                                        streamTarget.innerHTML = marked.parse(escapeHtml(aiResponseText));
                                        output.scrollTop = output.scrollHeight;
                                    }
                                } catch (e) { /* chunk partiel ou non-JSON, on ignore */ }
                            }
                        }
                    } catch (streamErr) {
                        clearTimeout(watchdogId);
                        interrupted = true;
                        const reason = stalled ? "Le flux s'est figé (aucune donnée reçue depuis 25s)." : (timedOut ? "Délai dépassé." : "Connexion interrompue.");
                        streamTarget.innerHTML += `<div class="mt-2 text-xs text-yellow-400"><i class="fa-solid fa-triangle-exclamation mr-1"></i>${escapeHtml(reason)} ${aiResponseText ? 'Réponse partielle conservée ci-dessus.' : ''}</div>`;
                    }
                    clearTimeout(watchdogId);
                    if (!aiResponseText) streamTarget.innerHTML = '(réponse vide)';
                }

                output.scrollTop = output.scrollHeight;

                saveChatHistoryEntry({
                    mode: 'custom',
                    model: config.model,
                    question: prompt,
                    response: (aiResponseText || '') + (interrupted ? ' (réponse interrompue)' : '')
                });

            } catch (error) {
                document.getElementById(loadingId)?.remove();
                const wasUserStop = error?.name === 'AbortError' && !timedOut && !stalled;
                const msg = describeRequestError(error, { timedOut, httpStatus: error?.httpStatus });

                if (aiResponseText) {
                    // On avait déjà du texte streamé quand ça a coupé : on ne le perd pas
                    saveChatHistoryEntry({ mode: 'custom', model: config.model, question: prompt, response: aiResponseText + ' (réponse interrompue)' });
                }

                if (!wasUserStop) {
                    output.innerHTML += `<div class="mt-2 text-red-400 p-2 bg-red-900/20 rounded text-sm flex items-center justify-between gap-2">
                        <span>Erreur (${escapeHtml(config.model)}): ${escapeHtml(msg)}</span>
                        <button class="text-xs underline text-red-300 hover:text-white shrink-0" onclick="retryCustomPrompt(this)" data-prompt="${escapeHtml(prompt)}">réessayer</button>
                    </div>`;
                    input.value = prompt; // on ne perd pas la question tapée
                } else {
                    output.innerHTML += `<div class="mt-2 text-gray-400 p-2 bg-slate-800/40 rounded text-sm"><i class="fa-solid fa-circle-stop mr-1"></i>Génération arrêtée.</div>`;
                }
                output.scrollTop = output.scrollHeight;
            } finally {
                clearTimeout(hardTimeoutId);
                clearTimeout(watchdogId);
                freevActiveController = null;
                setGeneratingState(false);
            }
        }

        function retryCustomPrompt(btn) {
            const prompt = btn?.dataset?.prompt;
            if (!prompt) return;
            const input = document.getElementById('ai-input');
            input.value = prompt;
            sendMessage();
        }

        // Enter key → sendMessage()
        document.getElementById('ai-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

