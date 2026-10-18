"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  X,
  ArrowLeft,
  Sparkles,
  Layers,
  Copy,
  ExternalLink,
} from "lucide-react";
import { FileUploadResult, BulkUploadResponse } from "@/types";
import { getApiBaseUrl } from "@/lib/api";

interface SelectedFileItem {
  file: File;
  id: string;
  status: "pending" | "uploading" | "success" | "duplicate" | "error";
  error?: string;
  resumeId?: string;
  existingResumeId?: string;
}

export default function ResumeUploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<SelectedFileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);

  const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB

  const handleFilesAdded = (incomingFiles: FileList | null) => {
    if (!incomingFiles) return;

    const newItems: SelectedFileItem[] = [];
    for (let i = 0; i < incomingFiles.length; i++) {
      const file = incomingFiles[i];
      const ext = file.name.split(".").pop()?.toLowerCase();
      const isValidExt = ext === "pdf" || ext === "docx";

      if (!isValidExt) {
        newItems.push({
          file,
          id: `${file.name}-${Date.now()}-${i}`,
          status: "error",
          error: "Unsupported file type. Only PDF and DOCX files are allowed.",
        });
      } else if (file.size > MAX_FILE_SIZE) {
        newItems.push({
          file,
          id: `${file.name}-${Date.now()}-${i}`,
          status: "error",
          error: "File exceeds 15MB limit.",
        });
      } else if (file.size === 0) {
        newItems.push({
          file,
          id: `${file.name}-${Date.now()}-${i}`,
          status: "error",
          error: "Empty file (0 bytes).",
        });
      } else {
        newItems.push({
          file,
          id: `${file.name}-${Date.now()}-${i}`,
          status: "pending",
        });
      }
    }

    setSelectedFiles((prev) => [...prev, ...newItems]);
    setUploadComplete(false);
  };

  const removeFile = (id: string) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== id));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      handleFilesAdded(e.dataTransfer.files);
    }
  };

  const handleUploadAll = async () => {
    const validPending = selectedFiles.filter((f) => f.status === "pending");
    if (validPending.length === 0) return;

    setUploading(true);

    // If single file, use single upload endpoint; if multiple, use bulk upload endpoint
    const token = localStorage.getItem("hirelens_access_token");
    const baseUrl = getApiBaseUrl();

    try {
      if (validPending.length === 1) {
        const item = validPending[0];
        const formData = new FormData();
        formData.append("file", item.file);

        setSelectedFiles((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, status: "uploading" } : f))
        );

        const res = await fetch(`${baseUrl}/resumes/upload`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });

        const data: FileUploadResult = await res.json();
        if (data.status === "SUCCESS") {
          setSelectedFiles((prev) =>
            prev.map((f) =>
              f.id === item.id ? { ...f, status: "success", resumeId: data.resume_id } : f
            )
          );
        } else if (data.status === "DUPLICATE") {
          setSelectedFiles((prev) =>
            prev.map((f) =>
              f.id === item.id
                ? {
                    ...f,
                    status: "duplicate",
                    existingResumeId: data.existing_resume_id,
                    error: data.error,
                  }
                : f
            )
          );
        } else {
          setSelectedFiles((prev) =>
            prev.map((f) =>
              f.id === item.id ? { ...f, status: "error", error: data.error || "Upload failed" } : f
            )
          );
        }
      } else {
        // Bulk Upload
        const formData = new FormData();
        validPending.forEach((item) => {
          formData.append("files", item.file);
        });

        setSelectedFiles((prev) =>
          prev.map((f) => (f.status === "pending" ? { ...f, status: "uploading" } : f))
        );

        const res = await fetch(`${baseUrl}/resumes/bulk-upload`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });

        const bulkData: BulkUploadResponse = await res.json();

        setSelectedFiles((prev) =>
          prev.map((f) => {
            const match = bulkData.results.find((r) => r.filename === f.file.name);
            if (!match) return f;
            if (match.status === "SUCCESS") {
              return { ...f, status: "success", resumeId: match.resume_id };
            } else if (match.status === "DUPLICATE") {
              return {
                ...f,
                status: "duplicate",
                existingResumeId: match.existing_resume_id,
                error: match.error,
              };
            } else {
              return { ...f, status: "error", error: match.error || "Upload rejected" };
            }
          })
        );
      }
      setUploadComplete(true);
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const successCount = selectedFiles.filter((f) => f.status === "success").length;
  const duplicateCount = selectedFiles.filter((f) => f.status === "duplicate").length;
  const errorCount = selectedFiles.filter((f) => f.status === "error").length;
  const pendingCount = selectedFiles.filter((f) => f.status === "pending").length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link
            href="/resumes"
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Upload Resumes</h1>
            <p className="text-sm text-slate-500">
              Select one or multiple resumes to extract facts and begin recruiter review.
            </p>
          </div>
        </div>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-blue-500 bg-blue-50/60"
            : "border-slate-300 hover:border-slate-400 bg-white"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => handleFilesAdded(e.target.files)}
        />
        <div className="w-14 h-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4">
          <UploadCloud className="w-7 h-7" />
        </div>
        <h3 className="text-base font-semibold text-slate-900">
          Click to browse or drag and drop resumes
        </h3>
        <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
          Supports authentic <span className="font-semibold text-slate-700">PDF</span> and{" "}
          <span className="font-semibold text-slate-700">DOCX</span> files up to 15MB each.
        </p>
        <div className="mt-3 inline-flex items-center px-2.5 py-1 rounded bg-slate-100 text-xs font-medium text-slate-600">
          <Sparkles className="w-3.5 h-3.5 mr-1 text-blue-600" />
          Automated text extraction & structured facts identification
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <div className="flex items-center space-x-3 text-sm">
              <span className="font-semibold text-slate-800">
                Selected Files ({selectedFiles.length})
              </span>
              {uploadComplete && (
                <div className="flex items-center space-x-2 text-xs">
                  {successCount > 0 && (
                    <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      {successCount} uploaded
                    </span>
                  )}
                  {duplicateCount > 0 && (
                    <span className="text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      {duplicateCount} duplicates
                    </span>
                  )}
                  {errorCount > 0 && (
                    <span className="text-rose-700 font-semibold bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                      {errorCount} rejected
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="space-x-2">
              <button
                onClick={() => setSelectedFiles([])}
                className="text-xs text-slate-500 hover:text-slate-800 font-medium px-2 py-1 rounded hover:bg-slate-100"
              >
                Clear All
              </button>
            </div>
          </div>

          <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            {selectedFiles.map((item) => (
              <div key={item.id} className="p-4 flex items-center justify-between text-sm">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="p-2 rounded bg-slate-100 text-slate-600 shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-slate-800 truncate">{item.file.name}</p>
                    <p className="text-xs text-slate-400">
                      {(item.file.size / 1024).toFixed(1)} KB
                    </p>
                    {item.error && (
                      <p className="text-xs text-rose-600 font-medium mt-0.5">{item.error}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  {item.status === "uploading" && (
                    <div className="flex items-center space-x-1.5 text-xs text-blue-600 font-medium">
                      <div className="w-3.5 h-3.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                      <span>Uploading...</span>
                    </div>
                  )}

                  {item.status === "success" && (
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Uploaded
                      </span>
                      {item.resumeId && (
                        <Link
                          href={`/resumes/${item.resumeId}/review`}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center"
                        >
                          Review <ExternalLink className="w-3 h-3 ml-1" />
                        </Link>
                      )}
                    </div>
                  )}

                  {item.status === "duplicate" && (
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        <Copy className="w-3 h-3 mr-1" />
                        Duplicate
                      </span>
                      {item.existingResumeId && (
                        <Link
                          href={`/resumes/${item.existingResumeId}`}
                          className="text-xs font-medium text-amber-800 hover:underline flex items-center"
                        >
                          View Existing <ExternalLink className="w-3 h-3 ml-1" />
                        </Link>
                      )}
                    </div>
                  )}

                  {item.status === "error" && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                      <AlertCircle className="w-3 h-3 mr-1" />
                      Rejected
                    </span>
                  )}

                  {!uploading && (
                    <button
                      onClick={() => removeFile(item.id)}
                      className="p-1 text-slate-400 hover:text-slate-600 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Action Footer */}
          <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              {pendingCount > 0
                ? `${pendingCount} file(s) ready to upload`
                : "All files have been processed."}
            </span>

            <div className="flex items-center space-x-3">
              {uploadComplete && (
                <Link
                  href="/resumes"
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Return to Directory
                </Link>
              )}

              {pendingCount > 0 && (
                <button
                  onClick={handleUploadAll}
                  disabled={uploading}
                  className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-sm transition-colors flex items-center"
                >
                  {uploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      Processing Upload...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4 mr-2" />
                      Upload {pendingCount} Resume{pendingCount > 1 ? "s" : ""}
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
