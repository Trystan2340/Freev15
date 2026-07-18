      (() => {
        try {
          const savedTheme = localStorage.getItem('freev_profile_banner_theme');
          if (['aurora', 'circuit', 'cosmos', 'pulse', 'calm', 'prism', 'rain', 'vortex', 'horizon', 'comet'].includes(savedTheme)) {
            document.body.dataset.freevBanner = savedTheme;
          }
        } catch (error) {}
      })();
