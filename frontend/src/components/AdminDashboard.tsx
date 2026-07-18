import React, { useState } from "react";
import type { Claim } from "../types";

interface AdminDashboardProps {
  claims: Claim[];
  onUpdateStatus: (claimId: string, status: string) => Promise<void>;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  claims,
  onUpdateStatus,
}) => {
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const selectedClaim = claims.find((c) => c.id === selectedClaimId);

  const filteredClaims = claims.filter((c) => {
    const statusMatch = statusFilter === "all" || c.status === statusFilter;
    const typeMatch = typeFilter === "all" || c.benefit_type === typeFilter;
    return statusMatch && typeMatch;
  });

  const getBenefitDisplayName = (type: string) => {
    switch (type) {
      case "purchase_protection":
        return "Purchase Protection";
      case "return_protection":
        return "Return Protection";
      case "travel_delay":
        return "Travel Delay";
      default:
        return type;
    }
  };

  const handleStatusAction = async (claimId: string, status: string) => {
    setActionInProgress(claimId);
    try {
      await onUpdateStatus(claimId, status);
    } catch (err) {
      console.error(err);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="glass-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h3 className="card-title" style={{ margin: 0 }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-shield"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
          Underwriting Operations Dashboard
        </h3>
        
        {/* Filters */}
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <select
            className="custom-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ padding: "0.3rem 1.8rem 0.3rem 0.6rem", fontSize: "0.8rem", borderRadius: "6px" }}
          >
            <option value="all">All Statuses</option>
            <option value="detected">Detected</option>
            <option value="submitted">Submitted</option>
            <option value="approved">Approved</option>
            <option value="paid">Paid</option>
            <option value="denied">Denied</option>
          </select>
          
          <select
            className="custom-select"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            style={{ padding: "0.3rem 1.8rem 0.3rem 0.6rem", fontSize: "0.8rem", borderRadius: "6px" }}
          >
            <option value="all">All Benefits</option>
            <option value="purchase_protection">Purchase Protection</option>
            <option value="return_protection">Return Protection</option>
            <option value="travel_delay">Travel Delay</option>
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selectedClaimId ? "1fr 400px" : "1fr", gap: "1.5rem" }}>
        {/* Main Claims Table */}
        <div className="admin-table-wrapper">
          {filteredClaims.length === 0 ? (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-secondary)" }}>
              No claims match the selected filters.
            </div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Cardholder ID</th>
                  <th>Benefit Type</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredClaims.map((claim) => {
                  const isClaimSelected = selectedClaimId === claim.id;
                  return (
                    <tr
                      key={claim.id}
                      onClick={() => setSelectedClaimId(claim.id)}
                      style={{
                        cursor: "pointer",
                        backgroundColor: isClaimSelected ? "rgba(0, 112, 210, 0.08)" : "",
                        borderLeft: isClaimSelected ? "3px solid var(--amex-blue)" : "none"
                      }}
                    >
                      <td style={{ fontFamily: "monospace" }}>{claim.id}</td>
                      <td>{claim.transaction?.card_member_id || "N/A"}</td>
                      <td>
                        <span className={`badge ${claim.benefit_type}`}>
                          {getBenefitDisplayName(claim.benefit_type)}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        ${claim.pre_filled_fields.claim_amount_requested.toFixed(2)}
                      </td>
                      <td>
                        <span className={`status-badge ${claim.status}`}>
                          {claim.status.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <div className={`confidence-indicator ${claim.confidence_score >= 0.85 ? 'high' : ''}`} style={{ fontSize: "0.8rem" }}>
                          <span className="confidence-dot"></span>
                          <span>{Math.round(claim.confidence_score * 100)}%</span>
                        </div>
                      </td>
                      <td>
                        <button
                          className="admin-action-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedClaimId(claim.id);
                          }}
                        >
                          Audit Trace
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Selected Claim Audit Trace Panel */}
        {selectedClaim && (
          <div className="glass-card" style={{ background: "rgba(255,255,255,0.015)", border: "1px solid var(--border-light)", display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-light)", paddingBottom: "0.5rem" }}>
              <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>Underwriting Review</span>
              <button
                className="btn-link"
                onClick={() => setSelectedClaimId(null)}
                style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}
              >
                Close ✕
              </button>
            </div>

            <div>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Claim Request Details</p>
              <div style={{ marginTop: "0.25rem", fontSize: "0.85rem" }}>
                <p><strong>Merchant:</strong> {selectedClaim.pre_filled_fields.merchant_name}</p>
                <p><strong>Product:</strong> {selectedClaim.pre_filled_fields.product_description}</p>
                <p><strong>Cost:</strong> ${selectedClaim.pre_filled_fields.purchase_amount.toFixed(2)}</p>
                <p><strong>Requested Cover:</strong> <span style={{ color: "var(--success)", fontWeight: 600 }}>${selectedClaim.pre_filled_fields.claim_amount_requested.toFixed(2)}</span></p>
                <p><strong>Current Status:</strong> <span className={`status-badge ${selectedClaim.status}`} style={{ fontSize: "0.7rem", verticalAlign: "middle" }}>{selectedClaim.status}</span></p>
              </div>
            </div>

            {/* Audit Trace Logs */}
            <div className="audit-section">
              <div className="audit-title">Deterministic Rule Validation</div>
              <div className="reasoning-list">
                {Object.entries(selectedClaim.reasoning)
                  .filter(([key]) => key !== "ml_classifier_validation")
                  .map(([key, check]: [string, any]) => {
                    const name = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                    return (
                      <div key={key} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", marginBottom: "0.4rem" }}>
                        <span className={`reasoning-status ${check.status}`} style={{ fontSize: "0.7rem", padding: "0.05rem 0.25rem" }}>
                          {check.status}
                        </span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                          <strong>{name}</strong>: {check.message}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>

            {selectedClaim.reasoning.ml_classifier_validation && (
              <div className="audit-section" style={{ borderColor: "rgba(0,112,210,0.2)" }}>
                <div className="audit-title" style={{ color: "var(--amex-blue)" }}>ML Classifier Insights</div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
                  <span className="reasoning-status PASS" style={{ fontSize: "0.7rem", padding: "0.05rem 0.25rem" }}>
                    MODEL
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    {selectedClaim.reasoning.ml_classifier_validation.message}
                  </span>
                </div>
              </div>
            )}

            {/* Action Buttons for Admin */}
            {selectedClaim.status === "submitted" && (
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button
                  className="btn btn-primary"
                  onClick={() => handleStatusAction(selectedClaim.id, "approved")}
                  disabled={actionInProgress === selectedClaim.id}
                  style={{ flex: 1, padding: "0.5rem", fontSize: "0.8rem", borderRadius: "6px" }}
                >
                  Approve
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleStatusAction(selectedClaim.id, "denied")}
                  disabled={actionInProgress === selectedClaim.id}
                  style={{ flex: 1, padding: "0.5rem", fontSize: "0.8rem", borderRadius: "6px", border: "1px solid var(--danger)", color: "#ff8888" }}
                >
                  Deny
                </button>
              </div>
            )}

            {selectedClaim.status === "approved" && (
              <button
                className="btn btn-primary"
                onClick={() => handleStatusAction(selectedClaim.id, "paid")}
                disabled={actionInProgress === selectedClaim.id}
                style={{ padding: "0.5rem", fontSize: "0.8rem", borderRadius: "6px", background: "var(--success)" }}
              >
                Mark Paid / Transfer Funds
              </button>
            )}

            {selectedClaim.status === "paid" && (
              <div style={{ background: "rgba(5, 205, 153, 0.05)", border: "1px solid rgba(5, 205, 153, 0.2)", color: "var(--success)", padding: "0.6rem", borderRadius: "6px", textAlign: "center", fontSize: "0.8rem", fontWeight: 600 }}>
                ✓ Claim Fully Paid & Settled
              </div>
            )}

            {selectedClaim.status === "denied" && (
              <div style={{ background: "rgba(255, 92, 92, 0.05)", border: "1px solid rgba(255, 92, 92, 0.2)", color: "#ff8888", padding: "0.6rem", borderRadius: "6px", textAlign: "center", fontSize: "0.8rem", fontWeight: 600 }}>
                ✕ Claim Application Denied
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
