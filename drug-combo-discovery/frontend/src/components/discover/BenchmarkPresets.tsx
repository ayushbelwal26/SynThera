import { Bookmark } from 'lucide-react';
import type { Drug } from '../../types/api';

export interface BenchmarkPreset {
  id: string;
  name: string;
  drugA: Drug;
  drugB: Drug;
  cellLine: string;
  expectedClass: 'synergy' | 'antagonism' | 'additive';
  indication: string;
}

export const BENCHMARKS: BenchmarkPreset[] = [
  {
    id: 'benchmark-1',
    name: 'Temozolomide × Cyclophosphamide',
    drugA: { id: 'DB00853', name: 'Temozolomide' },
    drugB: { id: 'DB00531', name: 'Cyclophosphamide' },
    cellLine: 'T98G',
    expectedClass: 'synergy',
    indication: 'Glioblastoma Multiforme (CNS)',
  },
  {
    id: 'benchmark-2',
    name: 'Temozolomide × Docetaxel',
    drugA: { id: 'DB00853', name: 'Temozolomide' },
    drugB: { id: 'DB01248', name: 'Docetaxel' },
    cellLine: 'OVCAR-5',
    expectedClass: 'antagonism',
    indication: 'Ovarian Carcinoma',
  },
  {
    id: 'benchmark-3',
    name: 'Docetaxel × Topotecan',
    drugA: { id: 'DB01248', name: 'Docetaxel' },
    drugB: { id: 'DB01030', name: 'Topotecan' },
    cellLine: 'A498',
    expectedClass: 'additive',
    indication: 'Renal Cell Carcinoma',
  },
];

interface BenchmarkPresetsProps {
  onSelect: (preset: BenchmarkPreset) => void;
  disabled?: boolean;
}

export const BenchmarkPresets: React.FC<BenchmarkPresetsProps> = ({
  onSelect,
  disabled = false,
}) => {
  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-md p-4">
      <div className="flex items-center gap-2 mb-2.5">
        <Bookmark className="w-3.5 h-3.5 text-[#0D9488]" />
        <h4 className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
          Curated Benchmark Reference Pairs
        </h4>
      </div>
      <p className="text-xs text-[#717784] mb-3">
        Load gold-standard oncology combinations with experimental multi-drug synergy, additive, or antagonism profiles:
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        {BENCHMARKS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(preset)}
            className="text-left p-2.5 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] hover:border-[#CBD5E1] rounded transition-all group disabled:opacity-50"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-xs text-[#0F172A] group-hover:text-[#0D9488] transition-colors">
                {preset.name}
              </span>
              <span
                className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded font-medium ${
                  preset.expectedClass === 'synergy'
                    ? 'bg-[#ECFDF5] text-[#047857]'
                    : preset.expectedClass === 'antagonism'
                    ? 'bg-[#FEF2F2] text-[#B91C1C]'
                    : 'bg-[#FFFBEB] text-[#B45309]'
                }`}
              >
                {preset.expectedClass}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] text-[#64748B] font-mono">
              <span>{preset.indication}</span>
              <span className="bg-[#E2E8F0] px-1 rounded text-[#334155]">
                {preset.cellLine}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
