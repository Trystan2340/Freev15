  (() => {
    window.FreevAuthModuleError = "";

    window.addEventListener('error', (event) => {
      const message = event.message || "";
      const filename = event.filename || "";
      if (message.includes("Firebase") || message.includes("module") || filename.includes("firebase")) {
        window.FreevAuthModuleError = message || `Erreur de chargement : ${filename}`;
      }
    }, true);

    window.addEventListener('unhandledrejection', (event) => {
      const reason = event.reason;
      const message = reason?.message || String(reason || "");
      if (message.includes("Firebase") || message.includes("firebase") || message.includes("module") || message.includes("import")) {
        window.FreevAuthModuleError = message;
      }
    });

    const setFallbackStatus = (message, type = "info") => {
      const status = document.getElementById('auth-status');
      if (!status) return;
      status.textContent = message;
      status.className = `min-h-5 text-xs leading-relaxed ${type === "error" ? "text-red-400" : "text-gray-400"}`;
    };

    const getFirebaseLoadDiagnostic = async () => {
      if (window.FreevAuthReady) return "";

      if (location.protocol === "file:") {
        return "La page est ouverte en fichier local. Ouvrez le site depuis Cloudflare/GitHub Pages ou avec un serveur local, pas en double-cliquant index.html.";
      }

      if (window.FreevAuthModuleError) {
        return window.FreevAuthModuleError;
      }

      try {
        await import("https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js");
      } catch (error) {
        return `Le CDN Firebase est bloqué ou inaccessible : ${error?.message || error}`;
      }

      return "Le module Firebase n'a pas démarré. Vérifiez que la dernière version de index.html est bien déployée, puis purgez le cache Cloudflare.";
    };

    const showFirebaseModuleError = async (event) => {
      if (window.FreevAuthReady) return;

      const target = event.target instanceof Element ? event.target : event.target?.parentElement;
      const isAuthClick = event.type === 'submit' || target?.closest('#login-button, #register-button');
      if (!isAuthClick) return;

      event.preventDefault();
      setFallbackStatus("Chargement Firebase en cours...", "info");

      setTimeout(async () => {
        if (window.FreevAuthReady) {
          setFallbackStatus("Firebase est prêt. Cliquez encore une fois sur Se connecter.", "info");
          return;
        }

        const diagnostic = await getFirebaseLoadDiagnostic();
        setFallbackStatus(`Firebase ne démarre pas : ${diagnostic}`, "error");
      }, 900);
    };

    const bindFallback = () => {
      const form = document.getElementById('auth-form');
      if (form?.dataset.firebaseFallbackBound === "true") return;
      if (form) {
        form.dataset.firebaseFallbackBound = "true";
        form.addEventListener('submit', showFirebaseModuleError);
      }
      document.addEventListener('click', showFirebaseModuleError);
    };

    bindFallback();
  })();
