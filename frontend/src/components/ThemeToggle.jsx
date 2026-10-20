import React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Moon, Sun } from 'lucide-react';
import { toggleTheme, useTheme } from '../lib/theme';

const ThemeToggle = ({ className = '' }) => {
  const theme = useTheme();
  const Icon = theme === 'dark' ? Sun : Moon;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
      className={`btn-ghost h-9 w-9 p-0 rounded-full ${className}`}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={theme}
          initial={{ opacity: 0, rotate: -45 }}
          animate={{ opacity: 1, rotate: 0 }}
          exit={{ opacity: 0, rotate: 45 }}
          transition={{ duration: 0.15 }}
          className="flex"
        >
          <Icon size={16} />
        </motion.span>
      </AnimatePresence>
    </button>
  );
};

export default ThemeToggle;
