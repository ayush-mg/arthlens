'use client';
import { MotionButton } from '@/components/ui/motion-button';

import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: ToastMessage[];
  showToast: (type: ToastType, message: string, title?: string, duration?: number) => void;
  removeToast: (id: string) => void;
  toast: {
    success: (message: string, title?: string) => void;
    error: (message: string, title?: string) => void;
    info: (message: string, title?: string) => void;
    warning: (message: string, title?: string) => void;
  };
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (type: ToastType, message: string, title?: string, duration: number = 4000) => {
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
      const newToast: ToastMessage = { id, type, title, message, duration };
      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  const toast = useMemo(() => ({
    success: (message: string, title?: string) => showToast('success', message, title),
    error: (message: string, title?: string) => showToast('error', message, title),
    info: (message: string, title?: string) => showToast('info', message, title),
    warning: (message: string, title?: string) => showToast('warning', message, title),
  }), [showToast]);
  const contextValue = useMemo(
    () => ({ toasts, showToast, removeToast, toast }),
    [toasts, showToast, removeToast, toast],
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {/* Toast Notification Container */}
      <div
        className="fixed bottom-5 right-5 z-50 flex flex-col space-y-3 pointer-events-none max-w-sm w-full"
        role="region"
        aria-label="Notifications"
      >
        {toasts.map((t) => {
          const typeStyles = {
            success: 'border-emerald-500/40 bg-emerald-950/80 text-emerald-100 shadow-emerald-950/50',
            error: 'border-rose-500/40 bg-rose-950/80 text-rose-100 shadow-rose-950/50',
            warning: 'border-amber-500/40 bg-amber-950/80 text-amber-100 shadow-amber-950/50',
            info: 'border-cyan-500/40 bg-cyan-950/80 text-cyan-100 shadow-cyan-950/50',
          }[t.type];

          const IconComponent = {
            success: CheckCircle2,
            error: AlertCircle,
            warning: AlertTriangle,
            info: Info,
          }[t.type];

          return (
            <div
              key={t.id}
              role="alert"
              aria-live="assertive"
              className={`pointer-events-auto backdrop-blur-xl border rounded-none p-4 shadow-2xl transition-all duration-300 animate-in fade-in slide-in-from-bottom-3 ${typeStyles}`}
            >
              <div className="flex items-start justify-between gap-3">
                <IconComponent className="h-5 w-5 shrink-0 mt-0.5" />
                <div className="flex-1 text-xs">
                  {t.title && <div className="font-semibold text-sm mb-0.5">{t.title}</div>}
                  <div className="leading-relaxed opacity-95">{t.message}</div>
                </div>
                <MotionButton
                  onClick={() => removeToast(t.id)}
                  className="opacity-70 hover:opacity-100 transition-opacity p-1 rounded-none hover:bg-white/10"
                  aria-label="Close notification"
                >
                  <X className="h-4 w-4" />
                </MotionButton>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

const fallbackToastContext: ToastContextValue = {
  toasts: [],
  showToast: (type, message) => console.log(`[Toast ${type}]: ${message}`),
  removeToast: () => {},
  toast: {
    success: (message) => console.log(`[Toast Success]: ${message}`),
    error: (message) => console.error(`[Toast Error]: ${message}`),
    info: (message) => console.log(`[Toast Info]: ${message}`),
    warning: (message) => console.warn(`[Toast Warning]: ${message}`),
  },
};

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  return context ?? fallbackToastContext;
}
