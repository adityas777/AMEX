import React, { useState, useEffect } from "react";
import type { Claim } from "../types";

interface ClaimDetailProps {
  claim: Claim;
  onSubmitClaim: (claimId: string, updatedFields: any) => Promise<void>;
  onClose: () => void;
}

export const ClaimDetail: React.FC<ClaimDetailProps> = ({
  claim,
  onSubmitClaim,
  onClose,
}) => {
  const [requestedAmount, setRequestedAmount] = useState<number>(0);
  const [description, setDescription] = useState<string>("");
  const [customFields, setCustomFields] = useState<Record<string, any>>({});
  const [uploadedEvidence, setUploadedEvidence] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sync state with selected claim
  useEffect(() => {
    setRequestedAmount(claim.pre_filled_fields.claim_amount_requested);
    setDescription(claim.pre_filled_fields.product_description || "");
    setUploadedEvidence({});
    
    // Copy secondary fields
    const secondary: Record<string, any> = {};
    if (claim.pre_filled_fields.delay_hours !== undefined) secondary.delay_hours = claim.pre_filled_fields.delay_hours;
    if (claim.pre_filled_fields.flight_number !== undefined) secondary.flight_number = claim.pre_filled_fields.flight_number;
    if (claim.pre_filled_fields.store_return_policy !== undefined) secondary.store_return_policy = claim.pre_filled_fields.store_return_policy;
    if (claim.pre_filled_fields.denial_reason !== undefined) secondary.denial_reason = claim.pre_filled_fields.denial_reason;
    setCustomFields(secondary);
  }, [claim]);

  const handleUploadEvidence = (item: string) => {
    setUploadedEvidence((prev) => ({
      ...prev,
      [item]: true,
    }));
  };

  const getStepStatusClass = (step: string) => {
    const status = claim.status;
    
    if (status === "denied") {
      if (step === "under_review") return "step denied";
    }

    const stepsOrder = ["detected", "submitted", "under_review", "approved", "paid"];
    const currentIdx = stepsOrder.indexOf(status === "approved" || status === "paid" ? status : status === "submitted" ? "submitted" : "detected");
    const stepIdx = stepsOrder.indexOf(step);

    if (currentIdx > stepIdx) return "step completed";
    if (currentIdx === stepIdx) return "step active";
    return "step";
  };

  const isFormEditable = claim.status === "detected" || claim.status === "pending_review";
  const requiredEvidenceList = claim.pre_filled_fields.required_evidence || [];
  const allEvidenceUploaded = requiredEvidenceList.every((item) => uploadedEvidence[item]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payloadFields = {
        ...claim.pre_filled_fields,
        claim_amount_requested: requestedAmount,
        product_description: description,
        ...customFields,
      };
      await onSubmitClaim(claim.id, payloadFields);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getBenefitDisplayName = (type: string) => {
    switch (type) {
      case "purchase_protection":
        return "Purchase Protection";
      case "return_protection":
        return "Return Protection";
      case "travel_delay":
        return "Travel Delay Insurance";
      default:
        return type;
    }
  };

  return (
    <div className="glass-card">
      <div className="detail-header-row">
        <div>
          <span className={`badge ${claim.benefit_type}`} style={{ display: "inline-block", marginBottom: "0.25rem" }}>
            {getBenefitDisplayName(claim.benefit_type)}
          </span>
          <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Claim review for {claim.pre_filled_fields.merchant_name}
          </h3>
        </div>
        <button
          className="btn-secondary"
          onClick={onClose}
          style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem", borderRadius: "6px", cursor: "pointer" }}
        >
          Close
        </button>
      </div>

      {/* Claim Progress Stepper */}
      <div className="stepper">
        <div className={getStepStatusClass("detected")}>
          <div className="step-dot">1</div>
          <div className="step-label">Detected</div>
        </div>
        <div className={getStepStatusClass("submitted")}>
          <div className="step-dot">2</div>
          <div className="step-label">Submitted</div>
        </div>
        <div className={getStepStatusClass("under_review")}>
          <div className="step-dot">3</div>
          <div className="step-label">{claim.status === "denied" ? "Denied" : "Under Review"}</div>
        </div>
        <div className={getStepStatusClass("approved")}>
          <div className="step-dot">4</div>
          <div className="step-label">Approved</div>
        </div>
        <div className={getStepStatusClass("paid")}>
          <div className="step-dot">5</div>
          <div className="step-label">Paid</div>
        </div>
      </div>

      <form className="claim-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Cardholder Name</label>
            <input
              type="text"
              className="form-input"
              value={claim.pre_filled_fields.cardholder_name}
              disabled
            />
          </div>
          <div className="form-group">
            <label>Card Product</label>
            <input
              type="text"
              className="form-input"
              value={claim.pre_filled_fields.card_product}
              disabled
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Merchant Name</label>
            <input
              type="text"
              className="form-input"
              value={claim.pre_filled_fields.merchant_name}
              disabled
            />
          </div>
          <div className="form-group">
            <label>Purchase Date</label>
            <input
              type="text"
              className="form-input"
              value={claim.pre_filled_fields.purchase_date}
              disabled
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Transaction Amount</label>
            <input
              type="text"
              className="form-input"
              value={`$${claim.pre_filled_fields.purchase_amount.toFixed(2)}`}
              disabled
            />
          </div>
          <div className="form-group">
            <label>Requested Claim Amount</label>
            <input
              type="number"
              step="0.01"
              max={claim.pre_filled_fields.purchase_amount}
              className="form-input"
              value={requestedAmount}
              onChange={(e) => setRequestedAmount(parseFloat(e.target.value) || 0)}
              disabled={!isFormEditable}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label>Product Description / Notes</label>
          <textarea
            className="form-input"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={!isFormEditable}
            style={{ resize: "vertical" }}
          />
        </div>

        {/* Custom fields based on benefit type */}
        {claim.benefit_type === "travel_delay" && (
          <div className="form-row" style={{ marginTop: "0.2rem" }}>
            <div className="form-group">
              <label>Flight Number</label>
              <input
                type="text"
                className="form-input"
                value={customFields.flight_number || ""}
                onChange={(e) => setCustomFields({ ...customFields, flight_number: e.target.value })}
                disabled={!isFormEditable}
              />
            </div>
            <div className="form-group">
              <label>Delay Hours</label>
              <input
                type="number"
                className="form-input"
                value={customFields.delay_hours || 0}
                onChange={(e) => setCustomFields({ ...customFields, delay_hours: parseInt(e.target.value) || 0 })}
                disabled={!isFormEditable}
              />
            </div>
          </div>
        )}

        {claim.benefit_type === "return_protection" && (
          <div className="form-group">
            <label>Store Return Denial Reason</label>
            <input
              type="text"
              className="form-input"
              value={customFields.denial_reason || ""}
              onChange={(e) => setCustomFields({ ...customFields, denial_reason: e.target.value })}
              disabled={!isFormEditable}
            />
          </div>
        )}

        {/* Evidence upload simulation checklist */}
        <div className="evidence-section">
          <div className="evidence-title">Required Claim Evidence Documents</div>
          <div className="evidence-list">
            {requiredEvidenceList.map((item, idx) => {
              const uploaded = !!uploadedEvidence[item];
              return (
                <div key={idx} className="evidence-item">
                  <span>{item}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <span className={`evidence-status ${uploaded ? "uploaded" : "missing"}`}>
                      {uploaded ? "✓ Uploaded" : "⚠ Missing"}
                    </span>
                    {!uploaded && isFormEditable && (
                      <button
                        type="button"
                        className="btn-upload"
                        onClick={() => handleUploadEvidence(item)}
                      >
                        Mock Upload
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {isFormEditable && (
          <div className="button-group">
            <button
              type="submit"
              className="btn btn-primary"
              style={{ flexGrow: 1 }}
              disabled={!allEvidenceUploaded || isSubmitting}
            >
              {isSubmitting ? "Submitting..." : allEvidenceUploaded ? "Submit Claim Verification" : "Upload Required Evidence to Submit"}
            </button>
          </div>
        )}

        {!isFormEditable && (
          <div style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--border-light)", borderRadius: "8px", padding: "0.85rem", textAlign: "center", marginTop: "0.5rem" }}>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
              Claim submitted and locked. Underwriting progress is simulated in real-time.
            </p>
          </div>
        )}
      </form>
    </div>
  );
};
