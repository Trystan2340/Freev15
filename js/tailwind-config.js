        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Poppins', 'sans-serif'],
                        heading: ['Montserrat', 'sans-serif'],
                    },
                    colors: {
                        brand: {
                            dark: '#0f172a',
                            primary: '#0ea5e9', // Sky blue
                            secondary: '#a855f7', // Purple
                            accent: '#22d3ee', // Cyan
                        }
                    },
                    animation: {
                        'float': 'float 6s ease-in-out infinite',
                        'pulse-glow': 'pulse-glow 3s infinite',
                    },
                    keyframes: {
                        float: {
                            '0%, 100%': { transform: 'translateY(0)' },
                            '50%': { transform: 'translateY(-20px)' },
                        },
                        'pulse-glow': {
                            '0%, 100%': { boxShadow: '0 0 20px #0ea5e9' },
                            '50%': { boxShadow: '0 0 40px #a855f7' },
                        }
                    }
                }
            }
        }
