"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { passengers } from "@/lib/api";
import type { PassengerListItem, RiskBand } from "@/types/api";
import RiskBadge from "@/components/RiskBadge";
import { Users, Search, ChevronLeft, ChevronRight, Eye } from "lucide-react";
import { motion } from "framer-motion";

export default function PassengersPage() {
  const router = useRouter();
  const [items, setItems] = useState<PassengerListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [riskFilter, setRiskFilter] = useState<RiskBand | "">("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const limit = 15;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await passengers.list({
        risk_band: riskFilter || undefined,
        search: search || undefined,
        limit,
        offset: (page - 1) * limit,
      });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, riskFilter, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const offset = (page - 1) * limit;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Контроль пассажиров</h1>
          <p className="page-subtitle">Список пассажиров с оценкой рисков</p>
        </div>
      </div>

      <motion.div className="card" style={{ padding: 24 }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        {/* Filters */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 24, justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Users size={20} style={{ color: "var(--accent)" }} />
            <h2 style={{ fontSize: "1.125rem" }}>Список пассажиров</h2>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <select className="select" value={riskFilter} onChange={(e) => { setRiskFilter(e.target.value as RiskBand | ""); setPage(1); }}>
              <option value="">Все риски</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <div style={{ position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
              <input
                type="text"
                className="input"
                style={{ paddingLeft: 36, width: 260 }}
                placeholder="Поиск по ФИО или ИИН..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: "auto", minHeight: 400 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Final Score</th>
                <th>Risk Band</th>
                <th>ФИО</th>
                <th>Fake Score</th>
                <th>Дата</th>
                <th style={{ textAlign: "right" }}>Действия</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    {[...Array(7)].map((__, j) => (
                      <td key={j}><div className="skeleton" style={{ width: j === 3 ? 140 : 60, height: 16 }} /></td>
                    ))}
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <div className="empty-state-icon"><Users size={28} /></div>
                      <p>Ничего не найдено</p>
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((p) => (
                  <tr key={p.id} className="clickable" onClick={() => router.push(`/passengers/${p.id}`)}>
                    <td><span className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>#{p.id}</span></td>
                    <td><span style={{ fontWeight: 800, fontSize: "1rem" }}>{p.final_score.toFixed(1)}</span></td>
                    <td><RiskBadge band={p.risk_band} /></td>
                    <td style={{ fontWeight: 600 }}>{p.fio_clean}</td>
                    <td style={{ color: "var(--text-muted)" }}>{p.fake_fio_score.toFixed(2)}</td>
                    <td style={{ whiteSpace: "nowrap", color: "var(--text-secondary)" }}>{new Date(p.last_seen_at).toLocaleDateString("ru-RU")}</td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn btn-ghost btn-icon" onClick={(e) => { e.stopPropagation(); router.push(`/passengers/${p.id}`); }}>
                        <Eye size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="pagination">
          <span className="pagination-info">
            Показано {total > 0 ? offset + 1 : 0}-{Math.min(offset + limit, total)} из {total}
          </span>
          <div className="pagination-controls">
            <button className="pagination-btn" disabled={page === 1} onClick={() => setPage(page - 1)}>
              <ChevronLeft size={16} />
            </button>
            <span className="pagination-current">{page}</span>
            <button className="pagination-btn" disabled={offset + limit >= total} onClick={() => setPage(page + 1)}>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
