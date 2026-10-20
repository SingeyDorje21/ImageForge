import React from 'react';
import { Toaster } from 'sonner';
import { useTheme } from '../lib/theme';

const ThemedToaster = () => <Toaster position="bottom-center" theme={useTheme()} closeButton />;

export default ThemedToaster;
