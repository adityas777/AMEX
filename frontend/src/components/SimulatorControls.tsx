import React from "react";

interface SimulatorControlsProps {
  cardholderId: string;
  logs: string[];
  onRunScenario: (scenarioType: string) => Promise<void>;
  onResetDb: () => Promise<void>;
}

export const SimulatorControls: React.FC<SimulatorControlsProps> = ({
  cardholderId,
  logs,
  onRunScenario,
  onResetDb,
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
