import React, { useState } from "react";
import type { Claim } from "../types";

interface ClaimFeedProps {
  claims: Claim[];
  selectedClaimId: string | null;
  onSelectClaim: (claim: Claim) => void;
}

export const ClaimFeed: React.FC<ClaimFeedProps> = ({
  claims,
  selectedClaimId,
  onSelectClaim,
}) => {
  const [expandedReasoningId, setExpandedReasoningId] = useState<string | null>(null);

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

  const getStatusText = (status: string) => {
    return status.replace("_", " ").toUpperCase();
  };

  const toggleReasoning = (e: React.MouseEvent, claimId: string) => {
    e.stopPropagation(); // Prevent choosing the claim for details
    setExpandedReasoningId(expandedReasoningId === claimId ? null : claimId);
  };

  return (
    <div className="glass-card">
      <h3 className="card-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-bell"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
        Detected Protection Benefits
      </h3>

      <div className="claims-feed">
        {claims.length === 0 ? (
          <div className="no-benefits">
            <div className="no-benefits-icon">✨</div>
            <p>No benefit claims detected. Ingest transactions or run simulator scenarios to auto-detect benefits.</p>
          </div>
        ) : (
          claims.map((claim) => {
            const isSelected = selectedClaimId === claim.id;
            const isReasoningExpanded = expandedReasoningId === claim.id;
            const isHighConfidence = claim.confidence_score >= 0.85;

            return (
              <div
                key={claim.id}
                className={`glass-card claim-item ${claim.benefit_type} ${isSelected ? 'highlight' : ''}`}
                onClick={() => onSelectClaim(claim)}
                style={{ padding: "1.25rem", borderRadius: "12px", borderStyle: "solid" }}
              >
                <div className="claim-header">
                  <div className="claim-title-row">
                    <span className={`badge ${claim.benefit_type}`}>
                      {getBenefitDisplayName(claim.benefit_type)}
                    </span>
                    <span className={`status-badge ${claim.status}`}>
                      {getStatusText(claim.status)}
                    </span>
                  </div>
                  <div className="confidence-indicator-wrapper">
                    <div className={`confidence-indicator ${isHighConfidence ? 'high' : ''}`}>
                      <span className="confidence-dot"></span>
                      <span>{Math.round(claim.confidence_score * 100)}% Match</span>
                    </div>
                  </div>
                </div>

                <div className="claim-body">
                  <div className="claim-meta">
                    <p>
                      Merchant: <span>{claim.pre_filled_fields.merchant_name}</span>
                    </p>
                    {claim.pre_filled_fields.product_description && (
                      <p>
                        Item: <span>{claim.pre_filled_fields.product_description}</span>
                      </p>
                    )}
                    <p style={{ marginTop: "0.2rem" }}>
                      Amount: <span>${claim.pre_filled_fields.purchase_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </p>
                  </div>

                  <div className="claim-action-row">
                    <button
                      className="btn-link"
                      onClick={(e) => toggleReasoning(e, claim.id)}
                      style={{ fontSize: "0.8rem", color: expandedReasoningId === claim.id ? "var(--warning)" : "var(--text-secondary)" }}
                    >
                      {isReasoningExpanded ? "Hide reasoning ▲" : "Why am I seeing this? ▼"}
                    </button>
                    <button className="btn-link" style={{ fontWeight: 700 }}>
                      Review Claim →
                    </button>
                  </div>
                </div>

                {isReasoningExpanded && (
                  <div className="why-reasoning-panel">
                    <p style={{ fontWeight: 600, marginBottom: "0.5rem", color: "var(--text-primary)" }}>
                      Transparency Audit Trace:
                    </p>
                    <div className="reasoning-list">
                      {Object.entries(claim.reasoning).map(([key, check]: [string, any]) => {
                        const name = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                        return (
                          <div key={key} className="reasoning-item">
                            <span className={`reasoning-status ${check.status}`}>
                              {check.status}
                            </span>
                            <span style={{ fontSize: "0.8rem" }}>
                              <strong>{name}</strong>: {check.message}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
