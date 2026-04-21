"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { passengers as passApi } from "@/lib/api";
import type { PassengerProfile, PassengerTransaction, RiskBand } from "@/types/api";
import RiskBadge from "@/components/RiskBadge";
import { useAuth } from "@/lib/auth-context";
import { ArrowLeft, AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { motion } from "framer-motion";

export default function PassengerProfilePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [profile, setProfile] = useState<PassengerProfile | null>(null);
  const [txs, setTxs] = useState<PassengerTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOverride, setShowOverride] = useState(false);
  const [overrideBand, setOverrideBand] = useState<RiskBand>("low");
  const [overrideReason, setOverrideReason] = useState("");

  useEffect(() => {
    if (!id) return;
    const fetch = async () => {
      setLoading(true);
      try {
        const [p, t] = await Promise.all([
          passApi.getById(id),
          passApi.transactions(id),
        ]);
        setProfile(p);
        setTxs(t);
      } catch (e) {
        console.error("Profile fetch error:", e);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [id]);

  const handleOverride = async () => {
    if (!id) return;
    try {
      await passApi.overrideRisk(id, { new_risk_band: overrideBand, reason: overrideReason });
      setShowOverride(false);
      // Refresh profile
      const p = await passApi.getById(id);
      setProfile(p);
    } catch (e) {
      console.error("Override error:", e);
    }
  };

  if (loading) {
    return (
      <div>
        <div className="skeleton" style={{ width: 200, height: 32, marginBottom: 24 }} />
        <div className="card" style={{ padding: 32 }}>
          <div className="skeleton" style={{ width: 300, height: 24, marginBottom: 16 }} />
          <div className="skeleton" style={{ width: "100%", height: 200 }} />
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="empty-state" style={{ minHeight: "60vh" }}>
        <div className="empty-state-icon"><AlertTriangle size={28} /></div>
        <p>Пассажир не найден</p>
        <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={() => router.push("/passengers")}>
          ← Назад к списку
        </button>
      </div>
    );
  }

  const score = profile.score;
  const features = profile.features;

  return (
    <div>
      <button className="btn btn-ghost" style={{ marginBottom: 16 }} onClick={() => router.push("/passengers")}>
        <ArrowLeft size={16} /> Назад к списку
      </button>

      <motion.div className="card" style={{ padding: 32 }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32, paddingBottom: 24, borderBottom: "1px solid var(--border)" }}>
          <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 800 }}>Пассажир: #{profile.id}</h1>
            <p style={{ color: "var(--text-secondary)", fontSize: "1.125rem", marginTop: 4 }}>ФИО: {profile.fio_clean}</p>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", marginTop: 4 }}>
              Fake FIO Score: <span className="mono">{profile.fake_fio_score.toFixed(3)}</span> · Первая активность: {new Date(profile.first_seen_at).toLocaleDateString("ru-RU")}
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {score && (
              <div style={{
                padding: "12px 24px",
                borderRadius: "var(--radius-lg)",
                background: score.risk_band === "critical" ? "var(--risk-critical-bg)" : score.risk_band === "high" ? "var(--risk-high-bg)" : score.risk_band === "medium" ? "var(--risk-medium-bg)" : "var(--risk-low-bg)",
                display: "flex", alignItems: "center", gap: 12,
              }}>
                <span style={{ fontWeight: 800, fontSize: "1.25rem" }}>
                  {score.final_score.toFixed(0)}/100
                </span>
                <RiskBadge band={score.risk_band} />
              </div>
            )}
            {user?.is_admin && (
              <button className="btn btn-secondary btn-sm" onClick={() => setShowOverride(!showOverride)}>
                <ShieldAlert size={14} /> Override
              </button>
            )}
          </div>
        </div>

        {/* Override Modal */}
        {showOverride && (
          <div style={{ marginBottom: 24, padding: 20, background: "var(--bg-secondary)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
            <h3 style={{ marginBottom: 12, fontSize: "0.9375rem" }}>Переопределить уровень риска</h3>
            <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <div>
                <label className="form-label">Новый уровень</label>
                <select className="select" value={overrideBand} onChange={(e) => setOverrideBand(e.target.value as RiskBand)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label className="form-label">Причина</label>
                <input className="input" placeholder="Укажите причину..." value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)} />
              </div>
              <button className="btn btn-primary btn-sm" onClick={handleOverride}>Применить</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowOverride(false)}>Отмена</button>
            </div>
          </div>
        )}

        {/* Content Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
          {/* Left: Score details + Features */}
          <div>
            {/* Risk Reasons */}
            {score && score.top_reasons.length > 0 && (
              <div style={{ marginBottom: 24, padding: 20, background: "var(--accent-light)", borderRadius: "var(--radius-md)", border: "1px solid #c7d2fe" }}>
                <h4 style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--accent)", marginBottom: 12 }}>
                  Причины риска
                </h4>
                <ul style={{ listStyle: "none", padding: 0 }}>
                  {score.top_reasons.map((r, i) => (
                    <li key={i} style={{ padding: "6px 0", fontSize: "0.875rem", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
                      <AlertTriangle size={14} style={{ color: "var(--accent)" }} /> {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Features */}
            {features && (
              <div style={{ padding: 20 }}>
                <h4 style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 12 }}>
                  Статистика
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {[
                    ["Всего билетов", features.total_tickets],
                    ["Возвратов", features.refund_cnt],
                    ["Доля возвратов", `${(features.refund_share * 100).toFixed(1)}%`],
                    ["Ночных билетов", features.night_tickets],
                    ["Доля ночных", `${(features.night_share * 100).toFixed(1)}%`],
                    ["Max за месяц", features.max_tickets_month],
                    ["Max на один день", features.max_tickets_same_depday],
                    ["Refund close ratio", features.refund_close_ratio.toFixed(3)],
                    ["Tickets/train peak", features.tickets_per_train_peak.toFixed(2)],
                  ].map(([label, val]) => (
                    <div key={String(label)} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                      <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{label}</span>
                      <span className="mono" style={{ fontWeight: 700, fontSize: "0.875rem" }}>{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Score breakdown */}
            {score && (
              <div style={{ padding: 20, marginTop: 12 }}>
                <h4 style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 12 }}>
                  Скоринг
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {[
                    ["Rule Score", score.rule_score.toFixed(2)],
                    ["ML Score", score.ml_score.toFixed(2)],
                    ["Final Score", score.final_score.toFixed(2)],
                    ["Manual Override", score.is_manual ? "Да" : "Нет"],
                  ].map(([label, val]) => (
                    <div key={String(label)} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                      <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{label}</span>
                      <span className="mono" style={{ fontWeight: 700, fontSize: "0.875rem" }}>{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Seat blocking + Transactions */}
          <div>
            {/* Seat blocking */}
            {score && (
              <div style={{
                padding: 20,
                borderRadius: "var(--radius-md)",
                marginBottom: 24,
                background: score.seat_blocking_flag ? "var(--risk-critical-bg)" : "var(--risk-low-bg)",
                border: `1px solid ${score.seat_blocking_flag ? "#fecdd3" : "#bbf7d0"}`,
                display: "flex", alignItems: "center", gap: 16,
              }}>
                {score.seat_blocking_flag ? <AlertTriangle size={28} style={{ color: "var(--risk-critical)" }} /> : <CheckCircle2 size={28} style={{ color: "var(--risk-low)" }} />}
                <div>
                  <p style={{ fontWeight: 700, fontSize: "0.9375rem" }}>
                    {score.seat_blocking_flag ? "Обнаружен Seat-blocking" : "Аномалий не выявлено"}
                  </p>
                  <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: 2 }}>
                    {score.seat_blocking_flag ? "Зафиксировано удержание мест перед отправлением" : "Признаков удержания мест не обнаружено"}
                  </p>
                </div>
              </div>
            )}

            {/* Transactions */}
            <div>
              <h4 style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 12 }}>
                История транзакций ({txs.length})
              </h4>
              <div style={{ borderRadius: "var(--radius-md)", border: "1px solid var(--border)", overflow: "hidden" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Тип</th>
                      <th>Поезд</th>
                      <th>Канал</th>
                      <th style={{ textAlign: "right" }}>Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    {txs.length === 0 ? (
                      <tr><td colSpan={5} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>История пуста</td></tr>
                    ) : (
                      txs.slice(0, 20).map((tx) => (
                        <tr key={tx.id}>
                          <td style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{new Date(tx.op_datetime).toLocaleDateString("ru-RU")}</td>
                          <td>
                            <span style={{ fontWeight: 700, color: tx.op_type === "RETURN" ? "var(--risk-critical)" : "var(--risk-low)" }}>
                              {tx.op_type}
                            </span>
                          </td>
                          <td className="mono" style={{ fontSize: "0.8125rem" }}>{tx.train_no || "—"}</td>
                          <td style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{tx.channel || "—"}</td>
                          <td className="mono" style={{ textAlign: "right", fontWeight: 600 }}>{tx.amount.toLocaleString()} ₸</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
