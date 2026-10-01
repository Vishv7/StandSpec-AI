import React from 'react';

export const EXAMPLE_QUERIES = [
  {
    label: "11 kV XLPE Power Cable",
    query: "Supply of 11 kV grade XLPE insulated 3-core 240 sq mm aluminium conductor underground power cables conforming to standard specifications with outer extruded PVC sheathing.",
    category: "Electrical (ETD)",
  },
  {
    label: "HDPE Pipe PN 10",
    query: "Supply of High Density Polyethylene (HDPE) pipes for rural potable water distribution networks. Pipe material grade PE-100, pressure rating PN 10, outside diameter 110 mm.",
    category: "Civil (CED)",
  },
  {
    label: "415 V 630 A Circuit Breaker",
    query: "Procurement of 415 V AC, 50 Hz, 630 A four-pole air circuit breaker (ACB) with microprocessor release and breaking capacity 50 kA for indoor main LT panel.",
    category: "Electrical (ETD)",
  },
  {
    label: "uPVC Doors and Windows",
    query: "Supply and fixing of unplasticized polyvinyl chloride (uPVC) profiles for external windows and ventilators with multi-point locking and EPDM weather gaskets.",
    category: "Civil (CED)",
  },
  {
    label: "Centrifugally Cast DI Pipes",
    query: "Procurement of centrifugally cast ductile iron pressure pipes Class K9 with push-on joints for municipal bulk water transmission mains.",
    category: "Civil (CED)",
  },
];

export default function ExampleQueries({ onSelectExample, disabled }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
          Example Procurement Specifications
        </span>
        <span className="text-[11px] text-slate-400">
          Clicking populates the query box (does not auto-run)
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((item, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectExample(item.query)}
            className="group flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-emerald-50/80 border border-slate-200 hover:border-emerald-300 text-xs font-medium text-slate-700 hover:text-emerald-900 transition-all shadow-2xs text-left cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-[15px] text-slate-400 group-hover:text-emerald-600 transition-colors">
              input
            </span>
            <span>{item.label}</span>
            <span className="text-[10px] font-mono px-1 rounded bg-slate-200/60 text-slate-600 group-hover:bg-emerald-100 group-hover:text-emerald-800">
              {item.category}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
