import React from 'react';
import { Play } from 'lucide-react';
import { useI18n } from '../i18n';

interface ReplayButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export const ReplayButton: React.FC<ReplayButtonProps> = ({ onClick, disabled = false }) => {
  const { t } = useI18n();

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="replay-mode-button"
      title={t('replayMode')}
    >
      <Play size={20} />
      <span className="replay-mode-label">{t('replayMode')}</span>
    </button>
  );
};
