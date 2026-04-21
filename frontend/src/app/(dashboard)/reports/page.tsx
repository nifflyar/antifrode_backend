"use client";

import React, { useState } from "react";
import { reports } from "@/lib/api";
import { FileSpreadsheet, FileText, Download } from "lucide-react";
import { motion } from "framer-motion";

export default function ReportsPage() {
  const [passengerIdInput, setPassengerIdInput] = useState("");
  const [downloading, setDownloading] = useState<string | null>(null);

  const downloadFile = async (type: string, fetcher: () => Promise<Response>, filename: string) => {
    setDownloading(type);
    try {
      const res = await fetcher();
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download error:", e);
    } finally {
      setDownloading(null);
    }
  };

  const reportCards = [
    {
      id: "excel",
      icon: FileSpreadsheet,
      color: "#10b981",
      bg: "#ecfdf5",
      title: "Excel Отчёт",
      description: "Полный список риск-пассажиров с признаками и подозрительными операциями.",
      buttonText: "Скачать .xlsx",
      buttonColor: "#10b981",
      onClick: () => downloadFile("excel", () => reports.suspiciousExcel(), `suspicious_ops_${new Date().toISOString().slice(0, 10)}.xlsx`),
    },
    {
      id: "concentration",
      icon: FileSpreadsheet,
      color: "#3b82f6",
      bg: "#eff6ff",
      title: "Концентрация рисков",
      description: "Сводный отчёт по концентрации рисков: каналы, терминалы, кассы, агрегаторы.",
      buttonText: "Скачать .xlsx",
      buttonColor: "#3b82f6",
      onClick: () => downloadFile("concentration", () => reports.concentrationExcel(), `risk_concentration_${new Date().toISOString().slice(0, 10)}.xlsx`),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Экспорт и отчётность</h1>
          <p className="page-subtitle">Генерация сводных отчётов для руководства</p>
        </div>
      </div>

      <div className="grid-3">
        {reportCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.id}
              className="card card-interactive"
              style={{ padding: 24 }}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <Icon size={32} style={{ color: card.color, marginBottom: 16 }} />
              <h3 style={{ marginBottom: 8 }}>{card.title}</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 20, lineHeight: 1.5 }}>{card.description}</p>
              <button
                className="btn btn-sm"
                style={{ width: "100%", background: `${card.color}14`, color: card.color, border: `1px solid ${card.color}30` }}
                onClick={card.onClick}
                disabled={downloading === card.id}
              >
                <Download size={14} />
                {downloading === card.id ? "Загрузка..." : card.buttonText}
              </button>
            </motion.div>
          );
        })}

        {/* PDF Report */}
        <motion.div
          className="card card-interactive"
          style={{ padding: 24 }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <FileText size={32} style={{ color: "#ef4444", marginBottom: 16 }} />
          <h3 style={{ marginBottom: 8 }}>PDF Досье</h3>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 16, lineHeight: 1.5 }}>
            Детальная карточка-досье на конкретного пассажира.
          </p>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              className="input"
              placeholder="ID пассажира"
              value={passengerIdInput}
              onChange={(e) => setPassengerIdInput(e.target.value)}
              style={{ flex: 1 }}
            />
          </div>
          <button
            className="btn btn-sm"
            style={{ width: "100%", background: "#fef2f2", color: "#ef4444", border: "1px solid #fecaca" }}
            onClick={() => {
              if (!passengerIdInput) return;
              downloadFile("pdf", () => reports.passengerPdf(parseInt(passengerIdInput)), `passenger_${passengerIdInput}_dossier.pdf`);
            }}
            disabled={downloading === "pdf" || !passengerIdInput}
          >
            <Download size={14} />
            {downloading === "pdf" ? "Генерация..." : "Сформировать PDF"}
          </button>
        </motion.div>
      </div>
    </div>
  );
}
