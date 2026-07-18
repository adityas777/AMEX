import type { EntitlementBalance } from "../types";

interface DashboardProps {
  memberName: string;
  cardProduct: string;
  entitlements: EntitlementBalance[];
}

export const Dashboard: React.FC<DashboardProps> = ({
  memberName,
  cardProduct,
  entitlements,
}) => {
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
    <div className="glass-card highlight">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
            Welcome back, {memberName}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginTop: "0.2rem" }}>
            Active Card: <span style={{ color: "var(--accent-gold-light)", fontWeight: 600 }}>{cardProduct}</span>
          </p>
        </div>
        <div className="logo-container">
          <div className="amex-box" style={{ fontSize: "0.9rem", padding: "0.2rem 0.4rem" }}>AMEX</div>
        </div>
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "1rem" }}>
          Current Annual Coverage Limits
        </h3>
        
        {entitlements.length === 0 ? (
          <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.5rem", borderRadius: "10px", textAlign: "center", border: "1px solid var(--border-light)" }}>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              No protection benefits active on this card product.
            </p>
          </div>
        ) : (
          <div className="entitlements-row">
            {entitlements.map((ent) => {
              const remaining = Math.max(0, ent.annual_limit - ent.utilized_amount);
              const percent = Math.min(100, Math.round((ent.utilized_amount / ent.annual_limit) * 100));
              const radius = 40;
              const circumference = 2 * Math.PI * radius;
              const strokeDashoffset = circumference - (percent / 100) * circumference;

              return (
                <div key={ent.id} className={`entitlement-card ${ent.benefit_type}`}>
                  <div className="entitlement-name">
                    {getBenefitDisplayName(ent.benefit_type)}
                  </div>
                  
                  <div className="entitlement-circle-container">
                    <svg className="entitlement-svg">
                      <circle className="circle-bg" cx="50" cy="50" r={radius} />
                      <circle
                        className="circle-progress"
                        cx="50"
                        cy="50"
                        r={radius}
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                      />
                    </svg>
                    <div className="circle-text">{percent}%</div>
                  </div>
                  
                  <div className="entitlement-details">
                    <div className="entitlement-numbers">
                      Utilized: <span>${ent.utilized_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="entitlement-numbers" style={{ marginTop: "0.2rem" }}>
                      Remaining: <span style={{ color: "var(--success)" }}>${remaining.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
