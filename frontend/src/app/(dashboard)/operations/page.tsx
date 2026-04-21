"use client";

import React, { useEffect, useState, useCallback } from "react";
import { operations } from "@/lib/api";
import type { SuspiciousOperation } from "@/types/api";
import RiskBadge from "@/components/RiskBadge";
import { ArrowLeftRight, ChevronLeft, ChevronRight } from "lucide-react";
import { motion } from "framer-motion";

export default function OperationsPage() {
  const [items, setItems] = useState<SuspiciousOperation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await operations.suspicious({ limit, offset: (page - 1) * limit });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const offset = (page - 1) * limit;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Операции высокого риска</h1>
          <p className="page-subtitle">Подозрительные транзакции, выявленные системой</p>
        </div>
      </div>

      <motion.div className="card" style={{ padding: 24 }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <ArrowLeftRight size={20} style={{ color: "var(--accent)" }} />
          <h2 style={{ fontSize: "1.125rem" }}>Журнал операций</h2>
        </div>

        <div style={{ overflowX: "auto", minHeight: 400 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Дата/время</th>
                <th>Пассажир ID</th>
                <th>Поезд</th>
                <th>Канал</th>
                <th>Терминал</th>
                <th>Касса</th>
                <th>Тип</th>
                <th>Риск</th>
                <th style={{ textAlign: "right" }}>Сумма</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(8)].map((_, i) => (
                  <tr key={i}>
                    {[...Array(9)].map((__, j) => (
                      <td key={j}><div className="skeleton" style={{ width: j === 0 ? 120 : 60, height: 16 }} /></td>
                    ))}
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="empty-state">
                      <div className="empty-state-icon"><ArrowLeftRight size={28} /></div>
                      <p>Нет данных</p>
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((op) => (
                  <tr key={op.id}>
                    <td style={{ whiteSpace: "nowrap", color: "var(--text-secondary)", fontSize: "0.8125rem" }}>{new Date(op.op_datetime).toLocaleString("ru-RU")}</td>
                    <td><span className="mono" style={{ fontWeight: 700, color: "var(--accent)" }}>{op.passenger_id}</span></td>
                    <td className="mono" style={{ fontSize: "0.8125rem" }}>{op.train_no || "—"}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>{op.channel || "—"}</td>
                    <td style={{ fontSize: "0.8125rem" }}>{op.terminal || "—"}</td>
                    <td style={{ fontSize: "0.8125rem" }}>{op.cashdesk || "—"}</td>
                    <td><span style={{ fontWeight: 800, color: op.op_type === "RETURN" ? "var(--risk-critical)" : "var(--risk-low)" }}>{op.op_type}</span></td>
                    <td><RiskBadge band={op.risk_band} /></td>
                    <td className="mono" style={{ textAlign: "right", fontWeight: 600 }}>{op.amount.toLocaleString()} ₸</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="pagination">
          <span className="pagination-info">Показано {total > 0 ? offset + 1 : 0}-{Math.min(offset + limit, total)} из {total}</span>
          <div className="pagination-controls">
            <button className="pagination-btn" disabled={page === 1} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button>
            <span className="pagination-current">{page}</span>
            <button className="pagination-btn" disabled={offset + limit >= total} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
