"use client";

import React, { useEffect, useState, useCallback } from "react";
import { uploads, scoring } from "@/lib/api";
import type { UploadResponse, ScoringStatusResponse } from "@/types/api";
import { Upload as UploadIcon, FileSpreadsheet, Play, CheckCircle2, Clock, AlertTriangle, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

export default function UploadPage() {
  const [uploadList, setUploadList] = useState<UploadResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [scoringJobs, setScoringJobs] = useState<Record<string, ScoringStatusResponse>>({});
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);

  const fetchUploads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await uploads.list(20, 0);
      setUploadList(res.items);
    } catch (e) {
      console.error("Uploads fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUploads(); }, [fetchUploads]);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith(".xlsx")) {
      setUploadMsg("Только .xlsx файлы поддерживаются");
      return;
    }
    setUploading(true);
    setUploadMsg("");
    try {
      const res = await uploads.uploadExcel(file);
      setUploadMsg(`✓ Файл принят (ID: ${res.id}). Обработка начата...`);
      fetchUploads();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Ошибка загрузки";
      setUploadMsg(`✗ ${message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const runScoring = async (uploadId: string) => {
    try {
      const res = await scoring.run(parseInt(uploadId));
      setScoringJobs((prev) => ({ ...prev, [uploadId]: { ...res, upload_id: parseInt(uploadId), finished_at: null, error_message: null } as ScoringStatusResponse }));
      // Start polling
      const interval = setInterval(async () => {
        try {
          const status = await scoring.status(res.job_id);
          setScoringJobs((prev) => ({ ...prev, [uploadId]: status }));
          if (status.status === "done" || status.status === "failed") {
            clearInterval(interval);
          }
        } catch {
          clearInterval(interval);
        }
      }, 3000);
    } catch (e) {
      console.error("Scoring run error:", e);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "DONE": case "done": return <CheckCircle2 size={16} style={{ color: "var(--success)" }} />;
      case "PENDING": case "pending": return <Clock size={16} style={{ color: "var(--warning)" }} />;
      case "PROCESSING": case "running": return <Loader2 size={16} style={{ color: "var(--info)", animation: "spin 1s linear infinite" }} />;
      case "FAILED": case "failed": return <AlertTriangle size={16} style={{ color: "var(--error)" }} />;
      default: return <Clock size={16} style={{ color: "var(--text-muted)" }} />;
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Загрузка данных</h1>
          <p className="page-subtitle">Импорт Excel-файлов с транзакциями для анализа</p>
        </div>
      </div>

      {/* Upload Zone */}
      <motion.div className="card" style={{ padding: 48, textAlign: "center", maxWidth: 640, margin: "0 auto 32px" }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ width: 72, height: 72, borderRadius: "var(--radius-xl)", background: "var(--risk-low-bg)", color: "var(--risk-low)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
          <FileSpreadsheet size={32} />
        </div>
        <h2 style={{ marginBottom: 8 }}>Загрузка файлов</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>Выберите Excel-файл с данными о продажах или возвратах для анализа.</p>

        <div
          className={`upload-zone ${dragging ? "dragging" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById("fileInput")?.click()}
        >
          <input type="file" id="fileInput" accept=".xlsx" style={{ display: "none" }} onChange={handleInputChange} />
          <UploadIcon size={40} style={{ color: dragging ? "var(--accent)" : "var(--text-muted)", marginBottom: 16, transition: "color 0.2s" }} />
          <p style={{ fontWeight: 600, color: "var(--text-secondary)" }}>
            {uploading ? "Загрузка..." : "Нажмите или перетащите файл"}
          </p>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 8 }}>XLSX до 50MB</p>
        </div>

        {uploadMsg && (
          <div style={{ marginTop: 20, padding: 12, borderRadius: "var(--radius-md)", background: uploadMsg.startsWith("✓") ? "var(--risk-low-bg)" : "var(--risk-critical-bg)", fontSize: "0.875rem", fontWeight: 500 }}>
            {uploadMsg}
          </div>
        )}
      </motion.div>

      {/* Upload History */}
      <motion.div className="card" style={{ padding: 24 }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <h3 style={{ fontSize: "1rem", marginBottom: 20 }}>История загрузок</h3>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 48 }} />)}
          </div>
        ) : uploadList.length === 0 ? (
          <div className="empty-state"><p>Нет загрузок</p></div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Файл</th>
                <th>Статус</th>
                <th>Дата</th>
                <th style={{ textAlign: "right" }}>Скоринг</th>
              </tr>
            </thead>
            <tbody>
              {uploadList.map((u) => {
                const job = scoringJobs[u.id];
                return (
                  <tr key={u.id}>
                    <td className="mono" style={{ color: "var(--text-muted)" }}>#{u.id}</td>
                    <td style={{ fontWeight: 600 }}>{u.filename}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {statusIcon(u.status)}
                        <span style={{ fontSize: "0.8125rem" }}>{u.status}</span>
                      </div>
                    </td>
                    <td style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{new Date(u.uploaded_at).toLocaleString("ru-RU")}</td>
                    <td style={{ textAlign: "right" }}>
                      {job ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
                          {statusIcon(job.status)}
                          <span style={{ fontSize: "0.8125rem" }}>{job.status}</span>
                        </div>
                      ) : (
                        <button className="btn btn-primary btn-sm" onClick={() => runScoring(u.id)} disabled={u.status !== "DONE"}>
                          <Play size={14} /> Запустить
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </motion.div>
    </div>
  );
}
