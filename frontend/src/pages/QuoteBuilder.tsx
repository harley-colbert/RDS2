import React from 'react';
import ExcelSummaryPanel from '../components/ExcelSummaryPanel';

export default function QuoteBuilder() {
  return (
    <div className="h-screen grid grid-cols-3">
      <div className="border-r overflow-auto">
        <div className="p-4 text-sm text-gray-700">System Options Panel (placeholder)</div>
      </div>
      <div className="border-r overflow-auto">
        <div className="p-4 text-sm text-gray-700">Pricing Summary Panel (placeholder)</div>
      </div>
      <ExcelSummaryPanel />
    </div>
  );
}
