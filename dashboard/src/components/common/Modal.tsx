import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Button } from './Button';

interface ModalProps {
  isOpen: boolean;
  title: string;
  children: ReactNode;
  confirmText?: string;
  cancelText?: string;
  onClose: () => void;
  onConfirm?: () => void;
}

export const Modal = ({ isOpen, title, children, confirmText = 'Confirm', cancelText = 'Cancel', onClose, onConfirm }: ModalProps) => {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-800" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="modal-title" className="text-2xl font-semibold text-slate-900 dark:text-white">
            {title}
          </h2>
          <button onClick={onClose} aria-label="Close modal" className="text-slate-500 hover:text-slate-700 dark:text-slate-300">
            ×
          </button>
        </div>
        <div className="mb-6 text-slate-700 dark:text-slate-200">{children}</div>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            {cancelText}
          </Button>
          {onConfirm && (
            <Button onClick={onConfirm}>
              {confirmText}
            </Button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
};
