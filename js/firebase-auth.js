  import { initializeApp, getApp, getApps } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
  import { createUserWithEmailAndPassword, getAuth, sendPasswordResetEmail, signInWithEmailAndPassword, onAuthStateChanged, signOut, updateProfile } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
  import { collection, deleteDoc, doc, getDoc, getDocs, getFirestore, runTransaction, setDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

  const firebaseConfig = {
    apiKey: "AIzaSyBtcQrFenU9T0C2v1qcBUpF2DfVqC_V5sM",
    authDomain: "freev-52df2.firebaseapp.com",
    projectId: "freev-52df2",
    storageBucket: "freev-52df2.appspot.com",
    messagingSenderId: "588481455818",
    appId: "1:588481455818:web:fb61c5d4003d670e71f633",
    measurementId: "G-4YHTHZR9G8",
  };

  const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  const auth = getAuth(app);
  const db = getFirestore(app);

  const authForm = document.getElementById("auth-form");
  const emailInput = document.getElementById("auth-email");
  const passwordInput = document.getElementById("auth-password");
  const loginButton = document.getElementById("login-button");
  const registerButton = document.getElementById("register-button");
  const resetPasswordButton = document.getElementById("reset-password-button");
  const authStatus = document.getElementById("auth-status");
  const firebaseUserData = document.getElementById("firebase-user-data");
  const navLoginButton = document.getElementById("open-login-modal");
  const navLoginMobileButton = document.getElementById("open-login-modal-mobile");
  const profileSection = document.getElementById("profile-section");
  const profileAvatarPreview = document.getElementById("profile-avatar-preview");
  const profileAvatarColor = document.getElementById("profile-avatar-color");
  const profileNickname = document.getElementById("profile-nickname");
  const profileDisplayName = document.getElementById("profile-display-name");
  const profileBio = document.getElementById("profile-bio");
  const profileFavoriteType = document.getElementById("profile-favorite-type");
  const saveProfileButton = document.getElementById("save-profile-button");
  const logoutButton = document.getElementById("logout-button");
  const profileSavesSection = document.getElementById("profile-saves-section");
  const profileSavesList = document.getElementById("profile-saves-list");
  const refreshSavesButton = document.getElementById("refresh-saves-button");
  const profileBannerThemeLabel = document.getElementById("profile-banner-theme-label");
  const profileBannerButtons = Array.from(document.querySelectorAll("[data-profile-banner]"));
  let manualAuthInProgress = false;
  let authActionInProgress = false;
  let selectedBannerTheme = "aurora";
  let lastSyncedUid = null;
  let profileSavesCache = new Map();

  const bannerThemeLabels = {
    aurora: "Aurore",
    circuit: "Circuit",
    cosmos: "Cosmos",
    pulse: "Neon Pulse",
    calm: "Calme",
    prism: "Prisme",
    rain: "Data Rain",
    vortex: "Vortex",
    horizon: "Horizon",
    comet: "Comète",
  };

  const bannerThemeKeys = Object.keys(bannerThemeLabels);

  const firebaseErrorMessages = {
    "auth/email-already-in-use": "Un compte existe déjà avec cet email. Utilisez Connexion.",
    "auth/invalid-email": "Adresse email invalide.",
    "auth/missing-password": "Mot de passe requis.",
    "auth/weak-password": "Le mot de passe doit contenir au moins 6 caractères.",
    "auth/invalid-credential": "Email ou mot de passe incorrect.",
    "auth/user-not-found": "Aucun compte trouvé avec cet email.",
    "auth/wrong-password": "Mot de passe incorrect.",
    "auth/network-request-failed": "Connexion réseau impossible. Vérifiez Internet ou le domaine autorisé Firebase.",
    "auth/operation-not-allowed": "La connexion Email/Mot de passe n'est pas activée dans Firebase Authentication.",
    "auth/too-many-requests": "Trop d'essais. Patientez un peu avant de réessayer.",
    "auth/unauthorized-domain": "Ce domaine n'est pas autorisé dans Firebase Authentication.",
    "auth/user-disabled": "Ce compte a été désactivé dans Firebase.",
    "permission-denied": "Firestore refuse l'accès. Vérifiez les règles de sécurité Firestore.",
    "unavailable": "Firebase est momentanément indisponible. Réessayez dans quelques secondes.",
    "freev/nickname-taken": "Ce surnom est déjà pris. Choisissez-en un autre.",
  };

  const formatFirebaseError = (error) => {
    const code = error?.code || "";
    return firebaseErrorMessages[code] || error?.message || "Erreur Firebase inconnue.";
  };

  const escapeText = (value = "") => {
    const span = document.createElement("span");
    span.textContent = value;
    return span.innerHTML;
  };

  const setAuthStatus = (message, type = "info") => {
    if (!authStatus) return;
    authStatus.textContent = message;
    authStatus.className = `min-h-5 text-xs leading-relaxed ${type === "error" ? "text-red-400" : type === "success" ? "text-emerald-400" : "text-gray-400"}`;
  };

  const setAuthBusy = (isBusy, action = "") => {
    [
      { button: loginButton, action: "login", idle: "Se connecter", busy: "Connexion..." },
      { button: registerButton, action: "register", idle: "S'inscrire", busy: "Inscription..." },
    ].forEach(({ button, action: buttonAction, idle, busy }) => {
      if (!button) return;
      button.disabled = isBusy;
      button.setAttribute("aria-busy", isBusy ? "true" : "false");
      button.textContent = isBusy && action === buttonAction ? busy : idle;
      button.classList.toggle("opacity-60", isBusy);
      button.classList.toggle("cursor-wait", isBusy);
    });
  };

  const normalizeNickname = (value = "") => value.trim().replace(/\s+/g, "_");

  const isValidNickname = (value = "") => /^[\p{L}\p{N}_-]{3,24}$/u.test(value);

  const normalizeAvatarColor = (value = "") => /^#[0-9a-f]{6}$/i.test(value) ? value : "#22d3ee";

  const normalizeBannerTheme = (value = "") => bannerThemeKeys.includes(value) ? value : "aurora";

  const getStoredBannerTheme = () => {
    try {
      return normalizeBannerTheme(localStorage.getItem("freev_profile_banner_theme") || "aurora");
    } catch (error) {
      return "aurora";
    }
  };

  const storeBannerTheme = (theme) => {
    try {
      localStorage.setItem("freev_profile_banner_theme", theme);
    } catch (error) {
      console.warn("Theme local non sauvegardé", error);
    }
  };

  const applyBannerTheme = (theme = "aurora", options = {}) => {
    const { persist = true } = options;
    selectedBannerTheme = normalizeBannerTheme(theme);
    document.body.dataset.freevBanner = selectedBannerTheme;

    if (profileBannerThemeLabel) {
      profileBannerThemeLabel.textContent = bannerThemeLabels[selectedBannerTheme];
    }

    profileBannerButtons.forEach((button) => {
      const isSelected = button.dataset.profileBanner === selectedBannerTheme;
      button.setAttribute("aria-pressed", String(isSelected));
      button.classList.toggle("ring-1", isSelected);
      button.classList.toggle("ring-brand-accent/50", isSelected);
    });

    if (persist) storeBannerTheme(selectedBannerTheme);
  };

  const getInitial = (value = "F") => {
    const clean = String(value || "F").trim();
    return clean ? clean[0].toUpperCase() : "F";
  };

  const updateAvatarPreview = (nickname = profileNickname?.value || "F", color = profileAvatarColor?.value || "#22d3ee") => {
    const safeColor = normalizeAvatarColor(color);
    profileSection?.style.setProperty("--profile-accent", safeColor);
    if (!profileAvatarPreview) return;
    profileAvatarPreview.textContent = getInitial(nickname);
    profileAvatarPreview.style.background = safeColor;
  };

  const claimNickname = async (user, nickname, previousNicknameLower = "") => {
    const nicknameLower = nickname.toLowerCase();
    const usernameRef = doc(db, "usernames", nicknameLower);
    const oldUsernameRef = previousNicknameLower && previousNicknameLower !== nicknameLower
      ? doc(db, "usernames", previousNicknameLower)
      : null;

    await runTransaction(db, async (transaction) => {
      const usernameSnap = await transaction.get(usernameRef);
      if (usernameSnap.exists() && usernameSnap.data().uid !== user.uid) {
        const error = new Error("Nickname taken");
        error.code = "freev/nickname-taken";
        throw error;
      }

      if (oldUsernameRef) {
        const oldSnap = await transaction.get(oldUsernameRef);
        if (oldSnap.exists() && oldSnap.data().uid === user.uid) {
          transaction.delete(oldUsernameRef);
        }
      }

      transaction.set(usernameRef, {
        uid: user.uid,
        nickname,
        nicknameLower,
        updatedAt: serverTimestamp(),
      }, { merge: true });
    });
  };

  const reserveNicknameSafely = async (user, nickname, previousNicknameLower = "") => {
    try {
      await claimNickname(user, nickname, previousNicknameLower);
      return true;
    } catch (error) {
      if (error?.code === "permission-denied") {
        console.warn("Réservation du surnom ignorée : règles usernames manquantes.", error);
        return false;
      }
      throw error;
    }
  };

  const showProfileSection = (data = {}) => {
    if (!profileSection) return;
    profileSection.classList.remove("hidden");
    profileNickname.value = data.nickname || "";
    profileAvatarColor.value = normalizeAvatarColor(data.avatarColor);
    profileDisplayName.value = data.displayName || "";
    profileBio.value = data.bio || "";
    profileFavoriteType.value = data.favoriteType || "logiciels";
    updateAvatarPreview(data.nickname || data.displayName || "F", data.avatarColor);
    applyBannerTheme(data.bannerTheme || getStoredBannerTheme());
  };

  const hideProfileSection = () => {
    profileSection?.classList.add("hidden");
  };

  const updateNavProfileButton = (user = null, data = {}) => {
    const nickname = data.nickname || data.displayName || user?.displayName || "";
    const avatarColor = normalizeAvatarColor(data.avatarColor);

    if (!nickname) {
      if (navLoginButton) {
        navLoginButton.innerHTML = '<i class="fa-solid fa-user-astronaut"></i> Connexion';
        navLoginButton.classList.remove("text-brand-accent", "border-brand-accent/40", "bg-brand-accent/10");
      }
      if (navLoginMobileButton) {
        navLoginMobileButton.innerHTML = '<i class="fa-solid fa-user-astronaut text-lg"></i>';
        navLoginMobileButton.className = "h-10 w-10 rounded-full bg-white/5 text-brand-accent border border-white/10";
        navLoginMobileButton.setAttribute("aria-label", "Connexion");
        navLoginMobileButton.title = "Connexion";
      }
      return;
    }

    const safeNickname = escapeText(nickname).slice(0, 24);
    if (navLoginButton) {
      navLoginButton.innerHTML = `<span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-black text-brand-dark" style="background:${avatarColor}">${escapeText(getInitial(nickname))}</span> ${safeNickname}`;
      navLoginButton.classList.add("text-brand-accent", "border-brand-accent/40", "bg-brand-accent/10");
      navLoginButton.title = `Profil de ${nickname}`;
    }
    if (navLoginMobileButton) {
      navLoginMobileButton.innerHTML = `<span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-black text-brand-dark" style="background:${avatarColor}">${escapeText(getInitial(nickname))}</span><span>${safeNickname}</span>`;
      navLoginMobileButton.className = "h-10 px-3 rounded-full bg-brand-accent/10 text-brand-accent border border-brand-accent/30 flex items-center gap-2 text-sm font-bold";
      navLoginMobileButton.setAttribute("aria-label", `Profil de ${nickname}`);
      navLoginMobileButton.title = `Profil de ${nickname}`;
    }
  };

  const getReadableDate = (value) => {
    if (!value) return "jamais";
    if (value.toDate) return value.toDate().toLocaleString("fr-FR");
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "jamais" : date.toLocaleString("fr-FR");
  };

  const getDateMillis = (value) => {
    if (!value) return 0;
    if (value.toMillis) return value.toMillis();
    if (value.toDate) return value.toDate().getTime();
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
  };

  const downloadJson = (filename, payload) => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const getSaveOpenHref = (save = {}) => {
    if (save.pagePath) {
      const parts = String(save.pagePath).split("/").filter(Boolean);
      const folder = parts[parts.length - 2];
      const file = parts[parts.length - 1];
      if (folder && file) return `${folder}/${file}`;
    }
    return save.pageUrl || "#";
  };

  const getSaveBadgeClass = (kind = "") => {
    if (kind === "jeu") return "text-amber-300 border-amber-400/20 bg-amber-400/10";
    if (kind === "logiciel") return "text-cyan-300 border-cyan-400/20 bg-cyan-400/10";
    return "text-gray-300 border-white/10 bg-white/5";
  };

  const renderProfileSaves = async (user) => {
    if (!profileSavesSection || !profileSavesList || !user) return;
    profileSavesSection.classList.remove("hidden");
    profileSavesList.innerHTML = `<p class="text-gray-500">Chargement des sauvegardes...</p>`;

    try {
      const savesSnap = await getDocs(collection(db, "users", user.uid, "saves"));
      profileSavesCache = new Map();
      const saves = [];
      savesSnap.forEach((entry) => {
        const data = entry.data();
        profileSavesCache.set(entry.id, data);
        saves.push({ id: entry.id, ...data });
      });

      saves.sort((a, b) => getDateMillis(b.updatedAt || b.clientSavedAt) - getDateMillis(a.updatedAt || a.clientSavedAt));

      if (!saves.length) {
        profileSavesList.innerHTML = `<p class="text-gray-500">Aucune sauvegarde cloud pour le moment.</p>`;
        return;
      }

      profileSavesList.innerHTML = saves.map((save) => `
        <article class="rounded-lg border border-white/10 bg-black/20 p-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="font-bold text-white truncate">${escapeText(save.pageTitle || save.id)}</p>
              <p class="text-[11px] text-gray-500">${getReadableDate(save.updatedAt || save.clientSavedAt)}</p>
            </div>
            <span class="shrink-0 rounded-full border px-2 py-1 text-[10px] font-bold uppercase ${getSaveBadgeClass(save.pageKind)}">${escapeText(save.pageKind || "page")}</span>
          </div>
          <div class="mt-3 grid grid-cols-3 gap-2">
            <a href="${escapeText(getSaveOpenHref(save))}" class="text-center rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 px-2 py-1.5 text-[11px] font-bold text-gray-200">Ouvrir</a>
            <button type="button" data-save-export="${save.id}" class="rounded-lg bg-cyan-400/10 hover:bg-cyan-400/20 border border-cyan-400/20 px-2 py-1.5 text-[11px] font-bold text-cyan-300">Exporter</button>
            <button type="button" data-save-delete="${save.id}" class="rounded-lg bg-red-400/10 hover:bg-red-400/20 border border-red-400/20 px-2 py-1.5 text-[11px] font-bold text-red-300">Supprimer</button>
          </div>
        </article>
      `).join("");

      profileSavesList.querySelectorAll("[data-save-export]").forEach((button) => {
        button.addEventListener("click", () => exportProfileSave(button.dataset.saveExport));
      });
      profileSavesList.querySelectorAll("[data-save-delete]").forEach((button) => {
        button.addEventListener("click", () => deleteProfileSave(user, button.dataset.saveDelete));
      });
    } catch (error) {
      profileSavesList.innerHTML = `<p class="text-yellow-300">Sauvegardes indisponibles : ${escapeText(formatFirebaseError(error))}</p>`;
    }
  };

  const exportProfileSave = (saveId) => {
    const save = profileSavesCache.get(saveId);
    if (!save) return;
    downloadJson(`freev-${saveId}-save-${Date.now()}.json`, {
      format: "freev-cloud-save",
      version: 2,
      pageId: save.pageId || saveId,
      pageKind: save.pageKind || "page",
      pageTitle: save.pageTitle || saveId,
      exportedAt: new Date().toISOString(),
      data: save.data,
    });
    setAuthStatus("Sauvegarde exportée en JSON.", "success");
  };

  const deleteProfileSave = async (user, saveId) => {
    if (!user || !saveId) return;
    const save = profileSavesCache.get(saveId);
    const ok = confirm(`Supprimer la sauvegarde principale de ${save?.pageTitle || saveId} ?`);
    if (!ok) return;

    try {
      const historySnap = await getDocs(collection(db, "users", user.uid, "saves", saveId, "history"));
      await Promise.all(historySnap.docs.map((entry) => deleteDoc(entry.ref)));
      await deleteDoc(doc(db, "users", user.uid, "saves", saveId));
      setAuthStatus("Sauvegarde supprimée.", "success");
      await renderProfileSaves(user);
      const freshSnapshot = await getDoc(doc(db, "users", user.uid));
      if (freshSnapshot.exists()) renderCloudStats(user, freshSnapshot.data());
    } catch (error) {
      setAuthStatus(`Suppression impossible : ${formatFirebaseError(error)}`, "error");
    }
  };

  const renderCloudStats = async (user, data = {}) => {
    const statsEl = document.getElementById("profile-cloud-stats");
    if (!statsEl || !user) return;

    try {
      const savesSnap = await getDocs(collection(db, "users", user.uid, "saves"));
      const savedPages = savesSnap.size;
      const stats = data.stats || {};
      statsEl.innerHTML = `
        <div class="grid grid-cols-2 gap-2 mt-3">
          <div class="rounded-lg bg-white/5 border border-white/10 p-3">
            <p class="text-[10px] uppercase tracking-wide text-gray-500">Pages sauvées</p>
            <p class="text-lg font-bold text-white">${savedPages}</p>
          </div>
          <div class="rounded-lg bg-white/5 border border-white/10 p-3">
            <p class="text-[10px] uppercase tracking-wide text-gray-500">Sauvegardes</p>
            <p class="text-lg font-bold text-white">${Number(stats.cloudSaveCount || 0)}</p>
          </div>
        </div>
        <p class="mt-2 text-gray-400">Dernière sauvegarde : ${escapeText(stats.lastSavedPageTitle || "aucune")} · ${getReadableDate(stats.lastCloudSaveAt)}</p>
      `;
    } catch (error) {
      statsEl.innerHTML = `<p class="mt-2 text-yellow-300">Stats cloud indisponibles : ${escapeText(formatFirebaseError(error))}</p>`;
    }
  };

  const renderUserData = (user, data = {}) => {
    if (!firebaseUserData) return;
    firebaseUserData.classList.remove("hidden");
    firebaseUserData.className = "profile-summary-card text-xs text-gray-300";
    const profileReady = Boolean(data.profileCompleted && data.nickname);
    const avatarColor = normalizeAvatarColor(data.avatarColor);
    const profileTitle = profileReady ? data.nickname : "Compte Freev";
    const profileSubtitle = profileReady ? "Profil actif" : "Profil à compléter";
    const bannerTheme = normalizeBannerTheme(data.bannerTheme || selectedBannerTheme);
    const bannerLabel = bannerThemeLabels[bannerTheme];
    firebaseUserData.innerHTML = `
      <div class="relative z-10 flex items-start gap-3">
        <span class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-base font-black text-brand-dark border-2 border-slate-950" style="background:${avatarColor}">${escapeText(getInitial(profileTitle))}</span>
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between gap-2">
            <p class="font-bold text-white truncate">${escapeText(profileTitle)}</p>
            <span class="shrink-0 rounded-full border ${profileReady ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-200" : "border-yellow-300/20 bg-yellow-300/10 text-yellow-200"} px-2 py-0.5 text-[10px] font-bold">${profileSubtitle}</span>
          </div>
          <p class="break-all text-[11px] text-gray-400">${escapeText(user.email || "")}</p>
        </div>
      </div>
      <div class="relative z-10 mt-3 grid grid-cols-2 gap-2 text-[11px]">
        <p class="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5"><span class="text-gray-500">Créé :</span> ${data.createdAt?.toDate ? data.createdAt.toDate().toLocaleDateString("fr-FR") : "maintenant"}</p>
        <p class="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5"><span class="text-gray-500">Connexion :</span> ${data.lastLoginAt?.toDate ? data.lastLoginAt.toDate().toLocaleDateString("fr-FR") : "maintenant"}</p>
      </div>
      ${profileReady ? `<p class="relative z-10 mt-2 text-gray-400"><span class="text-gray-500">Préférence :</span> ${escapeText(data.favoriteType || "Freev")} · <span class="text-gray-500">Bannière :</span> ${escapeText(bannerLabel)}</p>` : `<p class="relative z-10 mt-2 text-yellow-300">Choisissez un surnom pour débloquer les sauvegardes cloud.</p>`}
      ${data.bio ? `<p class="relative z-10 mt-1 text-gray-400">${escapeText(data.bio)}</p>` : ""}
      <div id="profile-cloud-stats" class="mt-3 text-xs text-gray-400">Chargement des stats cloud...</div>
    `;
    showProfileSection(data);
    updateNavProfileButton(user, data);
    renderCloudStats(user, data);
    renderProfileSaves(user);
  };

  const renderAuthOnlyUser = (user) => {
    if (!firebaseUserData) return;
    firebaseUserData.classList.remove("hidden");
    firebaseUserData.className = "profile-summary-card text-xs text-gray-300";
    firebaseUserData.innerHTML = `
      <div class="relative z-10 flex items-start gap-3">
        <span class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-yellow-300 text-slate-950 font-black border-2 border-slate-950">${escapeText(getInitial(user.email || "F"))}</span>
        <div class="min-w-0 flex-1">
          <p class="font-bold text-white">Compte Firebase connecté</p>
          <p class="break-all text-[11px] text-gray-400">${escapeText(user.email || "")}</p>
        </div>
      </div>
      <p class="relative z-10 mt-2 text-yellow-300">Synchronisation Firestore bloquée.</p>
    `;
    updateNavProfileButton(user);
  };

  const saveAndLoadUserData = async (user, isNewUser = false) => {
    const userRef = doc(db, "users", user.uid);
    const snapshot = await getDoc(userRef);
    const baseData = {
      uid: user.uid,
      email: user.email,
      lastLoginAt: serverTimestamp(),
    };

    await setDoc(userRef, {
      ...baseData,
      ...(!snapshot.exists() ? { createdAt: serverTimestamp(), profileCompleted: false } : {}),
    }, { merge: true });

    const freshSnapshot = await getDoc(userRef);
    const data = freshSnapshot.exists() ? freshSnapshot.data() : baseData;
    renderUserData(user, data);
    if (data.profileCompleted && data.nickname) {
      setAuthStatus(isNewUser ? "Inscription réussie : votre profil est actif." : "Connexion réussie : profil retrouvé.", "success");
    } else {
      setAuthStatus(isNewUser ? "Compte créé. Choisissez maintenant votre surnom pour terminer le profil." : "Connexion réussie. Complétez votre profil pour activer les sauvegardes cloud.", "info");
    }
  };

  const syncUserDataSafely = async (user, isNewUser = false) => {
    try {
      await saveAndLoadUserData(user, isNewUser);
    } catch (error) {
      renderAuthOnlyUser(user);
      const prefix = isNewUser ? "Compte créé, mais la synchronisation Firestore a échoué." : "Connexion réussie, mais la synchronisation Firestore a échoué.";
      setAuthStatus(`${prefix} ${formatFirebaseError(error)}`, "error");
      console.error("Erreur Firestore", error);
    } finally {
      lastSyncedUid = user.uid;
    }
  };

  const getCredentials = () => {
    const email = emailInput?.value.trim() || "";
    const password = passwordInput?.value || "";

    if (!email) {
      setAuthStatus("Entrez votre email pour vous connecter.", "error");
      emailInput?.focus();
      return null;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setAuthStatus("L'adresse email n'est pas valide.", "error");
      emailInput?.focus();
      return null;
    }

    if (!password) {
      setAuthStatus("Entrez votre mot de passe pour vous connecter.", "error");
      passwordInput?.focus();
      return null;
    }

    if (password.length < 6) {
      setAuthStatus("Le mot de passe doit contenir au moins 6 caractères.", "error");
      passwordInput?.focus();
      return null;
    }

    return { email, password };
  };

  applyBannerTheme(getStoredBannerTheme(), { persist: false });

  profileNickname?.addEventListener("input", () => updateAvatarPreview());
  profileAvatarColor?.addEventListener("input", () => updateAvatarPreview());
  profileBannerButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyBannerTheme(button.dataset.profileBanner || "aurora");
      setAuthStatus(`Bannière ${bannerThemeLabels[selectedBannerTheme]} appliquée. Sauvegardez le profil pour la garder sur Firebase.`, "success");
    });
  });
  refreshSavesButton?.addEventListener("click", async () => {
    if (!auth.currentUser) {
      setAuthStatus("Connectez-vous pour voir vos sauvegardes.", "error");
      return;
    }
    await renderProfileSaves(auth.currentUser);
  });

  saveProfileButton?.addEventListener("click", async () => {
    const user = auth.currentUser;
    if (!user) {
      setAuthStatus("Connectez-vous avant de créer un profil.", "error");
      return;
    }

    const nickname = normalizeNickname(profileNickname.value);
    if (!isValidNickname(nickname)) {
      setAuthStatus("Le surnom doit faire 3 à 24 caractères : lettres, chiffres, tiret ou underscore.", "error");
      profileNickname.focus();
      return;
    }

    const displayName = profileDisplayName.value.trim() || nickname;
    const profileData = {
      nickname,
      nicknameLower: nickname.toLowerCase(),
      displayName,
      avatarColor: normalizeAvatarColor(profileAvatarColor.value),
      bio: profileBio.value.trim().slice(0, 160),
      favoriteType: profileFavoriteType.value,
      bannerTheme: selectedBannerTheme,
      profileCompleted: true,
      updatedAt: serverTimestamp(),
    };

    saveProfileButton.disabled = true;
    saveProfileButton.classList.add("opacity-60", "cursor-wait");

    try {
      const userRef = doc(db, "users", user.uid);
      const currentProfile = await getDoc(userRef);
      const previousNicknameLower = currentProfile.exists() ? currentProfile.data().nicknameLower : "";
      const nicknameReserved = await reserveNicknameSafely(user, nickname, previousNicknameLower);
      await setDoc(userRef, profileData, { merge: true });
      await updateProfile(user, { displayName });
      const freshSnapshot = await getDoc(userRef);
      renderUserData(user, freshSnapshot.exists() ? freshSnapshot.data() : profileData);
      setAuthStatus(nicknameReserved
        ? "Profil sauvegardé. Les sauvegardes cloud sont maintenant actives."
        : "Profil sauvegardé. Pour réserver les surnoms uniques, ajoutez les règles Firestore usernames.",
        "success");
    } catch (error) {
      setAuthStatus(`Profil non sauvegardé : ${formatFirebaseError(error)}`, "error");
      console.error("Erreur profil", error);
    } finally {
      saveProfileButton.disabled = false;
      saveProfileButton.classList.remove("opacity-60", "cursor-wait");
    }
  });

  logoutButton?.addEventListener("click", async () => {
    try {
      await signOut(auth);
      emailInput.value = "";
      passwordInput.value = "";
      firebaseUserData?.classList.add("hidden");
      hideProfileSection();
      profileSavesSection?.classList.add("hidden");
      updateNavProfileButton();
      setAuthStatus("Déconnecté.", "success");
    } catch (error) {
      setAuthStatus(`Déconnexion impossible : ${formatFirebaseError(error)}`, "error");
    }
  });

  resetPasswordButton?.addEventListener("click", async () => {
    const email = emailInput.value.trim();
    if (!email) {
      setAuthStatus("Entrez votre email, puis cliquez sur mot de passe oublié.", "error");
      emailInput.focus();
      return;
    }

    try {
      await sendPasswordResetEmail(auth, email);
      setAuthStatus("Email de réinitialisation envoyé si ce compte existe.", "success");
    } catch (error) {
      setAuthStatus(`Réinitialisation impossible : ${formatFirebaseError(error)}`, "error");
    }
  });

  const handleRegister = async (event) => {
    event?.preventDefault();
    if (authActionInProgress) {
      setAuthStatus("Une action Firebase est déjà en cours...", "info");
      return;
    }

    const credentials = getCredentials();
    if (!credentials) return;

    authActionInProgress = true;
    setAuthBusy(true, "register");
    manualAuthInProgress = true;
    try {
      setAuthStatus("Inscription en cours...");
      await new Promise((resolve) => setTimeout(resolve, 0));
      const { user } = await createUserWithEmailAndPassword(auth, credentials.email, credentials.password);
      await syncUserDataSafely(user, true);
    } catch (error) {
      setAuthStatus(`Inscription impossible : ${formatFirebaseError(error)}`, "error");
      console.error("Erreur inscription", error);
    } finally {
      manualAuthInProgress = false;
      authActionInProgress = false;
      setAuthBusy(false);
    }
  };

  const handleLogin = async (event) => {
    event?.preventDefault();
    if (authActionInProgress) {
      setAuthStatus("Connexion déjà en cours...", "info");
      return;
    }

    const credentials = getCredentials();
    if (!credentials) return;

    authActionInProgress = true;
    setAuthBusy(true, "login");
    manualAuthInProgress = true;
    try {
      setAuthStatus("Connexion en cours...");
      await new Promise((resolve) => setTimeout(resolve, 0));
      const { user } = await signInWithEmailAndPassword(auth, credentials.email, credentials.password);
      await syncUserDataSafely(user);
    } catch (error) {
      setAuthStatus(`Connexion impossible : ${formatFirebaseError(error)}`, "error");
      console.error("Erreur connexion", error);
    } finally {
      manualAuthInProgress = false;
      authActionInProgress = false;
      setAuthBusy(false);
    }
  };

  authForm?.addEventListener("submit", handleLogin);
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    if (!target) return;

    if (target.closest("#login-button")) {
      handleLogin(event);
      return;
    }

    if (target.closest("#register-button")) {
      handleRegister(event);
    }
  });

  async function saveAiConfigToCloud(config) {
    if (!auth.currentUser) return false;
    const userRef = doc(db, "users", auth.currentUser.uid);
    await setDoc(userRef, { aiConfig: config }, { merge: true });
    return true;
  }

  async function loadAiConfigFromCloud() {
    if (!auth.currentUser) return null;
    const userRef = doc(db, "users", auth.currentUser.uid);
    const snapshot = await getDoc(userRef);
    if (snapshot.exists() && snapshot.data().aiConfig) return snapshot.data().aiConfig;
    return null;
  }

  async function saveAiConfigsListToCloud(list) {
    if (!auth.currentUser) return false;
    const userRef = doc(db, "users", auth.currentUser.uid);
    await setDoc(userRef, { aiConfigsList: list }, { merge: true });
    return true;
  }

  async function loadAiConfigsListFromCloud() {
    if (!auth.currentUser) return null;
    const userRef = doc(db, "users", auth.currentUser.uid);
    const snapshot = await getDoc(userRef);
    if (snapshot.exists() && Array.isArray(snapshot.data().aiConfigsList)) return snapshot.data().aiConfigsList;
    return null;
  }

  // Historique des conversations (chaque question + réponse, IA locale ou en ligne)
  async function saveChatHistoryEntryToCloud(entry) {
    if (!auth.currentUser || !entry?.id) return false;
    const entryRef = doc(db, "users", auth.currentUser.uid, "chatHistory", entry.id);
    await setDoc(entryRef, { ...entry, savedAt: serverTimestamp() });
    return true;
  }

  async function loadChatHistoryFromCloud() {
    if (!auth.currentUser) return null;
    const snap = await getDocs(collection(db, "users", auth.currentUser.uid, "chatHistory"));
    return snap.docs.map((d) => d.data());
  }

  window.FreevAuthReady = true;
  window.FreevAuthActions = {
    login: handleLogin,
    register: handleRegister,
    saveAiConfig: saveAiConfigToCloud,
    loadAiConfig: loadAiConfigFromCloud,
    saveAiConfigsList: saveAiConfigsListToCloud,
    loadAiConfigsList: loadAiConfigsListFromCloud,
    saveChatHistoryEntry: saveChatHistoryEntryToCloud,
    loadChatHistory: loadChatHistoryFromCloud,
    getCurrentUser: () => auth.currentUser,
  };

  onAuthStateChanged(auth, (user) => {
    if (user) {
      emailInput.value = user.email || "";
      if (typeof window.syncAiConfigFromCloud === "function") {
        window.syncAiConfigFromCloud();
      }
      if (typeof window.syncChatHistoryFromCloud === "function") {
        window.syncChatHistoryFromCloud();
      }
      if (manualAuthInProgress || lastSyncedUid === user.uid) return;
      syncUserDataSafely(user);
    } else {
      lastSyncedUid = null;
      firebaseUserData?.classList.add("hidden");
      hideProfileSection();
      profileSavesSection?.classList.add("hidden");
      updateNavProfileButton();
    }
  });

  console.log("Firebase connecté 🔥", app);
