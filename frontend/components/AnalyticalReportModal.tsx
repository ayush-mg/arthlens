'use client';

import React, { useState } from 'react';
import {
  FileCheck2,
  Printer,
  X,
  ShieldCheck,
  Building,
  Calendar,
  Hash,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
} from 'lucide-react';
import { GeoUnitSummary, IndicatorItem } from '../lib/types';
import { audioEngine } from '../lib/audio';
import { downloadReportFile, getTerritorialDossierDownloadUrl } from '../lib/api';

interface AnalyticalReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedUnit: GeoUnitSummary;
  indicators: IndicatorItem[];
}

export const AnalyticalReportModal: React.FC<AnalyticalReportModalProps> = ({
  isOpen,
  onClose,
  selectedUnit,
  indicators,
}) => {
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  if (!isOpen) return null;

  const handlePrint = () => {
    audioEngine.playClick(1000);
    window.print();
  };

  const handleDownload = async (format: 'json' | 'csv' | 'xlsx' | 'pdf') => {
    setDownloadingFormat(format);
    audioEngine.playClick(950);
    try {
      const url = getTerritorialDossierDownloadUrl(selectedUnit.id, format);
      const cleanName = selectedUnit.name.toLowerCase().replace(/\s+/g, '-');
      await downloadReportFile(url, `arthlens-dossier-${cleanName}.${format}`);
    } catch (err: unknown) {
      console.error(`Export failed for ${format}:`, err);
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-editorial-forest-dark/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-lg border border-editorial-brass bg-editorial-ivory p-6 sm:p-8 shadow-editorial-lg text-editorial-charcoal space-y-6">
        {/* Header Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-editorial-brass/30 pb-4">
          <div className="flex items-center space-x-2">
            <FileCheck2 className="h-6 w-6 text-editorial-copper" />
            <div>
              <h2 className="font-serif text-lg font-bold text-editorial-forest">
                ArthLens Decision Dossier
              </h2>
              <span className="font-mono text-[10px] text-editorial-charcoal-light">
                Auditable Territorial Evidence Brief • Handbook Part 10.3
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={() => handleDownload('json')}
              className="inline-flex items-center space-x-1 rounded border border-editorial-brass/40 bg-editorial-paper px-2 py-1 font-mono text-[11px] font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
              title="Download JSON Dossier"
            >
              <FileCode className="h-3 w-3" />
              <span>{downloadingFormat === 'json' ? '…' : 'JSON'}</span>
            </button>

            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={() => handleDownload('csv')}
              className="inline-flex items-center space-x-1 rounded border border-editorial-brass/40 bg-editorial-paper px-2 py-1 font-mono text-[11px] font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
              title="Download CSV Matrix (Formula-Injection Protected)"
            >
              <FileSpreadsheet className="h-3 w-3" />
              <span>{downloadingFormat === 'csv' ? '…' : 'CSV'}</span>
            </button>

            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={() => handleDownload('xlsx')}
              className="inline-flex items-center space-x-1 rounded border border-editorial-brass/40 bg-editorial-paper px-2 py-1 font-mono text-[11px] font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
              title="Download Excel Workbook"
            >
              <FileSpreadsheet className="h-3 w-3" />
              <span>{downloadingFormat === 'xlsx' ? '…' : 'XLSX'}</span>
            </button>

            <button
              type="button"
              disabled={downloadingFormat !== null}
              onClick={() => handleDownload('pdf')}
              className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest bg-editorial-forest px-3 py-1 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer shadow-sm disabled:opacity-50"
              title="Download Publication PDF"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>{downloadingFormat === 'pdf' ? 'Generating…' : 'PDF'}</span>
            </button>

            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center space-x-1 rounded border border-editorial-brass/40 bg-editorial-paper px-2.5 py-1 font-mono text-[11px] font-bold text-editorial-charcoal hover:bg-editorial-ivory transition-colors cursor-pointer"
            >
              <Printer className="h-3 w-3" />
              <span>Print</span>
            </button>

            <button
              type="button"
              aria-label="Close dossier modal"
              onClick={() => {
                audioEngine.playClick(900);
                onClose();
              }}
              className="p-1 rounded border border-editorial-brass/40 text-editorial-charcoal hover:bg-editorial-paper transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Dossier Document Body */}
        <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-6 space-y-6 font-mono text-xs shadow-sm">
          {/* Official Masthead Stamp */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-editorial-brass/20 pb-4">
            <div>
              <span className="text-[10px] text-editorial-copper font-bold uppercase tracking-widest block">
                Target Administrative Territory
              </span>
              <h3 className="font-serif text-xl font-bold text-editorial-forest">
                {selectedUnit.name}
              </h3>
              <p className="text-[11px] text-editorial-charcoal-light">
                Canonical LGD: {selectedUnit.lgd_code} {selectedUnit.census_code ? `• Census 2011: ${selectedUnit.census_code}` : ''}
              </p>
            </div>
            <div className="text-right">
              <span className="rounded border border-editorial-forest/50 bg-editorial-forest/10 px-2 py-1 text-[10px] font-bold text-editorial-forest">
                VERIFIED LEDGER EXTRACT
              </span>
              <p className="text-[10px] text-editorial-charcoal-light mt-1">
                Datum: EPSG:4326 • PostGIS 16
              </p>
            </div>
          </div>

          {/* Indicators Matrix */}
          <div className="space-y-3">
            <span className="text-xs font-bold text-editorial-forest uppercase tracking-wider block">
              Ingested Indicators ({indicators.length} Observations)
            </span>

            {indicators.length === 0 ? (
              <div className="p-4 rounded border border-dashed border-editorial-brass/40 bg-editorial-ivory text-center text-xs text-editorial-charcoal-light">
                No ingested economic observations registered for {selectedUnit.name}. Missing figures fail closed (never zero).
              </div>
            ) : (
              <div className="divide-y divide-editorial-brass/20 border-y border-editorial-brass/20">
                {indicators.map((ind) => (
                  <div key={ind.id} className="py-2.5 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-serif font-bold text-editorial-forest block">
                        {ind.definition_key}
                      </span>
                      <span className="text-[10px] text-editorial-charcoal-light">
                        As of: {ind.as_of} • Kind: {ind.kind}
                      </span>
                    </div>
                    <div className="text-right font-mono">
                      <span className="font-bold text-sm text-editorial-forest block">
                        {ind.value !== null ? `${ind.value.toLocaleString('en-IN')} ${ind.unit}` : 'Unavailable'}
                      </span>
                      <span className="text-[10px] text-editorial-copper font-semibold">
                        Floor {ind.evidence_floor} ({ind.quality_status})
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Epistemic Attestation Footer */}
          <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3.5 space-y-1.5 text-[11px] text-editorial-charcoal-light">
            <div className="flex items-center space-x-2 text-editorial-forest font-bold">
              <ShieldCheck className="h-4 w-4 text-editorial-forest shrink-0" />
              <span>Epistemic Integrity Statement</span>
            </div>
            <p className="leading-relaxed">
              Every value above represents an immutable quantity record in the ArthLens PostgreSQL epistemic ledger. In accordance with Handbook Part 10, observations are backed by official government gazettes (DS-05 Census 2011 / LGD Master 2026).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
