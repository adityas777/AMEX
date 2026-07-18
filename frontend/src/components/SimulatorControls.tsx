import React from "react";

interface SimulatorControlsProps {
  cardholderId: string;
  logs: string[];
  onRunScenario: (scenarioType: string) => Promise<void>;
  onResetDb: () => Promise<void>;
  onSyncGmail: () => Promise<void>;
  isSyncing?: boolean;
}

export const SimulatorControls: React.FC<SimulatorControlsProps> = ({
  cardholderId,
  logs,
  onRunScenario,
  onResetDb,
  onSyncGmail,
  isSyncing = false,
}) => {
  return (
    <div className="glass-card simulator-panel">
      <div className="simulator-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-activity"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
        Streaming Simulator ({cardholderId})
      </div>

      <div>
        <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
          Select a mock transaction + event stream to publish to the engine:
        </p>

        <button
          className="simulator-scenario-btn"
          onClick={() => onRunScenario("purchase_protection_theft")}
        >
          <div className="scenario-title">
            <span>Purchase Protection</span>
            <span className="scenario-tag">Theft</span>
          </div>
          <div className="scenario-desc">
            Sarah Jenkins buys a Sony Mirrorless Camera for $1,899.99 at B&H. 1 day later, she reports the camera stolen and submits a police report.
          </div>
        </button>

        <button
          className="simulator-scenario-btn"
          onClick={() => onRunScenario("travel_delay_flight")}
        >
          <div className="scenario-title">
            <span>Travel Delay</span>
            <span className="scenario-tag">Delay</span>
          </div>
          <div className="scenario-desc">
            Sarah Jenkins books a Lufthansa flight for $1,450.00. 12 hours later, her flight is delayed by 8 hours due to a strike.
          </div>
        </button>

        <button
          className="simulator-scenario-btn"
          onClick={() => onRunScenario("return_protection_refusal")}
        >
          <div className="scenario-title">
            <span>Return Protection</span>
            <span className="scenario-tag">Refusal</span>
          </div>
          <div className="scenario-desc">
            Sarah Jenkins buys Nike Air VaporMax shoes for $280.00. 45 days later, she tries to return them, but Nike Town denies the return.
          </div>
        </button>
      </div>

      <div style={{ marginBottom: "1.25rem" }}>
        <button
          className="btn"
          onClick={onSyncGmail}
          disabled={isSyncing}
          style={{
            width: "100%",
            padding: "0.75rem",
            fontSize: "0.85rem",
            background: isSyncing 
              ? "linear-gradient(135deg, #1e1b4b 0%, #311082 100%)" 
              : "linear-gradient(135deg, #5b21b6 0%, #7c3aed 100%)",
            color: isSyncing ? "var(--text-muted)" : "white",
            boxShadow: isSyncing ? "none" : "0 4px 12px rgba(124, 58, 237, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
            cursor: isSyncing ? "not-allowed" : "pointer"
          }}
        >
          {isSyncing ? (
            <>
              <svg className="animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" style={{ width: "16px", height: "16px" }}>
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" style={{ opacity: 0.25 }}></circle>
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" style={{ opacity: 0.75 }}></path>
              </svg>
              Establishing Secure Connection...
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="feather feather-mail"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
              Sync Alerts from Gmail
            </>
          )}
        </button>
      </div>

      <div>
        <p style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
          Engine Execution Console
        </p>
        <div className="terminal-console">
          {logs.map((log, index) => {
            let className = "console-line";
            if (log.includes("[ERROR]")) className += " err";
            else if (log.includes("[WARN]")) className += " warn";
            else if (log.includes("[SUCCESS]")) className += " info";
            
            return (
              <div key={index} className={className}>
                {log}
              </div>
            );
          })}
          {logs.length === 0 && (
            <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              Ready. Listening for streaming events...
            </div>
          )}
        </div>
      </div>

      <button className="reset-db-btn" onClick={onResetDb}>
        Reset Engine Database & Re-seed
      </button>
    </div>
  );
};
