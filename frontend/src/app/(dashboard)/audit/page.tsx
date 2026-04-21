"use client";

import React, { useEffect, useState, useCallback } from "react";
import { audit } from "@/lib/api";
import type { AuditLogItem } from "@/types/api";
import { useAuth } from "@/lib/auth-context";
import { ScrollText, ChevronLeft, ChevronRight, Shield, Filter } from "lucide-react";
import { motion } from "framer-motion";

export default function AuditPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const fetchData = useCallback(async () => {
    if (!user?.is_admin) { setLoading(false); return; }
    setLoading(true);
    try {
      const res = await audit.list({
        action: actionFilter || undefined,
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
  }, [page, actionFilter, user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (!user?.is_admin) {
    return (
      <div className="empty-state" style={{ minHeight: "60vh" }}>
        <div className="empty-state-icon"><Shield size={28} /></div>
        <p>Эта страница доступна только администраторам</p>
      </div>
    );
  }

  const offset = (page - 1) * limit;

  const actionColor = (action: string) => {
    if (action.includes("LOGIN")) return "var(--info)";
    if (action.includes("LOGOUT")) return "var(--text-muted)";
    if (action.includes("REGISTER")) return "var(--success)";
    if (action.includes("DELETE")) return "var(--error)";
    if (action.includes("UPLOAD")) return "var(--warning)";
    return "var(--accent)";
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Аудит логи</h1>
          <p className="page-subtitle">Детальное логирование всех действий пользователей</p>
        </div>
      </div>

      <motion.div className="card" style={{ padding: 24 }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        {/* Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <Filter size={16} style={{ color: "var(--text-muted)" }} />
          <select className="select" value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}>
            <option value="">Все действия</option>
            <option value="USER_LOGIN">Вход</option>
            <option value="USER_LOGOUT">Выход</option>
            <option value="USER_REGISTERED">Регистрация</option>
            <option value="FILE_UPLOADED">Загрузка файла</option>
            <option value="SCORING_STARTED">Скоринг</option>
          </select>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Время</th>
                <th>Действие</th>
                <th>Сущность</th>
                <th>Entity ID</th>
                <th>User ID</th>
                <th>Мета</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(6)].map((_, i) => (
                  <tr key={i}>{[...Array(6)].map((__, j) => <td key={j}><div className="skeleton" style={{ width: 80, height: 16 }} /></td>)}</tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className="empty-state">
                      <div className="empty-state-icon"><ScrollText size={28} /></div>
                      <p>Нет записей</p>
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: "nowrap", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                      {new Date(log.created_at).toLocaleString("ru-RU")}
                    </td>
                    <td>
                      <span className="badge" style={{ background: `${actionColor(log.action)}14`, color: actionColor(log.action) }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{log.entity_type || "—"}</td>
                    <td className="mono" style={{ fontSize: "0.8125rem" }}>{log.entity_id || "—"}</td>
                    <td className="mono" style={{ fontSize: "0.8125rem", color: "var(--accent)" }}>{log.user_id || "—"}</td>
                    <td style={{ fontSize: "0.75rem", color: "var(--text-muted)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {log.meta ? JSON.stringify(log.meta) : "—"}
                    </td>
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
