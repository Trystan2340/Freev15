      (() => {
        const modal = document.getElementById('login-modal');

        const openLoginModal = () => {
          if (!modal) return;
          modal.classList.remove('hidden');
          document.body.classList.add('overflow-hidden');
          if (typeof closeMobileMenu === 'function') closeMobileMenu();
          setTimeout(() => document.getElementById('auth-email')?.focus(), 50);
        };

        const closeLoginModal = () => {
          if (!modal) return;
          modal.classList.add('hidden');
          document.body.classList.remove('overflow-hidden');
        };

        window.FreevAuthModal = {
          open: openLoginModal,
          close: closeLoginModal,
        };

        document.addEventListener('click', (event) => {
          const target = event.target instanceof Element ? event.target : event.target?.parentElement;
          if (!target) return;

          const openButton = target.closest('[data-freev-open-login], #open-login-modal, #open-login-modal-mobile');
          if (openButton) {
            event.preventDefault();
            openLoginModal();
            return;
          }

          if (event.target === modal || target.closest('#close-login-modal')) {
            event.preventDefault();
            closeLoginModal();
          }
        });

        document.addEventListener('keydown', (event) => {
          if (event.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeLoginModal();
          }
        });

        if (location.hash === '#login') {
          openLoginModal();
        }
      })();
