import React from 'react';
import { ArrowUpCircle, ArrowDownCircle, CheckCircle2, Info, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface BiomarkerStatusIndicatorProps {
  interpretation: string;
  compact?: boolean;
  className?: string;
}

export const BiomarkerStatusIndicator: React.FC<BiomarkerStatusIndicatorProps> = ({ 
  interpretation, 
  compact = false,
  className = ''
}) => {
  const { t } = useTranslation();
  const status = interpretation.toLowerCase();
  const isHigh = status.includes('high') || status === 'h';
  const isLow = status.includes('low') || status === 'l';
  const isNormal = status === 'normal' || status === 'n';
  if (!isHigh && !isLow && !isNormal) {
    const abnormal = status === 'abnormal' || status === 'warning';
    const Icon = abnormal ? AlertCircle : Info;
    const label = status === 'nodata' ? t('common.no_data', 'Нет данных')
      : t(`biomarkers.status.${abnormal ? status : 'unknown'}`, abnormal ? interpretation : 'Не определён');
    return <div className={`flex flex-col items-end shrink-0 ${className}`}>
      <Icon className={`w-5 h-5 ${abnormal ? 'text-amber-600' : 'text-gray-400'}`} />
      <span className="mt-1 text-[8px] font-black uppercase tracking-tighter text-gray-500">{label}</span>
    </div>;
  }

  if (isHigh) {
    return (
      <div className={`flex flex-col items-end shrink-0 ${className}`}>
        <div className={`${compact ? 'p-1.5' : 'p-2'} bg-red-50 dark:bg-red-900/20 rounded-2xl shadow-inner animate-pulse`}>
          <ArrowUpCircle className={`${compact ? 'w-5 h-5' : 'w-6 h-6'} text-red-500 shadow-[0_0_12px_rgba(239,68,68,0.3)]`} />
        </div>
        <span className="mt-1 text-[8px] font-black uppercase tracking-tighter text-red-500">
          {interpretation}
        </span>
      </div>
    );
  }

  if (isLow) {
    return (
      <div className={`flex flex-col items-end shrink-0 ${className}`}>
        <div className={`${compact ? 'p-1.5' : 'p-2'} bg-blue-50 dark:bg-blue-900/20 rounded-2xl shadow-inner animate-pulse`}>
          <ArrowDownCircle className={`${compact ? 'w-5 h-5' : 'w-6 h-6'} text-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.3)]`} />
        </div>
        <span className="mt-1 text-[8px] font-black uppercase tracking-tighter text-blue-500">
          {interpretation}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex flex-col items-end shrink-0 ${className}`}>
      <div className={`${compact ? 'p-1.5' : 'p-2'} bg-green-50/30 dark:bg-green-900/10 rounded-2xl`}>
        <CheckCircle2 className={`${compact ? 'w-5 h-5' : 'w-6 h-6'} text-green-300 dark:text-green-800/40`} />
      </div>
      <span className="mt-1 text-[8px] font-black uppercase tracking-tighter text-gray-300">
        {t('biomarkers.status.normal', 'Норма')}
      </span>
    </div>
  );
};
