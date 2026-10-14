import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Layers
} from "lucide-react";
import { fetchDemoCatalogueVersions, isDemoSession } from "../services/demoService";
import {
  uploadCataloguePreview,
  confirmCatalogueImport,
  activateCatalogue,
  fetchCatalogueVersions,
  getStoredUser
} from "../services/api";
import type { CataloguePreview, CatalogueVersion } from "../types";

interface OwnerCatalogueViewProps {
  isDemo?: boolean;
}

export const OwnerCatalogueView: React.FC<OwnerCatalogueViewProps> = ({ isDemo: propIsDemo }) => {
  const user = getStoredUser();
  const isDemo = Boolean(propIsDemo ?? user?.is_demo ?? isDemoSession());
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [isActivating, setIsActivating] = useState<string | null>(null);
  const [preview, setPreview] = useState<CataloguePreview | null>(null);
  const [versions, setVersions] = useState<CatalogueVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form fields for import confirmation
  const [customName, setCustomName] = useState<string>("");
  const [customVersion, setCustomVersion] = useState<string>("");

  useEffect(() => {
    loadVersions();
  }, [isDemo]);

  const loadVersions = async () => {
    try {
      const data = isDemo ? await fetchDemoCatalogueVersions() : await fetchCatalogueVersions();
      setVersions(data);
    } catch (err: any) {
      console.error("Error loading versions:", err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setPreview(null);
      setError(null);
      setSuccessMsg(null);
    }
  };

  const handleUploadAndPreview = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const prev = await uploadCataloguePreview(file);
      setPreview(prev);
      setCustomName(`Catalogue Import: ${file.name}`);
      setCustomVersion(prev.inferred_version || "v1.1.0");
    } catch (err: any) {
      setError(err.message || "Failed to parse and validate catalogue.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!preview || !file) return;
    if (isDemo) {
      setSuccessMsg(`[Demo Sandbox Mode] Simulated import of '${customVersion || "v1.1.0"}' into demo session memory. Production database is untouched.`);
      setPreview(null);
      setFile(null);
      return;
    }
    setIsImporting(true);
    setError(null);

    try {
      const created = await confirmCatalogueImport({
        name: customName || `Catalogue Import: ${file.name}`,
        version: customVersion || "v1.1.0",
        filename: file.name,
        records: (preview.all_valid_records && preview.all_valid_records.length > 0) ? preview.all_valid_records : preview.preview_records,
        valid_count: preview.valid_count,
        invalid_count: preview.invalid_count,
        validation_report: { errors: preview.errors, warnings: preview.warnings }
      });
      setSuccessMsg(`Catalogue ${created.version} successfully imported into database as READY FOR ACTIVATION!`);
      setPreview(null);
      setFile(null);
      await loadVersions();
    } catch (err: any) {
      setError(err.message || "Import failed.");
    } finally {
      setIsImporting(false);
    }
  };

  const handleActivate = async (catId: string, version: string) => {
    if (isDemo) {
      setVersions((prev) => prev.map((v) => ({ ...v, is_active: v.id === catId })));
      setSuccessMsg(`[Demo Sandbox Mode] Version ${version} activated in demo view. Production database is untouched.`);
      return;
    }
    setIsActivating(catId);
    setError(null);
    setSuccessMsg(null);

    try {
      await activateCatalogue(catId);
      setSuccessMsg(`Catalogue version ${version} is now the active official store truth!`);
      await loadVersions();
    } catch (err: any) {
      setError(err.message || "Activation failed.");
    } finally {
      setIsActivating(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-8 animate-fade-in">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <Layers className="h-6 w-6 text-indigo-600" />
          <span>Official Catalogue Management & Versioning</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Upload official CSV or JSON files. Review live validation errors, import records into the persistent database, and activate versions atomically.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-600">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between font-medium">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-600">✕</button>
        </div>
      )}

      {/* Step 1: Upload Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <span className="h-6 w-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">
              1
            </span>
            <h3 className="text-sm font-bold text-slate-900">Upload & Validate Catalogue File</h3>
          </div>
          <span className="text-xs text-slate-400">Supported: .csv, .tsv, .json, .xls, .xlsx (max 35MB)</span>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-4">
          <input
            type="file"
            id="catalogue-file-input"
            accept=".csv,.tsv,.json,.xls,.xlsx"
            onChange={handleFileChange}
            className="w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
          />

          <button
            onClick={handleUploadAndPreview}
            disabled={!file || isUploading}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-sm transition-all disabled:opacity-50 cursor-pointer shrink-0"
          >
            {isUploading ? "Validating Records..." : "Upload & Preview Data"}
          </button>
        </div>
      </div>

      {/* Step 2: Preview & Validation Report */}
      {preview && (
        <div className="bg-white rounded-2xl p-6 border border-indigo-200 shadow-md space-y-5 animate-fade-in">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <span className="h-6 w-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">
                2
              </span>
              <h3 className="text-sm font-bold text-slate-900">Validation Report: {preview.filename}</h3>
            </div>
            <div className="flex items-center space-x-3 text-xs font-semibold">
              <span className="text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                {preview.valid_count} Valid Records
              </span>
              {preview.invalid_count > 0 && (
                <span className="text-rose-700 bg-rose-50 px-2.5 py-1 rounded-lg border border-rose-200">
                  {preview.invalid_count} Invalid Records
                </span>
              )}
            </div>
          </div>

          {/* Validation Errors if any */}
          {preview.errors.length > 0 && (
            <div className="p-4 rounded-xl bg-rose-50/80 border border-rose-200 space-y-2">
              <span className="text-xs font-bold text-rose-800 flex items-center space-x-1.5">
                <AlertTriangle className="h-4 w-4 text-rose-600" />
                <span>Detected Row Validation Errors ({preview.errors.length}):</span>
              </span>
              <div className="max-h-40 overflow-y-auto space-y-1 text-[11px] text-rose-700">
                {preview.errors.map((err, idx) => (
                  <div key={idx} className="font-mono bg-white/70 p-1.5 rounded border border-rose-200">
                    Row {err.row} [{err.product_id}]: {err.issue}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Record Preview Table */}
          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
              Parsed Preview Records (First 10 of {preview.valid_count}):
            </span>
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold">
                  <tr>
                    <th className="py-2 px-3">Product ID</th>
                    <th className="py-2 px-3">Title</th>
                    <th className="py-2 px-3">Category</th>
                    <th className="py-2 px-3">Price (₹)</th>
                    <th className="py-2 px-3">Stock Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                  {preview.preview_records.slice(0, 10).map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50/80">
                      <td className="py-2 px-3 font-mono font-semibold text-indigo-700">{r.product_id}</td>
                      <td className="py-2 px-3 truncate max-w-xs">{r.title}</td>
                      <td className="py-2 px-3">{r.category}</td>
                      <td className="py-2 px-3 font-semibold">₹{Number(r.price).toLocaleString("en-IN")}</td>
                      <td className="py-2 px-3">{r.stock_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Import Confirmation Form */}
          <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="Dataset Name..."
                className="w-full sm:w-64 px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              />
              <input
                type="text"
                value={customVersion}
                onChange={(e) => setCustomVersion(e.target.value)}
                placeholder="Version (e.g. v1.1.0)"
                className="w-full sm:w-32 px-3 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white font-mono"
              />
            </div>

            <button
              onClick={handleConfirmImport}
              disabled={isImporting || preview.valid_count === 0}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shadow-sm transition-all disabled:opacity-50 cursor-pointer shrink-0"
            >
              {isImporting ? "Saving to Database..." : "Confirm Import to Database"}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Versions Table */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <span className="h-6 w-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">
              3
            </span>
            <h3 className="text-sm font-bold text-slate-900">Catalogue Versions & Safe Activation</h3>
          </div>
          <span className="text-xs text-slate-400">Atomic Switching • Zero Downtime</span>
        </div>

        {versions.length === 0 ? (
          <p className="text-xs text-slate-400 py-6 text-center">No catalogue versions loaded yet.</p>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Version</th>
                  <th className="py-2.5 px-3">Name</th>
                  <th className="py-2.5 px-3">Filename</th>
                  <th className="py-2.5 px-3">Valid Items</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                {versions.map((v) => (
                  <tr key={v.id} className={v.is_active ? "bg-indigo-50/40" : "hover:bg-slate-50/80"}>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{v.version}</td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{v.name}</td>
                    <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px]">{v.filename}</td>
                    <td className="py-2.5 px-3">{v.valid_count}</td>
                    <td className="py-2.5 px-3">
                      {v.is_active ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>ACTIVE</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[11px] bg-slate-100 text-slate-600 font-semibold">
                          {v.status}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                      {new Date(v.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {v.is_active ? (
                        <span className="text-[11px] font-bold text-emerald-600">Currently Live</span>
                      ) : (
                        <button
                          onClick={() => handleActivate(v.id, v.version)}
                          disabled={isActivating === v.id}
                          className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-[11px] transition-colors shadow-xs cursor-pointer disabled:opacity-50"
                        >
                          {isActivating === v.id ? "Activating..." : "Activate Version"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
