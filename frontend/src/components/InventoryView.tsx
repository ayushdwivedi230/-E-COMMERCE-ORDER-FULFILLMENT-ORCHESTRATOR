import React from "react";
import { Package, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import type { Product } from "../types";

interface InventoryViewProps {
  products: Product[];
  onSelectProductForOrder?: (product: Product) => void;
}

export const InventoryView: React.FC<InventoryViewProps> = ({
  products,
  onSelectProductForOrder,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Catalog Inventory & Atomic Stock Status
          </h2>
        </div>
        <span className="text-xs text-slate-400">Guaranteed ACID reservation with rollback</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {products.map((p) => {
          let stockStatus = "In Stock";
          let stockBadge = "bg-emerald-950 text-emerald-400 border-emerald-800";
          let StockIcon = CheckCircle2;

          if (p.stock_quantity === 0) {
            stockStatus = "Out of Stock";
            stockBadge = "bg-rose-950 text-rose-400 border-rose-800";
            StockIcon = XCircle;
          } else if (p.stock_quantity <= 5) {
            stockStatus = "Low Stock";
            stockBadge = "bg-amber-950 text-amber-400 border-amber-800";
            StockIcon = AlertTriangle;
          }

          return (
            <div
              key={p.id}
              className="bg-slate-950 border border-slate-800 rounded-lg p-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <span className="text-xs font-mono font-bold text-indigo-400">{p.sku}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold flex items-center gap-1 ${stockBadge}`}>
                    <StockIcon className="w-3 h-3" />
                    {stockStatus}
                  </span>
                </div>
                <h3 className="font-bold text-sm text-slate-200 mt-1">{p.name}</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{p.description}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-slate-400">Unit Price:</span>
                  <span className="font-mono font-bold text-slate-200">${Number(p.price || 0).toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-slate-400">Available Stock:</span>
                  <span className="font-mono font-bold text-slate-300">{p.stock_quantity} units</span>
                </div>
                {p.substitute_sku && (
                  <div className="text-[11px] text-amber-400/90 mb-3">
                    Configured Substitute SKU: <span className="font-mono font-bold">{p.substitute_sku}</span>
                  </div>
                )}

                {onSelectProductForOrder && (
                  <button
                    onClick={() => onSelectProductForOrder(p)}
                    className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium transition"
                  >
                    Add to Test Order
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
